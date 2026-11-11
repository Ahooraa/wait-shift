#!/usr/bin/env python3
"""Node agent for the multi-laptop testbed (testbed/DESIGN.md, phase 2).

One agent runs on every laptop and hosts several LOGICAL edge nodes. It does not decide anything: the controller on the hub
decides (placement, dispatch, moves); the agent executes and measures. It emulates:

  * container slots: add_instance occupies capacity (sum of container weights <= ecc of the node) and a cold start keeps the
    instance unusable for the cold-start time; remove_instance frees it,
  * task execution: run_task keeps an instance busy for the requested time (a wait, not a CPU burn, see DESIGN.md) and reports
    start, end and how late the timer fired,
  * state storage per node (esc) and state transfers between logical nodes: bytes really cross the network when the two nodes
    live on different laptops, at 1/payload_scale of the nominal size; the transfer is held until the nominal time
    hops * size / bandwidth (Eq. 1-2) has passed, so network jitter and contention can only make it later, never earlier.

Protocol: every message is a 4-byte length plus a JSON object (state transfers add a binary payload). A first "hello" carries the
token. Controller connection: requests {"id", "op", ...} get {"id", "ok", ...}; events ({"event": {...}}) are pushed as they happen
and appended to a local JSONL log with wall-clock timestamps (the laptops' clocks are chrony-synchronised).

  ops: ping, configure, add_instance, remove_instance, run_task, store_state, release_state, send_state, status, get_log, shutdown
  events: instance_ready, task_done, transfer_done, transfer_failed, state_received

Standard library only. `--speed K` divides every duration (tests and development only; the log records it).
  python testbed/agent.py serve --port 5300 --token-file ~/.testbed/agent.token --log-dir ~/testbed-logs
"""
from __future__ import annotations

import argparse
import asyncio
import json
import secrets
import socket
import struct
import sys
import time
from pathlib import Path

VERSION = 1
HDR = struct.Struct("!I")
MAX_HDR = 1 << 20
CHUNK = 1 << 20
ZERO = memoryview(bytes(CHUNK))
EPS = 1e-9


class AgentError(Exception):
    def __init__(self, code, detail=""):
        super().__init__(f"{code}: {detail}")
        self.code, self.detail = code, detail


def pack(msg):
    body = json.dumps(msg, separators=(",", ":"), default=str).encode()
    return HDR.pack(len(body)) + body


async def read_frame(reader):
    n = HDR.unpack(await reader.readexactly(4))[0]
    if n > MAX_HDR:
        raise ValueError("frame header too large")
    return json.loads(await reader.readexactly(n))


async def send_zeros(writer, n):
    while n > 0:
        k = min(n, CHUNK)
        writer.write(ZERO[:k])
        n -= k
        await writer.drain()


async def drain_bytes(reader, n):
    while n > 0:
        chunk = await reader.read(min(n, CHUNK))
        if not chunk:
            raise ConnectionError("connection closed during payload")
        n -= len(chunk)


