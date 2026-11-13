"""Graph-Aware and FaaSPR as independent systems, built once for the simulator and for the testbed (DESIGN.md, phase 4b).

Both are exactly the arms of the held-out CAP-W1 comparison (output/data-analysis/capw1_independent.py, `run_job`; protocol and audit in
knowledge/synthesis/independent-baselines-capw1.md), with the same arguments and seeds; nothing is tuned and nothing of ours is in them: no request mover, FIFO queues, no
queue-aware binding.
  `ga`      Graph-Aware (Liang et al. 2026), arm `ga_p2`: substrate S-P = stock HPA sizing every 60 s (`ceil(load / 0.8)`) + our data-affinity placement (`qaware`,
            no queue term), the Graph-Aware dispatcher on every task with alpha = 1, beta = 1.1 and the v2 tie-break (lowest queue estimate, then random).
  `faaspr`  FaaSPR (Jia et al. 2025), arm `faaspr`: stock HPA sizing every 60 s, weighted horizontal/vertical-grouping placement (`faaspr_w`), per-workflow multi-stage LP
            router with the exact x-index threshold, 1,500 sampled paths per workflow (the sufficiency check's decision), 30 s rate window.
Both start from the layout `X0` the other systems start from.

On the testbed the compute of both is real wall time on the hub: the LP solve of FaaSPR (inside a routing call, when its refresh is due) and the dispatcher's scoring.
`health(sim)` returns the counters the protocol prints under every FaaSPR result (LP slack share, repaired and unplannable requests, solve time).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dfps import dispatchers as D                       # noqa: E402
from dfps.o3s import O3SimAdjuster                      # noqa: E402
from dfps.sim import Sim                                # noqa: E402
from dfps.variants import make_adjuster, sim_kwargs     # noqa: E402

N_PATHS = 1500                                           # the sufficiency check's decision (protocol section 5)
RATE_WINDOW_S = 30.0                                     # the held-out run's value
SCALING_S = 60.0
ARMS = ("ga", "faaspr")


def assumptions():
    import yaml
    return yaml.safe_load((ROOT / "config" / "assumptions.yaml").read_text(encoding="utf-8"))


def build(sc, X0, seed, *, arm, warmup, duration, sim_cls=Sim, n_paths=N_PATHS, **extra):
    """(sim, adjuster) for one run of `arm` ("ga" or "faaspr") on scenario `sc` from initial layout `X0`. `sim_cls` is `Sim` or a `LiveSim`; `extra` goes to its
    constructor (link=, drain_s=, exec_sampler=, record_requests=, ...). Seeds as in capw1_independent.run_job: annealer seed+300 (unused: blind, no annealing step), adjuster seed+800,
    simulator seed+400, FaaSPR's path sampling seed+900."""
    if arm not in ARMS:
        raise ValueError(f"unknown arm {arm!r}; known: {ARMS}")
    A = assumptions()
    kw = sim_kwargs("B_STAR", A)
    kw.update(warmup=warmup, duration=duration, retry_min_interval=1.0, retry_max_attempts=10)
    if arm == "faaspr":
        from dfps.controllers import FAASPR_W_DIAG
        for k in list(FAASPR_W_DIAG):                    # per-run counters (a process runs several builds in a test session or a queue)
            FAASPR_W_DIAG[k] = 0
        kw["dispatcher"] = D.FaaSPRRouterPaper(seed=seed + 900, n_paths=n_paths, window=RATE_WINDOW_S)
        churn = dict(no_inner=True, placement="faaspr_w")
    else:
        kw["dispatcher"] = D.GraphAware(tie="fst")
        churn = dict(no_inner=True, placement="qaware", origin_weight=1.0, tau=1.0, queue_term=False)
    adj = O3SimAdjuster(make_adjuster("B_STAR", A, seed=seed + 300), SCALING_S, epoch=SCALING_S, horizon=30.0, K=8, seed=seed + 800, warmup=warmup,
                        blind=True, cand_mode="hpa", churn=churn)
    kw["interval"] = adj.next_interval
    kw.update(extra)
    return sim_cls(sc, np.array(X0).copy(), adjuster=adj, seed=seed + 400, **kw), adj


def health(sim):
    """The in-run counters printed under every result of the independent systems (empty for Graph-Aware, which has none)."""
    r = sim.dispatcher
    if not hasattr(r, "n_solves"):
        return {}
    from dfps.controllers import FAASPR_W_DIAG
    return dict(n_solves=r.n_solves, n_wf_solves=r.n_wf_solves, n_slack=r.n_slack, n_wf_slack=r.n_wf_slack,
                slack_share_mean=float(np.mean(r.slack_share)) if r.slack_share else 0.0,
                solve_ms_mean=float(np.mean(r.solve_ms)) if r.solve_ms else None, solve_ms_max=float(np.max(r.solve_ms)) if r.solve_ms else None,
                n_pure=r.n_pure, n_repaired_req=r.n_repaired_req, n_repaired_tasks=r.n_repaired_tasks, n_unplanned=r.n_unplanned,
                repaired_req_share=r.n_repaired_req / max(1, r.n_pure + r.n_repaired_req), n_paths=r.n_paths, placement_diag=dict(FAASPR_W_DIAG))


def warm_up(sc, X0, arm, seed=1, seconds=70.0):
    """One short plain-simulator run, so the LP solver and every code path have been used once BEFORE a live run (a first solve on the wall clock would count as testbed
    overhead). The 60 s scaling interval needs more than 60 s to be reached once."""
    t0 = time.time()
    sim, _ = build(sc, X0, seed, arm=arm, warmup=min(10.0, seconds / 3), duration=seconds)
    sim.run()
    return time.time() - t0
