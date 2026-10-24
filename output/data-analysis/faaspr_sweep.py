"""FaaSPR (Jia et al., IEEE/ACM ToN 2025) ported into our controller, one mechanism at a time (2026-10-24).

Variants (all on the FROZEN-2 controller unless stated; 18 development cases; reference = nl_fz2_60):
  fp_place   placement replaced by FaaSPR's grouping + migration-minimizing placement; our sizing, DFPS dispatcher, our request moves
  fp_route   dispatcher replaced by FaaSPR's multi-stage LP routing (recomputed at every re-layout); our sizing and placement and moves
  fp_both    both replaced, our request moves kept (run only after the two single-mechanism variants)
  fp_pub     PUBLISHED-CONFIGURATION REFERENCE, not a controlled baseline: it changes three things at once (HPA-style sizing, FaaSPR
             placement and routing, no request moves), so a win or loss cannot be attributed. Report it apart from the single-mechanism rows.
Files <case>.O3S_h120_blind_nosim_nl_<variant>.json
  python faaspr_sweep.py smoke | run <variant,...> [workers] | analyze
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
import d3s_headroom as d  # noqa: E402
from frozen2 import FROZEN2, MOVE_PERIOD_S  # noqa: E402

import yaml  # noqa: E402

from dfps.dispatchers import FaaSPRRouter  # noqa: E402
from dfps.o3s import O3SimAdjuster  # noqa: E402
from dfps.sim import Sim  # noqa: E402
from dfps.variants import make_adjuster, sim_kwargs  # noqa: E402

ASSUME = yaml.safe_load((ROOT / "config" / "assumptions.yaml").read_text(encoding="utf-8"))
M = "p99_makespan"
CASES = [(f, r, s) for f in ("F1", "F2") for r in d.RHOS for s in (1, 2, 3)]
VARIANTS = {   # name -> (sizing cand mode, churn changes, FaaSPR routing?)
    "fp_place": ("nosim", dict(placement="faaspr"), False),
    "fp_route": ("nosim", {}, True),
    "fp_both": ("nosim", dict(placement="faaspr"), True),
    "fp_pub": ("hpa", dict(placement="faaspr", rebal=False), True),
}


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
        router = FaaSPRRouter(seed=seed + 900) if routing else None
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
            r["router"] = dict(solves=router.n_solves, fallback=router.n_fallback, slack_solves=router.n_slack,
                               theta=router.theta_used, solve_ms_mean=float(np.mean(router.solve_ms)) if router.solve_ms else 0.0)
        out.write_text(json.dumps(dict(variant=v, case=list(c), family=c[0], rho=c[1], seed=c[2], result=r)))
        return str(out)
    except Exception:
        import traceback
        out.with_suffix(".err").write_text(traceback.format_exc())
        return str(out) + " FAILED"


def tstar():
    T = json.loads((d.OUT / "g2_tstar.json").read_text())
    return {f: float(T["families"][f]["T_star"]) for f in ("F1", "F2")}


def smoke():
    sp = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(".")
    T = tstar()
    c = ("F1", 0.7, 1)
    for v in VARIANTS:
        t = time.time()
        o = sp / f"smoke_{v}.json"
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
    jobs = [(v, c, T[c[0]]) for v in names for c in sorted(CASES, key=lambda c: -c[1]) if not path(v, c).exists()]
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
    ref = load("nl_fz2_60")
    p = lambda b: f"{b['mean'] * 100:+6.1f}% ({b['lo'] * 100:+.0f} to {b['hi'] * 100:+.0f})"  # noqa: E731
    print("FaaSPR mechanisms in our controller, 18 development cases; positive = FROZEN-2 better (P99 lower)\n")
    print("%-9s %3s | %-26s | %5s | %-24s | %8s %8s %8s" % ("variant", "n", "FROZEN-2 better by", "wins", "gain over best existing", "cold=adds", "mv/req", "parked"))
    for v in VARIANTS:
        x = load(f"nl_{v}")
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
    else:
        analyze()
