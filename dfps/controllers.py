"""Simple heuristics for the headroom study (plan faas-edge-adaptation, Task 9). Each one is the "does a cheap rule already
capture the headroom?" check of one direction; none has a cost model, forecast or guarantee on purpose.

* D1  RateChangeTrigger        : re-run the DFPS annealing step only when the per-function request rate changed by more than
                                 `threshold` (relative L1 change) since the last re-plan (|d lambda| / lambda >= 0.3).
* D2  QueueThresholdAdmission  : reject a request when the number of requests in the system exceeds `theta` x total slots.
* D3  affinity_greedy_placement: instance counts proportional to expected load; instances placed greedily next to the
                                 functions they exchange the most data with (state size x request rate).
"""
from __future__ import annotations

import numpy as np


class RateChangeTrigger:
    """Adjuster wrapper (D1 heuristic). `inner` is a SimulatedAnnealing (B*); the trigger is evaluated every `check_s` seconds."""

    def __init__(self, inner, threshold=0.3, check_s=1.0):
        self.inner, self.threshold, self.next_interval = inner, float(threshold), float(check_s)
        self.ref = None
        self.n_triggered = 0

    def _rates(self, sim):
        return sim.lam.sum(axis=1).copy()                    # per-function request rate (all nodes)

    def run(self, sim):
        cur = self._rates(sim)
        if self.ref is None:                                 # first observation: becomes the reference, nothing to compare to
            self.ref = cur
            return None
        tot = max(float(self.ref.sum()), 1e-9)
        change = float(np.abs(cur - self.ref).sum()) / tot
        if change < self.threshold:
            return None
        self.ref = cur
        self.n_triggered += 1
        return self.inner.run(sim)


class QueueThresholdAdmission:
    """Admission callable (D2 heuristic): admit iff requests in system <= theta x total container slots."""

    def __init__(self, theta=2.0):
        self.theta = float(theta)

    def __call__(self, sim, req):
        return (sim.active + len(sim.waiting)) <= self.theta * float(sim.sc.ecc.sum())


def expected_workflow_rates(sc):
    """Requests per second of every workflow: from the scenario's per-application rates, else from the arrival list."""
    if "per_app_rate" in sc.meta:
        return np.array(sc.meta["per_app_rate"], dtype=float)
    dur = max(a[0] for a in sc.arrivals) if sc.arrivals else 1.0
    cnt = np.zeros(len(sc.workflows))
    for _, w, _ in sc.arrivals:
        cnt[w] += 1
    return cnt / dur


def proportional_counts(demand, S, floor=None):
    """Instance counts: >= floor (default 1) each, remaining slots proportional to demand (largest remainder)."""
    F = len(demand)
    n_f = np.ones(F, dtype=int) if floor is None else np.maximum(1, np.asarray(floor, dtype=int))
    left = S - int(n_f.sum())
    if left < 0:
        raise ValueError("fewer container slots than required instances")
    share = demand / demand.sum() * left if demand.sum() > 0 else np.full(F, left / F)
    n_f = n_f + np.floor(share).astype(int)
    rem = S - int(n_f.sum())
    for f in np.argsort(-(share - np.floor(share)))[:rem]:
        n_f[f] += 1
    return n_f


def origin_weights(arrivals, ne):
    """Share of requests arriving at each node, from an observed window of arrivals (no look-ahead)."""
    w = np.zeros(int(ne))
    for a in arrivals:
        w[a[2]] += 1.0
    return w / w.sum() if w.sum() else np.full(int(ne), 1.0 / int(ne))


