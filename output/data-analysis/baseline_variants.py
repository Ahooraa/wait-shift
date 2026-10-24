"""Baseline diagnostic, part 2 (2026-10-18): which source-paper choices could make Heu and RL as slow as in the DFPS paper?

  python -I output/data-analysis/baseline_variants.py run [--workers 8]
  python -I output/data-analysis/baseline_variants.py analyze

Part 1 (baseline_keepwarm.py) showed that container keep-warm is a minor factor. Run length is also ruled out: B*'s cold starts act as
a clock (its replacement round every 4 s produces a nearly constant number of cold starts per second) and match the paper's DFPS
counts at our 300 s, so the paper's runs are not much longer than ours. Variants tested here, all on the calibrated Fig. 5 scenarios
(rates x0.25 / x1 / x2, Uniform and Pareto, seeds 1-2), each an assumption, none described in the DFPS paper:
  HEU_xu     Heu with Xu et al.'s own workload feature: every function is invoked N_l times per request, N_l uniform in 1..5
             (Xu Sec. 6.1), processing delay proportional to N_l (Eq. 1); and a new container per request, released after use (AB-H5)
  RL_random  the RL baseline with an untrained (random) policy: lower bound of RL quality, i.e. what a poorly trained RL would do
  RL_random0 random policy and containers released after use (DFPS p.11: RL removes idle instances aggressively)
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
RUNS = ROOT / "results" / "baseline_variants"
KW = ROOT / "results" / "baseline_keepwarm"
OUT = ROOT / "output" / "data-analysis" / "results"
PAPER = json.loads((OUT / "paper_fig5_digitized.json").read_text())
VARIANTS = ("HEU_xu", "RL_random", "RL_random0")
SCALES, KINDS, SEEDS = (0.25, 1.0, 2.0), ("uniform", "pareto"), (1, 2)


def job(args):
    tag, var, out = args
    if Path(out).exists():
        return out
    try:
        from experiments.run import ASSUME, load_rl_policy
        from dfps.heu import HeuPolicy
        from dfps.ondemand import OnDemandSim
        sc = pickle.load(open(CAL / f"{tag}.pkl", "rb"))
        seed = int(tag.rsplit("_s", 1)[1])
        kw = dict(seed=seed + 400, warmup=ASSUME["A21_warmup_s"])
        if var == "HEU_xu":
            rng = np.random.default_rng(seed + 9100)
            mult = {f: int(rng.integers(1, 6)) for f in range(len(sc.functions))}
            pol, kw = HeuPolicy(seed=seed + 500), dict(kw, keep_warm=0, exec_mult=mult)
        else:
            pol = load_rl_policy(str(ROOT / "results" / "rl_policy.pt"), seed + 600)
            pol.epsilon = lambda: 1.0                                  # every decision random among feasible nodes
            if var == "RL_random0":
                kw = dict(kw, keep_warm=0)
        t = time.time()
        sim = OnDemandSim(sc, pol, **kw)
        r = sim.run()
        sim.check_invariants()
        r["wall_s"] = time.time() - t
        Path(out).write_text(json.dumps(dict(tag=tag, var=var, kind=sc.meta["kind"], scale=sc.meta["scale"], result=r)))
    except Exception:
        import traceback
        Path(out).with_suffix(".err").write_text(traceback.format_exc())
        return out + " FAILED"
    return out


def run(a):
    RUNS.mkdir(parents=True, exist_ok=True)
    jobs = [(f"{k}_x{s}_n80_a15_s{sd}", v, str(RUNS / f"{k}_x{s}_n80_a15_s{sd}.{v}.json"))
            for k in KINDS for s in SCALES for sd in SEEDS for v in VARIANTS]
    with ProcessPoolExecutor(a.workers) as ex:
        for d in ex.map(job, jobs):
            print("done", d, flush=True)


def analyze(a):
    rows = {}
    for f in RUNS.glob("*.json"):
        d = json.loads(f.read_text())
        rows.setdefault((d["kind"], d["scale"], d["var"]), []).append(d["result"])
    for f in KW.glob("*.keepNone.json"):                               # the baselines as run in the reproduction
        d = json.loads(f.read_text())
        rows.setdefault((d["kind"], d["scale"], d["method"] + "_asrun"), []).append(d["result"])
    out = {}
    for kind in KINDS:
        for s in SCALES:
            i = PAPER["x_scale"].index(s)
            line = {"paper_Heu": PAPER[kind]["makespan"]["Heu"][i], "paper_RL": PAPER[kind]["makespan"]["RL"][i],
                    "paper_DFPS": PAPER[kind]["makespan"]["DFPS"][i]}
            for v in ("HEU_asrun", "HEU_xu", "RL_asrun", "RL_random", "RL_random0"):
                rs = rows.get((kind, s, v), [])
                if rs:
                    line[v] = dict(makespan=float(np.mean([r["avg_makespan"] for r in rs])), cold=float(np.mean([r["cold_starts"] for r in rs])))
            out[f"{kind}_x{s}"] = line
    (OUT / "baseline_variants.json").write_text(json.dumps(out, indent=1))
    for k, line in out.items():
        print(k, "| paper Heu", line["paper_Heu"], "RL", line["paper_RL"], "DFPS", line["paper_DFPS"])
        for v, x in line.items():
            if isinstance(x, dict):
                print(f"   {v:11s} makespan {x['makespan']:7.1f}  cold {x['cold']:7.0f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "analyze"])
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    run(a) if a.cmd == "run" else analyze(a)