class Agent:
    def __init__(self, token, log_path=None, speed=1.0):
        self.token, self.speed = token, float(speed)
        self.nodes, self.inst, self.states, self.peers = {}, {}, {}, {}
        self.net, self.scale = None, 1.0
        self.seq, self.log_f, self.log_path = 0, None, log_path
        self.late = []
        self.counters = {"tasks": 0, "cold_starts": 0, "sent_bytes": 0, "recv_bytes": 0, "sent_transfers": 0, "recv_transfers": 0, "peer_connections": 0}
        self.ctl = None
        self.pool = {}                  # (host, port) -> idle peer connections, reused: a new connection costs a handshake, and on Wi-Fi a lost SYN a 1 s stall
        self.tasks = set()              # strong references: the event loop only keeps weak ones, and a collected task would hang silently
        self.stop_event = None
        self.loop = None
        if log_path:
            Path(log_path).parent.mkdir(parents=True, exist_ok=True)
            self.log_f = open(log_path, "a", buffering=1)
        self.log_lines = []

    # ---------------------------------------------------------------- events and log
    def emit(self, kind, **kw):
        self.seq += 1
        rec = {"seq": self.seq, "t": time.time(), "kind": kind, "speed": self.speed, **kw}
        line = json.dumps(rec, separators=(",", ":"), default=str)
        self.log_lines.append(line)
        if len(self.log_lines) > 200000:
            del self.log_lines[:50000]
        if self.log_f:
            self.log_f.write(line + "\n")
        if self.ctl is not None:
            try:
                self.ctl.write(pack({"event": rec}))
            except (ConnectionError, RuntimeError):
                self.ctl = None
        return rec

    def sleep_of(self, nominal_s):
        return max(0.0, float(nominal_s)) / self.speed

    # ---------------------------------------------------------------- operations (each returns the reply fields)
    async def op_ping(self, m):
        return {"time": time.time(), "mono": time.monotonic(), "version": VERSION, "speed": self.speed}

    async def op_configure(self, m):
        """nodes {id: {ecc, esc}}, peers {node_id: [host, port]} for every logical node, net {bw_MBps, hops: matrix},
        payload_scale (real bytes = nominal / scale). Resets all state."""
        for iid, i in self.inst.items():
            for h in (i.get("timer"), i.get("run_timer")):
                if h:
                    h.cancel()
        self.nodes = {int(k): {"ecc": float(v["ecc"]), "esc": float(v["esc"]), "used_w": 0.0, "used_mb": 0.0} for k, v in m["nodes"].items()}
        self.peers = {int(k): (v[0], int(v[1])) for k, v in m.get("peers", {}).items()}
        self.net = {"bw": float(m["net"]["bw_MBps"]), "hops": m["net"]["hops"]}
        self.scale = float(m.get("payload_scale", 1.0))
        self.inst, self.states = {}, {}
        self.late = []
        for k in self.counters:
            self.counters[k] = 0
        self.emit("configured", nodes=sorted(self.nodes), payload_scale=self.scale, bw_MBps=self.net["bw"])
        return {"nodes": sorted(self.nodes)}

    def _node(self, k):
        if int(k) not in self.nodes:
            raise AgentError("unknown_node", f"node {k} is not hosted here")
        return self.nodes[int(k)]

    async def op_add_instance(self, m):
        n = self._node(m["node"])
        w, iid = float(m.get("weight", 1.0)), m["iid"]
        if iid in self.inst:
            raise AgentError("duplicate_instance", str(iid))
        if n["used_w"] + w > n["ecc"] + EPS:
            raise AgentError("capacity", f"node {m['node']}: {n['used_w'] + w:.3f} > ecc {n['ecc']}")
        cold = float(m.get("cold_start_s", 0.0))
        t0 = time.time()
        n["used_w"] += w
        rec = {"node": int(m["node"]), "f": m.get("f"), "w": w, "state": "cold", "t_add": t0, "cold_s": cold}
        self.inst[iid] = rec
        rec["timer"] = self.loop.call_later(self.sleep_of(cold), self._ready, iid)
        self.counters["cold_starts"] += 1
        return {"t": t0}

    def _ready(self, iid):
        i = self.inst.get(iid)
        if i is None or i["state"] != "cold":
            return
        i["state"], i["timer"] = "idle", None
        t = time.time()
        late = (t - i["t_add"]) - self.sleep_of(i["cold_s"])
        self.late.append(late)
        self.emit("instance_ready", iid=iid, node=i["node"], f=i["f"], t_ready=t, cold_s=i["cold_s"], late_s=late)

    async def op_remove_instance(self, m):
        i = self.inst.get(m["iid"])
        if i is None:
            raise AgentError("unknown_instance", str(m["iid"]))
        if i["state"] == "busy":
            raise AgentError("busy", "remove after the running task has finished")
        if i.get("timer"):
            i["timer"].cancel()
        self.nodes[i["node"]]["used_w"] -= i["w"]
        del self.inst[m["iid"]]
        return {}

    async def op_run_task(self, m):
        i = self.inst.get(m["iid"])
        if i is None:
            raise AgentError("unknown_instance", str(m["iid"]))
        if i["state"] != "idle":
            raise AgentError("not_idle", f"instance {m['iid']} is {i['state']}")
        d = float(m["duration_s"])
        i["state"], i["t_run"], i["run_id"], i["req_s"] = "busy", time.time(), m["run_id"], d
        i["run_timer"] = self.loop.call_later(self.sleep_of(d), self._done, m["iid"])
        return {"t_start": i["t_run"]}

    def _done(self, iid):
        i = self.inst.get(iid)
        if i is None or i["state"] != "busy":
            return
        t1 = time.time()
        i["state"], i["run_timer"] = "idle", None
        late = (t1 - i["t_run"]) - self.sleep_of(i["req_s"])
        self.late.append(late)
        self.counters["tasks"] += 1
        self.emit("task_done", run_id=i["run_id"], iid=iid, node=i["node"], t_start=i["t_run"], t_end=t1, requested_s=i["req_s"], late_s=late)

    def _reserve(self, node, state_id, size_mb):
        n = self._node(node)
        key = (int(node), state_id)
        if key in self.states:
            return
        if n["used_mb"] + size_mb > n["esc"] + EPS:
            raise AgentError("storage_full", f"node {node}: {n['used_mb'] + size_mb:.1f} MB > esc {n['esc']}")
        n["used_mb"] += size_mb
        self.states[key] = size_mb

    def _release(self, node, state_id):
        size = self.states.pop((int(node), state_id), None)
        if size is not None:
            self.nodes[int(node)]["used_mb"] -= size
        return size is not None

    async def op_store_state(self, m):
        self._reserve(m["node"], m["state_id"], float(m["size_MB"]))
        return {}

    async def op_release_state(self, m):
        self._node(m["node"])
        return {"released": self._release(m["node"], m["state_id"])}

    async def op_send_state(self, m):
        src, dst = int(m["src_node"]), int(m["dst_node"])
        self._node(src)
        if self.net is None:
            raise AgentError("not_configured")
        if dst not in self.peers and dst not in self.nodes:
            raise AgentError("unknown_node", f"no address for node {dst}")
        if dst in self.nodes and m.get("store", True):
            self._reserve(dst, m["state_id"], float(m["size_MB"]))        # local: fail now, not later
        task = asyncio.get_running_loop().create_task(self._send(m))
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        return {"accepted": True}

    async def _peer_conn(self, host, port):
        """An idle connection to the peer if there is a healthy one, else a new one (hello, TCP_NODELAY)."""
        idle = self.pool.setdefault((host, port), [])
        while idle:
            r, w = idle.pop()
            if not w.is_closing() and not r.at_eof():
                return r, w
            w.close()
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), 10)
        sock = writer.get_extra_info("socket")
        if sock is not None:
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        writer.write(pack({"op": "hello", "role": "peer", "token": self.token}))
        await writer.drain()
        if not (await read_frame(reader)).get("ok"):
            writer.close()
            raise AgentError("peer_refused")
        self.counters["peer_connections"] += 1
        return reader, writer

    async def _send(self, m):
        src, dst, tid, size = int(m["src_node"]), int(m["dst_node"]), m["transfer_id"], float(m["size_MB"])
        nominal = self.net["hops"][src][dst] * size / self.net["bw"]
        t_wall, t0 = time.time(), time.monotonic()
        nbytes, net_s, local, store = 0, 0.0, dst in self.nodes, bool(m.get("store", True))
        try:
            if not local:
                nbytes = int(size * 1e6 / self.scale)
                host, port = self.peers[dst]
                reader, writer = await self._peer_conn(host, port)
                try:
                    writer.write(pack({"op": "state", "transfer_id": tid, "dst_node": dst, "from_node": src, "state_id": m["state_id"],
                                       "size_MB": size, "bytes": nbytes, "store": store}))
                    await send_zeros(writer, nbytes)
                    ack = await read_frame(reader)
                except BaseException:
                    writer.close()                                   # a broken connection is never put back
                    raise
                idle = self.pool.setdefault((host, port), [])
                if len(idle) < 16:
                    idle.append((reader, writer))
                else:
                    writer.close()
                net_s = time.monotonic() - t0
                if not ack.get("ok"):
                    raise AgentError(ack.get("error", "peer_error"), ack.get("detail", ""))
                self.counters["sent_bytes"] += nbytes
            self.counters["sent_transfers"] += 1
            wait = self.sleep_of(nominal) - (time.monotonic() - t0)
            if wait > 0:
                await asyncio.sleep(wait)
            if m.get("move"):
                self._release(src, m["state_id"])
            total = time.monotonic() - t0
            late = total - max(self.sleep_of(nominal), net_s)
            self.late.append(late)
            self.emit("transfer_done", transfer_id=tid, src_node=src, dst_node=dst, state_id=m["state_id"], size_MB=size, nominal_s=nominal,
                      net_s=net_s, total_s=total, bytes=nbytes, local=local, t_start=t_wall, t_end=time.time(), late_s=late)
        except Exception as e:                                   # noqa: BLE001 - whatever goes wrong must be reported, never swallowed
            if local and store:
                self._release(dst, m["state_id"])
            code = e.code if isinstance(e, AgentError) else type(e).__name__
            self.emit("transfer_failed", transfer_id=tid, src_node=src, dst_node=dst, error=code, detail=str(e))

    async def op_status(self, m):
        busy = sum(i["state"] == "busy" for i in self.inst.values())
        cold = sum(i["state"] == "cold" for i in self.inst.values())
        late = sorted(self.late)
        q = lambda p: late[min(len(late) - 1, int(p * len(late)))] if late else 0.0
        return {"nodes": {str(k): {"ecc": v["ecc"], "used_w": v["used_w"], "esc": v["esc"], "used_mb": v["used_mb"]} for k, v in self.nodes.items()},
                "instances": len(self.inst), "busy": busy, "cold": cold, "counters": dict(self.counters), "speed": self.speed,
                "lateness_s": {"n": len(late), "mean": sum(late) / len(late) if late else 0.0, "p95": q(0.95), "max": late[-1] if late else 0.0},
                "seq": self.seq}

    async def op_get_log(self, m):
        since = int(m.get("since_seq", 0))
        return {"lines": [ln for ln in self.log_lines if json.loads(ln)["seq"] > since][: int(m.get("limit", 5000))]}

    async def op_shutdown(self, m):
        self.loop.call_later(0.1, self.stop_event.set)
        return {}

    # ---------------------------------------------------------------- connections
    async def _peer(self, reader, writer):
        """Serve state transfers on one connection until the sender closes it (senders reuse their connections)."""
        try:
            while True:
                try:
                    m = await read_frame(reader)
                except (asyncio.IncompleteReadError, ConnectionError, OSError):
                    return
                if m.get("op") != "state":
                    return
                n = int(m["bytes"])
                store = bool(m.get("store", True))             # the controller's own accounting is authoritative when it asks for store=False
                try:
                    if store:
                        self._reserve(m["dst_node"], m["state_id"], float(m["size_MB"]))
                except AgentError as e:
                    await drain_bytes(reader, n)
                    writer.write(pack({"ok": False, "error": e.code, "detail": e.detail}))
                    await writer.drain()
                    continue
                try:
                    await drain_bytes(reader, n)
                except (ConnectionError, OSError):
                    if store:
                        self._release(m["dst_node"], m["state_id"])
                    return
                self.counters["recv_bytes"] += n
                self.counters["recv_transfers"] += 1
                self.emit("state_received", transfer_id=m["transfer_id"], node=int(m["dst_node"]), state_id=m["state_id"], bytes=n)
                writer.write(pack({"ok": True}))
                await writer.drain()
        finally:
            writer.close()

    async def _controller(self, reader, writer):
        if self.ctl is not None:
            try:
                self.ctl.close()
            except OSError:
                pass
        self.ctl = writer
        try:
            while True:
                m = await read_frame(reader)
                op = m.get("op")
                fn = getattr(self, f"op_{op}", None)
                try:
                    if fn is None:
                        raise AgentError("unknown_op", str(op))
                    reply = await fn(m)
                    writer.write(pack({"id": m.get("id"), "ok": True, **reply}))
                except AgentError as e:
                    writer.write(pack({"id": m.get("id"), "ok": False, "error": e.code, "detail": e.detail}))
                except (KeyError, TypeError, ValueError) as e:
                    writer.write(pack({"id": m.get("id"), "ok": False, "error": "bad_request", "detail": repr(e)}))
                await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionError, OSError):
            pass
        finally:
            if self.ctl is writer:
                self.ctl = None
            writer.close()

    async def handle(self, reader, writer):
        sock = writer.get_extra_info("socket")
        if sock is not None:
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        try:
            hello = await asyncio.wait_for(read_frame(reader), 10)
            ok = hello.get("op") == "hello" and secrets.compare_digest(str(hello.get("token", "")).encode(), self.token.encode())
            writer.write(pack({"ok": ok, "time": time.time(), "version": VERSION, **({} if ok else {"error": "bad_token"})}))
            await writer.drain()
            if not ok:
                writer.close()
                return
            await (self._controller if hello.get("role") == "ctl" else self._peer)(reader, writer)
        except (asyncio.IncompleteReadError, asyncio.TimeoutError, ConnectionError, OSError, ValueError):
            writer.close()

    async def serve(self, host="0.0.0.0", port=5300, ready=None):
        self.loop = asyncio.get_running_loop()
        self.stop_event = asyncio.Event()
        server = await asyncio.start_server(self.handle, host, port)
        bound = server.sockets[0].getsockname()[1]
        self.emit("agent_started", port=bound, version=VERSION)
        if ready:
            ready(bound)
        await self.stop_event.wait()
        server.close()
        await server.wait_closed()
        self.emit("agent_stopped")

    def stop(self):
        if self.loop and self.stop_event:
            self.loop.call_soon_threadsafe(self.stop_event.set)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve")
    s.add_argument("--port", type=int, default=5300)
    s.add_argument("--bind", default="0.0.0.0")
    s.add_argument("--token-file", required=True)
    s.add_argument("--log-dir", default=str(Path.home() / "testbed-logs"))
    s.add_argument("--speed", type=float, default=1.0)
    a = ap.parse_args(argv)
    token = Path(a.token_file).expanduser().read_text().strip()
    if not token:
        raise SystemExit("empty token file")
    log = Path(a.log_dir).expanduser() / f"agent-{a.port}-{time.strftime('%Y%m%d-%H%M%S')}.jsonl"
    agent = Agent(token, log, a.speed)
    print(f"agent listening on {a.bind}:{a.port}, log {log}", flush=True)
    try:
        asyncio.run(agent.serve(a.bind, a.port))
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
