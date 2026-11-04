"""Why does a per-task finish-time dispatcher beat the DFPS matcher with moves on?  Calibration comparison (3 Nov 2026, user request).

Both dispatchers rank nodes with the same simulator quantity, FST (the start-wait estimate of a function at a node, Sim.fst_vec), taken at
arrival. This script logs, per task, the FST of the node the policy chose (at planning) and compares it with the wait that task then
realised (first enqueue -> start, so it includes waits after request moves). CAP-W1, "ours" controller with the criticality queue order;
ONLY the dispatcher differs between the arms:
   ours   DFPS graph pattern matching          ccag   greedy_eft (per task: input transfer + FST)          ga   GraphAware, beta = 4
Cases: F1 85%, F2 85%, F1 70%, seed 1 (9 runs). The "ours" arm must reproduce the stored capW1_light event hash (trace changes nothing).

Readings fixed before any run (knowledge/synthesis/workflow-aware-decision-rules.md, "Dispatcher calibration"):
  per task: error = realised wait - predicted FST. Reported by arm for root tasks (planned moments before they run: pure selection effect,
  no staleness) and for non-root tasks (adds staleness), mean error and mean absolute error, plus the Spearman correlation between
  predicted and realised wait over the non-root tasks of each function (does the estimate rank the nodes it chose?).
  CAL: the matcher is worse calibrated if its mean absolute error on non-root tasks exceeds greedy_eft's by >= 20% in at least 2 of 3 cases.
  If it does, and the root-task error also differs, the cause is the selection (what the matcher picks), not staleness. If it does not,
  estimate quality does not explain the gain and the cause lies elsewhere (placement of siblings, transfer-vs-queue balance).
  python dispatch_calibration.py run [workers] | report | smoke
"""
import collections
import json
import os
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
OUT = ROOT / "results" / "dispatch_calibration"
W1 = ROOT / "results" / "capW1_light"
CASES = ["F1_r0.85_s1", "F2_r0.85_s1", "F1_r0.7_s1"]
ARMS = tuple(os.environ.get("CAL_ARMS", "ours,ccag,ga").split(","))   # CAL_ARMS=ours,ccag runs the arms that do not depend on the Graph-Aware port
DURATION, WARMUP = 900.0, 60.0


def run_job(args):
    tg, arm, duration = args
    out = OUT / (f"{tg}.{arm}.json" if duration == DURATION else f"smoke_{tg}.{arm}.json")
    if out.exists():
        return str(out)
    try:
        import numpy as _np
        assert _np.__version__.startswith("1."), "run with the Anaconda interpreter (numpy 1.26)"
        import yaml
        from dfps import dispatchers as D
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
        kw.update(warmup=WARMUP, duration=duration, retry_min_interval=1.0, retry_max_attempts=10, trace=True)
        kw["queue_priority"] = QueuePriority("full", aging=2.0)
        if arm == "ccag":
            kw["dispatcher"] = D.greedy_eft
        elif arm == "ga":
            kw["dispatcher"] = D.GraphAware(alpha=1.0, beta=4.0)
        adj = O3SimAdjuster(make_adjuster("B_STAR", A, seed=seed + 300), MOVE_PERIOD_S[fam], epoch=60.0, horizon=30.0, K=8,
                            seed=seed + 800, warmup=WARMUP, blind=True, cand_mode="nosim", churn=dict(FROZEN2, lam=0.5))
        kw["interval"] = adj.next_interval
        t0 = time.time()
        sim = Sim(sc, X0.copy(), adjuster=adj, seed=seed + 400, **kw)
        r = sim.run()
        sim.check_invariants()
        stored = json.loads((W1 / f"{tg}.ours.json").read_text())["result"]["event_hash"] if (arm == "ours" and duration == DURATION) else None
        OUT.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(dict(case=tg, arm=arm, duration=duration, p99=r["p99_makespan"], avg=r["avg_makespan"],
                                       cold=r["cold_starts"], n_moved=r["n_moved"], event_hash=r["event_hash"],
                                       hash_matches_stored=(r["event_hash"] == stored) if stored else None, wall_s=time.time() - t0,
                                       tasks=sim.trace["tasks"], pred=sim.trace.get("pred", []))))
    except Exception:
        import traceback
        OUT.mkdir(parents=True, exist_ok=True)
        out.with_suffix(".err").write_text(traceback.format_exc())
        return str(out) + " FAILED"
    return str(out)


