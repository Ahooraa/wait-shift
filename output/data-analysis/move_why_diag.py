"""Why does the mover move tasks? (3 Nov 2026) Logging-only runs of "ours" under CAP-W1 (the six step-1 cases) with churn["log_move_why"]: for
every accepted rule move, the three terms of the AET estimate at source and destination and the context. The event hash must equal the stored
capW1_light run. Reading fixed in knowledge/synthesis/workflow-aware-decision-rules.md ("Why does the mover move tasks?").
  python move_why_diag.py run [workers] | report
"""
import json
import pickle
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
OUT = ROOT / "results" / "move_why"
W1 = ROOT / "results" / "capW1_light"
CASES = [f"{f}_r{r}_s1" for f in ("F1", "F2") for r in (0.5, 0.7, 0.85)]
DURATION, WARMUP, LAM = 900.0, 60.0, 0.5
C = dict(now=0, rid=1, task=2, f=3, nmv=4, pos=5, qlen=6, cnt_k=7, cnt_k2=8, qlen_k2=9, in0=10, svc0=11, out0=12, in1=13, svc1=14, out1=15,
         src_plan=16, dst_plan=17, age=18, a0=19, a1=20, dst_child=21, src_child=22)


def run_job(tg):
    out = OUT / f"{tg}.json"
    if out.exists():
        return str(out)
    try:
        import numpy as _np
        assert _np.__version__.startswith("1."), "run with the Anaconda interpreter (numpy 1.26)"
        import yaml
        from dfps.dispatch_priority import QueuePriority
        from dfps.o3s import O3SimAdjuster
        from dfps.sim import Sim
        from dfps.variants import make_adjuster, sim_kwargs
        from frozen2 import FROZEN2, MOVE_PERIOD_S
        A = yaml.safe_load((ROOT / "config" / "assumptions.yaml").read_text(encoding="utf-8"))
        P = pickle.load(open(W1 / f"{tg}.sc.pkl", "rb"))
        sc, X0 = P["sc"], P["X0"]
        seed, fam = int(tg.split("_s")[1]), tg.split("_r")[0]
        kw = sim_kwargs("B_STAR", A)
        kw.update(warmup=WARMUP, duration=DURATION, retry_min_interval=1.0, retry_max_attempts=10)
        kw["queue_priority"] = QueuePriority("full", aging=2.0)
        adj = O3SimAdjuster(make_adjuster("B_STAR", A, seed=seed + 300), MOVE_PERIOD_S[fam], epoch=60.0, horizon=30.0, K=8,
                            seed=seed + 800, warmup=WARMUP, blind=True, cand_mode="nosim", churn=dict(FROZEN2, lam=LAM, log_move_why=True))
        kw["interval"] = adj.next_interval
        t0 = time.time()
        sim = Sim(sc, X0.copy(), adjuster=adj, seed=seed + 400, **kw)
        r = sim.run()
        sim.check_invariants()
        stored = json.loads((W1 / f"{tg}.ours.json").read_text())["result"]["event_hash"]
        OUT.mkdir(parents=True, exist_ok=True)
        np.save(OUT / f"{tg}.npy", np.array(getattr(adj, "why_log", []), dtype=float))
        out.write_text(json.dumps(dict(case=tg, p99=r["p99_makespan"], hash_matches_stored=(r["event_hash"] == stored), wall_s=time.time() - t0,
                                       n_logged=len(getattr(adj, "why_log", [])), n_moved=r["n_moved"])))
    except Exception:
        import traceback
        OUT.mkdir(parents=True, exist_ok=True)
        out.with_suffix(".err").write_text(traceback.format_exc())
        return str(out) + " FAILED"
    return str(out)


def run(workers):
    todo = [c for c in CASES if not (OUT / f"{c}.json").exists()]
    todo.sort(key=lambda c: -float(c.split("_r")[1].split("_")[0]))
    print(len(todo), "runs", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        for r in ex.map(run_job, todo):
            print("done", r, flush=True)


def report():
    nw = npull = done = 0
    for tg in CASES:
        p = OUT / f"{tg}.json"
        if not p.exists():
            print(tg, "missing")
            continue
        m = json.loads(p.read_text())
        if not m["hash_matches_stored"]:
            print(tg, "EVENT HASH DIFFERS from the stored run -> not used")
            continue
        a = np.load(OUT / f"{tg}.npy")
        a = a[a[:, C["now"]] >= WARMUP]

        def g(k):
            return a[:, C[k]]
        dIN, dSVC, dOUT = g("in0") - g("in1"), g("svc0") - g("svc1"), LAM * (g("out0") - g("out1"))
        G = dIN + dSVC + dOUT
        ben = np.maximum(dSVC, 0) + np.maximum(dOUT, 0)
        wait = (dSVC >= 0.5 * ben) & (ben > 0)
        pull = ~wait
        done += 1
        nw += wait.mean() >= 0.60
        npull += pull.mean() >= 0.30
        idle = g("qlen_k2") < g("cnt_k2")
        print(f"{tg}: moves {len(a)}  WAIT-driven {wait.mean():.0%}  PULL-driven {pull.mean():.0%}  | G mean {G.mean():.2f}s = dIN {dIN.mean():+.2f} + dSVC {dSVC.mean():+.2f} + dOUT {dOUT.mean():+.2f}"
              f"\n          source=plan {g('src_plan').mean():.0%}  dest=plan {g('dst_plan').mean():.0%}  dest hosts a planned child {g('dst_child').mean():.0%} (source {g('src_child').mean():.0%})"
              f"  predicted-idle dest {idle.mean():.0%}  repeat moves {(g('nmv') > 0).mean():.0%}"
              f"  queue/containers src {np.mean(g('qlen') / np.maximum(g('cnt_k'), 1)):.1f} vs dst {np.mean(g('qlen_k2') / np.maximum(g('cnt_k2'), 1)):.1f}  age at move median {np.median(g('age')):.1f}s")
    if done == len(CASES):
        print(f"\nWAIT-driven >= 60% in {nw}/6 cases -> {'WAIT holds' if nw >= 4 else 'WAIT not shown'};  PULL-driven >= 30% in {npull}/6 -> {'PULL holds' if npull >= 4 else 'PULL not shown'}")


if __name__ == "__main__":
    {"run": lambda: run(int(sys.argv[2]) if len(sys.argv) > 2 else 3), "report": report}[sys.argv[1]]()
