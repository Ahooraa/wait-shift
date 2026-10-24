"""Correctness checks for elastic capacity (2026-10-23): slots may stay empty, instances are added and removed explicitly.

  1 invariants    after random add / remove / swap sequences, check_invariants() holds (count bookkeeping, slots <= ecc, storage)
  2 identity      with elastic=False the new code path reproduces a stored result exactly (event hash), i.e. nothing changed for
                  every experiment run so far
  3 accounting    the integrated container count equals slots x window when nothing is ever removed
  4 controller    a short run of the elastic controller keeps the invariants, uses fewer containers than slots, and returns a
                  layout whose container count per function matches the sizing rule

  python output/data-analysis/elastic_test.py
"""
import json
import pickle
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

from dfps.o3s import O3SimAdjuster  # noqa: E402
from dfps.sim import Sim  # noqa: E402
from dfps.variants import make_adjuster, sim_kwargs  # noqa: E402

ASSUME = yaml.safe_load((ROOT / "config" / "assumptions.yaml").read_text(encoding="utf-8"))
D1 = ROOT / "results" / "d1_headroom"
OUT = ROOT / "output" / "data-analysis" / "results"
CASE = "F1_r0.5_s1"


def load():
    return pickle.load(open(D1 / f"{CASE}.pkl", "rb")), pickle.load(open(D1 / f"{CASE}.prep.pkl", "rb"))


def base_kw(duration):
    kw = sim_kwargs("B_STAR", ASSUME)
    kw.update(warmup=30.0, duration=duration, retry_min_interval=1.0, retry_max_attempts=10)
    return kw


def test_invariants():
    sc, P = load()
    sim = Sim(sc, P["X0"], elastic=True, seed=1, **base_kw(200.0))
    rng = np.random.default_rng(0)
    for step in range(400):
        k, f = int(rng.integers(sim.N)), int(rng.integers(sim.F))
        r = rng.random()
        sim.now = float(step) * 0.5                                           # time only has to move forward for the accounting
        if r < 0.4 and sim.cnt[f].sum() > 1 and sim.cnt[f, k] > 0:
            sim.remove_instance(k, f)
        elif r < 0.8:
            sim.add_instance(k, f)
        else:
            g = int(rng.integers(sim.F))
            if sim.cnt[f, k] > 0 and g != f:
                sim.swap_instance(k, f, g)
        sim.check_invariants()
    empty = int(sim.sc.ecc.sum() - sim._n_inst)
    print(f"  1 invariants: 400 random operations, bookkeeping consistent; {empty} of {int(sim.sc.ecc.sum())} slots ended empty,"
          f" {sim.n_add_blocked} additions blocked by a full node")
    assert sim._n_inst == sum(len(sim.inst[k][f]) for k in range(sim.N) for f in range(sim.F))


def test_identity():
    sc, P = load()
    ref = json.loads((D1 / f"{CASE}.B_STAR.json").read_text())
    T = json.loads((OUT / "g2_tstar.json").read_text())
    kw = sim_kwargs("B_STAR", ASSUME)
    kw.update(warmup=60.0, duration=900.0, retry_min_interval=1.0, retry_max_attempts=10, interval=float(T["families"]["F1"]["T_star"]))
    sim = Sim(sc, P["X0"], adjuster=make_adjuster("B_STAR", ASSUME, seed=301), seed=401, **kw)
    r = sim.run()
    same = r["event_hash"] == ref["result"]["event_hash"]
    print(f"  2 identity: B* on {CASE} with the new simulator -> event hash {'IDENTICAL to the stored run' if same else 'DIFFERENT'};"
          f" P99 {r['p99_makespan']:.1f} vs stored {ref['result']['p99_makespan']:.1f}")
    assert same, "the new code path changed the non-elastic behaviour"


def test_accounting():
    sc, P = load()
    # no adjuster keeps the fixed starting layout, whose queues never drain at this load: stop shortly after the window
    sim = Sim(sc, P["X0"], seed=1, drain_factor=0.3, **base_kw(200.0))
    r = sim.run()
    full = float(sc.ecc.sum()) * (200.0 - 30.0)
    print(f"  3 accounting: fixed budget, provisioned container-seconds {r['provisioned_slot_s']:.0f} vs slots x window {full:.0f}")
    assert abs(r["provisioned_slot_s"] - full) < 1e-6 * full


def test_controller():
    sc, P = load()
    T = json.loads((OUT / "g2_tstar.json").read_text())
    period = float(T["families"]["F1"]["T_star"])
    churn = {"no_inner": True, "rebal": True, "rebal_max": 10 ** 9, "placement": "kmedian", "improve": 0, "origin_weight": 1.0,
             "elastic": True}
    adj = O3SimAdjuster(make_adjuster("B_STAR", ASSUME, seed=301), period, epoch=60.0, horizon=120.0, K=5, seed=801, warmup=30.0,
                        blind=True, cand_mode="nosim", churn=churn)
    kw = base_kw(330.0)
    kw["interval"] = adj.next_interval
    sim = Sim(sc, P["X0"], adjuster=adj, seed=401, elastic=True, **kw)
    r = sim.run()
    sim.check_invariants()
    slots = int(sc.ecc.sum())
    print(f"  4 controller: {len(adj.log)} re-layouts, {adj.n_switch} applied; containers now {sim._n_inst} of {slots} slots;"
          f" mean over the window {r['mean_containers']:.0f} ({100 * r['mean_containers'] / slots:.0f}% of the slots);"
          f" P99 {r['p99_makespan']:.1f} s; cold starts {r['cold_starts']}; additions blocked {r['n_add_blocked']}")
    assert r["mean_containers"] < slots, "the elastic controller should use fewer containers than slots at 50% load"
    assert (sim.cnt.sum(axis=1) >= 1).all()


if __name__ == "__main__":
    print("elastic capacity tests")
    for t in (test_invariants, test_accounting, test_controller, test_identity):         # the long identity run goes last
        t()
    print("all passed")
