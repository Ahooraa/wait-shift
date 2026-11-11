"""Tests for testbed/sebs_scenario.py and the derived testbed/sebs_profiles.json (the SeBS-Flow-only, measured workload)."""
import numpy as np
import pytest

from dfps.sim import Sim
from dfps.nsga2 import PlacementProblem
from testbed import sebs_scenario as S


def test_profile_table_is_complete_and_attributed():
    prof = S.load_profiles()
    assert prof["source"]["doi"] == "10.5281/zenodo.14907321" and prof["source"]["license"] == "CC BY 4.0"
    assert list(prof["workflows"]) == S.BENCHMARKS
    assert sum(len(w["functions"]) for w in prof["workflows"].values()) == 25
    conf = prof["workflows"]["6200.trip-booking"]["functions"]["confirm"]
    assert conf["stand_in"] and len(conf["duration_s_q"]) == 101                 # the failing confirm has no measured row
    for w in prof["workflows"].values():
        for p in w["functions"].values():
            q = p["duration_s_q"]
            assert q == sorted(q) and q[0] >= 0 and p["cold_init_s_median"] > 0


def test_structure_matches_sebs_flow_table4_and_the_measured_functions():
    sc, _ = S.build(1)
    assert [w.n for w in sc.workflows] == [4, 7, 10, 16, 3, 19]
    assert len(sc.functions) == 25 and sc.network.ne == 20
    names = sc.meta["function_names"]
    for w, b in zip(sc.workflows, S.BENCHMARKS):
        assert all(names[f].startswith(b + "/") for f in w.ft)                    # a workflow only uses its own functions
    ex = sc.workflows[3]                                                           # ExCamera: 5 encode, 5 reencode, 5 rebase, 1 split
    assert sorted(names[f].split("/")[1] for f in ex.ft).count("encode") == 5


def test_state_sizes_come_from_the_measured_bytes():
    sc, _ = S.build(1)
    vid = sc.workflows[0]                                                          # decode wrote ~23.7 MB, shared by 2 analyse successors
    assert vid.ss[(0, 1)] == pytest.approx(vid.ss[(0, 2)]) and 10 < vid.ss[(0, 1)] < 14
    assert vid.ss[(1, 3)] == S.MIN_STATE_MB                                        # analyse wrote nothing measured
    assert 3 < vid.input_size < 5                                                  # decode read ~4.2 MB
    assert all(v >= S.MIN_STATE_MB for w in sc.workflows for v in w.ss.values())


def test_sampler_reproduces_the_measured_means():
    sc, samp = S.build(1)
    rng = np.random.default_rng(0)
    for f in range(len(sc.functions)):
        d = np.array([samp(f, rng) for _ in range(6000)])
        mu = sc.functions[f].exec_time
        assert abs(d.mean() - mu) <= 0.06 * mu + 1e-3, (sc.meta["function_names"][f], d.mean(), mu)
        assert d.min() >= 0


def test_arrival_rate_offers_the_requested_load():
    for mix in ("uniform", "equal_load"):
        sc, _ = S.build(3, rho=0.6, duration_s=4000.0, mix=mix)
        work = np.asarray(sc.meta["work_per_request_s"])
        offered = sum(work[w] for _, w, _ in sc.arrivals) / (sc.ecc.sum() * 4000.0)
        assert abs(offered / 0.6 - 1) < 0.25, (mix, offered)
    sc, _ = S.build(3, mix="equal_load", duration_s=4000.0)
    share = np.bincount([w for _, w, _ in sc.arrivals], minlength=6) * np.asarray(sc.meta["work_per_request_s"])
    assert share.max() / share.min() < 3                                           # equal work per application, up to sampling noise


def test_memory_weights_are_a_new_capacity_model_version():
    sc, _ = S.build(1, weights="memory")
    assert sc.meta["capacity_model"] == "CAP-W2" and abs(sc.fw.mean() - 1) < 1e-9 and sc.fw.max() / sc.fw.min() > 3
    assert S.build(1)[0].meta["capacity_model"] == "CAP-U"
    with pytest.raises(ValueError):
        S.build(1, mix="nope")
    with pytest.raises(ValueError):
        S.build(1, weights="nope")


def test_same_seed_same_scenario_and_it_runs_in_the_simulator():
    a, _ = S.build(2, rho=0.3, ne=16, duration_s=60.0, mix="equal_load")
    b, _ = S.build(2, rho=0.3, ne=16, duration_s=60.0, mix="equal_load")
    assert a.arrivals == b.arrivals
    sc, samp = a, S.build(2, rho=0.3, ne=16, duration_s=60.0, mix="equal_load")[1]
    pr = PlacementProblem(sc.network, sc.ecc, np.array([f.exec_time for f in sc.functions]))
    X = pr.random(np.random.default_rng(0))
    r = Sim(sc, X, seed=1, warmup=0.0, duration=60.0, exec_sampler=samp).run()
    assert r["n_completed"] == r["n_arrived"] and r["n_unfinished"] == 0 and r["n_arrived"] > 0
