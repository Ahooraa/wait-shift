"""On-demand execution model shared by the two baselines Heu [18] and RL [28] (BASELINES_SPEC.md).

DFPS p.9-11: Heu and RL "do not rely on an initial placement"; they place/schedule requests individually as they arrive, so
containers are created on demand (cold start of the function) and idle containers are recycled to make room ("aggressive
removal of idle instances", p.11). Both baselines run in THIS model, on the same scenario, network, capacities, execution-time
draws and metrics as SR/SG/DFPS; only the node-selection rule differs (`policy`).

Container model (identical for both baselines; AB-C1..AB-C4):
* node e_k has ecc_k container slots, initially empty (no instance of any function);
* a ready task needs a container of its function on its node: (1) an idle container of that function (warm, no cold start),
  else (2) a free slot -> new container, cold start of the function, else (3) the least-recently-used idle container of another
  function is recycled and replaced by a new one (cold start), else (4) the task waits in the node's FIFO queue;
* a container serves one task at a time and becomes idle when it finishes (kept warm until recycled by (3));
* storage, state transfers (Eq.1-2, parallel arrival of the input states), and metrics as in `Sim`.
Mode 'plan' (Heu): the policy returns the node of every task when the workflow request arrives.
Mode 'ready' (RL): the policy picks the node of a task when it becomes ready (all parents finished), one task at a time,
without knowledge of the workflow (DFPS p.10: RL "lacks awareness of workflow structure")."""
from __future__ import annotations

from collections import deque

import numpy as np

from .sim import Instance, Req, Run, Sim
from .solution import BUSY, COLD, IDLE


class OInstance(Instance):
    __slots__ = ("last",)

    def __init__(self, f, node, state, warm_at=0.0):
        super().__init__(f, node, state, warm_at)
        self.last = 0.0


class OReq(Req):
    __slots__ = ("rdy", "tready", "dec")


class ORun(Run):
    __slots__ = ("t_ready", "dec")