def affinity_placement_v2(sc, rates=None, counts=None, cur=None, keep_weight=0.0, origin_weight=0.0, epoch=60.0,
                          o_w=None, softmin=1):
    """Placement with an explicit cost in seconds per second (2026-10-23). Same greedy shape as
    `affinity_greedy_placement`, but the cost a candidate node pays is

        (a) state transfer between tasks   sum_g aff[f,g] / bw * hops(k -> nearest node holding g)
      + (b) state transfer from origins    origin_weight * sum_w r_w * input_size / bw * E_origin[hops(origin -> k)]
      - (c) cold start avoided by reuse    keep_weight * cold_start[f] / epoch, if an instance of f is already on k

    (a) is the published rule, rescaled to seconds (it divides by bandwidth; the paper's epd is 0). (b) and (c) are new:
    (b) because origin->root edges carry 24-32% of the expected transfer cost and the old rule never saw them, and (c)
    because the old rule rebuilt the layout from scratch, converting 2-6x more containers than the target counts require.
    Both are in the same unit as (a), so the weights are interpretable: 1.0 trades one second of transfer for one second
    of cold start amortised over the epoch. `softmin` > 1 averages the hops to the nearest `softmin` instances of g,
    which breaks the near-ties that appear once a function sits on many nodes."""
    N, F = sc.network.ne, len(sc.functions)
    rates = expected_workflow_rates(sc) if rates is None else np.asarray(rates, dtype=float)
    mu = np.array([f.exec_time for f in sc.functions])
    cs = np.array([f.cold_start for f in sc.functions])
    bw, epd = sc.network.bw, sc.network.epd
    h = sc.network.h.astype(float)
    demand = np.zeros(F)
    aff = np.zeros((F, F))
    ocost = np.zeros((F, N))
    for w, r in zip(sc.workflows, rates):
        for t in range(w.n):
            demand[w.ft[t]] += r * mu[w.ft[t]]
        for (u, v), size in w.ss.items():
            a, b = w.ft[u], w.ft[v]
            if a != b:
                aff[a, b] += r * size
                aff[b, a] += r * size
        if origin_weight and o_w is not None:
            for t in w.roots:
                ocost[w.ft[t]] += r * (epd + w.input_size / bw) * (np.asarray(o_w, dtype=float) @ h)
    S = int(sc.ecc.sum())
    n_f = np.asarray(counts, dtype=int) if counts is not None else proportional_counts(demand, S)
    assert n_f.sum() == S and (n_f >= 1).all()
    cur = None if cur is None else np.asarray(cur, dtype=int)
    X = np.zeros((N, F), dtype=int)
    free = sc.ecc.astype(int).copy()
    placed = np.zeros((N, F), dtype=int)
    for f in np.argsort(-aff.sum(axis=1)):                   # most data-connected functions first
        base = origin_weight * ocost[f] if origin_weight else np.zeros(N)
        partners = [(g, aff[f, g] / bw) for g in range(F) if aff[f, g] > 0]
        for _ in range(int(n_f[f])):
            cost = base.copy()
            for g, wgt in partners:
                nodes_g = np.flatnonzero(placed[:, g])
                if nodes_g.size == 0:
                    continue
                d = h[:, nodes_g]
                if softmin > 1 and nodes_g.size > 1:
                    m = min(int(softmin), nodes_g.size)
                    cost += wgt * np.sort(d, axis=1)[:, :m].mean(axis=1)
                else:
                    cost += wgt * d.min(axis=1)
            if keep_weight and cur is not None:
                cost -= keep_weight * (cs[f] / float(epoch)) * (cur[:, f] > X[:, f])
            eps = 1e-6 * (1.0 + float(np.abs(cost).max()))   # tie-break: spread copies, then prefer roomy nodes
            cost = cost + eps * X[:, f] - 1e-3 * eps * free
            cost[free <= 0] = np.inf
            k = int(np.argmin(cost))
            X[k, f] += 1
            placed[k, f] += 1
            free[k] -= 1
    assert (X.sum(axis=1) == sc.ecc).all() and (X.sum(axis=0) == n_f).all()
    return X


def _placement_costs(sc, rates, origin_weight, o_w):
    """Per-function affinity weights and the origin->root cost per node, both in seconds per second.
    Returns (demand, aff/bw, ocost[F, N])."""
    N, F = sc.network.ne, len(sc.functions)
    mu = np.array([f.exec_time for f in sc.functions])
    bw, epd, h = sc.network.bw, sc.network.epd, sc.network.h.astype(float)
    demand, aff, ocost = np.zeros(F), np.zeros((F, F)), np.zeros((F, N))
    oh = (np.asarray(o_w, dtype=float) @ h) if (origin_weight and o_w is not None) else None
    for w, r in zip(sc.workflows, rates):
        for t in range(w.n):
            demand[w.ft[t]] += r * mu[w.ft[t]]
        for (u, v), size in w.ss.items():
            a, b = w.ft[u], w.ft[v]
            if a != b:
                aff[a, b] += r * size
                aff[b, a] += r * size
        if oh is not None:
            for t in w.roots:
                ocost[w.ft[t]] += r * (epd + w.input_size / bw) * oh
    return demand, aff / bw, ocost


