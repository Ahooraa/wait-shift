"""Diagnostic: does the data-affinity term in our placement matter for P99 as data size grows? (2026-10-25)

NOT a clean placement-objective ablation: the move rule (Sol.aet) prices transfer to each child's PLANNED node, and the plan
comes from placement. Turning affinity off changes the plans the move rule is priced against, so this ablates data-aware
PLANNING as a whole (placement + the moves that are scored relative to it), not placement in isolation.

At k = 1 the measured ceiling for perfect co-location (knowledge/synthesis/workflow-aware-decision-rules.md) is small (2.8%
on one scenario); this probe checks whether dropping the affinity term costs P99 more as state sizes grow, while sizing, the
queueing term, capacity constraints and incremental construction stay identical. `ours` = FROZEN2 (affinity=True, the
default). `ours_noaff` = FROZEN2 with the workflow-partner term in demand_points zeroed (dfps/controllers.py:demand_points,
affinity=False): placement still respects capacity and spreads by the queueing term, but no longer pulls a function toward its
producers/consumers. Node storage scales with k (see workflow_stress.py). Scenarios: mix (Azure 70/85%) and chain12, k in {1, 10}.

Pre-registered reading (knowledge/synthesis/workflow-aware-decision-rules.md): bar is ours_noaff >= 3% worse at k = 10 AND
<= 1% worse at k = 1 to call the current term load-bearing. A SMALL loss at k = 10 (well under the 9-14% re-binding/co-location
ceilings measured by bounds_run.py) despite those ceilings existing would mean the current heuristic captures little of the
available headroom -- that specific combination reopens data-aware placement as a direction, with evidence.
  python affinity_probe.py run [workers] | analyze
"""
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(ROOT))
import d3s_headroom as d  # noqa: E402
import workflow_stress as w  # noqa: E402
from frozen2 import FROZEN2, MOVE_PERIOD_S  # noqa: E402

from dfps.o3s import O3SimAdjuster  # noqa: E402
from dfps.sim import Sim  # noqa: E402
from dfps.variants import make_adjuster, sim_kwargs  # noqa: E402

RUNS = ROOT / "results" / "affinity_probe"
SCENARIOS = [("mix", "F1", 0.7, 1), ("mix", "F1", 0.85, 1), ("chain12", "F1", 0.85, 1)]
KS = (1, 10)
CTRLS = {"ours": {}, "ours_noaff": {"affinity": False}}


def one(args, duration=None, out=None):
    scen, k, ctrl = args
    out = RUNS / f"{w.tag(scen, k)}.{ctrl}.json" if out is None else out
    if out.exists():
        return str(out)
    try:
        assert np.__version__.startswith("1."), "run with the Anaconda interpreter (numpy 1.26)"
        sc0, X0 = w.load(scen)
        sc = w.scale(sc0, k)
        seed = scen[3]
        T = w.tstars()[scen[1]]
        kw = sim_kwargs("B_STAR", w.ASSUME)
        kw.update(warmup=d.WARMUP, duration=d.DURATION if duration is None else duration, retry_min_interval=1.0, retry_max_attempts=10)
        churn = dict(FROZEN2, **CTRLS[ctrl])
        adj = O3SimAdjuster(make_adjuster("B_STAR", w.ASSUME, seed=seed + 300), MOVE_PERIOD_S[scen[1]], epoch=60.0, horizon=120.0, K=5,
                            seed=seed + 800, warmup=d.WARMUP, blind=True, cand_mode="nosim", churn=churn)
        kw["interval"] = adj.next_interval
        t = time.time()
        sim = Sim(sc, X0, adjuster=adj, seed=seed + 400, trace=True, **kw)
        r = sim.run()
        sim.check_invariants()
        r["wall_s"] = time.time() - t
        from dfps.diagnostics import summarize
        try:
            diag = summarize(sim)
        except Exception:
            diag = {}
        out.write_text(json.dumps(dict(scenario=list(scen), k=k, ctrl=ctrl, result=r, diag=diag)))
        return str(out)
    except Exception:
        import traceback
        out.with_suffix(".err").write_text(traceback.format_exc())
        return str(out) + " FAILED"


def run(workers):
    RUNS.mkdir(parents=True, exist_ok=True)
    jobs = [(scen, k, c) for scen in SCENARIOS for k in KS for c in CTRLS]
    jobs = [j for j in jobs if not (RUNS / f"{w.tag(j[0], j[1])}.{j[2]}.json").exists()]
    print(f"{len(jobs)} runs", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        for r in ex.map(one, jobs):
            print("done", r, flush=True)


def analyze():
    rows = {}
    for f in RUNS.glob("*.json"):
        x = json.loads(f.read_text())
        rows[(tuple(x["scenario"]), x["k"], x["ctrl"])] = x
    print("data-aware planning ablation (placement + the moves priced against its plans); bar: >=3% worse at k=10, <=1% at k=1")
    print("%-16s k | ours P99   noaff P99   change | cold ours   cold_noaff | mv/req ours  noaff | local edges final (ours -> noaff)" % "scenario")
    for scen in SCENARIOS:
        for k in KS:
            a = rows.get((tuple(scen), k, "ours"))
            b = rows.get((tuple(scen), k, "ours_noaff"))
            if not a or not b:
                continue
            p_a, p_b = a["result"]["p99_makespan"], b["result"]["p99_makespan"]
            mv_a = a["result"]["n_moved"] / max(1, a["result"]["n_completed"])
            mv_b = b["result"]["n_moved"] / max(1, b["result"]["n_completed"])
            la = a.get("diag", {}).get("all_local_final", float("nan"))
            lb = b.get("diag", {}).get("all_local_final", float("nan"))
            print("%-16s %2d | %8.1f   %8.1f   %+6.1f%% | %6d   %6d | %6.2f   %5.2f | %4.1f%% -> %4.1f%%" % (
                scen[0], k, p_a, p_b, 100 * (p_b - p_a) / p_a, a["result"]["cold_starts"], b["result"]["cold_starts"],
                mv_a, mv_b, 100 * la, 100 * lb))


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 4)
    else:
        analyze()
