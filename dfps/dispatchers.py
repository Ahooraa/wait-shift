"""Alternative request dispatchers (2026-10-24), to test whether the controller depends on DFPS's graph pattern matching.

A dispatcher is a callable (sim, request) -> {task: node} or None (no feasible plan: the request waits, as with DFPS's scheduler). It runs when
a request arrives and fixes where every task of its workflow will run; the controller's layout and request moves are unchanged. All of them
respect the two hard constraints of the model: the node must hold a container of the task's function and have free state storage for the
task's input states (storage is reserved task by task inside the plan, as DFPS's A-23 does after planning).

  greedy_eft  each task, in topological order, goes to the node with the smallest (input-transfer time from its parents' nodes, or from
              the request origin for a root) + (queueing/start estimate of that function there, FST). Per-task earliest finish time,
              the standard list-scheduling heuristic; it sees the same two costs DFPS's matcher minimises but decides one task at a time.
  locality    data gravity: a task goes to the node of its heaviest parent if that node can host it, else the closest feasible node to that
              parent (ties by FST); roots go to the feasible node closest to the origin. Ignores queues.
  jsq         join-the-shortest-queue: the feasible node with the fewest queued runs per container of the function. Ignores data placement.
  random      a feasible node chosen with probability proportional to its containers of the function. Lower bound on dispatcher quality.
"""
from __future__ import annotations

import numpy as np


def _plan_tasks(sim, r, choose):
    wf = r.wf
    free = sim.esc - sim.storage_used                       # local copy: storage is reserved task by task inside this plan
    plan = {}
    h = sim.net.h
    for t in range(wf.n):                                   # tasks are in topological order
        f = wf.ft[t]
        ks = np.flatnonzero((sim.cnt[f] > 0) & (free >= wf.input_total(t) - 1e-9))
        if ks.size == 0:
            return None
        if wf.parents[t]:
            src = [(plan[p], wf.ss[(p, t)]) for p in wf.parents[t]]
        else:
            src = [(r.origin, wf.input_size)]
        k = int(choose(sim, f, t, ks, src))
        plan[t] = k
        free[k] -= wf.input_total(t)
    return plan


def _transfer(sim, ks, src):
    """Summed input-state transfer time to each candidate node (DFPS sums the inputs, A-30)."""
    bw, epd, h = sim.net.bw, sim.net.epd, sim.net.h
    return sum(h[s, ks] * (epd + size / bw) for s, size in src)


def greedy_eft(sim, r):
    def choose(sim, f, t, ks, src):
        return ks[int(np.argmin(_transfer(sim, ks, src) + sim.fst_vec(f)[ks]))]
    return _plan_tasks(sim, r, choose)


def locality(sim, r):
    def choose(sim, f, t, ks, src):
        s = max(src, key=lambda x: x[1])[0]                 # node of the heaviest input
        d = sim.net.h[s, ks].astype(float) + 1e-6 * sim.fst_vec(f)[ks]
        return ks[int(np.argmin(d))]
    return _plan_tasks(sim, r, choose)


def transfer_only(sim, r):
    """Objective alignment, deterministic part only (2026-11-04): each task goes to the feasible node with the smallest summed input-transfer
    time from its parents' planned nodes (the origin for a root); ties (common: equal hop counts) broken by FST. No wait term is optimised,
    on the reading that the planning-time wait estimate carries little information and the mover handles waits."""
    def choose(sim, f, t, ks, src):
        d = _transfer(sim, ks, src)
        return ks[int(np.lexsort((sim.fst_vec(f)[ks], d))[0])]
    return _plan_tasks(sim, r, choose)


