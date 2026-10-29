"""Criticality-aware dispatch (2026-10-28): which waiting run an idle instance starts, instead of FIFO (Sim(queue_priority=...)).

The move rule only decides WHERE a task waits; the diagnosis (output/data-analysis/results/penalty_stepA/, ceiling A) put the
headroom in WHO STARTS FIRST at a pool. Everything below is online (nothing the simulator has not yet revealed).

  gate   a run whose request is waiting on it alone at a join (some child has exactly one input outstanding) starts first;
         everything else FIFO.
  full   tiers, highest first (user-approved 2026-10-28):
           3 overdue   elapsed + the task's remaining structural critical path >= the type's online P95 sojourn
           2 gating    the join-gating run above
           1 aged      waited (since first joining a queue) > aging x the function's online median wait   -- starvation bound
           0 the rest
         within tiers 3, 2 and 0: normalised urgency (elapsed + remaining critical path) / the type's online median sojourn;
         within tier 1: oldest first. aging=None switches tiers 3 and 1 off (the uncapped rule used for the gate-1 ceiling).
Ties keep FIFO order (Sim picks the first maximal run). Online statistics: last `window` values, refreshed every `refresh_s`;
before `min_samples` the unloaded critical path (sojourn) or the mean exec time (wait) stands in."""
from __future__ import annotations

from collections import deque

import numpy as np


class QueuePriority:
    def __init__(self, mode="full", aging=2.0, overdue_q=95.0, refresh_s=2.0, min_samples=20, window=500):
        assert mode in ("gate", "full")
        self.mode, self.aging, self.overdue_q = mode, aging, overdue_q
        self.refresh_s, self.min_samples, self.window = refresh_s, min_samples, window
        self._rem, self._med, self._p95, self._wmed, self._t = {}, {}, {}, {}, -1e18
        self._waits = {}
        self.tier_counts = [0, 0, 0, 0]                  # how often each tier won a dispatch

    def _rem_crit(self, sim, wf):
        d = self._rem.get(wf.id)
        if d is None:
            d = [0.0] * wf.n
            for t in reversed(range(wf.n)):              # children always have larger indices than their parents
                d[t] = sim.exec_time[wf.ft[t]] + max((d[c] for c in wf.children[t]), default=0.0)
            self._rem[wf.id] = d
        return d

    def _refresh(self, sim):
        if sim.now - self._t < self.refresh_s:
            return
        self._t = sim.now
        self._med, self._p95 = {}, {}
        for w, v in sim.soj_log.items():
            if len(v) >= self.min_samples:
                x = v[-self.window:]
                self._med[w], self._p95[w] = float(np.median(x)), float(np.percentile(x, self.overdue_q))
        self._wmed = {f: float(np.median(v)) for f, v in self._waits.items() if len(v) >= self.min_samples}

    def on_start(self, sim, run):
        """Called by Sim._start: records the wait of every started run, for the per-function median."""
        if self.aging is not None and run.t_first is not None:
            self._waits.setdefault(run.f, deque(maxlen=self.window)).append(sim.now - run.t_first)

    @staticmethod
    def gating(run):
        wf, r = run.req.wf, run.req
        return any(len(wf.parents[c]) > 1 and r.pending[c] == 1 for c in wf.children[run.task])

    def tier(self, sim, run, proj):
        if self.aging is None:
            return 2 if self.gating(run) else 0
        wid = run.req.wf.id
        p95 = self._p95.get(wid)
        if p95 is not None and proj >= p95:
            return 3
        if self.gating(run):
            return 2
        wmed = self._wmed.get(run.f, float(sim.exec_time[run.f]))
        if run.t_first is not None and sim.now - run.t_first > self.aging * wmed:
            return 1
        return 0

    def won(self, sim, run):
        """Called by Sim._dispatch with the run it starts: counts which tier decided (reporting only)."""
        if self.mode == "full":
            proj = sim.now - run.req.t_arr + self._rem_crit(sim, run.req.wf)[run.task]
            self.tier_counts[self.tier(sim, run, proj)] += 1

    def __call__(self, sim, run):
        if self.mode == "gate":
            return (self.gating(run),)
        self._refresh(sim)
        wf = run.req.wf
        proj = sim.now - run.req.t_arr + self._rem_crit(sim, wf)[run.task]
        tr = self.tier(sim, run, proj)
        second = -run.t_first if tr == 1 else proj / max(self._med.get(wf.id) or float(sim.crit_path[wf.id]), 1e-9)
        return (tr, second)
