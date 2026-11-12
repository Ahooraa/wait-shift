"""Diagnostic ORACLE on the paper's own development cases (CAP-W1, F1/F2 x rho 0.5/0.7/0.85 x seeds 1-3): FROZEN-4 (fill1 as stored) with the node of every single-parent task chosen when
the task is ready, against the stored fill1 run. Same configuration as capw1_rows.run_job; only the Late subclass differs. Simulator only; not a proposed controller.
  python late_capw1.py run [workers]   |   report
"""
import json, pickle, sys, time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "output" / "data-analysis"))
import os
IMPL = os.environ.get("F5_IMPL") == "1"                                     # 1: the implemented switch (Sim late_bind) instead of the diagnostic subclass
OUT = ROOT / "results" / ("f5_capw1" if IMPL else "late_capw1")
W1 = ROOT / "results" / "capW1_light"
CASES = [f"{f}_r{r}_s{s}" for f in ("F1", "F2") for r in ("0.5", "0.7", "0.85") for s in (1, 2, 3)]
DURATION, WARMUP = 900.0, 60.0


def one(tg):
    out = OUT / f"{tg}.json"
    if out.exists():
        return tg
    import yaml
    from dfps import dispatchers as D
    from dfps.dispatch_priority import QueuePriority
    from dfps.o3s import O3SimAdjuster
    from dfps.variants import make_adjuster, sim_kwargs
    from frozen2 import FROZEN4, MOVE_PERIOD_S
    from testbed.diag.late_class import Late
    A = yaml.safe_load((ROOT / "config" / "assumptions.yaml").read_text(encoding="utf-8"))
    P = pickle.load(open(W1 / f"{tg}.sc.pkl", "rb")); sc, X0 = P["sc"], P["X0"]
    seed, fam = int(tg.split("_s")[1]), tg.split("_r")[0]
    kw = sim_kwargs("B_STAR", A); kw.update(warmup=WARMUP, duration=DURATION, retry_min_interval=1.0, retry_max_attempts=10)
    kw["dispatcher"] = D.DISPATCHERS["transfer_only"]; kw["queue_priority"] = QueuePriority("full", aging=2.0)
    adj = O3SimAdjuster(make_adjuster("B_STAR", A, seed=seed + 300), MOVE_PERIOD_S[fam], epoch=60.0, horizon=30.0, K=8, seed=seed + 800, warmup=WARMUP, blind=True,
                        cand_mode="nosim", churn=dict(FROZEN4, lam=0.5))
    kw["interval"] = adj.next_interval
    t0 = time.time()
    if IMPL:
        from dfps.sim import Sim
        sim = Sim(sc, X0.copy(), adjuster=adj, seed=seed + 400, late_bind=True, **kw)
    else:
        sim = Late(sc, X0.copy(), adjuster=adj, seed=seed + 400, **kw)
    r = sim.run()
    OUT.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"case": tg, "wall_s": time.time() - t0, **{k: r.get(k) for k in ("p50_makespan", "p99_makespan", "cold_starts", "n_moved", "n_completed", "n_unfinished")}}, default=float))
    return tg


def report():
    rows = []
    for tg in CASES:
        f = OUT / f"{tg}.json"
        if not f.exists():
            continue
        a = json.loads(f.read_text()); b = json.loads((ROOT / "results" / "capW1_rows" / f"{tg}.fill1.json").read_text())["result"]
        rows.append((tg, b["p99_makespan"], a["p99_makespan"], b["p50_makespan"], a["p50_makespan"], b["n_moved"], a["n_moved"], b["cold_starts"], a["cold_starts"]))
        print(f"{tg:12} P99 {b['p99_makespan']:8.1f} -> {a['p99_makespan']:8.1f} ({a['p99_makespan']/b['p99_makespan']:.3f})  P50 {b['p50_makespan']:7.1f} -> {a['p50_makespan']:7.1f} ({a['p50_makespan']/b['p50_makespan']:.3f})  moves {b['n_moved']} -> {a['n_moved']}  cold {b['cold_starts']} -> {a['cold_starts']}")
    if rows:
        lr = np.log([r[2] / r[1] for r in rows]); lp = np.log([r[4] / r[3] for r in rows])
        rng = np.random.default_rng(0); bs = [rng.choice(lr, len(lr)).mean() for _ in range(4000)]
        print(f"\n{len(rows)} cases: geometric-mean P99 ratio (late / stored fill1) {np.exp(lr.mean()):.3f}  95% bootstrap CI [{np.exp(np.percentile(bs, 2.5)):.3f}, {np.exp(np.percentile(bs, 97.5)):.3f}]; better in {int((lr < 0).sum())}; P50 ratio {np.exp(lp.mean()):.3f}")


if __name__ == "__main__":
    if sys.argv[1] == "run":
        w = int(sys.argv[2]) if len(sys.argv) > 2 else 6
        with ProcessPoolExecutor(w) as ex:
            for tg in ex.map(one, CASES):
                print("done", tg, flush=True)
    else:
        report()