def mover_aet(sim, r):
    """Objective alignment with the mover's own score (2026-11-04): each task goes to the node minimising input transfer + the mover's
    service estimate (Sol.service_estimate over the live instance availability, at the current queue length plus the tasks of this plan
    already placed on that (function, node)). The output term of the mover's score is left out: here every edge is priced once, as the
    child's input transfer."""
    from .solution import Sol
    sol, extra = Sol(sim), {}

    def choose(sim, f, t, ks, src):
        svc = np.array([sol.service_estimate(f, int(k), len(sim.queue[int(k)][f]) + extra.get((f, int(k)), 0)) for k in ks])
        k = int(ks[int(np.argmin(_transfer(sim, ks, src) + svc))])
        extra[(f, k)] = extra.get((f, k), 0) + 1
        return k
    return _plan_tasks(sim, r, choose)


def jsq(sim, r):
    def choose(sim, f, t, ks, src):
        load = np.array([len(sim.queue[k][f]) for k in ks], dtype=float) / sim.cnt[f, ks]
        best = np.flatnonzero(load <= load.min() + 1e-12)
        return ks[int(sim.sched_rng.choice(best))]
    return _plan_tasks(sim, r, choose)


def random_node(sim, r):
    def choose(sim, f, t, ks, src):
        w = sim.cnt[f, ks].astype(float)
        return ks[int(sim.sched_rng.choice(len(ks), p=w / w.sum()))]
    return _plan_tasks(sim, r, choose)


class RoundRobin:
    """Round Robin, a baseline of Liang et al. (Future Internet 18:265, 2026, Sec. 5.1.4): tasks go to nodes "in a cyclic manner without
    considering workflow structure or resource heterogeneity". Port: the cycle runs over the nodes that hold a container of the task's
    function (the fixed slot budget), with one pointer per function."""

    def __init__(self):
        self.ptr = {}

    def __call__(self, sim, r):
        def choose(sim, f, t, ks, src):
            i = self.ptr.get(f, 0)
            self.ptr[f] = i + 1
            return ks[i % len(ks)]
        return _plan_tasks(sim, r, choose)


def resource_fit(sim, r):
    """Greedy Resource-Fit (Liang et al. 2026, Sec. 5.1.4): "the feasible node that provides the best local fit according to available
    capacity and estimated execution cost". Port: smallest start-time estimate FST of the function there (queueing included), ignoring
    data transfer; no node prices in our model, so the cost part is constant. Ties: more containers of the function, then lower index."""
    def choose(sim, f, t, ks, src):
        return ks[int(np.lexsort((-sim.cnt[f, ks], sim.fst_vec(f)[ks]))[0])]
    return _plan_tasks(sim, r, choose)


def heft_like(sim, r):
    """HEFT-like (Liang et al. 2026, Sec. 5.1.4, after Topcuoglu et al. 2002): tasks in decreasing upward rank, each to the node with
    the earliest estimated finish time. rank_u(t) = w_t + max_s (c_ts + rank_u(s)) with w_t = mean exec time and c_ts = state size / bw x
    mean hop count. EFT_k = max(avail_k, max_p(EFT_p + stt(p -> k))) + w_t, avail_k = now + FST plus the work this plan already put on k
    (HEFT's processor-availability update). Unlike greedy_eft it takes the max of data-ready and node-ready times, not their sum."""
    wf = r.wf
    net, mu = sim.net, sim.exec_time
    hbar = float(net.h[np.triu_indices(net.ne, 1)].mean()) if net.ne > 1 else 0.0
    rank = [0.0] * wf.n
    children = [[] for _ in range(wf.n)]
    for t in range(wf.n):
        for p in wf.parents[t]:
            children[p].append(t)
    for t in reversed(range(wf.n)):                         # indices are topological, so children are ranked first
        rank[t] = mu[wf.ft[t]] + max((wf.ss[(t, s)] / net.bw * hbar + rank[s] for s in children[t]), default=0.0)
    order = sorted(range(wf.n), key=lambda t: (-rank[t], t))  # decreasing rank_u is a valid topological order
    free = sim.esc - sim.storage_used
    extra = {}                                              # (f, k) -> work this plan has already assigned there
    plan, eft = {}, {}
    for t in order:
        f = wf.ft[t]
        ks = np.flatnonzero((sim.cnt[f] > 0) & (free >= wf.input_total(t) - 1e-9))
        if ks.size == 0:
            return None
        if wf.parents[t]:
            ready = np.max([eft[p] + net.h[plan[p], ks] * (net.epd + wf.ss[(p, t)] / net.bw) for p in wf.parents[t]], axis=0)
        else:
            ready = net.h[r.origin, ks] * (net.epd + wf.input_size / net.bw)
        avail = sim.fst_vec(f)[ks] + np.array([extra.get((f, int(k)), 0.0) for k in ks]) / sim.cnt[f, ks]
        fin = np.maximum(avail, ready) + mu[f]
        i = int(np.argmin(fin))
        k = int(ks[i])
        plan[t], eft[t] = k, float(fin[i])
        extra[(f, k)] = extra.get((f, k), 0.0) + mu[f]
        free[k] -= wf.input_total(t)
    return plan


