"""Check (pre-registration step): the implemented late_bind switch against the diagnostic oracle on the development cells, seeds 1-3, simulator."""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from testbed import frozen_live as FL, sebs_scenario as S               # noqa: E402
from testbed.queue_runs import CELLS, ORDER                             # noqa: E402
from dfps.nsga2 import PlacementProblem                                 # noqa: E402
ORACLE = {"690.ml": 2.81, "660.map-reduce": 3.96, "650.vid": 36.45, "6200.trip-booking": 2.05, "680.excamera": 138.68}   # P99 means of the oracle, late binding alone
for app in ORDER:
    rho, cap, warm, window, drain = CELLS[app]; dur = warm + window; P = {"frozen4": [], "frozen5": []}; ms = []
    for seed in (1, 2, 3):
        sc, samp = S.build(seed, apps=[app], rho=rho, ne=10, duration_s=dur, rate_cap=cap)
        X0 = PlacementProblem(sc.network, sc.ecc, np.array([f.exec_time for f in sc.functions])).random(np.random.default_rng(seed))
        for arm in P:
            sim, _ = FL.build(sc, X0, seed, arm=arm, warmup=warm, duration=dur, exec_sampler=samp)
            P[arm].append(sim.run()["p99_makespan"])
            if arm == "frozen5": ms += sim.late_bind_ms
    print(f"{app:18} P99 frozen4 {np.mean(P['frozen4']):8.2f}  frozen5 {np.mean(P['frozen5']):8.2f}  (oracle {ORACLE[app]:.2f})  ratio {np.exp(np.mean(np.log(np.array(P['frozen5'])/np.array(P['frozen4'])))):.3f}  decision p99 {np.percentile(ms,99):.3f} ms, max {max(ms):.2f} ms", flush=True)
