"""Tests for testbed/independent_live.py: Graph-Aware and FaaSPR built once for the simulator and for the testbed."""
import json
import pickle
from pathlib import Path

import numpy as np
import pytest

from dfps import dispatchers as D
from dfps.nsga2 import PlacementProblem
from testbed import independent_live as IL
from testbed import sebs_scenario as S
from testbed.agentclient import AgentClient
from testbed.livesim import LiveLink, LiveSim
from tests.live_helpers import TOKEN, start_agent_processes, stop

ROOT = Path(__file__).resolve().parent.parent
SPEED = 4.0                                   # FaaSPR's LP solve runs on the real clock: at a high speed-up it would saturate the hub (a test artefact)
PATHS = 60                                    # the production value is IL.N_PATHS = 1500; 60 keeps the tests short (the construction is the same)


def small(seed=1, rho=0.1, ne=6, dur=150.0):
    sc, samp = S.build(seed, apps=["660.map-reduce"], rho=rho, ne=ne, duration_s=dur)
    X0 = PlacementProblem(sc.network, sc.ecc, np.array([f.exec_time for f in sc.functions])).random(np.random.default_rng(seed))
    return sc, samp, X0


def kwargs(arm):
    return dict(n_paths=PATHS) if arm == "faaspr" else {}


def test_constants_are_the_protocols():
    assert IL.N_PATHS == 1500 and IL.RATE_WINDOW_S == 30.0 and IL.SCALING_S == 60.0 and IL.ARMS == ("ga", "faaspr")


@pytest.mark.parametrize("arm", IL.ARMS)
def test_build_is_deterministic_has_the_right_router_and_leaves_the_layout_alone(arm):
    sc, samp, X0 = small()
    X0_before = X0.copy()
    hashes = []
    for _ in range(2):
        sim, adj = IL.build(sc, X0, 1, arm=arm, warmup=30.0, duration=150.0, exec_sampler=samp, **kwargs(arm))
        if arm == "ga":
            assert isinstance(sim.dispatcher, D.GraphAware) and sim.dispatcher.beta == 1.1 and sim.dispatcher.alpha == 1.0
        else:
            assert isinstance(sim.dispatcher, D.FaaSPRRouterPaper) and sim.dispatcher.alpha == 0.9 and sim.dispatcher.window == 30.0
        assert sim.queue_priority is None and not getattr(sim, "late_bind", False)           # FIFO queues, none of ours
        r = sim.run()
        hashes.append(r["event_hash"])
    assert hashes[0] == hashes[1] and np.array_equal(X0, X0_before)
    assert r["n_unfinished"] == 0
    assert r["n_noop_adjust"] > 0                                                              # the 60 s scaling rounds ran (they re-lay out inside the adjuster and return no annealing solution: n_adjust is 0 in the held-out runs too)


def test_faaspr_health_counters_come_from_the_run():
    sc, samp, X0 = small()
    sim, _ = IL.build(sc, X0, 1, arm="faaspr", warmup=30.0, duration=150.0, exec_sampler=samp, n_paths=PATHS)
    sim.run()
    h = IL.health(sim)
    assert h["n_solves"] > 0 and h["n_paths"] == PATHS and 0.0 <= h["repaired_req_share"] <= 1.0
    sim_ga, _ = IL.build(sc, X0, 1, arm="ga", warmup=30.0, duration=150.0, exec_sampler=samp)
    sim_ga.run()
    assert IL.health(sim_ga) == {}


def test_unknown_arm_is_refused():
    sc, samp, X0 = small()
    with pytest.raises(ValueError):
        IL.build(sc, X0, 1, arm="heft", warmup=30.0, duration=150.0)


@pytest.mark.slow
@pytest.mark.parametrize("arm,name", [("ga", "ga_p2"), ("faaspr", "faaspr")])
def test_builder_reproduces_the_stored_independent_run(arm, name):
    """On a stored held-out scenario (900 s, F1, load 0.5, seed 7) the builder gives the stored event hash of the independent run (the stored run's own path count for FaaSPR)."""
    sc_pkl = ROOT / "results" / "capW1_light" / "F1_r0.5_s7.sc.pkl"
    stored = ROOT / "results" / "capW1_independent" / f"F1_r0.5_s7.{name}.json"
    if not (sc_pkl.exists() and stored.exists()):
        pytest.skip("the stored results are local (not in the repository)")
    d = json.loads(stored.read_text())
    ref = d["result"]
    P = pickle.load(open(sc_pkl, "rb"))
    sim, _ = IL.build(P["sc"], P["X0"], 7, arm=arm, warmup=60.0, duration=900.0, n_paths=int(d["info"].get("n_paths") or IL.N_PATHS))
    r = sim.run()
    assert r["event_hash"] == ref["event_hash"] and r["p99_makespan"] == ref["p99_makespan"]


@pytest.fixture(scope="module")
def agents():
    procs, ports = start_agent_processes(3, SPEED)
    yield ports
    stop(procs)


@pytest.mark.parametrize("arm", IL.ARMS)
def test_independent_system_runs_live_on_agents(agents, arm):
    sc, samp, X0 = small()
    ref_sim, _ = IL.build(sc, X0, 1, arm=arm, warmup=30.0, duration=150.0, exec_sampler=samp, **kwargs(arm))
    ref = ref_sim.run()
    clients = {f"a{i}": AgentClient("127.0.0.1", p, TOKEN) for i, p in enumerate(agents)}
    link = LiveLink(clients, LiveLink.blocks(sc.network.ne, list(clients)), speed=SPEED, payload_scale=100)
    sim, _ = IL.build(sc, X0, 1, arm=arm, warmup=30.0, duration=150.0, exec_sampler=samp, sim_cls=LiveSim, link=link, drain_s=300.0, **kwargs(arm))
    r = sim.run()
    assert r["n_unfinished"] == 0 and r["n_completed"] == r["n_arrived"] == ref["n_arrived"]
    assert r["live"]["hub_cpu_fraction"] < 0.9
    assert 0.7 < r["p50_makespan"] / ref["p50_makespan"] < 1.8
