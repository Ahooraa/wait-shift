"""Simulator sweep of the testbed's cells (13 Nov 2026, user: a faster overall view of the baselines before the live runs).

The same scenario, system and arguments as `controller_check.py` (so the same Azure-trace arrivals, CAP-W2 weights, cluster, common random numbers and window), but only the
simulator reference: no agents, no guard. `track_res` adds the resources over the window (container-seconds, warm idle seconds, MB relocated) for every system.

  ~/venv-dfps/bin/python testbed/sim_sweep.py --out ~/testbed-results/sim-sweep-capw2 [--workers 6]
"""
import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from testbed import controller_check as CC                       # noqa: E402
from testbed import queue_runs as QR                             # noqa: E402
from testbed import sebs_scenario as S                           # noqa: E402
from dfps.nsga2 import PlacementProblem                          # noqa: E402


def one(job):
    arm, app, seed, ne, weights, rho_over, peak_cap, cold_s, *rest = job
    mem_scale = float(rest[0]) if rest else 1.0                    # 16 Nov 2026 (cost test): fraction of the cluster's memory
    rho, warm, window, drain = QR.AZURE_CELLS.get(app, (0.5, 60, 900, 600))        # 15 Nov 2026: Trip Booking and 1000Genome have no live cell; the simulator uses the ML cell's windows
    if rho_over is not None:
        rho = rho_over                                             # 14 Nov 2026 (user): the same cell at a higher nominal load
    duration = warm + window
    t0 = time.time()
    sc, samp = S.build(seed, apps=[app], rho=rho, ne=ne, duration_s=duration, arrivals="azure", weights=weights,
                           peak_tasks_cap=peak_cap, mem_scale=mem_scale)
    if cold_s is not None:                                         # 15 Nov 2026 (user): sensitivity to the cold-start duration; one value for every function (the measured medians are 0.22-0.34 s)
        from dataclasses import replace
        sc.functions = [replace(f, cold_start=float(cold_s)) for f in sc.functions]
    assert sc.meta["capacity_model"] != "CAP-U" or weights == "uniform"                # CAP-U only when asked for explicitly (a labelled comparison)
    X0 = PlacementProblem(sc.network, sc.ecc, np.array([f.exec_time for f in sc.functions]), fw=sc.fw).random(np.random.default_rng(seed))
    build, _, _ = CC.systems(arm)
    sim, adj = build(sc, X0, seed, warmup=warm, duration=duration, exec_sampler=samp)
    sim.track_res = True
    r = sim.run()
    out = {"arm": arm, "app": app, "seed": seed, "capacity_model": sc.meta["capacity_model"], "rho_nominal": rho, "rho_effective": sc.meta["rho_effective"], "mem_scale": mem_scale, "capacity_total": int(sum(sc.ecc)),
           "capacity_total_original": int(sc.meta.get("ecc_total_original", int(sum(sc.ecc)))), "peak_tasks_cap": peak_cap, "n_nodes": ne, "cold_start_s": cold_s, "wall_s": round(time.time() - t0, 1),
           **CC.pick(r), "resources": r.get("resources"), "mb_relocated": r.get("mb_relocated")}
    if hasattr(getattr(sim, "policy", None), "stats") and sim.policy.name == "CLU":                # 16 Nov 2026: ClusterLess-style baseline: plans, escalations, predicted and real deadline misses, plan time
        out["clu"] = sim.policy.stats()
    if getattr(adj, "churn", None) and adj.churn.get("fast_scale"):                 # 16 Nov 2026: what the trigger did and what it cost
        acts = [x for x in adj.fast_log if x.get("applied")]
        ft = np.array(adj.fast_times) if adj.fast_times else np.zeros(1)
        out["trigger"] = {"checks": len(adj.fast_times), "actions": len(acts), "added": int(sum(x["added"] for x in acts)), "removed": int(sum(x["removed"] for x in acts)),
                          "time_total_s": float(ft.sum()), "time_mean_ms": float(ft.mean() * 1e3), "time_p99_ms": float(np.percentile(ft, 99) * 1e3), "time_max_ms": float(ft.max() * 1e3)}
    ch = getattr(adj, "churn", None) or {}
    if ch.get("event_relayout") or ch.get("first_relayout") is not None or ch.get("fast_scale"):   # 16 Nov 2026: how often the layout changed and what it cost
        lg = adj.log
        dw = np.array([x["wall_s"] for x in lg]) if lg else np.zeros(1)
        et = np.array(adj.event_times) if adj.event_times else np.zeros(1)
        out["relayout"] = {"scheduled": int(sum(1 for x in lg if not x.get("event"))), "event": int(sum(1 for x in lg if x.get("event"))),
                           "switched": int(sum(1 for x in lg if x.get("switched"))), "first_t": (round(lg[0]["t"], 2) if lg else None),
                           "decide_total_s": float(dw.sum()), "decide_p99_ms": float(np.percentile(dw, 99) * 1e3),
                           "checks": len(adj.event_times), "check_p99_ms": float(np.percentile(et, 99) * 1e3), "check_max_ms": float(et.max() * 1e3)}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--weights", default="memory")
    ap.add_argument("--ne", type=int, default=10)
    ap.add_argument("--rho", type=float, default=None, help="override the cell's nominal load")
    ap.add_argument("--peak-cap", type=float, default=S.PEAK_TASKS_CAP, help="tasks/s cap on the busiest minute; 0 = none (simulator only: the hub sustains about 350)")
    ap.add_argument("--cold-s", type=float, default=None, help="cold-start duration in seconds for every function (default: the measured SeBS-Flow medians)")
    ap.add_argument("--mem-scale", type=float, default=1.0, help="fraction of the cluster's memory (same arrivals; cost test, 16 Nov 2026)")
    ap.add_argument("--seeds", default="1,2")
    ap.add_argument("--apps", default=",".join(QR.PLANS["azure-initial"]["apps"]))
    ap.add_argument("--arms", default=",".join(QR.PLANS["azure-initial"]["arms"]))
    a = ap.parse_args()
    out = Path(a.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    jobs = [(arm, app, int(s), a.ne, a.weights, a.rho, (a.peak_cap or None), a.cold_s, a.mem_scale) for s in a.seeds.split(",") for app in a.apps.split(",") for arm in a.arms.split(",")]
    jobs = [j for j in jobs if not (out / f"{j[1]}.s{j[2]}.{j[0]}.json").exists()]
    print(f"{len(jobs)} runs to do, {a.workers} workers", flush=True)
    with ProcessPoolExecutor(a.workers) as ex:
        futs = {ex.submit(one, j): j for j in jobs}
        from concurrent.futures import as_completed
        for f in as_completed(futs):
            j = futs[f]
            try:
                r = f.result()
            except Exception as e:                                    # noqa: BLE001 - a failed cell is reported and the sweep goes on
                print(f"FAILED {j}: {e!r}", flush=True)
                continue
            (out / f"{j[1]}.s{j[2]}.{j[0]}.json").write_text(json.dumps(r, indent=1))
            print(f"done {j[1]} s{j[2]} {j[0]}: P99 {r['p99_makespan']:.2f} s, completed {r['n_completed']}/{r['n_arrived']}, {r['wall_s']} s", flush=True)


if __name__ == "__main__":
    main()
