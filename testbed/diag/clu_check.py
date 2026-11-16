"""Implementation checks of CLU (knowledge/synthesis/clusterless-baseline.md, section 6): short runs on the live cells, development seed 1.
  ~/venv-dfps/bin/python testbed/diag/clu_check.py [warm window]    (invariants, completion, decision time, estimate audit; no comparison with other systems)"""
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from dfps.clusterless import ClusterLessPolicy                    # noqa: E402
from dfps.nsga2 import PlacementProblem                           # noqa: E402
from dfps.ondemand import OnDemandSim                             # noqa: E402
from testbed import queue_runs as QR                              # noqa: E402
from testbed import sebs_scenario as S                            # noqa: E402

warm = float(sys.argv[1]) if len(sys.argv) > 1 else 30.0
window = float(sys.argv[2]) if len(sys.argv) > 2 else 120.0
print(f"short runs: warm-up {warm:.0f} s + window {window:.0f} s, seed 1, live-cell loads, CAP-W2")
for app in ["690.ml", "660.map-reduce", "650.vid", "680.excamera"]:
    for refine in (True, False):
        rho = QR.AZURE_CELLS[app][0]
        sc, samp = S.build(1, apps=[app], rho=rho, ne=10, duration_s=warm + window, arrivals="azure", weights="memory", peak_tasks_cap=S.PEAK_TASKS_CAP)
        pol = ClusterLessPolicy(seed=501, kappa=1.5, refine=refine, audit=True)
        sim = OnDemandSim(sc, pol, seed=401, duration=warm + window, warmup=warm, exec_sampler=samp)
        t0 = time.time()
        r = sim.run()
        wall = time.time() - t0
        sim.check_invariants()
        st = pol.stats()
        a = np.array(pol.audit)
        pred, real = a[:, 0], a[:, 1]
        ratio = float(np.median(pred / np.maximum(real, 1e-9)))
        print(f"{app:15} {'CLU  ' if refine else 'CLU-S'} completed {r['n_completed']}/{r['n_arrived']} P99 {r['p99_makespan']:.2f}s avg {r['avg_makespan']:.2f}s cold {r['cold_starts']} "
              f"| plans {st['plans']} replans {st['replans']} escal {st['escalations']} cold-mode {st['cold_mode_decisions']} pred-viol {st['pred_violated']} real-viol {st['real_violated']}/{st['requests']} "
              f"| plan ms p50 {st['plan_ms_p50']:.2f} p99 {st['plan_ms_p99']:.2f} max {st['plan_ms_max']:.1f} | time-to-finish pred/real median {ratio:.2f}, "
              f"mean pred {pred.mean():.2f}s real {real.mean():.2f}s | wall {wall:.0f}s", flush=True)
