"""FaaSPR (Jia et al., IEEE/ACM ToN 2025) ported into our controller, one mechanism at a time (2026-10-24).

Variants (all on the FROZEN-2 controller unless stated; 18 development cases; reference = nl_fz2_60):
  fp_place   placement replaced by FaaSPR's grouping + migration-minimizing placement; our sizing, DFPS dispatcher, our request moves
  fp_route   dispatcher replaced by FaaSPR's multi-stage LP routing (recomputed at every re-layout); our sizing and placement and moves
  fp_both    both replaced, our request moves kept (run only after the two single-mechanism variants)
  fp_pub     PUBLISHED-CONFIGURATION REFERENCE, not a controlled baseline: it changes three things at once (HPA-style sizing, FaaSPR
             placement and routing, no request moves), so a win or loss cannot be attributed. Report it apart from the single-mechanism rows.
Files <case>.O3S_h120_blind_nosim_nl_<variant>.json
  python faaspr_sweep.py smoke | run <variant,...> [workers] | analyze

Load x state-size grid (2026-10-26): the dev-grid CASES above use a fixed k (whatever the D1 headroom scenarios were built
at). GRID_CASES rebuilds scenarios at rho in d.RHOS x k in {1,5,10} (matching the lambda/P3 probes) x seed=1, for "ours",
fp_place and fp_route (fp_both/fp_pub deferred until the single-mechanism grid looks sane). 2 fam x 3 rho x 3 k x 3
variants = 54 runs. Files results/faaspr_grid/<fam>_r<rho>_k<k>_s<seed>.faaspr_grid_<variant>.json
  python faaspr_sweep.py grid_run [variant,...] [workers] | grid_analyze
"""
import json
import os
import pickle
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(ROOT))
import d3s_headroom as d  # noqa: E402
from frozen2 import FROZEN2, MOVE_PERIOD_S  # noqa: E402

import yaml  # noqa: E402

import p3_scaling_probe as p3  # noqa: E402

from dfps.dispatchers import FaaSPRRouter  # noqa: E402
from dfps.o3s import O3SimAdjuster  # noqa: E402
from dfps.sim import Sim  # noqa: E402
from dfps.variants import make_adjuster, sim_kwargs  # noqa: E402

ASSUME = yaml.safe_load((ROOT / "config" / "assumptions.yaml").read_text(encoding="utf-8"))
M = "p99_makespan"
CASES = [(f, r, s) for f in ("F1", "F2") for r in d.RHOS for s in (1, 2, 3)]

# Load x state-size grid (2026-10-26): the dev-grid CASES above use the fixed-k D1 pickles (whatever k the D1 headroom
# scenarios were built at), so they say nothing about whether a FaaSPR result holds across load or state size. This grid
# rebuilds scenarios directly (p3_scaling_probe.build, generalised over rho by setting p3.RHO before calling it) at
# rho x k combinations the rest of the project already uses (d.RHOS; k=1,5,10 as in the lambda/P3 probes), so results are
# comparable to the envelope/P3/lambda grids. "ours" (plain nosim, no FaaSPR) is rebuilt fresh in the same grid rather than
# reused from a different script's reference files, so the comparison never crosses a scenario-construction boundary.
#
# fp_both added 2026-10-26 (18 more cells): originally deferred because FaaSPR placement + FaaSPR routing together deadlocked
# on a storage-interaction bug (FaaSPRRouter's repair step had no fallback host once a consolidated function's single host
# saturated -- faaspr_both_diag.py confirmed it empirically, n_unplanned 2410/2252). Fixed with a minimum-replication floor in
# dfps/controllers.py::faaspr_placement (adaptation #5 in its docstring); the grid now includes it as a genuine "whole ported
# design" comparison point alongside the two single-mechanism rows.
GRID_KS = (1, 5, 10)
GRID_SEEDS = (1,)
GRID_CASES = [(f, r, k, s) for f in ("F1", "F2") for r in d.RHOS for k in GRID_KS for s in GRID_SEEDS]
GRID_VARIANTS = {"ours": ("nosim", dict(lam=0.5), False), "fp_place": ("nosim", dict(placement="faaspr", lam=0.5), False),
                  "fp_route": ("nosim", dict(lam=0.5), True), "fp_both": ("nosim", dict(placement="faaspr", lam=0.5), True)}
