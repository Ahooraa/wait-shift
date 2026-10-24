"""D1 headroom controllers (plan faas-edge-adaptation, Task 11). All are evaluated by full simulation on the same scenario,
seeds and initial placement as B*.

P_true   ForecastAdjuster(true rates): B* (corrected DFPS annealing) at period T*, but the rates it sees (lam for the
         matching scheduler, req_count for Alg. 1's choice of f_r) are the TRUE mean rates of the next T* seconds.
         Operationalisation: DFPS's rates are per (function, node); the true per-function total is split over nodes in
         proportion to the measured share of the last window (uniform over the nodes holding f when there is no data).
P_fc     the same with a forecast = truth x lognormal multiplicative error, sigma in {0.25, 0.5, 1.0}, mean-one, drawn
         independently per (window, function). This is an error-controlled forecast; a seasonal-naive forecaster was not
         used because the synthetic family F3 has no seasonality and 15-min windows hold no season (logged deviation).
O1       offline trigger oracle: dynamic programming over 10-s slots. In every slot the system either keeps its current
         placement or switches to the placement computed from that slot's true rates (affinity_greedy_placement).
         Slot cost = expected request-seconds in system from the corrected queueing model (Erlang-C with P0 per function,
         instances pooled over nodes, A-10 fallback when unstable) x slot length; switching cost = for every new instance,
         its cold start x the utilisation it would have had. The chosen switch schedule is then applied in the simulator
         (Sim.apply_placement). Optimistic simplifications (documented): queues pooled per function, transfers ignored.
O1+B*    diagnostic (added 2026-10-15 after a smoke test where O1 lost to B*): O1's clairvoyant placement switches applied
         while B*'s annealing keeps running every T*. Tests whether perfect switch timing adds to B*, not part of the rule.
S_mean   diagnostic control (not in the decision rule): static affinity-greedy placement from the window-MEAN true rates.
         If S_mean ~ O1, the headroom is placement quality, not reconfiguration timing.
"""
from __future__ import annotations

import numpy as np

from .controllers import affinity_greedy_placement
from .queueing import fst
from .traces import function_rates, workflow_rates


def _split_over_nodes(sim, lam_f):
    """Per-(function, node) rates from per-function totals, using the measured spatial share of the last window."""
    meas = sim.buckets.sum(axis=0)                                   # [F, N] counts in the last window
    out = np.zeros((sim.F, sim.N))
    for f in range(sim.F):
        tot = meas[f].sum()
        if tot > 0:
            out[f] = lam_f[f] * meas[f] / tot
        else:
            hold = sim.cnt[f] > 0
            if hold.any():
                out[f, hold] = lam_f[f] / hold.sum()
    return out