def run(workers):
    todo = [(c, a, DURATION) for c in CASES for a in ARMS if not (OUT / f"{c}.{a}.json").exists()]
    print(len(todo), "runs", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        for r in ex.map(run_job, todo):
            print("done", r, flush=True)


def spearman(a, b):
    if len(a) < 10:
        return float("nan")
    ra, rb = np.argsort(np.argsort(a)), np.argsort(np.argsort(b))
    return float(np.corrcoef(ra, rb)[0, 1])


def stats(d, roots):
    pred = {p[0]: p[2] for p in d["pred"]}
    rows = []
    for t in d["tasks"]:                                       # (rid, wid, task, plan, node, t_first, t_start, t_done, n_moves)
        p = pred.get(t[0])
        if p is None:
            continue
        rows.append((t[1], t[2], int(t[2]) in roots[int(t[1])], p[int(t[2])], t[6] - t[5], t[4] != t[3]))
    out = {}
    for name, sel in (("root", True), ("non-root", False)):
        r = [x for x in rows if x[2] == sel]
        pr, wa = np.array([x[3] for x in r]), np.array([x[4] for x in r])
        e = wa - pr
        out[name] = dict(n=len(r), pred=float(pr.mean()), real=float(wa.mean()), bias=float(e.mean()), mae=float(np.abs(e).mean()),
                         rho=spearman(pr, wa), off_plan=float(np.mean([x[5] for x in r])))
    return out


def report():
    from dfps.profiles import load_profiles  # noqa: F401  (keeps the import path identical to the runner)
    tab = {}
    for tg in CASES:
        sc = pickle.load(open(W1 / f"{tg}.sc.pkl", "rb"))["sc"]
        roots = {w.id: set(w.roots) for w in sc.workflows}
        for arm in ARMS:
            p = OUT / f"{tg}.{arm}.json"
            if not p.exists():
                continue
            d = json.loads(p.read_text())
            if arm == "ours" and not d["hash_matches_stored"]:
                print(tg, arm, "EVENT HASH DIFFERS from the stored run -> not used")
                continue
            s = stats(d, roots)
            tab[(tg, arm)] = s
            print(f"{tg} {arm:5s} P99 {d['p99']:6.1f} avg {d['avg']:5.1f} cold {d['cold']}  |  "
                  + "  |  ".join(f"{k}: n={v['n']} pred {v['pred']:.1f} real {v['real']:.1f} bias {v['bias']:+.1f} MAE {v['mae']:.1f} rho {v['rho']:.2f} off-plan {v['off_plan']:.0%}"
                                  for k, v in s.items()))
    done = [tg for tg in CASES if all((tg, a) in tab for a in ("ours", "ccag"))]
    if len(done) == len(CASES):
        n = sum(tab[(tg, "ours")]["non-root"]["mae"] >= 1.2 * tab[(tg, "ccag")]["non-root"]["mae"] for tg in CASES)
        print(f"\nCAL: matcher MAE on non-root tasks >= 1.2 x greedy_eft's in {n}/3 cases -> "
              f"{'matcher worse calibrated' if n >= 2 else 'estimate quality does not explain the gain'}")


if __name__ == "__main__":
    {"run": lambda: run(int(sys.argv[2]) if len(sys.argv) > 2 else 2), "report": report,
     "smoke": lambda: [print(run_job((CASES[0], a, 100.0))) for a in ("ours", "ccag")]}[sys.argv[1]]()
