"""FaaSPR comparison under moving hotspots (2026-10-27): F3 regime-shift scenarios (dfps/traces.py::
regime_shift_series, workflow popularity redrawn every 10 min -- "moves load between functions and therefore between
nodes" while total rate stays constant, per its own docstring). Reuses faaspr_fig11.py's instrumentation/breakdown and
VARIANTS unchanged, so the four rows (ours/fp_place/fp_route/fp_both) are directly comparable to that script's F1/F2
results. Tests the claim "topology/workflow-aware placement + moves adapts to a moving hotspot with less migration/
cold-start cost", not just lower P99 -- reports both (mb_relocated, cold_starts alongside p99_makespan).

Why this run didn't exist already: F3 is not new -- it is one of the project's three standard scenario families from
the earlier headroom-gate analysis (knowledge/.., output/data-analysis/results/headroom-ledger.md, G0-G3) -- but
faaspr_fig11.py/faaspr_sweep.py/faaspr_match_setup.py's CASES only ever covered F1 (Azure) and F2 (Huawei); FaaSPR's
ported mechanisms were never run against it.

duration=900.0 (d.DURATION), not fig11.py's 140.0: the regime shifts every 600 s, so a 140 s measurement window would
never see one. 900 s covers ~450 s before the shift and ~450 s after it inside [warmup=60, 900].
move_period 2.0 s, not frozen2.py's shared F1/F2 value (4.0 s): the headroom ledger's own T* tuning found F3's optimal
B* replacement period at 2 s (shorter than F1's 4 s / F2's 8 s->4 s) -- FROZEN2's move clock (inherited from B*'s T*,
per frozen2.py's own convention) follows that family-specific tuning rather than reusing F1/F2's constant.

  python -I output/data-analysis/faaspr_fig11_f3.py [variant,...]
"""
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(ROOT))

import d3s_headroom as d  # noqa: E402
import operating_envelope as oe  # noqa: E402
import workflow_stress as w  # noqa: E402
from frozen2 import FROZEN2  # noqa: E402

import faaspr_fig11 as fig11  # noqa: E402

from dfps.dispatchers import FaaSPRRouter, GraphAware  # noqa: E402
from dfps.nsga2 import PlacementProblem  # noqa: E402
from dfps.o3s import O3SimAdjuster  # noqa: E402
from dfps.sim import Sim  # noqa: E402
from dfps.traces import build_trace_scenario  # noqa: E402
from dfps.variants import make_adjuster, sim_kwargs  # noqa: E402

ASSUME = oe.ASSUME
OUT = ROOT / "output" / "data-analysis" / "results"
CASES = [("F3", 0.7, 5, 1)]            # same (rho, k, seed) as faaspr_fig11.py's F1/F2 cases -- a like-for-like comparison
MOVE_PERIOD_F3 = 2.0                   # headroom-ledger.md's own T* tuning for F3 (see module docstring)
VARIANTS = fig11.VARIANTS              # same four variants, unchanged
# Graph-Aware Scheduling (Liang et al., Future Internet 18:265, 2026), already ported as dfps/dispatchers.py::GraphAware
# and tuned by output/data-analysis/graphaware_sweep.py on F1/F2 (results/graphaware_grid/beta.json: alpha=1.0 fixed,
# beta grid {0.25,0.5,1,2,4,8,16} -> 4.0, confirmed not a boundary optimum). User-provided PDF (2026-10-27): the
# paper's own Data Availability Statement link (github.com/CBY-alt/graph-scheduling-edge-cloud) does not resolve to
# any repository -- no official reference implementation exists to check GraphAware's disclosed fidelity caveats
# against. Two distinct variants, named for what they actually swap (2026-10-27, renamed from the ambiguous "ga"):
#   graphaware_route      -- dispatcher-swap-in ONLY, same convention as fp_route: sizing/placement/re-layout/moves
#                             stay "ours" exactly (FROZEN2, lam=0.5), differing from "ours" only in the dispatcher.
#   graphaware_standalone -- the paper's OWN mechanism running alone, no admixture of "ours": static NSGA-II
#                             placement (same adjuster=None convention as sg below -- no periodic re-layout, no
#                             finish-time request moves, since the paper's Algorithm 1 has neither), with
#                             GraphAware as the ONLY scheduling decision (it already includes the paper's own
#                             online per-task resource-state update, Eq. 24, within one workflow's planning).
GA_BETA = 4.0

# DFPS's OWN baselines (zolfaghari-2025-dynamic-function-placement.md:96, Figs. 5-7): SG = static NSGA-II placement
# (no replacement, no moves -- exactly the X0 every adjuster-based variant above starts from, held fixed for the whole
# run); SR = static RANDOM placement, same "no replacement ever" rule. Both use adjuster=None, so dfps/sim.py never
# schedules an "adjust" event (sim.py:128) -- containers are fixed at t=0 and never replaced or moved, matching the
# paper's own claim that SR/SG cold starts are "zero by construction" (p. 10). Heu [18] and RL [28], the paper's other
# two baselines, are NOT added here: neither cited source has been read in this project (see that source page's
# "Numbers behind Figs. 5-7..." note), and the user's 2026-10-27 decision was to acquire and read them first rather
# than port from DFPS's own secondhand characterization.
STATIC_VARIANTS = ("sg", "sr", "graphaware_standalone")
ALL_VARIANTS = list(VARIANTS) + ["sg", "sr", "graphaware_route", "graphaware_standalone"]

