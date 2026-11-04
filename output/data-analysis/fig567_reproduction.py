"""Reproduce DFPS Figs. 5-7 (Zolfaghari et al. 2025, pp. 10-12) with B* and the paper's baselines (user request 2026-10-17).

  python -I output/data-analysis/fig567_reproduction.py run [--seeds 1-5] [--workers 10]
  python -I output/data-analysis/fig567_reproduction.py analyze
  add --protocol v2 to either for the protocol of 2026-11-03 (results/fig567_v2, fig567_reproduction_v2.json):
    fixed request count (run length 300 s / arrival scale, warm-up 10% of it; Figs. 6-7 run at scale 1, so 300 s / 30 s as before),
    Heu and RL release every container after its task (keep_warm=0: Xu et al. 2023 Alg. 1 l. 9 creates an instance per request;
    DFPS p. 11 "aggressive removal of idle instances"), and utilisation also as busy / alive-container time (util_alive).
    Why: knowledge/synthesis/fig5-7-reproduction-gap.md (probes 1-2). Capacity model CAP-U.

Not part of the pre-registered headroom plan; a reproduction add-on. Setting as G2 (Table 2, 300 s runs, 30 s warm-up, drained):
  Fig. 5  arrival scale 0.25, 0.5, ..., 2.0          (80 nodes, 15 applications)
  Fig. 6  network size 20, 40, ..., 160 nodes          (scale 1.0, 15 applications)
  Fig. 7  application types 5, 10, ..., 40             (scale 1.0, 80 nodes)
  x Uniform and Pareto, seeds as given (the paper: 10 workloads per point).
Methods: SR, SG (|.| Eq. 3), DFPS = B*, Heu (Xu et al. 2023), RL (MOSEC-style DQN, results/rl_policy.pt). Metrics as in the
paper: mean makespan, utilisation, cold starts. One job per (scenario, method) so a slow cell does not hold the others.
Cells shared with G2 (Fig. 5 scales 0.25/0.5/1.0/2.0) reuse G2's scenario and its SR / SG_abs / DFPS_B_STAR results.
Overload handling as G2 (retry throttle 1 s, cap 10 per round) whenever the scenario's offered utilisation is >= 0.8 or the
cell is one G2 treated as overloaded; the flag is stored with every result.
"""
from __future__ import annotations

import argparse
import json
import pickle
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from experiments.run import ASSUME, initial_placements, run_methods  # noqa: E402
from dfps.sim import Sim  # noqa: E402
from dfps.variants import make_adjuster, sim_kwargs  # noqa: E402
from dfps.workload import build_scenario  # noqa: E402

RUNS = ROOT / "results" / "fig567_cal"
# Calibrated scenario (2026-10-18, calibrate_fig5.py stage "depth", setting d2_any_distinct; chosen on Fig. 5 only, Figs. 6-7 held
# out): Alibaba jobs under 60 s whose longest chain is <= 2 tasks (single-task jobs included), every task its own function type,
# Table-2 load unchanged. B* and the baselines are unchanged. G2's scenarios use the old setting, so nothing is reused from G2.
CAL_DAGS, CAL_MAXDEPTH, CAL_MAPPING = "alibaba_dags_lt60s_min1.json", 2, "distinct"
G2 = ROOT / "results" / "g2_reproduction"
OUT = ROOT / "output" / "data-analysis" / "results"
KINDS = ("uniform", "pareto")
SCALES = (0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0)
NETS = (20, 40, 60, 80, 100, 120, 140, 160)
APPS = (5, 10, 15, 20, 25, 30, 35, 40)
METHODS = ("SR", "SG", "DFPS", "HEU", "RL", "RL_CAL")
G2_NAME = {"SR": "SR", "SG": "SG_abs", "DFPS": "DFPS_B_STAR"}


def cells():
    """Unique scenario cells: (kind, scale, ne, nw) -> list of figures using it."""
    out = {}
    for kind in KINDS:
        for s in SCALES:
            out.setdefault((kind, s, 80, 15), []).append("fig5")
        for ne in NETS:
            out.setdefault((kind, 1.0, ne, 15), []).append("fig6")
        for nw in APPS:
            out.setdefault((kind, 1.0, 80, nw), []).append("fig7")
    return out


def tag(kind, s, ne, nw, seed):
    return f"{kind}_x{s}_n{ne}_a{nw}_s{seed}"


def g2_tag(kind, s, ne, nw, seed):
    return None                                                     # calibrated setting: never reuse G2 (old scenarios)


def _g2_tag_old(kind, s, ne, nw, seed):
    if ne == 80 and nw == 15 and s in (0.25, 0.5, 1.0, 2.0):
        return f"{kind}_x{s}_s{seed}"
    return None


def offered_util(sc):
    mu = np.array([f.exec_time for f in sc.functions])
    W = np.array([sum(mu[w.ft[t]] for t in range(w.n)) for w in sc.workflows])
    return float((np.array(sc.meta["per_app_rate"]) * W).sum() / sc.ecc.sum())


