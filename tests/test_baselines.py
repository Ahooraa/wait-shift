"""Heu and RL baselines: algorithm-level tests (hand-computed / brute-force) and whole-simulation invariants."""
import itertools

import numpy as np
import pytest
import torch

from dfps.heu import HeuPolicy
from dfps.model import Function, Scenario, Workflow
from dfps.ondemand import OnDemandSim
from dfps.rl import D, Buffer, MosecPolicy, QNet
from dfps.workload import build_scenario, synthetic_alibaba_like
from tests.helpers import line_net


def chain_wf(n=3, size=20.0):
    return Workflow.from_edges(0, n, [(i, i + 1) for i in range(n - 1)], [0] * n, {(i, i + 1): size for i in range(n - 1)}, size)


def scenario(wf, n_nodes=5, ecc=4, arrivals=((0.0, 0, 0),), cold=2.0, exec_t=1.0):
    return Scenario([Function(0, exec_t, cold), Function(1, exec_t, cold)], [wf], line_net(n_nodes), np.full(n_nodes, ecc),
                    np.full(n_nodes, 1e6), list(arrivals), dict(duration_s=100.0))


# ------------------------------------------------------------------------------------------------ Heu
def test_heu_components_are_longest_path_levels():
    wf = Workflow.from_edges(0, 5, [(0, 2), (1, 2), (2, 3), (0, 4)], [0] * 5, {e: 10.0 for e in [(0, 2), (1, 2), (2, 3), (0, 4)]}, 10.0)
    lvl, comps = HeuPolicy().levels(wf)
    assert lvl == [0, 0, 1, 2, 1] and comps == [[0, 1], [2, 4], [3]]


def test_heu_path_equals_brute_force_over_all_layered_paths():
    sc = scenario(chain_wf(4, 30.0), n_nodes=6)
    sim = OnDemandSim(sc, HeuPolicy(seed=1), seed=0)
    pol, wf = sim.policy, sc.workflows[0]
    w, _ = pol.weights(sim, wf)
    rng = np.random.default_rng(3)
    for trial in range(20):
        feas = rng.random((4, 6)) < 0.7
        feas[:, rng.integers(0, 6)] = True                               # at least one node per layer
        origin = int(rng.integers(0, 6))
        nodes, cost = pol._path(sim, origin, w, feas, w, jitter=False)
        best = min((sum(sim.net.h[a, b] * w[q] for q, (a, b) in enumerate(zip((origin,) + p[:-1], p))), p)
                   for p in itertools.product(range(6), repeat=4) if all(feas[q, p[q]] for q in range(4)))
        assert cost == pytest.approx(best[0]) and sum(sim.net.h[a, b] * w[q] for q, (a, b) in enumerate(zip((origin,) + tuple(nodes[:-1]), nodes))) == pytest.approx(best[0])


def test_heu_weights_use_states_of_previous_component():
    wf = Workflow.from_edges(0, 3, [(0, 1), (0, 2)], [0, 0, 0], {(0, 1): 10.0, (0, 2): 25.0}, 15.0)
    sim = OnDemandSim(scenario(wf), HeuPolicy(), seed=0)
    w, nd = sim.policy.weights(sim, wf)
    assert w == [15.0, 35.0] and nd == [3.0, 3.0]            # exec 1 + cold 2 per layer (conservative, Eq.18-19 text)


def test_heu_prunes_nodes_without_container_slots():
    wf = chain_wf(2)
    sim = OnDemandSim(scenario(wf, ecc=1), HeuPolicy(), seed=0)
    sim.occ[0] = 1                                            # node 0 fully occupied
    feas = sim.policy.feasible(sim, wf)
    assert not feas[:, 0].any() and feas[:, 1:].all()