def transport_placement(sc, rates=None, counts=None, cur=None, keep_weight=1.0, origin_weight=1.0, epoch=60.0,
                        o_w=None, iters=2):
    """Placement as a min-cost transportation problem (2026-10-23), replacing the sequential greedy of
    `affinity_greedy_placement`.

    Cost of putting one container of function f on node k, in seconds per second:
        A[k, f] = sum_g aff[f, g] / bw * hops(k -> nearest node holding g)        state transfer between tasks
                + origin_weight * sum_w r_w * input_size / bw * E_o[hops(o -> k)]  state transfer from request origins
    and a container that REUSES an instance of f already on k pays `keep_weight * cold_start[f] / epoch` less, because it
    starts no container. Minimising sum_k,f A[k, f] X[k, f] - (reuse discount) subject to row sums = ecc_k and column sums =
    `counts` is a transportation problem (the reuse discount is a concave piecewise-linear term, so it splits into a cheap
    arc of capacity cur[k, f] and a full-price arc); its LP relaxation is integral for integral supplies, so HiGHS returns an
    integral optimum directly.

    Why not the greedy: measured on live re-layouts, the greedy leaves 98% of its decisions tied between several nodes (mean
    30 of 80) and converts 2-6x more containers than the target counts require, because it fills every slot in affinity order
    and cannot see that a slot it takes is one another function needed to keep. `hops(k -> nearest g)` is evaluated against a
    reference layout (the current one on the first pass, then the previous solution), which fixes the cost matrix; `iters`
    passes let the partner positions settle."""
    from scipy.optimize import linprog
    from scipy.sparse import coo_matrix
    N, F = sc.network.ne, len(sc.functions)
    rates = expected_workflow_rates(sc) if rates is None else np.asarray(rates, dtype=float)
    demand, affw, ocost = _placement_costs(sc, rates, origin_weight, o_w)
    S = int(sc.ecc.sum())
    n_f = np.asarray(counts, dtype=int) if counts is not None else proportional_counts(demand, S)
    assert n_f.sum() == S and (n_f >= 1).all()
    h = sc.network.h.astype(float)
    cs = np.array([f.cold_start for f in sc.functions])
    ecc = sc.ecc.astype(int)
    cur = np.zeros((N, F), dtype=int) if cur is None else np.asarray(cur, dtype=int)
    disc = keep_weight * cs / float(epoch) if keep_weight else np.zeros(F)
    keep_cap = np.minimum(cur, n_f[None, :]).astype(float)                 # reuse at most what is already there

    rows, cols, vals, beq = [], [], [], []
    for k in range(N):                                                     # every slot of every node is filled (D-7)
        for f in range(F):
            for off in (0, N * F):
                rows.append(k)
                cols.append(off + k * F + f)
                vals.append(1.0)
        beq.append(float(ecc[k]))
    for f in range(F):                                                     # the counts the sizing rule asked for
        for k in range(N):
            for off in (0, N * F):
                rows.append(N + f)
                cols.append(off + k * F + f)
                vals.append(1.0)
        beq.append(float(n_f[f]))
    Aeq = coo_matrix((vals, (rows, cols)), shape=(N + F, 2 * N * F))
    b_eq = np.array(beq)
    ub = np.concatenate([keep_cap.reshape(-1), np.full(N * F, np.inf)])
    bounds = list(zip(np.zeros(2 * N * F), ub))

    ref = cur if cur.any() else None
    X = None
    for _ in range(max(1, int(iters))):
        A = np.tile(origin_weight * ocost.T if origin_weight else np.zeros((N, F)), 1)
        A = A.astype(float).copy()
        for f in range(F):
            for g in np.flatnonzero(affw[f] > 0):
                hosts = np.flatnonzero(ref[:, g]) if ref is not None else np.arange(N)
                if hosts.size:
                    A[:, f] += affw[f, g] * h[:, hosts].min(axis=1)
        c = np.concatenate([(A - disc[None, :]).reshape(-1), A.reshape(-1)])
        res = linprog(c, A_eq=Aeq, b_eq=b_eq, bounds=bounds, method="highs")
        if not res.success:                                                # fall back rather than fail a run
            return affinity_placement_v2(sc, rates=rates, counts=n_f, cur=cur, keep_weight=keep_weight,
                                         origin_weight=origin_weight, epoch=epoch, o_w=o_w)
        X = np.rint(res.x[:N * F] + res.x[N * F:]).reshape(N, F).astype(int)
        ref = X
    assert (X.sum(axis=1) == ecc).all() and (X.sum(axis=0) == n_f).all()
    return X


def demand_points(sc, rates, cur, o_w=None, origin_weight=1.0):
    """Per function, the weighted demand points its containers have to be close to, in MB/s of state that must travel.

    For function f: every node holding a workflow partner g, carrying aff[f, g] of state per second (spread over g's hosts),
    plus -- for a root task -- the request origins, carrying the workflow's input volume per second. This turns placement into
    a weighted k-median: f's containers are facilities, and what a layout costs is sum over demand points of
    weight x hops(demand point -> NEAREST container of f). Partner positions are read from the reference layout `cur`.
    Returns dem[F, N] in MB/s."""
    N, F = sc.network.ne, len(sc.functions)
    rates = expected_workflow_rates(sc) if rates is None else np.asarray(rates, dtype=float)
    cur = np.asarray(cur, dtype=int)
    aff = np.zeros((F, F))
    dem = np.zeros((F, N))
    for w, r in zip(sc.workflows, rates):
        for (u, v), size in w.ss.items():
            a, b = w.ft[u], w.ft[v]
            if a != b:
                aff[a, b] += r * size
                aff[b, a] += r * size
        if origin_weight and o_w is not None:
            for t in w.roots:
                dem[w.ft[t]] += origin_weight * r * w.input_size * np.asarray(o_w, dtype=float)
    for f in range(F):
        for g in np.flatnonzero(aff[f] > 0):
            hosts = np.flatnonzero(cur[:, g])
            if hosts.size:
                dem[f, hosts] += aff[f, g] / hosts.size
    return dem


def _cover_gain(dem_f, h, cur_min):
    """Reduction in sum_d dem_f[d] * nearest-hop(d) if a container of f were added to each node (vectorised over nodes)."""
    return (dem_f[:, None] * np.maximum(0.0, cur_min[:, None] - h)).sum(axis=0)


