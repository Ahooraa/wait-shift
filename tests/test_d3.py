"""Task 13 (D3): surrogate, candidates, O3 surrogate adjuster, simulation clone scoring and the Kendall tau check."""
import numpy as np

from dfps.controllers import affinity_greedy_placement
from dfps.d3 import O3SurrogateAdjuster, Surrogate, candidates, simulate_candidate
from dfps.nsga2 import PlacementProblem
from dfps.sim import Sim
from dfps.traces import build_trace_scenario, function_rates, workflow_rates


def scen(seed=1, dur=120.0):
    ali = [dict(job=f"a{i}", n=4, edges=[(0, 1), (0, 2), (1, 3), (2, 3)], span=1.0) for i in range(30)]
    return build_trace_scenario("F3", 0.6, seed, "dev", dur, 10.0, ne=16, n_workflows=10, alibaba_dags=ali, pool_size=12)


def x0(sc, seed=0):
    prob = PlacementProblem(sc.network, sc.ecc, np.array([f.exec_time for f in sc.functions]), "abs")
    return prob.random(np.random.default_rng(seed))


def test_candidates_are_feasible_and_include_current():
    sc = scen()
    X = x0(sc)
    lam = function_rates(sc, 0, 10)
    cs = candidates(X, lam, np.array([f.exec_time for f in sc.functions]), np.random.default_rng(1), K=32)
    assert len(cs) == 32 and (cs[0] == X).all()
    for Y in cs:
        assert (Y.sum(axis=1) == sc.ecc).all() and (Y.sum(axis=0) >= 1).all() and (Y >= 0).all()


def test_surrogate_prefers_colocation_and_penalises_switching():
    sc = scen(seed=2)
    s = Surrogate(sc)
    lam, wr = function_rates(sc, 0, 120), workflow_rates(sc, 0, 120)
    Xa = affinity_greedy_placement(sc)
    Xr = x0(sc, 3)
    assert s.cost(Xa, lam, wr, 10.0) < s.cost(Xr, lam, wr, 10.0)       # balanced + co-located beats random
    assert s.cost(Xa, lam, wr, 10.0, X_from=Xr) > s.cost(Xa, lam, wr, 10.0, X_from=Xa)   # switching costs


def test_simulate_candidate_does_not_touch_the_live_system():
    sc = scen(seed=3)
    sim = Sim(sc, x0(sc, 4), seed=1, warmup=0.0, duration=120.0)
    import heapq
    while sim.events and sim.events[0][0] < 40.0:
        t, _, kind, a, b, c = heapq.heappop(sim.events)
        sim.now = t
        getattr(sim, "_ev_" + kind)(a, b, c)
    before = (sim.cnt.copy(), sim.active, len(sim.events), sim.now)
    v = simulate_candidate(sim, affinity_greedy_placement(sc), 10.0)
    assert v >= 0 and (sim.cnt == before[0]).all() and sim.active == before[1] and len(sim.events) == before[2] and sim.now == before[3]


def test_o3_adjuster_runs_and_measures_tau():
    sc = scen(seed=4)
    adj = O3SurrogateAdjuster(sc, 4.0, K=16, seed=1, tau_every=5, tau_k=6, tau_horizon=8.0)
    sim = Sim(sc, x0(sc, 5), adjuster=adj, interval=4.0, seed=1, warmup=0.0, duration=120.0)
    r = sim.run()
    sim.check_invariants()
    assert r["n_unfinished"] == 0 and adj.n_periods >= 25 and len(adj.taus) >= 4
    assert all(-1.0 <= t <= 1.0 for t in adj.taus if np.isfinite(t))


def test_kendall_tau_b_matches_scipy():
    from scipy.stats import kendalltau
    from dfps.d3 import kendall_tau_b
    rng = np.random.default_rng(0)
    for _ in range(50):
        x = rng.integers(0, 5, 8).astype(float)
        y = rng.integers(0, 5, 8).astype(float)
        ref = kendalltau(x, y).statistic
        got = kendall_tau_b(x, y)
        assert (np.isnan(ref) and np.isnan(got)) or abs(ref - got) < 1e-12
