"""CLU, the ClusterLess-style baseline (dfps/clusterless.py; pre-registered in knowledge/synthesis/clusterless-baseline.md): Eqs. 4-7 by hand, escalation, invariants."""
from types import SimpleNamespace

import numpy as np
import pytest

from dfps.clusterless import ClusterLessPolicy, _Req
from dfps.model import Function, Scenario, Workflow
from dfps.ondemand import OnDemandSim
from tests.helpers import line_net


def chain(n=2, size=20.0):
    return Workflow.from_edges(0, n, [(i, i + 1) for i in range(n - 1)], list(range(n)), {(i, i + 1): size for i in range(n - 1)}, size)


def system(wf, X0, nn=5, ecc=4, exec_t=1.0, cold=2.0, policy=None, arrivals=((0.0, 0, 0),)):
    nf = max(wf.ft) + 1
    sc = Scenario([Function(i, exec_t, cold) for i in range(nf)], [wf], line_net(nn), np.full(nn, ecc), np.full(nn, 1e6), list(arrivals), dict(duration_s=100.0))
    return OnDemandSim(sc, policy or ClusterLessPolicy(), seed=0, warmup=0.0, duration=100.0, X0=np.asarray(X0), debug=True)


def req(wf, origin=0, t_arr=0.0):
    return SimpleNamespace(id=0, wf=wf, origin=origin, t_arr=t_arr, plan=[None] * wf.n)


def plan(sim, wf, deadline, origin=0, limit_t=0):
    r = req(wf, origin)
    return sim.policy._plan(sim, r, _Req(), list(range(wf.n)), 0.0, deadline, limit_t)


def X0_of(nn, nf, where):
    X = np.zeros((nn, nf), dtype=int)
    for f, k in where:
        X[k, f] += 1
    return X


def test_warm_plan_matches_equations_4_to_7():
    wf = chain(2, 20.0)
    sim = system(wf, X0_of(5, 2, [(0, 1), (1, 3)]))
    net = sim.net
    nodes, fin, modes, wfin = plan(sim, wf, deadline=1e9)
    f0 = net.stt(wf.input_size, 0, 1) + 1.0                          # S = transfer of the input, chi = Q + T with Q = 0 (idle container)
    f1 = f0 + net.stt(20.0, 1, 3) + 1.0                              # S = F_parent + theta, Eq. 6
    assert nodes == {0: 1, 1: 3} and fin[0] == pytest.approx(f0) and fin[1] == pytest.approx(f1) and wfin == pytest.approx(f1)
    assert modes == {0: 0, 1: 0}


def test_tight_deadline_moves_the_bottleneck_to_cold_scaling_when_it_improves():
    wf = chain(2, 400.0)                                              # a large state: moving it to the only warm container is slow
    X0 = X0_of(5, 2, [(0, 0), (1, 4)])
    sim = system(wf, X0, cold=2.0)
    net = sim.net
    assert net.stt(400.0, 0, 4) > 2.0                                 # transfer costs more than a cold start here
    loose = plan(sim, wf, deadline=1e9)
    assert loose[0] == {0: 0, 1: 4} and loose[2] == {0: 0, 1: 0}
    tight = plan(sim, wf, deadline=loose[3] - 1e-3)
    assert tight[0] == {0: 0, 1: 0} and tight[2][1] == 1               # f1 scaled cold next to its parent
    assert tight[1][1] == pytest.approx(tight[1][0] + 2.0 + 1.0) and tight[3] < loose[3]


def test_escalation_is_dropped_when_it_does_not_improve():
    wf = chain(2, 1.0)
    sim = system(wf, X0_of(5, 2, [(0, 0), (1, 0)]), cold=5.0)         # warm plan is already the best: a cold start only costs more
    loose = plan(sim, wf, deadline=1e9)
    tight = plan(sim, wf, deadline=0.0)
    assert tight[0] == loose[0] and tight[3] == pytest.approx(loose[3]) and tight[2] == {0: 0, 1: 0}


def test_function_without_a_container_scales_cold_next_to_the_origin():
    wf = chain(1, 20.0)
    sim = system(wf, np.zeros((5, 1), dtype=int))
    nodes, fin, modes, _ = plan(sim, wf, deadline=1e9, origin=2)
    assert nodes[0] == 2 and fin[0] == pytest.approx(sim.net.stt(wf.input_size, 2, 2) + 2.0 + 1.0)


def test_single_task_warm_plan_equals_brute_force():
    wf = chain(1, 30.0)
    rng = np.random.default_rng(5)
    for _ in range(30):
        X0 = (rng.random((5, 1)) < 0.5).astype(int)
        if not X0.any():
            X0[rng.integers(5), 0] = 1
        sim = system(wf, X0)
        origin = int(rng.integers(5))
        nodes, fin, _, _ = plan(sim, wf, deadline=1e9, origin=origin)
        best = min((sim.net.stt(wf.input_size, origin, k), k) for k in range(5) if X0[k, 0])
        assert nodes[0] == best[1] and fin[0] == pytest.approx(best[0] + 1.0)


def test_plan_spreads_tasks_over_nodes_through_the_backlog():
    wf = Workflow.from_edges(0, 3, [(0, 1), (0, 2)], [0, 1, 1], {(0, 1): 1.0, (0, 2): 1.0}, 1.0)
    sim = system(wf, X0_of(2, 2, [(0, 0), (1, 0), (0, 1), (1, 1)]), nn=2, ecc=2)       # one idle f1 container on each node
    nodes, fin, _, _ = plan(sim, wf, deadline=1e9)
    assert nodes[1] != nodes[2]                                                           # the second f1 task sees the first one's container taken and goes to the other node
    only = system(wf, X0_of(2, 2, [(0, 0), (0, 1), (0, 1)]), nn=2, ecc=3)                # both f1 containers on node 0: warm candidates = node 0 only
    n2, f2, _, _ = plan(only, wf, deadline=1e9)
    assert n2[1] == n2[2] == 0


@pytest.mark.parametrize("refine", [True, False])
def test_whole_simulation_completes_and_keeps_the_invariants(refine):
    wf = chain(3, 15.0)
    arr = tuple((i * 0.7, 0, i % 5) for i in range(40))
    sim = system(wf, np.zeros((5, 3), dtype=int), ecc=3, policy=ClusterLessPolicy(refine=refine), arrivals=arr)
    res = sim.run()
    sim.check_invariants()
    assert res["n_completed"] == 40 and res["n_waiting_at_end"] == 0
    s = sim.policy.stats()
    assert s["requests"] == 40 and s["plans"] == 40
    assert (s["replans"] > 0) == refine


def test_same_seed_same_event_hash():
    wf = chain(3, 15.0)
    arr = tuple((i * 0.7, 0, i % 5) for i in range(30))
    h = []
    for _ in range(2):
        sim = system(wf, np.zeros((5, 3), dtype=int), ecc=3, arrivals=arr)
        sim.run()
        h.append(sim.results()["event_hash"])
    assert h[0] == h[1]
