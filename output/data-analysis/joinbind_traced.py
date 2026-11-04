"""Traced join binding vs traced arrival binding (3 Nov 2026): did join binding cut the early repair cost on joins?
Six step-1 cases, CAP-W1, greedy EFT dispatcher, "ours" controller, trace on, with join_bind False (arm "arr") and True (arm "jb").
Each arm's event hash must equal the stored untraced run (results/capW1_ccag for arr, results/capW1_joinbind for jb), else the case is not used.
Reading fixed in knowledge/synthesis/workflow-aware-decision-rules.md ("Traced join binding").
  python joinbind_traced.py run [workers] | report
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
OUT = ROOT / "results" / "joinbind_traced"
W1 = ROOT / "results" / "capW1_light"
STORED = {"arr": ROOT / "results" / "capW1_ccag", "jb": ROOT / "results" / "capW1_joinbind"}
CASES = [f"{f}_r{r}_s1" for f in ("F1", "F2") for r in (0.5, 0.7, 0.85)]
DURATION, WARMUP, PERIOD = 900.0, 60.0, 4.0
KINDS = ("root", "single", "join")


def run_job(args):
    tg, arm = args
    out = OUT / f"{tg}.{arm}.json"
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
        kw.update(warmup=WARMUP, duration=DURATION, retry_min_interval=1.0, retry_max_attempts=10, dispatcher=D.greedy_eft,
                  join_bind=(arm == "jb"), trace=True)
        kw["queue_priority"] = QueuePriority("full", aging=2.0)
        adj = O3SimAdjuster(make_adjuster("B_STAR", A, seed=seed + 300), MOVE_PERIOD_S[fam], epoch=60.0, horizon=30.0, K=8,
                            seed=seed + 800, warmup=WARMUP, blind=True, cand_mode="nosim", churn=dict(FROZEN2, lam=0.5))
        kw["interval"] = adj.next_interval
        t0 = time.time()
        sim = Sim(sc, X0.copy(), adjuster=adj, seed=seed + 400, **kw)
        r = sim.run()
        sim.check_invariants()
        stored = json.loads((STORED[arm] / f"{tg}.json").read_text())["result"]["event_hash"]
        OUT.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(dict(case=tg, arm=arm, p99=r["p99_makespan"], hash_matches_stored=(r["event_hash"] == stored),
                                       wall_s=time.time() - t0, tasks=sim.trace["tasks"], reqs=sim.trace["reqs"], moves=sim.trace.get("moves", []))))
    except Exception:
        import traceback
        OUT.mkdir(parents=True, exist_ok=True)
        out.with_suffix(".err").write_text(traceback.format_exc())
        return str(out) + " FAILED"
    return str(out)


def run(workers):
    jobs = [(c, a) for c in CASES for a in ("arr", "jb") if not (OUT / f"{c}.{a}.json").exists()]
    jobs.sort(key=lambda j: -float(j[0].split("_r")[1].split("_")[0]))
    print(len(jobs), "runs", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        for r in ex.map(run_job, jobs):
            print("done", r, flush=True)


def summarize(tg, arm):
    d = json.loads((OUT / f"{tg}.{arm}.json").read_text())
    if not d["hash_matches_stored"]:
        return None
    sc = pickle.load(open(W1 / f"{tg}.sc.pkl", "rb"))["sc"]
    kind_of = {w.id: ["root" if not w.parents[t] else ("single" if len(w.parents[t]) == 1 else "join") for t in range(w.n)] for w in sc.workflows}
    soj = {int(q[0]): q[3] - q[2] for q in d["reqs"]}
    wid = {int(q[0]): int(q[1]) for q in d["reqs"]}
    thr = np.quantile(list(soj.values()), 0.99)
    tail = {k for k, v in soj.items() if v >= thr}
    tail_mean = float(np.mean([soj[k] for k in tail]))
    cost = {(k, w): 0.0 for k in KINDS for w in ("early", "late")}
    n_moves = 0
    for rid, task, now, delay, t_first in d["moves"]:
        rid = int(rid)
        n_moves += 1
        if rid in tail:
            cost[(kind_of[wid[rid]][int(task)], "early" if (t_first is not None and now - t_first <= PERIOD) else "late")] += delay
    pts = lambda x: 100 * x / len(tail) / tail_mean
    return dict(p99=d["p99"], moves_per_req=n_moves / len(soj), tail_total=pts(sum(cost.values())), early_all=pts(sum(cost[(k, "early")] for k in KINDS)),
                early_join=pts(cost[("join", "early")]), early_single=pts(cost[("single", "early")]), early_root=pts(cost[("root", "early")]),
                late_join=pts(cost[("join", "late")]))


def report():
    fall = n = 0
    for tg in CASES:
        if not all((OUT / f"{tg}.{a}.json").exists() for a in ("arr", "jb")):
            print(tg, "missing")
            continue
        a, b = summarize(tg, "arr"), summarize(tg, "jb")
        if a is None or b is None:
            print(tg, "EVENT HASH DIFFERS from the stored run -> not used")
            continue
        n += 1
        rel = b["early_join"] / max(a["early_join"], 1e-9) - 1
        fall += rel <= -0.25
        print(f"{tg}: early JOIN move cost (pts of tail sojourn) {a['early_join']:.1f} -> {b['early_join']:.1f} ({rel:+.0%})  | early single {a['early_single']:.1f} -> {b['early_single']:.1f}"
              f"  early root {a['early_root']:.1f} -> {b['early_root']:.1f}  late join {a['late_join']:.1f} -> {b['late_join']:.1f}  | tail total {a['tail_total']:.1f} -> {b['tail_total']:.1f}"
              f"  | moves/req(window) {a['moves_per_req']:.2f} -> {b['moves_per_req']:.2f}  P99 {a['p99']:.0f} -> {b['p99']:.0f}")
    if n == len(CASES):
        print(f"\nearly join move cost down by >= 25% in {fall}/6 cases -> " + ("join binding removes early join repairs" if fall >= 4 else "early join repairs are not removed" if fall <= 2 else "mixed"))


if __name__ == "__main__":
    {"run": lambda: run(int(sys.argv[2]) if len(sys.argv) > 2 else 3), "report": report}[sys.argv[1]]()
