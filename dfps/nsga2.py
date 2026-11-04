"""Initial placement with NSGA-II (p.5-6 Sec.4.1, Fig.3; ref. [38] Deb et al. 2002).

Chromosome (Fig.3a): matrix X[k, l] = number of instances of function f_l on edge node e_k, with sum_l X[k, l] = ecc_k.
Objectives, both minimised (p.6):
  proximity       : sum_k (first BFS level at which all functions have been seen from e_k)   [level 0 = e_k itself, Q-5]
  proportionality : sum_l (FAN(f_l) - FEN(f_l))   Eq.3, FEN from Eq.4. Eq.3 as printed is identically 0 (E-1):
                    variant "signed" = literal, "abs" = prose (|FAN - FEN|).
Crossover (Fig.3b): swap the placement vectors of a random subset of nodes. Mutation: +1 to a random function and
-1 to another function (with >= 1 instance) on one node. Population Np = 100 and No = 2 objectives (p.9 Sec.4.4).
Final choice (p.6): normalise each criterion by its minimum on the non-dominated set, take the lowest sum."""
from __future__ import annotations

import numpy as np

from .constants import PAPER


def proximity(X, h, diameter, include_self=True):
    """Sum over nodes of the proximity level (p.6). Level of e_k = max over functions of the hop distance from e_k to
    the nearest node holding the function = first BFS level at which all of F has been visited.
    Uncovered function -> diameter + 1 (A-03). include_self=False starts the search at the neighbours (Q-5 variant)."""
    n, nf = X.shape
    big = diameter + 1
    hh = h if include_self else np.where(np.eye(n, dtype=bool), big, h)
    present = X > 0
    levels = np.zeros(n)
    for f in range(nf):
        idx = np.flatnonzero(present[:, f])
        d = np.full(n, big) if idx.size == 0 else hh[:, idx].min(axis=1)
        levels = np.maximum(levels, d)
    return float(levels.sum())


def proportionality(X, ecc, exec_time, variant="abs", fw=None):
    """Eq. 3-4. FAN(f_l) = sum_k X[k,l]; FEN(f_l) = sum_k ecc_k * mu_l / sum_l' mu_l' (mu = mean execution time, Q-1).
    fw (2026-11-02, heterogeneous container sizes): instance counts stay proportional to mu, scaled so that the WEIGHTED capacity is
    used up: FEN(f_l) = sum_k ecc_k * mu_l / sum_l' mu_l' fw_l'. With fw all ones this is exactly the printed formula."""
    fan = X.sum(axis=0)
    if fw is None or np.allclose(fw, 1.0):
        fen = ecc.sum() * exec_time / exec_time.sum()
    else:
        fen = ecc.sum() * exec_time / float((exec_time * np.asarray(fw, dtype=float)).sum())
    diff = fan - fen
    if variant == "signed":     # Eq. 3 literally (E-1): identically 0
        return float(diff.sum())
    if variant == "abs":
        return float(np.abs(diff).sum())
    raise ValueError(variant)


def fast_nondominated_sort(F):
    """Deb et al. 2002 (vectorised). Returns list of fronts (index arrays), minimisation."""
    F = np.asarray(F, dtype=float)
    le = (F[:, None, :] <= F[None, :, :]).all(axis=2)
    lt = (F[:, None, :] < F[None, :, :]).any(axis=2)
    dom = le & lt                      # dom[p, q] = p dominates q
    cnt = dom.sum(axis=0).astype(int)  # number of solutions dominating q
    fronts, cur = [], np.flatnonzero(cnt == 0)
    while cur.size:
        fronts.append(cur)
        cnt = cnt - dom[cur].sum(axis=0)
        cnt[cur] = -1
        cur = np.flatnonzero(cnt == 0)
    return fronts


def crowding_distance(F, front):
    d = np.zeros(len(front))
    if len(front) <= 2:
        d[:] = np.inf
        return d
    for m in range(F.shape[1]):
        order = np.argsort(F[front, m], kind="stable")
        fm = F[front, m][order]
        span = fm[-1] - fm[0]
        d[order[0]] = d[order[-1]] = np.inf
        if span > 0:
            d[order[1:-1]] += (fm[2:] - fm[:-2]) / span
    return d


