"""Dynamic replacement and rescheduling by simulated annealing (p.7-9 Sec.4.3, Alg.1, Alg.2, Eq.7-8).

ComputeNeighbor follows Algorithm 1 line by line (comments give the algorithm line). Acceptance follows Algorithm 2
with erratum E-5: accept="literal" is the test as printed (`random >= exp(-delta/T)`, which never reverts because
exp(-delta/T) > 1 for delta < 0), accept="prose" is Metropolis (revert unless random < exp(delta/T)).
Algorithm 2 returns the LAST solution Sol_t (L-1), not the best one seen.

Decisions that the paper leaves open are in DEVIATIONS.md: D-1 (f_n == f_r is a no-op, last instance of f_r is never removed),
D-2 (AET), D-3 (forced-relocation gain uses AET before the change), D-4 (moves need free storage), A-11 (temperatures)."""
from __future__ import annotations

import math

import numpy as np

from .solution import BUSY, COLD, IDLE, Sol


class SimulatedAnnealing:
    def __init__(self, seed=0, t_max=10.0, alpha=0.95, iterations=100, vicinity=2, accept="prose", best_so_far=False):
        self.rng = np.random.default_rng(seed)
        self.t_max, self.alpha, self.iterations, self.vicinity, self.accept = t_max, alpha, iterations, vicinity, accept
        self.best_so_far = best_so_far     # E3 correction (B*): return the best solution seen, not the last (paper: last, L-1)
        self.stats = dict(iterations=0, rejected=0, noop=0, reverted=0, accepted_worse=0, accepted_better=0,
                          fit_checked=0, nofit=0)       # fit_checked/nofit: heterogeneous sizes only (proposals tested for fit / rejected for not fitting)

    # ------------------------------------------------------------------------------------------ Algorithm 2
    def run(self, sim):
        sol = Sol(sim)                                                     # Sol_0 (Eq. 7)
        t = self.t_max                                                     # l.2
        t_min = self.t_max * self.alpha ** self.iterations
        score, best_score, best_snap = 0.0, 0.0, (sol.snapshot() if self.best_so_far else None)
        while t > t_min:                                                   # l.4
            sol.begin()
            ef = self.compute_neighbor(sol, sim)                           # l.5
            self.stats["iterations"] += 1
            if ef is None:                                                 # D-1 / D-4: neighbour rejected -> stay
                sol.rollback()
                self.stats["rejected"] += 1
            else:
                delta = ef                                                 # l.6 (EF of the new solution)
                if delta < 0:                                              # l.7
                    expo = -delta / t if self.accept == "literal" else delta / t   # E-5
                    thr = math.exp(min(expo, 700.0))
                    if self.rng.random() >= thr:                           # l.8
                        sol.rollback()                                     # l.9: Sol_t <- Sol_{t-1}
                        self.stats["reverted"] += 1
                    else:
                        self.stats["accepted_worse"] += 1
                        score += delta
                else:
                    self.stats["accepted_better"] += 1
                    score += delta
                if self.best_so_far and score > best_score + 1e-12:        # cumulative EF = sum of accepted relocation gains
                    best_score, best_snap = score, sol.snapshot()
            t *= self.alpha                                                # l.12 (geometric schedule, A-11)
        self.stats["last_score"], self.stats["best_score"] = score, max(score, best_score)
        if self.best_so_far and best_score > score + 1e-12:
            sol.restore(best_snap)
        return sol                                                         # l.14: Sol_t (last, L-1); best seen if best_so_far

    # ------------------------------------------------------------------------------------------ Algorithm 1
    def compute_neighbor(self, sol, sim):
        rng = self.rng
        es = int(rng.integers(0, sim.N))                                   # l.2 random edge node e_s
        present = np.flatnonzero(sol.cnt[:, es])
        if present.size == 0:
            self.stats["noop"] += 1
            return 0.0
        used = sim.req_count[present, es]                                  # l.3 least utilized function on e_s:
        f_r = int(rng.choice(present[used == used.min()]))                 #     fewest requests in the past interval (Q-6)
        f_n = int(rng.integers(0, sim.F))                                  # l.4 random function from F (L-2)
        if f_n == f_r:                                                     # A-32 no-op
            self.stats["noop"] += 1
            return 0.0
        if sol.cnt[f_r].sum() == 1:                                        # A-31: never remove the last instance of f_r
            return None
        fw = sim.sc.fw
        if sim.hetero:                                                     # heterogeneous sizes (2026-11-02): f_n must fit e_s
            room = sim.sc.ecc[es] - float(sol.cnt[:, es] @ fw) + fw[f_r]   # after removing one f_r
            self.stats["fit_checked"] += 1
            if fw[f_n] > room + 1e-9:                                      # redraw f_n among the functions that fit (never f_r),
                self.stats["nofit"] += 1                                   # (counted: the first draw did not fit)
                fit = [g for g in range(sim.F) if g != f_r and fw[g] <= room + 1e-9]   # so a trial is not wasted on a misfit;
                if not fit:                                                # with equal sizes everything fits and this never runs
                    self.stats["nofit_none"] = self.stats.get("nofit_none", 0) + 1
                    return None
                f_n = int(rng.choice(fit))
                self.stats["redraw_up"] = self.stats.get("redraw_up", 0) + int(fw[f_n] > fw[f_r])
        forced = sol.cnt[f_r, es] == 1                                     # will fn_rs reach 0 (l.7)?
        old_aet = {}
        if forced:                                                         # D-3: AET in Sol_{t-1}
            for i, rq in enumerate(sol.queue(f_r, es)):
                old_aet[rq] = sol.aet(rq, es, ahead=i)
        # l.5-6: remove an instance of f_r, put a new instance of f_n on e_s
        ent = sol.av(f_r, es)
        j = min(range(len(ent)), key=lambda i: (ent[i][1], ent[i][0]))    # idle, then cold, then busy (as the live system)
        avail, kind = ent[j]
        sol.set_av(f_r, es, ent[:j] + ent[j + 1:])
        new_av = (avail if kind == BUSY else 0.0) + sim.cold_start[f_n]
        sol.set_av(f_n, es, list(sol.av(f_n, es)) + [(new_av, COLD)])
        sol.set_cnt(f_r, es, sol.cnt[f_r, es] - 1)
        sol.set_cnt(f_n, es, sol.cnt[f_n, es] + 1)
        ef = 0.0
        if sol.cnt[f_r, es] == 0:                                          # l.7: fn_rs = 0
            for rq in list(old_aet):                                       # l.8: for all rq in FRQ_rs
                best = None                                                # l.9: e_s' <- empty
                for k in np.flatnonzero(sol.cnt[f_r]):                     # l.10: all e_k where f_r in EWF_k
                    k = int(k)
                    if k == es or sol.free[k] < rq.total:                  # D-4
                        continue
                    a = sol.aet(rq, k)                                     # l.11
                    if best is None or a < best[0]:                        # l.12-13
                        best = (a, k)
                if best is None:
                    return None                                            # nowhere to go -> reject the neighbour
                self._move(sol, rq, f_r, es, best[1])                      # l.16 append to the end of FRQ_rs'
                ef += old_aet[rq] - best[0]                                # relocation gain of a forced move
        for k in range(sim.N):                                             # l.19: e_s' in the vicinity of e_s ...
            if k == es or sim.net.h[es, k] > self.vicinity or sol.cnt[f_n, k] == 0:   # ... where f_n in EWF_s'
                continue
            for rq in list(sol.queue(f_n, k)):                             # l.20: ready-to-execute rq in FRQ_ns'
                rg = sol.aet(rq, k) - sol.aet(rq, es)                      # l.21 / Eq. 8: RG(rq, e_s', e_s)
                if rg > 0 and sol.free[es] >= rq.total:                    # l.22
                    self._move(sol, rq, f_n, k, es)                        # l.23: appended to FRQ_ns (E-6)
                    ef += rg
        return ef                                                          # EF(Sol_{t+1}): sum of relocation gains

    @staticmethod
    def _move(sol, rq, f, k_from, k_to):
        qa = list(sol.queue(f, k_from))
        qa.remove(rq)
        sol.set_queue(f, k_from, qa)
        sol.set_queue(f, k_to, list(sol.queue(f, k_to)) + [rq])
        sol.set_node(rq, k_to)
        sol.add_free(k_from, +rq.total)
        sol.add_free(k_to, -rq.total)
