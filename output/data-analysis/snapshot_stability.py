"""Snapshot stability (4 Nov 2026, user request): does the best node for a task move between its binding (last parent finished) and the mover's
passes? For a deterministic half of the in-window non-root tasks the live AET of every feasible node is scored (input from the parents' nodes,
service estimate at the current queue, 0.5 x output to the children's planned nodes) at binding, at first enqueue, and 2 s and 4 s after it.
CAP-W1, controller "ours" (capw1_light run), six step-1 cases, trace only: the event hash must equal the stored run (this also shows that the
default-off move-veto code is inert). Reading fixed in knowledge/synthesis/workflow-aware-decision-rules.md ("Snapshot stability").
  python snapshot_stability.py run [workers] | report | smoke
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
OUT = ROOT / "results" / "snapshot_stability"
W1 = ROOT / "results" / "capW1_light"
CASES = [f"{f}_r{r}_s1" for f in ("F1", "F2") for r in (0.5, 0.7, 0.85)]
DURATION, WARMUP = 900.0, 60.0


def run_job(tg, duration=None):
    duration = duration or DURATION
    out = OUT / (f"{tg}.json" if duration == DURATION else f"smoke_{tg}.json")
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
        kw.update(warmup=WARMUP, duration=duration, retry_min_interval=1.0, retry_max_attempts=10, trace=True)
        kw["queue_priority"] = QueuePriority("full", aging=2.0)
        adj = O3SimAdjuster(make_adjuster("B_STAR", A, seed=seed + 300), MOVE_PERIOD_S[fam], epoch=60.0, horizon=30.0, K=8,
                            seed=seed + 800, warmup=WARMUP, blind=True, cand_mode="nosim", churn=dict(FROZEN2, lam=0.5))
        kw["interval"] = adj.next_interval
        t0 = time.time()
        sim = Sim(sc, X0.copy(), adjuster=adj, seed=seed + 400, **kw)
        sim.trace_snap = True
        r = sim.run()
        sim.check_invariants()
        stored = json.loads((W1 / f"{tg}.ours.json").read_text())["result"]["event_hash"]
        OUT.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(dict(capacity_model="CAP-W1", case=tg, p99=r["p99_makespan"], hash_matches_stored=(r["event_hash"] == stored),
                                       wall_s=time.time() - t0, tasks=sim.trace["tasks"], snap=sim.trace.get("snap", []))))
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


def frac(xs, cond):
    return sum(1 for s in xs if cond(s)) / max(len(xs), 1)


def report():
    na = nb = done = 0
    for tg in CASES:
        p = OUT / f"{tg}.json"
        if not p.exists():
            print(tg, "missing")
            continue
        d = json.loads(p.read_text())
        if not d["hash_matches_stored"]:
            print(tg, "EVENT HASH DIFFERS from the stored run -> not used")
            continue
        ex = {(t[0], int(t[2])): t[4] for t in d["tasks"]}
        S = [s for s in d["snap"] if (s[0], int(s[1])) in ex]          # (rid, task, plan, t_bind, b0, t_enq, b1, g1, b2, g2, b4, g4)
        n = len(S)

        def e(s):
            return ex[(s[0], int(s[1]))]
        W2 = [s for s in S if s[8] is not None]
        W4 = [s for s in S if s[10] is not None]
        ch1, ch2, ch4 = frac(S, lambda s: s[6] != s[4]), frac(W2, lambda s: s[8] != s[4]), frac(W4, lambda s: s[10] != s[4])
        mat2 = frac(W2, lambda s: s[9] >= 1.0)
        g2 = np.array([min(s[9], 1e3) for s in W2]) if W2 else np.zeros(1)
        ag0, ag1, ag2 = frac(W2, lambda s: e(s) == s[4]), frac(W2, lambda s: e(s) == s[6]), frac(W2, lambda s: e(s) == s[8])
        ag0_4, ag4 = frac(W4, lambda s: e(s) == s[4]), frac(W4, lambda s: e(s) == s[10])
        done += 1
        na += mat2 >= 0.30
        nb += (ag2 - ag0) >= 0.10
        print(f"{tg}: n={n} sampled non-root tasks; started before +2 s {1 - len(W2) / max(n, 1):.0%}, before +4 s {1 - len(W4) / max(n, 1):.0%}"
              f"\n          best node differs from the bind-time best: at enqueue {ch1:.0%}, at +2 s {ch2:.0%}, at +4 s {ch4:.0%} (of tasks still waiting)"
              f"\n          bind-time choice >= 1 s worse than the best at +2 s: {mat2:.0%} (median regret {np.median(g2):.2f} s)"
              f"\n          tasks waiting at +2 s: exec = best at bind {ag0:.0%}, at enqueue {ag1:.0%}, at +2 s {ag2:.0%}"
              f"  | waiting at +4 s: bind {ag0_4:.0%}, +4 s {ag4:.0%}")
    if done == len(CASES):
        verdict = ("measured: the best node moves after binding and the final node follows the later state" if (na >= 4 and nb >= 4)
                   else "not shown" if (na <= 2 and nb <= 2) else "mixed")
        print(f"\nA (material change at +2 s >= 30%) in {na}/6 cases; B (exec agreement +2 s minus bind >= 10 pts) in {nb}/6 -> {verdict}")


if __name__ == "__main__":
    {"run": lambda: run(int(sys.argv[2]) if len(sys.argv) > 2 else 3), "report": report,
     "smoke": lambda: print(run_job("F1_r0.85_s1", 150.0))}[sys.argv[1]]()
