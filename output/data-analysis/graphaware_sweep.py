"""Graph-Aware Scheduling (Liang et al., Future Internet 18:265, 2026) and the baselines of its own Sec. 5.1.4, ported as dispatcher
swap-ins inside our controller (2026-10-26). Only the dispatcher changes: sizing, placement, re-layout and request moves are "ours"
exactly as in the FaaSPR grid (FROZEN2, lam=0.5, nosim), so every row differs from "ours" in one component.

Variants (dfps/dispatchers.py):
  ours          DFPS graph pattern matching (reference; read from results/faaspr_grid/*.faaspr_grid_ours.json, same scenarios/seeds)
  rr            Round Robin over the nodes holding the function
  grf           Greedy Resource-Fit: smallest start-time estimate, ignores transfer
  heft          HEFT-like: upward-rank order, earliest finish time with max(data ready, node ready)
  ccag          Comm.-Cost-Aware Greedy == our greedy_eft (FST + transfer in seconds; no node prices)
  ga            Graph Scheduling, beta frozen by the tuning stage below
Moves-off arm (suffix _nm; user request 2026-10-26): the same dispatchers with our request moves switched off (FROZEN2 + rebal=False;
FROZEN2's no_inner=True keeps B*'s annealing off too, so nothing relocates queued requests -- the 2x2's "re-layout, no moves" cell).
Reference dfps_nm = DFPS matcher, no moves. Orphaned queues after a re-layout are still rerouted by the simulator, as in every
no-moves row. Two questions: (1) dispatcher quality on its own (moves off); (2) whether our moves make the dispatcher choice matter
less (compare the spread across dispatchers in the two arms). Uses the beta frozen by the moves-on tuning (not re-tuned without moves).
Not ported: the paper's "MLP-Based Scheduler" -- its weights are learned and unpublished, and with the paper's structural term dropped
(caveat 1 in GraphAware's docstring) the remaining flat-feature scorer is the ga row itself.

Beta selection, fixed before any tuning run: alpha = 1; beta in {0.25, 0.5, 1, 2, 4} on TUNE_CASES; for each case divide each beta's
P99 by the best P99 over the betas; choose the beta with the smallest mean ratio (ties: smaller beta). Chosen value written to
results/graphaware_grid/beta.json and used unchanged for the full grid. Same budget order as the lambda sweep (5 vs 6 values).
TUNE_CASES are 4 of the 18 reported cases; the grid is the development span throughout (no test-span data used).
Declared extension (user decision 2026-10-26, made after seeing only the first tuning case, where P99 fell monotonically up to beta=4):
if the rule above picks the top of the grid (beta=4), beta in {8, 16} is added on the same TUNE_CASES and the same rule is re-applied
over all seven values. No further extension: if 16 wins, it is frozen and reported as a boundary optimum. `select` does both steps and
records the first pick and whether the extension ran in beta.json.

  python graphaware_sweep.py tune [workers] | select [workers] | run [workers] | run_nm [workers] | analyze
  (`pick` prints the original-grid choice without writing anything)
"""
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(ROOT))
import d3s_headroom as d  # noqa: E402
import faaspr_sweep as fs  # noqa: E402
import p3_scaling_probe as p3  # noqa: E402
from frozen2 import FROZEN2, MOVE_PERIOD_S  # noqa: E402

from dfps import dispatchers as D  # noqa: E402
from dfps.o3s import O3SimAdjuster  # noqa: E402
from dfps.sim import Sim  # noqa: E402
from dfps.variants import make_adjuster, sim_kwargs  # noqa: E402

RUNS = ROOT / "results" / "graphaware_grid"
M = "p99_makespan"
CHURN = dict(FROZEN2, lam=0.5)                           # identical to "ours" in faaspr_sweep.GRID_VARIANTS
CHURN_NM = dict(CHURN, rebal=False)                      # moves off (no_inner stays True: no B* annealing either)
CASES = fs.GRID_CASES                                    # (fam, rho, k, seed): F1/F2 x rho in d.RHOS x k in {1,5,10} x seed 1
TUNE_CASES = [("F1", 0.85, 10, 1), ("F2", 0.85, 10, 1), ("F1", 0.7, 5, 1), ("F2", 0.7, 5, 1)]
BETAS = (0.25, 0.5, 1.0, 2.0, 4.0)
EXT_BETAS = (8.0, 16.0)
BASELINES = ("rr", "grf", "heft", "ccag")


