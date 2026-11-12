"""Tests for testbed/baselines_live.py: the RL baseline built once for the simulator and for the testbed."""
import json
from pathlib import Path

import pytest

from dfps.ondemand import OnDemandSim
from testbed import baselines_live as BL
from testbed import sebs_scenario as S
from testbed.agentclient import AgentClient
from testbed.livesim import LiveLink, LiveOnDemandSim
from tests.live_helpers import TOKEN, start_agent_processes, stop

ROOT = Path(__file__).resolve().parent.parent
SPEED = 10.0
pytestmark = pytest.mark.skipif(not BL.RL_CKPT.exists(), reason="the RL checkpoint results/rl_policy.pt is local (not in the repository)")


def small(seed=1, rho=0.05, ne=6, dur=150.0):
    return S.build(seed, apps=["660.map-reduce"], rho=rho, ne=ne, duration_s=dur)


def test_rl_build_is_deterministic_and_common_random_numbers_reach_the_on_demand_simulator():
    sc, samp = small()
    h = [BL.build_rl(sc, 1, warmup=30.0, duration=150.0, exec_sampler=samp)[0].run()["event_hash"] for _ in range(2)]
    assert h[0] == h[1]
    other, _ = small(seed=2)
    h2 = BL.build_rl(other, 2, warmup=30.0, duration=150.0, exec_sampler=samp)[0].run()["event_hash"]
    assert h2 != h[0]
    plain = BL.build_rl(sc, 1, warmup=30.0, duration=150.0)[0].run()["event_hash"]
    assert plain != h[0]                                        # the sampler is used: without it the durations are the simulator's own


@pytest.mark.slow
def test_on_demand_change_keeps_the_stored_event_hash_of_the_papers_rl_run():
    """OnDemandSim now forwards extra Sim arguments; with none passed a stored paper run must give its stored hash (F1, load 0.5, seed 1, RL_CAL, CAP-W1)."""
    import pickle
    sc_pkl = ROOT / "results" / "capW1_light" / "F1_r0.5_s1.sc.pkl"
    stored = ROOT / "results" / "capW1_rows" / "F1_r0.5_s1.RL_CAL.json"
    ckpt = ROOT / "results" / "rl_policy_cal_capw1.pt"
    if not (sc_pkl.exists() and stored.exists() and ckpt.exists()):
        pytest.skip("the stored results are local (not in the repository)")
    from experiments.run import load_rl_policy
    sc = pickle.load(open(sc_pkl, "rb"))["sc"]
    sim = OnDemandSim(sc, load_rl_policy(str(ckpt), 601, sizes=True), seed=401, duration=900.0, warmup=60.0)
    assert sim.run()["event_hash"] == json.loads(stored.read_text())["result"]["event_hash"]


@pytest.fixture(scope="module")
def agents():
    procs, ports = start_agent_processes(3, SPEED)
    yield ports
    stop(procs)


def test_rl_runs_live_on_agents(agents):
    sc, samp = small()
    ref = BL.build_rl(sc, 1, warmup=30.0, duration=150.0, exec_sampler=samp)[0].run()
    clients = {f"a{i}": AgentClient("127.0.0.1", p, TOKEN) for i, p in enumerate(agents)}
    link = LiveLink(clients, LiveLink.blocks(sc.network.ne, list(clients)), speed=SPEED, payload_scale=100)
    BL.warm_up_rl(sc)
    sim, _ = BL.build_rl(sc, 1, warmup=30.0, duration=150.0, exec_sampler=samp, sim_cls=LiveOnDemandSim, link=link, drain_s=300.0)
    r = sim.run()
    assert r["n_unfinished"] == 0 and r["n_completed"] == r["n_arrived"] == ref["n_arrived"]
    lv = r["live"]
    assert lv["late_events"] == 0 and lv["hub_cpu_fraction"] < 0.9
    assert 0.7 < r["p50_makespan"] / ref["p50_makespan"] < 1.6
    # on demand: nearly every task cold-starts, in both; whether a container is reused depends on timing, which at loopback speed 10 is 10x noisier than on the
    # laptops (0.77 seen), so only the order of magnitude is checked here; the real comparison is controller_check.py on the laptops
    assert 0.5 < r["cold_starts"] / ref["cold_starts"] < 1.5
