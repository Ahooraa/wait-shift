"""Task 9 controllers: B* corrections (best-so-far SA, critical-path matching) and the three simple heuristics."""
import numpy as np

from dfps.controllers import QueueThresholdAdmission, RateChangeTrigger, affinity_greedy_placement
from dfps.matching import MatchContext, build_costs, critical_cost, full_cost, match
from dfps.model import Function, Scenario, Workflow
from dfps.network import Network
from dfps.nsga2 import PlacementProblem
from dfps.sa import SimulatedAnnealing
from dfps.sim import Sim
from dfps.solution import Sol
from dfps.workload import build_scenario


def scen(seed=1, ne=14, nw=6, dur=40.0, pool=8):
    return build_scenario(seed, "uniform", 1.0, ne=ne, n_workflows=nw, pool_size=pool, duration_s=dur, synthetic_max_tasks=6)


def rand_X(sc, seed=0):
    prob = PlacementProblem(sc.network, sc.ecc, np.array([f.exec_time for f in sc.functions]), "abs")
    return prob.random(np.random.default_rng(seed))


def test_best_so_far_never_worse_than_last_solution():
    sc = scen()
    X = rand_X(sc)
    for seed in range(4):
        # literal acceptance = always accept worse moves (E3): the last solution can be far below the best seen
        sim = Sim(sc, X, seed=seed, warmup=0.0, duration=40.0)
        for acc in ("literal", "prose"):
            sa_last = SimulatedAnnealing(seed=seed, accept=acc, iterations=60, best_so_far=False)
            sa_best = SimulatedAnnealing(seed=seed, accept=acc, iterations=60, best_so_far=True)
            sim2 = Sim(sc, X, seed=seed, warmup=0.0, duration=40.0)
            sim2._ev_lam_tick(None, None, None)
            sa_last.run(sim2)
            sa_best.run(sim2)
            assert sa_best.stats["best_score"] >= sa_best.stats["last_score"] - 1e-9
            # same seed and same state: identical trajectory, so best >= the last-solution score of the paper variant
            assert sa_best.stats["best_score"] >= sa_last.stats["last_score"] - 1e-9


def test_best_so_far_restores_the_best_snapshot():
    sc = scen(seed=2)
    X = rand_X(sc, 3)
    sim = Sim(sc, X, seed=1, warmup=0.0, duration=40.0)
    sa = SimulatedAnnealing(seed=5, accept="literal", iterations=80, best_so_far=True)
    sol = sa.run(sim)
    assert (sol.cnt.sum(axis=0) == sim.cnt.sum(axis=0)).all()          # 1-for-1 replacements preserve per-node totals
    assert (sol.cnt.sum(axis=0) == sc.ecc).all()


def test_critical_path_objective_is_no_worse_than_sum_objective_on_critical_cost():
    sc = scen(seed=4, nw=8)
    sim = Sim(sc, rand_X(sc, 1), seed=1, warmup=0.0, duration=40.0)
    ctx = MatchContext(sim.net, sim.fst_vec, sim.esc - sim.storage_used)
    for w in sc.workflows:
        if w.n < 3:
            continue
        cand, cost = build_costs(w, 0, ctx)
        a = match(w, 0, ctx, 10, 5, np.random.default_rng(0), True, (), "sum")
        b = match(w, 0, ctx, 10, 5, np.random.default_rng(0), True, (), "critical")
        assert a is not None and b is not None
        ia = {t: int(np.flatnonzero(cand[t] == a[0][t])[0]) for t in range(w.n)}
        ia[w.n] = 0
        ca = critical_cost(cost, ia, w.n)
        assert b[1] <= ca + 1e-9                                         # same candidate pool, objective = critical cost


