#!/usr/bin/env python3
"""LiveSim: the simulator's logic on a real clock with real agents (testbed/DESIGN.md, phase 3).

`LiveSim` (for `Sim`: DFPS, B*, SR, SG, ...) and `LiveOnDemandSim` (for `OnDemandSim`: Heu, RL) subclass the simulators WITHOUT changing
them, so every controller, dispatcher and baseline runs as it is. What changes:

  * time: `now` is the wall-clock time since the run started (times `speed`, a test option; 1 on the laptops). Arrivals, the load
    estimator, adjustment ticks and retries stay internal events and fire when the wall clock reaches them.
  * the four things the simulator only models are done by the agents (testbed/agent.py) and come back as the simulator's own events:
      warm   a cold start           -> agent add_instance (the instance becomes idle after the cold-start time)
      done   a task run             -> agent run_task (busy for the sampled duration)
      state  a state moving         -> agent send_state (real bytes between laptops, paced to the nominal Eq. 1-2 time)
      enqueue a relocated request   -> one send_state per input state; the request joins the queue when all have arrived
    The completion is processed at the time the hub receives it, so real network and scheduling delays, and the time the controller
    itself needs to compute, all appear in the measured makespans.
  * the controller's decision time is real (`adjust_ms`, `plan_ms` are wall-clock already).

The simulator's own accounting (capacity, storage) stays authoritative: agents are told not to enforce capacity or storage here.
Requests to the agents are posted without waiting, so the controller never stalls on a Wi-Fi round trip.

Not deterministic: the event hash is meaningless here. Compare distributions, not hashes (see tests/test_livesim.py).
"""
from __future__ import annotations

import heapq
import itertools
import queue
import threading
import time

import numpy as np

from dfps.ondemand import OnDemandSim
from dfps.sim import Sim

try:
    from testbed.agentclient import AgentClient
except ImportError:                                    # run as a script: testbed/ is sys.path[0]
    from agentclient import AgentClient

BIG = 1e12


