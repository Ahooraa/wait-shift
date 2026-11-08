"""D3 oracle O3S: simulation-scored placement switches on top of B* (design: output/data-analysis/sim/D3_O3S_design.md,
approved by the user 2026-10-17; a logged deviation from the pre-registered surrogate O3).

B* runs unchanged every `period` (T*). Every `epoch` seconds O3S builds K candidate placements, clones the live simulator once per
candidate, applies it, and runs the clone `horizon` seconds forward on the TRUE upcoming arrivals with the real matching scheduler
and no re-planning. Score = request-seconds in the system over the horizon (Little), so queueing, dispatch, transfers and the
cold starts of the switch all count. O3S switches to the best candidate if it beats "keep" by more than `margin` (relative).
Execution times in a clone come from the clone's own random stream (copied from the live one), not from the realised run.
"""
from __future__ import annotations

import bisect
import copy
import heapq

import numpy as np
from .solution import IDLE

from .controllers import (affinity_greedy_placement, affinity_placement_v2, demand_points, kmedian_placement, origin_weights,
                          proportional_counts, queue_aware_placement, faaspr_placement, faaspr_placement_w, placement_cost)
from .d3 import candidates, kendall_tau_b
from .traces import function_rates, workflow_rates


def clone_score(sim, X, horizon, seed=None, fc=None):
    """Clone the live system (scenario shared), apply X, run `horizon` s without re-planning; return request-seconds."""
    h, adj = sim._hash, sim.adjuster
    sim._hash, sim.adjuster = None, None
    try:
        c = copy.deepcopy(sim, {id(sim.sc): sim.sc})
    finally:
        sim._hash, sim.adjuster = h, adj
    if seed is not None:
        c.rng = np.random.default_rng(seed)
    if fc is not None:                                    # blind: replace the true upcoming arrivals by the forecast ones
        c.events = [e for e in c.events if not (e[2] == "arrive" and e[0] >= sim.now)]
        heapq.heapify(c.events)
        for t_, wid, origin in fc:
            c._at(t_, "arrive", wid, origin)
    if X is not None:
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


def backlog_per_function(sim):
    """Queued runs of each function over all nodes."""
    return np.array([sum(len(sim.queue[k][f]) for k in range(sim.N)) for f in range(sim.F)], dtype=float)


def random_placement(sc, counts, rng):
    """Ablation: the same per-function counts, but containers dropped on random nodes with free slots (no data affinity)."""
    if not np.allclose(sc.fw, 1.0):
        raise NotImplementedError("random_placement (ablation) assumes equal container sizes")
    N, F = sc.network.ne, len(sc.functions)
    X = np.zeros((N, F), dtype=int)
    free = sc.ecc.astype(int).copy()
    for f in rng.permutation(np.repeat(np.arange(F), np.asarray(counts, dtype=int))):
        k = int(rng.choice(np.flatnonzero(free > 0)))
        X[k, f] += 1
        free[k] -= 1
    assert (X.sum(axis=1) == sc.ecc).all() and (X.sum(axis=0) == np.asarray(counts)).all()
    return X


def apply_hold_floor(need, floor, demand, util_cap):
    """Raise `need` to at least `floor` (containers held after an emergency fix), paying with the functions that have the most slack
    above max(1, their own need, their floor). If the slack cannot cover it, the floors are only partly honoured."""
    need = need.astype(int).copy()
    want = np.maximum(need, np.asarray(floor, dtype=int))
    deficit = int((want - need).sum())
    if deficit <= 0:
        return need
    own = np.maximum(1, np.ceil(demand / util_cap)).astype(int)
    slack = np.maximum(0, need - np.maximum(own, np.asarray(floor, dtype=int)))
    slack[want > need] = 0
    out = want.copy()
    for f in np.argsort(-slack):
        if deficit <= 0 or slack[f] <= 0:
            break
        take = min(int(slack[f]), deficit)
        out[f] -= take
        deficit -= take
    if deficit > 0:                                                   # not enough slack: lower the raised floors back
        for f in np.flatnonzero(want > need):
            if deficit <= 0:
                break
            give = min(int(out[f] - need[f]), deficit)
            out[f] -= give
            deficit -= give
    return out


def bottleneck_first_placement(sim, lam_f, horizon, util_cap=0.8, wf_rate=None, rng=None, place=None, elastic=False,
                                hold_floor=None, sizing_cache=None):
    """Hot functions first: enough instances to keep utilisation <= util_cap for the upcoming load (lam_f, the oracle
    rate -- an exogenous property of the scenario's trace, never of this sim's own queues: problem-scope.md S3,
    "the autoscaler is an input, not a contribution"); remaining (fw-weighted) budget proportional to that demand;
    nodes by data affinity. `place`: None = the published affinity rule; a dict = `affinity_placement_v2` keyword
    arguments (keep / origin / softmin).
    2026-10-27 fix: `demand` used to add backlog_per_function(sim) * mu / horizon -- the system's OWN observed queue
    backlog, which differs by placement quality (worse placement -> more backlog -> more containers reallocated to
    compensate). That fed each variant's placement quality back into its own sizing, diluting the exact signal the
    FaaSPR comparison measures (live in this function, shared by all four variants via cand_mode="nosim"). Removed;
    `demand` is now a pure function of the trace. `sizing_cache`: an optional dict shared across several Sim runs of
    the SAME scenario+seed -- makes "the same schedule, replayed identically to every system" literal rather than
    merely incidental to the formula's purity: whichever variant reaches a given sim time first computes it, every
    later one at that same time reuses the cached array."""
    sc = sim.sc
    mu = np.array([f.exec_time for f in sc.functions])
    demand = lam_f * mu                                                 # exogenous: oracle rate x nominal exec time only
    key = round(sim.now, 6) if sizing_cache is not None else None
    need = sizing_cache.get(key) if key is not None else None
    if need is None:
        S = float(sc.ecc.sum())
        need = np.maximum(1, np.ceil(demand / util_cap).astype(int))
        if float(need @ sc.fw) > S:                                     # cannot satisfy everyone: shrink proportionally
            need = proportional_counts(demand, S, fw=sc.fw)
        elif not elastic:
            need = proportional_counts(demand, S, floor=need, fw=sc.fw)  # fixed budget: leftover follows demand
        # elastic: the sizing rule's own count is the answer; slots beyond it stay empty (no container, no cost)
        if key is not None:
            sizing_cache[key] = need
    if hold_floor is not None and (np.asarray(hold_floor) > need).any():
        if elastic:
            # on-demand (6 Nov 2026): the held containers are extra, no function pays for them; if they do not all fit the cluster, the held
            # increments are trimmed, heaviest first, until they do (apply_hold_floor counts containers, not weight, so it cannot be used here)
            want = np.maximum(need, np.asarray(hold_floor, dtype=int))
            fwv, cap = np.asarray(sc.fw, dtype=float), float(sc.ecc.sum())
            while float(want @ fwv) > cap + 1e-9 and (want > need).any():
                g = int(np.argmax(np.where(want > need, (want - need) * fwv, -1.0)))
                want[g] -= 1
            need = want
        else:
            need = apply_hold_floor(need, hold_floor, demand, util_cap)
    rates = np.maximum(workflow_rates(sc, sim.now, sim.now + horizon) if wf_rate is None else wf_rate, 1e-9)
    if rng is not None:
        return random_placement(sc, need, rng)
    if place:
        if place.pop("faaspr", False):                                  # FaaSPR's grouping + migration-minimizing placement (port)
            return faaspr_placement(sc, rates=rates, counts=need, cur=sim.cnt.T, **place)
        if place.pop("qaware", False):                                  # capacity- and queue-aware (needs the busy slots per function)
            place.pop("elastic_qaware", None)                           # a baseline_layout flag (hpa modes), not a placement argument
            return queue_aware_placement(sc, rates=rates, counts=need, cur=sim.cnt.T, busy=demand, **place)
        fn = kmedian_placement if place.pop("kmedian", False) else affinity_placement_v2
        return fn(sc, rates=rates, counts=need, cur=sim.cnt.T, **place)
    return affinity_greedy_placement(sc, rates=rates, counts=need)


def limit_changes(cur, target, cap):
    """Apply at most `cap` of the 1-for-1 container replacements needed to go from cur to target, those that fill the largest
    function gaps first (never removing a function's last instance)."""
    gap = target.sum(axis=0) - cur.sum(axis=0)                       # per function: how many more containers it should have
    pairs = []
    for k in range(cur.shape[0]):
        d = target[k] - cur[k]
        dec = [f for f in np.argsort(d) if d[f] < 0 for _ in range(int(-d[f]))]
        inc = [f for f in np.argsort(-d) if d[f] > 0 for _ in range(int(d[f]))]
        pairs += [(gap[f_n], k, f_r, f_n) for f_r, f_n in zip(dec, inc)]
    pairs.sort(key=lambda p: -p[0])
    X = cur.copy()
    for _, k, f_r, f_n in pairs[:int(cap)]:
        if X[:, f_r].sum() <= 1:
            continue
        X[k, f_r] -= 1
        X[k, f_n] += 1
    return X


def _fit_counts(need, demand, S, fw=None):
    """Fit per-function container needs to the fixed slot budget S (every function keeps >= 1): if the needs fit, they are a floor and
    the leftover slots follow `demand`; if they exceed S, all slots are split in proportion to `demand`. fw: per-function container
    weight (heterogeneous sizes; S is then in the same units); None = one slot per container."""
    need = np.maximum(1, np.asarray(need, dtype=int))
    demand = np.asarray(demand, dtype=float)
    if (float(need @ np.asarray(fw, dtype=float)) if fw is not None else need.sum()) > S:
        return proportional_counts(demand, S, fw=fw)
    return proportional_counts(demand, S, floor=need, fw=fw)


def _dag_weights(sc):
    """Kraken-style DAG weights per function: Connectivity = descendants / tasks (mean over the function's occurrences),
    Commonality = share of the workflows that contain the function."""
    F = len(sc.functions)
    conn, occ, comm = np.zeros(F), np.zeros(F), np.zeros(F)
    for w in sc.workflows:
        desc = [set() for _ in range(w.n)]
        for t in range(w.n - 1, -1, -1):                              # tasks are in topological order
            for c in w.children[t]:
                desc[t] |= {c} | desc[c]
        seen = set()
        for t in range(w.n):
            f = w.ft[t]
            conn[f] += len(desc[t]) / w.n
            occ[f] += 1
            if f not in seen:
                comm[f] += 1.0 / len(sc.workflows)
                seen.add(f)
    return conn / np.maximum(occ, 1), comm


