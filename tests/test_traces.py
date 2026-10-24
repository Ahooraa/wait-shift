"""Trace-driven workload generation (Task 7): thinning, rho calibration, regime shifts, empirical sampler."""
import numpy as np

from dfps.sim import Sim
from dfps.traces import (EmpiricalSampler, offered_load_profile, regime_shift_series, scale_to_rho, thin_arrivals,
                         trace_series, workflow_work)
from dfps.workload import build_scenario


def scen(seed=1, ne=12, nw=6, dur=60.0):
    return build_scenario(seed, "uniform", 1.0, ne=ne, n_workflows=nw, pool_size=10, duration_s=dur, synthetic_max_tasks=6)


def test_thinning_matches_expected_counts_per_bin():
    rng = np.random.default_rng(0)
    rate = np.array([[2.0] * 50 + [10.0] * 50, [0.0] * 100])            # requests per second in 1-s bins
    arr = thin_arrivals(rate, 1.0, 100.0, 5, rng)
    t = np.array([a[0] for a in arr])
    assert all(a[1] == 0 for a in arr)                                    # zero-rate workflow never arrives
    n1, n2 = (t < 50).sum(), (t >= 50).sum()
    assert abs(n1 - 100) < 5 * np.sqrt(100) and abs(n2 - 500) < 5 * np.sqrt(500)
    assert all(arr[i][0] <= arr[i + 1][0] for i in range(len(arr) - 1))


def test_scale_to_rho_hits_target_utilisation():
    sc = scen()
    rng = np.random.default_rng(1)
    rel = rng.uniform(0.5, 1.5, (len(sc.workflows), 40))
    for rho in (0.5, 0.7, 0.85):
        r = scale_to_rho(sc, rel, rho)
        prof = offered_load_profile(sc, r, 1.0)
        assert abs(prof.mean() - rho) < 1e-9


def test_regime_shift_changes_popularity_but_not_total_rate():
    rng = np.random.default_rng(2)
    s = regime_shift_series(8, 3000.0, 60.0, rng, shift_every_s=600.0)
    assert np.allclose(s.sum(axis=0), s.sum(axis=0)[0])                   # total constant
    assert not np.allclose(s[:, 0], s[:, 10])                             # popularity differs between regimes
    assert np.allclose(s[:, 0], s[:, 9])                                  # constant within a regime (10 bins of 60 s)


def test_trace_series_resamples_per_minute_counts():
    counts = np.arange(1, 6)[:, None] * np.ones((5, 120))
    rng = np.random.default_rng(3)
    s = trace_series(counts, 3, 600.0, 10.0, rng)
    assert s.shape == (3, 60) and (s > 0).all()


def test_empirical_sampler_preserves_mean_and_heavy_tail():
    rng = np.random.default_rng(4)
    pool = rng.lognormal(0.0, 1.2, 50_000)
    smp = EmpiricalSampler(pool, mu=[5.0, 8.0])
    x = np.array([smp(0, rng) for _ in range(40_000)])
    assert abs(x.mean() - 5.0) / 5.0 < 0.15
    assert x.var() / x.mean() ** 2 > 2                                    # SCV well above exponential's 1


def test_sim_runs_on_thinned_trace_arrivals_and_reports_slo():
    sc = scen(dur=120.0)
    rng = np.random.default_rng(5)
    rate = scale_to_rho(sc, regime_shift_series(len(sc.workflows), 120.0, 10.0, rng, shift_every_s=60.0), 0.4)
    sc.arrivals = thin_arrivals(rate, 10.0, 120.0, sc.network.ne, rng)
    from dfps.nsga2 import PlacementProblem
    prob = PlacementProblem(sc.network, sc.ecc, np.array([f.exec_time for f in sc.functions]), "abs")
    X = prob.random(np.random.default_rng(6))
    sim = Sim(sc, X, seed=1, warmup=0.0, duration=120.0)
    r = sim.run()
    sim.check_invariants()
    assert r["n_arrived"] == len(sc.arrivals) and r["n_unfinished"] == 0
    assert 0 <= r["slo_ok"] <= r["n_completed"] and workflow_work(sc).min() > 0


def test_sebsflow_dags_match_table4_function_counts():
    from dfps.sebsflow import EXPECTED_FUNCTIONS, all_named_dags
    got = {d["job"].replace("sebsflow-", ""): d["n"] for d in all_named_dags() if d["job"].startswith("sebsflow-")}
    for b, n in EXPECTED_FUNCTIONS.items():
        assert got[b] == n or (b == "660.map-reduce" and got[b] == 10)     # documented MapReduce difference
    for d in all_named_dags():
        assert all(u < v for u, v in d["edges"])                          # topological order


def test_build_trace_scenario_f3_hits_rho_and_runs():
    from dfps.traces import build_trace_scenario
    rng = np.random.default_rng(0)
    ali = [dict(job=f"a{i}", n=3, edges=[(0, 1), (1, 2)], span=1.0) for i in range(20)]
    sc = build_trace_scenario("F3", 0.5, 1, duration_s=120.0, bin_s=10.0, ne=12, n_workflows=10, alibaba_dags=ali, pool_size=10)
    assert abs(sc.meta["offered_util_mean"] - 0.5) < 1e-9 and sc.meta["n_arrivals"] == len(sc.arrivals) > 0
    assert sc.meta["workflows"][:7] == ["sebsflow-650.vid", "sebsflow-6200.trip-booking", "sebsflow-660.map-reduce",
                                        "sebsflow-680.excamera", "sebsflow-690.ml", "sebsflow-6100.1000-genome",
                                        "dfps-fig1-image-processing"]
