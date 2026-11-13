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
    arm, app, seed, ne, weights = job
    rho, warm, window, drain = QR.AZURE_CELLS[app]
    duration = warm + window
    t0 = time.time()
    sc, samp = S.build(seed, apps=[app], rho=rho, ne=ne, duration_s=duration, arrivals="azure", weights=weights)
    assert sc.meta["capacity_model"] != "CAP-U" or weights == "uniform"                # CAP-U only when asked for explicitly (a labelled comparison)
    X0 = PlacementProblem(sc.network, sc.ecc, np.array([f.exec_time for f in sc.functions]), fw=sc.fw).random(np.random.default_rng(seed))
    build, _, _ = CC.systems(arm)
    sim, _ = build(sc, X0, seed, warmup=warm, duration=duration, exec_sampler=samp)
    sim.track_res = True
    r = sim.run()
    out = {"arm": arm, "app": app, "seed": seed, "capacity_model": sc.meta["capacity_model"], "rho_effective": sc.meta["rho_effective"], "wall_s": round(time.time() - t0, 1),
           **CC.pick(r), "resources": r.get("resources"), "mb_relocated": r.get("mb_relocated")}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--weights", default="memory")
    ap.add_argument("--ne", type=int, default=10)
    ap.add_argument("--seeds", default="1,2")
    ap.add_argument("--apps", default=",".join(QR.PLANS["azure-initial"]["apps"]))
    ap.add_argument("--arms", default=",".join(QR.PLANS["azure-initial"]["arms"]))
    a = ap.parse_args()
    out = Path(a.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    jobs = [(arm, app, int(s), a.ne, a.weights) for s in a.seeds.split(",") for app in a.apps.split(",") for arm in a.arms.split(",")]
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
