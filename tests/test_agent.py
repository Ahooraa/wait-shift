"""Tests for testbed/agent.py and testbed/agentclient.py: agents on loopback (no laptops, no SSH)."""
import asyncio
import json
import threading
import time

import pytest

from testbed.agent import Agent
from testbed.agentclient import AgentCallError, AgentClient

TOKEN = "t0k3n"
SPEED = 50.0                      # tests only: every duration is divided by 50


def start_agent(speed=SPEED, log_path=None):
    agent = Agent(TOKEN, log_path, speed)
    box, ev = [], threading.Event()
    threading.Thread(target=lambda: asyncio.run(agent.serve("127.0.0.1", 0, ready=lambda p: (box.append(p), ev.set()))), daemon=True).start()
    assert ev.wait(5)
    return agent, box[0]


def hops_full(n):
    return [[0 if i == j else 1 for j in range(n)] for i in range(n)]


@pytest.fixture
def one(tmp_path):
    agent, port = start_agent(log_path=tmp_path / "a.jsonl")
    c = AgentClient("127.0.0.1", port, TOKEN)
    c.call("configure", nodes={0: {"ecc": 3, "esc": 100}, 1: {"ecc": 2, "esc": 40}}, peers={0: ["127.0.0.1", port], 1: ["127.0.0.1", port]},
           net={"bw_MBps": 50, "hops": hops_full(2)}, payload_scale=100)
    yield agent, c, tmp_path
    c.close()
    agent.stop()


def test_wrong_token_is_refused():
    agent, port = start_agent()
    with pytest.raises(AgentCallError, match="bad_token"):
        AgentClient("127.0.0.1", port, "nope")
    agent.stop()


def test_capacity_uses_container_weights_and_frees_on_remove(one):
    agent, c, _ = one
    c.call("add_instance", iid="a", node=0, f=1, weight=1.5)
    c.call("add_instance", iid="b", node=0, f=2, weight=1.5)
    with pytest.raises(AgentCallError, match="capacity"):
        c.call("add_instance", iid="c", node=0, f=3, weight=0.5)
    with pytest.raises(AgentCallError, match="duplicate_instance"):
        c.call("add_instance", iid="a", node=0, f=1)
    with pytest.raises(AgentCallError, match="unknown_node"):
        c.call("add_instance", iid="z", node=9, f=1)
    c.call("remove_instance", iid="b")
    c.call("add_instance", iid="c", node=0, f=3, weight=0.5)
    assert c.call("status")["nodes"]["0"]["used_w"] == pytest.approx(2.0)


def test_cold_start_then_task_timing_and_state_rules(one):
    agent, c, _ = one
    c.call("add_instance", iid="i", node=0, f=1, cold_start_s=5.0)
    with pytest.raises(AgentCallError, match="not_idle"):
        c.call("run_task", iid="i", run_id="r0", duration_s=1.0)          # still cold
    t = time.time()
    ev = c.wait_event("instance_ready", iid="i", timeout=5)
    assert 0.08 < time.time() - t < 0.4 and abs(ev["late_s"]) < 0.05       # 5 s / 50 = 0.1 s
    c.call("run_task", iid="i", run_id="r1", duration_s=10.0)
    with pytest.raises(AgentCallError, match="not_idle"):
        c.call("run_task", iid="i", run_id="r2", duration_s=1.0)          # busy
    with pytest.raises(AgentCallError, match="busy"):
        c.call("remove_instance", iid="i")
    done = c.wait_event("task_done", run_id="r1", timeout=5)
    assert abs((done["t_end"] - done["t_start"]) - 10.0 / SPEED) < 0.05 and abs(done["late_s"]) < 0.05
    c.call("run_task", iid="i", run_id="r3", duration_s=1.0)
    c.wait_event("task_done", run_id="r3", timeout=5)
    s = c.call("status")
    assert s["counters"]["tasks"] == 2 and s["lateness_s"]["n"] >= 3 and s["lateness_s"]["max"] < 0.05


def test_storage_budget(one):
    _, c, _ = one
    c.call("store_state", node=1, state_id="a", size_MB=30)
    with pytest.raises(AgentCallError, match="storage_full"):
        c.call("store_state", node=1, state_id="b", size_MB=20)
    assert c.call("release_state", node=1, state_id="a")["released"] is True
    c.call("store_state", node=1, state_id="b", size_MB=20)
    assert c.call("release_state", node=1, state_id="nothing")["released"] is False


def test_same_agent_transfer_is_paced_without_network_bytes(one):
    _, c, _ = one
    c.call("send_state", src_node=0, dst_node=1, state_id="s", size_MB=30, transfer_id="t")
    ev = c.wait_event("transfer_done", transfer_id="t", timeout=5)
    assert ev["local"] is True and ev["bytes"] == 0
    assert ev["nominal_s"] == pytest.approx(0.6) and ev["total_s"] >= 0.6 / SPEED - 1e-3     # 30 MB x 1 hop / 50 MB/s
    assert c.call("status")["nodes"]["1"]["used_mb"] == 30


def start_mesh(n_agents, nodes_per=2, esc=100, ecc=4):
    agents = [start_agent() for _ in range(n_agents)]
    where = {k: i for i in range(n_agents) for k in range(i * nodes_per, (i + 1) * nodes_per)}
    peers = {k: ["127.0.0.1", agents[i][1]] for k, i in where.items()}
    clients = []
    for i, (agent, port) in enumerate(agents):
        c = AgentClient("127.0.0.1", port, TOKEN)
        mine = [k for k, a in where.items() if a == i]
        c.call("configure", nodes={k: {"ecc": ecc, "esc": esc} for k in mine}, peers=peers,
               net={"bw_MBps": 50, "hops": hops_full(n_agents * nodes_per)}, payload_scale=100)
        clients.append(c)
    return agents, clients, where