def queue_aware_placement(sc, rates=None, counts=None, cur=None, o_w=None, origin_weight=1.0, busy=None, tau=1.0,
                          queue_term=True, util_clip=0.97):
    """Capacity- and queue-aware incremental placement (2026-10-23): the k-median of `kmedian_placement` with a cost that
    knows containers have finite capacity.

    Why: k-median counts only the distance to the NEAREST container, so a function's demand is assumed to be served for free
    wherever it is closest. Measured in the simulator that objective does not predict P99 -- the binding constraint is queued
    state and dispatch flexibility, and a layout that is better on distance alone was 22.5% worse until the request moves were
    unlimited. This version prices both.

    Model for one function f with container counts c[n] on nodes n, demand points d (the same ones `demand_points` builds) and
    request rate r_d of f arriving at each (r_d = busy_f / mu_f, split by the demand-point weights):
      routing   a request at d goes to node n with probability p_dn = c_n exp(-hops_dn / tau) / sum_m c_m exp(-hops_dm / tau)
                (a smooth stand-in for the dispatcher: nearer and bigger nodes attract more, nothing is ever 'free')
      transfer  sum_d r_d sum_n p_dn hops_dn t_hop            seconds of state transfer per second
      queueing  sum_n lam_n mu_f u_n / (1 - u_n),  u_n = lam_n mu_f / c_n   M/M/1 per container, seconds of waiting per second
    (with p proportional to c_n the utilisation is the same on every container of a node, and independent of c_n).
    The layout cost is transfer + queueing, in seconds per second, for every function, so gains are comparable across
    functions. Growth picks the (function, node) pair with the largest cost reduction; shrinking removes the container whose
    loss is smallest; containers that need not move stay where they are (the incremental construction of the k-median).
    `queue_term=False` keeps the soft routing but drops the waiting term (ablation: isolates what the queue model adds)."""
    N, F = sc.network.ne, len(sc.functions)
    rates = expected_workflow_rates(sc) if rates is None else np.asarray(rates, dtype=float)
    mu = np.array([f.exec_time for f in sc.functions])
    h = sc.network.h.astype(float)
    ecc = sc.ecc.astype(int)
    S = int(ecc.sum())
    if counts is None:
        dm = np.zeros(F)
        for w, r in zip(sc.workflows, rates):
            for t in range(w.n):
                dm[w.ft[t]] += r * mu[w.ft[t]]
        counts = proportional_counts(dm, S)
    n_f = np.asarray(counts, dtype=int)
    assert n_f.sum() <= S and (n_f >= 1).all()
    cur = np.zeros((N, F), dtype=int) if cur is None else np.asarray(cur, dtype=int)
    ref = cur if cur.any() else np.ones((N, F), dtype=int)
    dem = demand_points(sc, rates, ref, o_w=o_w, origin_weight=origin_weight)
    busy = (0.8 * n_f.astype(float)) if busy is None else np.asarray(busy, dtype=float)
    ss = [s for w in sc.workflows for s in w.ss.values()]
    t_hop = sc.network.epd + (float(np.mean(ss)) if ss else 30.0) / sc.network.bw       # seconds per hop for a typical state
    W = np.exp(-h / float(tau))                                                         # [N, N] attraction between nodes
    B = W * h

    def share(f):
        """r_d for function f: requests per second arriving at each node (zeros where nothing pulls f)."""
        w = dem[f].copy()
        if w.sum() <= 0:
            w = np.ones(N)                                                              # no partner, no root: uniform demand
        return (busy[f] / mu[f]) * w / w.sum()

    def costs(f, c, delta):
        """Cost of f's layout c + delta[k] for every candidate k (delta: [K, N] one-hot additions/removals). Returns [K]."""
        r = share(f)
        active = np.flatnonzero(r > 0)
        ra, Wa, Ba = r[active], W[active], B[active]                                    # [D], [D, N], [D, N]
        cc = c[None, :] + delta                                                         # [K, N]
        Sd = cc @ Wa.T                                                                  # [K, D] sum_n c'_n W_dn
        Sd = np.maximum(Sd, 1e-12)
        transfer = ((cc @ Ba.T) / Sd * ra[None, :]).sum(axis=1) * t_hop                 # [K]
        if not queue_term:
            return transfer
        T = (1.0 / Sd) * ra[None, :] @ Wa                                               # [K, N] sum_d r_d W_dn / S'_d
        u = mu[f] * T                                                                   # utilisation per container, [K, N]
        lam = cc * T                                                                    # requests per second to node n
        uc = np.minimum(u, util_clip)
        wait = mu[f] * uc / (1.0 - uc) + 100.0 * mu[f] * np.maximum(0.0, u - util_clip)  # M/M/1 wait, steep beyond the clip
        return transfer + (lam * wait).sum(axis=1)

    X = cur.copy()
    for f in np.flatnonzero(cur.sum(axis=0) > n_f):                 # shrink: give up the container whose loss is smallest
        for _ in range(int(X[:, f].sum() - n_f[f])):
            hosts = np.flatnonzero(X[:, f] > 0)
            if X[:, f].sum() <= 1:
                break
            delta = np.zeros((len(hosts), N))
            delta[np.arange(len(hosts)), hosts] = -1.0
            cost = costs(f, X[:, f].astype(float), delta)
            X[hosts[int(np.argmin(cost))], f] -= 1
    free = ecc - X.sum(axis=1)
    need = n_f - X.sum(axis=0)
    assert (free >= 0).all() and need.sum() <= free.sum()

    gains, dirty = {}, set(np.flatnonzero(need > 0).tolist())
    while need.sum() > 0:
        avail = np.flatnonzero(free > 0)
        for f in list(dirty):
            c = X[:, f].astype(float)
            delta = np.zeros((len(avail), N))
            delta[np.arange(len(avail)), avail] = 1.0
            base = costs(f, c, np.zeros((1, N)))[0] if c.sum() > 0 else None
            new = costs(f, c, delta)
            g = np.full(N, -np.inf)
            g[avail] = (base - new) if base is not None else -new
            gains[f] = g
        dirty.clear()
        best, bf, bk = -np.inf, None, None
        for f in np.flatnonzero(need > 0):
            g = gains[int(f)].copy()
            g[free <= 0] = -np.inf
            k = int(np.argmax(g))
            if g[k] > best:
                best, bf, bk = float(g[k]), int(f), k
        if bf is None:
            bf = int(np.flatnonzero(need > 0)[0])
            bk = int(avail[0])
        X[bk, bf] += 1
        free[bk] -= 1
        need[bf] -= 1
        if need[bf] > 0:
            dirty.add(bf)
    assert (X.sum(axis=1) <= ecc).all() and (X.sum(axis=0) == n_f).all()
    return X