# lam=0.5 (2026-10-26, user decision) on every row that keeps our request moves: fp_place/fp_route/fp_both swap one FaaSPR component
# into our controller and keep our moves, so lam is our parameter there too; leaving them at 1.0 made each row differ from "ours" in
# two components. The dev-grid VARIANTS below are left at lam=1.0 on purpose: their reference (nl_fz2_60) is also lam=1.0.
GRID_RUNS = ROOT / "results" / "faaspr_grid"
VARIANTS = {   # name -> (sizing cand mode, churn changes, FaaSPR routing?)
    "fp_place": ("nosim", dict(placement="faaspr"), False),
    "fp_route": ("nosim", {}, True),
    "fp_both": ("nosim", dict(placement="faaspr"), True),
    "fp_pub": ("hpa", dict(placement="faaspr", rebal=False), True),
    # Can routing replace request moves? Both without our request moves; fp_route_nm is compared with ours_nm (same controller, DFPS dispatcher).
    "ours_nm": ("nosim", dict(rebal=False), False),
    "fp_route_nm": ("nosim", dict(rebal=False), True),
}
REFERENCE = {"fp_route_nm": "ours_nm"}                  # variant -> the run it is compared with (default: nl_fz2_60)


def path(v, c):
    return d.RUNS / f"{d.tag(*c)}.O3S_h120_blind_nosim_nl_{v}.json"


def one(args, duration=None, out=None):
    v, c, tstar = args
    out = path(v, c) if out is None else out
    if out.exists():
        return str(out)
    try:
        assert np.__version__.startswith("1."), "run with the Anaconda interpreter (numpy 1.26)"
        cand, extra, routing = VARIANTS[v]
        tg, seed = d.tag(*c), c[2]
        sc = pickle.load(open(d.D1 / f"{tg}.pkl", "rb"))
        P = pickle.load(open(d.D1 / f"{tg}.prep.pkl", "rb"))
        kw = sim_kwargs("B_STAR", ASSUME)
        kw.update(warmup=d.WARMUP, duration=d.DURATION if duration is None else duration, retry_min_interval=1.0, retry_max_attempts=10)
        router = FaaSPRRouter(seed=seed + 900, n_paths=int(os.environ.get("FP_PATHS", 300))) if routing else None
        if router is not None:
            kw["dispatcher"] = router
        adj = O3SimAdjuster(make_adjuster("B_STAR", ASSUME, seed=seed + 300), MOVE_PERIOD_S[c[0]], epoch=60.0, horizon=120.0, K=5,
                            seed=seed + 800, warmup=d.WARMUP, blind=True, cand_mode=cand, churn=dict(FROZEN2, **extra))
        kw["interval"] = adj.next_interval
        t = time.time()
        sim = Sim(sc, P["X0"], adjuster=adj, seed=seed + 400, **kw)
        r = sim.run()
        sim.check_invariants()
        r["wall_s"] = time.time() - t
        if router is not None:
            r["router"] = dict(solves=router.n_solves, pure=router.n_pure, repaired_req=router.n_repaired_req, repaired_tasks=router.n_repaired_tasks, unplanned=router.n_unplanned, slack_solves=router.n_slack,
                               theta=router.theta_used, slack_frac=router.slack_frac, solve_ms_mean=float(np.mean(router.solve_ms)) if router.solve_ms else 0.0)
        out.write_text(json.dumps(dict(variant=v, case=list(c), family=c[0], rho=c[1], seed=c[2], result=r)))
        return str(out)
    except Exception:
        import traceback
        out.with_suffix(".err").write_text(traceback.format_exc())
        return str(out) + " FAILED"


def tstar():
    T = json.loads((d.OUT / "g2_tstar.json").read_text())
    return {f: float(T["families"][f]["T_star"]) for f in ("F1", "F2")}


def grid_path(v, c):
    fam, rho, k, seed = c
    return GRID_RUNS / f"{fam}_r{rho}_k{k}_s{seed}.faaspr_grid_{v}.json"