def make_dispatcher(v):
    v = v[:-3] if v.endswith("_nm") else v
    if v == "dfps":
        return None                                      # DFPS graph pattern matching (the simulator's default)
    if v == "rr":
        return D.RoundRobin()
    if v == "grf":
        return D.resource_fit
    if v == "heft":
        return D.heft_like
    if v == "ccag":
        return D.greedy_eft
    if v.startswith("ga_b"):
        return D.GraphAware(alpha=1.0, beta=float(v[4:]))
    raise ValueError(v)


def path(v, c):
    if v == "ours":
        return fs.grid_path("ours", c)
    fam, rho, k, seed = c
    return RUNS / f"{fam}_r{rho}_k{k}_s{seed}.ga_{v}.json"


def one(args, duration=None):
    v, c = args
    fam, rho, k, seed = c
    out = path(v, c)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        return str(out)
    try:
        assert np.__version__.startswith("1."), "run with the Anaconda interpreter (numpy 1.26)"
        p3.RHO = rho
        sc, X0 = p3.build(fam, k, seed)
        kw = sim_kwargs("B_STAR", fs.ASSUME)
        kw.update(warmup=d.WARMUP, duration=d.DURATION if duration is None else duration, retry_min_interval=1.0, retry_max_attempts=10)
        kw["dispatcher"] = make_dispatcher(v)
        churn = CHURN_NM if v.endswith("_nm") else CHURN
        adj = O3SimAdjuster(make_adjuster("B_STAR", fs.ASSUME, seed=seed + 300), MOVE_PERIOD_S[fam], epoch=60.0, horizon=120.0, K=5,
                            seed=seed + 800, warmup=d.WARMUP, blind=True, cand_mode="nosim", churn=dict(churn))
        kw["interval"] = adj.next_interval
        t = time.time()
        sim = Sim(sc, X0, adjuster=adj, seed=seed + 400, **kw)
        res = sim.run()
        sim.check_invariants()
        res["wall_s"] = time.time() - t
        res["plan_ms_mean"] = float(np.mean(sim.plan_ms)) if sim.plan_ms else 0.0
        out.write_text(json.dumps(dict(variant=v, family=fam, rho=rho, k=k, seed=seed, churn_lam=churn["lam"],
                                       moves=bool(churn["rebal"]), result=res)))
        return str(out)
    except Exception:
        import traceback
        out.with_suffix(".err").write_text(traceback.format_exc())
        return str(out) + " FAILED"


