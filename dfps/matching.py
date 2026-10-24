"""Request scheduling by graph pattern matching (p.6-7 Sec.4.2, Fig.4; ref. [39] Cheng, Zeng, Yu, ICDE 2013).

OPEN-1: the paper describes [39] only briefly ("a number of minimum spanning trees are first found by searching the pattern
graph within the reference graph. Then, the missing paths in the spanning trees are substituted with the shortest
alternative paths ... The match with the least total graph edge weight is selected"). This module implements:
  1. reference graph: g-node (t, e_k) for every task t whose function has an instance on e_k and where e_k has room for
     t's input states (Q-2); g-edge weight (u,e_k)->(v,e_k') = FST(FT(v), e_k') + STT(s_uv, e_k, e_k')  (p.7);
  2. spanning trees of the pattern graph (BFS tree + random ones), the top-K lowest-weight matches of each tree by exact
     dynamic programming (K-best), each completed with the weights of the non-tree pattern edges ("missing paths": every
     g-node pair already has a g-edge, so this is O(1) per edge, as the paper notes on p.9);
  3. the match with the least total g-edge weight over all pattern edges is returned.
It is NOT verified against [39]. Root tasks: a virtual source g-node at the request origin (Q-3 / A-09)."""
from __future__ import annotations

import itertools
from dataclasses import dataclass

import numpy as np

INF = np.inf


@dataclass
class MatchContext:
    net: object                 # Network (hop counts, bw)
    fst: object                 # callable f -> np.ndarray [Ne] of FST(f, e_k) (inf where no instance)
    free_storage: np.ndarray    # free storage per node (MB)


def build_costs(wf, origin, ctx, use_source=True, banned=()):
    """Candidate g-nodes per pattern vertex and the g-edge weight matrices (pattern vertex n = virtual source)."""
    n = wf.n
    banned = set(banned)
    cand = []
    for t in range(n):
        ok = np.isfinite(ctx.fst(wf.ft[t])) & (ctx.free_storage >= wf.input_total(t))
        c = np.flatnonzero(ok)
        c = np.array([k for k in c if (t, int(k)) not in banned], dtype=int)
        cand.append(c)
    cand.append(np.array([origin], dtype=int))
    cost = {}
    for (u, v), size in wf.ss.items():
        m = ctx.net.stt_matrix(size)[np.ix_(cand[u], cand[v])] + ctx.fst(wf.ft[v])[cand[v]][None, :]
        cost[(u, v)] = m
    for r in wf.roots:
        if use_source:
            m = ctx.net.stt_matrix(wf.input_size)[np.ix_(cand[n], cand[r])] + ctx.fst(wf.ft[r])[cand[r]][None, :]
        else:
            m = np.zeros((1, len(cand[r])))
        cost[(n, r)] = m
    return cand, cost


def full_cost(cost, assign):
    """Total weight of all g-edges of the match (assign: pattern vertex -> index into its candidate array)."""
    return float(sum(m[assign[a], assign[b]] for (a, b), m in cost.items()))


def critical_cost(cost, assign, n):
    """Longest source-to-sink path weight of the match (the makespan-like objective of erratum E5): tasks 0..n-1 are in
    topological order, pattern vertex n is the virtual source. Same g-edge weights as full_cost, max instead of sum."""
    dist = {n: 0.0}
    inc = {}
    for (a, b), m in cost.items():
        inc.setdefault(b, []).append((a, float(m[assign[a], assign[b]])))
    for v in range(n):
        dist[v] = max(dist[a] + w for a, w in inc[v]) if v in inc else 0.0
    return max(dist[v] for v in range(n))


def spanning_tree(n_vertices, edges, root, rng=None):
    """Spanning tree (list of tree edges as (parent, child)) of the undirected pattern; BFS tree if rng is None,
    otherwise a random spanning tree (random-priority Kruskal), rooted at `root`."""
    und = {}
    for a, b in edges:
        und.setdefault(a, []).append(b)
        und.setdefault(b, []).append(a)
    if rng is None:
        seen, order, tree = {root}, [root], []
        for v in order:
            for w in und.get(v, []):
                if w not in seen:
                    seen.add(w)
                    order.append(w)
                    tree.append((v, w))
        return tree
    uf = list(range(n_vertices))

    def find(x):
        while uf[x] != x:
            uf[x] = uf[uf[x]]
            x = uf[x]
        return x

    chosen = []
    es = list(edges)
    rng.shuffle(es)
    for a, b in es:
        ra, rb = find(a), find(b)
        if ra != rb:
            uf[ra] = rb
            chosen.append((a, b))
    return spanning_tree(n_vertices, chosen, root)  # re-root the random tree at the source


def _take(A, idx):
    """A[i, idx[i, j]] for 2-D A, idx (same as np.take_along_axis(A, idx, axis=1), without its Python overhead)."""
    return A[np.arange(A.shape[0])[:, None], idx]


def _topk_rows(M, K):
    """K smallest entries per row (sorted ascending), padded with inf. Returns (values, column indices)."""
    r, c = M.shape
    if c <= K:
        idx = np.argsort(M, axis=1, kind="stable")
        vals = _take(M, idx)
        pad = K - c
        if pad:
            vals = np.concatenate([vals, np.full((r, pad), INF)], axis=1)
            idx = np.concatenate([idx, np.zeros((r, pad), dtype=int)], axis=1)
        return vals, idx
    part = np.argpartition(M, K - 1, axis=1)[:, :K]
    pv = _take(M, part)
    order = np.argsort(pv, axis=1, kind="stable")
    return _take(pv, order), _take(part, order)


