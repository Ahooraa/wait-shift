"""Tests for testbed/bstar_live.py: B* built once for the simulator and for the testbed."""
import json
import pickle
from pathlib import Path

import numpy as np
import pytest

from dfps.nsga2 import PlacementProblem
from testbed import bstar_live as BS
from testbed import sebs_scenario as S
from testbed.agentclient import AgentClient
from testbed.livesim import LiveLink, LiveSim
from tests.live_helpers import TOKEN, start_agent_processes, stop

ROOT = Path(__file__).resolve().parent.parent
SPEED = 4.0                                   # the annealer and the matcher run on the real clock: at a high speed-up they would saturate the hub (a test artefact)


def small(seed=1, rho=0.1, ne=6, dur=150.0):
    sc, samp = S.build(seed, apps=["660.map-reduce"], rho=rho, ne=ne, duration_s=dur)
    X0 = PlacementProblem(sc.network, sc.ecc, np.array([f.exec_time for f in sc.functions])).random(np.random.default_rng(seed))
    return sc, samp, X0


def test_build_is_deterministic_uses_the_matcher_and_leaves_the_layout_alone():
    sc, samp, X0 = small()
    X0_before = X0.copy()
    hashes = []
    for _ in range(2):
        sim, adj = BS.build(sc, X0, 1, warmup=30.0, duration=150.0, exec_sampler=samp)
        assert sim.dispatcher is None and sim.queue_priority is None and sim.interval == BS.PERIOD_S     # DFPS matcher, FIFO, T* = 4 s
        r = sim.run()
        hashes.append(r["event_hash"])
    assert hashes[0] == hashes[1] and np.array_equal(X0, X0_before)
    assert r["n_unfinished"] == 0 and r["n_adjust"] > 0                                                   # the annealer ran


@pytest.mark.slow
def test_builder_reproduces_the_stored_bstar_run():
    """On a stored scenario of the paper (900 s, F1, load 0.5, seed 1) the builder, given the case's own period, gives the stored event hash of `B_STAR`."""
    sc_pkl = ROOT / "results" / "capW1_light" / "F1_r0.5_s1.sc.pkl"
    stored = ROOT / "results" / "capW1_light" / "F1_r0.5_s1.B_STAR.json"
    d1 = ROOT / "results" / "d1_headroom" / "F1_r0.5_s1.B_STAR.json"
    if not (sc_pkl.exists() and stored.exists() and d1.exists()):
        pytest.skip("the stored results are local (not in the repository)")
    P = pickle.load(open(sc_pkl, "rb"))
    period = json.loads(d1.read_text())["period"]
    sim, _ = BS.build(P["sc"], P["X0"], 1, warmup=60.0, duration=900.0, period=period)
    r = sim.run()
    ref = json.loads(stored.read_text())["result"]
    assert r["event_hash"] == ref["event_hash"] and r["p99_makespan"] == ref["p99_makespan"]


@pytest.fixture(scope="module")
def agents():
    procs, ports = start_agent_processes(3, SPEED)
    yield ports
    stop(procs)


def test_bstar_runs_live_on_agents(agents):
    sc, samp, X0 = small()
    ref_sim, _ = BS.build(sc, X0, 1, warmup=30.0, duration=150.0, exec_sampler=samp)
    ref = ref_sim.run()
    clients = {f"a{i}": AgentClient("127.0.0.1", p, TOKEN) for i, p in enumerate(agents)}
    link = LiveLink(clients, LiveLink.blocks(sc.network.ne, list(clients)), speed=SPEED, payload_scale=100)
    BS.warm_up(sc, X0)
    sim, adj = BS.build(sc, X0, 1, warmup=30.0, duration=150.0, exec_sampler=samp, sim_cls=LiveSim, link=link, drain_s=300.0)
    r = sim.run()
    assert r["n_unfinished"] == 0 and r["n_completed"] == r["n_arrived"] == ref["n_arrived"]
    assert r["n_adjust"] > 0                                                      # the annealer took decisions on the live clock
    assert r["live"]["hub_cpu_fraction"] < 0.9
    assert 0.7 < r["p50_makespan"] / ref["p50_makespan"] < 1.6
