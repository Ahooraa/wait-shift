"""D3 with the simulation-scored oracle O3S (dfps/o3s.py; design output/data-analysis/sim/D3_O3S_design.md; user-approved
deviation 2026-10-17: 27 runs = seeds 1-3 of every family x load, epoch 30 s, horizon 30 s, K = 8, run before Figs. 5-7).

  python -I output/data-analysis/d3s_headroom.py run [--workers N]
  python -I output/data-analysis/d3s_headroom.py analyze

Same scenarios, X0, T*, seeds and simulator settings as D1 (results/d1_headroom), so B* and O1+B* come from D1's runs.
Outputs: h_O3S = (B* - O3S)/B* on P99; O3S vs O1+B* (does scoring placement with dispatch add beyond D1's switching?);
scorer noise floor = Kendall tau between two simulated rankings with different execution-time streams (5 checks per run).
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

import yaml  # noqa: E402
from dfps.o3s import O3SimAdjuster  # noqa: E402
from dfps.sim import Sim  # noqa: E402
from dfps.variants import make_adjuster, sim_kwargs  # noqa: E402

D1 = ROOT / "results" / "d1_headroom"
RUNS = ROOT / "results" / "d3s_headroom"
OUT = ROOT / "output" / "data-analysis" / "results"
ASSUME = yaml.safe_load((ROOT / "config" / "assumptions.yaml").read_text(encoding="utf-8"))   # no PyTorch import (OMP #15)
FAMILIES, RHOS, SEEDS = ("F1", "F2", "F3"), (0.5, 0.7, 0.85), (1, 2, 3)
DURATION, WARMUP, EPOCH, HORIZON, K = 900.0, 60.0, 30.0, 30.0, 8
SUFFIX = "O3S"
BLIND = False
FUTURE = None
CAND = "full"
CHURN = {}
# Long look-ahead variant (user request 2026-10-17): python ... run --long  -> horizon 120 s, epoch 60 s, K = 5 (no local variants),
# seed 1 of every family x load (9 runs), files <tag>.O3S_h120.json


def configure(long, seeds=None, blind=False, future=None, cand="full", horizon=None, k=None, epoch=None, min_frac=None, cap=None,
              min_backlog=None):
    global EPOCH, HORIZON, K, SEEDS, SUFFIX, BLIND, FUTURE, CAND, CHURN
    BLIND, FUTURE, CAND = bool(blind), future, cand
    if long:
        EPOCH, HORIZON, K, SEEDS, SUFFIX = 60.0, 120.0, 5, (1,), "O3S_h120"
    if blind:
        SUFFIX += "_blind"
    if future == "rate":
        SUFFIX += "_rateoracle"
    if cand != "full":
        SUFFIX += "_" + cand
    if horizon:
        HORIZON = float(horizon)
        SUFFIX += f"_H{int(horizon)}"
    if k:
        K = int(k)
        SUFFIX += f"_K{K}"
    if epoch:
        EPOCH = float(epoch)
        SUFFIX += f"_E{int(epoch)}"
    CHURN = {}
    if min_frac:
        CHURN["min_frac"] = float(min_frac)
        SUFFIX += f"_frac{min_frac}"
    if cap:
        CHURN["cap"] = int(cap)
        SUFFIX += f"_cap{int(cap)}"
    if min_backlog:
        CHURN["min_backlog"] = float(min_backlog)
        SUFFIX += f"_bl{min_backlog}"
    if seeds:
        lo, hi = (int(x) for x in seeds.split("-"))
        SEEDS = tuple(range(lo, hi + 1))


def tag(f, r, s):
    return f"{f}_r{r}_s{s}"


def job(args):
    try:
        return _job(args)
    except Exception:
        import traceback
        Path(args[1]).with_suffix(".err").write_text(traceback.format_exc())
        return args[1] + " FAILED"


def _job(args):
    assert np.__version__.startswith("1."), "run with the Anaconda interpreter (numpy 1.26): numpy 2 changes the random streams"
    tg, out_path, seed, period = args[:4]
    duration = args[4] if len(args) > 4 else DURATION
    epoch, horizon, k_c = (args[5], args[6], args[7]) if len(args) > 7 else (EPOCH, HORIZON, K)
    # mode must travel with the job: spawned workers re-import this module, so globals set by configure() are NOT seen there
    # (bug found 2026-10-21: blind / rate-oracle runs had silently run as the exact oracle)
    blind, future, cand = (args[8], args[9], args[10]) if len(args) > 10 else (BLIND, FUTURE, CAND)
    churn = args[11] if len(args) > 11 else CHURN
    if Path(out_path).exists():
        return out_path
    sc = pickle.load(open(D1 / f"{tg}.pkl", "rb"))
    P = pickle.load(open(D1 / f"{tg}.prep.pkl", "rb"))
    kw = sim_kwargs("B_STAR", ASSUME)
    kw.update(warmup=WARMUP, duration=duration, retry_min_interval=1.0, retry_max_attempts=10)
    if churn.get("elastic"):                                                  # elastic capacity (slots may stay empty)
        kw["elastic"] = True
    adj = O3SimAdjuster(make_adjuster("B_STAR", ASSUME, seed=seed + 300), period, epoch=epoch, horizon=horizon, K=k_c,
                        seed=seed + 800, tau_checks=5, warmup=WARMUP, blind=blind, future=future, cand_mode=cand, churn=churn)
    kw["interval"] = adj.next_interval
    t = time.time()
    sim = Sim(sc, P["X0"], adjuster=adj, seed=seed + 400, **kw)
    r = sim.run()
    sim.check_invariants()
    r["wall_s"] = time.time() - t
    Path(out_path).write_text(json.dumps(dict(family=sc.meta["family"], rho=sc.meta["rho"], seed=seed, period=period, result=r,
                                              n_switch=adj.n_switch, decisions=adj.log, taus=adj.taus,
                                              epoch=epoch, horizon=horizon, K=k_c, mode=dict(future=adj.future, cand=adj.cand_mode, churn=adj.churn),
                                              swap_log=getattr(adj, "swap_log", None), rebal_moves=getattr(adj, "rebal_moves", None),
                                              fine_moves=getattr(adj, "fine_moves", None),
                                              env=dict(python=sys.version.split()[0], numpy=np.__version__))))
    return out_path


def run(a):
    T = json.loads((OUT / "g2_tstar.json").read_text())
    T = {f: float(T["families"][f]["T_star"]) for f in FAMILIES}
    RUNS.mkdir(parents=True, exist_ok=True)
    fams = tuple(a.families.split(",")) if getattr(a, "families", None) else FAMILIES
    jobs = [(tag(f, r, s), str(RUNS / f"{tag(f, r, s)}.{SUFFIX}.json"), s, T[f], DURATION, EPOCH, HORIZON, K, BLIND, FUTURE, CAND, CHURN) for f in fams for r in RHOS for s in SEEDS]
    jobs.sort(key=lambda j: -float(j[0].split("_r")[1].split("_")[0]))       # high load first (slowest)
    with ProcessPoolExecutor(a.workers) as ex:
        for d in ex.map(job, jobs):
            print("done", d, flush=True)


def boot_ci(x, n=10_000, seed=0):
    x = np.asarray([v for v in x if np.isfinite(v)], dtype=float)
    if len(x) < 2:
        return dict(mean=float(x.mean()) if len(x) else float("nan"), lo=float("nan"), hi=float("nan"), n=int(len(x)))
    m = np.random.default_rng(seed).choice(x, (n, len(x)), replace=True).mean(axis=1)
    return dict(mean=float(x.mean()), lo=float(np.percentile(m, 2.5)), hi=float(np.percentile(m, 97.5)), n=int(len(x)),
                median=float(np.median(x)))


def analyze(a):
    metric = "p99_makespan"
    res = {}
    for f in RUNS.glob(f"*.{SUFFIX}.json"):
        d = json.loads(f.read_text())
        res.setdefault((d["family"], d["rho"], d["seed"]), {})["O3S"] = d
    for f in D1.glob("*.json"):
        d = json.loads(f.read_text())
        if d.get("ctrl") in ("B_STAR", "O1_BSTAR", "S_MEAN"):
            key = (d["family"], d["rho"], d["seed"])
            if key in res:
                res[key][d["ctrl"]] = d
    out = dict(metric=metric, families={}, cells={}, design=dict(epoch=EPOCH, horizon=HORIZON, K=K, seeds=SEEDS))

    def summ(keys):
        h, vs_o1, sat, taus, sw, best = [], [], [], [], [], {}
        p = {c: [] for c in ("B_STAR", "O1_BSTAR", "O3S")}
        for k in keys:
            c = res[k]
            if not all(x in c for x in ("B_STAR", "O3S")):
                continue
            b, o = c["B_STAR"]["result"][metric], c["O3S"]["result"][metric]
            h.append((b - o) / b)
            for x in p:
                if x in c:
                    p[x].append(c[x]["result"][metric])
            if "O1_BSTAR" in c:
                vs_o1.append((c["O1_BSTAR"]["result"][metric] - o) / c["O1_BSTAR"]["result"][metric])
            if "S_MEAN" in c and b - o > 0:
                sat.append((b - c["S_MEAN"]["result"][metric]) / (b - o))
            taus += [t for t in c["O3S"]["taus"] if np.isfinite(t)]
            sw.append(c["O3S"]["n_switch"] / max(1, len(c["O3S"]["decisions"])))
            for d in c["O3S"]["decisions"]:
                if d["switched"]:
                    best[d["best"]] = best.get(d["best"], 0) + 1
        return dict(h=boot_ci(h), o3s_vs_o1bstar=boot_ci(vs_o1), heuristic_saturation=boot_ci(sat), scorer_tau=boot_ci(taus),
                    switch_share=float(np.mean(sw)) if sw else float("nan"), switched_to=best,
                    p99_mean={x: float(np.mean(v)) if v else float("nan") for x, v in p.items()})

    for f in FAMILIES:
        fk = []
        for r in RHOS:
            keys = [(f, r, s) for s in SEEDS if (f, r, s) in res]
            fk += keys
            out["cells"][f"{f}_r{r}"] = summ(keys)
        out["families"][f] = summ(fk)
    lo = {f: out["families"][f]["h"]["lo"] for f in FAMILIES}
    n_go = sum(1 for v in lo.values() if np.isfinite(v) and v >= 0.25)
    kill = all(np.isfinite(v) and v < 0.10 for v in lo.values())
    dec = "GO" if n_go >= 2 else ("KILL" if kill else "MAYBE")
    n_inst = sum(1 for k in res if 'B_STAR' in res[k])
    if dec == "GO" and n_inst < 90:                                     # pre-registered grid is 90 instances
        dec = f"MAYBE (capped: reduced grid, {n_inst} of 90 instances)"
    out["decision_D3_O3S"] = dec
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / ("d3s_headroom.json" if SUFFIX == "O3S" else f"d3s_headroom_{SUFFIX}.json")).write_text(json.dumps(out, indent=2))
    print("D3 (O3S) decision:", dec)
    for f in FAMILIES:
        s = out["families"][f]
        print(f, {k: (round(s[k]["mean"], 3), round(s[k]["lo"], 3), round(s[k]["hi"], 3), s[k]["n"])
                  for k in ("h", "o3s_vs_o1bstar", "scorer_tau")}, "switch", round(s["switch_share"], 2), s["switched_to"],
              {k: round(v) for k, v in s["p99_mean"].items() if np.isfinite(v)})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "analyze"])
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--long", action="store_true")
    ap.add_argument("--cand", default="full", choices=["full", "nosim", "local_sim", "keep_bottleneck", "hpa", "fifer", "kraken"])
    ap.add_argument("--horizon", type=float, default=None)
    ap.add_argument("--epoch", type=float, default=None, help="seconds between re-layouts (default 60 with --long)")
    ap.add_argument("--min-frac", type=float, default=None, help="busiest-first: skip unless this fraction of slots would change")
    ap.add_argument("--cap", type=int, default=None, help="busiest-first: change at most this many containers per re-layout")
    ap.add_argument("--min-backlog", type=float, default=None, help="busiest-first: skip unless queued runs >= this fraction of slots")
    ap.add_argument("--K", type=int, default=None)
    ap.add_argument("--families", default=None, help="e.g. F1,F2 (default: all three)")
    ap.add_argument("--future", choices=["exact", "rate"], default=None, help="rate = rate oracle: fresh Poisson draw of the true rates")
    ap.add_argument("--blind", action="store_true", help="no future knowledge: persistence forecast of arrivals (and rates)")
    ap.add_argument("--seeds", default=None, help="e.g. 1-3 (default: 1-3, or 1 with --long)")
    a = ap.parse_args()
    configure(a.long, a.seeds, a.blind, a.future, a.cand, a.horizon, a.K, a.epoch, a.min_frac, a.cap, a.min_backlog)
    run(a) if a.cmd == "run" else analyze(a)
