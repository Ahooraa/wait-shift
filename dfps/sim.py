"""Discrete-event simulator of the DFPS system model (p.4-5 Sec.3.1).

Per edge node e_k: ecc_k container slots (instances of functions, fn_lk of function f_l), esc_k MB of state storage, one
request queue FRQ_lk per function. A task becomes ready-to-execute when all its input states are stored on the node chosen
by the scheduler; its request then waits in FRQ_lk for one of the fn_lk instances. After execution the output states are
sent to the nodes where the child tasks are scheduled; consumed input states are deleted (p.5).
Not modelled because the paper does not model it (p.5): link contention, propagation delay, keep-alive expiry.
Execution times are exponential with mean mu_l (A-13); transfers follow Eq.1-2 exactly."""
from __future__ import annotations

import hashlib
import heapq
import itertools
import time
from collections import deque

import numpy as np

from .matching import MatchContext, schedule
from .queueing import fst as fst_formula
from .solution import BUSY, COLD, IDLE, Sol


class Instance:
    __slots__ = ("f", "node", "state", "warm_at", "busy_until", "swap_to", "token", "run")

    def __init__(self, f, node, state, warm_at=0.0):
        self.f, self.node, self.state, self.warm_at = f, node, state, warm_at
        self.busy_until, self.swap_to, self.token, self.run = 0.0, None, 0, None


class Req:
    __slots__ = ("id", "wf", "origin", "t_arr", "plan", "pending", "left", "t_done")


class Run:
    """A request for function FT(t) on node `node` (an element of FRQ_lk)."""
    __slots__ = ("req", "task", "f", "node", "sizes", "total", "t_enq", "t_first", "t_start", "n_moves")

    def __init__(self, req, task, node):
        wf = req.wf
        self.req, self.task, self.f, self.node = req, task, wf.ft[task], node
        self.sizes = [wf.input_size] if not wf.parents[task] else [wf.ss[(u, task)] for u in wf.parents[task]]
        self.total = float(sum(self.sizes))
        self.t_enq = 0.0
        self.t_first, self.t_start, self.n_moves = None, 0.0, 0