# ------------------------------------------------------------------------------------------------ container model
def test_first_task_pays_cold_start_and_second_reuses_warm_container():
    wf = Workflow.from_edges(0, 1, [], [0], {}, 20.0)
    sc = scenario(wf, ecc=2, arrivals=((0.0, 0, 0), (50.0, 0, 0)), cold=2.0, exec_t=0.5)
    sim = OnDemandSim(sc, HeuPolicy(seed=0), seed=0, warmup=0.0, duration=100.0, debug=True)
    res = sim.run()
    sim.check_invariants()
    assert res["cold_starts"] == 1 and res["n_completed"] == 2
    assert res["avg_makespan"] >= 2.0 / 2                      # at least half of the requests paid the 2 s cold start


def test_lru_idle_container_of_another_function_is_recycled_when_node_is_full():
    wf0 = Workflow.from_edges(0, 1, [], [0], {}, 10.0)
    wf1 = Workflow.from_edges(1, 1, [], [1], {}, 10.0)
    sc = Scenario([Function(0, 1.0, 2.0), Function(1, 1.0, 2.0)], [wf0, wf1], line_net(1), np.array([1]), np.array([1e6]),
                  [(0.0, 0, 0), (30.0, 1, 0)], dict(duration_s=100.0))
    sim = OnDemandSim(sc, HeuPolicy(seed=0), seed=0, warmup=0.0, duration=100.0)
    res = sim.run()
    assert res["n_recycled"] == 1 and res["cold_starts"] == 2 and res["n_completed"] == 2


@pytest.mark.parametrize("policy_name", ["heu", "rl"])
def test_whole_run_invariants_and_conservation(policy_name):
    rng = np.random.default_rng(5)
    dags = synthetic_alibaba_like(rng, 40, max_tasks=8)
    sc = build_scenario(7, "uniform", 1.0, ne=20, n_workflows=5, pool_size=8, duration_s=40.0, dags=dags)
    pol = HeuPolicy(seed=1) if policy_name == "heu" else MosecPolicy(seed=1, train=True, total_train_decisions=10**9)  # epsilon ~ 1: random actions + learning updates
    sim = OnDemandSim(sc, pol, seed=3, duration=40.0, warmup=5.0, debug=True)
    for t_stop in (10.0, 20.0, 40.0):                          # check the invariants repeatedly during the run
        while sim.events and sim.events[0][0] <= t_stop:
            import heapq
            t, _, kind, a, b, c = heapq.heappop(sim.events)
            sim.now = t
            getattr(sim, "_ev_" + kind)(a, b, c)
        sim.check_invariants()
    res = sim.run()
    sim.check_invariants()
    assert res["n_unfinished"] == 0 and res["n_completed"] == res["n_arrived"] > 0
    # every task ran exactly once on a node with its function type
    assert sim.active == 0 and not sim.waiting and not sim.wait_tasks


def test_same_seed_same_result():
    dags = synthetic_alibaba_like(np.random.default_rng(5), 40, max_tasks=8)
    sc = build_scenario(7, "uniform", 1.0, ne=20, n_workflows=5, pool_size=8, duration_s=30.0, dags=dags)
    out = [OnDemandSim(sc, HeuPolicy(seed=1), seed=3, duration=30.0, warmup=5.0).run()["avg_makespan"] for _ in range(2)]
    assert out[0] == out[1]


# ------------------------------------------------------------------------------------------------ RL
def test_ddqn_target_is_hand_computed():
    pol = MosecPolicy(seed=0, train=True, gamma=0.5)
    for net in (pol.q, pol.target):                            # make Q linear-free: all weights zero except the output bias
        for p in net.parameters():
            torch.nn.init.zeros_(p)
    pol.q.net[4].bias.data.fill_(2.0)                         # online Q = 2 everywhere
    pol.target.net[4].bias.data.fill_(10.0)                   # target Q = 10 everywhere
    s = torch.zeros(3, 4, D)
    m = torch.ones(3, 4, dtype=torch.bool)
    a = torch.tensor([0, 1, 2])
    r = torch.tensor([-1.0, 0.0, 3.0])
    loss = pol.ddqn_loss(s, m, a, r, s, m)
    y = r + 0.5 * 10.0                                         # y = r + gamma * Q_target(s', argmax Q(s'))
    assert loss.item() == pytest.approx(float(((y - 2.0) ** 2).mean()))


