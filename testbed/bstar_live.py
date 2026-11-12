"""B* (DFPS with the corrections E1-E4, replacement period T*) built once for the simulator and for the testbed.

B* is the paper's own algorithm as corrected in this project: every request is planned by the graph-pattern matcher (no dispatcher override, FIFO queues, no request
mover), and every T* seconds the simulated-annealing replacement changes containers. The configuration is that of the stored `B_STAR` runs (capw1_light.py): the arguments
of `variants.sim_kwargs("B_STAR")`, retry 1.0 s / 10 attempts, adjuster seed + 300, simulator seed + 400. The testbed pre-registration fixes T* = 4 s (the stored runs read the
period of each case from the D1 result; the pilot cases have none).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dfps.sim import Sim                                 # noqa: E402
from dfps.variants import make_adjuster, sim_kwargs     # noqa: E402

PERIOD_S = 4.0                                           # T* of the testbed pre-registration


def assumptions():
    import yaml
    return yaml.safe_load((ROOT / "config" / "assumptions.yaml").read_text(encoding="utf-8"))


def build(sc, X0, seed, *, warmup, duration, sim_cls=Sim, period=PERIOD_S, **extra):
    """(sim, adjuster) for one run of B* on scenario `sc` from initial layout `X0`. `sim_cls` is `Sim` or a `LiveSim`; `extra` goes to its constructor
    (link=, drain_s=, exec_sampler=, record_requests=, ...)."""
    A = assumptions()
    kw = sim_kwargs("B_STAR", A)
    kw.update(warmup=warmup, duration=duration, retry_min_interval=1.0, retry_max_attempts=10, interval=float(period))
    kw.update(extra)
    adj = make_adjuster("B_STAR", A, seed=seed + 300)
    return sim_cls(sc, np.array(X0).copy(), adjuster=adj, seed=seed + 400, **kw), adj


def warm_up(sc, X0, seed=1, seconds=40.0):
    """One short plain-simulator run, so that every code path (matcher, annealer) has been taken once BEFORE a live run."""
    t0 = time.time()
    sim, _ = build(sc, X0, seed, warmup=min(10.0, seconds / 3), duration=seconds)
    sim.run()
    return time.time() - t0