def baseline_layout(sim, lam_f, wf_rate, kind, clear_s=120.0, util_cap=0.8, kraken_cap=0.25, elastic=False, place=None, rng=None):
    """Published container-sizing rules as whole-layout rules on our fixed slot budget (2026-10-22). All take the same observed
    load (last 2 min) as busiest-first and are placed by the same data-affinity routine, so only the sizing rule differs.
      hpa     Kubernetes HPA / Knative target utilisation: containers = ceil(load / 0.8), no backlog term.
      fifer   Fifer RScale (Gunasekaran 2020): containers for the load plus ceil(queue length / batch size) for the backlog, added only
              if the queue's drain time exceeds the function's cold start (Df > Cd); batch size = slack / exec time = slo_factor - 1
              (slack split in proportion to run time). The LSTM proactive part is not used (no forecasting anywhere in this comparison).
      kraken  Kraken weights (Bhasi 2021): containers = ceil(load) + ceil((Connectivity + Commonality) x ceil(load)); both capped
              (cap = 0.25, the paper does not give the value); invocation probabilities are 1 (our DAGs are static)."""
    sc = sim.sc
    mu = np.array([f.exec_time for f in sc.functions])
    cs = np.array([f.cold_start for f in sc.functions])
    S = int(sc.ecc.sum())
    load = lam_f * mu
    backlog = backlog_per_function(sim)
    if kind == "hpa":
        need, demand = np.ceil(load / util_cap), load
    elif kind == "concurrency":                                          # FaaSPR's scaler (Sec. II-A): concurrency = request rate x duration
        need, demand = np.ceil(load), load
    elif kind == "fifer":
        B = max(1.0, np.floor(sim.slo_factor - 1.0))
        n_cur = np.maximum(1, sim.cnt.sum(axis=1)).astype(float)
        sr = sim.slo_factor * mu                                           # per-stage response budget = slack + exec time
        df = backlog * sr / (n_cur * B)                                    # queuing delay Df = Td / L
        extra = np.where(df > cs, np.ceil(backlog / B), 0.0)
        need, demand = np.ceil(load) + extra, load + extra
    elif kind == "kraken":
        conn, comm = _dag_weights(sc)
        req = np.ceil(load)
        extra = np.ceil((np.minimum(conn, kraken_cap) + np.minimum(comm, kraken_cap)) * req)
        need, demand = req + extra, req + extra
    else:
        raise ValueError(kind)
    if elastic:                                                          # the rule's own container count; slots beyond it stay empty
        need = np.maximum(1, np.asarray(need, dtype=int))
        n_f = proportional_counts(np.maximum(demand, 1e-9), S, fw=sc.fw) if float(need @ sc.fw) > S else need
        if place and place.get("faaspr_w"):                              # FaaSPR's own placement, weighted capacity (FP-2)
            return faaspr_placement_w(sc, rates=np.maximum(wf_rate, 1e-9), counts=n_f, cur=sim.cnt.T, rng=place.get("rng"))
        if place and place.get("elastic_qaware"):                        # on-demand re-comparison (6 Nov 2026): keep the data-affinity (qaware) placement, counts not filled
            place = {k: v for k, v in place.items() if k != "elastic_qaware"}
            place.pop("qaware", None)
            return queue_aware_placement(sc, rates=np.maximum(wf_rate, 1e-9), counts=n_f, cur=sim.cnt.T, busy=demand, **place)
        return kmedian_placement(sc, rates=np.maximum(wf_rate, 1e-9), counts=n_f, cur=sim.cnt.T, origin_weight=0.0)
    n_f = _fit_counts(need, np.maximum(demand, 1e-9), S, fw=sc.fw)
    if rng is not None:                                                  # data-oblivious placement (off-the-shelf stack)
        return random_placement(sc, n_f, rng)
    if place and place.get("faaspr_w"):                                  # FaaSPR's own placement, weighted capacity (FP-2), counts from the same sizing
        return faaspr_placement_w(sc, rates=np.maximum(wf_rate, 1e-9), counts=n_f, cur=sim.cnt.T, rng=place.get("rng"))
    if place and place.get("faaspr"):
        place = dict(place)
        place.pop("faaspr")
        return faaspr_placement(sc, rates=np.maximum(wf_rate, 1e-9), counts=n_f, cur=sim.cnt.T, **place)
    if place and place.get("qaware"):                                    # final controller's incremental soft-routing placement
        place = dict(place); place.pop("qaware")
        return queue_aware_placement(sc, rates=np.maximum(wf_rate, 1e-9), counts=n_f, cur=sim.cnt.T, busy=demand, **place)
    return affinity_greedy_placement(sc, rates=np.maximum(wf_rate, 1e-9), counts=n_f)


def half_way(cur, target):
    """Move each node half-way from cur to target: apply the larger half of the 1-for-1 instance replacements."""
    X = cur.copy()
    for k in range(cur.shape[0]):
        d = target[k] - cur[k]
        dec = [f for f in np.argsort(d) if d[f] < 0 for _ in range(int(-d[f]))]
        inc = [f for f in np.argsort(-d) if d[f] > 0 for _ in range(int(d[f]))]
        n = (min(len(dec), len(inc)) + 1) // 2
        for f_r, f_n in zip(dec[:n], inc[:n]):
            if X[:, f_r].sum() <= 1:                                    # never remove a function's last instance
                continue
            X[k, f_r] -= 1
            X[k, f_n] += 1
    return X


