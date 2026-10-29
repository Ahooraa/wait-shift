"""Diagnose fp_both's storage-interaction bug (2026-10-26): the smoke test found 47.5% of requests unplanned under
FaaSPR placement + FaaSPR routing together, vs 0.3% for routing alone and 0 parked for placement alone. Hypothesis:
FaaSPR's placement (data-locality grouping, migration-minimizing) consolidates each function onto fewer nodes than
our own placement does; the router's per-task repair step then has fewer candidate nodes to fall back to, and those
few nodes run out of free input-state storage room under load -- a genuine interaction the paper's own evaluation
never has to face (their routing LP is computed FROM their own placement, which we have not re-derived; we are
composing two independently-ported mechanisms that happen not to be mutually consistent at our scenario's scale).

Uses FaaSPRRouter.on_unplanned (dfps/dispatchers.py, 2026-10-26) to log, on each n_unplanned event, how many nodes
host the stuck task's function and how much free storage those nodes have left vs. the task's own requirement --
confirming or refuting the hypothesis with real numbers instead of guessing.

  python -I output/data-analysis/faaspr_both_diag.py
"""
import os
import sys
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


def main(fam="F1", rho=0.7, k=1, seed=1, duration=140.0, log_n=12):
    p3.RHO = rho
    sc, X0 = p3.build(fam, k, seed)
    kw = sim_kwargs("B_STAR", ASSUME)
    kw.update(warmup=d.WARMUP, duration=duration, retry_min_interval=1.0, retry_max_attempts=10)
    router = FaaSPRRouter(seed=seed + 900, n_paths=int(os.environ.get("FP_PATHS", 300)))
    kw["dispatcher"] = router
    adj = O3SimAdjuster(make_adjuster("B_STAR", ASSUME, seed=seed + 300), MOVE_PERIOD_S[fam], epoch=60.0, horizon=120.0, K=5,
                         seed=seed + 800, warmup=d.WARMUP, blind=True, cand_mode="nosim", churn=dict(FROZEN2, placement="faaspr"))
    kw["interval"] = adj.next_interval
    sim = Sim(sc, X0, adjuster=adj, seed=seed + 400, **kw)

    logged = [0]

    def on_unplanned(sim, r, t, f):
        if logged[0] >= log_n:
            return
        free = sim.esc - sim.storage_used
        need = r.wf.input_total(t) - 1e-9
        hosts = np.flatnonzero(sim.cnt[f] > 0)
        slack = [float(free[h_] - need) for h_ in hosts]
        print(f"  UNPLANNED t={sim.now:7.1f} f={f} n_hosts={hosts.size} need={need:.3f} "
              f"free_on_hosts={['%.3f' % x for x in slack]}", flush=True)
        logged[0] += 1

    router.on_unplanned = on_unplanned

    print(f"running fp_both diag on {fam} rho={rho} k={k} seed={seed} duration={duration}", flush=True)
    res = sim.run()
    print(f"\ndone: p99={res['p99_makespan']:.1f} completed={res['n_completed']}/{res['n_arrived']} "
          f"unplanned={router.n_unplanned} repaired_req={router.n_repaired_req} pure={router.n_pure}", flush=True)
    n_hosts = (sim.cnt > 0).sum(axis=1)
    n_total = sim.cnt.sum(axis=1)
    print(f"nodes-per-function histogram under fp_both placement (final): {sorted(n_hosts.tolist())}", flush=True)
    single_host = np.flatnonzero(n_hosts == 1)
    print(f"single-host functions: f -> total instances = {[(int(f), int(n_total[f])) for f in single_host]}", flush=True)


if __name__ == "__main__":
    main()
