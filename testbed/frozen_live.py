"""The paper's controller (FROZEN-4 and its relatives) as one function, for the simulator and for the testbed (DESIGN.md, phase 4).

The experiments of the paper build the controller inline in every script (output/data-analysis/capw1_rows.py: `run_job`). The testbed needs the same
construction for `Sim` (the reference) and `LiveSim` (the real run), so it lives here once, with the same arguments in the same order. It is checked
against the paper's own results: on a stored scenario this builder gives the stored event hash (tests/test_frozen_live.py).

What the controller is, in the simulator's terms: `Sim` with an `O3SimAdjuster` around the B* annealer, `cand_mode="nosim"` (busiest-first re-layout every
`epoch` seconds, no clone check), the request mover every `move_period` seconds, a blind persistence forecast, the `transfer_only` dispatcher and the
criticality queue order. The configuration dictionaries are the single definition in output/data-analysis/frozen2.py.

On the testbed the controller's own compute is real wall time: while a re-layout or a move pass runs on the hub, the agents keep working and their events
wait in the inbox. That is part of what the testbed measures; `Sim.run()` reports it as adjust_ms_* / plan_ms_*, and LiveSim as late events and inbox depth.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
for _p in (str(ROOT), str(ROOT / "output" / "data-analysis")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from dfps import dispatchers as D                       # noqa: E402
from dfps.dispatch_priority import QueuePriority        # noqa: E402
from dfps.o3s import O3SimAdjuster                      # noqa: E402
from dfps.sim import Sim                                # noqa: E402
from dfps.variants import make_adjuster, sim_kwargs     # noqa: E402
import frozen2                                          # noqa: E402

ARMS = {"frozen4": frozen2.FROZEN4,                     # the paper's controller (PL-5 fill, MV-4 mover)
        "frozen4_mv3": frozen2.FROZEN4_MV3,             # the same decisions with the MV-3 mover (no numba needed)
        "frozen5": frozen2.FROZEN4,                     # FROZEN-4 + queue-aware binding of single-parent tasks at ready time (Sim late_bind; pre-registered 12 Nov 2026)
        "frozen4_p8": frozen2.FROZEN4_P8,               # PL-5p: 8 fill passes, the scale option
        "frozen3": frozen2.FROZEN3}                     # the controller of the results before 9 Nov 2026
MOVE_PERIOD_S = 4.0
EPOCH_S = 60.0
LAM = 0.5


def assumptions():
    import yaml
    return yaml.safe_load((ROOT / "config" / "assumptions.yaml").read_text(encoding="utf-8"))


def build(sc, X0, seed, *, arm="frozen4", warmup, duration, sim_cls=Sim, move_period=MOVE_PERIOD_S, epoch=EPOCH_S, **extra):
    """(sim, adjuster) for one run of the controller `arm` on scenario `sc` from initial layout `X0`.

    `sim_cls` is `Sim` for the reference or a `LiveSim` subclass; `extra` goes to its constructor (link=, drain_s=, exec_sampler=, record_requests=, ...).
    Arguments and seeds as in capw1_rows.run_job: adjuster seed+300 (annealer) and seed+800, simulator seed+400."""
    A = assumptions()
    kw = sim_kwargs("B_STAR", A)
    kw.update(warmup=warmup, duration=duration, retry_min_interval=1.0, retry_max_attempts=10)
    kw["dispatcher"] = D.DISPATCHERS[frozen2.FROZEN3_DISPATCHER]
    kw["queue_priority"] = QueuePriority("full", aging=2.0)
    adj = O3SimAdjuster(make_adjuster("B_STAR", A, seed=seed + 300), move_period, epoch=epoch, horizon=30.0, K=8, seed=seed + 800, warmup=warmup,
                        blind=True, cand_mode="nosim", churn=dict(ARMS[arm], lam=LAM))
    kw["interval"] = adj.next_interval
    if arm == "frozen5":
        kw["late_bind"] = True
    kw.update(extra)
    return sim_cls(sc, np.array(X0).copy(), adjuster=adj, seed=seed + 400, **kw), adj


def warm_up_kernels(sc, X0, seed=1, seconds=70.0, arm="frozen4"):
    """Run the controller once in the plain simulator, so the compiled mover kernel is loaded and every code path has been taken once BEFORE a live run.
    Without it the first re-layout or move pass of a live run would pay for loading and compiling on the wall clock, and that stall would count as testbed overhead."""
    t0 = time.time()
    sim, _ = build(sc, X0, seed, arm=arm, warmup=min(30.0, seconds / 3), duration=seconds)
    sim.run()
    return time.time() - t0