# Self-documenting labels for reporting (user request 2026-10-27: "ga" alone is ambiguous -- always show which
# dispatcher AND which placement/replacement mechanism a variant actually uses).
DISPATCHER_LABEL = {
    "ours": "DFPS default (graph pattern matching)", "fp_place": "DFPS default (graph pattern matching)",
    "fp_route": "FaaSPRRouter (LP path-routing)", "fp_both": "FaaSPRRouter (LP path-routing)",
    "sg": "DFPS default (graph pattern matching)", "sr": "DFPS default (graph pattern matching)",
    "graphaware_route": f"GraphAware (beta={GA_BETA})", "graphaware_standalone": f"GraphAware (beta={GA_BETA})",
}
PLACEMENT_LABEL = {
    "ours": "NSGA-II init + our re-layout/moves", "fp_place": "FaaSPR placement + our re-layout/moves",
    "fp_route": "NSGA-II init + our re-layout/moves", "fp_both": "FaaSPR placement + our re-layout/moves",
    "sg": "static NSGA-II (no re-layout/moves)", "sr": "static random (no re-layout/moves)",
    "graphaware_route": "NSGA-II init + our re-layout/moves", "graphaware_standalone": "static NSGA-II (no re-layout/moves)",
}


def random_layout(sc, seed):
    """DFPS's own random individual (nsga2.py's PlacementProblem.random, docstring A-02): a uniform multinomial draw of
    ecc_k slots over functions, per node -- the same representation NSGA-II itself seeds its population with, so it is
    guaranteed capacity-admissible without any new invariant logic."""
    prob = PlacementProblem(sc.network, sc.ecc, np.array([f.exec_time for f in sc.functions]), "abs")
    return prob.random(np.random.default_rng(seed + 750))


def build(fam, rho, k, seed):
    sc = build_trace_scenario(fam, rho, seed, "dev", d.DURATION + d.WARMUP, 60.0, ne=80, n_workflows=15,
                              alibaba_dags=oe.alibaba_dags(), pool_size=ASSUME["A17_function_pool_size"])
    sc = w.scale(sc, k)
    X0 = oe.initial_layout(sc, seed, ASSUME["A06_generations"])
    return sc, X0


def run_one(fam, rho, k, seed, variant, duration=900.0, sc=None, X0=None, sizing_cache=None):
    if sc is None:
        sc, X0 = build(fam, rho, k, seed)
    kw = sim_kwargs("B_STAR", ASSUME)
    kw.update(warmup=d.WARMUP, duration=duration, retry_min_interval=1.0, retry_max_attempts=10)
    if variant in STATIC_VARIANTS:
        x_init = random_layout(sc, seed) if variant == "sr" else X0
        if variant == "graphaware_standalone":
            kw["dispatcher"] = GraphAware(alpha=1.0, beta=GA_BETA)
        sim = Sim(sc, x_init.copy(), adjuster=None, seed=seed + 400, **kw)
    else:
        if variant == "graphaware_route":
            cand, extra, router = "nosim", dict(lam=0.5), GraphAware(alpha=1.0, beta=GA_BETA)
        else:
            cand, extra, routing = VARIANTS[variant]
            router = FaaSPRRouter(seed=seed + 900, n_paths=int(os.environ.get("FP_PATHS", 300))) if routing else None
        if router is not None:
            kw["dispatcher"] = router
        adj = O3SimAdjuster(make_adjuster("B_STAR", ASSUME, seed=seed + 300), MOVE_PERIOD_F3, epoch=60.0, horizon=120.0, K=5,
                             seed=seed + 800, warmup=d.WARMUP, blind=True, cand_mode=cand, churn=dict(FROZEN2, **extra),
                             sizing_cache=sizing_cache)
        kw["interval"] = adj.next_interval
        sim = Sim(sc, X0.copy(), adjuster=adj, seed=seed + 400, **kw)
    T, exp_arr = fig11.instrument(sim)
    done = []
    o_done = sim._ev_done

    def watch(ins, token, c, o_done=o_done):
        run = ins.run
        o_done(ins, token, c)
        if run is not None and run.req.t_done is not None and sim.in_window(run.req.t_arr) and run.req not in done:
            done.append(run.req)
    sim._ev_done = watch
    res = sim.run()
    sim.check_invariants()
    b = fig11.breakdown(sim, T, exp_arr, done)
    b["p99_makespan"] = res["p99_makespan"]
    b["mean_containers"] = res["mean_containers"]
    b["cold_starts"] = res["cold_starts"]
    b["mb_relocated"] = res["mb_relocated"]
    b["n_moved"] = res["n_moved"]
    return b


if __name__ == "__main__":
    names = sys.argv[1].split(",") if len(sys.argv) > 1 else ALL_VARIANTS
    out = {}
    for fam, rho, k, seed in CASES:
        sc, X0 = build(fam, rho, k, seed)
        sizing_cache = {}          # shared across this case's variants: one exogenous sizing schedule, computed once
        for v in names:
            key = f"{fam}_r{rho}_k{k}_s{seed}_{v}"
            print(f"{key}  [dispatcher: {DISPATCHER_LABEL[v]} | placement: {PLACEMENT_LABEL[v]}]", flush=True)
            b = run_one(fam, rho, k, seed, v, sc=sc, X0=X0, sizing_cache=sizing_cache)
            out[key] = dict(b, dispatcher=DISPATCHER_LABEL[v], placement=PLACEMENT_LABEL[v])
            print(f"  p99 {b['p99_makespan']:7.1f} | transfer {b['transfer']:5.2f} cold {b['cold']:5.2f} queue {b['queue']:5.2f} "
                  f"reroute {b['reroute']:5.2f} exec {b['exec']:5.2f} | mb_relocated {b['mb_relocated']:8.1f} "
                  f"cold_starts {b['cold_starts']:4d} n_moved {b['n_moved']:5d} | n {b['n']}", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "faaspr_fig11_f3_breakdown.json").write_text(json.dumps(out, indent=1))