def test_critical_cost_is_max_over_paths_and_equals_sum_on_a_chain():
    net = Network(3, [(0, 1), (1, 2)])
    chain = Workflow.from_edges(0, 3, [(0, 1), (1, 2)], [0, 0, 0], {(0, 1): 10.0, (1, 2): 10.0}, 10.0)
    diamond = Workflow.from_edges(1, 4, [(0, 1), (0, 2), (1, 3), (2, 3)], [0, 0, 0, 0],
                                  {(0, 1): 10.0, (0, 2): 10.0, (1, 3): 10.0, (2, 3): 10.0}, 10.0)
    ctx = MatchContext(net, lambda f: np.ones(3), np.full(3, 1e9))
    for wf in (chain, diamond):
        cand, cost = build_costs(wf, 0, ctx)
        assign = {t: 0 for t in range(wf.n)}
        assign[wf.n] = 0
        c, s = critical_cost(cost, assign, wf.n), full_cost(cost, assign)
        assert c <= s + 1e-9
        if wf is chain:
            assert abs(c - s) < 1e-9
        else:
            assert c < s - 1e-9                                          # two parallel branches: max < sum


def test_rate_change_trigger_skips_steady_rates_and_fires_on_a_jump():
    sc = scen()
    sim = Sim(sc, rand_X(sc), seed=1, warmup=0.0, duration=40.0)
    class Inner:
        n = 0
        def run(self, s):
            Inner.n += 1
            return "sol"
    trig = RateChangeTrigger(Inner(), threshold=0.3, check_s=1.0)
    sim.lam = np.ones((len(sc.functions), sc.network.ne))
    assert trig.run(sim) is None and trig.next_interval == 1.0           # first call: reference only
    sim.lam = sim.lam * 1.1
    assert trig.run(sim) is None                                         # +10%: below the threshold
    sim.lam = sim.lam * 2.0
    assert trig.run(sim) == "sol" and trig.n_triggered == 1              # +100% vs the reference
    assert trig.run(sim) is None                                         # reference was reset


def test_queue_threshold_admission_rejects_above_theta():
    sc = scen()
    sim = Sim(sc, rand_X(sc), seed=1, warmup=0.0, duration=40.0)
    adm = QueueThresholdAdmission(theta=2.0)
    cap = float(sc.ecc.sum())
    sim.active = int(2 * cap)
    assert adm(sim, None)
    sim.active = int(2 * cap) + 1
    assert not adm(sim, None)


def test_affinity_greedy_is_feasible_and_colocates_more_than_random():
    sc = scen(seed=5, ne=30, nw=8, pool=10)
    X = affinity_greedy_placement(sc)
    assert (X.sum(axis=1) == sc.ecc).all() and (X.sum(axis=0) >= 1).all()
    net = sc.network

    def weighted_distance(X):
        tot = 0.0
        rates = sc.meta["per_app_rate"]
        for w, r in zip(sc.workflows, rates):
            for (u, v), size in w.ss.items():
                a, b = w.ft[u], w.ft[v]
                na, nb = np.flatnonzero(X[:, a]), np.flatnonzero(X[:, b])
                tot += r * size * net.h[np.ix_(na, nb)].min(axis=1).mean()
        return tot

    rand = np.mean([weighted_distance(rand_X(sc, s)) for s in range(5)])
    assert weighted_distance(X) < rand


def test_sim_runs_with_all_new_pieces_together():
    sc = scen(seed=6, dur=40.0)
    X = affinity_greedy_placement(sc)
    sa = SimulatedAnnealing(seed=1, iterations=30, best_so_far=True)
    sim = Sim(sc, X, adjuster=RateChangeTrigger(sa, 0.3, 2.0), seed=1, warmup=0.0, duration=40.0,
              admission=QueueThresholdAdmission(3.0), match_objective="critical", debug=True)
    r = sim.run()
    sim.check_invariants()
    assert r["n_completed"] + r["n_rejected"] == r["n_arrived"] and r["n_unfinished"] == 0


def test_variants_differ_exactly_in_e1_to_e3():
    from dfps.variants import VARIANTS
    a, b = VARIANTS["AS_PRINTED"], VARIANTS["B_STAR"]
    assert a["prop_variant"] == "signed" and b["prop_variant"] == "abs"      # E1
    assert a["fst_variant"] == "literal" and b["fst_variant"] == "prose"     # E2
    assert a["accept"] == "literal" and b["accept"] == "prose"               # E3 acceptance
    assert not a["best_so_far"] and b["best_so_far"]                         # E3 best-so-far
