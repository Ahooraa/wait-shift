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
    __slots__ = ("id", "wf", "origin", "t_arr", "plan", "pending", "left", "t_done", "held")


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
                 move_cost=1.0, elastic=False, dispatcher=None, trace=False, queue_priority=None, join_bind=False):
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
        # heterogeneous container sizes (2026-11-02): sc.fw not all ones. A node then holds any containers whose weights sum to at
        # most ecc_k, and cannot in general be filled exactly, so D-7 ("every slot always holds an instance") becomes "no further
        # container of the lightest function fits"; layouts are applied as plain removals and additions, not 1-for-1 swaps.
        # With fw all ones nothing below changes.
        self.hetero = not bool(np.allclose(sc.fw, 1.0))
        # dispatcher: callable(sim, request) -> {task: node} or None; None = DFPS's graph pattern matching (see dfps/dispatchers.py)
        self.dispatcher = dispatcher
        # join_bind (2026-11-03): a join task (>= 2 parents) is bound when its LAST parent finishes; the earlier parents' output states
        # stay on the nodes that produced them until then. Its node is re-chosen with the queues of that moment (greedy EFT score: summed
        # input transfer from the parents' actual nodes + FST), among nodes holding the function with room for its inputs; the arrival-time
        # plan and its storage reservation are the fallback (the reservation moves only if the new node has room). Simplification: held
        # states stay accounted on the planned node's storage until binding. False = all tasks bound at arrival, the original behaviour.
        self.join_bind = join_bind
        self.n_join_bound = self.n_join_rebound = 0
        self.trace = {"tasks": [], "reqs": []} if trace else None      # per-task trace of in-window requests (dfps/diagnostics.py)
        self._snap_due = []                                            # trace-only snapshot timers (trace_snap, 2026-11-04); empty = off
        self.soj_log = {}                                              # workflow id -> sojourn of every completed request (online per-type median)
        # queue_priority (2026-10-28): callable(sim, run) -> sortable key; an idle instance starts the waiting run with the largest
        # key (ties: the oldest). None = FIFO, the original behaviour. See dfps/dispatch_priority.py.
        self.queue_priority = queue_priority
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
        self.q_active, self.inst_active = set(), set()               # MV-4 (9 Nov 2026): keys of queues / instance lists that may be non-empty; an entry is added on append and dropped lazily by the scan
        self.cnt = np.zeros((self.F, self.N), dtype=int)
        self.storage_used = np.zeros(self.N)
        self.req_count = np.zeros((self.F, self.N), dtype=int)       # requests per (f,k) in the past interval
        self.lam_w, self.lam_dt = int(lam_window), lam_update
        self.buckets = np.zeros((self.lam_w, self.F, self.N))
        self.lam = np.zeros((self.F, self.N))
        self._fst_cache, self.waiting, self.active = {}, deque(), 0
        for k in range(self.N):
            if float((X[k] * sc.fw).sum()) > sc.ecc[k] + 1e-9:
                raise ValueError(f"placement exceeds ecc_{k}")
            for f in range(self.F):
                for _ in range(int(X[k, f])):
                    self.inst[k][f].append(Instance(f, k, IDLE))
                    self.inst_active.add(k * self.F + f)
                self.cnt[f, k] = int(X[k, f])
        self._n_inst, self._t_acct, self.inst_s, self.n_add_blocked = int(np.asarray(X).sum()), 0.0, 0.0, 0
        # heterogeneous sizes (2026-11-02): containers already in the final count (cnt) that wait for room on their node, because
        # the capacity they need is still held by a busy instance marked for removal or conversion. Started, in order, as soon as
        # room frees up. Always empty with equal sizes.
        self.pending_add = [[] for _ in range(self.N)]
        self.n_add_deferred = 0
        if not allow_empty and (self.cnt.sum(axis=1) == 0).any():   # allow_empty: on-demand baselines (Heu, RL) start empty
            raise ValueError("initial placement leaves a function without any instance")
        # metrics (measured in [warmup, duration], D: makespan of requests that ARRIVE in the window)
        self.makespans, self.n_arrived, self.cold_starts, self.busy_time, self.n_unfinished = [], 0, 0, 0.0, 0
        self.cold_starts_total, self.n_rerouted, self.n_adjust, self.n_moved = 0, 0, 0, 0
        # reconfiguration cost, dim. 1 (problem-scope.md S6, "bytes re-transferred"): input-state MB moved by relocate()
        # (every request move, whether a deliberate Sol.aet move or a forced D-6/A-25 reroute -- both funnel through it).
        # Windowed the same way as cold_starts/cold_starts_total (dim. 2): _mb is [warmup, duration] only, _total is all-time.
        self.mb_relocated, self.mb_relocated_total = 0.0, 0.0
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

    def _exec_s(self, run):
        """Execution time of one run. A sampler with a `for_run(function, request id, task)` method draws it from the seed and the run's identity
        (common random numbers: every method then sees the same duration for the same task of the same request, whatever the order in which
        the methods start their tasks); any other sampler is called as exec_sampler(function, rng) from the shared stream, as before."""
        mu = self.exec_time[run.f]
        if self.exec_sampler is None:
            return float(self.rng.exponential(mu))
        if hasattr(self.exec_sampler, "for_run"):
            return float(self.exec_sampler.for_run(run.f, run.req.id, run.task))
        return float(self.exec_sampler(run.f, self.rng))

    def _stt(self, size_mb, k, k2):
        """Transfer time of one state from node k to node k2, as used by every event that schedules a state move (Eq. 1-2). A hook:
        the model here; testbed/livesim.py overrides it to learn which state moves where and sends the bytes through real agents."""
        return self.net.stt(size_mb, k, k2)

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
            if self._snap_due and self._snap_due[0][0] <= t:      # trace only: snapshots due before this event (state as of their due time)
                self._snap_fire(t)
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

    def all_availability(self):
        """The lists of `live_availability` for every (f, k) at once, one scan of the instances (7 Nov 2026, MV-3): same entries in the same order."""
        out, ex, cs, now = {}, self.exec_time, self.cold_start, self.now
        for k in range(self.N):
            for lst in self.inst[k]:
                for ins in lst:
                    if ins.swap_to is not None:
                        f = ins.swap_to
                        e = (ex[ins.f] + cs[f], COLD)
                    else:
                        f = ins.f
                        if ins.state == IDLE:
                            e = (0.0, IDLE)
                        elif ins.state == COLD:
                            e = (max(0.0, ins.warm_at - now), COLD)
                        else:
                            e = (ex[f], BUSY)
                    out.setdefault((f, k), []).append(e)
            if self.hetero and self.pending_add[k]:
                leaving = [ex[i.f] for lst in self.inst[k] for i in lst if i.swap_to is not None]
                first = min(leaving) if leaving else 0.0
                for f in set(self.pending_add[k]):
                    out.setdefault((f, k), []).extend([(first + cs[f], COLD)] * self.pending_add[k].count(f))
        return out

    def availability_flat(self):
        """The values of `all_availability` as two flat lists (f * N + k, availability), scanning only the non-empty instance lists (MV-4, 9 Nov 2026)."""
        qi, vi, ex, cs, now, N, F, inst = [], [], self.exec_time, self.cold_start, self.now, self.N, self.F, self.inst
        empty = []
        for key in self.inst_active:
            k, g = divmod(key, F)
            lst = inst[k][g]
            if not lst:
                empty.append(key)
                continue
            for ins in lst:
                if ins.swap_to is not None:
                    f = ins.swap_to
                    v = ex[ins.f] + cs[f]
                else:
                    f = ins.f
                    v = 0.0 if ins.state == IDLE else (max(0.0, ins.warm_at - now) if ins.state == COLD else ex[f])
                qi.append(f * N + k)
                vi.append(v)
        self.inst_active.difference_update(empty)
        if self.hetero:
            for k in range(N):
                if self.pending_add[k]:
                    leaving = [ex[i.f] for lst in inst[k] for i in lst if i.swap_to is not None]
                    first = min(leaving) if leaving else 0.0
                    for f in set(self.pending_add[k]):
                        c = self.pending_add[k].count(f)
                        qi.extend([f * N + k] * c)
                        vi.extend([first + cs[f]] * c)
        return qi, vi

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
        if self.hetero and f in self.pending_add[k]:              # waiting for room: starts when the first instance marked for
            leaving = [self.exec_time[i.f] for g in range(self.F) for i in self.inst[k][g] if i.swap_to is not None]
            first = min(leaving) if leaving else 0.0              # removal or conversion ends (mean residual), then cold-starts
            out += [(first + self.cold_start[f], COLD)] * self.pending_add[k].count(f)
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
        r.held = {}
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
        if self.trace is not None and self.in_window(r.t_arr):   # trace only: the start-wait estimate (FST) of every chosen node, at planning
            self.trace.setdefault("pred", []).append((r.id, self.now, [float(self.fst_vec(wf.ft[t])[r.plan[t]]) for t in range(wf.n)]))
        if self.trace is not None and getattr(self, "trace_cf", False) and self.in_window(r.t_arr):   # trace only: what greedy EFT would have planned now
            from . import dispatchers as _D
            cf = _D.greedy_eft(self, r)
            self.trace.setdefault("cf", []).append((r.id, None if cf is None else [int(cf[t]) for t in range(wf.n)]))
        for t in range(wf.n):                                    # A-23: reserve the input states' storage at planning
            self.storage_used[r.plan[t]] += wf.input_total(t)
        for root in wf.roots:
            self._at(self.now + self._stt(wf.input_size, r.origin, r.plan[root]), "state", r, root)
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
        if getattr(self, "trace_live", False):                    # trace only: the run is no longer in transit
            kk = self.__dict__.get("_infl_key", {}).pop((run.req.id, run.task), None)
            if kk is not None:
                self._infl[(f, kk)] -= 1
        if self.cnt[f, k] == 0:                                   # D-6 / A-25: no instance here any more -> reroute by AET
            self._reroute(run)
            return
        run.node, run.t_enq = k, self.now
        first = run.t_first is None
        if first:
            run.t_first = self.now
        self.queue[k][f].append(run)
        self.q_active.add(f * self.N + k)
        self.buckets[0, f, k] += 1
        self.req_count[f, k] += 1
        if first and self.trace is not None and getattr(self, "trace_snap", False):
            self._snap_enqueue(run)
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
        delay = self.move_cost * sum(self._stt(s, k_old, k_new) for s in run.sizes)
        if self.trace is not None and self.in_window(run.req.t_arr):      # trace only: per-move cost, nothing here changes the dynamics
            self.trace.setdefault("moves", []).append((run.req.id, run.task, self.now, delay, run.t_first))
        self.storage_used[k_old] -= run.total
        self.storage_used[k_new] += run.total
        run.node = k_new
        if getattr(self, "trace_live", False):                    # trace only: a relocated run is in transit to k_new until it enqueues
            self.__dict__.setdefault("_infl_key", {})[(run.req.id, run.task)] = k_new
            i_ = self.__dict__.setdefault("_infl", {})
            i_[(run.f, k_new)] = i_.get((run.f, k_new), 0) + 1
        run.n_moves += 1
        self.n_moved += 1
        self.mb_relocated_total += run.total
        if self.in_window(self.now):
            self.mb_relocated += run.total
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
                if self.queue_priority is None:
                    self._start(ins, q.popleft())
                else:
                    run = max(q, key=lambda r: self.queue_priority(self, r))   # max() keeps the first (oldest) among ties
                    self.n_priority_overrides = getattr(self, "n_priority_overrides", 0) + (run is not q[0])
                    if hasattr(self.queue_priority, "won"):
                        self.queue_priority.won(self, run)
                    q.remove(run)
                    self._start(ins, run)

    def _start(self, ins, run):
        s = self._exec_s(run)
        ins.state, ins.run, ins.busy_until = BUSY, run, self.now + s
        run.t_start = self.now
        if self.trace is not None and getattr(self, "trace_snap", False):
            self.__dict__.setdefault("_snap_started", set()).add((run.req.id, run.task))
        if self.queue_priority is not None and hasattr(self.queue_priority, "on_start"):
            self.queue_priority.on_start(self, run)
        lo, hi = max(self.now, self.warmup), min(self.now + s, self.duration)
        if hi > lo:
            self.busy_time += hi - lo
        self._at(self.now + s, "done", ins, ins.token)

    # ---- snapshot stability (trace only, 2026-11-04): does the best node move between binding and the mover's passes? -------------------
    def _snap_scores(self, r, ch, h, run):
        """Live AET of placing task ch of request r on every feasible node now: input transfer from the parents' nodes (the router's
        counterfactual "bind it now") + service estimate (own queue position if it already waits there, else the queue length) + 0.5 x
        output transfer to the children's planned nodes. Reads state only."""
        from .solution import Sol
        wf = r.wf
        f, tot = wf.ft[ch], wf.input_total(ch)
        sol = Sol(self)
        res = int(r.plan[ch]) if run is None else int(run.node)       # node holding the task's storage reservation
        sc = {}
        for k2 in np.flatnonzero(self.cnt[f]):
            k2 = int(k2)
            if self.esc[k2] - self.storage_used[k2] + (tot if k2 == res else 0.0) < tot - 1e-9:
                continue
            q = self.queue[k2][f]
            ahead = q.index(run) if (run is not None and run.node == k2 and run in q) else len(q)
            sc[k2] = (sum(self.net.stt(s_, sk, k2) for sk, s_ in h) + sol.service_estimate(f, k2, ahead)
                      + 0.5 * sum(self.net.stt(wf.ss[(ch, c)], k2, r.plan[c]) for c in wf.children[ch]))
        return sc

    @staticmethod
    def _snap_pick(sc, b0):
        if not sc:
            return None, None
        b = min(sc, key=sc.get)
        return b, (sc.get(b0, float("inf")) - sc[b]) if b0 is not None else None

    def _snap_bind(self, r, ch, k, size):
        h = self.__dict__.setdefault("_snap_par", {}).setdefault((r.id, ch), [])
        h.append((k, size))
        if len(h) < len(r.wf.parents[ch]):
            return
        del self._snap_par[(r.id, ch)]
        if not self.in_window(r.t_arr) or r.id % 2:                      # deterministic half sample of in-window requests (cost)
            return
        b0, _ = self._snap_pick(self._snap_scores(r, ch, h, None), None)
        if b0 is not None:
            self.__dict__.setdefault("_snap", {})[(r.id, ch)] = dict(r=r, h=h, t0=self.now, b0=b0, run=None, rec=[])

    def _snap_enqueue(self, run):
        d = self.__dict__.get("_snap", {}).get((run.req.id, run.task))
        if d is None:
            return
        d["run"], d["te"] = run, self.now
        d["rec"].append(self._snap_pick(self._snap_scores(run.req, run.task, d["h"], run), d["b0"]))
        self._snap_seq = getattr(self, "_snap_seq", 0) + 1
        heapq.heappush(self._snap_due, (self.now + 2.0, self._snap_seq, (run.req.id, run.task), 2))
        self._snap_seq += 1
        heapq.heappush(self._snap_due, (self.now + 4.0, self._snap_seq, (run.req.id, run.task), 4))

    def _snap_fire(self, t):
        started = self.__dict__.setdefault("_snap_started", set())
        while self._snap_due and self._snap_due[0][0] <= t:
            _, _, key, lag = heapq.heappop(self._snap_due)
            d = self._snap.get(key)
            if d is None:
                continue
            if key in started:
                d["rec"].append((None, None))
            else:
                d["rec"].append(self._snap_pick(self._snap_scores(d["r"], key[1], d["h"], d["run"]), d["b0"]))
            if lag == 4:
                (b1, g1), (b2, g2), (b4, g4) = d["rec"]
                self.trace.setdefault("snap", []).append((key[0], key[1], int(d["r"].plan[key[1]]), round(d["t0"], 3), d["b0"],
                                                          round(d["te"], 3), b1, g1, b2, g2, b4, g4))
                del self._snap[key]

    def _live_probe(self, r, ch, k, size):
        """Trace only (2026-11-03, live-state replay): when the last parent of `ch` finishes, which node would a router that scores with the
        mover's AET on the LIVE state (input transfer from the parents' nodes + service estimate at the current queue length + 0.5 x output
        transfer to the children's planned nodes) pick? Reads state, writes only the trace; the event hash must be unchanged."""
        h = self.__dict__.setdefault("_tl", {}).setdefault((r.id, ch), [])
        h.append((k, size))
        wf = r.wf
        if len(h) < len(wf.parents[ch]):
            return
        del self._tl[(r.id, ch)]
        infl = self.__dict__.setdefault("_infl", {})                 # (f, node) -> tasks bound or relocated there, not yet in its queue
        if self.in_window(r.t_arr):
            from .solution import Sol
            sol, f, tot = Sol(self), wf.ft[ch], wf.input_total(ch)
            best, best2, a_plan, sq, si = None, None, float("inf"), 0, 0
            for k2 in np.flatnonzero(self.cnt[f]):
                k2 = int(k2)
                if self.esc[k2] - self.storage_used[k2] + (tot if k2 == r.plan[ch] else 0.0) < tot - 1e-9:
                    continue
                nq, ni = len(self.queue[k2][f]), infl.get((f, k2), 0)
                sq, si = sq + nq, si + ni
                base = sum(self.net.stt(s, sk, k2) for sk, s in h) + 0.5 * sum(self.net.stt(wf.ss[(ch, c)], k2, r.plan[c]) for c in wf.children[ch])
                a = base + sol.service_estimate(f, k2, nq)
                a2 = base + sol.service_estimate(f, k2, nq + ni)       # in-transit tasks counted as already queued
                if k2 == r.plan[ch]:
                    a_plan = a
                if best is None or a < best[0]:
                    best = (a, k2)
                if best2 is None or a2 < best2[0]:
                    best2 = (a2, k2)
            self.trace.setdefault("live", []).append((r.id, ch, self.now, int(r.plan[ch]), None if best is None else best[1],
                                                      None if best is None else float(best[0]), float(a_plan),
                                                      None if best2 is None else best2[1], sq, si,
                                                      0 if best is None else infl.get((wf.ft[ch], best[1]), 0)))
        self.__dict__.setdefault("_infl_key", {})[(r.id, ch)] = int(r.plan[ch])
        infl[(wf.ft[ch], int(r.plan[ch]))] = infl.get((wf.ft[ch], int(r.plan[ch])), 0) + 1

    def _ev_done(self, ins, token, c):
        run = ins.run
        r, wf, t, k = run.req, run.req.wf, run.task, ins.node
        ins.run, ins.state = None, IDLE
        self.storage_used[k] -= run.total                          # consumed input states are removed (p.5)
        for ch in wf.children[t]:
            if self.trace is not None and getattr(self, "trace_live", False):
                self._live_probe(r, ch, k, wf.ss[(t, ch)])
            if self.trace is not None and getattr(self, "trace_snap", False):
                self._snap_bind(r, ch, k, wf.ss[(t, ch)])
            if self.join_bind and len(wf.parents[ch]) >= 2:
                h = r.held.setdefault(ch, [])
                h.append((k, wf.ss[(t, ch)]))
                if len(h) == len(wf.parents[ch]):
                    self._bind_join(r, ch, h)
            else:
                self._at(self.now + self._stt(wf.ss[(t, ch)], k, r.plan[ch]), "state", r, ch)
        if self.trace is not None and self.in_window(r.t_arr):
            self.trace["tasks"].append((r.id, wf.id, t, r.plan[t], k, run.t_first, run.t_start, self.now, run.n_moves))
        r.left -= 1
        if r.left == 0:
            r.t_done = self.now
            self.soj_log.setdefault(wf.id, []).append(self.now - r.t_arr)
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

    def _bind_join(self, r, t, held):
        """join_bind: all parents of join task t are done; choose its node now and send the held input states there."""
        wf, f, k0 = r.wf, r.wf.ft[t], r.plan[t]
        total = wf.input_total(t)
        room = self.esc - self.storage_used
        room[k0] += total                                         # its own reservation sits on the planned node
        ks = np.flatnonzero((self.cnt[f] > 0) & (room >= total - 1e-9))
        k = k0
        if ks.size:
            bw, epd, h = self.net.bw, self.net.epd, self.net.h
            score = sum(h[s, ks] * (epd + size / bw) for s, size in held) + self.fst_vec(f)[ks]
            k = int(ks[int(np.argmin(score))])
        self.n_join_bound += 1
        if k != k0:
            self.n_join_rebound += 1
            self.storage_used[k0] -= total
            self.storage_used[k] += total
            r.plan[t] = k
        for s, size in held:
            self._at(self.now + self._stt(size, s, k), "state", r, t)
        del r.held[t]

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
        """The instance becomes a cold instance of function g (cold-start delay of g). Heterogeneous sizes: if the new container
        does not fit next to what the node still holds (other busy instances waiting to convert), the old one is removed and the
        new one waits in pending_add until room frees up, so live capacity is never exceeded."""
        k = ins.node
        if self.hetero and self.weighted_used(k) - self.sc.fw[ins.f] + self.sc.fw[g] > self.sc.ecc[k] + 1e-9:
            ins.swap_to = -1                                       # its count has already moved to g
            self.pending_add[k].append(int(g))
            self.n_add_deferred += 1
            self._destroy(ins)                                     # frees its room and starts what now fits
            return
        self.inst[ins.node][ins.f].remove(ins)
        ins.f, ins.swap_to, ins.state = g, None, COLD
        ins.warm_at = self.now + self.cold_start[g]
        ins.token += 1
        self.inst[ins.node][g].append(ins)
        self.inst_active.add(ins.node * self.F + g)
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

    def weighted_used(self, k):
        """Capacity used on node k, in sc.fw units (== n_slots_used when fw is all-ones)."""
        return sum(len(self.inst[k][g]) * self.sc.fw[g] for g in range(self.F))

    def add_instance(self, k, f, defer=False):
        """Start a new (cold) instance of f in a free slot of node k. Returns False if the node has no free slot (a slot is
        occupied until a busy instance marked for removal has finished its run). defer=True (heterogeneous sizes only): the
        container joins the final count now and starts as soon as the room is free (pending_add), instead of being dropped."""
        if self.weighted_used(k) + self.sc.fw[f] > self.sc.ecc[k] + 1e-9:
            if defer and self.hetero:
                self.pending_add[k].append(int(f))
                self.cnt[f, k] += 1
                self.n_add_deferred += 1
                self._fst_cache = {}
                return True
            self.n_add_blocked += 1
            return False
        self.cnt[f, k] += 1
        self._new_instance(k, f)
        return True

    def _new_instance(self, k, f):
        """A new cold instance of f on node k (its count is already in cnt)."""
        self._acct()
        ins = Instance(f, k, COLD, warm_at=self.now + self.cold_start[f])
        self.inst[k][f].append(ins)
        self.inst_active.add(k * self.F + f)
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
        if self.hetero and f in self.pending_add[k]:              # a container that never started: cancel it
            self.pending_add[k].remove(int(f))
            self.cnt[f, k] -= 1
            self._fst_cache = {}
            return
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
        if self.hetero and self.pending_add[ins.node]:
            self._start_pending(ins.node)

    def _start_pending(self, k):
        """Start the waiting containers of node k that now fit, in the order they were requested (heterogeneous sizes)."""
        for f in list(self.pending_add[k]):
            if self.weighted_used(k) + self.sc.fw[f] <= self.sc.ecc[k] + 1e-9:
                self.pending_add[k].remove(f)
                self._new_instance(k, f)

    # ------------------------------------------------------------------------------------------------ replacement
    def swap_instance(self, k, f_r, f_n):
        """Replace one instance of f_r on node k by a new (cold) instance of f_n (Alg.1 l.5-6). Preference: idle, then
        cold, then busy (the busy one finishes its run first, D-5)."""
        if self.hetero and f_r in self.pending_add[k]:          # f_r has not started yet: wait for room as f_n instead
            self.pending_add[k][self.pending_add[k].index(f_r)] = int(f_n)
            self.cnt[f_r, k] -= 1
            self.cnt[f_n, k] += 1
            self._start_pending(k)
            self._fst_cache = {}
            return
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
        used = X.dot(self.sc.fw)                                   # weighted row sums (== X.sum(axis=1) when fw is all-ones)
        if self.elastic or self.hetero:                           # slots may stay empty: row sums only have to fit
            assert (used <= self.sc.ecc + 1e-9).all() and (X.sum(axis=0) >= 1).all()
        else:
            assert (np.abs(used - self.sc.ecc) <= 1e-9).all() and (X.sum(axis=0) >= 1).all()
        for k in range(self.N):
            d = X[k] - self.cnt[:, k]
            if not d.any():
                continue
            dec = [f for f in np.flatnonzero(d < 0) for _ in range(int(-d[f]))]
            inc = [f for f in np.flatnonzero(d > 0) for _ in range(int(d[f]))]
            if self.hetero:                                       # a swap changes the node's weight: removals first, then additions
                for f_r in dec:
                    self.remove_instance(k, int(f_r))
                for f_n in inc:
                    self.add_instance(k, int(f_n), defer=True)
                continue
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
                    n_join_bound=self.n_join_bound, n_join_rebound=self.n_join_rebound,
                    # reconfiguration cost (problem-scope.md S6): a 2D vector reported alongside P99, never optimised
                    # directly -- dim. 1 is mb_relocated (this), dim. 2 is cold_starts (above).
                    mb_relocated=float(self.mb_relocated), mb_relocated_total=float(self.mb_relocated_total),
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
                    n_add_blocked=int(self.n_add_blocked), n_add_deferred=int(self.n_add_deferred),
                    adjust_ms_p95=q(self.adjust_ms, 95), plan_ms_p95=q(self.plan_ms, 95),
                    plan_ms_mean=float(np.mean(self.plan_ms)) if self.plan_ms else float("nan"),
                    event_hash=self._hash.hexdigest(),
                    **({"mover_impl": self.adjuster.mover_impl} if getattr(self.adjuster, "mover_impl", None) else {}),
                    **({"mover_pass": self.adjuster.mover_pass} if getattr(self.adjuster, "mover_pass", None) else {}),
                    **({"place_impl": self.adjuster.place_impl} if getattr(self.adjuster, "place_impl", None) else {}))

    def check_invariants(self):
        """Capacity (D-7), storage and bookkeeping invariants; raises AssertionError."""
        for k in range(self.N):
            total = self.weighted_used(k)
            if self.hetero:                                       # final (cnt-based) weight fits; in-flight conversions may differ
                final = float(self.cnt[:, k] @ self.sc.fw)
                assert final <= self.sc.ecc[k] + 1e-9, f"node {k}: final weighted capacity {final} > ecc {self.sc.ecc[k]}"
                assert total <= self.sc.ecc[k] + 1e-9, f"node {k}: live weighted capacity {total} > ecc {self.sc.ecc[k]}"
            elif self.elastic:
                assert total <= self.sc.ecc[k] + 1e-9, f"node {k}: {total} weighted capacity > ecc {self.sc.ecc[k]}"
            else:
                assert abs(total - self.sc.ecc[k]) <= 1e-9, f"node {k}: {total} weighted capacity != ecc {self.sc.ecc[k]} (D-7)"
            assert self.storage_used[k] <= self.esc[k] + 1e-6, f"node {k}: storage overflow"
            for f in range(self.F):
                n_final = sum(1 for i in self.inst[k][f] if i.swap_to is None) + \
                    sum(1 for g in range(self.F) for i in self.inst[k][g] if i.swap_to == f) + self.pending_add[k].count(f)
                assert n_final == self.cnt[f, k], f"cnt mismatch at (f={f}, k={k})"