def _nearest_two(h, hosts):
    """(hops to the nearest host, hops to the nearest host other than the closest one) for every node."""
    d = np.sort(h[:, hosts], axis=1)
    big = h.max() + 1.0
    return d[:, 0], (d[:, 1] if d.shape[1] > 1 else np.full(d.shape[0], big))


def _two_opt(sc, X, dem, h, epoch, max_swaps, cap=None):
    """Improvement pass: exchange a container of f on node k for one on node j (and a container of g the other way, so every
    node keeps its slot count and every function keeps the count the sizing rule set). A swap is applied only while the
    state-transfer seconds per second it saves exceed the cold-start seconds it costs, amortised over the epoch -- so the
    layout keeps improving exactly as long as improving is cheaper than the churn it causes, with no tuning knob."""
    bw = sc.network.bw
    cs = np.array([f.cold_start for f in sc.functions])
    F = X.shape[1]
    swaps = 0
    for _ in range(int(max_swaps)):
        cand = None
        state = {}
        for f in range(F):
            hosts = np.flatnonzero(X[:, f])
            if hosts.size == 0:
                continue
            near, near2 = _nearest_two(h, hosts)
            gain = _cover_gain(dem[f], h, near)
            gain[hosts] = -np.inf                                  # already covered from there
            if cap is not None:
                gain[X[:, f] >= cap[f]] = -np.inf
            loss = {int(k): float((dem[f] * (np.where(h[:, k] <= near, np.minimum(near2, h[:, k]), near) - near)).sum())
                    if X[k, f] == 1 else 0.0 for k in hosts}       # a duplicate is free to move
            state[f] = (gain, loss)
        for f in range(F):
            if f not in state:
                continue
            gain_f, loss_f = state[f]
            j = int(np.argmax(gain_f))
            if not np.isfinite(gain_f[j]) or gain_f[j] <= 0:
                continue
            k = min(loss_f, key=loss_f.get)                        # the instance of f that is least useful where it is
            if k == j:
                continue
            for g in range(F):                                     # something must come back from j to k
                if g == f or g not in state or X[j, g] == 0:
                    continue
                gain_g, loss_g = state[g]
                if not np.isfinite(gain_g[k]):
                    continue
                net = (gain_f[j] - loss_f[k] + max(0.0, gain_g[k]) - loss_g.get(int(j), 0.0)) / bw
                price = (cs[f] + cs[g]) / float(epoch)
                if net > price and (cand is None or net - price > cand[0]):
                    cand = (net - price, f, g, int(k), int(j))
        if cand is None:
            break
        _, f, g, k, j = cand
        X[k, f] -= 1
        X[j, f] += 1
        X[j, g] -= 1
        X[k, g] += 1
        swaps += 1
    return swaps


