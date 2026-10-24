import itertools

import numpy as np
import pytest

from dfps.matching import (MatchContext, brute_force, build_costs, full_cost, kbest_tree, match, schedule,
                           spanning_tree)
from dfps.model import Workflow
from dfps.network import Network


def make_ctx(rng, ne=6, nf=4, storage=1e9):
    edges = [(i, i + 1) for i in range(ne - 1)] + [(0, ne - 1), (1, 4)]
    net = Network(ne, edges)
    fstmat = rng.uniform(0.5, 6.0, (nf, ne))
    fstmat[rng.random((nf, ne)) < 0.3] = np.inf
    for f in range(nf):                       # every function must exist somewhere
        if not np.isfinite(fstmat[f]).any():
            fstmat[f, int(rng.integers(0, ne))] = 2.0
    return MatchContext(net, lambda f: fstmat[f], np.full(ne, storage))


def tree_workflow(rng, n, nf):
    edges = [(int(rng.integers(0, v)), v) for v in range(1, n)]        # random out-tree (single root 0)
    ss = {e: float(rng.uniform(10, 50)) for e in edges}
    return Workflow.from_edges(0, n, edges, rng.integers(0, nf, n).tolist(), ss, 20.0)


def dag_workflow(rng, n, nf):
    edges = set()
    for v in range(1, n):
        for u in rng.choice(v, size=int(rng.integers(1, min(3, v) + 1)), replace=False):
            edges.add((int(u), v))
    edges = sorted(edges)
    ss = {e: float(rng.uniform(10, 50)) for e in edges}
    return Workflow.from_edges(0, n, edges, rng.integers(0, nf, n).tolist(), ss, 20.0)


def test_kbest_tree_equals_bruteforce_enumeration():
    rng = np.random.default_rng(0)
    for trial in range(20):
        ctx = make_ctx(rng)
        wf = tree_workflow(rng, int(rng.integers(3, 6)), 4)
        origin = int(rng.integers(0, 6))
        cand, cost = build_costs(wf, origin, ctx)
        n = wf.n
        tree = spanning_tree(n + 1, list(cost.keys()), n)
        K = 5
        got = [c for c, _ in kbest_tree(tree, n, cand, cost, K)]
        allc = []
        for combo in itertools.product(*[range(len(cand[t])) for t in range(n)]):
            a = {t: combo[t] for t in range(n)}
            a[n] = 0
            allc.append(full_cost(cost, a))        # the workflow IS the tree, so tree cost == full cost
        want = sorted(allc)[:K]
        assert len(got) == len(want)
        assert np.allclose(got, want)


def test_match_is_exact_on_tree_workflows():
    rng = np.random.default_rng(1)
    for trial in range(25):
        ctx = make_ctx(rng)
        wf = tree_workflow(rng, int(rng.integers(3, 7)), 4)
        origin = int(rng.integers(0, 6))
        plan, c = match(wf, origin, ctx, k_best=3, n_trees=1)
        bf, _ = brute_force(wf, origin, ctx)
        assert c == pytest.approx(bf)


def test_match_on_dags_never_below_optimum_and_gap_is_reported():
    rng = np.random.default_rng(2)
    gaps = []
    for trial in range(40):
        ctx = make_ctx(rng)
        wf = dag_workflow(rng, int(rng.integers(4, 7)), 4)
        origin = int(rng.integers(0, 6))
        res = match(wf, origin, ctx, k_best=10, n_trees=5, rng=np.random.default_rng(trial))
        bf, _ = brute_force(wf, origin, ctx)
        assert res[1] >= bf - 1e-9                      # a valid match can never beat the optimum
        gaps.append(res[1] / bf - 1.0)
    gaps = np.array(gaps)
    print(f"\nmatching vs brute force on DAGs: exact in {np.mean(gaps < 1e-9):.0%} of cases, "
          f"mean gap {gaps.mean():.2%}, max {gaps.max():.2%}")
    assert gaps.mean() < 0.10                           # sanity bound, not a tuning target


def test_storage_repair_respects_free_storage():
    rng = np.random.default_rng(3)
    ctx = make_ctx(rng)
    wf = dag_workflow(rng, 5, 4)
    total = sum(wf.input_total(t) for t in range(wf.n))
    ctx = MatchContext(ctx.net, ctx.fst, np.full(6, total * 0.45))   # no single node can hold everything
    res = schedule(wf, 0, ctx, k_best=5, n_trees=3, rng=np.random.default_rng(0))
    assert res is not None
    plan, _ = res
    used = {}
    for t, k in plan.items():
        used[k] = used.get(k, 0.0) + wf.input_total(t)
    assert all(u <= ctx.free_storage[k] + 1e-9 for k, u in used.items())