def test_transfer_between_agents_moves_real_bytes_and_respects_nominal_time():
    agents, cl, where = start_mesh(2)
    cl[0].call("store_state", node=0, state_id="s", size_MB=30)
    t = time.time()
    cl[0].call("send_state", src_node=0, dst_node=2, state_id="s", size_MB=30, transfer_id="x", move=True)
    ev = cl[0].wait_event("transfer_done", transfer_id="x", timeout=10)
    assert ev["local"] is False and ev["bytes"] == 300_000                      # 30 MB / payload_scale 100
    assert ev["total_s"] >= ev["nominal_s"] / SPEED - 1e-3 and ev["net_s"] > 0
    rec = cl[1].wait_event("state_received", transfer_id="x", timeout=5)
    assert rec["node"] == 2 and rec["bytes"] == 300_000
    assert cl[1].call("status")["nodes"]["2"]["used_mb"] == 30                   # stored at the destination
    assert cl[0].call("status")["nodes"]["0"]["used_mb"] == 0                    # move=True released the source
    assert cl[1].call("status")["counters"]["recv_bytes"] == 300_000
    for c in cl:
        c.close()
    for a, _ in agents:
        a.stop()


def test_remote_storage_full_is_reported_and_nothing_is_kept():
    agents, cl, where = start_mesh(2, esc=25)
    cl[0].call("send_state", src_node=0, dst_node=2, state_id="big", size_MB=30, transfer_id="f")
    ev = cl[0].wait_event("transfer_failed", transfer_id="f", timeout=10)
    assert ev["error"] == "storage_full"
    assert cl[1].call("status")["nodes"]["2"]["used_mb"] == 0
    for c in cl:
        c.close()
    for a, _ in agents:
        a.stop()


def test_unreachable_peer_is_reported(one):
    agent, c, _ = one
    import socket
    s = socket.socket(); s.bind(("127.0.0.1", 0)); dead = s.getsockname()[1]; s.close()
    c.call("configure", nodes={0: {"ecc": 1, "esc": 100}}, peers={0: ["127.0.0.1", 1], 5: ["127.0.0.1", dead]},
           net={"bw_MBps": 50, "hops": hops_full(6)}, payload_scale=100)
    c.call("send_state", src_node=0, dst_node=5, state_id="s", size_MB=10, transfer_id="u")
    ev = c.wait_event("transfer_failed", transfer_id="u", timeout=15)
    assert ev["error"] in ("ConnectionRefusedError", "OSError", "TimeoutError")


def test_all_ordered_pairs_of_four_agents_transfer():
    agents, cl, where = start_mesh(4)
    ids = []
    for src in range(4):
        for dst in range(4):
            if src != dst:
                tid = f"{src}->{dst}"
                cl[src].call("send_state", src_node=src * 2, dst_node=dst * 2, state_id=tid, size_MB=10, transfer_id=tid)
                ids.append((src, tid))
    for src, tid in ids:
        ev = cl[src].wait_event("transfer_done", transfer_id=tid, timeout=20)
        assert ev["bytes"] == 100_000
    assert sum(c.call("status")["counters"]["recv_transfers"] for c in cl) == 12
    for c in cl:
        c.close()
    for a, _ in agents:
        a.stop()


def test_log_file_and_get_log_agree_and_configure_resets(one):
    agent, c, tmp = one
    c.call("add_instance", iid="i", node=0, f=1, cold_start_s=1.0)
    c.wait_event("instance_ready", iid="i", timeout=5)
    lines = [json.loads(x) for x in (tmp / "a.jsonl").read_text().splitlines()]
    assert [x["kind"] for x in lines][-1] == "instance_ready" and all("t" in x and "seq" in x for x in lines)
    got = c.call("get_log", since_seq=lines[0]["seq"])["lines"]
    assert [json.loads(x)["seq"] for x in got] == [x["seq"] for x in lines[1:]]
    c.call("configure", nodes={0: {"ecc": 1, "esc": 10}}, peers={}, net={"bw_MBps": 50, "hops": hops_full(1)})
    assert c.call("status")["instances"] == 0


def test_agent_survives_controller_disconnect_and_accepts_a_new_one(one):
    agent, c, _ = one
    c.call("add_instance", iid="i", node=0, f=1)
    port = c.port
    c.close()
    time.sleep(0.1)
    c2 = AgentClient("127.0.0.1", port, TOKEN)
    assert c2.call("status")["instances"] == 1
    c2.close()


def test_agent_check_runs_on_loopback_agents(capsys):
    from testbed.agentcheck import run_check
    agents = [start_agent() for _ in range(3)]
    laps = [{"name": f"edge-{i + 1}", "ssh": "127.0.0.1", "wifi_ip": "127.0.0.1", "agent_port": port} for i, (_, port) in enumerate(agents)]
    lines = []
    ok = run_check(laps, TOKEN, log=lines.append)
    assert ok is True, "\n".join(lines)
    text = "\n".join(lines)
    assert "edge-1 -> edge-2" in text and "edge-3 -> edge-1" in text and len(__import__("re").findall(r"edge-\d -> edge-\d", text)) == 6      # every ordered pair of three
    assert "clocks" in text
    for a, _ in agents:
        a.stop()