def kmedian_placement(sc, rates=None, counts=None, cur=None, o_w=None, origin_weight=1.0, incremental=True,
                      improve=0, epoch=60.0, spread_cap=None):
    """Re-layout as an incremental weighted k-median (2026-10-23), replacing `affinity_greedy_placement`.

    Each function's containers are facilities; `demand_points` gives what they must be near (partners' nodes weighted by the
    state volume per second between the functions, and the request origins weighted by input volume for root tasks). A
    container is placed where it most reduces sum over demand points of weight x hops to the nearest container of that
    function -- a marginal-coverage greedy, the standard heuristic for this objective.

    `incremental` (the default) changes only what the new counts require: a function that shrinks gives up its least useful
    instances (duplicates on one node first -- a second copy costs nothing in coverage), a function that grows takes the
    freed slots that buy the most coverage, and every other container stays where it is. The number of conversions is then the
    smallest the counts allow, which is 2-6x fewer than rebuilding the layout from scratch.

    Why this and not the published rule: that rule scores a node by the hops to the nearest instance of each partner, which
    saturates once a partner sits on many nodes -- measured on live re-layouts, 98% of its decisions were tied between
    several nodes (mean 30 of 80) and the tie-break placed the container. Marginal coverage gain does not saturate: it falls
    to zero exactly where another instance already covers the demand. Why not a transportation/assignment formulation: the
    cost is a minimum over a function's containers, not a sum over them, so linearising it per container makes every
    container chase the same central nodes (measured: 2-3x worse transfer cost, see `transport_placement`)."""
    N, F = sc.network.ne, len(sc.functions)
    rates = expected_workflow_rates(sc) if rates is None else np.asarray(rates, dtype=float)
    mu = np.array([f.exec_time for f in sc.functions])
    h = sc.network.h.astype(float)
    ecc = sc.ecc.astype(int)
    S = int(ecc.sum())
    if counts is None:
        demand = np.zeros(F)
        for w, r in zip(sc.workflows, rates):
            for t in range(w.n):
                demand[w.ft[t]] += r * mu[w.ft[t]]
        counts = proportional_counts(demand, S)
    n_f = np.asarray(counts, dtype=int)
    assert n_f.sum() <= S and (n_f >= 1).all()                   # elastic capacity: fewer containers than slots is allowed
    cur = np.zeros((N, F), dtype=int) if cur is None else np.asarray(cur, dtype=int)
    ref = cur if cur.any() else np.ones((N, F), dtype=int)       # no layout yet: partners assumed everywhere
    dem = demand_points(sc, rates, ref, o_w=o_w, origin_weight=origin_weight)

    if incremental and cur.any():
        X = cur.copy()
        for f in np.flatnonzero(cur.sum(axis=0) > n_f):          # shrink: give up the least useful instances
            hosts = list(np.flatnonzero(X[:, f]))
            for _ in range(int(X[:, f].sum() - n_f[f])):
                dup = [k for k in hosts if X[k, f] > 1]
                if dup:                                           # a duplicate costs nothing in coverage
                    X[max(dup, key=lambda k: X[k, f]), f] -= 1
                    continue
                best = None
                for k in hosts:
                    if X[k, f] <= 0 or X[:, f].sum() <= 1:
                        continue
                    rest = [j for j in hosts if j != k and X[j, f] > 0]
                    if not rest:
                        continue
                    loss = float((dem[f] * (h[:, rest].min(axis=1) - h[:, hosts].min(axis=1))).sum())
                    if best is None or loss < best[0]:
                        best = (loss, k)
                if best is None:
                    break
                X[best[1], f] -= 1
                hosts = list(np.flatnonzero(X[:, f]))
    else:
        X = np.zeros((N, F), dtype=int)
        seed_free = ecc.copy()                                    # from scratch: one seed each, then marginal gain below
        for f in np.argsort(-dem.sum(axis=1)):                    # busiest demand first, and only onto a node with a free slot
            g = _cover_gain(dem[f], h, np.full(N, h.max() + 1.0))
            g[seed_free <= 0] = -np.inf
            k = int(np.argmax(g))
            X[k, f] += 1
            seed_free[k] -= 1
    free = ecc - X.sum(axis=1)
    need = n_f - X.sum(axis=0)
    assert (free >= 0).all() and need.sum() <= free.sum()

    big = h.max() + 1.0
    # spread_cap: at most this many containers of one function on one node. Pure coverage concentrates a function on the few
    # nodes nearest its partners, which exhausts those nodes' state storage and leaves the dispatcher no alternative host --
    # measured at 85% load: requests parked (0 -> 15 per run) and P99 38% worse despite a third of the cold starts.
    cap = None if spread_cap is None else np.maximum(1, np.asarray(spread_cap, dtype=int) * np.ones(F, dtype=int))
    gains, dirty = {}, set(np.flatnonzero(need > 0).tolist())
    while need.sum() > 0:
        avail = free > 0
        for f in list(dirty):
            hosts = np.flatnonzero(X[:, f])
            cur_min = h[:, hosts].min(axis=1) if hosts.size else np.full(N, big)
            g = _cover_gain(dem[f], h, cur_min)
            if cap is not None:
                g[X[:, f] >= cap[f]] = -np.inf
            g[~avail] = -np.inf
            gains[f] = g
        dirty.clear()
        best, bf, bk = -np.inf, None, None
        for f in np.flatnonzero(need > 0):
            g = gains[int(f)]
            g[~avail] = -np.inf
            if cap is not None:
                g[X[:, f] >= cap[f]] = -np.inf
            k = int(np.argmax(g))
            if g[k] > best:
                best, bf, bk = float(g[k]), int(f), k
        if bf is None:                                            # no gain anywhere (or the cap blocks every free node)
            bf = int(np.flatnonzero(need > 0)[0])
            ok = avail & ((X[:, bf] < cap[bf]) if cap is not None else True)
            bk = int(np.flatnonzero(ok if ok.any() else avail)[0])
        X[bk, bf] += 1
        free[bk] -= 1
        need[bf] -= 1
        dirty.add(bf)
        if need[bf] > 0:
            dirty.add(bf)
    if improve:
        _two_opt(sc, X, dem, h, epoch, improve, cap=cap)
    assert (X.sum(axis=1) <= ecc).all() and (X.sum(axis=0) == n_f).all()
    return X