class O3SimAdjuster:
    def __init__(self, inner, period, epoch=30.0, horizon=30.0, K=8, margin=0.02, seed=0, tau_checks=0, warmup=60.0, blind=False, future=None, cand_mode="full", churn=None, sizing_cache=None):
        self.inner, self.period = inner, float(period)
        self.epoch, self.horizon, self.K, self.margin = float(epoch), float(horizon), int(K), float(margin)
        self.next_interval = float(min(period, epoch))
        self.next_sa, self.next_dec = float(period), float(warmup)
        self.rng = np.random.default_rng(seed)
        self.tau_checks, self.tau_seed = int(tau_checks), seed + 10_000
        self.log, self.taus, self.n_switch = [], [], 0
        # future: "exact" = replay the true upcoming arrivals (the oracle); "persist" = copy the last min(horizon, now) seconds
        # (first blind attempt, kept for reference); "rate" = rate oracle: replay a FRESH Poisson draw from the true rate series,
        # so the clone knows where traffic is heading but not the random arrival clumps (2026-10-20).
        self.future = future or ("persist" if blind else "exact")
        self.blind, self._fc = self.future == "persist", None
        self.fc_rng = np.random.default_rng(seed + 20_000)
        # cand_mode (mechanism ablations / speed study, 2026-10-21):
        #   full            keep, affinity, bottleneck, two half-way moves, all judged by the clone (the O3S design)
        #   nosim           ablation 1: apply the busiest-first layout every epoch, NO simulation check
        #   local_sim       ablation 2: clone-judge only small DFPS-style swap variants of the current layout (no big moves)
        #   keep_bottleneck speed study: clone-judge only keep vs busiest-first (2 clones per decision)
        self.cand_mode = cand_mode
        self.clear_s = 120.0
        # churn controls for the busiest-first rule ('nosim' mode only; 2026-10-21, user concern about migration / cold-start cost):
        #   min_frac     skip the re-layout unless at least this fraction of all container slots would change
        #   cap          change at most this many containers per re-layout (largest function gaps first)
        #   min_backlog  skip the re-layout unless the queued runs reach this fraction of all container slots
        self.churn = dict(min_frac=0.0, cap=None, min_backlog=0.0)
        self.churn.update(churn or {})
        self._times, self._last_fast, self.fast_log = None, -1e9, []
        self.hold, self._burstiness = {}, 0.0
        # sizing_cache (2026-10-27 fix, problem-scope.md S3/S6): an optional dict shared across several Sim runs of the
        # SAME scenario+seed (e.g. the FaaSPR-comparison variants). bottleneck_first_placement's target counts are now
        # a pure function of the scenario/trace (no backlog term -- see its docstring); this cache makes "compute the
        # schedule once, replay identically to every system" literal rather than merely incidental to that purity.
        self.sizing_cache = sizing_cache
        self._pending = []                               # (apply_at, layout) of re-layouts held back by relayout_delay            # held counts {function: (containers, until)}; smoothed |short - long| / long
        self.warmup = float(warmup)                                 # the measured window opens here (fast_step acts only inside it)
        # rule ablation (2026-10-22): utilisation target, backlog-clearing horizon, placement ("random" = no data affinity)
        self.util_cap = float(self.churn.get("util_cap", 0.8))
        self.clear_s = float(self.churn.get("clear_s", self.clear_s))
        self.staleness_log = []                           # (now, mismatch) if churn["log_staleness"]: diagnostic, 2026-10-25
        self.calib_log = []                               # (now, proxy_mismatch, true_mismatch) if churn["calibrate_placement"]
        self.gain_log = []                                # (now, gain_s) per accepted finish-time move, if churn["log_gain"] -- 2026-10-25
        self.ctx_log = []                                 # (pass, now, f, mu, cur ahead/cnt/parts, [(k2, parts, ahead, cnt)], accepted_k2), every decision of every 4th pass, if churn["log_move_ctx"] -- 2026-11-02
        self.lambda_log = []                              # (now, cur_parts, [(k2, parts)], accepted_k2) per evaluated decision, if churn["log_lambda_components"] -- 2026-10-26
        self._calib_left = int(self.churn.get("calibrate_placement_n", 15))
        self._calib_tick = 0
        # mover implementation tag (2026-11-04), recorded in every result like capacity_model: MV-2 = vectorised request mover
        # (_rebalance_fast, the default), MV-1 = the original loop. MV-2 reproduces MV-1 field by field (6 of 6 full-length cases,
        # 250 s on 2 more); results without a tag are MV-1.
        self.mover_impl = ("MV-2" if (self.churn.get("fast_rebal", True) and self._fast_ok() and self.churn.get("rebal_rule", "aet") == "aet"
                                      and not self.churn.get("move_terms")) else "MV-1")
        if self.churn.get("fast_order") and self.churn.get("pass_order") == "gain" and self._fast_ok():
            self.mover_impl = "MV-3"                                    # 7 Nov 2026: gain-ordered pass with per-function estimate arrays; event hashes equal MV-2
        # re-layout scoring tag (7 Nov 2026), recorded in every result: PL-1 = exact scoring of every candidate (all results before this tag),
        # PL-1f = fast_place (same formula, rounding can tip exact ties), PL-2 = lazy scoring (re-price only the candidate about to be accepted),
        # PL-3 = lazy + thinning to place_thin hosts per function.
        self.place_impl = ("PL-3" if int(self.churn.get("place_thin", 0)) > 0 else "PL-2" if self.churn.get("lazy_place")
                           else "PL-1f" if self.churn.get("fast_place") else "PL-1")
        # pass order of the request mover (2026-11-04), recorded in every result: "gain" (FROZEN-3) or "count" (FROZEN-2 and earlier;
        # results without the field are "count")
        self.mover_pass = "gain" if (self.churn.get("pass_order") == "gain" and self._fast_ok()) else "count"

    def _staleness(self, sim):
        """Diagnostic (2026-10-25): mismatch between the LIVE layout and what sizing would choose if re-solved right now from the
        controller's own blind window rates (same formula as bottleneck_first_placement's demand/need, no placement run -- cheap).
        Returns sum|live - ideal| / slots, in [0, ~2]. Logged at the move-period cadence (self.next_sa) between re-layouts, to see
        whether drift grows steadily (a fixed period is already about right) or in bursts (an event-triggered period could help)."""
        mu = np.array([f.exec_time for f in sim.sc.functions])
        wf_rate = workflow_rates(sim.sc, sim.now, sim.now + self.horizon)
        lam_f = np.zeros(len(sim.sc.functions))
        for w, r in zip(sim.sc.workflows, wf_rate):
            for t_ in range(w.n):
                lam_f[w.ft[t_]] += r
        demand = lam_f * mu + backlog_per_function(sim) * mu / self.clear_s
        S = int(sim.sc.ecc.sum())
        need = np.maximum(1, np.ceil(demand / self.util_cap).astype(int))
        need = proportional_counts(demand, S) if need.sum() > S else proportional_counts(demand, S, floor=need)
        live = sim.cnt.sum(axis=1)
        return float(np.abs(live - need).sum()) / S

    def _placement_mismatch(self, sim):
        """Diagnostic (2026-10-25): cheap, no-solve companion to `_staleness` -- that one only sees per-function COUNTS; this one
        sees whether the live containers sit on the right NODES. For each function, rank nodes by locality attractiveness to
        current demand (the same demand_points used by queue_aware_placement, reduced to a single attraction score per node via
        the soft-routing kernel W = exp(-hops/tau)); a function's live containers are 'misplaced' if they sit outside its own
        top-n_f(f) nodes by that ranking. Ignores the capacity/queueing interaction between functions (a real incremental solve
        would resolve contention for the same good node), so this is a lower bound on placement staleness, not the full cost.
        Returns the share of all live containers that are misplaced by this ranking, in [0, 1]."""
        sc = sim.sc
        wf_rate = workflow_rates(sc, sim.now, sim.now + self.horizon)
        o_w = origin_weights(self.past_arrivals(sim), sim.N)
        dem = demand_points(sc, wf_rate, sim.cnt.T, o_w=o_w, origin_weight=1.0)         # [F, N]
        W = np.exp(-sc.network.h.astype(float) / 1.0)
        attract = dem @ W.T                                                             # [F, N]
        mis, tot = 0, 0
        for f in range(len(sc.functions)):
            live = sim.cnt[f]
            n_live = int(live.sum())
            if n_live == 0:
                continue
            top = set(np.argsort(-attract[f])[:n_live].tolist())
            mis += sum(int(live[k]) for k in range(sim.N) if k not in top)
            tot += n_live
        return float(mis) / max(tot, 1)

    def _queue_tail(self, sim):
        """Loss proxy for the TAIL, not the mean (2026-10-25): the 95th percentile of current (node, function) queue lengths.
        Backlog (sum of queue lengths) is mean-ish and can move opposite to P99 -- the no-moves pair showed routing improving
        the mean while P99 stayed 7.9x worse -- so the staleness-to-loss check should also be run against this, and the
        trigger (if built) should key on whichever of the two the check supports, stated explicitly, not backlog by default."""
        lens = [len(sim.queue[k][f]) for k in range(sim.N) for f in range(sim.F)]
        return float(np.percentile(lens, 95)) if lens else 0.0

    def _true_placement_mismatch(self, sim):
        """Calibration only (2026-10-25), budget-limited (self._calib_left, default 15 calls per run): solves a FRESH
        placement for the live per-function counts (cur=zeros, so full freedom, same capacity) and scores both the live and
        the fresh layout with `placement_cost` (the real transfer+queueing objective). Returns (proxy, true) where true =
        (cost_live - cost_fresh) / cost_fresh, so `_placement_mismatch`'s cheap no-solve proxy can be checked against it. A
        real solve per call, so this is for a short calibration run, never for the main staleness_log path."""
        sc = sim.sc
        wf_rate = workflow_rates(sc, sim.now, sim.now + self.horizon)
        lam_f = np.zeros(len(sc.functions))
        for w, r in zip(sc.workflows, wf_rate):
            for t_ in range(w.n):
                lam_f[w.ft[t_]] += r
        mu = np.array([f.exec_time for f in sc.functions])
        demand = lam_f * mu + backlog_per_function(sim) * mu / self.clear_s
        o_w = origin_weights(self.past_arrivals(sim), sim.N)
        n_f = sim.cnt.sum(axis=1).astype(int)
        n_f = np.maximum(1, n_f)
        X_fresh = queue_aware_placement(sc, rates=wf_rate, counts=n_f, cur=np.zeros((sim.N, len(sc.functions)), dtype=int),
                                        o_w=o_w, origin_weight=1.0, busy=demand, tau=1.0)
        cost_live = placement_cost(sc, sim.cnt.T, rates=wf_rate, o_w=o_w, origin_weight=1.0, busy=demand, tau=1.0)
        cost_fresh = placement_cost(sc, X_fresh, rates=wf_rate, o_w=o_w, origin_weight=1.0, busy=demand, tau=1.0)
        return float((cost_live - cost_fresh) / max(cost_fresh, 1e-9))

    def forecast(self, sim):
        """Blind forecast = persistence: the arrivals seen in the last L = min(horizon, now) seconds are repeated forward
        (shifted by L, 2L, ...) over the horizon. Uses only the past of the arrival list. Returns (arrivals, workflow rates)."""
        arr = sim.sc.arrivals
        now, L = sim.now, min(self.horizon, sim.now)
        times = [a[0] for a in arr]
        lo, hi = bisect.bisect_left(times, now - L), bisect.bisect_left(times, now)
        past = arr[lo:hi]
        fc, m = [], 1
        while m * L < self.horizon + 1e-9:
            fc += [(t_ + m * L, w, o) for t_, w, o in past if t_ + m * L < now + self.horizon]
            m += 1
        rate = np.zeros(len(sim.sc.workflows))
        for _, w, _ in past:
            rate[w] += 1.0 / L
        return fc, rate

    def past_arrivals(self, sim):
        """The arrivals of the last min(horizon, now) seconds (past only, as `forecast` uses them)."""
        arr = sim.sc.arrivals
        now, L = sim.now, max(1e-9, min(self.horizon, sim.now))
        times = [a[0] for a in arr]
        return arr[bisect.bisect_left(times, now - L):bisect.bisect_left(times, now)]

    def place_kwargs(self, sim):
        """Keyword arguments for `affinity_placement_v2`, or None for the published affinity rule (placement ablation 2026-10-23)."""
        p = self.churn.get("placement")
        if p not in ("v2", "kmedian", "qaware", "faaspr", "faaspr_w"):
            return None
        if p == "faaspr":
            return dict(faaspr=True, rng=self.rng)
        if p == "faaspr_w":
            return dict(faaspr_w=True, rng=self.rng)
        if p == "qaware":
            kw = dict(qaware=True, origin_weight=float(self.churn.get("origin_weight", 1.0)), tau=float(self.churn.get("tau", 1.0)),
                      queue_term=bool(self.churn.get("queue_term", True)), affinity=bool(self.churn.get("affinity", True)),
                      struct=self.churn.get("pstruct"), size_aware=bool(self.churn.get("size_aware", False)),
                      fill_leftover=not bool(self.churn.get("elastic")),     # weighted scenarios: elastic = do not fill the leftover memory
                      fast_cost=bool(self.churn.get("fast_place") or self.churn.get("lazy_place")), lazy=bool(self.churn.get("lazy_place")),
                      thin=int(self.churn.get("place_thin", 0)))
            if self.churn.get("elastic_qaware"):
                kw["elastic_qaware"] = True                      # baseline_layout only (hpa modes): see there
        elif p == "kmedian":
            kw = dict(kmedian=True, epoch=self.epoch, origin_weight=float(self.churn.get("origin_weight", 1.0)),
                      incremental=bool(self.churn.get("incremental", True)), improve=int(self.churn.get("improve", 300)))
        else:
            kw = dict(epoch=self.epoch, keep_weight=float(self.churn.get("keep_weight", 0.0)),
                      origin_weight=float(self.churn.get("origin_weight", 0.0)), softmin=int(self.churn.get("softmin", 1)))
        if kw["origin_weight"]:
            kw["o_w"] = origin_weights(self.past_arrivals(sim), sim.N)
        return kw

    def rate_draw(self, sim):
        """Rate oracle: a fresh Poisson realisation of the TRUE rate series over [now, now + horizon), capped at the end of the
        series (the real run has no arrivals after it). One draw per decision, shared by all candidates (common random numbers)."""
        from .traces import thin_arrivals
        R = np.asarray(sim.sc.meta["rate_series"], dtype=float)
        b = float(sim.sc.meta["bin_s"])
        now = sim.now
        end = min(now + self.horizon, R.shape[1] * b)
        if end <= now:
            return []
        b0, b1 = int(now // b), int(np.ceil(end / b))
        off = b0 * b
        arr = thin_arrivals(R[:, b0:b1], b, end - off, sim.sc.network.ne, self.fc_rng)
        return [(t_ + off, w, o) for t_, w, o in arr if t_ + off >= now]

    def candidates(self, sim):
        cur = sim.cnt.T.copy()
        if self.future == "rate":
            self._fc = self.rate_draw(sim)
            wf_rate = workflow_rates(sim.sc, sim.now, sim.now + self.horizon)
            lam_f = function_rates(sim.sc, sim.now, sim.now + self.horizon)
        elif self.blind:
            self._fc, wf_rate = self.forecast(sim)
            lam_f = np.zeros(len(sim.sc.functions))
            for w, r in zip(sim.sc.workflows, wf_rate):
                for t_ in range(w.n):
                    lam_f[w.ft[t_]] += r
        else:
            self._fc, wf_rate = None, workflow_rates(sim.sc, sim.now, sim.now + self.horizon)
            lam_f = function_rates(sim.sc, sim.now, sim.now + self.horizon)
        # backlog is sized to clear within clear_s = 120 s regardless of the look-ahead (speed study: H changes only the cost of
        # judging, not how aggressive the busiest-first proposal is; identical to before for H = 120)
        bot = None if (self.cand_mode == "concurrency" or self.churn.get("placement") == "faaspr_w") else bottleneck_first_placement(sim, lam_f, self.clear_s, util_cap=self.util_cap, wf_rate=wf_rate,
                                         rng=self.rng if self.churn.get("placement") == "random" else None,
                                         place=self.place_kwargs(sim), elastic=bool(self.churn.get("elastic")),
                                         hold_floor=self._floors(sim, lam_f), sizing_cache=self.sizing_cache)
        if self.cand_mode == "local_sim":
            mu = np.array([f.exec_time for f in sim.sc.functions])
            loc = candidates(cur, lam_f, mu, self.rng, K=self.K)[1:]
            return ["keep"] + [f"local{j + 1}" for j in range(len(loc))], [cur] + loc, lam_f, 0
        if self.cand_mode in ("hpa", "fifer", "kraken", "concurrency"):
            return ["keep", self.cand_mode], [cur, baseline_layout(sim, lam_f, wf_rate, self.cand_mode,
                                                                   elastic=bool(self.churn.get("elastic")), place=self.place_kwargs(sim),
                                                                   rng=self.rng if self.churn.get("placement") == "random" else None)], lam_f, 0
        if self.cand_mode in ("nosim", "keep_bottleneck"):
            return ["keep", "bottleneck"], [cur, bot], lam_f, 0
        # computed only where it is used (2026-11-02): the published affinity rule assumes equal container sizes and refuses weighted
        # scenarios; it is deterministic, so skipping it in the nosim / keep_bottleneck / baseline modes changes no result
        aff = affinity_greedy_placement(sim.sc, rates=np.maximum(wf_rate, 1e-9))
        names, cands = ["keep", "affinity", "bottleneck", "half_affinity", "half_bottleneck"], [cur, aff, bot, half_way(cur, aff), half_way(cur, bot)]
        n_local = max(0, self.K - len(cands))
        return names, cands, lam_f, n_local

    def decide(self, sim):
        import time as _t
        t0 = _t.perf_counter()
        names, cands, lam_f, n_local = self.candidates(sim)
        if self.cand_mode in ("nosim", "hpa", "fifer", "kraken", "concurrency"):
            cur, target = cands[0], cands[1]
            slots = float(sim.sc.ecc.sum())
            n_change = int(max(np.maximum(0, target - cur).sum(), np.maximum(0, cur - target).sum()))   # equal unless capacity is elastic
            backlog = float(backlog_per_function(sim).sum())
            ch = self.churn
            target = limit_changes(cur, target, ch["cap"]) if ch["cap"] else target
            if n_change < ch["min_frac"] * slots or backlog < ch["min_backlog"] * slots:
                target = cur
            n_applied = int(max(np.maximum(0, target - cur).sum(), np.maximum(0, cur - target).sum()))
            switched = n_applied > 0
            if switched:
                self.last_relayout = (sim.now, target.sum(axis=0) - cur.sum(axis=0))
                delay = float(self.churn.get("relayout_delay", 0.0))
                if delay > 0:                                   # layout-age test: decided on time, applied `delay` seconds late
                    self._pending.append((sim.now + delay, target.copy()))
                else:
                    sim.apply_placement(target)
                self.n_switch += 1
            self.log.append(dict(t=sim.now, best=names[1], switched=bool(switched), keep=float("nan"), best_score=float("nan"),
                                 wall_s=_t.perf_counter() - t0, n_wanted=n_change, n_applied=n_applied, backlog=backlog))
            return switched
        scores = [clone_score(sim, None if i == 0 else X, self.horizon, fc=self._fc) for i, X in enumerate(cands)]
        if n_local:
            base = cands[int(np.argmin(scores[1:])) + 1]
            mu = np.array([f.exec_time for f in sim.sc.functions])
            loc = candidates(base, lam_f, mu, self.rng, K=n_local + 1)[1:]
            for j, X in enumerate(loc):
                names.append(f"local{j + 1}")
                cands.append(X)
                scores.append(clone_score(sim, X, self.horizon, fc=self._fc))
        wall_decide = _t.perf_counter() - t0                    # decision cost only (the tau re-scoring below is a diagnostic)
        if self.tau_checks and len(self.log) % max(1, 30 // self.tau_checks) == 0 and len(self.taus) < self.tau_checks:
            again = [clone_score(sim, None if i == 0 else X, self.horizon, seed=self.tau_seed + len(self.taus), fc=self._fc) for i, X in enumerate(cands)]
            self.taus.append(kendall_tau_b(scores, again))
        best = int(np.argmin(scores))
        switched = best != 0 and scores[best] < (1.0 - self.margin) * scores[0]
        if switched:
            sim.apply_placement(cands[best])
            self.n_switch += 1
        self.log.append(dict(t=sim.now, best=names[best], switched=bool(switched), keep=scores[0], best_score=scores[best],
                             wall_s=wall_decide, wall_total_s=_t.perf_counter() - t0))
        return switched

    def fine_step(self, sim, util_cap=0.8):
        """Independent variant (2026-10-22): the small-move layer of busiest-first itself, replacing B*'s annealing. Every `period`
        seconds move up to churn['fine'] containers, one at a time, from the function with the most spare capacity to the one under
        the most pressure; pressure = (load + backlog x run time / 120 s) / containers, in busy slots per container. Same blind
        2-minute rates and backlog signal as the big re-layout, no simulation. A container is taken from a node that holds the
        donor function, preferring a node that already holds the receiving function (data affinity)."""
        _, wf_rate = self.forecast(sim)
        lam_f = np.zeros(len(sim.sc.functions))
        for w, r in zip(sim.sc.workflows, wf_rate):
            for t_ in range(w.n):
                lam_f[w.ft[t_]] += r
        mu = np.array([f.exec_time for f in sim.sc.functions])
        demand = lam_f * mu + backlog_per_function(sim) * mu / self.clear_s
        X = sim.cnt.T.copy()
        n = X.sum(axis=0).astype(float)
        moved = 0
        for _ in range(int(self.churn["fine"])):
            p = demand / n
            hi = int(np.argmax(p))
            donors = np.flatnonzero(n > 1)
            if donors.size == 0 or p[hi] <= util_cap:
                break
            lo = int(donors[np.argmin(p[donors])])
            if lo == hi or p[lo] >= util_cap * 0.9 or p[lo] >= p[hi]:
                break
            nodes = np.flatnonzero(X[:, lo] > 0)
            k = int(nodes[np.argmax(X[nodes, hi])])
            X[k, lo] -= 1
            X[k, hi] += 1
            n[lo] -= 1
            n[hi] += 1
            moved += 1
        if moved:
            sim.apply_placement(X)
            self.fine_moves = getattr(self, "fine_moves", 0) + moved
        return None

    def _floors(self, sim, lam_f):
        """Floor for the slow re-layout: the trigger's hold, and (churn `shrink_delay` = K > 0, 6 Nov 2026) a gentler shrink: a function whose
        sizing need is below its current count keeps the current count until that has been true at K consecutive re-layouts. Growth is never
        delayed. Called once per re-layout (the streak is counted here)."""
        floor = self.hold_floor(sim)
        k = int(self.churn.get("shrink_delay", 0))
        if k <= 0:
            return floor
        mu = np.array([f.exec_time for f in sim.sc.functions])
        n_cur = sim.cnt.sum(axis=1).astype(int)
        below = np.maximum(1, np.ceil(lam_f * mu / self.util_cap)) < n_cur
        prev = getattr(self, "_below_streak", np.zeros(len(n_cur), dtype=int))
        self._below_streak = np.where(below, prev + 1, 0)
        delay = np.where(self._below_streak < k, n_cur, 0)
        return delay if floor is None else np.maximum(floor, delay)

    def hold_floor(self, sim):
        """Containers per function that the slow re-layout may not go below because an emergency fix raised them less than
        `fast_hold` seconds ago (asymmetric rule: scale up fast, scale down slowly); None if no hold is active."""
        if not self.hold:
            return None
        floor = np.zeros(len(sim.sc.functions), dtype=int)
        for f, (cnt, until) in list(self.hold.items()):
            if sim.now < until:
                floor[f] = cnt
            else:
                del self.hold[f]
        return floor if floor.any() else None

    def window_rates(self, sim, L):
        """Per-workflow arrival rates over the last min(L, now) seconds, from the observed arrivals only (no look-ahead)."""
        import bisect as _b
        if getattr(self, "_times", None) is None:
            self._times = [a[0] for a in sim.sc.arrivals]
            F = len(sim.sc.functions)
            self._A = np.zeros((F, len(sim.sc.workflows)))                 # tasks of workflow w that run function f
            for j, w in enumerate(sim.sc.workflows):
                for t_ in range(w.n):
                    self._A[w.ft[t_], j] += 1.0
        Lw = max(1e-9, min(float(L), sim.now))
        lo, hi = _b.bisect_left(self._times, sim.now - Lw), _b.bisect_left(self._times, sim.now)
        cnt = np.zeros(len(sim.sc.workflows))
        for a in sim.sc.arrivals[lo:hi]:
            cnt[a[1]] += 1.0
        return cnt / Lw

    def fast_scale(self, sim):
        """Trigger-based add and shrink between two re-layouts, for on-demand capacity (6 Nov 2026, user request).

        `fast_step` only converts containers inside a full cluster. With on-demand sizing there is free memory and surplus to give back, so the
        slow 60 s loop is the only way capacity changes, and a rise in demand waits for it. This checks every move tick (cooldown `fast_cooldown`):
          add     a function whose queue would take longer than `fast_trigger` cold starts to drain AND whose short-window sizing,
                  ceil((short-window load + queued work / fast_clear) / util_cap), exceeds its containers gets up to the deficit, worst drain first,
                  within the free memory plus what the shrink releases; at most `fast_budget` containers per action
          shrink  a function with nothing queued whose count exceeds (1 + `fast_shrink_margin`) x max(short-window, long-window need) releases the excess
          place   the frozen soft-routing placement with the new counts, leftover not filled; the slow re-layout starts from the live layout.
        Parameters are the `fast_step` defaults; the shrink margin (0.25) is new. Nothing tuned."""
        c = self.churn
        if sim.now < self.warmup or sim.now >= sim.duration or sim.now - self._last_fast < float(c.get("fast_cooldown", 10.0)):
            return
        from .controllers import queue_aware_placement as _qa
        fw = np.asarray(sim.sc.fw, dtype=float)
        mu = np.array([f.exec_time for f in sim.sc.functions])
        cs = np.array([f.cold_start for f in sim.sc.functions])
        n = sim.cnt.sum(axis=1).astype(float)
        backlog = backlog_per_function(sim)
        clear = float(c.get("fast_clear", 30.0))
        self.window_rates(sim, 1.0)                                    # makes sure self._A exists
        lam_s = self._A @ self.window_rates(sim, float(c.get("fast_window", 20.0)))
        lam_l = self._A @ self.window_rates(sim, 120.0)
        need_s = np.maximum(1.0, np.ceil((lam_s * mu + backlog * mu / clear) / self.util_cap))
        need_l = np.maximum(1.0, np.ceil((lam_l * mu + backlog * mu / self.clear_s) / self.util_cap))
        drain = backlog * mu / np.maximum(n, 1.0)
        emerg = (drain > float(c.get("fast_trigger", 1.0)) * cs) & (need_s > n)
        level = np.ceil(np.maximum(need_s, need_l) * (1.0 + float(c.get("fast_shrink_margin", 0.25))))
        held = self.hold_floor(sim)
        if held is not None:
            level = np.maximum(level, held)
        surplus = np.where((~emerg) & (backlog == 0) & (n > level), n - level, 0.0)
        budget = float(c.get("fast_budget", 40))
        take = np.zeros(len(n))
        left = budget
        for f in np.argsort(-surplus):
            if surplus[f] <= 0 or left <= 0:
                break
            take[f] = min(surplus[f], left)
            left -= take[f]
        room = float(sim.sc.ecc.sum() - n @ fw + take @ fw)
        add = np.zeros(len(n))
        left = budget
        for f in np.argsort(-drain):
            if not emerg[f] or left <= 0:
                continue
            k = min(need_s[f] - n[f], left, np.floor(room / fw[f] + 1e-9))
            if k > 0:
                add[f] = k
                left -= k
                room -= k * fw[f]
        if add.sum() + take.sum() <= 0:
            return
        rec = dict(t=round(sim.now, 2), n_emerg=int(emerg.sum()), added=int(add.sum()), removed=int(take.sum()), applied=0)
        counts = (n + add - take).astype(int)
        assert (counts >= 1).all() and float(counts @ fw) <= float(sim.sc.ecc.sum()) + 1e-6
        kw = self.place_kwargs(sim)
        assert kw and kw.pop("qaware", False), "fast_scale needs the soft-routing placement"
        kw.pop("elastic_qaware", None)
        wf_rate = np.maximum(self.window_rates(sim, 120.0), 1e-9)
        X = _qa(sim.sc, rates=wf_rate, counts=counts, cur=sim.cnt.T, busy=lam_s * mu + backlog * mu / clear, **kw)
        if (X != sim.cnt.T).any():
            sim.apply_placement(X)
            self._last_fast = sim.now
            rec["applied"] = 1
            hold_s = float(c.get("fast_hold", 0.0))
            if hold_s > 0:                                              # scale up fast, scale down slowly: the slow loop may not take these back for hold_s seconds
                for f in np.flatnonzero(add > 0):
                    self.hold[int(f)] = (int(n[f] + add[f]), sim.now + hold_s)
        self.fast_log.append(rec)

    def fast_step(self, sim):
        """Emergency fixes between two re-layouts (2026-10-24): a SMALL, TRIGGERED capacity change from a short window.

        The 60 s re-layout sizes from the last two minutes and cannot add capacity inside its own interval; the request moves only
        redistribute. This adds the missing fast capacity loop, built so that it cannot repeat B*'s failure (half of B*'s swaps undid
        the layout): the slow re-layout starts from the live layout, so it keeps an emergency fix while the demand lasts and reverses
        it when the burst is over.
          trigger   a function is in emergency if its queue would take longer than `fast_trigger` cold starts to drain with today's
                    containers (Fifer's queue-or-start rule) AND the short-window sizing needs more containers than it has
          size      containers = ceil((short-window load + queued work / fast_clear) / 0.8), same formula as the slow loop
          donors    only containers above BOTH the long-window and the short-window need of their function; none are taken if no
                    donor has spare (a full cluster has nothing to give)
          budget    at most `fast_budget` conversions per action and one action per `fast_cooldown` seconds
          placement the frozen incremental soft-routing placement with the new counts (conversions happen where donors are freed)."""
        c = self.churn
        if sim.now < self.warmup or sim.now >= sim.duration or sim.now - self._last_fast < float(c.get("fast_cooldown", 10.0)):
            return
        from .controllers import queue_aware_placement as _qa
        mu = np.array([f.exec_time for f in sim.sc.functions])
        cs = np.array([f.cold_start for f in sim.sc.functions])
        n = sim.cnt.sum(axis=1).astype(float)
        backlog = backlog_per_function(sim)
        clear = float(c.get("fast_clear", 30.0))
        wr_s = self.window_rates(sim, float(c.get("fast_window", 20.0)))
        lam_s = self._A @ wr_s
        drain = backlog * mu / np.maximum(n, 1.0)
        need_s = np.maximum(1, np.ceil((lam_s * mu + backlog * mu / clear) / self.util_cap))
        trig = float(c.get("fast_trigger", 1.0))
        gate = float(c.get("fast_gate", 0.0))
        if gate > 0:                                   # regime gate: how far the 20 s rate sits from the 2-minute baseline (smoothed)
            r_long = float(self.window_rates(sim, 120.0).sum())
            dev = abs(float(wr_s.sum()) - r_long) / max(r_long, 1e-9)
            self._burstiness = 0.7 * self._burstiness + 0.3 * dev
            if self._burstiness < gate:                # calm regime: demand a queue that outlasts TWO cold starts
                trig *= 2.0
        emerg = (drain > trig * cs) & (need_s > n)
        if not emerg.any():
            return
        wr_l = self.window_rates(sim, 120.0)
        lam_l = self._A @ wr_l
        need_l = np.maximum(1, np.ceil((lam_l * mu + backlog * mu / self.clear_s) / self.util_cap))
        spare = np.maximum(0.0, n - np.maximum(np.maximum(need_l, need_s), 1.0))
        spare[emerg] = 0.0
        deficit = np.where(emerg, need_s - n, 0.0)
        budget = float(c.get("fast_budget", 40))
        mu_sev = float(c.get("fast_mu", 0.0))
        if mu_sev > 0:                                 # severity-scaled budget: worse queues (relative to a cold start) get more
            sev = float(np.clip((drain[emerg] / cs[emerg]).max() - 1.0, 0.0, 3.0))
            budget *= 1.0 + mu_sev * sev
        total = int(min(deficit.sum(), spare.sum(), budget))
        rec = dict(t=round(sim.now, 2), n_emerg=int(emerg.sum()), deficit=float(deficit.sum()), spare=float(spare.sum()), applied=0)
        if total <= 0:
            rec["why"] = "no donor" if spare.sum() <= 0 else "none"
            self.fast_log.append(rec)
            return
        add = np.zeros(len(n))
        for f in np.argsort(-drain):                                      # worst queues first
            if deficit[f] > 0 and add.sum() < total:
                add[f] = min(deficit[f], total - add.sum())
        take = np.zeros(len(n))
        order = np.argsort(-spare)
        left = add.sum()
        for f in order:                                                   # donors with the most spare first
            if left <= 0 or spare[f] <= 0:
                break
            take[f] = min(spare[f], left)
            left -= take[f]
        counts = (n + add - take).astype(int)
        assert counts.sum() == int(n.sum()) and (counts >= 1).all()
        kw = self.place_kwargs(sim)
        assert kw and kw.pop("qaware", False), "fast_step needs the soft-routing placement"
        wf_rate = np.maximum(self.window_rates(sim, 120.0), 1e-9)
        X = _qa(sim.sc, rates=wf_rate, counts=counts, cur=sim.cnt.T, busy=lam_s * mu + backlog * mu / clear, **kw)
        n_conv = int(np.maximum(0, X - sim.cnt.T).sum())
        if n_conv:
            sim.apply_placement(X)
            self._last_fast = sim.now
            self.n_fast = getattr(self, "n_fast", 0) + n_conv
            hold_s = float(c.get("fast_hold", 0.0))
            if hold_s > 0:                             # window caching: keep the raised counts for hold_s seconds
                for f in np.flatnonzero(add):
                    self.hold[int(f)] = (int(n[f] + add[f]), sim.now + hold_s)
        rec.update(applied=n_conv, funcs=[int(f) for f in np.flatnonzero(add)])
        self.fast_log.append(rec)

    def rebalance_step(self, sim, max_moves=None):
        """Diagnostic (2026-10-22): B*'s request moving without its container swaps. Every `period` seconds each waiting request,
        longest queues first and from the back of each queue, is moved to the node holding its function where it would finish
        earliest (AET, the same estimate B* uses, including the state transfer), if that beats staying. Storage limits as in B*.

        slack_frac_aware (2026-10-27, step 2 of the moving-hotspot diagnostic in output/data-analysis/results/): three
        deterministic, no-training corrections on top of plain AET, each gated by its own churn weight (0.0 = off, the
        original rule):
          urgency_gain     a task with negative structural slack (SLO-like budget minus elapsed time minus its own remaining
                            critical-path length, _slack below) gets an easier bar to clear to move. Targets the diagnostic's
                            finding that criticality-aware handling of MOVED tasks specifically -- not plain queue FIFO order,
                            which bought ~0 -- was where ceiling A's ~9% headroom came from.
          pingpong_penalty a task already moved n_moves times needs a correspondingly bigger AET improvement to move again --
                            the diagnostic's tail requests ping-ponged (moved >= 2x) at 2.1x the overall rate.
          frac_penalty     moving away from the task's OWN planned node (req.plan[task]) costs an extra flat penalty unless
                            AET's own gain clears it too -- a cheap proxy for the B1/B2 cohesion ceiling (~9-10%), reusing the
                            plan already carried on the request instead of new bookkeeping.
        Returns a Sol with no container change, so the simulator applies only the moves."""
        from .solution import Sol
        sol = Sol(sim)
        rule = self.churn.get("rebal_rule", "aet")
        if rule != "aet":
            return self._queue_balance(sim, sol, rule, max_moves or self.churn.get("rebal_max", 10 ** 9))
        if self.churn.get("move_terms"):
            return self._rebalance_terms(sim, sol, max_moves or self.churn.get("rebal_max", 10 ** 9))
        if self.churn.get("pass_order") == "gain" and self._fast_ok():  # V3 follow-up (2026-11-04): gain-ordered pass; default off
            mv = self._order_cf(sim, online_sol=sol)
            self.rebal_moves = getattr(self, "rebal_moves", 0) + len(mv)
            return sol if mv else None
        if self.churn.get("fast_rebal", True) and self._fast_ok():
            cf = None
            if self.churn.get("log_order_cf"):                          # logging only (2026-11-04): pass-order counterfactual on copies
                self._cf_tick = getattr(self, "_cf_tick", 0) + 1
                if self._cf_tick % int(self.churn.get("order_cf_every", 4)) == 0:
                    cf = self._order_cf(sim)
            out = self._rebalance_fast(sim, sol, max_moves or self.churn.get("rebal_max", 10 ** 9))
            if cf is not None:
                cf["real_match"] = bool(self._fast_moves == cf.pop("_v0_list"))
                self.__dict__.setdefault("order_cf_log", []).append(cf)
            return out
        qs = sorted(((len(sim.queue[k][f]), f, k) for k in range(sim.N) for f in range(sim.F) if sim.queue[k][f]), reverse=True)
        moved, cap = 0, max_moves or self.churn.get("rebal_max", 10 ** 9)
        lam = self.churn.get("lam", 1.0)                        # 2026-10-26, lambda-sweep probe; default 1.0 == unweighted (original rule)
        ww = float(self.churn.get("wait_w", 1.0))               # 2026-11-02, weight on the predicted queue wait; default 1.0 == original
        log_lam = self.churn.get("log_lambda_components")
        log_ctx = self.churn.get("log_move_ctx")
        tz = float(self.churn.get("tail_z", 0.0))               # 2026-11-02, M1: score = estimate + tz * sd of the start time (0.78 mu sqrt(ahead per container + 1))

        def tail(f, kk, ah):
            return tz * 0.78 * float(sim.exec_time[f]) * (ah / max(int(sol.cnt[f, kk]), 1) + 1.0) ** 0.5
        self._np = getattr(self, "_np", 0) + 1
        sfa = bool(self.churn.get("slack_frac_aware"))
        urgency_gain = float(self.churn.get("urgency_gain", 0.0))
        pingpong_penalty = float(self.churn.get("pingpong_penalty", 0.0))
        frac_penalty = float(self.churn.get("frac_penalty", 0.0))
        # prio_aet (2026-10-28, diagnostic): under Sim(queue_priority=...) a run does not start in queue order, so count as "ahead"
        # only the runs that would start before it (higher key, or equal key and older); default: queue position (FIFO)
        # prio_aet_peek (2026-11-03): same, but the key is read without refreshing the dispatcher's statistics (QueuePriority.peek)
        peek = bool(self.churn.get("prio_aet_peek"))
        qp = sim.queue_priority if (self.churn.get("prio_aet") or peek) else None
        log_pm = bool(self.churn.get("log_prio_mismatch")) and sim.queue_priority is not None
        kc = {}
        vp = float(self.churn.get("veto_p", 0.0))               # 2026-11-04, move-veto experiment; 0.0 == original rule
        if vp:
            if not hasattr(self, "_vrng"):
                self._vrng = np.random.default_rng(int(self.churn.get("veto_seed", 0)))
                self._vetoed, self._randomised, self.veto_log = set(), set(), []
            vrng, vetoed, randomised = self._vrng, self._vetoed, self._randomised

        def key(r):
            if r not in kc:
                kc[r] = sim.queue_priority.peek(sim, r) if (peek or (log_pm and qp is None)) else qp(sim, r)
            return kc[r]

        def ahead(rq, f, kk, here):
            q, kr = sol.queue(f, kk), key(rq)
            if here:
                i = q.index(rq)
                return sum(1 for j, r in enumerate(q) if r is not rq and (key(r) > kr or (key(r) == kr and j < i)))
            return sum(1 for r in q if key(r) >= kr)

        for _, f, k in qs:
            hosts = [int(x) for x in np.flatnonzero(sol.cnt[f]) if int(x) != k]
            if not hosts:
                continue
            for rq in reversed(list(sol.queue(f, k))):
                if moved >= cap:
                    break
                if vp and (rq.req.id, rq.task) in vetoed:               # move-veto experiment: a vetoed task is never moved
                    continue
                a0 = sol.aet(rq, k, lam=lam, wait_w=ww, ahead=ahead(rq, f, k, True) if qp else None)
                if tz:
                    qk0 = sol.queue(f, k)
                    a0 += tail(f, k, qk0.index(rq) if rq in qk0 else len(qk0))
                threshold = a0
                if sfa:
                    threshold = a0 + urgency_gain * max(0.0, -self._slack(sim, rq)) - pingpong_penalty * rq.n_moves
                best = None
                cand_log = []
                for k2 in hosts:
                    if sol.free[k2] < rq.total:
                        continue
                    a = sol.aet(rq, k2, lam=lam, wait_w=ww, ahead=ahead(rq, f, k2, False) if qp else None)
                    if tz:
                        a += tail(f, k2, len(sol.queue(f, k2)))
                    if sfa and k2 != rq.req.plan[rq.task]:
                        a += frac_penalty
                    if log_lam:
                        cand_log.append((k2, sol.aet(rq, k2, parts=True)))
                    if a < threshold and (best is None or a < best[0]):
                        best = (a, k2)
                if log_lam and cand_log:
                    # every evaluated decision point, current node's parts + every candidate's parts, lam=1 decomposition
                    # (the lambda probe's Gate 0 re-scores these offline for hypothetical lam' without re-simulating)
                    self.lambda_log.append((round(sim.now, 2), sol.aet(rq, k, parts=True), cand_log,
                                             best[1] if best is not None else None))
                if log_ctx:
                    if self._np % 4 == 0:                               # every 4th pass, all its decisions (pass structure kept)
                        qk = sol.queue(f, k)
                        self.ctx_log.append((self._np, round(sim.now, 2), f, float(sim.exec_time[f]), qk.index(rq) if rq in qk else len(qk),
                                             int(sol.cnt[f, k]), sol.aet(rq, k, parts=True),
                                             [(k2, sol.aet(rq, k2, parts=True), len(sol.queue(f, k2)), int(sol.cnt[f, k2]))
                                              for k2 in hosts if sol.free[k2] >= rq.total],
                                             best[1] if best is not None else None))
                if best is None:
                    break                                               # requests further ahead wait less: stop this queue
                if log_pm:                                              # logging only (2026-11-03): FIFO versus priority-order "ahead" for this move
                    qk, k2_ = sol.queue(f, k), best[1]
                    qd = sol.queue(f, k2_)
                    i_f = qk.index(rq) if rq in qk else len(qk)
                    kr_ = key(rq)
                    i_p = sum(1 for j, r in enumerate(qk) if r is not rq and (key(r) > kr_ or (key(r) == kr_ and j < i_f)))
                    d_f, d_p = len(qd), sum(1 for r in qd if key(r) >= kr_)
                    p0, p1 = sol.aet(rq, k, parts=True), sol.aet(rq, k2_, parts=True)
                    wf_, tt_ = rq.req.wf, rq.task
                    qpr = sim.queue_priority
                    tier_ = qpr.tier(sim, rq, sim.now - rq.req.t_arr + qpr._rem_crit(sim, wf_)[tt_]) if qpr.mode == "full" else -1
                    self.__dict__.setdefault("pm_log", []).append((
                        round(sim.now, 3), rq.req.id, tt_, f, i_f, i_p, len(qk), d_f, d_p, tier_,
                        float(p0[0]), float(p0[1]), float(sol.service_estimate(f, k, i_p)), float(p0[2]),
                        float(p1[0]), float(p1[1]), float(sol.service_estimate(f, k2_, d_p)), float(p1[2])))
                if self.churn.get("log_move_why"):                      # logging only (2026-11-03): why this move; nothing here changes the dynamics
                    qk = sol.queue(f, k)
                    p0, p1 = sol.aet(rq, k, parts=True), sol.aet(rq, best[1], parts=True)
                    wf_, tt_ = rq.req.wf, rq.task
                    self.__dict__.setdefault("why_log", []).append((
                        round(sim.now, 3), rq.req.id, tt_, f, rq.n_moves, qk.index(rq) if rq in qk else len(qk), len(qk),
                        int(sol.cnt[f, k]), int(sol.cnt[f, best[1]]), len(sol.queue(f, best[1])),
                        float(p0[0]), float(p0[1]), float(p0[2]), float(p1[0]), float(p1[1]), float(p1[2]),
                        int(k == rq.req.plan[tt_]), int(best[1] == rq.req.plan[tt_]),
                        -1.0 if rq.t_first is None else round(sim.now - rq.t_first, 3), float(a0), float(best[0]),
                        int(any(rq.req.plan[c] == best[1] for c in wf_.children[tt_])), int(any(rq.req.plan[c] == k for c in wf_.children[tt_]))))
                if self.churn.get("log_gain"):
                    self.gain_log.append((round(sim.now, 2), float(a0 - best[0])))
                if vp and rq.n_moves == 0 and (rq.req.id, rq.task) not in randomised:
                    # move-veto experiment (2026-11-04): at a task's first accepted move, veto it with probability veto_p (own RNG, so no
                    # other random draw changes); a vetoed task stays where it is for good. veto_p = 0 (default) leaves the rule untouched.
                    randomised.add((rq.req.id, rq.task))
                    veto = bool(vrng.random() < vp)
                    qk_ = sol.queue(f, k)
                    qpr = sim.queue_priority
                    tier_ = (qpr.tier(sim, rq, sim.now - rq.req.t_arr + qpr._rem_crit(sim, rq.req.wf)[rq.task])
                             if (qpr is not None and qpr.mode == "full") else -1)
                    self.veto_log.append((round(sim.now, 3), rq.req.id, rq.task, f, float(a0 - best[0]), tier_,
                                          qk_.index(rq) if rq in qk_ else len(qk_), len(qk_), int(veto)))
                    if veto:
                        vetoed.add((rq.req.id, rq.task))
                        continue
                q = list(sol.queue(f, k))
                q.remove(rq)
                sol.set_queue(f, k, q)
                sol.set_queue(f, best[1], list(sol.queue(f, best[1])) + [rq])
                sol.set_node(rq, best[1])
                sol.add_free(k, +rq.total)
                sol.add_free(best[1], -rq.total)
                moved += 1
        self.rebal_moves = getattr(self, "rebal_moves", 0) + moved
        return sol if moved else None

    def _fast_ok(self):
        """The fast path replicates the plain AET rule (lam, wait_w) only; any diagnostic switch falls back to the original loop."""
        c = self.churn
        return not (c.get("prio_aet") or c.get("prio_aet_peek") or c.get("log_prio_mismatch") or c.get("log_move_why") or c.get("log_gain")
                    or c.get("log_lambda_components") or c.get("log_move_ctx") or float(c.get("tail_z", 0.0)) or c.get("slack_frac_aware")
                    or float(c.get("veto_p", 0.0)))

    def _order_cf(self, sim, online_sol=None):
        """Logging only (2026-11-04, pass-order Gate 0): run the plain AET pass on fresh copies of the solution state under four pass
        logics and report what each would move. V0 = current (count order, from the back, early stop; same arithmetic as
        _rebalance_fast, so its moves must equal the real pass's), V1 = no early stop, V2 = queues by estimated wait of their back
        request, V3 = lazy gain-ordered greedy (M4). Nothing here touches the simulator: Sol(sim) copies the state it changes."""
        import heapq as _hq
        from .solution import Sol
        net = sim.net
        h, epd, bw = net.h, net.epd, net.bw
        lam = self.churn.get("lam", 1.0)
        assert float(self.churn.get("wait_w", 1.0)) == 1.0
        N = h.shape[0]

        def engine(mode, base=None):
            sol = base if base is not None else Sol(sim)
            cache, hcache = {}, {}
            st = dict(evals=0, blocked_any=0, blocked_changed=0)
            use_vec = mode == "V3" and bool(self.churn.get("fast_order"))     # MV-3 (7 Nov 2026): same numbers as the host loop below, no Python loop per candidate
            vecs = {}
            if use_vec:
                sol._av.update(sim.all_availability())                  # one scan per pass instead of one per (function, node)

            def vec(f):
                v = vecs.get(f)
                if v is None:
                    v = np.full(N, np.inf)
                    for k2 in np.flatnonzero(sol.cnt[f]):
                        k2 = int(k2)
                        v[k2] = svc(f, k2, len(sol.queue(f, k2)))
                    vecs[f] = v
                return v

            def svc(f, k, ah):
                key = (f, k, ah)
                v = cache.get(key)
                if v is None:
                    v = cache[key] = sol.service_estimate(f, k, ah)
                return v

            def hosts_of(f, k):
                key = (f, k)
                if key not in hcache:
                    if use_vec:                                         # same hosts in the same order, without a Python loop
                        hv_ = np.flatnonzero(sol.cnt[f])
                        hv_ = hv_[hv_ != k]
                        hcache[key] = (hv_.tolist(), hv_)
                    else:
                        hs = [int(x) for x in np.flatnonzero(sol.cnt[f]) if int(x) != k]
                        hcache[key] = (hs, np.asarray(hs))
                return hcache[key]

            def evaluate(rq, f, k):
                hosts, hv = hosts_of(f, k)
                if not hosts:
                    return None
                wf, loc = rq.req.wf, sol.node_of(rq)
                if use_vec:                                             # the same element-wise arithmetic, on the hosts and the source node only
                    inp_k = inp_v = out_k = out_v = 0.0
                    for sz in rq.sizes:
                        d = epd + sz / bw
                        inp_k = inp_k + h[loc, k] * d
                        inp_v = inp_v + h[loc, hv] * d
                    for c in wf.children[rq.task]:
                        d, pc = epd + wf.ss[(rq.task, c)] / bw, rq.req.plan[c]
                        out_k = out_k + h[k, pc] * d
                        out_v = out_v + h[hv, pc] * d
                    qk = sol.queue(f, k)
                    ah = len(qk) - 1 if (qk and qk[-1] is rq) else (qk.index(rq) if rq in qk else len(qk))
                    a0 = float(inp_k) + svc(f, k, ah) + lam * float(out_k)
                    a = np.where(sol.free[hv] >= rq.total, inp_v + vec(f)[hv] + lam * out_v, np.inf)
                    j = int(np.argmin(a))
                    return (a0 - float(a[j]), hosts[j]) if a[j] < a0 else None
                inp = 0.0
                for sz in rq.sizes:
                    inp = inp + h[loc] * (epd + sz / bw)
                if not len(rq.sizes):
                    inp = np.zeros(N)
                out = 0.0
                for c in wf.children[rq.task]:
                    out = out + h[:, rq.req.plan[c]] * (epd + wf.ss[(rq.task, c)] / bw)
                if not len(wf.children[rq.task]):
                    out = np.zeros(N)
                qk = sol.queue(f, k)
                ah = len(qk) - 1 if (qk and qk[-1] is rq) else (qk.index(rq) if rq in qk else len(qk))
                a0 = float(inp[k]) + svc(f, k, ah) + lam * float(out[k])
                sv = vec(f)[hv] if use_vec else np.array([svc(f, k2, len(sol.queue(f, k2))) for k2 in hosts])
                base = inp[hv] + sv + lam * out[hv]
                ok = sol.free[hv] >= rq.total
                if mode == "V0":
                    st["evals"] += 1
                    if not ok.all():
                        st["blocked_any"] += 1
                        ju = int(np.argmin(base))
                        if base[ju] < a0 and not ok[ju]:
                            st["blocked_changed"] += 1
                a = np.where(ok, base, np.inf)
                j = int(np.argmin(a))
                return (a0 - float(a[j]), hosts[j]) if a[j] < a0 else None

            moves = []
            tot = [0.0]

            def apply(rq, f, k, k2, g):
                qk = sol.queue(f, k)
                sol.set_queue(f, k, list(qk[:-1]) if qk[-1] is rq else [r for r in qk if r is not rq])
                sol.set_queue(f, k2, list(sol.queue(f, k2)) + [rq])
                sol.set_node(rq, k2)
                sol.add_free(k, +rq.total)
                sol.add_free(k2, -rq.total)
                moves.append((rq.req.id, rq.task, k2))
                tot[0] += g
                if use_vec and f in vecs:                                   # only these two queues changed
                    vecs[f][k] = svc(f, k, len(sol.queue(f, k)))
                    vecs[f][k2] = svc(f, k2, len(sol.queue(f, k2)))
            qs = sorted(((len(sim.queue[k][f]), f, k) for k in range(sim.N) for f in range(sim.F) if sim.queue[k][f]), reverse=True)
            if mode in ("V0", "V1", "V2"):
                if mode == "V2":
                    def wait_key(t):
                        n, f, k = t
                        return svc(f, k, n - 1) - float(sim.exec_time[f])
                    qs = sorted(qs, key=lambda t: (wait_key(t), t), reverse=True)
                for _, f, k in qs:
                    if not hosts_of(f, k)[0]:
                        continue
                    for rq in reversed(list(sol.queue(f, k))):
                        b = evaluate(rq, f, k)
                        if b is None:
                            if mode == "V1":
                                continue
                            break
                        apply(rq, f, k, b[1], b[0])
            else:                                                       # V3: lazy gain-ordered greedy, early stop per queue
                heap, cap = [], 10 * sum(t[0] for t in qs) + 10
                for _, f, k in qs:
                    q = sol.queue(f, k)
                    if q and hosts_of(f, k)[0]:
                        b = evaluate(q[-1], f, k)
                        if b is not None:
                            heap.append((-b[0], f, k))
                _hq.heapify(heap)
                while heap and len(moves) < cap:
                    _, f, k = _hq.heappop(heap)
                    q = sol.queue(f, k)
                    if not q:
                        continue
                    rq = q[-1]
                    b = evaluate(rq, f, k)
                    if b is None:
                        continue                                        # early stop: this queue is done
                    if heap and b[0] < -heap[0][0]:
                        _hq.heappush(heap, (-b[0], f, k))               # stale: wait for its turn
                        continue
                    apply(rq, f, k, b[1], b[0])
                    if sol.queue(f, k):
                        _hq.heappush(heap, (-b[0], f, k))               # its next request: re-evaluated on pop
            return moves, tot[0], st
        if online_sol is not None:                                      # V3 follow-up (2026-11-04): the gain-ordered pass applied for real
            return engine("V3", online_sol)[0]
        res = {m: engine(m) for m in ("V0", "V1", "V2", "V3")}
        v0 = set(res["V0"][0])
        out = dict(t=round(sim.now, 2), _v0_list=list(res["V0"][0]), storage=res["V0"][2])
        for m, (mv, g, _) in res.items():
            sm = set(mv)
            out[m] = (len(mv), float(g), len(sm & v0), len(sm))
        return out

    def _rebalance_fast(self, sim, sol, cap):
        """Speed-only twin of the plain AET loop in rebalance_step (2026-11-04). Same arithmetic in the same order, so the moves are
        bit-identical (checked by comparing whole results); what changes is the cost: input/output transfer terms are vectorised over
        the candidate nodes (accumulated in the original order), service_estimate is cached per (f, k, ahead) for the pass (availability
        entries do not change inside a pass), the position of a request in its own queue is read from the tail instead of searched."""
        net = sim.net
        h, epd, bw = net.h, net.epd, net.bw
        lam = self.churn.get("lam", 1.0)
        ww = float(self.churn.get("wait_w", 1.0))
        self._np = getattr(self, "_np", 0) + 1
        svc_cache = {}
        rec = self._fast_moves = [] if self.churn.get("log_order_cf") else None

        def svc_at(f, k, ahead):
            key = (f, k, ahead)
            v = svc_cache.get(key)
            if v is None:
                v = svc_cache[key] = sol.service_estimate(f, k, ahead)
            return v
        qs = sorted(((len(sim.queue[k][f]), f, k) for k in range(sim.N) for f in range(sim.F) if sim.queue[k][f]), reverse=True)
        moved = 0
        for _, f, k in qs:
            hosts = [int(x) for x in np.flatnonzero(sol.cnt[f]) if int(x) != k]
            if not hosts:
                continue
            hv = np.asarray(hosts)
            mu = sim.exec_time[f]

            def svc_row(k2):                                            # estimate at host k2 for its current queue length (the same for every request here)
                v = svc_at(f, k2, len(sol.queue(f, k2)))
                return mu + ww * (v - mu) if ww != 1.0 else v
            sv = np.array([svc_row(k2) for k2 in hosts])                # only the destination's queue grows when a request moves: update that entry
            for rq in reversed(list(sol.queue(f, k))):
                if moved >= cap:
                    break
                wf, loc = rq.req.wf, sol.node_of(rq)
                inp = 0.0
                for sz in rq.sizes:
                    inp = inp + h[loc] * (epd + sz / bw)
                if not len(rq.sizes):
                    inp = np.zeros(h.shape[0])
                out = 0.0
                for c in wf.children[rq.task]:
                    out = out + h[:, rq.req.plan[c]] * (epd + wf.ss[(rq.task, c)] / bw)
                if not len(wf.children[rq.task]):
                    out = np.zeros(h.shape[0])
                qk = sol.queue(f, k)
                ahead0 = len(qk) - 1 if (qk and qk[-1] is rq) else (qk.index(rq) if rq in qk else len(qk))
                s0 = svc_at(f, k, ahead0)
                if ww != 1.0:
                    s0 = mu + ww * (s0 - mu)
                a0 = float(inp[k]) + s0 + lam * float(out[k])
                ok = sol.free[hv] >= rq.total
                if not ok.any():
                    break
                a = np.where(ok, inp[hv] + sv + lam * out[hv], np.inf)
                j = int(np.argmin(a))
                if not a[j] < a0:
                    break                                               # requests further ahead wait less: stop this queue
                k2 = hosts[j]
                sol.set_queue(f, k, list(qk[:-1]) if qk[-1] is rq else [r for r in qk if r is not rq])
                sol.set_queue(f, k2, list(sol.queue(f, k2)) + [rq])
                sol.set_node(rq, k2)
                sol.add_free(k, +rq.total)
                sol.add_free(k2, -rq.total)
                sv[j] = svc_row(k2)
                if rec is not None:
                    rec.append((rq.req.id, rq.task, k2))
                moved += 1
        self.rebal_moves = getattr(self, "rebal_moves", 0) + moved
        return sol if moved else None

    def _rem_crit(self, sim, wf):
        """Remaining structural critical path (mean exec time only, no queueing/transfer/cold-start) from each task to the
        workflow's end -- the backward twin of Sim._critical_path, cached per workflow type (2026-10-27, slack_frac_aware)."""
        cache = self.__dict__.setdefault("_rem_crit_cache", {})
        if wf.id not in cache:
            d = [0.0] * wf.n
            for t in reversed(range(wf.n)):          # topological order: a child always has a strictly greater index than its parents
                d[t] = sim.exec_time[wf.ft[t]] + max((d[c] for c in wf.children[t]), default=0.0)
            cache[wf.id] = d
        return cache[wf.id]

    def _slack(self, sim, rq):
        """Online, no-future-knowledge slack estimate (2026-10-27, slack_frac_aware): the request's SLO-like budget
        (slo_factor x unloaded critical path -- the same constant sim.py's own SLO check uses) minus time already elapsed
        minus this task's own remaining structural critical path. Negative = already behind even with no further queueing
        from here on; the move rule reads only its sign and magnitude, nothing further ahead than the task's own workflow."""
        wf = rq.req.wf
        rem = self._rem_crit(sim, wf)[rq.task]
        elapsed = sim.now - rq.req.t_arr
        budget = sim.slo_factor * sim.crit_path[wf.id]
        return budget - elapsed - rem

    def _float(self, sim, wf):
        """Structural float of every task (critical path minus the longest exec-only path through the task), cached per workflow
        type: 0 on the structural critical path (2026-10-28, move_terms)."""
        cache = self.__dict__.setdefault("_float_cache", {})
        if wf.id not in cache:
            ex = [sim.exec_time[wf.ft[t]] for t in range(wf.n)]
            est = [0.0] * wf.n
            for t in range(wf.n):
                est[t] = max((est[u] + ex[u] for u in wf.parents[t]), default=0.0)
            rem = self._rem_crit(sim, wf)
            cp = max(est[t] + rem[t] for t in range(wf.n))
            cache[wf.id] = [cp - est[t] - rem[t] for t in range(wf.n)]
        return cache[wf.id]

    def _edge_class(self, sim, wf):
        """Per edge (t, c): 2 = on every root-to-sink path of the DAG (a cut edge, always on the realised critical path), 1 = not a
        cut edge but into a child of structural float 0, 0 = into a child with float > 0; cached per workflow type."""
        cache = self.__dict__.setdefault("_edge_class_cache", {})
        if wf.id not in cache:
            fwd, bwd = [0] * wf.n, [0] * wf.n
            for t in range(wf.n):
                fwd[t] = 1 if not wf.parents[t] else sum(fwd[u] for u in wf.parents[t])
            for t in reversed(range(wf.n)):
                bwd[t] = 1 if not wf.children[t] else sum(bwd[c] for c in wf.children[t])
            total = sum(fwd[t] for t in range(wf.n) if not wf.children[t])
            fl = self._float(sim, wf)
            cache[wf.id] = {(u, v): 2 if fwd[u] * bwd[v] == total else (1 if fl[v] <= 1e-9 else 0) for (u, v) in wf.ss}
        return cache[wf.id]

    def _median_sojourn(self, sim):
        """Online running median sojourn per workflow type over its last 500 completed requests; before 20 completions the
        unloaded critical path stands in (2026-10-28, move_terms)."""
        out = {}
        for wid, cp in sim.crit_path.items():
            lst = sim.soj_log.get(wid, ())
            out[wid] = float(np.median(lst[-500:])) if len(lst) >= 20 else float(cp)
        return out

    def _rebalance_terms(self, sim, sol, cap):
        """Request moves with the four terms found by the Step A diagnostic (2026-10-28, output/data-analysis/results/penalty_stepA/;
        each switchable through churn, all off == B*'s plain AET rule with the lam-weighted downstream term):
          margin_theta     a move must save at least theta x mu_f of start time (input transfer + service estimate at the
                           destination vs staying; mu_f = the function's mean service time). Below 0.25 mu realised gain is ~0 and
                           ~50% of moves hurt, in every workflow family; above 0.5 mu it pays reliably.
          urgency_priority within a queue the candidates are handled most urgent first -- (elapsed + the task's remaining
                           structural critical path) / the type's online median sojourn -- so urgent tasks take the earlier slots
                           at the destination. Ordering only: it never changes the bar a move has to clear.
          join_gate        a task whose request is waiting on it alone at a join (some child has exactly one input outstanding) is
                           on the critical path with probability ~1: it goes first, and its downstream transfer counts in full.
                           Only workflows with a join can have such a task.
          relevance_out    the downstream transfer of each edge is weighted by how often an edge of its class lies on the realised
                           critical path (Step B, F3 baseline, moved parents): 1.0 on every root-to-sink path (exact), rel_w0=0.39
                           into a child of float 0, rel_w1=0.21 otherwise -- instead of one uniform lam.
        Pass 1 collects the candidates the plain rule would consider (from the back of the queue until the first that fails, as
        before); pass 2 re-evaluates them in priority order against the live state."""
        ch = self.churn
        theta = float(ch.get("margin_theta", 0.0))
        prio, jgate, rel = bool(ch.get("urgency_priority")), bool(ch.get("join_gate")), bool(ch.get("relevance_out"))
        wt = {2: 1.0, 1: float(ch.get("rel_w0", 0.39)), 0: float(ch.get("rel_w1", 0.21))}      # weight by edge class (_edge_class)
        lam = ch.get("lam", 1.0)
        net = sim.net
        med = self._median_sojourn(sim) if prio else None

        def gating(rq):
            wf = rq.req.wf
            return jgate and any(len(wf.parents[c]) > 1 and rq.req.pending[c] == 1 for c in wf.children[rq.task])

        def out_cost(rq, k, full):
            wf, t, plan = rq.req.wf, rq.task, rq.req.plan
            if rel and not full:
                ec = self._edge_class(sim, wf)
                return sum(wt[ec[(t, c)]] * net.stt(wf.ss[(t, c)], k, plan[c]) for c in wf.children[t])
            return (1.0 if full else lam) * sum(net.stt(wf.ss[(t, c)], k, plan[c]) for c in wf.children[t])

        log = self.__dict__.setdefault("decision_stats", dict(evals=0, rule_accepts=0, plain_accepts=0, vetoed=0, added=0,
                                                              both_same_dest=0, both_other_dest=0, out_delta_s=0.0)) \
            if ch.get("log_terms") else None
        if log is not None:
            self.__dict__.setdefault("backlog_log", []).append(
                (round(sim.now, 2), int(sum(len(sim.queue[k][f]) for k in range(sim.N) for f in range(sim.F)))))

        def raw_out(rq, k):
            wf, t, plan = rq.req.wf, rq.task, rq.req.plan
            return sum(net.stt(wf.ss[(t, c)], k, plan[c]) for c in wf.children[t])

        def best_for(rq, k, hosts, record=False):
            full = gating(rq)
            inp0, svc0, _ = sol.aet(rq, k, parts=True)
            a0 = inp0 + svc0 + out_cost(rq, k, full)
            bar = theta * sim.exec_time[rq.f]
            best = plain = None
            p0 = inp0 + svc0 + lam * raw_out(rq, k) if record else None
            for k2 in hosts:
                if sol.free[k2] < rq.total:
                    continue
                inp, svc, _ = sol.aet(rq, k2, parts=True)
                if theta and (inp0 + svc0) - (inp + svc) <= bar:
                    continue
                a = inp + svc + out_cost(rq, k2, full)
                if a < a0 and (best is None or a < best[0]):
                    best = (a, k2)
                if record:                                       # what B*'s plain lam-weighted rule would decide here
                    p = inp + svc + lam * raw_out(rq, k2)
                    if p < p0 and (plain is None or p < plain[0]):
                        plain = (p, k2)
            if record:
                log["evals"] += 1
                log["rule_accepts"] += best is not None
                log["plain_accepts"] += plain is not None
                log["vetoed"] += plain is not None and best is None
                log["added"] += best is not None and plain is None
                if best is not None and plain is not None:
                    log["both_same_dest" if best[1] == plain[1] else "both_other_dest"] += 1
                if best is not None:
                    log["out_delta_s"] += raw_out(rq, best[1]) - raw_out(rq, k)
            return best

        def urgency(rq):
            wf = rq.req.wf
            return (sim.now - rq.req.t_arr + self._rem_crit(sim, wf)[rq.task]) / max(med[wf.id], 1e-9) if prio else 0.0

        def apply(rq, f, k, k2):
            q = list(sol.queue(f, k))
            q.remove(rq)
            sol.set_queue(f, k, q)
            sol.set_queue(f, k2, list(sol.queue(f, k2)) + [rq])
            sol.set_node(rq, k2)
            sol.add_free(k, +rq.total)
            sol.add_free(k2, -rq.total)

        qs = sorted(((len(sim.queue[k][f]), f, k) for k in range(sim.N) for f in range(sim.F) if sim.queue[k][f]), reverse=True)
        moved = 0
        for _, f, k in qs:
            hosts = [int(x) for x in np.flatnonzero(sol.cnt[f]) if int(x) != k]
            if not hosts:
                continue
            if not (prio or jgate):
                for rq in reversed(list(sol.queue(f, k))):
                    if moved >= cap:
                        break
                    b = best_for(rq, k, hosts, record=log is not None)
                    if b is None:
                        break
                    apply(rq, f, k, b[1])
                    moved += 1
                continue
            cands = []
            for rq in reversed(list(sol.queue(f, k))):
                if best_for(rq, k, hosts) is None:
                    break
                cands.append(rq)
            ts = self.__dict__.setdefault("term_stats", dict(candidates=0, gating_candidates=0, gating_moved=0, moves=0))
            ts["candidates"] += len(cands)
            ts["gating_candidates"] += sum(1 for rq in cands if gating(rq))
            cands.sort(key=lambda rq: (gating(rq), urgency(rq)), reverse=True)
            for rq in cands:
                if moved >= cap:
                    break
                b = best_for(rq, k, hosts, record=log is not None)
                if b is not None:
                    ts["gating_moved"] += int(gating(rq))
                    ts["moves"] += 1
                    apply(rq, f, k, b[1])
                    moved += 1
        self.rebal_moves = getattr(self, "rebal_moves", 0) + moved
        return sol if moved else None

    def _queue_balance(self, sim, sol, rule, cap):
        """Standard load-balancing rules in place of the finish-time rule (baseline, 2026-10-22). Both ignore state-transfer cost,
        node distance and service time, as textbook balancers do; they only look at queue lengths and idle containers.
          jsq    join-the-shortest-queue: per function, move waiting requests from the node with the longest queue per container to
                 the node with the shortest, while the gap between the two exceeds one request per container.
          steal  work stealing: a node with an idle container of the function and an empty queue takes a waiting request from the
                 tail of the longest queue of that function (one per idle container)."""
        def move(rq, f, a, b):
            q = list(sol.queue(f, a))
            q.remove(rq)
            sol.set_queue(f, a, q)
            sol.set_queue(f, b, list(sol.queue(f, b)) + [rq])
            sol.set_node(rq, b)
            sol.add_free(a, +rq.total)
            sol.add_free(b, -rq.total)

        moved = 0
        order = sorted(range(sim.F), key=lambda f: -sum(len(sim.queue[k][f]) for k in range(sim.N)))
        for f in order:
            hosts = [int(k) for k in np.flatnonzero(sim.cnt[f])]
            if len(hosts) < 2:
                continue
            while moved < cap:
                if rule == "jsq":
                    load = {k: len(sol.queue(f, k)) / float(sim.cnt[f, k]) for k in hosts}
                    a, b = max(load, key=load.get), min(load, key=load.get)
                    if load[a] - load[b] <= 1.0 or not sol.queue(f, a):
                        break
                    rq = sol.queue(f, a)[-1]
                else:
                    idle = [k for k in hosts if not sol.queue(f, k) and any(i.state == IDLE for i in sim.inst[k][f])]
                    donors = [k for k in hosts if len(sol.queue(f, k)) >= 2]
                    if not idle or not donors:
                        break
                    a, b = max(donors, key=lambda k: len(sol.queue(f, k))), idle[0]
                    rq = sol.queue(f, a)[-1]
                if sol.free[b] < rq.total:
                    break
                move(rq, f, a, b)
                moved += 1
        self.rebal_moves = getattr(self, "rebal_moves", 0) + moved
        return sol if moved else None

    def _log_round(self, sim, sol):
        """Swap log (diagnostic): per B* round, container changes, request moves, and how they relate to the last re-layout."""
        d = sol.cnt - sim.cnt                                           # [F, N]
        n_sw = int(np.maximum(0, d).sum())
        n_mv = sum(1 for run, k in sol.rnode.items() if k != run.node)
        t_l, delta = getattr(self, "last_relayout", (None, None))
        undo = 0
        bl = backlog_per_function(sim)
        to_bl = 0
        if n_sw:
            gained, lost = np.maximum(0, d).sum(axis=1), np.maximum(0, -d).sum(axis=1)
            to_bl = int(gained[bl > 0].sum())
            if delta is not None:                                       # B* adding what the re-layout took away, or removing what it added
                undo = int(gained[delta < 0].sum() + lost[delta > 0].sum())
        if not hasattr(self, "swap_log"):
            self.swap_log = []
        self.swap_log.append((round(sim.now, 2), None if t_l is None else round(sim.now - t_l, 2), n_sw, n_mv, undo, to_bl))

    def run(self, sim):
        while self._pending and sim.now + 1e-9 >= self._pending[0][0]:     # stale layouts whose delay has run out, oldest first
            sim.apply_placement(self._pending.pop(0)[1])
        # no_relayout (control, 2026-10-22): busiest-first switched off, only the small-move layer runs
        if sim.now + 1e-9 >= self.next_dec and sim.now < sim.duration and not self.churn.get("no_relayout"):
            self.next_dec += self.epoch
            if self.decide(sim) and not self.churn.get("moves_after_relayout"):
                return None                                             # placement just changed: skip SA this tick
            # moves_after_relayout (2026-10-24): on the tick a re-layout is applied, fall through to the request moves at once instead
            # of waiting one B* period (4 s Azure, 8 s Huawei), so queued work reaches the new layout immediately
        if sim.now + 1e-9 >= self.next_sa:
            self.next_sa += self.period
            if self.churn.get("log_staleness"):
                pm = self._placement_mismatch(sim)
                self.staleness_log.append((sim.now, self._staleness(sim), pm,
                                           float(backlog_per_function(sim).sum()), self._queue_tail(sim)))
            if self.churn.get("calibrate_placement") and self._calib_left > 0:
                # spread the (expensive, real-solve) calibration calls evenly over the run instead of front-loading them
                stride = max(1, int((sim.duration / self.period) / int(self.churn.get("calibrate_placement_n", 15))))
                self._calib_tick += 1
                if self._calib_tick % stride == 0:
                    self._calib_left -= 1
                    self.calib_log.append((sim.now, self._placement_mismatch(sim), self._true_placement_mismatch(sim)))
            if self.churn.get("fast"):
                self.fast_step(sim)                                     # triggered emergency capacity fix from a short window
            if self.churn.get("fast_scale"):
                self.fast_scale(sim)                                    # on-demand: triggered add / shrink between two re-layouts
            if self.churn.get("fine"):
                return self.fine_step(sim)                              # independent variant: own small moves instead of B*'s annealing
            if self.churn.get("rebal"):
                if not self.churn.get("no_inner"):                      # control: B*'s round first, then move waiting requests
                    sim.apply_solution(self.inner.run(sim))
                    sim.req_count[:] = 0
                return self.rebalance_step(sim)                         # diagnostic: move waiting requests only, no container swaps
            if self.churn.get("no_inner"):
                return None                                             # no_inner: B*'s annealing swaps switched off
            sol = self.inner.run(sim)
            if self.churn.get("log_swaps"):
                self._log_round(sim, sol)
            if self.churn.get("swaps_only"):                            # diagnostic: B*'s container swaps, its request moves dropped
                sim.apply_placement(sol.cnt.T.copy())                   # (orphaned queues are rerouted, as after any placement change)
                sim.req_count[:] = 0
                self.n_swaps_only = getattr(self, "n_swaps_only", 0) + 1
                return None
            return sol
        return None
