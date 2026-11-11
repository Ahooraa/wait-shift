"""Tests for testbed/livesim.py: the simulator's logic on a real clock with agents (separate processes on loopback)."""
import time

import numpy as np
import pytest

from dfps.heu import HeuPolicy
from dfps.nsga2 import PlacementProblem
from dfps.sa import SimulatedAnnealing
from dfps.sim import Sim
from dfps.workload import build_scenario
from testbed.agentclient import AgentClient
from testbed.livesim import LiveLink, LiveOnDemandSim, LiveSim
from tests.live_helpers import TOKEN, start_agent_processes, stop

SPEED = 25.0


@pytest.fixture(scope="module")
def agents():
    procs, ports = start_agent_processes(3, SPEED)
    yield ports
    stop(procs)


def make_link(ports, ne):
    clients = {f"a{i}": AgentClient("127.0.0.1", p, TOKEN) for i, p in enumerate(ports)}
    return LiveLink(clients, LiveLink.blocks(ne, list(clients)), speed=SPEED, payload_scale=100)


def scenario(seed=2, scale=0.2, ne=10, duration=30.0):
    return build_scenario(seed, "uniform", scale, ne=ne, n_workflows=4, pool_size=8, duration_s=duration)


def placement(sc, seed=0):
    pr = PlacementProblem(sc.network, sc.ecc, np.array([f.exec_time for f in sc.functions]))
    return pr.random(np.random.default_rng(seed))


def test_static_placement_conserves_requests_and_cleans_up(agents):
    sc = scenario()
    sim = LiveSim(sc, placement(sc), seed=1, warmup=0.0, duration=30.0, link=make_link(agents, sc.network.ne), drain_s=400.0)
    r = sim.run()
    # the controller's planning time is real wall time, so at 25x speed some late arrivals fall after the measurement window:
    # every counted request must complete, and every request (counted or not) must have been processed
    assert r["n_unfinished"] == 0 and r["n_completed"] == r["n_arrived"] >= 0.5 * len(sc.arrivals)
    assert (sim.storage_used < 1e-6).all()
    assert r["cold_starts"] == 0 and r["live"]["warm"] == 0                      # static: nothing cold starts
    assert r["live"]["runs"] == sum(sc.workflows[w].n for _, w, _ in sc.arrivals)  # every task of every arrival ran once on an agent
    assert r["live"]["transfers"] > 0 and r["live"]["relocation_transfers"] == 0
    assert all(a["lateness_s"]["max"] < 0.1 for a in r["live"]["agents"].values())  # timers fire within 100 ms of their target


def test_dfps_style_reconfiguration_reaches_the_agents(agents):
    sc = scenario(scale=0.3)
    sim = LiveSim(sc, placement(sc), adjuster=SimulatedAnnealing(seed=5, iterations=40), seed=1, warmup=0.0, duration=30.0,
                  link=make_link(agents, sc.network.ne), drain_s=400.0)
    r = sim.run()
    assert r["n_unfinished"] == 0 and r["n_completed"] == r["n_arrived"] >= 0.5 * len(sc.arrivals)
    assert (sim.storage_used < 1e-6).all()
    assert r["live"]["runs"] == sum(sc.workflows[w].n for _, w, _ in sc.arrivals)
    assert r["n_adjust"] >= 3 and r["cold_starts"] > 0 and r["live"]["warm"] >= r["cold_starts"]
    assert r["live"]["relocation_transfers"] >= 0
    sim._gc_agents()                                                              # containers the simulator dropped leave the agents
    time.sleep(0.5)
    on_agents = sum(s["instances"] for s in sim.link.statuses().values())
    assert on_agents == sum(len(lst) for row in sim.inst for lst in row)


def test_on_demand_baseline_runs_on_agents(agents):
    sc = scenario(scale=0.2)
    sim = LiveOnDemandSim(sc, HeuPolicy(seed=0), seed=0, warmup=0.0, duration=30.0, link=make_link(agents, sc.network.ne), drain_s=400.0)
    r = sim.run()
    assert r["n_unfinished"] == 0 and r["n_completed"] == r["n_arrived"] > 0
    assert r["live"]["runs"] == sum(sc.workflows[w].n for _, w, _ in sc.arrivals)
    assert r["cold_starts"] > 0 and r["live"]["warm"] >= r["cold_starts"] and (sim.storage_used < 1e-6).all()


def test_agent_refusal_is_fatal_not_silent(agents):
    sc = scenario()
    link = make_link(agents, sc.network.ne)
    sim = LiveSim(sc, placement(sc), seed=1, warmup=0.0, duration=30.0, link=link, drain_s=400.0)
    sim._fatal = None
    link.clients["a0"].close()                                                   # the connection to an agent breaks
    with pytest.raises(Exception):
        sim.run()


@pytest.mark.slow
def test_live_matches_the_simulator_in_distribution(agents):
    """Same scenarios, several seeds: mean makespan of the live system close to the simulator's (not identical: the order of
    events differs a little, so the sampled durations pair up differently)."""
    ref, live = [], []
    for seed in (1, 2, 3, 4, 5, 6):
        sc = scenario(seed=seed, scale=0.15, duration=40.0)
        X = placement(sc, seed)
        ref.append(Sim(sc, X, seed=1, warmup=0.0, duration=40.0).run()["p50_makespan"])
        link = make_link(agents, sc.network.ne)
        live.append(LiveSim(sc, X, seed=1, warmup=0.0, duration=40.0, link=link, drain_s=500.0).run()["p50_makespan"])
    ref, live = np.array(ref), np.array(live)
    assert abs(live.mean() / ref.mean() - 1) < 0.15, (ref, live)
