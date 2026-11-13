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
