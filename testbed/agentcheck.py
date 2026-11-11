"""Acceptance check for the node agents on the real laptops (testbed/DESIGN.md, phase 2). Run from the hub, through fleet.py:

    ~/venv-dfps/bin/python testbed/fleet.py agents check

Configures every agent with two logical nodes, then measures, one thing at a time:
  1. timers: a cold start and a task on every laptop in parallel; how late did each timer fire?
  2. transfers: every ordered pair of laptops, one pair at a time, a state of `nominal_mb`; real bytes are 1/payload_scale of that.
     Reports the nominal time (hops x size / bandwidth), the time the real bytes took on the network, the total, and the lateness.
  3. clocks: each agent's wall clock against the hub's, from a round trip.
No addresses are written here: they come from the local, git-ignored cluster file.
"""
from __future__ import annotations

import time

try:
    from testbed.agentclient import AgentClient
except ImportError:
    from agentclient import AgentClient

PORT = 5300


def clock_offset_ms(client, n=15):
    best = None
    for _ in range(n):
        t0 = time.time()
        r = client.call("ping")
        t1 = time.time()
        d = t1 - t0
        if best is None or d < best[0]:
            best = (d, r["time"] - (t0 + t1) / 2)
    return best[1] * 1e3, best[0] * 1e3


def run_check(laps, token, port=PORT, nominal_mb=20.0, payload_scale=100.0, bw=50.0, log=print):
    addr = lambda lap: (lap.get("wifi_ip") or lap["ssh"], lap.get("agent_port", port))
    clients = {lap["name"]: AgentClient(*addr(lap), token) for lap in laps}
    names = [lap["name"] for lap in laps]
    node_of = {n: [2 * i, 2 * i + 1] for i, n in enumerate(names)}
    nn = 2 * len(names)
    hops = [[0 if i == j else 1 for j in range(nn)] for i in range(nn)]
    peers = {node: list(addr(lap)) for lap in laps for node in node_of[lap["name"]]}
    for n in names:
        clients[n].call("configure", nodes={k: {"ecc": 4, "esc": 500} for k in node_of[n]}, peers=peers,
                        net={"bw_MBps": bw, "hops": hops}, payload_scale=payload_scale)
    ok = True

    log("1. timers: a 2 s cold start and a 3 s task on every laptop at once")
    for n in names:
        clients[n].call("add_instance", iid="chk", node=node_of[n][0], f=0, weight=1.0, cold_start_s=2.0)
    for n in names:
        ev = clients[n].wait_event("instance_ready", iid="chk", timeout=15)
        clients[n].call("run_task", iid="chk", run_id="chk-run", duration_s=3.0)
        log(f"   {n}: cold start fired {ev['late_s'] * 1e3:+.1f} ms late")
        ok &= abs(ev["late_s"]) < 0.05
    for n in names:
        ev = clients[n].wait_event("task_done", run_id="chk-run", timeout=15)
        log(f"   {n}: 3 s task fired {ev['late_s'] * 1e3:+.1f} ms late")
        ok &= abs(ev["late_s"]) < 0.05

    log(f"2. transfers: {nominal_mb:g} MB nominal states, {nominal_mb * 1e6 / payload_scale / 1e3:.0f} kB real bytes, one pair at a time")
    log(f"   {'from -> to':<16} {'nominal':>8} {'network':>9} {'total':>8} {'late':>8}")
    for a in names:
        for b in names:
            if a == b:
                continue
            tid = f"{a}>{b}"
            clients[a].call("send_state", src_node=node_of[a][0], dst_node=node_of[b][0], state_id=tid, size_MB=nominal_mb, transfer_id=tid)
            try:
                ev = clients[a].wait_event("transfer_done", transfer_id=tid, timeout=30)
            except TimeoutError:
                log(f"   {a} -> {b}: NO RESULT within 30 s")
                ok = False
                continue
            log(f"   {a + ' -> ' + b:<16} {ev['nominal_s']:>7.3f}s {ev['net_s'] * 1e3:>7.0f}ms {ev['total_s']:>7.3f}s {ev['late_s'] * 1e3:>6.0f}ms")
            ok &= ev["total_s"] >= ev["nominal_s"] / ev["speed"] - 1e-3 and ev["late_s"] < 0.25      # speed is 1 on the laptops
    for n in names:
        clients[n].call("release_state", node=node_of[n][0], state_id="x")

    log("3. clocks (agent wall clock minus the hub's, from the fastest of 15 round trips)")
    for n in names:
        off, rtt = clock_offset_ms(clients[n])
        log(f"   {n}: {off:+.1f} ms (round trip {rtt:.1f} ms)")
    st = {n: clients[n].call("status") for n in names}
    log("4. totals: " + ", ".join(f"{n} sent {s['counters']['sent_bytes'] // 1000} kB / received {s['counters']['recv_bytes'] // 1000} kB" for n, s in st.items()))
    for c in clients.values():
        c.close()
    return bool(ok)
