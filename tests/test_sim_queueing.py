"""The simulator's queueing must reproduce M/M/c theory (validates Sim, independent of the paper's equations)."""
import numpy as np
import pytest

from dfps.model import Function, Scenario, Workflow
from dfps.network import Network
from dfps.queueing import fst
from dfps.sim import Sim


def one_node_system(c, exec_time, lam, horizon, seed=0, n_tasks=1):
    net = Network(1, [])
    wf = Workflow.from_edges(0, 1, [], [0], {}, 0.0)
    rng = np.random.default_rng(seed)
    t, arr = rng.exponential(1 / lam), []
    while t < horizon:
        arr.append((float(t), 0, 0))
        t += rng.exponential(1 / lam)
    sc = Scenario([Function(0, exec_time, 5.0)], [wf], net, np.array([c]), np.array([1e12]), arr,
                  dict(duration_s=horizon))
    return Sim(sc, np.array([[c]]), seed=seed + 1, warmup=100.0, duration=horizon, k_best=1, n_trees=1)


@pytest.mark.slow
@pytest.mark.parametrize("c,lam", [(1, 0.5), (2, 1.5), (3, 2.0)])
def test_single_function_matches_erlang_c(c, lam):
    """Mean over 4 independent seeds must match the Erlang-C mean time in system within 3 standard errors
    (a single seed at rho = 0.75 has a ~3% standard error, so single-seed 3% checks are flaky)."""
    res = []
    for seed in range(4):
        r = one_node_system(c, 1.0, lam, horizon=30_000.0, seed=10 * c + seed).run()
        assert r["n_unfinished"] == 0
        res.append((r["avg_makespan"], r["utilization"]))
    m = np.array([x[0] for x in res])
    u = np.array([x[1] for x in res])
    sem = m.std(ddof=1) / np.sqrt(len(m))
    assert abs(m.mean() - fst(lam, 1.0, c, "prose")) < 3 * sem + 0.01
    assert u.mean() == pytest.approx(lam / c, rel=0.03)
