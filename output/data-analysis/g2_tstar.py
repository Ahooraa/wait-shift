"""Task 10 (last step): tune B*'s replacement period T* per trace family on dev data (plan: T* from {1, 2, 4, 8, 16, 32, 64} s).

  python -I output/data-analysis/g2_tstar.py run     [--workers 10]
  python -I output/data-analysis/g2_tstar.py analyze

Design (fixed before running; reduced from the headroom grid to fit the Task 10 timebox, logged):
  * families F1 (Azure 2019), F2 (Huawei Public 2023, per-minute), F3 (synthetic popularity shifts every 10 min); dev span
  * rho = 0.7 (the middle load level), 3 dev instances per family (seeds 1-3), 15-min windows (900 s) after 60 s warm-up
  * workflow mix: 6 SeBS-Flow apps + DFPS Fig. 1 + 8 Alibaba DAGs; DFPS Table-2 infrastructure, 80 nodes
  * B* = DFPS with E1-E4 corrected (variants.py), initial placement NSGA-II (|.|), same seeds for every period
  * selection: T* = the period with the lowest mean P99 makespan over the 3 instances (primary metric of D1/D3);
    ties within 2% go to the longer period (fewer reconfigurations). Mean makespan and SLO-goodput are reported too.
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

from experiments.run import ASSUME, initial_placements  # noqa: E402
from dfps.sim import Sim  # noqa: E402
from dfps.traces import bottleneck_utilisation, build_trace_scenario, load_counts  # noqa: E402
from dfps.variants import PERIODS, make_adjuster, sim_kwargs  # noqa: E402

RUNS = ROOT / "results" / "g2_tstar"
OUT = ROOT / "output" / "data-analysis" / "results"
FAMILIES = ("F1", "F2", "F3")
SEEDS = (1, 2, 3)
RHO, DURATION, WARMUP = 0.7, 900.0, 60.0


def job(args):
    try:
        return _job(args)
    except Exception:
        import traceback
        Path(args[1]).with_suffix(".err").write_text(traceback.format_exc())
        return args[1] + " FAILED"


def _job(args):
    sc_path, out_path, seed, period = args
    if Path(out_path).exists():
        return out_path
    sc, X, bott = pickle.load(open(sc_path, "rb"))
    kw = sim_kwargs("B_STAR", ASSUME)
    kw["warmup"] = WARMUP
    t = time.time()
    sim = Sim(sc, X, adjuster=make_adjuster("B_STAR", ASSUME, seed=seed + 300), interval=float(period), seed=seed + 400,
              duration=DURATION, retry_min_interval=1.0, retry_max_attempts=10, **kw)
    r = sim.run()
    sim.check_invariants()
    r["wall_s"] = time.time() - t
    Path(out_path).write_text(json.dumps(dict(family=sc.meta["family"], seed=seed, period=period, rho=RHO,
                                              meta={k: v for k, v in sc.meta.items() if k not in ("per_app_rate",)},
                                              bottleneck_initial=bott, result=r)))
    return out_path


def run(a):
    RUNS.mkdir(parents=True, exist_ok=True)
    dags = None
    jobs = []
    for fam in FAMILIES:
        counts = None if fam == "F3" else load_counts(fam, "dev")
        for seed in SEEDS:
            sc_path = RUNS / f"{fam}_s{seed}.pkl"
            if not sc_path.exists():
                if dags is None:
                    dags = json.load(open(ROOT / "data" / "alibaba_dags_lt60s.json"))
                sc = build_trace_scenario(fam, RHO, seed, "dev", DURATION, 60.0, ne=80, n_workflows=15, alibaba_dags=dags,
                                          pool_size=ASSUME["A17_function_pool_size"], counts=counts)
                _, X, _ = initial_placements(sc, seed, ASSUME["A06_generations"], "abs")
                pickle.dump((sc, X, bottleneck_utilisation(sc, X)), open(sc_path, "wb"))
                print("built", sc_path.name, {k: sc.meta[k] for k in ("offered_util_mean", "offered_util_median", "n_arrivals")},
                      flush=True)
            for p in PERIODS:
                jobs.append((str(sc_path), str(RUNS / f"{fam}_s{seed}_T{p}.json"), seed, p))
    del dags
    with ProcessPoolExecutor(a.workers) as ex:
        for done in ex.map(job, jobs):
            print("done", done, flush=True)


def analyze(a):
    rows = {}
    for f in RUNS.glob("*.json"):
        d = json.loads(f.read_text())
        rows.setdefault((d["family"], d["period"]), []).append(d)
    out = {"design": dict(rho=RHO, duration_s=DURATION, warmup_s=WARMUP, seeds=SEEDS, periods=PERIODS), "families": {}}
    for fam in FAMILIES:
        tab = {}
        for p in PERIODS:
            rs = rows.get((fam, p), [])
            if not rs:
                continue
            tab[p] = dict(n=len(rs), p99=float(np.mean([d["result"]["p99_makespan"] for d in rs])),
                          mean=float(np.mean([d["result"]["avg_makespan"] for d in rs])),
                          goodput=float(np.mean([d["result"]["slo_goodput"] for d in rs])),
                          reconfigs=float(np.mean([d["result"]["n_adjust"] for d in rs])),
                          cold_starts=float(np.mean([d["result"]["cold_starts"] for d in rs])),
                          unfinished_max=int(max(d["result"]["n_unfinished"] for d in rs)),
                          bottleneck_max=float(np.mean([d["bottleneck_initial"]["max"] for d in rs])),
                          offered_util_median=float(np.mean([d["meta"]["offered_util_median"] for d in rs])))
        if not tab:
            continue
        best = min(tab[p]["p99"] for p in tab)
        cands = [p for p in tab if tab[p]["p99"] <= best * 1.02]
        out["families"][fam] = dict(table=tab, T_star=max(cands), complete=all(tab[p]["n"] == len(SEEDS) for p in tab)
                                    and len(tab) == len(PERIODS))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "g2_tstar.json").write_text(json.dumps(out, indent=2))
    for fam, v in out["families"].items():
        print(fam, "T* =", v["T_star"], "complete" if v["complete"] else "INCOMPLETE")
        for p, r in sorted(v["table"].items(), key=lambda x: float(x[0])):
            print(f"   T={p:>2}s  P99 {r['p99']:7.1f}  mean {r['mean']:6.1f}  goodput {r['goodput']:5.2f}/s  reconfigs {r['reconfigs']:5.0f}"
                  f"  cold {r['cold_starts']:6.0f}  unfinished {r['unfinished_max']}  bottleneck {r['bottleneck_max']:.2f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "analyze"])
    ap.add_argument("--workers", type=int, default=10)
    a = ap.parse_args()
    run(a) if a.cmd == "run" else analyze(a)
