"""Offline comparison of placement rules (2026-10-23) on the inputs of real re-layouts.

A short run of the no-B* controller is recorded; at every re-layout the (current layout, target counts, observed rates,
observed origin weights) are captured. Each placement rule is then given the SAME inputs, so the rules are compared without
the feedback loop of a full run (that is what the simulator runs are for). Reported per rule: containers converted, and the
expected state-transfer cost in seconds per second, split into origin->root and task->task.

  python output/data-analysis/placement_offline.py [case]
"""
import json
import pickle
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent))

import yaml  # noqa: E402

from dfps.controllers import (affinity_greedy_placement, affinity_placement_v2, origin_weights,  # noqa: E402
                              kmedian_placement, transport_placement)
from dfps.o3s import O3SimAdjuster, backlog_per_function, bottleneck_first_placement  # noqa: E402
from dfps.sim import Sim  # noqa: E402
from dfps.variants import make_adjuster, sim_kwargs  # noqa: E402
from placement_diag import min_changes, transfer_proxy  # noqa: E402

ASSUME = yaml.safe_load((ROOT / "config" / "assumptions.yaml").read_text(encoding="utf-8"))
D1 = ROOT / "results" / "d1_headroom"
OUT = ROOT / "output" / "data-analysis" / "results"

RULES = [
    ("transport (wrong model, kept as negative result)", dict(rule="t", keep_weight=3.0, origin_weight=1.0)),
    ("published affinity rule", dict(rule="v1")),
    ("k-median, incremental, origin w=1", dict(rule="km", origin_weight=1.0)),
    ("k-median, incremental, no origin", dict(rule="km", origin_weight=0.0)),
    ("k-median, from scratch, origin w=1", dict(rule="km", origin_weight=1.0, incremental=False)),
    ("k-median incr + improve 100", dict(rule="km", origin_weight=1.0, improve=100)),
    ("k-median incr + improve 300", dict(rule="km", origin_weight=1.0, improve=300)),
    ("k-median incr + improve 1000", dict(rule="km", origin_weight=1.0, improve=1000)),
    ("v2, same cost (sanity check)", dict()),
    ("v2 + keep (churn-aware), w=1", dict(keep_weight=1.0)),
    ("v2 + keep, w=3", dict(keep_weight=3.0)),
    ("v2 + keep, w=10", dict(keep_weight=10.0)),
    ("v2 + origin-aware, w=1", dict(origin_weight=1.0, pass_ow=True)),
    ("v2 + keep w=3 + origin w=1", dict(keep_weight=3.0, origin_weight=1.0, pass_ow=True)),
]


def capture(case, duration=300.0):
    sc = pickle.load(open(D1 / f"{case}.pkl", "rb"))
    P = pickle.load(open(D1 / f"{case}.prep.pkl", "rb"))
    T = json.loads((OUT / "g2_tstar.json").read_text())
    period = float(T["families"][sc.meta["family"]]["T_star"])
    kw = sim_kwargs("B_STAR", ASSUME)
    kw.update(warmup=60.0, duration=duration, retry_min_interval=1.0, retry_max_attempts=10)
    adj = O3SimAdjuster(make_adjuster("B_STAR", ASSUME, seed=301), period, epoch=60.0, horizon=120.0, K=5, seed=801,
                        warmup=60.0, blind=True, cand_mode="nosim", churn={"no_inner": True, "rebal": True, "rebal_max": 300})
    snaps = []
    real = O3SimAdjuster.candidates

    def spy(self, sim):
        res = real(self, sim)
        _, wf_rate = self.forecast(sim)
        mu = np.array([f.exec_time for f in sim.sc.functions])
        lam_f = res[2]
        snaps.append(dict(cur=sim.cnt.T.copy(), counts=res[1][1].sum(axis=0).copy(),
                          rates=np.maximum(wf_rate, 1e-9), o_w=origin_weights(self.past_arrivals(sim), sim.N),
                          demand=lam_f * mu + backlog_per_function(sim) * mu / self.clear_s))
        return res
    O3SimAdjuster.candidates = spy
    try:
        kw["interval"] = adj.next_interval
        Sim(sc, P["X0"], adjuster=adj, seed=401, **kw).run()
    finally:
        O3SimAdjuster.candidates = real
    return sc, snaps


def main(case):
    sc, snaps = capture(case)
    print(f"=== {case}: {len(snaps)} re-layouts ===")
    rows = {}
    for lab, kwargs in RULES:
        ch, co, cs_, lb = [], [], [], []
        for s in snaps:
            kw = {k: v for k, v in kwargs.items() if k not in ("rule", "pass_ow")}
            if kwargs.get("pass_ow") or kwargs.get("rule") in ("t", "km"):
                kw["o_w"] = s["o_w"]
            if kwargs.get("rule") == "v1":
                X = affinity_greedy_placement(sc, rates=s["rates"], counts=s["counts"])
            elif kwargs.get("rule") == "km":
                X = kmedian_placement(sc, rates=s["rates"], counts=s["counts"], cur=s["cur"], **kw)
            elif kwargs.get("rule") == "t":
                X = transport_placement(sc, rates=s["rates"], counts=s["counts"], cur=s["cur"], epoch=60.0, **kw)
            else:
                X = affinity_placement_v2(sc, rates=s["rates"], counts=s["counts"], cur=s["cur"], epoch=60.0, **kw)
            ch.append(int(np.maximum(0, X - s["cur"]).sum()))
            c = transfer_proxy(sc, X, s["rates"])
            co.append(c["total"])
            cs_.append(c["origin_to_root"])
            lo, _ = min_changes(s["cur"], s["counts"], sc.ecc.astype(int))
            lb.append(int(round(lo)) if lo is not None else np.nan)
        rows[lab] = dict(changes=float(np.mean(ch)), cost=float(np.mean(co)), origin_cost=float(np.mean(cs_)),
                         changes_per=ch, cost_per=[round(x, 1) for x in co])
        print(f"  {lab:44s} converts {np.mean(ch):6.0f} containers | transfer {np.mean(co):6.1f} s/s"
              f" (origin->root {np.mean(cs_):5.1f})")
    print(f"  {'fewest conversions the counts allow':44s} converts {np.nanmean(lb):6.0f}")
    base = rows["published affinity rule"]
    print("\n  change against the published rule:")
    for lab, r in rows.items():
        if lab == "published affinity rule":
            continue
        print(f"    {lab:44s} conversions {100 * (r['changes'] / base['changes'] - 1):+6.0f}%"
              f" | transfer cost {100 * (r['cost'] / base['cost'] - 1):+6.0f}%")
    (OUT / f"placement_offline_{case}.json").write_text(json.dumps(
        {k: {kk: vv for kk, vv in v.items()} for k, v in rows.items()}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "F1_r0.7_s1")
