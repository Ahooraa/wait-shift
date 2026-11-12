"""Diagnostic: does FROZEN-4's queueing in a cell depend on how often the mover corrects the queues? (simulator only; the controller itself is unchanged)"""
import sys, math
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from testbed.diag.latency_breakdown import RecSim, breakdown          # noqa: E402
from testbed import frozen_live as FL, sebs_scenario as S             # noqa: E402
from testbed.queue_runs import CELLS                                  # noqa: E402
from dfps.nsga2 import PlacementProblem                               # noqa: E402

def erlang_wait(c, a, mu):
    """mean wait in an M/M/c queue, c servers (float rounded), offered load a erlangs, service rate mu"""
    c = int(round(c)); rho = a / c
    if rho >= 1: return float("inf")
    s = sum(a**k / math.factorial(k) for k in range(c)); t = a**c / math.factorial(c) / (1 - rho)
    return (t / (s + t)) / (c * mu - a * mu)

app, seeds = sys.argv[1], [1, 2, 3]
rho, cap, warm, window, drain = CELLS[app]; dur = warm + window
print(app, "mean over seeds 1-3: P99, mean queue, top-5% queue, moves")
for per in (4.0, 2.0, 1.0, 0.5):
    P, Q, QT, MV = [], [], [], []
    for seed in seeds:
        sc, samp = S.build(seed, apps=[app], rho=rho, ne=10, duration_s=dur, rate_cap=cap)
        X0 = PlacementProblem(sc.network, sc.ecc, np.array([f.exec_time for f in sc.functions])).random(np.random.default_rng(seed))
        sim, _ = FL.build(sc, X0, seed, arm="frozen4", warmup=warm, duration=dur, exec_sampler=samp, sim_cls=RecSim, move_period=per)
        out = sim.run(); arr, bad = breakdown(sim)
        top = arr[arr[:, 0] >= np.percentile(arr[:, 0], 95)]
        P.append(out["p99_makespan"]); Q.append(arr[:, 2].mean()); QT.append(top[:, 2].mean()); MV.append(out["n_moved"])
    print(f"  mover period {per:>4} s: P99 {np.mean(P):8.2f}  queue {np.mean(Q):6.2f}  queue top5% {np.mean(QT):6.2f}  moves {np.mean(MV):8.0f}", flush=True)
print("M/M/c reference for ExCamera function 0 if its 95 containers were ONE pool vs 10 per-node pools of ~9.5:")
mu = 1 / 27.88; a = 0.5 * 5 * 27.88
print(f"  one pool c=95: wait {erlang_wait(95, a, mu):.3f} s;   ten pools c~9.5 (a/10 each): wait {erlang_wait(9.5, a/10, mu):.2f} s")
