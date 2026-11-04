"""Objective-aligned routers on the 18 CAP-W1 development cases (4 Nov 2026, user request): can a router that leaves the wait to the mover give
a lower cost at the same P99? Arm from env ALIGN_ARM: transfer_only (input transfer only, ties by FST) or mover_aet (input transfer + the mover's
live service estimate). Controller "ours" (FROZEN-2, lam 0.5, criticality queue order); only the dispatcher differs. Results:
results/capW1_align_{arm}/{tag}.json. Reading fixed in knowledge/synthesis/workflow-aware-decision-rules.md ("Objective-aligned routers").
  performance  P99 vs the matcher (stored capW1_light ours): NOT WORSE if the CI upper end of the geometric-mean ratio <= 1.02 and the
               cold-start ratio <= 1.2 (the usual rule).
  cost         vs Graph-Aware beta 4 (results/capW1_ga_b4): moves per completed request and relocated MB per completed request,
               geometric mean of the case ratios with a bootstrap 95% CI; "lower cost" if the CI upper end of the moves ratio <= 0.90 and
               the relocated-MB ratio's point estimate <= 1.00. Plan time reported.
  python capw1_align.py run [workers] | report      (ALIGN_ARM=transfer_only|mover_aet)
"""
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
ARM = os.environ.get("ALIGN_ARM", "transfer_only")
assert ARM in ("transfer_only", "mover_aet"), ARM
OUT = ROOT / "results" / f"capW1_align_{ARM}"
W1 = ROOT / "results" / "capW1_light"
GA = ROOT / "results" / "capW1_ga_b4"
DURATION, WARMUP = 900.0, 60.0


def cases():
    return [f"{f}_r{r}_s{s}" for f in ("F1", "F2") for r in (0.5, 0.7, 0.85) for s in (1, 2, 3)]


def run_job(tg):
    out = OUT / f"{tg}.json"
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
        kw.update(warmup=WARMUP, duration=DURATION, retry_min_interval=1.0, retry_max_attempts=10, dispatcher=D.DISPATCHERS[ARM])
        kw["queue_priority"] = QueuePriority("full", aging=2.0)
        adj = O3SimAdjuster(make_adjuster("B_STAR", A, seed=seed + 300), MOVE_PERIOD_S[fam], epoch=60.0, horizon=30.0, K=8,
                            seed=seed + 800, warmup=WARMUP, blind=True, cand_mode="nosim", churn=dict(FROZEN2, lam=0.5))
        kw["interval"] = adj.next_interval
        t0 = time.time()
        sim = Sim(sc, X0.copy(), adjuster=adj, seed=seed + 400, **kw)
        r = sim.run()
        sim.check_invariants()
        r["wall_s"] = time.time() - t0
        OUT.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(dict(capacity_model="CAP-W1", case=tg, ctrl=f"ours_{ARM}", result=r)))
    except Exception:
        import traceback
        OUT.mkdir(parents=True, exist_ok=True)
        out.with_suffix(".err").write_text(traceback.format_exc())
        return str(out) + " FAILED"
    return str(out)


def run(workers):
    todo = [c for c in cases() if not (OUT / f"{c}.json").exists()]
    todo.sort(key=lambda c: -float(c.split("_r")[1].split("_")[0]))
    print(len(todo), "runs", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        for r in ex.map(run_job, todo):
            print("done", r, flush=True)


def gm_ci(x, seed=0):
    x = np.log(np.asarray(x, float))
    rng = np.random.default_rng(seed)
    bs = [x[rng.integers(0, len(x), len(x))].mean() for _ in range(10000)]
    lo, hi = np.exp(np.percentile(bs, [2.5, 97.5]))
    return float(np.exp(x.mean())), float(lo), float(hi)


def report():
    rows = []
    for tg in cases():
        a, m, g = OUT / f"{tg}.json", W1 / f"{tg}.ours.json", GA / f"{tg}.json"
        if a.exists() and m.exists() and g.exists():
            rows.append((tg, *(json.loads(p.read_text())["result"] for p in (m, g, a))))
    print(f"arm {ARM}: {len(rows)} of {len(cases())} cases done")

    def mv(x):
        return x["n_moved"] / x["n_completed"]

    def mb(x):
        return x["mb_relocated"] / x["n_completed"]
    for tg, m, g, a in rows:
        print(f"{tg:12s} P99 matcher {m['p99_makespan']:6.1f}  GA {g['p99_makespan']:6.1f}  {ARM} {a['p99_makespan']:6.1f} ({(a['p99_makespan']/m['p99_makespan']-1)*100:+.0f}% vs matcher)"
              f"  | moves/req {mv(m):.2f} / {mv(g):.2f} / {mv(a):.2f}  MB relocated/req {mb(m):.1f} / {mb(g):.1f} / {mb(a):.1f}"
              f"  plan_ms {m['plan_ms_mean']:.0f} / {g['plan_ms_mean']:.1f} / {a['plan_ms_mean']:.1f}  cold {m['cold_starts']}/{a['cold_starts']}")
    if len(rows) >= 6:
        p, lo, hi = gm_ci([a["p99_makespan"] / m["p99_makespan"] for _, m, g, a in rows])
        pg = gm_ci([a["p99_makespan"] / g["p99_makespan"] for _, m, g, a in rows])
        cold = np.mean([a["cold_starts"] / m["cold_starts"] for _, m, g, a in rows])
        c_mv = gm_ci([mv(a) / mv(g) for _, m, g, a in rows])
        c_mb = gm_ci([mb(a) / max(mb(g), 1e-9) for _, m, g, a in rows])
        wins = sum(a["p99_makespan"] < m["p99_makespan"] for _, m, g, a in rows)
        print(f"\nP99 {ARM} / matcher {p:.3f} [{lo:.3f}, {hi:.3f}], better in {wins}/{len(rows)}, cold-start ratio {cold:.2f};"
              f" P99 {ARM} / Graph-Aware {pg[0]:.3f} [{pg[1]:.3f}, {pg[2]:.3f}]")
        print(f"cost vs Graph-Aware: moves/req ratio {c_mv[0]:.3f} [{c_mv[1]:.3f}, {c_mv[2]:.3f}], relocated MB/req ratio {c_mb[0]:.3f} [{c_mb[1]:.3f}, {c_mb[2]:.3f}]")
        perf = hi <= 1.02 and cold <= 1.2
        cost = c_mv[2] <= 0.90 and c_mb[0] <= 1.00
        print("performance:", "NOT WORSE" if perf else "not shown to be non-inferior", "| cost:", "LOWER than Graph-Aware" if cost else "not lower",
              "->", "better cost at the same performance" if (perf and cost) else "not shown",
              "" if len(rows) == len(cases()) else f"(partial: {len(rows)} cases, not the pre-registered reading)")


if __name__ == "__main__":
    {"run": lambda: run(int(sys.argv[2]) if len(sys.argv) > 2 else 3), "report": report}[sys.argv[1]]()
