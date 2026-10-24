"""Baseline diagnostic (2026-10-18): why are our Heu and RL so much stronger than in the DFPS paper (Figs. 5-7)?

  python -I output/data-analysis/baseline_keepwarm.py run [--workers 8]
  python -I output/data-analysis/baseline_keepwarm.py analyze

Hypothesis: our on-demand container model keeps an idle container warm until its slot is needed, so later requests reuse it without
a cold start. The DFPS paper says Heu and RL decide "individually for each incoming request" with "frequent replacement" and many
cold starts (35-58 thousand in Figs. 5-7), and that RL removes idle instances aggressively; BASELINES_SPEC AB-H5 proposed "new
instance per request, released after use" for Heu, AB-R4 an idle timeout for RL. Test: rerun Heu and RL on the calibrated Fig. 5
scenarios (results/fig567_cal, rates x0.25 / x1 / x2, Uniform and Pareto, seeds 1-2) with keep_warm = forever (as run), 0 (release
after each task), 10 s and 60 s idle timeout, and compare makespan and cold starts with the paper's Fig. 5 (digitized).
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

CAL = ROOT / "results" / "fig567_cal"
RUNS = ROOT / "results" / "baseline_keepwarm"
OUT = ROOT / "output" / "data-analysis" / "results"
PAPER = json.loads((OUT / "paper_fig5_digitized.json").read_text())
KEEP = (None, 0, 10, 60)
SCALES, KINDS, SEEDS = (0.25, 1.0, 2.0), ("uniform", "pareto"), (1, 2)


def job(args):
    tag, method, keep, out = args
    if Path(out).exists():
        return out
    try:
        from experiments.run import ASSUME, load_rl_policy
        from dfps.heu import HeuPolicy
        from dfps.ondemand import OnDemandSim
        sc = pickle.load(open(CAL / f"{tag}.pkl", "rb"))
        seed = int(tag.rsplit("_s", 1)[1])
        pol = HeuPolicy(seed=seed + 500) if method == "HEU" else load_rl_policy(str(ROOT / "results" / "rl_policy.pt"), seed + 600)
        t = time.time()
        sim = OnDemandSim(sc, pol, seed=seed + 400, warmup=ASSUME["A21_warmup_s"], keep_warm=keep)
        r = sim.run()
        sim.check_invariants()
        r["wall_s"], r["n_expired"], r["n_recycled"] = time.time() - t, sim.n_expired, sim.n_recycled
        r["n_tasks_in_window"] = int(sum(w.n for _, wid, _ in sc.arrivals for w in [sc.workflows[wid]]))
        Path(out).write_text(json.dumps(dict(tag=tag, method=method, keep=keep, kind=sc.meta["kind"], scale=sc.meta["scale"], result=r)))
    except Exception:
        import traceback
        Path(out).with_suffix(".err").write_text(traceback.format_exc())
        return out + " FAILED"
    return out


def run(a):
    RUNS.mkdir(parents=True, exist_ok=True)
    jobs = []
    for kind in KINDS:
        for s in SCALES:
            for seed in SEEDS:
                tag = f"{kind}_x{s}_n80_a15_s{seed}"
                for m in ("HEU", "RL"):
                    for k in KEEP:
                        jobs.append((tag, m, k, str(RUNS / f"{tag}.{m}.keep{k}.json")))
    with ProcessPoolExecutor(a.workers) as ex:
        for d in ex.map(job, jobs):
            print("done", d, flush=True)


def analyze(a):
    rows = {}
    for f in RUNS.glob("*.json"):
        d = json.loads(f.read_text())
        rows.setdefault((d["kind"], d["scale"], d["method"], d["keep"]), []).append(d["result"])
    out = {}
    pm = {"HEU": "Heu", "RL": "RL"}
    for kind in KINDS:
        for m in ("HEU", "RL"):
            for s in SCALES:
                i = PAPER["x_scale"].index(s)
                line = {"paper": dict(makespan=PAPER[kind]["makespan"][pm[m]][i], cold=PAPER[kind]["cold"][pm[m]][i],
                                      util=PAPER[kind]["util"][pm[m]][i])}
                for k in KEEP:
                    rs = rows.get((kind, s, m, k), [])
                    if rs:
                        line[f"keep={k}"] = dict(makespan=float(np.mean([r["avg_makespan"] for r in rs])),
                                                 cold=float(np.mean([r["cold_starts"] for r in rs])),
                                                 util=float(np.mean([r["utilization"] for r in rs]) * 100),
                                                 tasks=float(np.mean([r["n_tasks_in_window"] for r in rs])), n=len(rs))
                out[f"{kind}_{m}_x{s}"] = line
    (OUT / "baseline_keepwarm.json").write_text(json.dumps(out, indent=1))
    for key, line in out.items():
        print(key)
        for k, v in line.items():
            print(f"   {k:10s} makespan {v['makespan']:7.1f}  cold {v['cold']:8.0f}  util {v['util']:5.1f}" + (f"  tasks {v['tasks']:.0f}" if "tasks" in v else ""))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "analyze"])
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    run(a) if a.cmd == "run" else analyze(a)