class Sim:
    def __init__(self, sc, X, adjuster=None, interval=None, seed=0, fst_variant="prose", k_best=10, n_trees=5,
                 lam_window=5, lam_update=1.0, duration=None, warmup=30.0, drain_factor=20.0, use_source=True, debug=False,
                 allow_empty=False, admission=None, exec_sampler=None, slo_factor=3.0, match_objective="sum", retry_min_interval=0.0, retry_max_attempts=None, lam_source=None, record_requests=False,
                 move_cost=1.0, elastic=False, dispatcher=None, trace=False):
        from .constants import PAPER
        self.sc, self.net = sc, sc.network
        self.N, self.F = self.net.ne, len(sc.functions)
        self.exec_time = np.array([f.exec_time for f in sc.functions])
        self.cold_start = np.array([f.cold_start for f in sc.functions])
        self.esc = sc.esc.astype(float)
        self.rng = np.random.default_rng(seed)
        self.sched_rng = np.random.default_rng(seed + 1)
        self.fst_variant, self.k_best, self.n_trees, self.use_source = fst_variant, k_best, n_trees, use_source
        self.adjuster, self.debug = adjuster, debug
        self.move_cost = float(move_cost)
        # elastic capacity (2026-10-23): DFPS fixes the container count at the slot budget (D-7: every slot always holds an
        # instance) and can only convert one function into another. elastic=True lets a controller leave slots EMPTY, adding an
        # instance into a free slot (cold start) and destroying one (immediately if idle or still cold, after its run if busy).
        # The unit of cost is then the number of provisioned containers, integrated over the measured window (inst_s).
        self.elastic = bool(elastic)
        # dispatcher: callable(sim, request) -> {task: node} or None; None = DFPS's graph pattern matching (see dfps/dispatchers.py)
        self.dispatcher = dispatcher
        self.trace = {"tasks": [], "reqs": []} if trace else None      # per-task trace of in-window requests (dfps/diagnostics.py)
        # --- Task 7 extensions (all default to the DFPS behaviour; see output/data-analysis/sim/DECISION.md)
        # waiting-list retries: 0.0 = after every task completion (original behaviour, A-24); > 0 = at most once per that many
        # simulated seconds (a request still gets placed as soon as room appears, delayed by at most the interval)
        self.retry_min_interval, self._last_retry, self._retry_pending = float(retry_min_interval), -1e18, False
        self.n_retry_rounds = 0
        self.lam_source = lam_source          # callable(sim) -> lam [F, N]; None = measured window rates (DFPS)
        self.n_placements_applied = 0
        self.record_requests, self.request_log = record_requests, []   # (id, t_arr, makespan, slo_ok) of in-window requests
        self.request_cp = []                  # unloaded critical path of each logged request (same order): lets the SLO factor be re-evaluated offline
        self.n_parked = 0                     # A-25b: reroute attempts that found no node with room (request waits 1 s)
        self.retry_max_attempts = retry_max_attempts   # None = try every waiting request each round; k = at most k per round (round-robin)
        self.match_objective = match_objective  # "sum" (paper) or "critical" (E5 variant)
        self.admission = admission            # callable(sim, req) -> bool; None admits every request (DFPS)
        self.exec_sampler = exec_sampler      # callable(function_id, rng) -> seconds; None = exponential(mu_l) (A-13)
        self.slo_factor = float(slo_factor)   # SLO_w = slo_factor x unloaded critical path (sum of mean exec times)
        self.crit_path = {w.id: self._critical_path(w) for w in sc.workflows}
        self._hash = hashlib.blake2b(digest_size=16)
        self.n_rejected, self.n_slo_ok, self.cold_slot_s = 0, 0, 0.0
        self.adjust_ms, self.plan_ms, self.n_noop_adjust = [], [], 0
        self.interval = float(PAPER["replacement_interval_s"]["value"] if interval is None else interval)
        self.duration = float(sc.meta.get("duration_s", 300.0) if duration is None else duration)
        self.warmup, self.t_end = warmup, self.duration * (1.0 + drain_factor)
        self.events, self.seq, self.now = [], itertools.count(), 0.0
        # state
        self.inst = [[[] for _ in range(self.F)] for _ in range(self.N)]
        self.queue = [[deque() for _ in range(self.F)] for _ in range(self.N)]
        self.cnt = np.zeros((self.F, self.N), dtype=int)
        self.storage_used = np.zeros(self.N)
        self.req_count = np.zeros((self.F, self.N), dtype=int)       # requests per (f,k) in the past interval
        self.lam_w, self.lam_dt = int(lam_window), lam_update
        self.buckets = np.zeros((self.lam_w, self.F, self.N))
        self.lam = np.zeros((self.F, self.N))
        self._fst_cache, self.waiting, self.active = {}, deque(), 0
        for k in range(self.N):
            if X[k].sum() > sc.ecc[k]:
                raise ValueError(f"placement exceeds ecc_{k}")
            for f in range(self.F):
                for _ in range(int(X[k, f])):
                    self.inst[k][f].append(Instance(f, k, IDLE))
                self.cnt[f, k] = int(X[k, f])
        self._n_inst, self._t_acct, self.inst_s, self.n_add_blocked = int(np.asarray(X).sum()), 0.0, 0.0, 0
        if not allow_empty and (self.cnt.sum(axis=1) == 0).any():   # allow_empty: on-demand baselines (Heu, RL) start empty
            raise ValueError("initial placement leaves a function without any instance")
        # metrics (measured in [warmup, duration], D: makespan of requests that ARRIVE in the window)
        self.makespans, self.n_arrived, self.cold_starts, self.busy_time, self.n_unfinished = [], 0, 0, 0.0, 0
        self.cold_starts_total, self.n_rerouted, self.n_adjust, self.n_moved = 0, 0, 0, 0
        self.rid = itertools.count()
        self.win = {}                                    # in-window requests not yet finished: id -> arrival time
        for t, wid, origin in sc.arrivals:
            self._at(t, "arrive", wid, origin)
        self._at(self.lam_dt, "lam_tick")
        if adjuster is not None:
            self._at(self.interval, "adjust")

    # ------------------------------------------------------------------------------------------------ plumbing
    def _at(self, t, kind, a=None, b=None, c=None):
        heapq.heappush(self.events, (t, next(self.seq), kind, a, b, c))

    def _critical_path(self, wf):
        """Unloaded critical path of a workflow: longest path of mean execution times (no queueing, cold starts, transfers)."""
        d = [0.0] * wf.n
        for t in range(wf.n):                                     # tasks are in topological order
            d[t] = self.exec_time[wf.ft[t]] + max((d[u] for u in wf.parents[t]), default=0.0)
        return max(d)

    def run(self):
        h = self._hash
        same_t, n_same = None, 0
        while self.events:
            t, _, kind, a, b, c = heapq.heappop(self.events)
            if t > self.t_end:
                break
            if t == same_t:                                       # guard: the clock must advance (fail loudly, never hang)
                n_same += 1
                if n_same > 5_000_000:
                    raise RuntimeError(f"simulation livelock: >5e6 events at t={t} (last kind {kind})")
            else:
                same_t, n_same = t, 0
            self.now = t
            h.update(f"{t:.9f}|{kind}|{a if isinstance(a, int) else ''}|{b if isinstance(b, int) else ''};".encode())
            getattr(self, "_ev_" + kind)(a, b, c)
        self.n_unfinished = self.active + len(self.waiting)
        return self.results()

    def t_end_effective(self):
        return min(self.now, self.t_end)

    def in_window(self, t):
        return self.warmup <= t < self.duration

    # ------------------------------------------------------------------------------------------------ estimates
    def fst_vec(self, f):
        v = self._fst_cache.get(f)
        if v is None:
            v = np.full(self.N, np.inf)
            for k in np.flatnonzero(self.cnt[f]):
                v[k] = fst_formula(self.lam[f, k], self.exec_time[f], int(self.cnt[f, k]), self.fst_variant,
                                   queued=len(self.queue[k][f]))
            self._fst_cache[f] = v
        return v

    def live_availability(self, f, k):
        """(relative availability, kind) of every instance whose FINAL type is f on node k (idle: 0; busy: mean residual
        mu_f of its running function (memoryless); cold: time until warm; a busy instance waiting to be swapped into f
        becomes available after its run ends plus f's cold start)."""
        out = []
        for g in range(self.F):
            for ins in self.inst[k][g]:
                final = ins.swap_to if ins.swap_to is not None else ins.f
                if final != f:
                    continue
                if ins.swap_to is not None:
                    out.append((self.exec_time[ins.f] + self.cold_start[f], COLD))
                elif ins.state == IDLE:
                    out.append((0.0, IDLE))
                elif ins.state == COLD:
                    out.append((max(0.0, ins.warm_at - self.now), COLD))
                else:
                    out.append((self.exec_time[f], BUSY))
        return out

    # ------------------------------------------------------------------------------------------------ events
    def _ev_lam_tick(self, a, b, c):
        self.buckets = np.roll(self.buckets, 1, axis=0)
        self.buckets[0] = 0.0
        w = min(self.lam_w * 1.0, max(self.now, 1.0))
        self.lam = self.buckets.sum(axis=0) / w if self.lam_source is None else self.lam_source(self)
        self._fst_cache = {}
        if self.now < self.t_end and (self.active or self.waiting or self.events):
            self._at(self.now + self.lam_dt, "lam_tick")

    def _ev_adjust(self, a, b, c):
        if self.now >= self.duration and not self.active and not self.waiting:
            return
        t0 = time.perf_counter()
        sol = self.adjuster.run(self)                              # may return None: no reconfiguration this tick
        self.adjust_ms.append((time.perf_counter() - t0) * 1e3)
        if sol is None:
            self.n_noop_adjust += 1
        else:
            self.apply_solution(sol)
            if self.debug:
                self.check_invariants()
            self.n_adjust += 1
            self.req_count[:] = 0
        self._at(self.now + float(getattr(self.adjuster, "next_interval", None) or self.interval), "adjust")

    def _ev_arrive(self, wid, origin, c):
        wf = self.sc.workflows[wid]
        r = Req()
        r.id, r.wf, r.origin, r.t_arr, r.t_done = next(self.rid), wf, origin, self.now, None
        r.plan = None
        r.pending = [1 if not wf.parents[t] else len(wf.parents[t]) for t in range(wf.n)]
        r.left = wf.n
        if self.admission is not None and not self.admission(self, r):
            if self.in_window(self.now):
                self.n_arrived += 1
                self.n_rejected += 1
            return
        self.active += 1
        if self.in_window(self.now):
            self.n_arrived += 1
            self.win[r.id] = self.now
        if not self._plan(r):
            self.waiting.append(r)

    def _plan(self, r):
        wf = r.wf
        ctx = MatchContext(self.net, self.fst_vec, self.esc - self.storage_used)
        t0 = time.perf_counter()
        if self.dispatcher is not None:
            res = self.dispatcher(self, r)
            res = None if res is None else (res, 0.0)
        else:
            res = schedule(wf, r.origin, ctx, self.k_best, self.n_trees, self.sched_rng, self.use_source, self.match_objective)
        self.plan_ms.append((time.perf_counter() - t0) * 1e3)
        if res is None:
            return False
        r.plan = res[0]
        for t in range(wf.n):                                    # A-23: reserve the input states' storage at planning
            self.storage_used[r.plan[t]] += wf.input_total(t)
        for root in wf.roots:
            self._at(self.now + self.net.stt(wf.input_size, r.origin, r.plan[root]), "state", r, root)
        return True

    def _retry_waiting(self):
        n = len(self.waiting) if self.retry_max_attempts is None else min(len(self.waiting), int(self.retry_max_attempts))
        for _ in range(n):
            r = self.waiting.popleft()
            if not self._plan(r):
                self.waiting.append(r)

    def _ev_state(self, r, task, c):
        r.pending[task] -= 1
        if r.pending[task] == 0:
            run = Run(r, task, r.plan[task])
            self._enqueue(run, run.node)

    def _enqueue(self, run, k):
        f = run.f
        if self.cnt[f, k] == 0:                                   # D-6 / A-25: no instance here any more -> reroute by AET
            self._reroute(run)
            return
        run.node, run.t_enq = k, self.now
        if run.t_first is None:
            run.t_first = self.now
        self.queue[k][f].append(run)
        self.buckets[0, f, k] += 1
        self.req_count[f, k] += 1
        self._dispatch(k, f)

    def _reroute(self, run):
        sol = Sol(self)
        best = None
        for k in np.flatnonzero(self.cnt[run.f]):
            if self.esc[k] - self.storage_used[k] + (run.total if k == run.node else 0.0) < run.total:
                continue
            a = sol.aet(run, int(k))
            if best is None or a < best[0]:
                best = (a, int(k))
        if best is None:
            # A-25b (2026-10-14): no node that holds f has room for the request's input states (storage exhausted under deep
            # overload). The paper does not cover this; like A-24 (wait and retry) the request stays where it is, keeps its
            # storage, and tries again after 1 s of simulated time (an instance of f may be placed back, or room may free up).
            self.n_parked += 1
            self._at(self.now + 1.0, "enqueue", run, run.node)
            return
        self.n_rerouted += 1
        self.relocate(run, best[1])

    def relocate(self, run, k_new):
        """Move a request (and its input states) to another node; it joins FRQ there after the transfer (A-12, A-30)."""
        k_old = run.node
        # move_cost (sensitivity study 2026-10-23): relocating a queued request transfers its input states again, and that
        # traffic shares the network with the workflows' own transfers -- which this simulator does not model (STT is a fixed
        # function of size and hops, with no link contention). Measured in the winning configuration, relocations add 41% to
        # the total state volume, and P99 improves monotonically as their cap is lifted, i.e. nothing prices them. A factor
        # > 1 charges each relocation that multiple of its nominal transfer time, for every controller alike.
        delay = self.move_cost * sum(self.net.stt(s, k_old, k_new) for s in run.sizes)
        self.storage_used[k_old] -= run.total
        self.storage_used[k_new] += run.total
        run.node = k_new
        run.n_moves += 1
        self.n_moved += 1
        self._at(self.now + delay, "enqueue", run, k_new)

    def _ev_enqueue(self, run, k, c):
        if run.node != k:                                          # relocated again in the meantime
            return
        self._enqueue(run, k)

    def _dispatch(self, k, f):
        q = self.queue[k][f]
        for ins in self.inst[k][f]:
            if not q:
                return
            if ins.state == IDLE and ins.swap_to is None:
                self._start(ins, q.popleft())

    def _start(self, ins, run):
        mu = self.exec_time[run.f]
        s = float(self.rng.exponential(mu)) if self.exec_sampler is None else float(self.exec_sampler(run.f, self.rng))
        ins.state, ins.run, ins.busy_until = BUSY, run, self.now + s
        run.t_start = self.now
        lo, hi = max(self.now, self.warmup), min(self.now + s, self.duration)
        if hi > lo:
            self.busy_time += hi - lo
        self._at(self.now + s, "done", ins, ins.token)

    def _ev_done(self, ins, token, c):
        run = ins.run
        r, wf, t, k = run.req, run.req.wf, run.task, ins.node
        ins.run, ins.state = None, IDLE
        self.storage_used[k] -= run.total                          # consumed input states are removed (p.5)
        for ch in wf.children[t]:
            self._at(self.now + self.net.stt(wf.ss[(t, ch)], k, r.plan[ch]), "state", r, ch)
        if self.trace is not None and self.in_window(r.t_arr):
            self.trace["tasks"].append((r.id, wf.id, t, r.plan[t], k, run.t_first, run.t_start, self.now, run.n_moves))
        r.left -= 1
        if r.left == 0:
            r.t_done = self.now
            if self.trace is not None and self.in_window(r.t_arr):
                self.trace["reqs"].append((r.id, wf.id, r.t_arr, self.now))
            self.active -= 1
            if self.in_window(r.t_arr):
                self.makespans.append(self.now - r.t_arr)
                ok = self.now - r.t_arr <= self.slo_factor * self.crit_path[wf.id]
                if ok:
                    self.n_slo_ok += 1
                if self.record_requests:
                    self.request_log.append((r.id, r.t_arr, self.now - r.t_arr, bool(ok)))
                    self.request_cp.append(float(self.crit_path[wf.id]))
                self.win.pop(r.id, None)
        if ins.swap_to == -1:                                      # elastic: a busy instance scheduled for removal ends now
            self._destroy(ins)
        elif ins.swap_to is not None:                              # D-5: a busy instance that was replaced converts now
            self._convert(ins, ins.swap_to)
        else:
            self._dispatch(k, ins.f)
        if self.waiting:
            self._maybe_retry()

    def _maybe_retry(self):
        if self.retry_min_interval <= 0.0 or self.now - self._last_retry >= self.retry_min_interval:
            self._last_retry = self.now
            self.n_retry_rounds += 1
            self._retry_waiting()
        elif not self._retry_pending:
            self._retry_pending = True
            self._at(self._last_retry + self.retry_min_interval, "retry")

    def _ev_retry(self, a, b, c):
        # This event is scheduled exactly at the earliest allowed time, so retry unconditionally. Re-testing
        # `now - last >= interval` here can fail by floating-point rounding ((t + 1.0) - t < 1.0 for ~0.04% of t), which
        # re-scheduled the event at the same timestamp forever (livelock found 2026-10-14).
        self._retry_pending = False
        if self.waiting:
            self._last_retry = self.now
            self.n_retry_rounds += 1
            self._retry_waiting()

    def _convert(self, ins, g):
        """The instance becomes a cold instance of function g (cold-start delay of g)."""
        self.inst[ins.node][ins.f].remove(ins)
        ins.f, ins.swap_to, ins.state = g, None, COLD
        ins.warm_at = self.now + self.cold_start[g]
        ins.token += 1
        self.inst[ins.node][g].append(ins)
        self.cold_starts_total += 1
        if self.in_window(self.now):
            self.cold_starts += 1
        self.cold_slot_s += max(0.0, min(ins.warm_at, self.duration) - max(self.now, self.warmup))
        self._at(ins.warm_at, "warm", ins, ins.token)
        self._fst_cache = {}

    def _ev_warm(self, ins, token, c):
        if token != ins.token or ins.state != COLD:
            return
        ins.state = IDLE
        self._dispatch(ins.node, ins.f)

    # ------------------------------------------------------------------------------------------------ elastic capacity
    def _acct(self):
        """Integrate the number of provisioned containers over the measured window [warmup, duration]."""
        lo, hi = max(self._t_acct, self.warmup), min(self.now, self.duration)
        if hi > lo:
            self.inst_s += self._n_inst * (hi - lo)
        self._t_acct = max(self._t_acct, self.now)

    def n_slots_used(self, k):
        return sum(len(self.inst[k][g]) for g in range(self.F))

    def add_instance(self, k, f):
        """Start a new (cold) instance of f in a free slot of node k. Returns False if the node has no free slot (a slot is
        occupied until a busy instance marked for removal has finished its run)."""
        if self.n_slots_used(k) >= self.sc.ecc[k]:
            self.n_add_blocked += 1
            return False
        self._acct()
        ins = Instance(f, k, COLD, warm_at=self.now + self.cold_start[f])
        self.inst[k][f].append(ins)
        self.cnt[f, k] += 1
        self._n_inst += 1
        self.cold_starts_total += 1
        if self.in_window(self.now):
            self.cold_starts += 1
        self.cold_slot_s += max(0.0, min(ins.warm_at, self.duration) - max(self.now, self.warmup))
        self._at(ins.warm_at, "warm", ins, ins.token)
        self._fst_cache = {}
        return True

    def remove_instance(self, k, f):
        """Remove one instance of f from node k (the final count drops by one now). Preference as for a replacement: idle, then
        cold, destroyed at once; otherwise a pending incoming conversion is cancelled, otherwise a busy instance is destroyed
        when its run ends."""
        cands = [i for i in self.inst[k][f] if i.swap_to is None]
        pref = [i for i in cands if i.state == IDLE] or [i for i in cands if i.state == COLD]
        if pref:
            self._destroy(pref[0])
        else:
            pend = [i for g in range(self.F) for i in self.inst[k][g] if i.swap_to == f]
            if pend:
                pend[0].swap_to = -1
            else:
                busy = [i for i in cands if i.state == BUSY]
                busy[0].swap_to = -1
        self.cnt[f, k] -= 1
        self._fst_cache = {}

    def _destroy(self, ins):
        """Take the instance out of its slot. A pending removal (swap_to == -1) has already left the count."""
        self._acct()
        self.inst[ins.node][ins.f].remove(ins)
        ins.token += 1                                               # a stale 'warm' or 'done' event for it is ignored
        ins.state = None
        self._n_inst -= 1
        self._fst_cache = {}

    # ------------------------------------------------------------------------------------------------ replacement
    def swap_instance(self, k, f_r, f_n):
        """Replace one instance of f_r on node k by a new (cold) instance of f_n (Alg.1 l.5-6). Preference: idle, then
        cold, then busy (the busy one finishes its run first, D-5)."""
        cands = [i for i in self.inst[k][f_r] if i.swap_to is None]
        pref = [i for i in cands if i.state == IDLE] or [i for i in cands if i.state == COLD]
        if pref:
            ins = pref[0]
            self.cnt[f_r, k] -= 1
            self.cnt[f_n, k] += 1
            self._convert(ins, f_n)
        else:
            # the instances counted for f_r are pending replacements of busy instances (swap_to == f_r): redirect one
            pend = [i for g in range(self.F) for i in self.inst[k][g] if i.swap_to == f_r]
            if pend:
                pend[0].swap_to = f_n
            else:                                              # only busy instances of f_r: replace one after its run
                busy = [i for i in cands if i.state == BUSY]
                busy[0].swap_to = f_n
            self.cnt[f_r, k] -= 1
            self.cnt[f_n, k] += 1
        self._fst_cache = {}

    def apply_solution(self, sol):
        """Apply the final solution Sol_f of the annealing step to the live system: net instance changes per node
        (1-for-1 replacements) and the relocation of moved requests."""
        for k in range(self.N):
            d = sol.cnt[:, k] - self.cnt[:, k]
            if not d.any():
                continue
            dec = [f for f in np.flatnonzero(d < 0) for _ in range(int(-d[f]))]
            inc = [f for f in np.flatnonzero(d > 0) for _ in range(int(d[f]))]
            assert len(dec) == len(inc), "replacements must be 1-for-1"
            for f_r, f_n in zip(dec, inc):
                self.swap_instance(k, int(f_r), int(f_n))
        for run, k_new in list(sol.rnode.items()):
            if k_new != run.node:
                q = self.queue[run.node][run.f]
                if run in q:
                    q.remove(run)
                    self.relocate(run, int(k_new))

    def apply_placement(self, X):
        """Move the live system to placement X [N, F] (row sums must equal ecc): 1-for-1 replacements per node, then reroute
        requests queued at (f, k) pairs that no longer hold f (they would otherwise never be served). Used by oracles."""
        X = np.asarray(X, dtype=int)
        if self.elastic:                                          # slots may stay empty: row sums only have to fit
            assert (X.sum(axis=1) <= self.sc.ecc).all() and (X.sum(axis=0) >= 1).all()
        else:
            assert (X.sum(axis=1) == self.sc.ecc).all() and (X.sum(axis=0) >= 1).all()
        for k in range(self.N):
            d = X[k] - self.cnt[:, k]
            if not d.any():
                continue
            dec = [f for f in np.flatnonzero(d < 0) for _ in range(int(-d[f]))]
            inc = [f for f in np.flatnonzero(d > 0) for _ in range(int(d[f]))]
            for f_r, f_n in zip(dec, inc):
                self.swap_instance(k, int(f_r), int(f_n))
            if self.elastic:                                      # the net difference: plain removals and additions
                for f_r in dec[len(inc):]:
                    self.remove_instance(k, int(f_r))
                for f_n in inc[len(dec):]:
                    self.add_instance(k, int(f_n))
            else:
                assert len(dec) == len(inc)
        for k in range(self.N):
            for f in range(self.F):
                if self.cnt[f, k] == 0 and self.queue[k][f]:
                    orphans = list(self.queue[k][f])
                    self.queue[k][f].clear()
                    for run in orphans:
                        self._reroute(run)
        self.n_placements_applied += 1
        self._fst_cache = {}

    # ------------------------------------------------------------------------------------------------ results
    def results(self):
        self._acct()
        cap_t = max(self.duration - self.warmup, 1e-9)
        ms = np.array(self.makespans)
        # censored mean: a request that has not finished when the run stops counts with its age (a LOWER bound of its makespan)
        cens = np.concatenate([ms, [self.t_end_effective() - t for t in self.win.values()]]) if self.win else ms
        return dict(avg_makespan=float(ms.mean()) if len(ms) else float("nan"), n_completed=int(len(ms)),
                    avg_makespan_censored=float(cens.mean()) if len(cens) else float("nan"),
                    n_arrived=self.n_arrived, n_unfinished=int(self.n_unfinished),
                    utilization=float(self.busy_time / (self.sc.ecc.sum() * cap_t)),
                    cold_starts=int(self.cold_starts), cold_starts_total=int(self.cold_starts_total),
                    n_adjust=self.n_adjust, n_moved=self.n_moved, n_rerouted=self.n_rerouted,
                    **self._extended_results(ms, cap_t))

    def _extended_results(self, ms, cap_t):
        pct = (lambda q: float(np.percentile(ms, q))) if len(ms) else (lambda q: float("nan"))
        slots = self.sc.ecc.sum() * cap_t
        q = lambda a, p: float(np.percentile(a, p)) if len(a) else float("nan")
        return dict(p50_makespan=pct(50), p95_makespan=pct(95), p99_makespan=pct(99),
                    slo_goodput=float(self.n_slo_ok / cap_t), slo_ok=int(self.n_slo_ok), n_rejected=int(self.n_rejected),
                    n_noop_adjust=int(self.n_noop_adjust), n_retry_rounds=int(self.n_retry_rounds), n_parked=int(self.n_parked), n_placements_applied=int(self.n_placements_applied),
                    warm_idle_slot_s=float(max(0.0, slots - self.busy_time - self.cold_slot_s)),
                    provisioned_slot_s=float(self.inst_s), mean_containers=float(self.inst_s / cap_t),
                    warm_idle_provisioned_s=float(max(0.0, self.inst_s - self.busy_time - self.cold_slot_s)),
                    n_add_blocked=int(self.n_add_blocked),
                    adjust_ms_p95=q(self.adjust_ms, 95), plan_ms_p95=q(self.plan_ms, 95),
                    plan_ms_mean=float(np.mean(self.plan_ms)) if self.plan_ms else float("nan"),
                    event_hash=self._hash.hexdigest())

    def check_invariants(self):
        """Capacity (D-7), storage and bookkeeping invariants; raises AssertionError."""
        for k in range(self.N):
            total = sum(len(self.inst[k][f]) for f in range(self.F))
            if self.elastic:
                assert total <= self.sc.ecc[k], f"node {k}: {total} instances > ecc {self.sc.ecc[k]}"
            else:
                assert total == self.sc.ecc[k], f"node {k}: {total} instances != ecc {self.sc.ecc[k]} (D-7)"
            assert self.storage_used[k] <= self.esc[k] + 1e-6, f"node {k}: storage overflow"
            for f in range(self.F):
                n_final = sum(1 for i in self.inst[k][f] if i.swap_to is None) + \
                    sum(1 for g in range(self.F) for i in self.inst[k][g] if i.swap_to == f)
                assert n_final == self.cnt[f, k], f"cnt mismatch at (f={f}, k={k})"