def grid_one(args, duration=None, out=None):
    v, c = args
    fam, rho, k, seed = c
    out = grid_path(v, c) if out is None else out
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        return str(out)
    try:
        assert np.__version__.startswith("1."), "run with the Anaconda interpreter (numpy 1.26)"
        cand, extra, routing = GRID_VARIANTS[v]
        p3.RHO = rho                                          # p3_scaling_probe.build reads this module global
        sc, X0 = p3.build(fam, k, seed)
        kw = sim_kwargs("B_STAR", ASSUME)
        kw.update(warmup=d.WARMUP, duration=d.DURATION if duration is None else duration, retry_min_interval=1.0, retry_max_attempts=10)
        router = FaaSPRRouter(seed=seed + 900, n_paths=int(os.environ.get("FP_PATHS", 300))) if routing else None
        if router is not None:
            kw["dispatcher"] = router
        adj = O3SimAdjuster(make_adjuster("B_STAR", ASSUME, seed=seed + 300), MOVE_PERIOD_S[fam], epoch=60.0, horizon=120.0, K=5,
                            seed=seed + 800, warmup=d.WARMUP, blind=True, cand_mode=cand, churn=dict(FROZEN2, **extra))
        kw["interval"] = adj.next_interval
        t = time.time()
        sim = Sim(sc, X0, adjuster=adj, seed=seed + 400, **kw)
        r = sim.run()
        sim.check_invariants()
        r["wall_s"] = time.time() - t
        if router is not None:
            r["router"] = dict(solves=router.n_solves, pure=router.n_pure, repaired_req=router.n_repaired_req, repaired_tasks=router.n_repaired_tasks, unplanned=router.n_unplanned, slack_solves=router.n_slack,
                               theta=router.theta_used, slack_frac=router.slack_frac, solve_ms_mean=float(np.mean(router.solve_ms)) if router.solve_ms else 0.0)
        out.write_text(json.dumps(dict(variant=v, family=fam, rho=rho, k=k, seed=seed, result=r)))
        return str(out)
    except Exception:
        import traceback
        out.with_suffix(".err").write_text(traceback.format_exc())
        return str(out) + " FAILED"


