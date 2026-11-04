"""Step 1 of the dispatcher work (3 Nov 2026): do arrival-time plans go stale, and what do the repairs cost?  CAP-W1, controller "ours"
(the capw1_light "ours" run), with the simulator's trace on. Six cases: F1 and F2 x 50/70/85% load, seed 1.
Trace on changes nothing in the dynamics; the event hash of every re-run must equal the stored capW1_light run, else the case is not used.

Readings fixed before any run (knowledge/synthesis/workflow-aware-decision-rules.md, "Dispatcher replacement, step 1"):
 STALE   plan age of a task = time from its request's arrival to the task's first enqueue. Over non-root tasks in the window, the share
         that runs on a node other than its planned node, in the oldest age quartile divided by the same share in the youngest.
         Late binding is worth building only if the ratio is >= 1.5 in at least 4 of 6 cases. Also reported: the same ratio with age
         split at the median WITHIN each (workflow, task) cell, which removes depth (a deep task is both older and further from its plan).
 REPAIR  transfer seconds of all request moves of the tail requests (sojourn >= the case's P99), divided by the tail's mean sojourn, and the
         part made within one move period (4 s) of the task's first enqueue. Upper bound (not every move is on the critical path).
         Below 2% in at least 4 of 6 cases: the repairs cost too little for late binding to recover.
  python stale_plan_probe.py run [workers] | report | smoke
"""
import collections
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
OUT = ROOT / "results" / "stale_plan_probe"
W1 = ROOT / "results" / "capW1_light"
CASES = [f"{f}_r{r}_s1" for f in ("F1", "F2") for r in (0.5, 0.7, 0.85)]
DURATION, WARMUP, PERIOD = 900.0, 60.0, 4.0


def run_job(args):
    tg, duration = args
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
        r = sim.run()
        sim.check_invariants()
        stored = json.loads((W1 / f"{tg}.ours.json").read_text())["result"]["event_hash"] if duration == DURATION else None
        OUT.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(dict(case=tg, duration=duration, p99=r["p99_makespan"], event_hash=r["event_hash"],
                                       hash_matches_stored=(r["event_hash"] == stored) if stored else None, wall_s=time.time() - t0,
                                       tasks=sim.trace["tasks"], reqs=sim.trace["reqs"], moves=sim.trace.get("moves", []))))
    except Exception:
        import traceback
        OUT.mkdir(parents=True, exist_ok=True)
        out.with_suffix(".err").write_text(traceback.format_exc())
        return str(out) + " FAILED"
    return str(out)


def run(workers):
    todo = [(c, DURATION) for c in CASES if not (OUT / f"{c}.json").exists()]
    print(len(todo), "runs", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        for r in ex.map(run_job, sorted(todo, key=lambda j: -float(j[0].split("_r")[1].split("_")[0]))):
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
        arr = {q[0]: q[2] for q in d["reqs"]}
        soj = {q[0]: q[3] - q[2] for q in d["reqs"]}
        rows_t = [t for t in d["tasks"] if int(t[2]) not in roots[int(t[1])]]            # non-root tasks only
        wid = np.array([t[1] for t in rows_t], dtype=int)
        tk = np.array([t[2] for t in rows_t], dtype=int)
        disp = np.array([t[3] != t[4] for t in rows_t], dtype=float)
        age = np.array([t[5] - arr[t[0]] for t in rows_t])
        mv = np.array([t[8] for t in rows_t], dtype=float)
        q = np.quantile(age, [0.25, 0.75])
        lo, hi = age <= q[0], age >= q[1]
        r_disp = disp[hi].mean() / max(disp[lo].mean(), 1e-9)
        r_mv = mv[hi].mean() / max(mv[lo].mean(), 1e-9)
        cells = collections.defaultdict(list)
        for w, t, a, x in zip(wid, tk, age, disp):
            cells[(w, t)].append((a, x))
        up = dn = n = 0.0
        for v in cells.values():
            if len(v) < 40:
                continue
            v.sort()
            h = len(v) // 2
            dn += sum(x for _, x in v[:h])
            up += sum(x for _, x in v[-h:])
            n += h
        r_ctl = (up / n) / max(dn / n, 1e-9) if n else float("nan")
        ss = np.array(list(soj.values()))
        thr = np.quantile(ss, 0.99)
        tail = {k for k, v in soj.items() if v >= thr}
        tail_mean = np.mean([soj[k] for k in tail])
        mv_tail = [m for m in d["moves"] if int(m[0]) in tail]
        c_all = sum(m[3] for m in mv_tail) / len(tail) / tail_mean
        c_fast = sum(m[3] for m in mv_tail if m[4] is not None and m[2] - m[4] <= PERIOD) / len(tail) / tail_mean
        rows.append((tg, r_disp, r_ctl, c_all))
        print(f"{tg}: P99 {d['p99']:.0f}  non-root tasks run off-plan {disp.mean():.1%}  oldest/youngest quartile: off-plan x{r_disp:.2f}, "
              f"moves/task x{r_mv:.2f}, depth-controlled x{r_ctl:.2f}  |  tail moves' transfer / tail sojourn: all {c_all:.1%}, "
              f"within {PERIOD:.0f}s of enqueue {c_fast:.1%}")
    if len(rows) == len(CASES):
        n1 = sum(r[1] >= 1.5 for r in rows)
        n2 = sum(r[2] >= 1.5 for r in rows)
        n3 = sum(r[3] < 0.02 for r in rows)
        print(f"\nSTALE: ratio >= 1.5 in {n1}/6 cases (depth-controlled {n2}/6) -> {'build late binding' if n1 >= 4 else 'not shown'}")
        print(f"REPAIR: tail move cost < 2% of tail sojourn in {n3}/6 cases -> {'too cheap to recover' if n3 >= 4 else 'a cost worth recovering'}")


if __name__ == "__main__":
    {"run": lambda: run(int(sys.argv[2]) if len(sys.argv) > 2 else 2), "report": report,
     "smoke": lambda: print(run_job((CASES[0], 120.0)))}[sys.argv[1]]()