class OnDemandSim(Sim):
    def __init__(self, sc, policy, seed=0, duration=None, warmup=30.0, drain_factor=20.0, debug=False, keep_warm=None, exec_mult=None,
                 X0=None):
        # X0 (2026-11-01, user question: is the empty-slot start part of why Heu/RL show so many cold starts?): optional [N, F]
        # placement of WARM idle containers to start from, e.g. the same NSGA-II layout B* and ours start from (P["X0"] in
        # results/d1_headroom/*.prep.pkl). None = the paper's own model, every slot empty (DFPS p.9-11, the default above).
        # This only changes the t=0 state; dispatch, recycling and cold-start accounting afterwards are unchanged.
        N, F = sc.network.ne, len(sc.functions)
        super().__init__(sc, np.zeros((N, F), dtype=int), adjuster=None, seed=seed, duration=duration, warmup=warmup,
                         drain_factor=drain_factor, debug=debug, allow_empty=True)
        self.policy, self.mode = policy, policy.mode
        self.ecc = sc.ecc.astype(int)
        self.idle = np.zeros((F, N), dtype=int)       # idle containers of f on k
        self.qcnt = np.zeros((F, N), dtype=int)       # queued runs of f on k
        self.tot = np.zeros(N, dtype=int)             # containers on k (any state)
        self.occ = np.zeros(N, dtype=int)             # containers busy or cold-starting for a bound task
        self.nq = [deque() for _ in range(N)]
        self.wait_tasks = deque()
        self.n_recycled = 0
        self.X0 = None if X0 is None else np.asarray(X0, dtype=int)
        if self.X0 is not None:
            assert self.X0.shape == (N, F), f"X0 shape {self.X0.shape} != ({N}, {F})"
            for k in range(N):
                if (float(self.X0[k] @ sc.fw) > self.ecc[k] + 1e-9) if self.hetero else (int(self.X0[k].sum()) > self.ecc[k]):
                    raise ValueError(f"X0 exceeds ecc_{k}")
                for f in range(F):
                    for _ in range(int(self.X0[k, f])):
                        ins = OInstance(f, k, IDLE)        # warm from t=0: not an _acquire() cold start, not counted anywhere
                        self.inst[k][f].append(ins)
                        self.idle[f, k] += 1
                        self.tot[k] += 1
                    self.cnt[f, k] = int(self.X0[k, f])
        # keep_warm (baseline diagnostic, 2026-10-18): None = an idle container stays warm until its slot is recycled (AB-C1..C4,
        # the default so far); 0 = released as soon as its task finishes (no reuse; AB-H5's proposed default "new instance per
        # request, released after use"); t > 0 = removed after t seconds idle (MOSEC-style idle timeout, AB-R4).
        self.keep_warm = keep_warm
        # evict_score (look-ahead cheater only): array over functions; when set, recycling evicts the idle container whose
        # function has the lowest score (e.g. least upcoming demand per container) instead of the least recently used one
        self.evict_score = None
        # recycle_limit (look-ahead cheater only): max containers recycled per node per second-of-simulated-time budget; None = no
        # limit (RL as published). When exhausted, a task without a warm container of its function waits in the node queue.
        self.recycle_budget = None
        # exec_mult (baseline diagnostic): {function id: N} multiplies the function's execution time, e.g. Xu et al.'s N_l
        # invocations of a function per request (Sec. 6.1: 1-5; processing delay proportional to N_l, Eq. 1). None = off.
        self.exec_mult = exec_mult
        if exec_mult:
            mu = self.exec_time
            self.exec_sampler = lambda f, rng: float(rng.exponential(mu[f])) * exec_mult.get(int(f), 1)
        self.n_expired = 0
        policy.attach(self)

    # --------------------------------------------------------------------------------------------- arrivals
    def _ev_arrive(self, wid, origin, c):
        wf = self.sc.workflows[wid]
        r = OReq()
        r.id, r.wf, r.origin, r.t_arr, r.t_done = next(self.rid), wf, origin, self.now, None
        r.pending = [1 if not wf.parents[t] else len(wf.parents[t]) for t in range(wf.n)]
        r.rdy = [len(wf.parents[t]) for t in range(wf.n)]
        r.tready = [self.now] * wf.n
        r.dec = {}
        r.left = wf.n
        r.plan = [None] * wf.n
        self.active += 1
        if self.in_window(self.now):
            self.n_arrived += 1
            self.win[r.id] = self.now
        if not self._start_request(r):
            self.waiting.append(r)

    def _start_request(self, r):
        wf = r.wf
        if self.mode == "plan":
            nodes = self.policy.plan(self, r)
            if nodes is None:
                return False
            r.plan = list(nodes)
            for t in range(wf.n):                                   # A-23: reserve the input states' storage at planning
                self.storage_used[r.plan[t]] += wf.input_total(t)
            for root in wf.roots:
                self._at(self.now + self._stt(wf.input_size, r.origin, r.plan[root]), "state", r, root)
            return True
        for root in wf.roots:                                        # mode 'ready': roots are ready at arrival
            if not self._decide(r, root):
                self.wait_tasks.append((r, root))
        return True

    def _decide(self, r, t):
        wf = r.wf
        k = self.policy.choose(self, r, t)
        if k is None:
            return False
        r.plan[t] = int(k)
        self.storage_used[k] += wf.input_total(t)
        if not wf.parents[t]:
            srcs = [(r.origin, wf.input_size)]
        else:
            srcs = [(r.plan[p], wf.ss[(p, t)]) for p in wf.parents[t]]
        for node, size in srcs:
            self._at(self.now + self._stt(size, node, k), "state", r, t)
        return True

    def _retry_waiting(self):
        for _ in range(len(self.waiting)):
            r = self.waiting.popleft()
            if not self._start_request(r):
                self.waiting.append(r)
        for _ in range(len(self.wait_tasks)):
            r, t = self.wait_tasks.popleft()
            if not self._decide(r, t):
                self.wait_tasks.append((r, t))

    # --------------------------------------------------------------------------------------------- execution
    def _ev_state(self, r, task, c):
        r.pending[task] -= 1
        if r.pending[task] == 0:
            run = ORun(r, task, r.plan[task])
            run.t_ready, run.dec = r.tready[task], r.dec.get(task)
            run.t_enq = self.now
            self.nq[run.node].append(run)
            self.qcnt[run.f, run.node] += 1
            self._try_node(run.node)

    def _try_node(self, k):
        q = self.nq[k]
        avail = len(q) if self.hetero else self.ecc[k] - self.occ[k]   # unequal sizes: _acquire decides whether a run fits
        if not q or avail <= 0:
            return
        for run in list(q):
            if avail <= 0:
                break
            if self.hetero and self.idle[:, k].sum() == 0 and \
                    self.ecc[k] - float(self.cnt[:, k] @ self.sc.fw) < self.sc.fw.min() - 1e-9:
                break                                               # nothing idle to use or recycle and no room for even the lightest
            if self._acquire(k, run) is False:                      # only pre-warming containers of other functions are free
                continue
            q.remove(run)
            self.qcnt[run.f, k] -= 1
            avail -= 1

    def _acquire(self, k, run):
        f = run.f
        if self.idle[f, k] > 0:                                      # (1) warm container of the function
            ins = next(i for i in self.inst[k][f] if i.state == IDLE and i.run is None)
            self.idle[f, k] -= 1
            self.occ[k] += 1
            self._start(ins, run)
            return
        pre = next((i for i in self.inst[k][f] if i.state == COLD and i.run is None), None)
        if pre is not None:                                          # (1b) a container being pre-warmed for f (cheater only)
            pre.run = run
            self.occ[k] += 1
            return
        if self.hetero and not self._room_for(k, f):                 # (3h) unequal container sizes: recycle idle ones until f fits
            return False
        if not self.hetero and self.tot[k] >= self.ecc[k]:           # (3) recycle the LRU idle container of another function
            if self.recycle_budget is not None:
                if self.recycle_budget[k] < 1.0:
                    return False                                     # anti-churn: wait for a warm container instead
                self.recycle_budget[k] -= 1.0
            best = self._evict_choice(k)
            if best is None:                                         # cannot happen without pre-warming
                return False
            self.inst[k][best.f].remove(best)
            self.idle[best.f, k] -= 1
            self.cnt[best.f, k] -= 1
            self.tot[k] -= 1
            self.n_recycled += 1
        ins = OInstance(f, k, COLD, self.now + self.cold_start[f])   # (2) new container on a free slot
        ins.run = run
        self.inst[k][f].append(ins)
        self.cnt[f, k] += 1
        self.tot[k] += 1
        self.occ[k] += 1
        self.cold_starts_total += 1
        if self.in_window(self.now):
            self.cold_starts += 1
        self._at(ins.warm_at, "warm", ins, ins.token)

    def _remove_idle(self, ins):
        k = ins.node
        self.inst[k][ins.f].remove(ins)
        self.idle[ins.f, k] -= 1
        self.cnt[ins.f, k] -= 1
        self.tot[k] -= 1
        self.n_expired += 1

    def _ev_expire(self, ins, last, c):
        if ins.state == IDLE and ins.run is None and ins.last == last and ins in self.inst[ins.node][ins.f]:
            self._remove_idle(ins)

    def _ev_warm(self, ins, token, c):
        if token != ins.token or ins.state != COLD:
            return
        if ins.run is None:                                          # pre-warmed, nobody waiting: becomes a warm idle container
            ins.state, ins.last = IDLE, self.now
            self.idle[ins.f, ins.node] += 1
            if self.keep_warm == 0:
                self._remove_idle(ins)
            elif self.keep_warm is not None:
                self._at(self.now + float(self.keep_warm), "expire", ins, ins.last)
            self._try_node(ins.node)
            return
        self._start(ins, ins.run)

    def _room_for(self, k, f):
        """Heterogeneous container sizes (2026-11-02): make room on node k for one new container of f, recycling idle containers of
        OTHER functions in the same order as `_evict_choice` (LRU by default) until the weights fit. All-or-nothing: if the idle
        containers cannot free enough, nothing is evicted and False is returned (the run waits). Returns True when f fits."""
        fw = self.sc.fw
        need = float(self.cnt[:, k] @ fw) + fw[f] - self.ecc[k]
        if need <= 1e-9:
            return True
        cand = []
        for g in np.flatnonzero(self.idle[:, k]):
            if g == f:
                continue
            for i in self.inst[k][g]:
                if i.state == IDLE and i.run is None:
                    cand.append(((i.last,) if self.evict_score is None else (float(self.evict_score[g]), i.last), id(i), i))
        cand.sort(key=lambda x: (x[0], x[1]))
        chosen, freed = [], 0.0
        for _, _, i in cand:
            chosen.append(i)
            freed += fw[i.f]
            if freed >= need - 1e-9:
                break
        if freed < need - 1e-9:
            return False
        if self.recycle_budget is not None:
            if self.recycle_budget[k] < len(chosen):
                return False                                         # anti-churn: wait for a warm container instead
            self.recycle_budget[k] -= len(chosen)
        for i in chosen:
            self.inst[k][i.f].remove(i)
            self.idle[i.f, k] -= 1
            self.cnt[i.f, k] -= 1
            self.tot[k] -= 1
            self.n_recycled += 1
        return True

    def _evict_choice(self, k, exclude=None):
        """Idle container to recycle on node k: least recently used (default) or, with evict_score, lowest score then LRU."""
        best, bkey = None, None
        for g in np.flatnonzero(self.idle[:, k]):
            if g == exclude:
                continue
            for i in self.inst[k][g]:
                if i.state == IDLE and i.run is None:
                    key = (i.last,) if self.evict_score is None else (float(self.evict_score[g]), i.last)
                    if bkey is None or key < bkey:
                        best, bkey = i, key
        return best

    def prewarm(self, f, k):
        """Start a container of f on node k before any task needs it (used only by the look-ahead cheater). Uses a free slot,
        else recycles the least-recently-used idle container of another function; returns False if the node is full of busy or
        warming containers. Counts as a cold start."""
        if self.hetero:
            raise NotImplementedError("prewarm (look-ahead cheater) assumes equal container sizes")
        if self.tot[k] >= self.ecc[k]:
            best = self._evict_choice(k, exclude=f)
            if best is None:
                return False
            self.inst[k][best.f].remove(best)
            self.idle[best.f, k] -= 1
            self.cnt[best.f, k] -= 1
            self.tot[k] -= 1
            self.n_recycled += 1
        ins = OInstance(f, k, COLD, self.now + self.cold_start[f])
        self.inst[k][f].append(ins)
        self.cnt[f, k] += 1
        self.tot[k] += 1
        self.cold_starts_total += 1
        if self.in_window(self.now):
            self.cold_starts += 1
        self._at(ins.warm_at, "warm", ins, ins.token)
        return True

    def _ev_done(self, ins, token, c):
        run = ins.run
        r, wf, t, k = run.req, run.req.wf, run.task, ins.node
        ins.run, ins.state, ins.last = None, IDLE, self.now
        self.idle[ins.f, k] += 1
        self.occ[k] -= 1
        if self.keep_warm == 0:
            self._remove_idle(ins)
        elif self.keep_warm is not None:
            self._at(self.now + float(self.keep_warm), "expire", ins, ins.last)
        self.storage_used[k] -= run.total
        self.policy.on_task_done(self, run)
        for ch in wf.children[t]:
            if self.mode == "plan":
                self._at(self.now + self._stt(wf.ss[(t, ch)], k, r.plan[ch]), "state", r, ch)
            else:
                r.rdy[ch] -= 1
                if r.rdy[ch] == 0:
                    r.tready[ch] = self.now
                    if not self._decide(r, ch):
                        self.wait_tasks.append((r, ch))
        r.left -= 1
        if r.left == 0:
            r.t_done = self.now
            self.active -= 1
            if self.in_window(r.t_arr):
                self.makespans.append(self.now - r.t_arr)
                self.win.pop(r.id, None)
        self._try_node(k)
        if self.waiting or self.wait_tasks:
            self._retry_waiting()

    # --------------------------------------------------------------------------------------------- bookkeeping
    def results(self):
        out = super().results()
        out["n_recycled"] = int(self.n_recycled)
        out["n_waiting_at_end"] = int(len(self.waiting) + len(self.wait_tasks))
        return out

    def check_invariants(self):
        for k in range(self.N):
            n_inst = sum(len(self.inst[k][f]) for f in range(self.F))
            if self.hetero:
                wused = sum(len(self.inst[k][f]) * self.sc.fw[f] for f in range(self.F))
                assert n_inst == self.tot[k] and wused <= self.ecc[k] + 1e-9, f"node {k}: weighted capacity {wused} / {self.ecc[k]}"
            else:
                assert n_inst == self.tot[k] <= self.ecc[k], f"node {k}: container count {n_inst}/{self.tot[k]}/{self.ecc[k]}"
            occ = sum(1 for f in range(self.F) for i in self.inst[k][f] if i.run is not None)
            assert occ == self.occ[k], f"node {k}: occupied {occ} != {self.occ[k]}"
            for f in range(self.F):
                idle = sum(1 for i in self.inst[k][f] if i.state == IDLE and i.run is None)
                assert idle == self.idle[f, k], f"idle count mismatch (f={f}, k={k})"
                assert self.qcnt[f, k] == sum(1 for x in self.nq[k] if x.f == f)
            assert self.storage_used[k] <= self.esc[k] + 1e-6, f"node {k}: storage overflow"
