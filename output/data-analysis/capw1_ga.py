"""Graph-Aware (Liang et al. 2026) as the dispatcher of our controller, on the 18 CAP-W1 development cases (4 Nov 2026, user request). beta from env GA_BETA
(default 4.0 = the value frozen on 26 Oct by the pre-registered rule; 1.0 = inside the paper's own range 0.2-1.1); results/capW1_ga_b{beta}/. Template: capw1_ccag.py.
Original docstring: Greedy EFT as the dispatcher of our controller, on the 18 CAP-W1 development cases (3 Nov 2026, user request).

Same scenario, start layout, arrivals, seeds and controller as the stored capW1_light "ours" run (re-layout every 60 s, request moves every
4 s, criticality queue order, lam = 0.5); ONLY the dispatcher differs: dfps.dispatchers.greedy_eft (per task, in topological order: input
transfer time + FST, no tuned constant) instead of DFPS's graph pattern matching. Results: results/capW1_ccag/{tag}.json.

Reading fixed before any run (knowledge/synthesis/workflow-aware-decision-rules.md, "Greedy EFT on CAP-W1"):
  primary   per-case ratio P99(greedy EFT) / P99(matcher); geometric mean with a bootstrap 95% CI over the 18 log ratios (cases are the unit).
  NOT WORSE accepted as a replacement if the upper end of the CI is <= 1.02 AND cold starts are not more than 20% higher (mean of case ratios).
  BETTER    claimed only if the upper end of the CI is <= 0.97 (the pre-registered 3% threshold of this project).
  Also reported: wins out of 18, P50/P95, moves per request, cold starts, mean plan time.
  python capw1_ccag.py run [workers] | report
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
import placement_extensions as pe  # noqa: E402

BETA = float(os.environ.get("GA_BETA", "4.0"))
OUT = ROOT / "results" / f"capW1_ga_b{BETA:g}"
W1 = ROOT / "results" / "capW1_light"
DURATION, WARMUP = 900.0, 60.0


def cases():
    return [pe.tag(f, r, s) for f in pe.FAMS for r in pe.RHOS for s in pe.SEEDS]


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
        kw.update(warmup=WARMUP, duration=DURATION, retry_min_interval=1.0, retry_max_attempts=10, dispatcher=D.GraphAware(alpha=1.0, beta=BETA))
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
        out.write_text(json.dumps(dict(capacity_model="CAP-W1", case=tg, ctrl=f"ours_graph_aware_b{BETA:g}", result=r)))
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


def report():
    rows = []
    for tg in cases():
        a, b = OUT / f"{tg}.json", W1 / f"{tg}.ours.json"
        if a.exists() and b.exists():
            rows.append((tg, json.loads(b.read_text())["result"], json.loads(a.read_text())["result"]))
    print(f"{len(rows)} of {len(cases())} cases done")
    lr = []
    for tg, m, g in rows:
        lr.append(np.log(g["p99_makespan"] / m["p99_makespan"]))
        print(f"{tg:12s} matcher {m['p99_makespan']:7.1f}  Graph-Aware {g['p99_makespan']:7.1f} ({(g['p99_makespan']/m['p99_makespan']-1)*100:+.0f}%)"
              f"  cold {m['cold_starts']}/{g['cold_starts']}  moves/req {m['n_moved']/m['n_completed']:.2f}/{g['n_moved']/g['n_completed']:.2f}"
              f"  P50 {m['p50_makespan']:.0f}/{g['p50_makespan']:.0f}  P95 {m['p95_makespan']:.0f}/{g['p95_makespan']:.0f}  plan_ms {m['plan_ms_mean']:.0f}/{g['plan_ms_mean']:.1f}")
    if len(rows) >= 6:
        lr = np.array(lr)
        rng = np.random.default_rng(0)
        bs = [lr[rng.integers(0, len(lr), len(lr))].mean() for _ in range(10000)]
        lo, hi = np.exp(np.percentile(bs, [2.5, 97.5]))
        cold = np.mean([g["cold_starts"] / m["cold_starts"] for _, m, g in rows])
        wins = sum(l < 0 for l in lr)
        print(f"\ngeometric-mean ratio Graph-Aware / matcher {np.exp(lr.mean()):.3f}, 95% CI [{lo:.3f}, {hi:.3f}]; better in {wins}/{len(lr)}; cold-start ratio {cold:.2f}")
        verdict = "BETTER (CI upper <= 0.97)" if hi <= 0.97 else ("NOT WORSE (CI upper <= 1.02)" if hi <= 1.02 else "not shown to be non-inferior")
        print("verdict:", verdict + ("" if cold <= 1.2 else "; cold starts more than 20% higher -> fails the cold-start condition"),
              "" if len(rows) == len(cases()) else f"(partial: {len(rows)} cases, not the pre-registered reading)")


if __name__ == "__main__":
    {"run": lambda: run(int(sys.argv[2]) if len(sys.argv) > 2 else 3), "report": report}[sys.argv[1]]()
