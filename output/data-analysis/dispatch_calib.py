"""Load calibration for the dispatch evaluation (2026-10-28): the diamond and grid archetypes ran at stretch 2.24 / 2.75 at
rho 0.7; the evaluation is restricted to loaded scenarios (baseline mean stretch >= 3). Baseline (FIFO "ours") at several rho,
seed 1; also a smoke run of the capped priority rule and the prio_aet diagnostic on the data-heavy archetype.

  python output/data-analysis/dispatch_calib.py <workers>"""
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))
RES = HERE / "results" / "dispatch_calib"
JOBS = [(a, r, None) for a in ("diamond", "grid") for r in (0.8, 0.85, 0.9)] + [("heavy", 0.7, "full2"), ("heavy", 0.7, "full2_aet")]
if "diamond2" in sys.argv:                                   # second step: the diamond does not reach stretch 3 at rho 0.9
    JOBS = [("diamond", r, None) for r in (0.93, 0.95)]


def job(args):
    arch, rho, prio = args
    out = RES / f"{arch}_r{rho}_{prio or 'base'}.json"
    if out.exists():
        return args, json.loads(out.read_text())
    import d3s_headroom as d
    import faaspr_fig11_f3 as m
    import dag_suite
    from dfps.dispatch_priority import QueuePriority
    from dfps.o3s import O3SimAdjuster
    from dfps.sim import Sim
    from dfps.variants import make_adjuster, sim_kwargs
    from frozen2 import FROZEN2
    t0, seed = time.time(), 1
    sc, X0 = dag_suite.build(arch, seed, rho=rho)
    kw = sim_kwargs("B_STAR", m.ASSUME)
    kw.update(warmup=d.WARMUP, duration=900.0, retry_min_interval=1.0, retry_max_attempts=10, trace=True)
    churn = dict(FROZEN2, lam=0.5)
    if prio:
        kw["queue_priority"] = QueuePriority("full", aging=2.0)
        churn["prio_aet"] = prio.endswith("_aet")
    adj = O3SimAdjuster(make_adjuster("B_STAR", m.ASSUME, seed=seed + 300), m.MOVE_PERIOD_F3, epoch=60.0, horizon=120.0, K=5,
                        seed=seed + 800, warmup=d.WARMUP, blind=True, cand_mode="nosim", churn=churn, sizing_cache={})
    kw["interval"] = adj.next_interval
    sim = Sim(sc, X0.copy(), adjuster=adj, seed=seed + 400, **kw)
    res = sim.run()
    sim.check_invariants()
    cp = {w.id: float(sim.crit_path[w.id]) for w in sc.workflows}
    rq = [(r[2], r[3] - r[2], cp[r[1]]) for r in sim.trace["reqs"] if r[2] >= 120.0]
    soj = np.array([x[1] for x in rq])
    st = np.array([x[1] / x[2] for x in rq])
    late = np.array([x[1] / x[2] for x in rq if x[0] >= 720.0])
    early = np.array([x[1] / x[2] for x in rq if x[0] < 300.0])
    qp = kw.get("queue_priority")
    d_ = dict(arch=arch, rho=rho, prio=prio, p99=float(np.percentile(soj, 99)), stretch=float(st.mean()),
              stretch_early=float(early.mean()), stretch_settled=float(late.mean()), n=len(rq), offered=sc.meta["offered_util_mean"],
              n_moved=res["n_moved"], tiers=None if qp is None else qp.tier_counts, wall_s=time.time() - t0)
    RES.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(d_))
    return args, d_


if __name__ == "__main__":
    with ProcessPoolExecutor(int(sys.argv[1])) as ex:
        for a, d_ in ex.map(job, JOBS):
            print(f"{a[0]:8s} rho {a[1]} {a[2] or 'base':10s} stretch {d_['stretch']:.2f} (early {d_['stretch_early']:.2f}, settled "
                  f"{d_['stretch_settled']:.2f})  P99 {d_['p99']:.1f}  n {d_['n']}  tiers {d_['tiers']}  {d_['wall_s']:.0f}s", flush=True)
