"""Replay diagnostic (3 Nov 2026): would a finish-time planner (greedy EFT at planning time) have chosen the nodes the mover later moved tasks to?
CAP-W1, controller "ours" (the capw1_light run), six step-1 cases. Trace only: Sim._plan also computes greedy_eft and logs it; dynamics unchanged
(event hash must equal the stored run). Reading fixed in knowledge/synthesis/workflow-aware-decision-rules.md ("Replay diagnostic").
  python replay_diag.py run [workers] | report
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
OUT = ROOT / "results" / "replay_diag"
W1 = ROOT / "results" / "capW1_light"
CASES = [f"{f}_r{r}_s1" for f in ("F1", "F2") for r in (0.5, 0.7, 0.85)]
DURATION, WARMUP = 900.0, 60.0


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
        kw.update(warmup=WARMUP, duration=DURATION, retry_min_interval=1.0, retry_max_attempts=10, trace=True)
        kw["queue_priority"] = QueuePriority("full", aging=2.0)
        adj = O3SimAdjuster(make_adjuster("B_STAR", A, seed=seed + 300), MOVE_PERIOD_S[fam], epoch=60.0, horizon=30.0, K=8,
                            seed=seed + 800, warmup=WARMUP, blind=True, cand_mode="nosim", churn=dict(FROZEN2, lam=0.5))
        kw["interval"] = adj.next_interval
        t0 = time.time()
        sim = Sim(sc, X0.copy(), adjuster=adj, seed=seed + 400, **kw)
        sim.trace_cf = True
        r = sim.run()
        sim.check_invariants()
        stored = json.loads((W1 / f"{tg}.ours.json").read_text())["result"]["event_hash"]
        holders = [int(np.count_nonzero(sim.cnt[f])) for f in range(sim.cnt.shape[0])]
        OUT.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(dict(case=tg, p99=r["p99_makespan"], hash_matches_stored=(r["event_hash"] == stored), wall_s=time.time() - t0,
                                       tasks=sim.trace["tasks"], cf=sim.trace["cf"], holders=holders)))
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
    rows = []
    for tg in CASES:
        p = OUT / f"{tg}.json"
        if not p.exists():
            print(tg, "missing")
            continue
        d = json.loads(p.read_text())
        if not d["hash_matches_stored"]:
            print(tg, "EVENT HASH DIFFERS from the stored run -> not used")
            continue
        sc = pickle.load(open(W1 / f"{tg}.sc.pkl", "rb"))["sc"]
        roots = {w.id: set(w.roots) for w in sc.workflows}
        cf = {c[0]: c[1] for c in d["cf"]}
        n = a_plan = a_cf = off = off_cf = same = 0
        chance = 0.0
        for t in d["tasks"]:                                   # (rid, wid, task, plan, exec, ...)
            c = cf.get(t[0])
            if c is None or int(t[2]) in roots[int(t[1])]:
                continue
            ccf = c[int(t[2])]
            n += 1
            a_plan += t[3] == t[4]
            a_cf += ccf == t[4]
            same += ccf == t[3]
            if t[3] != t[4]:
                off += 1
                off_cf += ccf == t[4]
        rows.append((tg, a_cf / n - a_plan / n))
        print(f"{tg}: n={n}  exec=plan {a_plan/n:.1%}  exec=cf {a_cf/n:.1%} (diff {100*(a_cf-a_plan)/n:+.1f} pts)  cf=plan {same/n:.1%}  "
              f"off-plan tasks with exec=cf {off_cf/max(off,1):.1%}")
    if len(rows) == len(CASES):
        k = sum(r[1] >= 0.10 for r in rows)
        j = sum(r[1] < 0.10 for r in rows)
        print(f"\ndiff >= 10 pts in {k}/6 cases, < 10 pts in {j}/6 -> " + ("premise supported" if k >= 4 else ("premise not supported: drop the repair-priced term" if j >= 3 else "mixed")))


if __name__ == "__main__":
    {"run": lambda: run(int(sys.argv[2]) if len(sys.argv) > 2 else 3), "report": report}[sys.argv[1]]()
