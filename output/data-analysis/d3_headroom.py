"""Task 13 (pre-registered; design option 2 chosen by the user 2026-10-15): D3 headroom, coupled placement-dispatch.

  python -I output/data-analysis/d3_headroom.py run [--workers N]
  python -I output/data-analysis/d3_headroom.py analyze

Shares the D1 grid (results/d1_headroom: same 90 scenarios, seeds, initial placement X0, T*). B* = D1's B_STAR runs; the
affinity-greedy heuristic = D1's S_MEAN runs (static affinity-greedy placement from the window's mean rates). New here: O3, the
surrogate-scored oracle (dfps/d3.py), on all 90 instances; on seed 1 of every family x load (9 instances) it also measures Kendall
tau between surrogate and simulated rankings (8 random candidates every 10th period, own random stream: decisions unchanged).
Metric: P99 makespan. h = (B* - O3) / B*; heuristic saturation = (B* - AFF) / (B* - O3). Decision as in the plan, with the
tau >= 0.7 downgrade (GO -> MAYBE).
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
from dfps.d3 import O3SurrogateAdjuster  # noqa: E402
from dfps.sim import Sim  # noqa: E402
from dfps.variants import sim_kwargs  # noqa: E402

D1 = ROOT / "results" / "d1_headroom"
RUNS = ROOT / "results" / "d3_headroom"
OUT = ROOT / "output" / "data-analysis" / "results"
# Loaded directly (not via experiments.run, which imports PyTorch: PyTorch + numpy/MKL matrix products load two OpenMP
# runtimes in one process on this machine, OMP Error #15).
ASSUME = yaml.safe_load((ROOT / "config" / "assumptions.yaml").read_text(encoding="utf-8"))
FAMILIES, RHOS, SEEDS = ("F1", "F2", "F3"), (0.5, 0.7, 0.85), tuple(range(1, 11))
DURATION, WARMUP = 900.0, 60.0


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
    tg, out_path, seed, period, with_tau = args
    if Path(out_path).exists():
        return out_path
    sc = pickle.load(open(D1 / f"{tg}.pkl", "rb"))
    P = pickle.load(open(D1 / f"{tg}.prep.pkl", "rb"))
    kw = sim_kwargs("B_STAR", ASSUME)
    kw.update(warmup=WARMUP, duration=DURATION, retry_min_interval=1.0, retry_max_attempts=10, interval=float(period))
    adj = O3SurrogateAdjuster(sc, period, K=32, seed=seed + 700, tau_every=10 if with_tau else 0, tau_k=8)
    t = time.time()
    sim = Sim(sc, P["X0"], adjuster=adj, seed=seed + 400, **kw)
    r = sim.run()
    sim.check_invariants()
    r["wall_s"] = time.time() - t
    Path(out_path).write_text(json.dumps(dict(family=sc.meta["family"], rho=sc.meta["rho"], seed=seed, period=period, result=r,
                                              o3_switches=adj.n_switch, o3_periods=adj.n_periods, taus=adj.taus,
                                              tau_horizon=adj.tau_horizon)))
    return out_path


def run(a):
    T = json.loads((OUT / "g2_tstar.json").read_text())
    T = {f: float(T["families"][f]["T_star"]) for f in FAMILIES}
    RUNS.mkdir(parents=True, exist_ok=True)
    jobs = [(tag(f, r, s), str(RUNS / f"{tag(f, r, s)}.O3.json"), s, T[f], s == 1) for f in FAMILIES for r in RHOS for s in SEEDS]
    jobs.sort(key=lambda j: not j[4])                                 # tau instances first (longest)
    with ProcessPoolExecutor(a.workers) as ex:
        for d in ex.map(job, jobs):
            print("done", d, flush=True)


def boot_ci(x, n=10_000, seed=0):
    x = np.asarray([v for v in x if np.isfinite(v)], dtype=float)
    if len(x) < 2:
        return dict(mean=float(x.mean()) if len(x) else float("nan"), lo=float("nan"), hi=float("nan"), n=int(len(x)))
    m = np.random.default_rng(seed).choice(x, (n, len(x)), replace=True).mean(axis=1)
    return dict(mean=float(x.mean()), lo=float(np.percentile(m, 2.5)), hi=float(np.percentile(m, 97.5)), n=int(len(x)))


def analyze(a):
    metric = "p99_makespan"
    res = {}
    for f in RUNS.glob("*.O3.json"):
        d = json.loads(f.read_text())
        res.setdefault((d["family"], d["rho"], d["seed"]), {})["O3"] = d
    for f in D1.glob("*.json"):
        d = json.loads(f.read_text())
        if d["ctrl"] in ("B_STAR", "S_MEAN"):
            res.setdefault((d["family"], d["rho"], d["seed"]), {})[d["ctrl"]] = d
    out = dict(metric=metric, families={}, cells={})

    def summ(keys):
        h, sat, taus = [], [], []
        for k in keys:
            c = res.get(k, {})
            if not all(x in c for x in ("B_STAR", "O3")):
                continue
            b, o = c["B_STAR"]["result"][metric], c["O3"]["result"][metric]
            h.append((b - o) / b)
            if "S_MEAN" in c and b - o > 0:
                sat.append((b - c["S_MEAN"]["result"][metric]) / (b - o))
            taus += [t for t in c["O3"].get("taus", []) if np.isfinite(t)]
        return dict(h=boot_ci(h), heuristic_saturation=boot_ci(sat), tau=boot_ci(taus),
                    o3_switch_share=float(np.mean([res[k]["O3"]["o3_switches"] / max(1, res[k]["O3"]["o3_periods"])
                                                   for k in keys if "O3" in res.get(k, {})])) if keys else float("nan"))

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
    sats = [out["families"][f]["heuristic_saturation"]["mean"] for f in FAMILIES]
    if dec == "GO" and sum(1 for x in sats if np.isfinite(x) and x >= 0.70) >= 2:
        dec = "MAYBE (heuristic captures >= 70% of the headroom in >= 2 families)"
    taus_all = [out["families"][f]["tau"]["mean"] for f in FAMILIES if np.isfinite(out["families"][f]["tau"]["mean"])]
    tau_mean = float(np.mean(taus_all)) if taus_all else float("nan")
    if dec == "GO" and np.isfinite(tau_mean) and tau_mean >= 0.7:
        dec = "MAYBE (surrogate tau >= 0.7: the learned-encoder angle adds little)"
    out["decision_D3"], out["tau_mean"] = dec, tau_mean
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "d3_headroom.json").write_text(json.dumps(out, indent=2))
    print("D3 decision:", dec, "| tau mean", round(tau_mean, 3) if np.isfinite(tau_mean) else tau_mean)
    for f in FAMILIES:
        s = out["families"][f]
        print(f, {k: (round(s[k]["mean"], 3), round(s[k]["lo"], 3), round(s[k]["hi"], 3), s[k]["n"]) for k in ("h", "heuristic_saturation", "tau")},
              "switch share", round(s["o3_switch_share"], 3))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "analyze"])
    ap.add_argument("--workers", type=int, default=10)
    a = ap.parse_args()
    run(a) if a.cmd == "run" else analyze(a)
