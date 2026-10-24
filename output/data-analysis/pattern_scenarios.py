"""Does the controller work across workflow patterns? (2026-10-23)

The standard scenarios mix 7 named applications (6 SeBS-Flow + DFPS Fig. 1) with 8 Alibaba DAGs, so every result so far is an
average over chains, diamonds, joins and one wide multi-root workflow (about 6 tasks each) and says nothing about any one shape.
Here every workflow in a scenario has the SAME pattern, so a weakness tied to a shape cannot hide in the average.

Patterns (15 workflows per scenario, each its own DAG; functions are drawn from the usual pool of 30, state sizes and runtimes
as in every other scenario; arrivals scaled so the offered utilisation is rho for every pattern -- matched total load):
  chain3 / chain12     sequential chains of 3 and 12 tasks              (cold-start spillover grows with depth)
  diamond4 / diamond8  source -> 4 or 8 parallel tasks -> sink          (a join waits for the slowest branch)
  wide16               source -> 16 parallel tasks -> sink              (a burst of simultaneous demand for few functions)
  outtree7             binary out-tree, 7 tasks                         (fan-out only, no join)
  intree7              binary in-tree, 7 tasks                          (fan-in only, many roots)
  layered12            3 layers of 4 tasks, all-to-all between layers   (dense dependencies)
  real7                the 6 SeBS-Flow applications + DFPS Fig. 1, repeated to 15 (realistic structure, 3-19 tasks)
F1/F2 x rho 0.85 x seeds 1-2 = 4 scenarios per pattern, 36 in all (the 50% load cases were cut to halve the run time). Each is run under B* and under the frozen controller
(busiest-first sizing, incremental k-median placement, finish-time request moves with no cap, no B*).
Metric: P99 makespan, gain over B* on the same scenario; also cold starts and request moves.

  python output/data-analysis/pattern_scenarios.py run [workers]
  python output/data-analysis/pattern_scenarios.py analyze
"""
import json
import pickle
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(ROOT))

from experiments.run import ASSUME, initial_placements  # noqa: E402
from dfps.o3s import O3SimAdjuster  # noqa: E402
from dfps.sim import Sim  # noqa: E402
from dfps.variants import make_adjuster, sim_kwargs  # noqa: E402

RUNS = ROOT / "results" / "patterns"
OUT = ROOT / "output" / "data-analysis" / "results"
FAMS, RHOS, SEEDS = ("F1", "F2"), (0.85,), (1, 2)      # 85% load only (user decision 2026-10-23: where the mechanisms matter most)
DURATION, WARMUP = 900.0, 60.0
CTRL = {"no_inner": True, "rebal": True, "rebal_max": 10 ** 9, "placement": "kmedian", "improve": 0, "origin_weight": 1.0}
M = "p99_makespan"
N_WF = 15


def _dag(job, n, edges):
    return dict(job=job, n=n, edges=sorted(set(map(tuple, edges))), span=float("nan"), names=[f"t{i}" for i in range(n)])


def chain(n):
    return _dag(f"chain{n}", n, [(i, i + 1) for i in range(n - 1)])


def diamond(w):
    return _dag(f"diamond{w}", w + 2, [(0, 1 + i) for i in range(w)] + [(1 + i, w + 1) for i in range(w)])