class ForecastAdjuster:
    """B* annealing driven by a rate forecast for the next `period` seconds (P_true when sigma = 0, else P_fc)."""

    def __init__(self, inner, period, sigma=0.0, seed=0):
        self.inner, self.next_interval, self.sigma = inner, float(period), float(sigma)
        self.rng = np.random.default_rng(seed)
        self._err, self._err_window = None, None

    def forecast(self, sim):
        t0 = sim.now
        lam = function_rates(sim.sc, t0, t0 + self.next_interval)
        if self.sigma > 0:
            w = int(t0 // self.next_interval)
            if self._err_window != w:                                 # one error draw per (window, function)
                self._err = np.exp(self.rng.normal(-0.5 * self.sigma ** 2, self.sigma, len(lam)))
                self._err_window = w
            lam = lam * self._err
        return lam

    def lam_source(self, sim):
        return _split_over_nodes(sim, self.forecast(sim))

    def run(self, sim):
        lam = _split_over_nodes(sim, self.forecast(sim))
        sim.lam = lam
        sim.req_count[:] = np.rint(lam * self.next_interval).astype(int)   # Alg. 1 picks f_r by "requests in the interval"
        sim._fst_cache = {}
        return self.inner.run(sim)


# --------------------------------------------------------------------------------------------------------- O1
def erlang_c_time(lam, exec_time, c):
    """Mean time in system of an M/M/c queue, numerically stable for large c (Erlang-B recursion; equals
    queueing.fst(..., "prose") where that one does not overflow). Unstable or c = 0: the A-10 fallback of queueing.fst."""
    if c <= 0:
        return float("inf")
    if lam <= 0:
        return float(exec_time)
    mu = 1.0 / exec_time
    if lam >= c * mu:
        return exec_time / c + exec_time * (lam / (c * mu))          # A-10 (queued = 0), as in queueing.fst
    a = lam / mu
    B = 1.0
    for k in range(1, c + 1):
        B = a * B / (k + a * B)
    rho = a / c
    C = B / (1.0 - rho * (1.0 - B))
    return C / (c * mu - lam) + exec_time


def _queue_cost(sc, lam_f, n_f, slot_s):
    mu = np.array([f.exec_time for f in sc.functions])
    c = 0.0
    for f in range(len(lam_f)):
        if lam_f[f] <= 0:
            continue
        c += lam_f[f] * erlang_c_time(lam_f[f], mu[f], int(n_f[f])) * slot_s
    return c


def _switch_cost(sc, X_from, X_to, lam_f):
    mu = np.array([f.exec_time for f in sc.functions])
    cs = np.array([f.cold_start for f in sc.functions])
    new = np.maximum(0, X_to - X_from).sum(axis=0)                  # new instances per function (summed over nodes)
    n_to = np.maximum(1, X_to.sum(axis=0))
    util = np.minimum(1.0, lam_f * mu / n_to)
    return float((new * cs * util).sum())


def o1_schedule(sc, X0, duration_s, slot_s=10.0):
    """Offline DP. Returns (list of (time, X) switches, dict of diagnostics)."""
    S = int(np.ceil(duration_s / slot_s))
    lam = [function_rates(sc, s * slot_s, (s + 1) * slot_s) for s in range(S)]
    cand = [affinity_greedy_placement(sc, rates=np.maximum(workflow_rates(sc, s * slot_s, (s + 1) * slot_s), 1e-9))
            for s in range(S)]
    states = [X0] + cand                                             # state 0 = initial placement, state j = cand[j-1]
    qc = {}

    def qcost(s, j):
        key = (s, j)
        if key not in qc:
            qc[key] = _queue_cost(sc, lam[s], states[j].sum(axis=0), slot_s)
        return qc[key]

    INF = float("inf")
    best = {0: (qcost(0, 0), None)}                                  # state -> (cost so far, back-pointer (s_prev, state_prev))
    best[1] = (_switch_cost(sc, X0, states[1], lam[0]) + qcost(0, 1), (0, 0))
    hist = [dict(best)]
    for s in range(1, S):
        nxt = {}
        for j, (c, _) in best.items():                               # keep
            v = c + qcost(s, j)
            if v < nxt.get(j, (INF,))[0]:
                nxt[j] = (v, (s - 1, j))
        j_new = s + 1                                                # switch to this slot's placement
        cands = [(c + _switch_cost(sc, states[j], states[j_new], lam[s]), j) for j, (c, _) in best.items()]
        c_sw, j_from = min(cands)
        nxt[j_new] = (c_sw + qcost(s, j_new), (s - 1, j_from))
        best = nxt
        hist.append(dict(best))
    j_end = min(best, key=lambda j: best[j][0])
    path, s, j = [], S - 1, j_end
    while s >= 0:
        path.append(j)
        bp = hist[s][j][1]
        if bp is None:
            break
        s, j = bp
    path = path[::-1]
    switches, cur = [], 0
    for s, j in enumerate(path):
        if j != cur:
            switches.append((s * slot_s, states[j]))
            cur = j
    keep_cost = sum(qcost(s, 0) for s in range(S))
    return switches, dict(slots=S, n_switches=len(switches), model_cost=float(best[j_end][0]), model_cost_static_x0=float(keep_cost))


class ScheduleAdjuster:
    """Applies a precomputed switch schedule at slot boundaries (O1); never runs the annealing."""

    def __init__(self, switches, slot_s=10.0):
        self.switches = sorted(switches, key=lambda x: x[0])
        self.next_interval = float(slot_s)
        self.i = 0

    def run(self, sim):
        while self.i < len(self.switches) and self.switches[self.i][0] <= sim.now + 1e-9:
            sim.apply_placement(self.switches[self.i][1])
            self.i += 1
        return None


def s_mean_placement(sc, duration_s):
    return affinity_greedy_placement(sc, rates=np.maximum(workflow_rates(sc, 0.0, duration_s), 1e-9))


class ScheduleWithAnnealing:
    """O1+B*: apply the O1 switch schedule at slot boundaries and run B*'s annealing every `period` seconds."""

    def __init__(self, switches, inner, period, slot_s=10.0):
        self.sched = ScheduleAdjuster(switches, slot_s)
        self.inner, self.period = inner, float(period)
        self.next_interval = float(min(slot_s, period))
        self.next_sa = float(period)

    def run(self, sim):
        self.sched.run(sim)
        if sim.now + 1e-9 >= self.next_sa:
            self.next_sa += self.period
            return self.inner.run(sim)
        return None
