"""Heterogeneous container sizes (sc.fw not all ones), 2026-11-02: weighted capacity in the simulator, NSGA-II, annealing, the
final controller's placement and the on-demand baselines; plus the guarantee that fw = ones changes nothing."""
import numpy as np
import pytest

from dfps.controllers import (affinity_placement_v2, expected_workflow_rates, proportional_counts, queue_aware_placement)
from dfps.heu import HeuPolicy
from dfps.model import Function, Scenario, Workflow
from dfps.nsga2 import PlacementProblem, proportionality
from dfps.ondemand import OnDemandSim
from dfps.workload import build_scenario, synthetic_alibaba_like
from tests.helpers import line_net, tiny_sim


def weighted_scenario(seed=3, fw_lo=0.4, fw_hi=2.0):
    sc = build_scenario(seed, "uniform", 1.0, ne=12, n_workflows=5, pool_size=10, duration_s=60.0)
    sc.fw = np.random.default_rng(seed).uniform(fw_lo, fw_hi, len(sc.functions))
    return sc


def test_default_weights_are_ones_and_sim_is_not_hetero():
    sim = tiny_sim([[1, 1], [1, 1]], [1.0, 1.0], [2.0, 2.0])
    assert np.allclose(sim.sc.fw, 1.0) and sim.hetero is False


def test_proportionality_with_unit_weights_is_the_printed_formula():
    X = np.array([[2, 1, 1], [1, 3, 0]])
    ecc, mu = np.array([4, 4]), np.array([2.0, 5.0, 3.0])
    assert proportionality(X, ecc, mu) == proportionality(X, ecc, mu, fw=np.ones(3))


def test_nsga2_random_and_mutate_respect_weighted_capacity():
    sc = weighted_scenario()
    mu = np.array([f.exec_time for f in sc.functions])
    prob = PlacementProblem(sc.network, sc.ecc, mu, "abs", fw=sc.fw)
    rng = np.random.default_rng(0)
    for _ in range(20):
        X = prob.random(rng)
        assert (X @ sc.fw <= sc.ecc + 1e-9).all()
        assert ((sc.ecc - X @ sc.fw) < sc.fw.min() + 1e-9).all()             # maximal: not even the lightest container fits
        Y = prob.mutate(X, rng, p_node=1.0)
        assert (Y @ sc.fw <= sc.ecc + 1e-9).all()


def test_proportional_counts_weighted_fits_budget():
    rng = np.random.default_rng(1)
    for _ in range(50):
        F = int(rng.integers(3, 12))
        fw, demand = rng.uniform(0.4, 2.5, F), rng.uniform(0.1, 5.0, F)
        S = float(fw.sum() + rng.uniform(5, 60))
        n = proportional_counts(demand, S, fw=fw)
        assert (n >= 1).all() and float(n @ fw) <= S + 1e-9


def test_queue_aware_placement_weighted_is_feasible_and_filled():
    sc = weighted_scenario()
    rates = expected_workflow_rates(sc)
    mu = np.array([f.exec_time for f in sc.functions])
    dm = np.zeros(len(mu))
    for w, r in zip(sc.workflows, rates):
        for t in range(w.n):
            dm[w.ft[t]] += r * mu[w.ft[t]]
    counts = proportional_counts(dm, float(sc.ecc.sum()), fw=sc.fw)
    X = queue_aware_placement(sc, rates=rates, counts=counts, queue_term=False)
    assert (X @ sc.fw <= sc.ecc + 1e-9).all() and (X.sum(axis=0) >= 1).all()
    assert ((sc.ecc - X @ sc.fw) < sc.fw.min() + 1e-9).all()                 # D-7 for unequal sizes: nothing else fits
    # incremental: from that layout, new counts keep most containers where they are
    X2 = queue_aware_placement(sc, rates=rates, counts=counts, cur=X, queue_term=False)
    assert (X2 @ sc.fw <= sc.ecc + 1e-9).all() and np.minimum(X, X2).sum() >= 0.9 * X.sum()


def test_equal_size_only_rules_refuse_unequal_sizes():
    sc = weighted_scenario()
    with pytest.raises(NotImplementedError):
        affinity_placement_v2(sc)


def test_sim_applies_weighted_layout_and_keeps_invariants():
    sc = weighted_scenario()
    mu = np.array([f.exec_time for f in sc.functions])
    prob = PlacementProblem(sc.network, sc.ecc, mu, "abs", fw=sc.fw)
    X = prob.random(np.random.default_rng(4))
    X[:, 0] = np.maximum(X[:, 0], 0)
    X[0, :] = X[0, :]
    # every function must be present somewhere for the Sim constructor
    for f in np.flatnonzero(X.sum(axis=0) == 0):
        k = int(np.argmax(sc.ecc - X @ sc.fw))
        X[k, f] += 1
        assert (X @ sc.fw <= sc.ecc + 1e-9).all()
    from dfps.sim import Sim
    sim = Sim(sc, X, seed=1, duration=60.0, warmup=5.0)
    assert sim.hetero
    sim.run()
    sim.check_invariants()
    Y = prob.random(np.random.default_rng(5))
    for f in np.flatnonzero(Y.sum(axis=0) == 0):
        k = int(np.argmax(sc.ecc - Y @ sc.fw))
        Y[k, f] += 1
    sim.apply_placement(Y)
    sim.check_invariants()


def test_ondemand_weighted_capacity_never_exceeded():
    rng = np.random.default_rng(2)
    dags = synthetic_alibaba_like(rng, 8)
    sc = build_scenario(5, "uniform", 0.3, ne=6, n_workflows=4, pool_size=6, duration_s=80.0, dags=dags)
    sc.fw = np.array([0.5, 1.5, 0.7, 2.0, 1.0, 0.4])
    sim = OnDemandSim(sc, HeuPolicy(seed=1), seed=1, duration=80.0, warmup=5.0)
    sim.run()
    sim.check_invariants()
    for k in range(sim.N):
        assert float(sim.cnt[:, k] @ sc.fw) <= sc.ecc[k] + 1e-9