class PlacementProblem:
    def __init__(self, net, ecc, exec_time, prop_variant="abs", include_self=True, fw=None):
        self.net, self.ecc = net, np.asarray(ecc)
        self.exec_time = np.asarray(exec_time, dtype=float)
        self.nf = len(exec_time)
        self.prop_variant, self.include_self = prop_variant, include_self
        self.fw = None if fw is None or np.allclose(fw, 1.0) else np.asarray(fw, dtype=float)   # None = one slot per container

    def random(self, rng):
        """A-02: for each node a uniform multinomial draw of ecc_k slots over F. With container weights (fw): draw functions
        uniformly among those that still fit until none does, so a node ends full to within the lightest container."""
        if self.fw is None:
            return np.stack([rng.multinomial(int(e), np.full(self.nf, 1.0 / self.nf)) for e in self.ecc])
        X = np.zeros((len(self.ecc), self.nf), dtype=int)
        for k, e in enumerate(self.ecc):
            free = float(e)
            while True:
                fit = np.flatnonzero(self.fw <= free + 1e-9)
                if fit.size == 0:
                    break
                f = int(rng.choice(fit))
                X[k, f] += 1
                free -= self.fw[f]
        return X

    def objectives(self, X):
        return np.array([proximity(X, self.net.h, self.net.diameter, self.include_self),
                         proportionality(X, self.ecc, self.exec_time, self.prop_variant, self.fw)])

    def crossover(self, a, b, rng, p_node=0.5):
        mask = rng.random(len(a)) < p_node
        c1, c2 = a.copy(), b.copy()
        c1[mask], c2[mask] = b[mask], a[mask]
        return c1, c2

    def mutate(self, X, rng, p_node=None):
        """Per node with probability p_node (default 1/Ne): +1 to a random function, -1 to another with >= 1 instance."""
        p_node = 1.0 / len(X) if p_node is None else p_node
        X = X.copy()
        for k in range(len(X)):
            if rng.random() < p_node:
                a = int(rng.integers(0, self.nf))
                cand = [b for b in np.flatnonzero(X[k] > 0) if b != a]
                if cand:
                    b = int(rng.choice(cand))
                    if self.fw is not None and float(X[k] @ self.fw) + self.fw[a] - self.fw[b] > self.ecc[k] + 1e-9:
                        continue                              # the swap would overfill the node
                    X[k, a] += 1
                    X[k, b] -= 1
        return X


def _rank_crowd(F):
    n = len(F)
    rank = np.zeros(n, dtype=int)
    crowd = np.zeros(n)
    for r, fr in enumerate(_fronts := fast_nondominated_sort(F)):
        rank[fr] = r
        crowd[fr] = crowding_distance(F, fr)
    return rank, crowd, _fronts


def nsga2(problem, rng, pop=None, gens=250, p_cross=0.9, p_node_cross=0.5, p_node_mut=None, log=None):
    """Returns (final non-dominated placements, their objectives, the paper's chosen plan)."""
    pop = PAPER["nsga2_population_size"]["value"] if pop is None else pop
    P = [problem.random(rng) for _ in range(pop)]
    FP = np.array([problem.objectives(x) for x in P])
    for g in range(gens):
        rank, crowd, _ = _rank_crowd(FP)

        def tournament():
            i, j = rng.integers(0, pop, 2)
            if rank[i] != rank[j]:
                return i if rank[i] < rank[j] else j
            return i if crowd[i] >= crowd[j] else j

        Q = []
        while len(Q) < pop:
            a, b = P[tournament()], P[tournament()]
            if rng.random() < p_cross:
                c1, c2 = problem.crossover(a, b, rng, p_node_cross)
            else:
                c1, c2 = a.copy(), b.copy()
            Q += [problem.mutate(c1, rng, p_node_mut), problem.mutate(c2, rng, p_node_mut)]
        Q = Q[:pop]
        FQ = np.array([problem.objectives(x) for x in Q])
        R, FR = P + Q, np.vstack([FP, FQ])
        fronts = fast_nondominated_sort(FR)
        keep = []
        for fr in fronts:
            if len(keep) + len(fr) <= pop:
                keep += fr.tolist()
            else:
                cd = crowding_distance(FR, fr)
                keep += fr[np.argsort(-cd, kind="stable")][: pop - len(keep)].tolist()
                break
        P, FP = [R[i] for i in keep], FR[keep]
        if log is not None and g % 25 == 0:
            log(g, FP.min(axis=0))
    front = fast_nondominated_sort(FP)[0]
    return [P[i] for i in front], FP[front], choose_final(P, FP, front)


def choose_final(P, FP, front):
    """p.6: divide each criterion by its minimum within the non-dominated set; pick the lowest sum.
    D-8: if a minimum is 0 (always for the literal signed Eq.3) that criterion is not normalised (divisor 1)."""
    f = FP[front]
    mins = f.min(axis=0)
    mins = np.where(mins > 0, mins, 1.0)
    score = (f / mins).sum(axis=1)
    return P[front[int(np.argmin(score))]]
