"""Tests for testbed/frozen_live.py: the paper's controller (FROZEN-4) built once for the simulator and for the testbed."""
import pickle
from pathlib import Path

import numpy as np
import pytest

from dfps.nsga2 import PlacementProblem
from dfps.sim import Sim
from testbed import frozen_live as FL
from testbed import sebs_scenario as S
from testbed.agentclient import AgentClient
from testbed.livesim import LiveLink, LiveSim
from tests.live_helpers import TOKEN, start_agent_processes, stop

ROOT = Path(__file__).resolve().parent.parent
SPEED = 10.0


def small(seed=1, rho=0.1, ne=6, dur=150.0):
    sc, samp = S.build(seed, apps=["660.map-reduce"], rho=rho, ne=ne, duration_s=dur)
    X0 = PlacementProblem(sc.network, sc.ecc, np.array([f.exec_time for f in sc.functions])).random(np.random.default_rng(seed))
    return sc, samp, X0


def test_arms_are_the_papers_configurations():
    assert FL.ARMS["frozen4"]["fill_order"] == "shortfall" and FL.ARMS["frozen4"]["fast_mv4"] is True
    assert FL.ARMS["frozen4_mv3"]["fast_mv4"] is False and FL.ARMS["frozen4_p8"]["fill_passes"] == 8
    assert "fill_order" not in FL.ARMS["frozen3"]


def test_build_is_deterministic_and_leaves_the_layout_alone():
    sc, samp, X0 = small()
    X0_before = X0.copy()
    hashes = []
    for _ in range(2):
        sim, adj = FL.build(sc, X0, 1, warmup=30.0, duration=150.0, exec_sampler=samp)
        hashes.append(sim.run()["event_hash"])
    assert hashes[0] == hashes[1] and np.array_equal(X0, X0_before)             # the controller works on its own copy of the layout
    assert adj.n_switch >= 0 and len(adj.log) > 0                                # the adjuster ran


@pytest.mark.slow
def test_builder_reproduces_the_papers_stored_frozen4_run():
    """On a stored scenario of the paper (900 s, F1, load 0.5, seed 1) the builder gives the stored event hash of the `fill1` arm (= FROZEN-4)."""
    import json
    sc_pkl = ROOT / "results" / "capW1_light" / "F1_r0.5_s1.sc.pkl"
    stored = ROOT / "results" / "capW1_rows" / "F1_r0.5_s1.fill1.json"
    if not (sc_pkl.exists() and stored.exists()):
        pytest.skip("the stored results are local (not in the repository)")
    P = pickle.load(open(sc_pkl, "rb"))
    sim, _ = FL.build(P["sc"], P["X0"], 1, warmup=60.0, duration=900.0)
    r = sim.run()
    ref = json.loads(stored.read_text())["result"]
    assert r["event_hash"] == ref["event_hash"] and r["p99_makespan"] == ref["p99_makespan"]


def test_late_bind_is_off_by_default_and_changes_events_when_on():
    sc, samp, X0 = small(rho=0.3, ne=6, dur=240.0)
    off1, _ = FL.build(sc, X0, 1, arm="frozen4", warmup=30.0, duration=240.0, exec_sampler=samp)
    off2, _ = FL.build(sc, X0, 1, arm="frozen4", warmup=30.0, duration=240.0, exec_sampler=samp, late_bind=False)
    h_off = off1.run()["event_hash"]
    assert off1.late_bind is False and h_off == off2.run()["event_hash"] and off1.late_bind_ms == []
    on, _ = FL.build(sc, X0, 1, arm="frozen5", warmup=30.0, duration=240.0, exec_sampler=samp)
    r = on.run()
    assert r["event_hash"] != h_off                                                  # on: the node choices differ, so the events do
    assert on.late_bind and len(on.late_bind_ms) > 0 and r["n_unfinished"] == 0 and np.percentile(on.late_bind_ms, 99) < 10.0


def test_late_bind_is_deterministic_and_keeps_storage_balanced():
    sc, samp, X0 = small(rho=0.3, ne=6, dur=240.0)
    out = []
    for _ in range(2):
        sim, _ = FL.build(sc, X0, 1, arm="frozen5", warmup=30.0, duration=240.0, exec_sampler=samp)
        out.append(sim.run()["event_hash"])
        sim.check_invariants()                                                      # storage within capacity, every function present
        assert (sim.storage_used >= -1e-6).all()
    assert out[0] == out[1]


@pytest.fixture(scope="module")
def agents():
    procs, ports = start_agent_processes(3, SPEED)
    yield ports
    stop(procs)


def test_the_controller_runs_live_on_agents_and_acts(agents):
    sc, samp, X0 = small()
    ref_sim, _ = FL.build(sc, X0, 1, warmup=30.0, duration=150.0, exec_sampler=samp)
    ref = ref_sim.run()
    clients = {f"a{i}": AgentClient("127.0.0.1", p, TOKEN) for i, p in enumerate(agents)}
    link = LiveLink(clients, LiveLink.blocks(sc.network.ne, list(clients)), speed=SPEED, payload_scale=100)
    FL.warm_up_kernels(sc, X0)
    sim, adj = FL.build(sc, X0, 1, warmup=30.0, duration=150.0, exec_sampler=samp, sim_cls=LiveSim, link=link, drain_s=300.0)
    r = sim.run()
    assert r["n_unfinished"] == 0 and r["n_completed"] == r["n_arrived"] == ref["n_arrived"]
    assert adj.n_switch + r["n_adjust"] > 0 and len(adj.log) > 0                  # the controller took decisions on the live clock
    lv = r["live"]
    assert lv["late_events"] == 0 and lv["hub_cpu_fraction"] < 0.9               # the controller's own compute did not stall the hub
    assert 0.7 < r["p50_makespan"] / ref["p50_makespan"] < 1.6                    # same system, real clock (checked closely on the laptops)
    assert abs(r["cold_starts"] - ref["cold_starts"]) <= max(5, 0.25 * ref["cold_starts"])