def kbest_tree(tree, root, cand, cost, K):
    """Exact K-best assignments of a rooted spanning tree: minimise the sum of the tree-edge weights.
    Returns a list of (tree_cost, {pattern vertex: candidate index}) sorted ascending (at most K)."""
    children = {}
    for p, c in tree:
        children.setdefault(p, []).append(c)

    def edge_matrix(p, c):
        return cost[(p, c)] if (p, c) in cost else cost[(c, p)].T

    order, st = [], [root]
    while st:
        v = st.pop()
        order.append(v)
        st += children.get(v, [])
    best, comb = {}, {}
    for v in reversed(order):
        P = len(cand[v])
        acc = np.full((P, K), INF)
        acc[:, 0] = 0.0
        ranks = np.zeros((P, K, 0), dtype=int)
        links = []
        for c in children.get(v, []):
            E = edge_matrix(v, c)                                    # [P_v, P_c]
            M = (E[:, :, None] + best[c][None, :, :]).reshape(P, -1)  # [P_v, P_c * K]
            Lc, idx = _topk_rows(M, K)
            Lq, Lr = idx // K, idx % K
            links.append((c, Lq, Lr))
            pair = (acc[:, :, None] + Lc[:, None, :]).reshape(P, K * K)
            nv, ni = _topk_rows(pair, K)
            a_i, b_i = ni // K, ni % K
            ranks = np.concatenate([np.take_along_axis(ranks, a_i[:, :, None].repeat(ranks.shape[2], 2), axis=1)
                                    if ranks.shape[2] else ranks, b_i[:, :, None]], axis=2)  # (kept: needs a 3-D gather)
            acc = nv
        best[v] = acc
        comb[v] = (ranks, links)
    results = []
    for r in range(K):
        if not np.isfinite(best[root][0, r]):
            continue
        assign, stack = {}, [(root, 0, r)]
        while stack:
            v, p, rk = stack.pop()
            assign[v] = p
            ranks, links = comb[v]
            for j, (c, Lq, Lr) in enumerate(links):
                i = ranks[p, rk, j]
                stack.append((c, int(Lq[p, i]), int(Lr[p, i])))
        results.append((float(best[root][0, r]), assign))
    return results


def match(wf, origin, ctx, k_best=10, n_trees=5, rng=None, use_source=True, banned=(), objective="sum"):
    """Best match over the spanning trees; returns (plan {task: node}, objective value) or None if infeasible.
    objective "sum": least total g-edge weight (the paper, p.7). "critical": among the same K-best candidates, the match with the
    least critical-path weight (erratum E5 variant; the candidate set is still produced by the sum-based tree DP)."""
    n = wf.n
    cand, cost = build_costs(wf, origin, ctx, use_source, banned)
    if any(len(cand[t]) == 0 for t in range(n)):
        return None
    edges = list(cost.keys())
    rng = np.random.default_rng(0) if rng is None else rng
    best = None
    seen_trees = set()
    for ti in range(max(1, n_trees)):
        tree = spanning_tree(n + 1, edges, n, None if ti == 0 else rng)   # rng is consumed exactly as before
        key = frozenset(frozenset(e) for e in tree)
        if key in seen_trees:                      # same undirected tree -> same K-best list -> no new candidate
            continue
        seen_trees.add(key)
        for _, assign in kbest_tree(tree, n, cand, cost, k_best):
            c = full_cost(cost, assign) if objective == "sum" else critical_cost(cost, assign, n)
            if best is None or c < best[0] - 1e-12:
                best = (c, assign)
    if best is None:
        return None
    c, assign = best
    return {t: int(cand[t][assign[t]]) for t in range(n)}, c


def schedule(wf, origin, ctx, k_best=10, n_trees=5, rng=None, use_source=True, objective="sum"):
    """match() + storage repair (A-28): while the plan overloads a node's free storage, ban the largest-input task
    on the most overloaded node and match again."""
    banned = set()
    for _ in range(wf.n * 4):
        res = match(wf, origin, ctx, k_best, n_trees, rng, use_source, banned, objective)
        if res is None:
            return None
        plan, c = res
        used = {}
        for t, k in plan.items():
            used.setdefault(k, []).append(t)
        bad = [(k, sum(wf.input_total(t) for t in ts) - ctx.free_storage[k]) for k, ts in used.items()
               if sum(wf.input_total(t) for t in ts) > ctx.free_storage[k] + 1e-9]
        if not bad:
            return plan, c
        k = max(bad, key=lambda x: x[1])[0]
        t = max(used[k], key=lambda t: wf.input_total(t))
        banned.add((t, k))
    return None


def brute_force(wf, origin, ctx, use_source=True):
    """Exact minimum of the total g-edge weight (test oracle, small instances only)."""
    cand, cost = build_costs(wf, origin, ctx, use_source)
    n = wf.n
    best = (INF, None)
    for combo in itertools.product(*[range(len(cand[t])) for t in range(n)]):
        assign = {t: combo[t] for t in range(n)}
        assign[n] = 0
        c = full_cost(cost, assign)
        if c < best[0]:
            best = (c, assign)
    return best[0], {t: int(cand[t][best[1][t]]) for t in range(n)}
