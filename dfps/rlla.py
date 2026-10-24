"""RL + look-ahead cheater "RLLA" (2026-10-18): how much room is there above the best existing method (RL)?

RL places every task exactly as the trained policy does (no change to RL itself). On top, every `epoch` seconds the cheater may
PRE-WARM containers: start containers of functions whose load in the near future exceeds their warm and running containers, so
the coming requests find them warm. This is the on-demand counterpart of D1's "move capacity before the shift". It chooses among a
few pre-warm plans by cloning the live simulator and replaying the TRUE upcoming arrivals for `horizon` seconds (RL deciding as
usual inside the clone), scored by request-seconds in the system (as O3S). Clairvoyance: the true future rates (plans) and arrivals
(scoring); execution times in a clone come from the clone's own random stream.

Candidate plans per epoch (applied until the next epoch):
  none     plain RL (least-recently-used eviction when a node is full)
  evict    future-aware eviction: when a node is full, recycle the idle container whose function has the least upcoming demand per
           container over the next `lead` seconds (Belady-style clairvoyant replacement)
  evict+pw future-aware eviction and pre-warming: functions whose expected busy containers over the next `lead` seconds (x 1.5)
           exceed their containers get new ones on the nodes with the most free slots
"""
from __future__ import annotations

import copy
import heapq
import math

import numpy as np

from .traces import function_rates

MARGINS = (0.5,)


def plan_prewarm(sim, lead, margin):
    """List of (f, k) containers to start now."""
    lam = function_rates(sim.sc, sim.now, sim.now + lead)
    need = np.ceil((1.0 + margin) * lam * sim.exec_time - 1e-9).astype(int)
    have = np.array([sum(len(sim.inst[k][f]) for k in range(sim.N)) for f in range(sim.F)])
    free = (sim.ecc - sim.tot).astype(int).copy()
    plan = []
    for f in np.argsort(-(need - have)):
        d = int(need[f] - have[f])
        for _ in range(max(0, d)):
            cnt_f = np.array([len(sim.inst[k][f]) for k in range(sim.N)])
            k = int(np.lexsort((cnt_f, -free))[0])
            if free[k] <= 0:
                break
            plan.append((int(f), k))
            free[k] -= 1
    return plan


def clone(sim):
    memo = {id(sim.sc): sim.sc}
    pol = sim.policy
    if hasattr(pol, "q"):
        memo[id(pol.q)] = pol.q                                      # share the (read-only) Q-network
    h, la = sim._hash, sim.lookahead
    sim._hash, sim.lookahead = None, None
    try:
        c = copy.deepcopy(sim, memo)
    finally:
        sim._hash, sim.lookahead = h, la
    return c


def future_evict_score(sim, lead):
    lam = function_rates(sim.sc, sim.now, sim.now + lead)
    have = np.array([sum(len(sim.inst[k][f]) for k in range(sim.N)) for f in range(sim.F)], dtype=float)
    return lam * sim.exec_time / np.maximum(1.0, have)


def score(sim, plan, horizon, evict=None, budget=None):
    c = clone(sim)
    c.evict_score = evict
    c.recycle_budget = None if budget is None else np.full(c.N, float(budget))
    for f, k in plan:
        c.prewarm(f, k)
    end, area, last = sim.now + horizon, 0.0, sim.now
    while c.events and c.events[0][0] < end:
        t, _, kind, a, b, cc = heapq.heappop(c.events)
        area += c.active * (t - last)
        last = t
        c.now = t
        if kind == "epoch":
            continue
        getattr(c, "_ev_" + kind)(a, b, cc)
    area += c.active * (end - last)
    return float(area)


class LookAhead:
    def __init__(self, epoch=30.0, horizon=120.0, lead=60.0, margins=MARGINS, rel_margin=0.02, budgets=()):
        self.epoch, self.horizon, self.lead, self.margins, self.rel_margin = epoch, horizon, lead, margins, rel_margin
        self.budgets = budgets
        self.log = []

    def decide(self, sim):
        ev = future_evict_score(sim, self.lead)
        plans = {"none": ([], None), "evict": ([], ev)}
        for m in self.margins:
            plans[f"evict+pw{m}"] = (plan_prewarm(sim, self.lead, m), ev)
        # anti-churn: each node may recycle at most B containers during the next epoch (B = 0: never evict another function)
        budgets = {"none": None, "evict": None}
        for b in self.budgets:
            plans[f"limit{b}"] = ([], ev)
            budgets[f"limit{b}"] = b
        for m in self.margins:
            budgets[f"evict+pw{m}"] = None
        scores = {n: score(sim, p, self.horizon, e, budgets[n]) for n, (p, e) in plans.items()}
        best = min(scores, key=scores.get)
        if best == "none" or scores[best] >= (1.0 - self.rel_margin) * scores["none"]:
            best = "none"
        p, e = plans[best]
        sim.evict_score = e
        sim.recycle_budget = None if budgets[best] is None else np.full(sim.N, float(budgets[best]))
        for f, k in p:
            sim.prewarm(f, k)
        self.log.append(dict(t=sim.now, chosen=best, n_prewarm=len(p), keep=scores["none"], best_score=scores[best]))


def attach_lookahead(sim, la, first=60.0):
    """Give an OnDemandSim an epoch event that calls the look-ahead (inside the measured window only)."""
    sim.lookahead = la

    def _ev_epoch(a, b, c, sim=sim):
        if sim.lookahead is not None and sim.now < sim.duration:
            sim.lookahead.decide(sim)
        if sim.now + sim.lookahead_epoch < sim.duration:
            sim._at(sim.now + sim.lookahead_epoch, "epoch")

    sim.lookahead_epoch = la.epoch
    sim._ev_epoch = _ev_epoch
    sim._at(first, "epoch")