def job(args):
    try:
        return _job(args)
    except Exception:
        import traceback
        Path(args[1]).with_suffix(".err").write_text(traceback.format_exc())
        return args[1] + " FAILED"


def timing(proto, sc):
    """(run length, warm-up): v1 = the scenario's 300 s / 30 s; v2 = fixed request count (300 s / scale, warm-up 10%)."""
    if proto == "v2":
        d = ASSUME["A21_run_length_s"] / float(sc.meta["scale"])
        return d, 0.1 * d
    return ASSUME["A21_run_length_s"], ASSUME["A21_warmup_s"]


def _job(args):
    sc_path, out_path, seed, method = args[:4]
    proto = args[4] if len(args) > 4 else "v1"
    if proto == "v2":
        return _job_v2(sc_path, out_path, seed, method)
    if Path(out_path).exists():
        return out_path
    sc = pickle.load(open(sc_path, "rb"))
    rho = offered_util(sc)
    g2_over = sc.meta["kind"] == "pareto" and sc.meta["scale"] >= 0.5 or sc.meta["scale"] >= 2.0
    overloaded = bool(rho >= 0.8 or g2_over)
    t = time.time()
    if method in ("HEU", "RL", "RL_CAL"):
        # RL_CAL (2026-10-18): the same RL baseline retrained on the calibrated scenario (results/rl_policy_cal.pt)
        pt = "rl_policy_cal.pt" if method == "RL_CAL" else "rl_policy.pt"
        m0 = "RL" if method == "RL_CAL" else method
        res, _ = run_methods(sc, seed, ASSUME["A06_generations"], methods=(m0,), rl_path=str(ROOT / "results" / pt))
        r = res[m0]
    else:
        x_sr, x_sg, _ = initial_placements(sc, seed, ASSUME["A06_generations"], "abs")
        kw = sim_kwargs("B_STAR", ASSUME)
        retry, cap = (1.0, 10) if overloaded else (0.0, None)
        adj = make_adjuster("B_STAR", ASSUME, seed=seed + 300) if method == "DFPS" else None
        sim = Sim(sc, x_sr if method == "SR" else x_sg, adjuster=adj, seed=seed + 400, retry_min_interval=retry,
                  retry_max_attempts=cap, **kw)
        r = sim.run()
        sim.check_invariants()
    r["wall_s"] = time.time() - t
    Path(out_path).write_text(json.dumps(dict(method=method, seed=seed, overloaded=overloaded, offered_util=rho,
                                              meta={k: v for k, v in sc.meta.items() if k != "per_app_rate"}, result=r)))
    return out_path


def _job_v2(sc_path, out_path, seed, method):
    from fig5_pattern_probe import AcctOnDemand
    from experiments.run import load_rl_policy
    from dfps.heu import HeuPolicy
    import torch
    torch.set_num_threads(1)
    sc = pickle.load(open(sc_path, "rb"))
    dur, warm = timing("v2", sc)
    rho = offered_util(sc)
    overloaded = bool(rho >= 0.8 or (sc.meta["kind"] == "pareto" and sc.meta["scale"] >= 0.5) or sc.meta["scale"] >= 2.0)
    t = time.time()
    if method in ("HEU", "RL", "RL_CAL"):
        pt = "rl_policy_cal.pt" if method == "RL_CAL" else "rl_policy.pt"
        pol = HeuPolicy(seed=seed + 500) if method == "HEU" else load_rl_policy(str(ROOT / "results" / pt), seed + 600)
        sim = AcctOnDemand(sc, pol, seed=seed + 400, duration=dur, warmup=warm, keep_warm=0)
    else:
        x_sr, x_sg, _ = initial_placements(sc, seed, ASSUME["A06_generations"], "abs")
        kw = sim_kwargs("B_STAR", ASSUME)
        kw["warmup"] = warm
        retry, cap = (1.0, 10) if overloaded else (0.0, None)
        adj = make_adjuster("B_STAR", ASSUME, seed=seed + 300) if method == "DFPS" else None
        sim = Sim(sc, x_sr if method == "SR" else x_sg, adjuster=adj, seed=seed + 400, retry_min_interval=retry,
                  retry_max_attempts=cap, **kw)
    r = sim.run()
    sim.check_invariants()
    r["wall_s"] = time.time() - t
    busy = r["utilization"] * float(sc.ecc.sum()) * (dur - warm)
    r["util_alive"] = busy / r["provisioned_slot_s"] if r.get("provisioned_slot_s") else None
    Path(out_path).write_text(json.dumps(dict(method=method, seed=seed, overloaded=overloaded, offered_util=rho, protocol="v2",
                                              capacity_model="CAP-U", duration=dur, warmup=warm,
                                              meta={k: v for k, v in sc.meta.items() if k != "per_app_rate"}, result=r)))
    return out_path


