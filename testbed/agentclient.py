"""Hub-side client for the node agents (testbed/agent.py). Blocking calls plus a queue of the agent's pushed events.

    c = AgentClient(host, port, token)
    c.call("configure", nodes={...}, peers={...}, net={...}, payload_scale=100)
    c.call("add_instance", iid="i1", node=0, f=3, weight=1.0, cold_start_s=4.0)
    ev = c.wait_event("instance_ready", iid="i1", timeout=10)      # events also arrive on c.events (a queue.Queue)

Standard library only. One client per agent; calls from several threads are safe.
"""
from __future__ import annotations

import json
import queue
import socket
import struct
import threading
import time

HDR = struct.Struct("!I")


class AgentCallError(Exception):
    def __init__(self, op, code, detail=""):
        super().__init__(f"{op}: {code} {detail}".strip())
        self.op, self.code, self.detail = op, code, detail


def _recvn(sock, n):
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("agent closed the connection")
        buf += chunk
    return bytes(buf)


def _frame(msg):
    body = json.dumps(msg, separators=(",", ":")).encode()
    return HDR.pack(len(body)) + body


def _read(sock):
    n = HDR.unpack(_recvn(sock, 4))[0]
    return json.loads(_recvn(sock, n))


class AgentClient:
    def __init__(self, host, port, token, timeout=15.0):
        self.host, self.port, self.timeout = host, port, timeout
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.sock.sendall(_frame({"op": "hello", "role": "ctl", "token": token}))
        hello = _read(self.sock)
        if not hello.get("ok"):
            self.sock.close()
            raise AgentCallError("hello", hello.get("error", "refused"))
        self.sock.settimeout(None)
        self.events = queue.Queue()
        self._seen = []                       # events taken off the queue by wait_event but not matched
        self._lock, self._id, self._pending, self._closed = threading.Lock(), 0, {}, False
        self._thread = threading.Thread(target=self._reader, daemon=True)
        self._thread.start()

    def _reader(self):
        try:
            while True:
                m = _read(self.sock)
                if "event" in m:
                    self.events.put(m["event"])
                else:
                    with self._lock:
                        slot = self._pending.pop(m.get("id"), None)
                    if slot:
                        slot[1].append(m)
                        slot[0].set()
        except (ConnectionError, OSError, ValueError):
            pass
        finally:
            self._closed = True
            with self._lock:
                for ev, box in self._pending.values():
                    box.append({"ok": False, "error": "connection_lost"})
                    ev.set()
                self._pending.clear()

    def call(self, op, timeout=None, **kw):
        if self._closed:
            raise AgentCallError(op, "connection_lost")
        with self._lock:
            self._id += 1
            rid = self._id
            slot = (threading.Event(), [])
            self._pending[rid] = slot
        try:
            self.sock.sendall(_frame({"id": rid, "op": op, **kw}))
        except OSError as e:
            raise AgentCallError(op, "connection_lost", str(e))
        if not slot[0].wait(timeout or self.timeout):
            raise AgentCallError(op, "timeout")
        reply = slot[1][0]
        if not reply.get("ok"):
            raise AgentCallError(op, reply.get("error", "error"), reply.get("detail", ""))
        return reply

    def wait_event(self, kind, timeout=30.0, **match):
        """Next event of this kind whose fields equal `match`; other events are kept for later calls."""
        end = time.time() + timeout
        for i, ev in enumerate(self._seen):
            if ev["kind"] == kind and all(ev.get(k) == v for k, v in match.items()):
                return self._seen.pop(i)
        while True:
            left = end - time.time()
            if left <= 0:
                raise TimeoutError(f"no {kind} event {match} within {timeout} s")
            try:
                ev = self.events.get(timeout=left)
            except queue.Empty:
                raise TimeoutError(f"no {kind} event {match} within {timeout} s")
            if ev["kind"] == kind and all(ev.get(k) == v for k, v in match.items()):
                return ev
            self._seen.append(ev)

    def close(self):
        self._closed = True
        try:
            self.sock.close()
        except OSError:
            pass