class GraphAware:
    """Graph-Aware Scheduling, Liang et al. (Future Internet 18:265, 2026, Sec. 4, Eqs. 15-24), ported to our model. Each task, in
    topological order, goes to argmax_j s_ij over the feasible nodes, with
        s_ij = -alpha * l~exec_ij - beta * l~comm_ij - gamma * l~cost_ij + eta * delta_ij           (Eq. 21)
    and the resource state updated after every assignment (Psi, Eq. 24). Port-fidelity caveats (also in the run script):
      (1) eta = 0, delta dropped: the paper never specifies its encoders f_w, f_r or the fixed weights of g (Eq. 20), and its own Sec. 5.6
          finds eta "has only a limited effect".
      (2) gamma = 0: our nodes have no price, so l_cost = rho_j * c_i is the same on every candidate and drops out.
      (3) l_exec = c_i / u_j "augmented with queueing delay" (Eq. 15) -> FST of the function on the node + its exec time (nodes are
          homogeneous here, so the c_i / u_j part is constant); Psi adds the work this plan already placed on (f, k) / containers.
          Psi is per plan: a planned task becomes visible to other requests only when it enqueues (the simulator's own state).
      (4) l_comm (Eq. 16): sum over predecessors on other nodes of d_ki / b + lambda_lat * tau. Ours is store-and-forward per hop,
          hops x (epd + d / bw), with lambda_lat = 1; epd = 0 (DFPS assumption), so the latency term vanishes.
      (5) normalisation "within the current scheduling instance" (Sec. 4.3, Eq. 20) -> min-max over the candidate set of each decision.
      (6) the paper gives no default coefficients ("fixed default values chosen a priori", Sec. 5.1.6); alpha = 1 and beta is chosen
          on development cases (its Sec. 5.6 range is 0.2-1.1)."""

    def __init__(self, alpha=1.0, beta=1.0, gamma=0.0, eta=0.0):
        assert gamma == 0.0 and eta == 0.0, "cost and correction terms are not modelled (caveats 1-2)"
        self.alpha, self.beta = float(alpha), float(beta)

    @staticmethod
    def _norm(x):
        lo, hi = float(x.min()), float(x.max())
        return np.zeros_like(x) if hi - lo <= 1e-12 else (x - lo) / (hi - lo)

    def __call__(self, sim, r):
        extra = {}

        def choose(sim, f, t, ks, src):
            occ = np.array([extra.get((f, int(k)), 0.0) for k in ks]) / sim.cnt[f, ks]
            l_exec = sim.fst_vec(f)[ks] + occ + sim.exec_time[f]
            l_comm = _transfer(sim, ks, src)
            s = -self.alpha * self._norm(l_exec) - self.beta * self._norm(l_comm)
            k = int(ks[int(np.argmax(s))])
            extra[(f, k)] = extra.get((f, k), 0.0) + sim.exec_time[f]
            return k
        return _plan_tasks(sim, r, choose)


