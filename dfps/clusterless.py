"""CLU: a ClusterLess-style deadline-aware workflow scheduler, single-cluster reduction (knowledge/synthesis/clusterless-baseline.md, pre-registered 16 Nov 2026).

Source: "ClusterLess: Deadline-Aware Serverless Workflow Orchestration on Federated Edge Clusters", arXiv 2605.04310 (May 2026), Eqs. 4-7, 11 and Algorithm 2
(intra-cluster orchestration). Written from the paper's equations only; nothing is taken from the F5/F6 controller (o3s.py, sim.py late binding). It reads the
simulator's state (queues, container counts, idle counts, execution and cold-start times, capacities, storage) and nothing else.

Model (deviations D1-D7 of the pre-registration):
  D1 one cluster = the logical nodes; no offloading, no super-master.   D2 one cold-start value per function: modes are warm execution and cold scaling.
  D3 no bandwidth check (Eqs. 12-13); transfers cost time, storage is a hard limit.   D4 deadline D_w = kappa x L_w, L_w = longest path of (execution + cold start).
  D5 a request whose deadline cannot be met still runs (smallest predicted finish) and is counted.   D6 no keep-alive or pre-warming (container model of Heu and RL).
  D7 nominal mean execution times.

Plan of one request, functions in topological order (a function f on node k, parents g with predicted finish F_g on node n_g):
  S = max(now, max_g F_g + theta(g->k)),  roots: now + transfer of the request input;  chi = Q + T (warm execution) or CS + T (cold scaling);  F = S + chi.
  warm execution: candidates = nodes holding a container of f; Q = 0 if one of them is idle (and not already taken by this plan), else backlog_k / ecc_k, the work
  queued on the node plus the remaining work of its running tasks plus the work this plan has already put there (the paper's per-worker queue delay Q_ni).
  cold scaling: candidates = nodes with room for a new container of f (free capacity, or idle containers of other functions that can be recycled).
  Algorithm 2: every function starts in warm execution; while the predicted finish of the workflow exceeds A_w + D_w, the function with the largest predicted finish
  that is not yet in cold scaling moves to cold scaling; the move is kept if its finish improves, else the function is excluded; descendants are recomputed.
Binding: refine=True (arm CLU) re-plans the not-yet-started functions whenever a function becomes ready (Sec. V-B refinement, Sec. III-C); refine=False (arm CLU-S)
  builds the plan at arrival only (Algorithm 2 read literally).
Ties: smaller finish, then smaller transfer, then lower node index."""
from __future__ import annotations

import time

import numpy as np

from .solution import BUSY, COLD

WARM, CLOLD = 0, 1                     # modes of a function in a plan: warm execution, cold scaling


class _Req:
    __slots__ = ("fin", "pf", "nodes", "d", "counted", "tdec")

    def __init__(self):
        self.fin = {}                  # task -> real finish time (finished tasks)
        self.pf = {}                   # task -> predicted finish at the plan that decided it
        self.nodes = {}                # CLU-S: the plan made at arrival
        self.d = 0.0
        self.counted = False
        self.tdec = {}                 # task -> time of its decision (audit)


