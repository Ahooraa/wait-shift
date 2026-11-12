"""Diagnostic (simulator only, development seeds 1-3): FROZEN-4 with its own dispatcher (transfer_only) against other dispatchers, same mover, same layout controller.
Shows how much of the queueing in a cell comes from WHERE tasks are sent at request arrival (transfer_only ignores waiting)."""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from testbed.diag.latency_breakdown import RecSim, breakdown            # noqa: E402
from testbed import frozen_live as FL, sebs_scenario as S               # noqa: E402
from testbed.queue_runs import CELLS                                    # noqa: E402
from dfps.nsga2 import PlacementProblem                                 # noqa: E402
from dfps import dispatchers as D                                       # noqa: E402

apps = sys.argv[1].split(",")
names = sys.argv[2].split(",") if len(sys.argv) > 2 else ["transfer_only", "jsq", "mover_aet", "greedy_eft"]
for app in apps:
    rho, cap, warm, window, drain = CELLS[app]; dur = warm + window
    print(f"\n{app}  (mean over seeds 1-3)", flush=True)
    for name in names:
        P, P50, Q, QT, MV, CS, TR = [], [], [], [], [], [], []
        for seed in (1, 2, 3):
            sc, samp = S.build(seed, apps=[app], rho=rho, ne=10, duration_s=dur, rate_cap=cap)
            X0 = PlacementProblem(sc.network, sc.ecc, np.array([f.exec_time for f in sc.functions])).random(np.random.default_rng(seed))
            sim, _ = FL.build(sc, X0, seed, arm="frozen4", warmup=warm, duration=dur, exec_sampler=samp, sim_cls=RecSim, dispatcher=D.DISPATCHERS[name])
            out = sim.run(); arr, bad = breakdown(sim)
            top = arr[arr[:, 0] >= np.percentile(arr[:, 0], 95)]
            P.append(out["p99_makespan"]); P50.append(out["p50_makespan"]); Q.append(arr[:, 2].mean()); QT.append(top[:, 2].mean())
            MV.append(out["n_moved"]); CS.append(out["cold_starts"]); TR.append(arr[:, 1].mean())
        print(f"  {name:14} P50 {np.mean(P50):7.2f}  P99 {np.mean(P):8.2f}  queue {np.mean(Q):6.2f}  queue top5% {np.mean(QT):6.2f}  transfer {np.mean(TR):5.2f}  moves {np.mean(MV):7.0f}  cold {np.mean(CS):5.0f}", flush=True)