def affinity_greedy_placement(sc, rates=None, counts=None):
    """D3 heuristic placement X [N, F] (instances of function f on node k), filling every container slot (invariant D-7).
    counts: optional instance count per function (sum = total slots); default proportional to expected busy slots."""
    N, F = sc.network.ne, len(sc.functions)
    rates = expected_workflow_rates(sc) if rates is None else np.asarray(rates, dtype=float)
    mu = np.array([f.exec_time for f in sc.functions])
    demand = np.zeros(F)                                     # expected busy slots per function
    aff = np.zeros((F, F))                                   # state volume per second between function types
    for w, r in zip(sc.workflows, rates):
        for t in range(w.n):
            demand[w.ft[t]] += r * mu[w.ft[t]]
        for (u, v), size in w.ss.items():
            a, b = w.ft[u], w.ft[v]
            if a != b:
                aff[a, b] += r * size
                aff[b, a] += r * size
    S = int(sc.ecc.sum())
    if counts is not None:
        n_f = np.asarray(counts, dtype=int)
        assert n_f.sum() == S and (n_f >= 1).all()
    else:
        n_f = proportional_counts(demand, S)
    X = np.zeros((N, F), dtype=int)
    free = sc.ecc.astype(int).copy()
    h = sc.network.h.astype(float)
    order = np.argsort(-aff.sum(axis=1))                     # most data-connected functions first
    placed = np.zeros((N, F), dtype=int)
    for f in order:
        for _ in range(int(n_f[f])):
            cost = np.zeros(N)
            for g in range(F):
                if aff[f, g] <= 0 or placed[:, g].sum() == 0:
                    continue
                nodes_g = np.flatnonzero(placed[:, g])
                cost += aff[f, g] * h[:, nodes_g].min(axis=1)
            cost = cost + 1e-6 * X[:, f] - 1e-9 * free      # tie-break: spread copies, prefer roomy nodes
            cost[free <= 0] = np.inf
            k = int(np.argmin(cost))
            X[k, f] += 1
            placed[k, f] += 1
            free[k] -= 1
    assert (X.sum(axis=1) == sc.ecc).all() and (X.sum(axis=0) == n_f).all()
    return X


class RecordingAdmission:
    """Wraps an admission callable (None = admit all) and logs (id, t, load, admitted) per arrival, load = requests in system
    / total container slots at the arrival instant (used by the D2 oracle O2H to find where a pass had slack)."""

    def __init__(self, inner=None):
        self.inner, self.log = inner, []

    def __call__(self, sim, req):
        ok = True if self.inner is None else bool(self.inner(sim, req))
        self.log.append((req.id, sim.now, (sim.active + len(sim.waiting)) / float(sim.sc.ecc.sum()), ok))
        return ok


class RejectSet:
    """Admission callable for the D2 oracle O2: reject exactly the request ids in `ids` (request ids are assigned in arrival
    order before the admission test, so they are stable across re-runs of the same scenario)."""

    def __init__(self, ids):
        self.ids = set(ids)

    def __call__(self, sim, req):
        return req.id not in self.ids


