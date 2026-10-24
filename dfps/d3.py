"""D3 headroom (plan faas-edge-adaptation, Task 13; design option 2 chosen by the user on 2026-10-15).

O3 (surrogate-scored): every T* seconds generate K = 32 candidate placements by local search from the current one (the current
placement itself + 31 variants of 1-8 instance swaps, biased towards functions whose true upcoming load per instance is high) and
pick the one with the lowest surrogate cost; switch only if it beats keeping the current placement.

Surrogate = the corrected queueing model, coupled to dispatch through the placement:
  queueing   sum_{f,k} lam_fk * W(lam_fk, mu_f, n_fk), lam_fk = lam_f * n_fk / n_f   (Erlang-C with P0, stable form)
  transfer   sum over workflow edges (u, v) of rate_w * E[STT]: the source and target nodes are drawn in proportion to the instances
             of FT(u) and FT(v), E[STT] = p_u^T H p_v * size / bw  (the matching scheduler's dispatch, approximated)
  switching  every new instance: cold start x the utilisation it would have
both scaled to one period (T*), with the TRUE rates of the next period (the oracle part: it knows the upcoming requests' rates).

Kendall tau check: at sampled periods, 8 of the 32 candidates (chosen at random) are also scored by simulation: a clone of the live
system with the candidate applied runs forward for `horizon` seconds without re-planning; score = time-integral of requests in the
system (Little: request-seconds). tau(surrogate cost, simulated score) is averaged over the sampled periods.
"""
from __future__ import annotations

import copy
import heapq

import numpy as np

from .oracles import erlang_c_time
from .traces import function_rates, workflow_rates


class Surrogate:
    def __init__(self, sc):
        self.sc = sc
        self.mu = np.array([f.exec_time for f in sc.functions])
        self.cs = np.array([f.cold_start for f in sc.functions])
        self.H = sc.network.h.astype(float)
        self.bw = float(sc.network.bw)
        self.edges = [(w.id, w.ft[u], w.ft[v], size) for w in sc.workflows for (u, v), size in w.ss.items()]

    def cost(self, X, lam_f, wrate, period, X_from=None):
        """X: placement [N, F]. lam_f: true per-function rates of the next period; wrate: true per-workflow rates."""
        n_f = np.maximum(1, X.sum(axis=0))
        q = 0.0
        for f in np.flatnonzero(lam_f > 0):
            for k in np.flatnonzero(X[:, f]):
                lfk = lam_f[f] * X[k, f] / n_f[f]
                q += lfk * erlang_c_time(lfk, self.mu[f], int(X[k, f]))
        P = X / n_f[None, :]                                          # [N, F] node distribution of each function
        M = P.T @ self.H @ P                                          # [F, F] expected hops between two functions' instances
        tr = sum(wrate[w] * M[a, b] * size / self.bw for w, a, b, size in self.edges)
        sw = 0.0
        if X_from is not None:
            new = np.maximum(0, X - X_from).sum(axis=0)
            util = np.minimum(1.0, lam_f * self.mu / n_f)
            sw = float((new * self.cs * util).sum())
        return (q + tr) * period + sw


def candidates(X, lam_f, mu, rng, K=32, max_swaps=8):
    """The current placement + K-1 local-search variants (instance swaps on one node at a time)."""
    out = [X.copy()]
    N, F = X.shape
    load = lam_f * mu                                                 # busy instances needed per function
    for _ in range(K - 1):
        Y = X.copy()
        for _ in range(int(rng.integers(1, max_swaps + 1))):
            n_f = Y.sum(axis=0)
            press = (load + 1e-9) / np.maximum(n_f, 1)                # pressure: load per instance
            removable = np.flatnonzero(n_f > 1)
            if removable.size == 0:
                break
            w_rm = 1.0 / press[removable]
            f_r = int(rng.choice(removable, p=w_rm / w_rm.sum()))
            nodes = np.flatnonzero(Y[:, f_r])
            k = int(rng.choice(nodes))
            w_add = press / press.sum()
            f_n = int(rng.choice(F, p=w_add))
            if f_n == f_r:
                continue
            Y[k, f_r] -= 1
            Y[k, f_n] += 1
        out.append(Y)
    return out


class O3SurrogateAdjuster:
    """Applies the surrogate-best of K candidates every `period` seconds (never runs the DFPS annealing)."""

    def __init__(self, sc, period, K=32, seed=0, tau_every=0, tau_k=8, tau_horizon=None):
        self.s = Surrogate(sc)
        self.next_interval = float(period)
        self.K, self.rng = K, np.random.default_rng(seed)
        self.n_switch = 0
        self.tau_every, self.tau_k = tau_every, tau_k
        self.tau_horizon = float(tau_horizon) if tau_horizon else max(8.0, min(30.0, 2 * period))
        self.taus, self.n_periods = [], 0
        self.tau_rng = np.random.default_rng(seed + 10_000)        # separate stream: measuring tau never changes O3's decisions

    def run(self, sim):
        self.n_periods += 1
        X = sim.cnt.T.copy()
        t0, t1 = sim.now, sim.now + self.next_interval
        lam_f, wrate = function_rates(sim.sc, t0, t1), workflow_rates(sim.sc, t0, t1)
        cands = candidates(X, lam_f, self.s.mu, self.rng, self.K)
        costs = [self.s.cost(Y, lam_f, wrate, self.next_interval, X_from=X) for Y in cands]
        if self.tau_every and self.n_periods % self.tau_every == 0:
            self.taus.append(self.tau_at(sim, cands, costs))
        best = int(np.argmin(costs))
        if best != 0 and costs[best] < costs[0]:
            sim.apply_placement(cands[best])
            self.n_switch += 1
        return None

    def tau_at(self, sim, cands, costs):
        idx = self.tau_rng.choice(len(cands), size=min(self.tau_k, len(cands)), replace=False)
        sims = [simulate_candidate(sim, cands[i], self.tau_horizon) for i in idx]
        return kendall_tau_b([costs[i] for i in idx], sims)


def kendall_tau_b(x, y):
    """Kendall's tau-b (ties handled); implemented here because importing scipy.stats next to PyTorch loads a second OpenMP
    runtime on this machine (OMP Error #15)."""
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    n = len(x)
    c = d = tx = ty = 0
    for i in range(n):
        for j in range(i + 1, n):
            a, b = np.sign(x[i] - x[j]), np.sign(y[i] - y[j])
            if a == 0 and b == 0:
                continue
            if a == 0:
                tx += 1
            elif b == 0:
                ty += 1
            elif a == b:
                c += 1
            else:
                d += 1
    den = np.sqrt((c + d + tx) * (c + d + ty))
    return float((c - d) / den) if den > 0 else float("nan")


def simulate_candidate(sim, X, horizon):
    """Clone the live system (scenario shared), apply X, run `horizon` seconds without re-planning; return request-seconds."""
    h, adj = sim._hash, sim.adjuster
    sim._hash, sim.adjuster = None, None
    try:
        c = copy.deepcopy(sim, {id(sim.sc): sim.sc})
    finally:
        sim._hash, sim.adjuster = h, adj
    c.apply_placement(X)
    end, area, last = sim.now + horizon, 0.0, sim.now
    while c.events and c.events[0][0] < end:
        t, _, kind, a, b, cc = heapq.heappop(c.events)
        area += c.active * (t - last)
        last = t
        c.now = t
        if kind == "adjust":
            continue
        getattr(c, "_ev_" + kind)(a, b, cc)
    area += c.active * (end - last)
    return float(area)