class LiveLink:
    """The agents and which of them hosts which logical node."""

    def __init__(self, clients, node_agent, speed=1.0, payload_scale=100.0):
        self.clients = clients                      # {agent name: AgentClient}
        self.node_agent = node_agent                # {node id: agent name}
        self.speed, self.payload_scale = float(speed), float(payload_scale)

    @classmethod
    def from_cluster(cls, laps, token, ne, port=5300, speed=1.0, payload_scale=100.0):
        """Connect to the agents of the laptops listed in the (local) cluster file; the logical nodes go to them in contiguous blocks."""
        clients = {lap["name"]: AgentClient(lap.get("wifi_ip") or lap["ssh"], port, token) for lap in laps}
        return cls(clients, cls.blocks(ne, list(clients)), speed, payload_scale)

    @staticmethod
    def blocks(n_nodes, names):
        """Contiguous blocks of logical nodes per agent (as even as possible)."""
        return {k: names[k * len(names) // n_nodes] for k in range(n_nodes)}

    def client_of(self, node):
        return self.clients[self.node_agent[int(node)]]

    def configure(self, sc):
        names = list(self.clients)
        peers = {k: [self.clients[a].host, self.clients[a].port] for k, a in self.node_agent.items()}
        hops = sc.network.h.tolist()
        for a in names:
            mine = [k for k, n in self.node_agent.items() if n == a]
            rep = self.clients[a].call("ping")
            if abs(rep["speed"] - self.speed) > 1e-9:
                raise RuntimeError(f"agent {a} runs at speed {rep['speed']}, LiveSim at {self.speed}")
            self.clients[a].call("configure", nodes={k: {"ecc": BIG, "esc": BIG} for k in mine}, peers=peers,
                                 net={"bw_MBps": sc.network.bw, "hops": hops}, payload_scale=self.payload_scale)

    def statuses(self):
        return {a: c.call("status") for a, c in self.clients.items()}


class LiveMixin:
    """The real-time behaviour, shared by LiveSim and LiveOnDemandSim."""

    def __init__(self, *args, link=None, drain_s=120.0, **kw):
        if link is None:
            raise ValueError("LiveSim needs link=LiveLink(...)")
        self._live_on = False
        self.link, self.drain_s = link, float(drain_s)
        self._xlog = []                                       # transfers computed since the last scheduled event
        self.inbox = queue.Queue()
        self._ids = itertools.count(1)
        self._reg = {}                                        # id(instance) -> (instance, iid at the agent)
        self._warm, self._runs, self._xfers = {}, {}, {}
        self._fatal, self.n_agent_ops = None, 0
        self.live_log = {"warm": 0, "runs": 0, "transfers": 0, "relocation_transfers": 0, "late_events": 0, "inbox_max": 0, "hub_cpu_fraction": None}
        super().__init__(*args, **kw)
        self.t_end = float(self.duration) + self.drain_s
        self.speed = link.speed

    # ---------------------------------------------------------------- the clock
    def _clock(self):
        return (time.time() - self._t0) * self.speed

    # ---------------------------------------------------------------- hooks: what the simulator schedules
    def _stt(self, size_mb, k, k2):
        d = super()._stt(size_mb, k, k2)
        if self._live_on:
            self._xlog.append((int(k), int(k2), float(size_mb)))
        return d

    def _at(self, t, kind, a=None, b=None, c=None):
        if self._live_on:
            if kind == "warm":
                return self._live_warm(a, b, t)
            if kind == "done":
                return self._live_run(a, b, t)
            if kind == "state" and self._xlog:
                return self._live_transfer(kind, a, b, [self._xlog[-1]], t)
            if kind == "enqueue" and self._xlog:
                n = len(a.sizes)                                # a = the relocated Run; one transfer per input state
                if len(self._xlog) >= n:
                    return self._live_transfer(kind, a, b, self._xlog[-n:], t)
        self._xlog.clear()
        return super()._at(t, kind, a, b, c)

    def _post(self, at_node, op, **kw):
        """Post `op` to the agent that hosts logical node `at_node` (without waiting for the reply)."""
        self.n_agent_ops += 1
        self.link.client_of(at_node).post(op, callback=self._on_reply(op), **kw)

    def _on_reply(self, op):
        def cb(reply):
            if not reply.get("ok") and self._fatal is None and reply.get("error") not in ("unknown_instance", "busy"):
                self._fatal = f"agent refused {op}: {reply.get('error')} {reply.get('detail', '')}"
        return cb

    def _live_iid(self, ins):
        return f"i{next(self._ids)}"

    def _live_warm(self, ins, token, warm_at):
        """A cold start: register (or re-register after a conversion) the instance with its agent; ready after the cold-start time."""
        old = self._reg.get(id(ins))
        if old is not None:                                      # converted: the old container of the same object goes away first
            self._post(ins.node, "remove_instance", iid=old[1])
        iid = self._live_iid(ins)
        self._reg[id(ins)] = (ins, iid)
        self._warm[iid] = (ins, token)
        self.live_log["warm"] += 1
        self._post(ins.node, "add_instance", iid=iid, node=int(ins.node), f=int(ins.f), weight=float(self.sc.fw[ins.f]),
                   cold_start_s=max(0.0, float(warm_at) - self.now))

    def _live_run(self, ins, token, t_done):
        run_id = f"r{next(self._ids)}"
        self._runs[run_id] = (ins, token)
        self.live_log["runs"] += 1
        self._post(ins.node, "run_task", iid=self._reg[id(ins)][1], run_id=run_id, duration_s=max(0.0, float(t_done) - self.now))

    def _live_transfer(self, kind, a, b, entries, t):
        self._xlog.clear()
        real = [e for e in entries if e[0] != e[1]]              # a state that stays on its node needs no transfer
        if not real:
            return super()._at(t, kind, a, b, None)
        group = {"kind": kind, "args": (a, b), "left": len(real)}
        for src, dst, size in real:
            tid = f"x{next(self._ids)}"
            self._xfers[tid] = group
            self.live_log["relocation_transfers" if kind == "enqueue" else "transfers"] += 1
            self._post(src, "send_state", src_node=src, dst_node=dst, state_id=tid, size_MB=size, transfer_id=tid, store=False)

    # ---------------------------------------------------------------- events coming back from the agents
    def _handle(self, ev):
        k = ev["kind"]
        if k == "instance_ready":
            item = self._warm.pop(ev["iid"], None)
            if item:
                self._ev_warm(item[0], item[1], None)
        elif k == "task_done":
            item = self._runs.pop(ev["run_id"], None)
            if item:
                self._ev_done(item[0], item[1], None)
        elif k == "transfer_done":
            g = self._xfers.pop(ev["transfer_id"], None)
            if g is not None:
                g["left"] -= 1
                if g["left"] == 0:
                    getattr(self, "_ev_" + g["kind"])(g["args"][0], g["args"][1], None)
        elif k == "transfer_failed" and self._fatal is None:
            self._fatal = f"transfer failed: {ev.get('error')} {ev.get('detail', '')}"

    def _pump(self, client, stop):
        """Forward the agent's events to the run's inbox until the run ends (a reader left over would steal the next run's events)."""
        while not stop.is_set():
            try:
                self.inbox.put(client.events.get(timeout=0.2))
            except queue.Empty:
                continue

    # ---------------------------------------------------------------- housekeeping
    def _gc_agents(self):
        """Remove from the agents the containers the simulator no longer has (destroyed, recycled, expired)."""
        live = {id(i) for row in self.inst for lst in row for i in lst}
        for oid, (ins, iid) in list(self._reg.items()):
            if oid not in live:
                self._post(ins.node, "remove_instance", iid=iid)
                del self._reg[oid]

    def _outstanding(self):
        return len(self._warm) + len(self._runs) + len(self._xfers)

    # ---------------------------------------------------------------- the run
    def run(self):
        self.link.configure(self.sc)
        stop = threading.Event()
        for c in self.link.clients.values():                        # events left over from an earlier run on the same connections
            while True:
                try:
                    c.events.get_nowait()
                except queue.Empty:
                    break
        pumps = [threading.Thread(target=self._pump, args=(c, stop), daemon=True) for c in self.link.clients.values()]
        for t in pumps:
            t.start()
        try:
            return self._run_body()
        finally:
            stop.set()
            for t in pumps:
                t.join(timeout=1.0)

    def _run_body(self):
        ready = set()
        for row in self.inst:                                       # containers that exist at the start (static placement): idle at t = 0
            for lst in row:
                for ins in lst:
                    iid = self._live_iid(ins)
                    self._reg[id(ins)] = (ins, iid)
                    self._warm[iid] = None
                    ready.add(iid)
                    self._post(ins.node, "add_instance", iid=iid, node=int(ins.node), f=int(ins.f), weight=float(self.sc.fw[ins.f]),
                               cold_start_s=0.0)
        t_wait = time.time() + 60
        while ready:
            if time.time() > t_wait:
                raise RuntimeError(f"{len(ready)} initial containers did not report ready")
            try:
                ev = self.inbox.get(timeout=1.0)
            except queue.Empty:
                continue
            if ev["kind"] == "instance_ready" and ev["iid"] in ready:
                ready.discard(ev["iid"])
                self._warm.pop(ev["iid"], None)
            if self._fatal:
                raise RuntimeError(self._fatal)
        self._live_on = True
        self._t0 = time.time()
        cpu0 = time.process_time()
        self.now, last_gc = 0.0, 0.0
        while True:
            if self._fatal:
                raise RuntimeError(self._fatal)
            now = self._clock()
            if now > self.t_end:
                break
            wait = 0.05
            if self.events:
                wait = min(wait, max(0.0, (self.events[0][0] - now) / self.speed))
            try:
                ev = self.inbox.get(timeout=wait)
                self.now = self._clock()
                self.live_log["inbox_max"] = max(self.live_log["inbox_max"], self.inbox.qsize() + 1)
                self._handle(ev)
                continue
            except queue.Empty:
                pass
            now = self._clock()
            if self.events and self.events[0][0] <= now:
                t, _, kind, a, b, c = heapq.heappop(self.events)
                self.now = now
                if now - t > 0.25 * max(1.0, self.speed):
                    self.live_log["late_events"] += 1            # the hub itself fell behind (controller computing, GC, ...)
                getattr(self, "_ev_" + kind)(a, b, c)
                continue
            if not self.events and not self._outstanding():
                break
            if now - last_gc > 2.0 * self.speed:
                last_gc = now
                self._gc_agents()
        self.n_unfinished = self.active + len(self.waiting)
        self.live_log["hub_cpu_fraction"] = (time.process_time() - cpu0) / max(1e-9, time.time() - self._t0)   # share of one core the hub process used
        res = self.results()
        res["live"] = {"speed": self.speed, "payload_scale": self.link.payload_scale, "agent_ops": self.n_agent_ops, **self.live_log,
                       "agents": {a: {"lateness_s": s["lateness_s"], "counters": s["counters"]} for a, s in self.link.statuses().items()}}
        return res


class LiveSim(LiveMixin, Sim):
    """DFPS, B*, SR, SG and every other controller built on `Sim`, on a real clock with real agents."""


class LiveOnDemandSim(LiveMixin, OnDemandSim):
    """The on-demand baselines (Heu, RL) on a real clock with real agents."""
