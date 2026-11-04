"""Heu and RL with the SAME starting layout as ours/B* (user question, 2026-11-01): Heu and RL start with every slot
empty (DFPS p.9-11, "do not rely on an initial placement") and pay a burst of cold starts bootstrapping their own
layout from nothing. Ours and B* start from the NSGA-II layout instead. That is a real difference in the comparison,
not just a method difference, and it is a candidate explanation for Heu/RL's very high cold-start counts on slide 2.

This reruns Heu and RL on the SAME 18 development cases as the abstract chart (F1/F2 x rho 0.5/0.7/0.85 x seeds 1-3),
giving both baselines the same warm NSGA-II start (P["X0"] from results/d1_headroom/*.prep.pkl -- the exact array B*
and ours start from). Everything else (scenario, seed offsets, policy, duration, warmup, metrics) is identical to the
existing cold-start runs in results/d1_baselines/*.{HEU,RL}.json, so the two sets are a controlled before/after.
Output goes to a SEPARATE directory (results/d1_baselines_warmstart/) -- the original cold-start files are untouched,
since other analyses (headroom vs best existing, held-out comparisons) read them and should not silently change.

  python output/data-analysis/baselines_warmstart.py run [--workers N]
  python output/data-analysis/baselines_warmstart.py analyze
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

D1 = ROOT / "results" / "d1_headroom"
COLD = ROOT / "results" / "d1_baselines"
RUNS = ROOT / "results" / "d1_baselines_warmstart"
OUT = ROOT / "output" / "data-analysis" / "results"
FAMS, RHOS, SEEDS = ("F1", "F2"), (0.5, 0.7, 0.85), (1, 2, 3)
DURATION, WARMUP = 900.0, 60.0   # identical to d1_vs_baselines.py


def tag(f, r, s):
    return f"{f}_r{r}_s{s}"


def job(args):
    tg, m, seed, out = args
    if Path(out).exists():
        return out
    try:
        from experiments.run import load_rl_policy
        from dfps.heu import HeuPolicy
        from dfps.ondemand import OnDemandSim
        sc = pickle.load(open(D1 / f"{tg}.pkl", "rb"))
        P = pickle.load(open(D1 / f"{tg}.prep.pkl", "rb"))
        if m == "HEU":
            pol = HeuPolicy(seed=seed + 500)
        else:
            pol = load_rl_policy(str(ROOT / "results" / "rl_policy.pt"), seed + 600)
        t = time.time()
        sim = OnDemandSim(sc, pol, seed=seed + 400, duration=DURATION, warmup=WARMUP, X0=P["X0"])
        r = sim.run()
        sim.check_invariants()
        r["wall_s"] = time.time() - t
        Path(out).write_text(json.dumps(dict(family=sc.meta["family"], rho=sc.meta["rho"], seed=seed, ctrl=m, result=r)))
    except Exception:
        import traceback
        Path(out).with_suffix(".err").write_text(traceback.format_exc())
        return out + " FAILED"
    return out


def jobs():
    out = []
    for f in FAMS:
        for r in RHOS:
            for s in SEEDS:
                tg = tag(f, r, s)
                for m in ("HEU", "RL"):
                    out.append((tg, m, s, str(RUNS / f"{tg}.{m}.json")))
    return out


def run(workers):
    RUNS.mkdir(parents=True, exist_ok=True)
    js = jobs()
    print(f"{len(js)} jobs, {workers} workers", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        for done in ex.map(job, js):
            print("done", done, flush=True)


def _load(dirn, ctrl):
    out = {}
    for f in dirn.glob("*.json"):
        try:
            x = json.loads(f.read_text())
        except Exception:
            continue
        if x.get("ctrl") == ctrl and x.get("family") in FAMS and x.get("seed") in SEEDS:
            out[(x["family"], x["rho"], x["seed"])] = x["result"]
    return out


def analyze():
    cases = [(f, r, s) for f in FAMS for r in RHOS for s in SEEDS]
    out = {}
    for m in ("HEU", "RL"):
        cold = _load(COLD, m)
        warm = _load(RUNS, m)
        have = [k for k in cases if k in cold and k in warm]
        print(f"\n=== {m}: {len(have)}/{len(cases)} cases with both cold-start and warm-start results ===")
        rows = []
        for k in have:
            c, w = cold[k]["p99_makespan"], warm[k]["p99_makespan"]
            cc, wc = cold[k]["cold_starts"], warm[k]["cold_starts"]
            rows.append(dict(case=f"{k[0]} r{k[1]} s{k[2]}", p99_cold=c, p99_warm=w, p99_pct_change=(w - c) / c,
                             cold_starts_cold=cc, cold_starts_warm=wc,
                             cold_starts_pct_change=(wc - cc) / cc if cc else float("nan")))
            print(f"  {rows[-1]['case']:14s} P99 {c:8.1f} -> {w:8.1f} ({rows[-1]['p99_pct_change']*100:+5.1f}%)   "
                 f"cold starts {cc:7d} -> {wc:7d} ({rows[-1]['cold_starts_pct_change']*100:+6.1f}%)")
        out[m] = rows
    (OUT / "baselines_warmstart.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "analyze"])
    ap.add_argument("--workers", type=int, default=10)
    a = ap.parse_args()
    run(a.workers) if a.cmd == "run" else analyze()