def test_ddqn_selects_next_action_with_online_net_and_evaluates_with_target():
    pol = MosecPolicy(seed=0, train=True, gamma=1.0)
    for net in (pol.q, pol.target):
        for p in net.parameters():
            torch.nn.init.zeros_(p)
    pol.q.net[0].weight.data[0, 0] = 1.0                      # online Q(s,a) = tanh-free first unit -> prefers large feature 0
    pol.q.net[2].weight.data[0, 0] = 1.0
    pol.q.net[4].weight.data[0, 0] = 1.0
    pol.target.net[0].weight.data[0, 1] = 1.0                 # target prefers large feature 1 (a different node)
    pol.target.net[2].weight.data[0, 0] = 1.0
    pol.target.net[4].weight.data[0, 0] = 1.0
    s2 = torch.zeros(1, 3, D)
    s2[0, 2, 0] = 1.0                                         # online argmax = node 2
    s2[0, 0, 1] = 1.0                                         # target would prefer node 0
    m = torch.ones(1, 3, dtype=torch.bool)
    q_online = pol.q(s2)[0]
    assert int(q_online.argmax()) == 2
    t0, t2 = pol.target(s2)[0, 0].item(), pol.target(s2)[0, 2].item()
    assert t0 > t2                                            # double DQN must use t2 (online argmax), not max(target)
    loss = pol.ddqn_loss(torch.zeros(1, 3, D), m, torch.tensor([1]), torch.tensor([0.0]), s2, m)
    q_s_a = pol.q(torch.zeros(1, 3, D))[0, 1].item()
    assert loss.item() == pytest.approx((t2 - q_s_a) ** 2)


def test_ner_keeps_the_most_similar_transitions():
    buf = Buffer(100, 2, 3)
    rng = np.random.default_rng(0)
    for i in range(100):
        buf.add(np.full((2, 3), float(i), np.float32), np.ones(2, bool), 0, 0.0, np.zeros((2, 3), np.float32), np.ones(2, bool))
    cur = np.full((2, 3), 50.0, np.float32)
    idx = buf.ner_sample(cur, b=8, lam=100, rng=rng)           # lam*b >= size -> the whole buffer is drawn
    assert len(idx) == 8 and set(range(47, 54)) <= set(idx.tolist())   # 50 +/- 3 and one of the two tied at distance 4
    assert np.abs(idx - 50).max() == 4


def test_mosec_published_settings():
    pol = MosecPolicy(train=True)
    layers = [m for m in pol.q.net if isinstance(m, torch.nn.Linear)]
    assert [l.out_features for l in layers] == [64, 64, 1]                # 2 hidden layers x 64
    assert sum(isinstance(m, torch.nn.Tanh) for m in pol.q.net) == 2
    assert (pol.gamma, pol.batch, pol.lam, pol.buf_cap) == (0.99, 64, 3, 5000)
    assert pol.opt.defaults["lr"] == 0.001 and isinstance(pol.opt, torch.optim.Adam)


def test_features_have_fixed_shape_and_storage_mask():
    wf = chain_wf(3)
    sc = scenario(wf, n_nodes=5)
    sc.esc[:] = np.array([1e6, 1e6, 5.0, 1e6, 1e6])           # node 2 cannot store the 20 MB input
    pol = MosecPolicy(seed=0)
    sim = OnDemandSim(sc, pol, seed=0)
    from dfps.ondemand import OReq
    r = OReq()
    r.wf, r.origin, r.plan = wf, 0, [None, None, None]
    x, mask = pol.features(sim, r, 0)
    assert x.shape == (5, D) and np.isfinite(x).all()
    assert mask.tolist() == [True, True, False, True, True]
    assert x[0, 4 + 7] == 0 and x[4, 4 + 7] > x[1, 4 + 7]      # transfer feature grows with the hop distance from the origin