class ClusterLessPolicy:
    mode = "ready"
    name = "CLU"

    def __init__(self, seed=0, kappa=1.5, refine=True, audit=False):
        self.kappa, self.refine = float(kappa), bool(refine)
        self.rng = np.random.default_rng(seed)         # unused: the rule is deterministic
        self.n_prune_fail = 0
        self._req = {}
        self._cp = {}                                  # workflow id -> L_w
        self.n_plans = self.n_replans = self.n_escalations = self.n_pred_violated = self.n_real_violated = self.n_requests = 0
        self.n_cold_mode = self.n_decisions = 0
        self.plan_ms = []
        self.audit = [] if audit else None             # (predicted time to finish, real time to finish) per task, from its decision

    def attach(self, sim):
        self.sim = sim
        self._req = {}
        self._cp = {}
        self.fw = np.asarray(sim.sc.fw, dtype=float)
        self.T = np.asarray(sim.exec_time, dtype=float)
        self.CS = np.asarray(sim.cold_start, dtype=float)

    # ------------------------------------------------------------------------------------------------- estimates
    def critical(self, wf):
        """L_w: longest path of (nominal execution time + cold start) over the workflow, no transfers (D4)."""
        if wf.id not in self._cp:
            d = [0.0] * wf.n
            for t in range(wf.n):
                f = wf.ft[t]
                d[t] = self.T[f] + self.CS[f] + max((d[u] for u in wf.parents[t]), default=0.0)
            self._cp[wf.id] = max(d)
        return self._cp[wf.id]

    def backlog(self, sim):
        """Work on every node in capacity-weighted seconds: queued runs, plus the remaining nominal work of running tasks (a container still cold-starting for a task
        counts its remaining cold start plus the execution)."""
        fw, T = self.fw, self.T
        b = (sim.qcnt * (T * fw)[:, None]).sum(axis=0).astype(float)
        now = sim.now
        for k in range(sim.N):
            for f in np.flatnonzero(sim.occf[:, k]):
                for i in sim.inst[k][f]:
                    run = i.run
                    if run is None:
                        continue
                    if i.state == BUSY:
                        rem = max(0.0, T[f] - (now - run.t_start))
                    elif i.state == COLD:
                        rem = max(0.0, i.warm_at - now) + T[f]
                    else:
                        continue
                    b[k] += rem * fw[f]
        return b

    def room(self, sim, f):
        """Nodes where a new container of f fits now: free capacity, or idle containers of other functions that can be recycled."""
        fw = self.fw
        free = sim.ecc - fw @ sim.cnt
        idle_other = fw @ sim.idle - fw[f] * sim.idle[f]
        return (free + idle_other) >= fw[f] - 1e-9

    # ------------------------------------------------------------------------------------------------- planning
    def _plan(self, sim, r, st, scope, now, deadline, limit_t):
        """Plan the tasks of `scope` (topological order) with Algorithm 2. Returns (nodes, finish times, modes, predicted workflow finish)."""
        wf = r.wf
        net = sim.net
        ecc = sim.ecc.astype(float)
        free_store = sim.esc - sim.storage_used
        bl = self.backlog(sim)
        room_cache = {}
        N = sim.N
        ks = np.arange(N)

        def parent_data(x):
            """(predicted/real finish, node, size) of every parent of x: finished parents use the real time, decided ones the plan's, undecided the current plan's."""
            return [(st.fin[p] if p in st.fin else (fin_cur[p] if p in fin_cur else st.pf.get(p, now)), p, wf.ss[(p, x)]) for p in wf.parents[x]]

        fin_cur = {}

        def evaluate(modes):
            nodes, fin = {}, fin_cur
            fin.clear()
            extra = np.zeros(N)
            taken = {}                                    # (f, k) -> idle containers of f on k already used by this plan
            for x in scope:
                f = wf.ft[x]
                need = wf.input_total(x)
                ok = free_store >= need
                if not ok.any():
                    ok = np.ones(N, dtype=bool) if x != limit_t else ok
                if not wf.parents[x]:
                    theta = net.h[r.origin, :] * (net.epd + wf.input_size / net.bw)
                    start = now + theta
                else:
                    start = np.full(N, now)
                    theta = np.zeros(N)
                    for ft, p, size in parent_data(x):
                        pn = nodes[p] if p in nodes else r.plan[p]
                        tt = net.h[pn, :] * (net.epd + size / net.bw)
                        start = np.maximum(start, ft + tt)
                        theta = np.maximum(theta, tt)
                cold = modes.get(x, WARM) == CLOLD
                if not cold:
                    cand = ok & (sim.cnt[f] > 0)
                    if cand.any():
                        idle_free = np.array([sim.idle[f, k] - taken.get((f, k), 0) > 0 for k in ks])
                        chi = np.where(idle_free, 0.0, (bl + extra) / ecc) + self.T[f]
                    else:
                        cold = True                       # no container of f anywhere: it must scale (cold-scaling rule)
                if cold:
                    cand = ok & self._room(sim, f, room_cache)
                    if cand.any():
                        chi = np.full(N, self.CS[f] + self.T[f])
                    else:                                 # no room anywhere: the task waits in a node queue
                        cand = ok.copy()
                        chi = (bl + extra) / ecc + self.T[f]
                if not cand.any():
                    return None
                finish = start + chi
                finish = np.where(cand, finish, np.inf)
                m = finish.min()
                tie = np.flatnonzero(finish <= m + 1e-12)
                if len(tie) > 1:
                    th = theta[tie]
                    tie = tie[th <= th.min() + 1e-12]
                k = int(tie[0])
                nodes[x] = k
                fin[x] = float(finish[k])
                extra[k] += self.T[f] * self.fw[f]
                if sim.idle[f, k] - taken.get((f, k), 0) > 0:
                    taken[(f, k)] = taken.get((f, k), 0) + 1
            return nodes, dict(fin)

        modes = {x: WARM for x in scope}
        res = evaluate(modes)
        if res is None:
            return None
        nodes, fin = res

        def wf_finish(fin_):
            allf = [st.fin.get(p, st.pf.get(p)) for p in range(wf.n) if p not in fin_ and (p in st.fin or p in st.pf)]
            return max(list(fin_.values()) + [v for v in allf if v is not None])

        failed = set()
        while wf_finish(fin) > deadline:
            cands = [x for x in scope if modes[x] == WARM and x not in failed]
            if not cands:
                break
            b = max(cands, key=lambda x: fin[x])
            trial = dict(modes)
            trial[b] = CLOLD
            res2 = evaluate(trial)
            if res2 is not None and res2[1][b] < fin[b] - 1e-12:
                modes, (nodes, fin) = trial, res2
                self.n_escalations += 1
            else:
                failed.add(b)
        return nodes, fin, modes, wf_finish(fin)

    def _room(self, sim, f, cache):
        v = cache.get(f)
        if v is None:
            v = cache[f] = self.room(sim, f)
        return v

    # ------------------------------------------------------------------------------------------------- interface
    def choose(self, sim, r, t):
        t0 = time.perf_counter()
        wf = r.wf
        st = self._req.get(r.id)
        if st is None:
            st = self._req[r.id] = _Req()
            st.d = r.t_arr + self.kappa * self.critical(wf)
            self.n_requests += 1
        need = wf.input_total(t)
        if not self.refine and t in st.nodes and sim.esc[st.nodes[t]] - sim.storage_used[st.nodes[t]] >= need:
            if self.audit is not None:
                st.tdec[t] = sim.now
            return st.nodes[t]
        scope = [x for x in range(wf.n) if r.plan[x] is None]
        res = self._plan(sim, r, st, scope, sim.now, st.d, t)
        self.plan_ms.append((time.perf_counter() - t0) * 1e3)
        if res is None:
            return None
        nodes, fin, modes, wfin = res
        if st.counted:
            self.n_replans += 1
        else:
            self.n_plans += 1
        if not st.counted:
            st.counted = True
            if wfin > st.d:
                self.n_pred_violated += 1
        for x, v in fin.items():
            st.pf[x] = v
        if not self.refine:
            st.nodes.update(nodes)
        self.n_decisions += 1
        if modes.get(t) == CLOLD:
            self.n_cold_mode += 1
        k = nodes[t]
        if self.audit is not None:
            st.tdec[t] = sim.now
        if sim.esc[k] - sim.storage_used[k] < need:
            return None
        return int(k)

    def on_task_done(self, sim, run):
        st = self._req.get(run.req.id)
        if st is None:
            return
        st.fin[run.task] = sim.now
        if self.audit is not None and run.task in st.tdec and run.task in st.pf:
            self.audit.append((st.pf[run.task] - st.tdec[run.task], sim.now - st.tdec[run.task]))
        if len(st.fin) == run.req.wf.n:
            if sim.now > st.d + 1e-9:
                self.n_real_violated += 1
            del self._req[run.req.id]

    def stats(self):
        pm = np.array(self.plan_ms) if self.plan_ms else np.zeros(1)
        return dict(requests=self.n_requests, plans=self.n_plans, replans=self.n_replans, escalations=self.n_escalations, cold_mode_decisions=self.n_cold_mode,
                    pred_violated=self.n_pred_violated, real_violated=self.n_real_violated, decisions=self.n_decisions,
                    plan_ms_p50=float(np.percentile(pm, 50)), plan_ms_p99=float(np.percentile(pm, 99)), plan_ms_max=float(pm.max()))
