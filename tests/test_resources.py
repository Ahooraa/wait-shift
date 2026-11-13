"""Resource tracking in the simulator (13 Nov 2026): container-seconds, warm idle seconds, MB moved. Opt-in; must not change the simulation."""
import numpy as np
import pytest

from dfps.heu import HeuPolicy
from dfps.nsga2 import PlacementProblem
from dfps.ondemand import OnDemandSim
from dfps.sa import SimulatedAnnealing
from dfps.sim import Sim
from dfps.workload import build_scenario


def scenario():
    return build_scenario(2, "uniform", 0.3, ne=10, n_workflows=4, pool_size=8, duration_s=60.0)


def run(track, kind):
    sc = scenario()
    if kind == "dfps":
        X = PlacementProblem(sc.network, sc.ecc, np.array([f.exec_time for f in sc.functions])).random(np.random.default_rng(0))
        sim = Sim(sc, X, adjuster=SimulatedAnnealing(seed=5, iterations=40), seed=1, warmup=10.0, duration=60.0)
    else:
        sim = OnDemandSim(sc, HeuPolicy(seed=0), seed=0, warmup=10.0, duration=60.0)
    sim.track_res = track
    return sim.run(), sc


@pytest.mark.parametrize("kind", ["dfps", "ondemand"])
def test_tracking_does_not_change_the_simulation_and_the_parts_add_up(kind):
    base, _ = run(False, kind)
    r, sc = run(True, kind)
    assert r["event_hash"] == base["event_hash"] and r["p99_makespan"] == base["p99_makespan"]
    res = r["resources"]
    assert res["window_s"] == 50.0
    assert res["provisioned_container_s"] == pytest.approx(res["warm_idle_container_s"] + res["busy_container_s"] + res["cold_container_s"])
    assert res["provisioned_capacity_s"] == pytest.approx(res["provisioned_container_s"])             # unit sizes
    assert 0 < res["provisioned_container_s"] <= float(sc.ecc.sum()) * 50.0 + 1e-6
    assert res["state_mb"] > 0 and 0.0 <= res["relocated_mb"] <= res["state_mb"] + 1e-9


def test_a_run_with_relocations_counts_their_moved_mb():
    r, _ = run(True, "dfps")
    assert r["n_moved"] > 0 and r["resources"]["relocated_mb"] > 0
    assert r["resources"]["relocated_mb"] <= r["resources"]["relocated_mb_nominal"] + 1e-9            # states that stay put are not moved


def test_heu_prune_in_capacity_units_equals_the_count_prune_at_unit_sizes():
    """14 Nov 2026: Heu's residual-slots prune is expressed in weight units when container sizes differ. With every weight 1 it must equal the count version, so
    the occupied weight must reproduce sim.occ exactly (containers busy or cold-starting for a bound task)."""
    sc = build_scenario(2, "uniform", 0.5, ne=10, n_workflows=4, pool_size=8, duration_s=80.0)
    pol = HeuPolicy(seed=0)
    sim = OnDemandSim(sc, pol, seed=0, warmup=10.0, duration=80.0)
    sim.t_end = 45.0                                                 # stop in the middle of the run, with containers busy, cold and queued work
    sim.run()
    assert sim.occ.sum() > 0
    assert (pol._occupied_weight(sim) == sim.occ).all()
    wf = sc.workflows[0]
    pol._static = {}
    count = pol.feasible(sim, wf)
    sim.hetero = True                                                # unit weights through the weighted branch
    pol._static = {}
    assert (pol.feasible(sim, wf) == count).all()


def test_heu_demand_uses_container_sizes():
    sc = build_scenario(2, "uniform", 0.3, ne=10, n_workflows=4, pool_size=8, duration_s=40.0)
    sc.fw = np.full(len(sc.functions), 0.5)
    pol = HeuPolicy(seed=0)
    sim = OnDemandSim(sc, pol, seed=0, warmup=5.0, duration=40.0)
    assert sim.hetero
    wf = sc.workflows[0]
    comps = pol.levels(wf)[1]
    need = pol._static_of(sim, wf)[2]
    assert np.allclose(need[0], np.minimum(0.5 * len(comps[0]), sim.ecc.astype(float)))