def run(a):
    global RUNS
    lo, hi = (int(x) for x in a.seeds.split("-"))
    if a.protocol == "v2":
        RUNS = ROOT / "results" / "fig567_v2"
    RUNS.mkdir(parents=True, exist_ok=True)
    dags, jobs = None, []
    for (kind, s, ne, nw) in cells():
        for seed in range(lo, hi + 1):
            tg = tag(kind, s, ne, nw, seed)
            gt = g2_tag(kind, s, ne, nw, seed)
            sc_path = (G2 / f"{gt}.pkl") if gt else (RUNS / f"{tg}.pkl")
            if not sc_path.exists():
                if dags is None:
                    from calibrate_fig5 import dag_depth
                    dags = [d for d in json.load(open(ROOT / "data" / CAL_DAGS)) if dag_depth(d) <= CAL_MAXDEPTH]
                d = ASSUME["A21_run_length_s"] / (s if a.protocol == "v2" else 1.0)
                sc = build_scenario(seed, kind, s, ne=ne, n_workflows=nw, duration_s=d, dags=dags, function_mapping=CAL_MAPPING,
                                    pool_size=ASSUME["A17_function_pool_size"])
                if a.protocol == "v2":
                    sc.meta = dict(sc.meta, capacity_model="CAP-U", protocol="v2")
                pickle.dump(sc, open(sc_path, "wb"))
            for m in METHODS:
                if gt and m in G2_NAME:
                    continue                                          # taken from G2 in analyze
                jobs.append((str(sc_path), str(RUNS / f"{tg}.{m}.json"), seed, m, a.protocol))
    del dags
    # slowest first (overloaded: low node counts, many apps, high scales, Pareto) so the tail is short
    jobs.sort(key=lambda j: ("pareto" not in j[0], "_n20_" not in j[1] and "_n40_" not in j[1]))
    print(len(jobs), "jobs", flush=True)
    with ProcessPoolExecutor(a.workers) as ex:
        for d in ex.map(job, jobs):
            print("done", d, flush=True)


def load():
    """rows[(kind, scale, ne, nw)][method] = list of result dicts."""
    rows = {}
    for f in RUNS.glob("*.json"):
        d = json.loads(f.read_text())
        m = d["meta"]
        key = (m["kind"], float(m["scale"]), int(m.get("ne", 80)), int(m.get("nw", 15)))
        rows.setdefault(key, {}).setdefault(d["method"], []).append(d["result"])
    for f in ([] if True else G2.glob("*.json")):                  # calibrated setting: G2 results are not comparable
        d = json.loads(f.read_text())
        key = (d["meta"]["kind"], float(d["meta"]["scale"]), 80, 15)
        for m, g in G2_NAME.items():
            if g in d["results"]:
                rows.setdefault(key, {}).setdefault(m, []).append(d["results"][g])
    return rows


def analyze(a):
    global RUNS
    if a.protocol == "v2":
        RUNS = ROOT / "results" / "fig567_v2"
    rows = load()
    figs = {"fig5": ("scale", SCALES), "fig6": ("ne", NETS), "fig7": ("nw", APPS)}
    out = {}
    for fig, (axis, xs) in figs.items():
        out[fig] = {}
        for kind in KINDS:
            series = {}
            for m in METHODS:
                pts = []
                for x in xs:
                    key = {"scale": (kind, x, 80, 15), "ne": (kind, 1.0, x, 15), "nw": (kind, 1.0, 80, x)}[axis]
                    rs = rows.get(key, {}).get(m, [])
                    pts.append(dict(x=x, n=len(rs),
                                    makespan=float(np.mean([r["avg_makespan"] for r in rs])) if rs else None,
                                    util=float(np.mean([r["utilization"] for r in rs]) * 100) if rs else None,
                                    util_alive=float(np.mean([r["util_alive"] for r in rs]) * 100)
                                    if rs and all(r.get("util_alive") is not None for r in rs) else None,
                                    cold=float(np.mean([r["cold_starts"] for r in rs])) if rs else None,
                                    unfinished_max=int(max(r.get("n_unfinished", 0) for r in rs)) if rs else None))
                series[m] = pts
            out[fig][kind] = series
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / ("fig567_reproduction_v2.json" if a.protocol == "v2" else "fig567_reproduction_cal.json")).write_text(json.dumps(out, indent=1))
    for fig in out:
        for kind in KINDS:
            print(fig, kind)
            for m, pts in out[fig][kind].items():
                print("  ", m.ljust(5), " ".join("-" if p["makespan"] is None else f"{p['makespan']:.0f}" for p in pts),
                      "| n", min(p["n"] for p in pts))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "analyze"])
    ap.add_argument("--seeds", default="1-5")
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--protocol", choices=["v1", "v2"], default="v1")
    a = ap.parse_args()
    run(a) if a.cmd == "run" else analyze(a)