def outtree(n=7):
    return _dag("outtree7", n, [((i - 1) // 2, i) for i in range(1, n)])


def intree(n=7):
    e = [((i - 1) // 2, i) for i in range(1, n)]                   # out-tree edges parent -> child, then reversed
    return _dag("intree7", n, [(n - 1 - c, n - 1 - p) for p, c in e])      # relabelled so tasks stay in topological order


def layered(width=4, layers=3):
    n = width * layers
    e = [(l * width + i, (l + 1) * width + j) for l in range(layers - 1) for i in range(width) for j in range(width)]
    return _dag("layered12", n, e)


def real7():
    from dfps.sebsflow import all_named_dags
    named = all_named_dags()
    return [dict(named[i % len(named)]) for i in range(N_WF)]


PATTERNS = {
    "chain3": lambda: [chain(3)] * N_WF, "chain12": lambda: [chain(12)] * N_WF,
    "diamond4": lambda: [diamond(4)] * N_WF, "diamond8": lambda: [diamond(8)] * N_WF,
    "wide16": lambda: [diamond(16)] * N_WF, "outtree7": lambda: [outtree()] * N_WF, "intree7": lambda: [intree()] * N_WF,
    "layered12": lambda: [layered()] * N_WF, "real7": real7,
}


def check_dags():
    """Every DAG is acyclic, in topological order (edges go forward) and connected."""
    for name, mk in PATTERNS.items():
        d = mk()
        assert len(d) == N_WF, name
        for g in d:
            assert all(a < b for a, b in g["edges"]), (name, "edge not forward")
            assert all(0 <= a < g["n"] and 0 <= b < g["n"] for a, b in g["edges"]), name
    return True


def build(pattern, fam, rho, seed):
    """Trace scenario with every workflow of the given pattern (build_trace_scenario with workflow_mix replaced)."""
    import dfps.traces as T
    real = T.workflow_mix
    T.workflow_mix = lambda seed_, n_workflows=15, alibaba_dags=None: PATTERNS[pattern]()
    try:
        sc = T.build_trace_scenario(fam, rho, seed, "dev", DURATION, 60.0, ne=80, n_workflows=N_WF, alibaba_dags=None,
                                    pool_size=ASSUME["A17_function_pool_size"], counts=T.load_counts(fam, "dev"))
    finally:
        T.workflow_mix = real
    sc.meta["pattern"] = pattern
    return sc


def job(args):
    pattern, fam, rho, seed, period = args
    tg = f"{pattern}_{fam}_r{rho}_s{seed}"
    out_path = RUNS / f"{tg}.json"
    if out_path.exists():
        return str(out_path)
    try:
        import numpy as _np
        assert _np.__version__.startswith("1."), "run with the Anaconda interpreter (numpy 1.26)"
        p = RUNS / f"{tg}.pkl"
        if p.exists():
            sc = pickle.load(open(p, "rb"))
        else:
            sc = build(pattern, fam, rho, seed)
            pickle.dump(sc, open(p, "wb"))
        _, X0, info = initial_placements(sc, seed, ASSUME["A06_generations"], "abs")
        res = dict(pattern=pattern, family=fam, rho=rho, seed=seed, mean_tasks=sc.meta["mean_tasks"], n_arrivals=sc.meta["n_arrivals"])
        kw = sim_kwargs("B_STAR", ASSUME)
        kw.update(warmup=WARMUP, duration=DURATION, retry_min_interval=1.0, retry_max_attempts=10)
        t = time.time()
        sim = Sim(sc, X0, adjuster=make_adjuster("B_STAR", ASSUME, seed=seed + 300), seed=seed + 400, interval=float(period), **kw)
        res["B_STAR"] = sim.run()
        sim.check_invariants()
        res["B_STAR"]["wall_s"] = time.time() - t
        adj = O3SimAdjuster(make_adjuster("B_STAR", ASSUME, seed=seed + 300), period, epoch=60.0, horizon=120.0, K=5,
                            seed=seed + 800, warmup=WARMUP, blind=True, cand_mode="nosim", churn=dict(CTRL))
        kw["interval"] = adj.next_interval
        t = time.time()
        sim = Sim(sc, X0, adjuster=adj, seed=seed + 400, **kw)
        res["OURS"] = sim.run()
        sim.check_invariants()
        res["OURS"]["wall_s"] = time.time() - t
        out_path.write_text(json.dumps(res))
        return str(out_path)
    except Exception:
        import traceback
        out_path.with_suffix(".err").write_text(traceback.format_exc())
        return str(out_path) + " FAILED"


def run(workers):
    check_dags()
    RUNS.mkdir(parents=True, exist_ok=True)
    T = json.loads((OUT / "g2_tstar.json").read_text())
    T = {f: float(T["families"][f]["T_star"]) for f in FAMS}
    jobs = [(pat, f, r, s, T[f]) for r in sorted(RHOS, reverse=True) for pat in PATTERNS for f in FAMS for s in SEEDS]
    with ProcessPoolExecutor(workers) as ex:
        for done in ex.map(job, jobs):
            print("done", done, flush=True)


def analyze():
    from d1_rlla import boot
    rows = {}
    for f in RUNS.glob("*.json"):
        d = json.loads(f.read_text())
        rows.setdefault(d["pattern"], []).append(d)
    p = lambda b: f"{b['mean'] * 100:+6.1f}% ({b['lo'] * 100:+.0f} to {b['hi'] * 100:+.0f})"  # noqa: E731
    out = {}
    print("%-10s %3s %6s | %9s %9s | %-24s | %5s | %7s %7s | %8s" % ("pattern", "n", "tasks", "B* P99", "ours P99", "gain over B*", "wins",
                                                                  "B* cold", "our cold", "moves/req"))
    for pat in PATTERNS:
        ds = rows.get(pat, [])
        if not ds:
            continue
        g = [(d["B_STAR"][M] - d["OURS"][M]) / d["B_STAR"][M] for d in ds]
        row = dict(n=len(ds), tasks=float(np.mean([d["mean_tasks"] for d in ds])), bstar=float(np.mean([d["B_STAR"][M] for d in ds])),
                   ours=float(np.mean([d["OURS"][M] for d in ds])), gain=boot(g), wins=int(sum(x > 0 for x in g)),
                   cold_b=float(np.mean([d["B_STAR"]["cold_starts"] for d in ds])), cold_o=float(np.mean([d["OURS"]["cold_starts"] for d in ds])),
                   moves_per_req=float(np.mean([d["OURS"]["n_moved"] / max(1, d["OURS"]["n_completed"]) for d in ds])))
        by_fam = {fam: [x for x, d in zip(g, ds) if d["family"] == fam] for fam in FAMS}
        row["gain_by_family"] = {k: (float(np.mean(v)) if v else float("nan")) for k, v in by_fam.items()}
        out[pat] = row
        print("%-10s %3d %6.1f | %9.1f %9.1f | %-24s | %2d/%2d | %7.0f %7.0f | %8.2f   (Azure %+.0f%%  Huawei %+.0f%%)" % (
            pat, row["n"], row["tasks"], row["bstar"], row["ours"], p(row["gain"]), row["wins"], row["n"], row["cold_b"], row["cold_o"],
            row["moves_per_req"], 100 * row["gain_by_family"].get("F1", float("nan")), 100 * row["gain_by_family"].get("F2", float("nan"))))
    (OUT / "pattern_scenarios.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 11)
    elif sys.argv[1] == "check":
        print("dags ok:", check_dags())
    else:
        analyze()
