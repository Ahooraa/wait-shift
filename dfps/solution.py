"""Solution state used by the replacement step (Eq.7: Sol = {<EWF_k, ESS_k, U_l FRQ_lk>}) and the AET estimate.

`Sol` is a lazily-built, transactional copy of the live system: instance counts fn_lk, per-instance availability times,
request queues FRQ_lk, free storage and the node of every moved request. Mutations are recorded so that Alg.2 can revert a
rejected neighbour (Sol_t <- Sol_{t-1}) cheaply.

AET(rq, e_k) (p.8 text, D-2/A-26/A-30): sum of the input-state transfer times of rq to e_k, plus the estimated service time of
rq on e_k considering the requests waiting there, plus the output-state transfer times from e_k to the nodes where the
children of rq's task are scheduled."""
from __future__ import annotations

import heapq

import numpy as np

IDLE, COLD, BUSY = 0, 1, 2     # instance kinds; removal preference order (idle first), see Sim.apply_solution


class Sol:
    def __init__(self, sim):
        self.sim = sim
        self.net = sim.net
        self.cnt = sim.cnt.copy()                 # fn_lk as an array [F, N]
        self.free = sim.esc - sim.storage_used    # free storage per node
        self._av, self._q, self.rnode = {}, {}, {}
        self.undo = []

    # --- lazy base state -------------------------------------------------------------------------------------------
    def av(self, f, k):
        """Availability entries (relative time, kind) of the instances of function f on node k (final types)."""
        key = (f, k)
        if key not in self._av:
            self._av[key] = self.sim.live_availability(f, k)
        return self._av[key]

    def queue(self, f, k):
        key = (f, k)
        if key not in self._q:
            self._q[key] = list(self.sim.queue[k][f])
        return self._q[key]

    def node_of(self, run):
        return self.rnode.get(run, run.node)

    # --- transactional mutation -------------------------------------------------------------------------------------
    def begin(self):
        self.undo = []

    def set_cnt(self, f, k, v):
        self.undo.append(("cnt", f, k, int(self.cnt[f, k])))
        self.cnt[f, k] = v

    def set_av(self, f, k, lst):
        self.undo.append(("av", f, k, self.av(f, k)))
        self._av[(f, k)] = lst

    def set_queue(self, f, k, lst):
        self.undo.append(("q", f, k, self.queue(f, k)))
        self._q[(f, k)] = lst

    def add_free(self, k, delta):
        self.undo.append(("free", k, 0, float(self.free[k])))
        self.free[k] += delta

    def set_node(self, run, k):
        self.undo.append(("rn", run, 0, self.rnode.get(run)))
        self.rnode[run] = k

    def snapshot(self):
        """Copy of the solution state (values in the dicts are replaced, never mutated in place, so shallow copies suffice)."""
        return (self.cnt.copy(), self.free.copy(), dict(self._av), dict(self._q), dict(self.rnode))

    def restore(self, snap):
        self.cnt, self.free = snap[0].copy(), snap[1].copy()
        self._av, self._q, self.rnode = dict(snap[2]), dict(snap[3]), dict(snap[4])
        self.undo = []

    def rollback(self):
        for kind, a, b, old in reversed(self.undo):
            if kind == "cnt":
                self.cnt[a, b] = old
            elif kind == "av":
                self._av[(a, b)] = old
            elif kind == "q":
                self._q[(a, b)] = old
            elif kind == "free":
                self.free[a] = old
            else:
                if old is None:
                    self.rnode.pop(a, None)
                else:
                    self.rnode[a] = old
        self.undo = []

    # --- AET --------------------------------------------------------------------------------------------------------
    def service_estimate(self, f, k, ahead):
        """Estimated time (from now) until a request with `ahead` requests in front of it, queued at (f, k), has been
        served: list-scheduling over the instances' availability times (A-26)."""
        entries = self.av(f, k)
        if not entries:
            return float("inf")
        mu = self.sim.exec_time[f]
        heap = [e[0] for e in entries]
        heapq.heapify(heap)
        for _ in range(ahead):
            heapq.heappush(heap, heapq.heappop(heap) + mu)
        return heap[0] + mu

    def aet(self, run, k, ahead=None):
        net, wf = self.net, run.req.wf
        loc = self.node_of(run)
        inp = sum(net.stt(s, loc, k) for s in run.sizes)                     # input states to e_k (A-30: summed)
        if ahead is None:
            q = self.queue(run.f, k)
            ahead = q.index(run) if run in q else len(q)
        out = sum(net.stt(wf.ss[(run.task, c)], k, run.req.plan[c]) for c in wf.children[run.task])
        return inp + self.service_estimate(run.f, k, ahead) + out

    def total_size(self, run):
        return run.total
