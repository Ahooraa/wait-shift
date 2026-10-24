"""Task 11 controllers: O1 DP schedule, schedule application, forecast-driven B* (P_true / P_fc), S_mean."""
import numpy as np

from dfps.oracles import ForecastAdjuster, ScheduleAdjuster, o1_schedule, s_mean_placement
from dfps.nsga2 import PlacementProblem
from dfps.sa import SimulatedAnnealing
from dfps.sim import Sim
from dfps.traces import build_trace_scenario, function_rates


def scen(seed=1, dur=120.0):
    ali = [dict(job=f"a{i}", n=4, edges=[(0, 1), (0, 2), (1, 3), (2, 3)], span=1.0) for i in range(30)]
    return build_trace_scenario("F3", 0.6, seed, "dev", dur, 10.0, ne=16, n_workflows=10, alibaba_dags=ali, pool_size=12)


def x0(sc, seed=0):
    prob = PlacementProblem(sc.network, sc.ecc, np.array([f.exec_time for f in sc.functions]), "abs")
    return prob.random(np.random.default_rng(seed))


def test_function_rates_sum_tasks():
    sc = scen()
    lam = function_rates(sc, 0.0, 120.0)
    R = np.asarray(sc.meta["rate_series"]).mean(axis=1)
    assert np.isclose(lam.sum(), sum(r * w.n for r, w in zip(R, sc.workflows)))


def test_o1_model_cost_not_worse_than_never_switching():
    sc = scen()
    X0 = x0(sc)
    sw, info = o1_schedule(sc, X0, 120.0, 10.0)
    assert info["model_cost"] <= info["model_cost_static_x0"] + 1e-6
    for t, X in sw:
        assert (X.sum(axis=1) == sc.ecc).all() and (X.sum(axis=0) >= 1).all()


def test_schedule_applies_in_simulation():
    sc = scen(seed=2)
    X0 = x0(sc, 1)
    sw, info = o1_schedule(sc, X0, 120.0, 10.0)
    if sw and sw[0][0] == 0.0:
        X0, sw = sw[0][1], sw[1:]
    sim = Sim(sc, X0, adjuster=ScheduleAdjuster(sw, 10.0), interval=10.0, seed=1, warmup=0.0, duration=120.0, debug=True)
    r = sim.run()
    sim.check_invariants()
    assert r["n_placements_applied"] == len(sw) and r["n_unfinished"] == 0


def test_apply_placement_reroutes_orphans_and_keeps_invariants():
    sc = scen(seed=3)
    X0 = x0(sc, 2)
    sim = Sim(sc, X0, seed=1, warmup=0.0, duration=60.0)
    sim.duration = 30.0
    target = s_mean_placement(sc, 120.0)
    sim._at(15.0, "place")
    sim._ev_place = lambda a, b, c: sim.apply_placement(target)
    r = sim.run()
    sim.check_invariants()
    assert r["n_placements_applied"] == 1 and r["n_unfinished"] == 0
    assert (sim.cnt.T == target).all()


def test_forecast_adjuster_true_and_noisy():
    sc = scen(seed=4)
    X0 = x0(sc, 3)
    for sigma in (0.0, 0.5):
        adj = ForecastAdjuster(SimulatedAnnealing(seed=1, iterations=20, best_so_far=True), 4.0, sigma, seed=7)
        sim = Sim(sc, X0, adjuster=adj, interval=4.0, seed=1, warmup=0.0, duration=120.0, lam_source=adj.lam_source)
        r = sim.run()
        sim.check_invariants()
        assert r["n_unfinished"] == 0 and r["n_adjust"] > 10


def test_stable_erlang_c_matches_queueing_fst_and_handles_large_c():
    from dfps.oracles import erlang_c_time
    from dfps.queueing import fst
    for c in (1, 2, 5, 16, 25):
        for rho in (0.3, 0.7, 0.95, 1.2):
            lam = rho * c / 4.0
            assert abs(erlang_c_time(lam, 4.0, c) - fst(lam, 4.0, c, "prose")) < 1e-9 * max(1.0, fst(lam, 4.0, c, "prose"))
    v = erlang_c_time(0.9 * 400 / 3.0, 3.0, 400)                      # c = 400 overflowed the factorial formula
    assert 3.0 <= v < 3.5