def grid_run(names, workers):
    GRID_RUNS.mkdir(parents=True, exist_ok=True)
    only = os.environ.get("FP_ONLY")
    jobs = [(v, c) for v in names for c in sorted(GRID_CASES, key=lambda c: -c[1]) if not grid_path(v, c).exists()
            and (only is None or f"{c[0]}_r{c[1]}_k{c[2]}_s{c[3]}" == only)]
    print(f"{len(jobs)} runs", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        for done in ex.map(grid_one, jobs):
            print("done", done, flush=True)


def grid_analyze():
    """Reports FaaSPR's OWN three evaluation metrics (jia-2025-faaspr.md, 'Evaluation: six workflows...': average
    latency, P99, resource consumption), not just our P99 headline, so a win/loss claim can be stated on their terms."""
    print("FaaSPR mechanisms across load x state size (rho x k), single seed")
    print("positive %% = ours better (lower); metrics: P99 latency, average latency, resource consumption (mean containers) -- FaaSPR's own three\n")
    data = {}
    for v in GRID_VARIANTS:
        for c in GRID_CASES:
            f = grid_path(v, c)
            if f.exists():
                data[(v, c)] = json.loads(f.read_text())["result"]

    def row(fam, rho, k, seed, v):
        c = (fam, rho, k, seed)
        r = data.get((v, c))
        return r

    print("%-3s %5s %3s %-9s | %8s %8s %8s | %7s %7s %7s" % (
        "fam", "rho", "k", "variant", "P99", "avg_lat", "containers", "dP99", "davg", "dres"))
    for fam in ("F1", "F2"):
        for rho in d.RHOS:
            for k in GRID_KS:
                for seed in GRID_SEEDS:
                    ours = row(fam, rho, k, seed, "ours")
                    if ours is None:
                        continue
                    print("%-3s %5s %3d %-9s | %8.1f %8.1f %10.2f |" % (
                        fam, rho, k, "ours", ours[M], ours["avg_makespan"], ours["mean_containers"]))
                    for v in ("fp_place", "fp_route", "fp_both"):
                        r = row(fam, rho, k, seed, v)
                        if r is None:
                            continue
                        dP99 = 100 * (r[M] - ours[M]) / r[M]
                        davg = 100 * (r["avg_makespan"] - ours["avg_makespan"]) / r["avg_makespan"]
                        dres = 100 * (r["mean_containers"] - ours["mean_containers"]) / r["mean_containers"]
                        print("%-3s %5s %3d %-9s | %8.1f %8.1f %10.2f | %+6.1f%% %+6.1f%% %+6.1f%%" % (
                            fam, rho, k, v, r[M], r["avg_makespan"], r["mean_containers"], dP99, davg, dres))


def smoke():
    sp = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(".")
    T = tstar()
    c = ("F1", 0.7, 1)
    for v in (sys.argv[3].split(",") if len(sys.argv) > 3 else VARIANTS):
        t = time.time()
        o = sp / f"smoke_{v}_{os.environ.get('FP_PATHS', 60)}.json"
        res = one((v, c, T[c[0]]), duration=140.0, out=o)
        if res.endswith("FAILED"):
            print(v, "FAILED", o.with_suffix(".err").read_text()[-1500:], flush=True)
            continue
        x = json.loads(o.read_text())["result"]
        print("%-9s P99 %7.1f | completed %d of %d | moves/request %.2f | cold %d | parked %d | router %s | %.0f s" % (
            v, x["p99_makespan"], x["n_completed"], x["n_arrived"], x["n_moved"] / max(1, x["n_completed"]), x["cold_starts"], x["n_parked"],
            x.get("router"), time.time() - t), flush=True)


def run(names, workers):
    T = tstar()
    only = os.environ.get("FP_ONLY")                      # e.g. F1_r0.7_s1: run a single case
    jobs = [(v, c, T[c[0]]) for v in names for c in sorted(CASES, key=lambda c: -c[1]) if not path(v, c).exists()
            and (only is None or d.tag(*c) == only)]
    print(f"{len(jobs)} runs", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        for done in ex.map(one, jobs):
            print("done", done, flush=True)


def analyze():
    from d1_rlla import BASE, D1, boot
    base = {}
    for d_ in (D1, BASE):
        for f in d_.glob("*.json"):
            x = json.loads(f.read_text())
            if x.get("ctrl") in ("B_STAR", "RL", "RL_CAL"):
                base.setdefault((x["family"], x["rho"], x["seed"]), {})[x["ctrl"]] = x["result"][M]

    def load(s):
        o = {}
        for f in d.RUNS.glob(f"*.O3S_h120_blind_nosim_{s}.json"):
            x = json.loads(f.read_text())
            if x["seed"] <= 3:
                o[(x["family"], x["rho"], x["seed"])] = x["result"]
        return o
    ref0 = load("nl_fz2_60")
    p = lambda b: f"{b['mean'] * 100:+6.1f}% ({b['lo'] * 100:+.0f} to {b['hi'] * 100:+.0f})"  # noqa: E731
    print("FaaSPR mechanisms in our controller, 18 development cases; positive = FROZEN-2 better (P99 lower)\n")
    print("%-9s %3s | %-26s | %5s | %-24s | %8s %8s %8s" % ("variant", "n", "FROZEN-2 better by", "wins", "gain over best existing", "cold=adds", "mv/req", "parked"))
    for v in VARIANTS:
        x = load(f"nl_{v}")
        ref = load(f"nl_{REFERENCE[v]}") if v in REFERENCE else ref0
        if v == "ours_nm":
            ref = ref0                                    # shown against FROZEN-2 to see what the moves are worth
        ks = [k for k in ref if k in x]
        if not ks:
            continue
        g = [(x[k][M] - ref[k][M]) / x[k][M] for k in ks]
        be = [min(base[k].values()) for k in ks]
        v = v + (" (ref)" if v == "fp_pub" else "")
        print("%-9s %3d | %-26s | %2d/%2d | %+6.1f%% (ref %+6.1f%%)    | %8.0f %8.2f %8.1f" % (
            v, len(ks), p(boot(g)), sum(a > 0 for a in g), len(ks), 100 * np.mean([(b - x[k][M]) / b for b, k in zip(be, ks)]),
            100 * np.mean([(b - ref[k][M]) / b for b, k in zip(be, ks)]), np.mean([x[k]["cold_starts"] for k in ks]),
            np.mean([x[k]["n_moved"] / x[k]["n_completed"] for k in ks]), np.mean([x[k]["n_parked"] for k in ks])))


if __name__ == "__main__":
    a = sys.argv[1]
    if a == "smoke":
        smoke()
    elif a == "run":
        run(sys.argv[2].split(","), int(sys.argv[3]) if len(sys.argv) > 3 else 4)
    elif a == "grid_run":
        grid_run(sys.argv[2].split(",") if len(sys.argv) > 2 else list(GRID_VARIANTS), int(sys.argv[3]) if len(sys.argv) > 3 else 4)
    elif a == "grid_analyze":
        grid_analyze()
    else:
        analyze()