def faaspr_placement(sc, rates=None, counts=None, cur=None, hg_limit=4, aggre=1e-3, rng=None):
    """FaaSPR's placement (Jia et al., IEEE/ACM ToN 2025, Sec. IV: horizontal and vertical grouping + migration-minimizing placing),
    ported to our model (2026-10-24). Returns X [N, F] filling every slot.

    Kept from the paper: workflows are placed one after another in random order; per workflow, functions are merged into vertical
    groups greedily along the critical path (largest transfer edge first) while a feasible placement exists; every vertical group is
    cut into at most min(min_f n_f / hg_limit, #servers) horizontal groups of near-equal size (hg_limit = 4), and each horizontal
    group goes to the server with the highest priority = sum over its functions of (live instances reusable there / group share) x
    cold-start time + saved transfer to neighbouring functions already placed there (random routing assumed) + a tiny aggregation
    bonus for servers already holding the function. `cur` is the live layout (the paper's last placement).
    Adaptations: (1) the instance counts are given (our sizing) and split over the workflows that use a function in proportion to
    rate x occurrences (the paper's functions belong to one workflow); (2) a group must fit the server's free slots (the paper uses
    memory); (3) if the strict placement of a workflow is infeasible, groups are split in halves until they fit, so the layout
    always fills the slot budget exactly, as our invariant requires; (4) switch/foreach control logic is not modelled."""
    rng = np.random.default_rng(0) if rng is None else rng
    N, F = sc.network.ne, len(sc.functions)
    S = int(sc.ecc.sum())
    rates = expected_workflow_rates(sc) if rates is None else np.asarray(rates, dtype=float)
    n_f = np.asarray(counts, dtype=int)
    assert n_f.sum() == S and (n_f >= 1).all()
    cur = np.zeros((F, N), dtype=int) if cur is None else np.asarray(cur, dtype=int).T      # callers pass [N, F] (sim.cnt.T)
    cold = np.array([f.cold_start for f in sc.functions])
    mu = np.array([f.exec_time for f in sc.functions])
    hop = float(sc.network.h.mean())
    bw, epd = sc.network.bw, sc.network.epd
    W = len(sc.workflows)
    # 1. split each function's instances over the workflows that use it
    share = np.zeros((W, F))
    for w, (wf, r) in enumerate(zip(sc.workflows, rates)):
        for t in range(wf.n):
            share[w, wf.ft[t]] += max(r, 1e-9)
    nw = np.zeros((W, F), dtype=int)
    for f in range(F):
        s = share[:, f]
        if s.sum() <= 0:
            continue
        q = n_f[f] * s / s.sum()
        base = np.floor(q).astype(int)
        for w in np.argsort(-(q - base))[: n_f[f] - base.sum()]:
            base[w] += 1
        nw[:, f] = base
    placed = np.zeros((F, N), dtype=int)              # all workflows so far
    free = sc.ecc.astype(int).copy()

    def split(parts):
        """Cut a {function: count} dict in two halves (counts kept exact); None if it is a single instance."""
        a, b = {}, {}
        for f, c in parts.items():
            a[f] = (c + 1) // 2
            if c - a[f] > 0:
                b[f] = c - a[f]
        if not b:
            ks = list(parts)
            if len(ks) < 2:
                return None
            a, b = {ks[0]: parts[ks[0]]}, {k: parts[k] for k in ks[1:]}
        return a, b

    def priority(parts, P, nw_w, edge_w, free_loc):
        p = np.zeros(N)
        for f, c in parts.items():
            reuse = np.minimum(np.maximum(cur[f] - placed[f] - P[f], 0), c)
            p += reuse / c * cold[f]
            for g, wgt in edge_w.get(f, ()):
                if g not in parts and nw_w[g] > 0:
                    p += P[g] / nw_w[g] * wgt
            p += (placed[f] + P[f]) * aggre
        p[free_loc < sum(parts.values())] = -np.inf
        return p

    def hgroups(vg, nw_w):
        fs = [f for f in vg if nw_w[f] > 0]
        if not fs:
            return []
        hn = max(1, min(min(nw_w[f] // hg_limit for f in fs), N))
        out = []
        for i in range(hn):
            part = {f: nw_w[f] // hn + (1 if i < nw_w[f] % hn else 0) for f in fs}
            part = {f: c for f, c in part.items() if c > 0}
            if part:
                out.append(part)
        return out

    def place_wf(vgroups, nw_w, edge_w, strict):
        P = np.zeros((F, N), dtype=int)
        fr = free.copy()
        for vg in vgroups:
            todo = hgroups(vg, nw_w)
            while todo:
                parts = todo.pop(0)
                pr = priority(parts, P, nw_w, edge_w, fr)
                if np.isfinite(pr).any():
                    j = int(np.argmax(pr))
                elif strict:
                    return None
                else:
                    halves = split(parts)
                    if halves is None:
                        j = int(np.argmax(fr))                                   # one instance: any server with a free slot
                        assert fr[j] > 0
                    else:
                        todo = [halves[0], halves[1]] + todo
                        continue
                for f, c in parts.items():
                    P[f, j] += c
                fr[j] -= sum(parts.values())
        return P

    for w in [int(x) for x in rng.permutation(W)]:
        wf = sc.workflows[w]
        nw_w = nw[w]
        if nw_w.sum() == 0:
            continue
        edge_w = {}
        for (u, v), size in wf.ss.items():
            a, b = wf.ft[u], wf.ft[v]
            if a != b:
                wgt = (epd + size / bw) * hop
                edge_w.setdefault(a, []).append((b, wgt))
                edge_w.setdefault(b, []).append((a, wgt))
        fns = sorted({wf.ft[t] for t in range(wf.n) if nw_w[wf.ft[t]] > 0})
        vg_of = {f: i for i, f in enumerate(fns)}                                # vertical group id per function

        def crit_edges():
            fin = [0.0] * wf.n
            pred = [None] * wf.n
            for t in range(wf.n):
                best, bp = 0.0, None
                for u in wf.parents[t]:
                    c = fin[u] + (0.0 if vg_of.get(wf.ft[u]) == vg_of.get(wf.ft[t]) else (epd + wf.ss[(u, t)] / bw) * hop)
                    if c > best:
                        best, bp = c, u
                fin[t] = best + mu[wf.ft[t]]
                pred[t] = bp
            t = int(np.argmax(fin))
            es = []
            while pred[t] is not None:
                u = pred[t]
                if vg_of.get(wf.ft[u]) is not None and vg_of.get(wf.ft[t]) is not None and vg_of[wf.ft[u]] != vg_of[wf.ft[t]]:
                    es.append(((epd + wf.ss[(u, t)] / bw) * hop, wf.ft[u], wf.ft[t]))
                t = u
            return sorted(es, reverse=True)

        def groups():
            g = {}
            for f in fns:
                g.setdefault(vg_of[f], []).append(f)
            return list(g.values())

        merged = True
        while merged:
            merged = False
            for _, a, b in crit_edges():
                saved = dict(vg_of)
                old_b = vg_of[b]
                for f in fns:
                    if vg_of[f] == old_b:
                        vg_of[f] = vg_of[a]
                if place_wf(groups(), nw_w, edge_w, True) is not None:
                    merged = True
                    break
                vg_of.clear()
                vg_of.update(saved)
        P = place_wf(groups(), nw_w, edge_w, True)
        if P is None:
            P = place_wf(groups(), nw_w, edge_w, False)
        placed += P
        free -= P.sum(axis=0)
    # functions that no workflow uses still get at least one container from our sizing (FaaSPR would deploy none): place them
    # where a live instance can be reused, else on the server with the most free slots
    for f in range(F):
        for _ in range(int(n_f[f] - placed[f].sum())):
            cand = np.flatnonzero((free > 0) & (cur[f] - placed[f] > 0))
            j = int(cand[np.argmax(free[cand])]) if cand.size else int(np.argmax(free))
            placed[f, j] += 1
            free[j] -= 1
    assert (free == 0).all() and (placed.sum(axis=1) == n_f).all()
    return placed.T.copy()