def _launch(jobs, workers):
    jobs = [j for j in jobs if not path(*j).exists()]
    print(f"{len(jobs)} runs", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        for r in ex.map(one, jobs):
            print("done", r, flush=True)


def tune(workers):
    _launch([(f"ga_b{b}", c) for c in TUNE_CASES for b in BETAS], workers)


def pick(betas=BETAS):
    ratios = {b: [] for b in betas}
    for c in TUNE_CASES:
        vals = {b: json.loads(path(f"ga_b{b}", c).read_text())["result"][M] for b in betas}
        best = min(vals.values())
        print("%-3s r%-4s k%-2d | " % c[:3] + " | ".join("b=%s %7.1f" % (b, vals[b]) for b in betas), flush=True)
        for b in betas:
            ratios[b].append(vals[b] / best)
    mean = {b: float(np.mean(ratios[b])) for b in betas}
    chosen = min(betas, key=lambda b: (round(mean[b], 9), b))
    print("mean P99 / best-per-case:", {b: round(mean[b], 4) for b in betas}, "-> beta =", chosen, flush=True)
    return chosen, mean


def select(workers):
    first, mean = pick(BETAS)
    extended = first == max(BETAS)
    chosen = first
    if extended:
        print(f"top of the grid picked (beta={first}): running the declared extension {EXT_BETAS}", flush=True)
        _launch([(f"ga_b{b}", c) for c in TUNE_CASES for b in EXT_BETAS], workers)
        chosen, mean = pick(BETAS + EXT_BETAS)
        if chosen == max(EXT_BETAS):
            print(f"beta={chosen} is again the top of the (extended) grid: frozen as a boundary optimum, no further extension", flush=True)
    RUNS.mkdir(parents=True, exist_ok=True)
    (RUNS / "beta.json").write_text(json.dumps(dict(beta=chosen, first_pick=first, extended=extended,
                                                     boundary=chosen == max(BETAS + (EXT_BETAS if extended else ())),
                                                     mean_ratio={str(b): v for b, v in mean.items()}, tune_cases=TUNE_CASES)))
    return chosen


def chosen_beta():
    return json.loads((RUNS / "beta.json").read_text())["beta"]


def run(workers):
    b = chosen_beta()
    _launch([(v, c) for c in sorted(CASES, key=lambda c: -c[1]) for v in BASELINES + (f"ga_b{b}",)], workers)


def run_nm(workers):
    b = chosen_beta()
    _launch([(v + "_nm", c) for c in sorted(CASES, key=lambda c: -c[1]) for v in ("dfps",) + BASELINES + (f"ga_b{b}",)], workers)


def _load(names):
    data = {}
    for v in names:
        for c in CASES:
            f = path(v, c)
            if f.exists():
                data[(v, c)] = json.loads(f.read_text())["result"]
    return data


def _arm(title, names, data):
    ref = names[0]
    print(f"\n{title}  (relative P99 vs {ref}; + = {ref} better)")
    print("%-3s %5s %3s | " % ("fam", "rho", "k") + " | ".join("%16s" % v for v in names))
    rel = {v: [] for v in names}
    for c in CASES:
        o = data.get((ref, c))
        if o is None:
            continue
        cells = []
        for v in names:
            r = data.get((v, c))
            if r is None:
                cells.append("%16s" % "-")
            elif v == ref:
                cells.append("%16.1f" % r[M])
            else:
                cells.append("%8.1f (%+5.0f%%)" % (r[M], 100 * (r[M] - o[M]) / o[M]))
                rel[v].append((r[M] - o[M]) / o[M])
        print("%-3s %5s %3d | " % c[:3] + " | ".join(cells))
    for v in names[1:]:
        xs = rel[v]
        if xs:
            print(f"  {v:16s} mean {100 * np.mean(xs):+6.1f}%   {ref} better in {sum(x > 0 for x in xs)}/{len(xs)}")
    print("  mean over cases: avg_makespan / mean_containers / plan_ms")
    for v in names:
        rs = [data[(v, c)] for c in CASES if (v, c) in data]
        if rs:
            print(f"  {v:16s} avg={np.mean([r['avg_makespan'] for r in rs]):8.1f}  containers={np.mean([r['mean_containers'] for r in rs]):7.2f}"
                  f"  plan_ms={np.mean([r.get('plan_ms_mean', float('nan')) for r in rs]):6.2f}  n={len(rs)}")


def analyze():
    b = chosen_beta()
    on = ("ours",) + BASELINES + (f"ga_b{b}",)
    off = tuple(v + "_nm" for v in ("dfps",) + BASELINES + (f"ga_b{b}",))
    data = _load(on + off)
    print(f"Dispatcher swap-ins inside our controller (lam=0.5), single seed; GA beta={b} (frozen by `pick`)")
    _arm("MOVES ON", on, data)
    _arm("MOVES OFF", off, data)
    print("\nDoes moving queued requests make the dispatcher matter less? Per case: worst/best P99 across the 6 dispatchers, per arm")
    for c in CASES:
        a = [data[(v, c)][M] for v in on if (v, c) in data]
        z = [data[(v, c)][M] for v in off if (v, c) in data]
        if len(a) == len(on) and len(z) == len(off):
            print("  %-3s r%-4s k%-2d  moves on %5.2fx   moves off %5.2fx" % (c[0], c[1], c[2], max(a) / min(a), max(z) / min(z)))


if __name__ == "__main__":
    cmd = sys.argv[1]
    w = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    {"tune": lambda: tune(w), "pick": pick, "select": lambda: select(w), "run": lambda: run(w), "run_nm": lambda: run_nm(w),
     "analyze": analyze}[cmd]()