# Comm.-Cost-Aware Greedy (Liang et al. 2026, Sec. 5.1.4: "local execution suitability, predecessor communication penalty, and execution
# cost") is exactly greedy_eft here: FST + transfer, in seconds, with no node prices.
DISPATCHERS = {"greedy_eft": greedy_eft, "locality": locality, "jsq": jsq, "random": random_node, "resource_fit": resource_fit,
               "heft_like": heft_like, "ccag": greedy_eft, "transfer_only": transfer_only, "mover_aet": mover_aet}


class FaaSPRRouter:
    """FaaSPR's routing (Jia et al., IEEE/ACM ToN 2025, Sec. V), ported to our model (2026-10-24). Callable (sim, request) -> plan.

    Kept from the paper: a routing path assigns every task of a workflow to a server hosting its function; a path has a latency (critical
    path of mean execution times plus state transfers, no queueing, no cold starts). A linear programme chooses the request frequency of
    every path: cover the workflow's arrival rate, and keep the load on each (function, server) at most alpha = 0.9 of that server's
    containers' capacity (containers / run time). Multi-stage: the latency threshold is lowered while the LP stays feasible, then the
    average latency is minimised under it. Requests draw a path with probability proportional to its frequency. It is recomputed after
    every layout change (the paper: at every scaling request), from the arrival rates of the last `window` seconds.
    Adaptations: (1) the paths are a sampled set (`n_paths` per workflow: randomised greedy local-first plus capacity-proportional
    random), not all of them, because with 80 servers the full set is astronomically large (the paper splits servers in groups of 8 for
    the same reason); (2) functions are shared between workflows here, so the capacity constraints couple all workflows in ONE LP,
    where the paper solves one LP per workflow; (3) the threshold is relative to each workflow's best path (theta x minimum latency);
    (4) the request's origin node is not used (as in the paper); (5) if the LP cannot cover the rate, the uncovered part is a slack
    (penalised) and requests still draw from the frequencies found; (6) a task whose drawn node lacks free storage (the paper has no per-node storage limit) is re-assigned alone to the
    cheapest hosting node with free storage; the share of requests routed exactly by the LP path is reported (n_pure); (7)
    formula audit (2026-10-26, checked against the paper's own Sec. V-B/C/D text, Constraints 1-3 and the LP objective): no
    correctness deviations found in the LP constraints (execution-frequency, instance-capacity alpha*P_ij/t_i, and the
    latency-threshold cutoff) or the multi-stage binary search for the smallest feasible threshold -- all match the paper's
    formulas exactly. One addition with no paper counterpart: when a workflow's solved frequencies are all ~zero (can happen
    with our sampled, non-exhaustive path set -- the paper's exhaustive enumeration does not need this), we fall back to a
    uniform distribution over paths within 1.3x of that workflow's best latency, rather than leaving it unroutable."""

    THETAS = (1.0, 1.15, 1.3, 1.6, 2.0, 3.0, 6.0, np.inf)

    def __init__(self, n_paths=60, alpha=0.9, window=120.0, refresh=60.0, seed=0):
        self.n_paths, self.alpha, self.window, self.refresh = int(n_paths), float(alpha), float(window), float(refresh)
        self.rng = np.random.default_rng(seed)
        self.ver, self.t_last = -1, -1e9
        self.arr = []                                   # (time, workflow index)
        self.paths, self.prob, self.widx = {}, {}, None
        self.n_solves, self.n_fallback, self.n_slack, self.theta_used, self.solve_ms = 0, 0, 0, [], []
        self.n_pure, self.n_repaired_req, self.n_repaired_tasks, self.n_unplanned = 0, 0, 0, 0   # requests routed exactly by the LP path / repaired / not plannable
        self.slack_frac = []                                                                      # uncovered share of the rate per solve
        self.on_unplanned = None                        # optional debug hook(sim, r, t, f) called when a task cannot be repaired (2026-10-26)

    # ---------------------------------------------------------------- path generation
    def _latency(self, sim, wf, nodes):
        net, mu = sim.net, sim.exec_time
        fin = np.zeros(wf.n)
        for t in range(wf.n):
            s = 0.0
            for p in wf.parents[t]:
                s = max(s, fin[p] + net.h[nodes[p], nodes[t]] * (net.epd + wf.ss[(p, t)] / net.bw))
            fin[t] = s + mu[wf.ft[t]]
        return float(fin.max())

    def _gen(self, sim, wf):
        cnt, net = sim.cnt, sim.net
        hosts = [np.flatnonzero(cnt[f]) for f in range(sim.F)]
        seen, out = set(), []
        for i in range(self.n_paths):
            greedy = i % 2 == 0
            noise = self.rng.uniform(0.0, 1.5)
            nodes = np.zeros(wf.n, dtype=int)
            for t in range(wf.n):
                f = wf.ft[t]
                ks = hosts[f]
                if not wf.parents[t] or not greedy:
                    w = cnt[f, ks].astype(float)
                    nodes[t] = ks[self.rng.choice(len(ks), p=w / w.sum())]
                else:
                    c = sum(net.h[nodes[p], ks] * (net.epd + wf.ss[(p, t)] / net.bw) for p in wf.parents[t])
                    c = c * (1.0 + noise * self.rng.random(len(ks))) - 1e-6 * cnt[f, ks]
                    nodes[t] = ks[int(np.argmin(c))]
            key = tuple(nodes)
            if key not in seen:
                seen.add(key)
                out.append((nodes.copy(), self._latency(sim, wf, nodes)))
        return out

    # ---------------------------------------------------------------- the multi-stage LP
    def _solve(self, sim, rates):
        import time as _t
        from scipy.optimize import linprog
        from scipy.sparse import coo_matrix, hstack, vstack
        t0 = _t.perf_counter()
        W = len(sim.sc.workflows)
        cols = []                                       # (workflow, nodes, latency)
        for w, wf in enumerate(sim.sc.workflows):
            for nodes, lat in self._gen(sim, wf):
                cols.append((w, nodes, lat))
        n = len(cols)
        lat = np.array([c[2] for c in cols])
        wid = np.array([c[0] for c in cols])
        best = np.array([lat[wid == w].min() for w in range(W)])
        rows, cs = [], []
        index = {}
        for k, (w, nodes, _) in enumerate(cols):
            wf = sim.sc.workflows[w]
            for t in range(wf.n):
                r = index.setdefault((wf.ft[t], int(nodes[t])), len(index))
                rows.append(r)
                cs.append(k)
        cap = np.array([self.alpha * sim.cnt[f, j] / sim.exec_time[f] for (f, j) in index])
        A = coo_matrix((np.ones(len(rows)), (rows, cs)), shape=(len(index), n)).tocsr()
        # variables: o_1..o_n then slack_1..slack_W ; coverage: sum o + slack >= rate  ->  -sum o - slack <= -rate
        Acov = coo_matrix((-np.ones(n + W), (np.concatenate([wid, np.arange(W)]), np.concatenate([np.arange(n), n + np.arange(W)]))),
                          shape=(W, n + W)).tocsr()
        Aub = vstack([hstack([A, coo_matrix((len(index), W))]), Acov]).tocsr()
        bub = np.concatenate([cap, -rates])

        def lp(theta, c):
            ub = np.where(lat <= theta * best[wid] + 1e-12, np.inf, 0.0)
            bounds = list(zip(np.zeros(n + W), np.concatenate([ub, np.full(W, np.inf)])))
            return linprog(c, A_ub=Aub, b_ub=bub, bounds=bounds, method="highs")

        c_slack = np.concatenate([np.zeros(n), np.ones(W)])
        s_inf = lp(np.inf, c_slack)
        if s_inf.status != 0:
            raise RuntimeError("LP failed: " + str(s_inf.message))
        target = s_inf.fun + 1e-9 + 1e-6 * rates.sum()
        lo, hi = 0, len(self.THETAS) - 1                # smallest threshold whose minimal slack equals the unrestricted one
        while lo < hi:
            mid = (lo + hi) // 2
            r = lp(self.THETAS[mid], c_slack)
            if r.status == 0 and r.fun <= target:
                hi = mid
            else:
                lo = mid + 1
        theta = self.THETAS[lo]
        res = lp(theta, np.concatenate([lat, np.full(W, 1e4)]))
        if res.status != 0:
            res = s_inf
        o = np.maximum(res.x[:n], 0.0)
        self.paths, self.prob = {}, {}
        for w in range(W):
            idx = np.flatnonzero(wid == w)
            if o[idx].sum() <= 1e-12:                   # no frequency: use the low-latency paths uniformly
                p = np.where(lat[idx] <= best[w] * 1.3, 1.0, 0.0)
                p = p / p.sum() if p.sum() else np.full(len(idx), 1.0 / len(idx))
            else:
                p = o[idx] / o[idx].sum()
            self.paths[w] = [cols[k][1] for k in idx]
            self.prob[w] = p
        self.n_solves += 1
        self.n_slack += int(res.x[n:].sum() > 1e-6)
        self.slack_frac.append(float(res.x[n:].sum() / max(rates.sum(), 1e-12)))
        self.theta_used.append(float(theta) if np.isfinite(theta) else 99.0)
        self.solve_ms.append((_t.perf_counter() - t0) * 1e3)

    def _rates(self, sim):
        W = len(sim.sc.workflows)
        lo = sim.now - self.window
        i = 0
        while i < len(self.arr) and self.arr[i][0] < lo:
            i += 1
        self.arr = self.arr[i:]
        eff = min(self.window, max(sim.now, 10.0))
        r = np.full(W, 0.5 / eff)
        for _, w in self.arr:
            r[w] += 1.0 / eff
        return r

    # ---------------------------------------------------------------- dispatch
    def __call__(self, sim, r):
        if self.widx is None:
            self.widx = {w.id: i for i, w in enumerate(sim.sc.workflows)}
        wf = r.wf
        w = self.widx[wf.id]
        self.arr.append((sim.now, w))
        if sim.n_placements_applied != self.ver or sim.now - self.t_last >= self.refresh or not self.paths:
            self._solve(sim, self._rates(sim))
            self.ver, self.t_last = sim.n_placements_applied, sim.now
        k = int(self.rng.choice(len(self.paths[w]), p=self.prob[w]))
        nodes = self.paths[w][k]
        free = sim.esc - sim.storage_used
        plan, repaired = {}, 0
        net = sim.net
        for t in range(wf.n):
            f, need = wf.ft[t], wf.input_total(t) - 1e-9
            j = int(nodes[t])
            if sim.cnt[f, j] <= 0 or free[j] < need:
                # repair this task only: the hosting node with free storage that is cheapest to reach from where its inputs are
                ks = np.flatnonzero((sim.cnt[f] > 0) & (free >= need))
                if ks.size == 0:
                    self.n_unplanned += 1
                    if self.on_unplanned is not None:
                        self.on_unplanned(sim, r, t, f)
                    return None                                    # no feasible node: the request waits, as with any dispatcher
                if wf.parents[t]:
                    c = sum(net.h[plan[p], ks] * (net.epd + wf.ss[(p, t)] / net.bw) for p in wf.parents[t])
                else:
                    c = net.h[r.origin, ks] * (net.epd + wf.input_size / net.bw)
                j = int(ks[int(np.argmin(c))])
                repaired += 1
            plan[t] = j
            free[j] -= wf.input_total(t)
        if repaired:
            self.n_repaired_req += 1
            self.n_repaired_tasks += repaired
        else:
            self.n_pure += 1
        return plan
