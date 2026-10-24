import numpy as np
import pytest

from dfps.network import Network
from dfps.nsga2 import (PlacementProblem, choose_final, crowding_distance, fast_nondominated_sort, nsga2,
                        proportionality, proximity)


def line(n):
    return Network(n, [(i, i + 1) for i in range(n - 1)])


def test_nondominated_sort_known_fronts():
    F = np.array([[1, 5], [2, 3], [4, 1], [3, 4], [5, 5], [2, 6]], float)
    fr = fast_nondominated_sort(F)
    assert sorted(fr[0].tolist()) == [0, 1, 2]
    assert sorted(fr[1].tolist()) == [3, 5]
    assert sorted(fr[2].tolist()) == [4]


def test_crowding_distance_boundaries_infinite():
    F = np.array([[1, 5], [2, 3], [4, 1]], float)
    d = crowding_distance(F, np.array([0, 1, 2]))
    assert np.isinf(d[0]) and np.isinf(d[2]) and np.isfinite(d[1]) or np.isinf(d).all()


def test_proximity_line_graph():
    net = line(4)                       # 0-1-2-3, functions F = {0, 1}
    X = np.array([[1, 0], [0, 0], [0, 0], [0, 1]])
    # node0: f0 at 0 (dist 0), f1 at 3 (dist 3) -> 3 ; node1: f0 dist 1, f1 dist 2 -> 2 ; node2: f0 2, f1 1 -> 2 ; node3: 3
    assert proximity(X, net.h, net.diameter) == 3 + 2 + 2 + 3
    Y = np.array([[1, 1], [0, 0], [0, 0], [1, 1]])      # every end node holds both functions
    assert proximity(Y, net.h, net.diameter) == 0 + 1 + 1 + 0
    # uncovered function -> diameter + 1 (A-03)
    Z = np.array([[1, 0], [1, 0], [1, 0], [1, 0]])
    assert proximity(Z, net.h, net.diameter) == 4 * (net.diameter + 1)


def test_proportionality_variants_and_erratum_E1():
    ecc = np.array([4, 6])
    mu = np.array([1.0, 3.0])                      # FEN = 10 * [0.25, 0.75] = [2.5, 7.5]
    X = np.array([[2, 2], [3, 3]])                 # FAN = [5, 5]
    assert proportionality(X, ecc, mu, "abs") == pytest.approx(2.5 + 2.5)
    assert proportionality(X, ecc, mu, "signed") == pytest.approx(0.0)    # signed sum is 0 (E-1)
    rng = np.random.default_rng(0)
    for _ in range(20):                            # identically 0 for ANY feasible chromosome
        Xr = np.stack([rng.multinomial(int(e), [0.5, 0.5]) for e in ecc])
        assert proportionality(Xr, ecc, mu, "signed") == pytest.approx(0.0)


def test_operators_keep_rows_feasible():
    net = line(6)
    ecc = np.array([5, 7, 9, 5, 6, 8])
    prob = PlacementProblem(net, ecc, np.linspace(2, 10, 8))
    rng = np.random.default_rng(3)
    a, b = prob.random(rng), prob.random(rng)
    assert (a.sum(1) == ecc).all()
    c1, c2 = prob.crossover(a, b, rng)
    assert (c1.sum(1) == ecc).all() and (c2.sum(1) == ecc).all()
    for _ in range(50):
        m = prob.mutate(c1, rng, p_node=1.0)
        assert (m.sum(1) == ecc).all() and (m >= 0).all()


def test_nsga2_improves_and_final_choice_rule():
    net = line(8)
    ecc = np.full(8, 6)
    prob = PlacementProblem(net, ecc, np.linspace(2, 10, 8))
    rng = np.random.default_rng(1)
    pop0 = np.array([prob.objectives(prob.random(rng)) for _ in range(100)])
    front, Ff, best = nsga2(prob, rng, pop=40, gens=40)
    assert (best.sum(1) == ecc).all()
    assert Ff.sum(axis=1).min() < pop0.sum(axis=1).mean()
    # chosen plan = lowest sum of min-normalised criteria on the front
    mins = np.where(Ff.min(0) > 0, Ff.min(0), 1.0)
    chosen = prob.objectives(best)
    assert (chosen / mins).sum() == pytest.approx((Ff / mins).sum(axis=1).min())
