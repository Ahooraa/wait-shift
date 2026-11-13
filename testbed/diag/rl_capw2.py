"""Why is RL so slow on CAP-W2? (13 Nov 2026, user question.) One cell, several RL / Heu variants on the same scenario, with what the policy actually did.

  ~/venv-dfps/bin/python testbed/diag/rl_capw2.py 690.ml 1
"""
import sys
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from testbed import queue_runs as QR, sebs_scenario as S        # noqa: E402
from dfps.ondemand import OnDemandSim                           # noqa: E402
from dfps.heu import HeuPolicy                                  # noqa: E402
from experiments.run import load_rl_policy                      # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def run(job):
    app, seed, variant = job
    rho, warm, window, _ = QR.AZURE_CELLS[app]
    weights = "uniform" if variant.endswith("_u") else "memory"
    sc, samp = S.build(seed, apps=[app], rho=rho, ne=10, duration_s=warm + window, arrivals="azure", weights=weights)
    if variant.startswith("rl_size"):
        pol = load_rl_policy(str(ROOT / "results" / "rl_policy_capw1.pt"), seed + 600, sizes=True)
    elif variant.startswith("rl"):
        pol = load_rl_policy(str(ROOT / "results" / "rl_policy.pt"), seed + 600)
    else:
        pol = HeuPolicy(seed=seed + 500)
    chosen, warm_hit, qlen, room_ok = np.zeros(10), [0, 0], [], [0, 0]
    if variant.startswith("rl"):
        orig = pol.choose

        def choose(sim, r, t):
            k = orig(sim, r, t)
            if k is not None:
                chosen[k] += 1
                warm_hit[0] += int(sim.idle[r.wf.ft[t], k] > 0)
                warm_hit[1] += 1
                qlen.append(len(sim.nq[k]))
                used = float(np.asarray(sim.sc.fw) @ sim.cnt[:, k])
                room_ok[0] += int(used + sim.sc.fw[r.wf.ft[t]] <= sim.ecc[k] + 1e-9)
                room_ok[1] += 1
            return k
        pol.choose = choose
    sim = OnDemandSim(sc, pol, seed=seed + 400, duration=warm + window, warmup=warm, exec_sampler=samp)
    sim.track_res = True
    r = sim.run()
    fw = np.asarray(sc.fw)
    out = dict(variant=variant, capacity=sc.meta["capacity_model"], fw=[round(float(x), 3) for x in fw], mean_fw=float(fw.mean()), mean=r["avg_makespan"], p50=r["p50_makespan"],
               p99=r["p99_makespan"], cold=r["cold_starts"], recycled=sim.n_recycled, expired=sim.n_expired, mean_containers=r["resources"]["mean_containers"],
               mean_capacity=r["resources"]["mean_capacity"], capacity_budget=float(sc.ecc.sum()), ecc=sc.ecc.tolist())
    if chosen.sum():
        out.update(node_share=(chosen / chosen.sum()).round(3).tolist(), ecc_share=(sc.ecc / sc.ecc.sum()).round(3).tolist(), warm_hit=warm_hit[0] / max(1, warm_hit[1]),
                   mean_qlen_at_choice=float(np.mean(qlen)), fits_without_evicting=room_ok[0] / max(1, room_ok[1]))
    return out


if __name__ == "__main__":
    app, seed = sys.argv[1], int(sys.argv[2])
    variants = sys.argv[3].split(",") if len(sys.argv) > 3 else ["rl_w2", "rl_size_w2", "heu_w2", "heu_u"]
    with ProcessPoolExecutor(len(variants)) as ex:
        for o in ex.map(run, [(app, seed, v) for v in variants]):
            print(json.dumps(o), flush=True)
