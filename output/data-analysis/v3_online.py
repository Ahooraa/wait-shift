"""V3 follow-up: gain-ordered move selection online (CAP-W1; pre-registered 4 Nov 2026 in
knowledge/synthesis/workflow-aware-decision-rules.md, "V3 follow-up"). The last mover experiment.
12 cases F1/F2 x rho 0.7/0.85 x seeds 1-3; FROZEN-2 + transfer_only dispatcher, mover pass in gain order (churn pass_order="gain")
versus the current mover with the same dispatcher (stored results/capW1_align_transfer_only).
  success = P99 gm ratio CI upper <= 1.02 AND moves/req gm ratio CI upper <= 0.95 (both).
  python v3_online.py run [workers] | report
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
OUT = ROOT / "results" / "v3_online"
W1 = ROOT / "results" / "capW1_light"
REF = ROOT / "results" / "capW1_align_transfer_only"
DURATION, WARMUP = 900.0, 60.0


def cases():
    return [f"{f}_r{r}_s{s}" for f in ("F1", "F2") for r in (0.7, 0.85) for s in (1, 2, 3)]


def run_job(tg):
    out = OUT / f"{tg}.json"
    if out.exists():
        return str(out)
    OUT.mkdir(parents=True, exist_ok=True)
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
        kw.update(warmup=WARMUP, duration=DURATION, retry_min_interval=1.0, retry_max_attempts=10, dispatcher=D.DISPATCHERS["transfer_only"])
        kw["queue_priority"] = QueuePriority("full", aging=2.0)
        adj = O3SimAdjuster(make_adjuster("B_STAR", A, seed=seed + 300), MOVE_PERIOD_S[fam], epoch=60.0, horizon=30.0, K=8,
                            seed=seed + 800, warmup=WARMUP, blind=True, cand_mode="nosim", churn=dict(FROZEN2, lam=0.5, pass_order="gain"))
        kw["interval"] = adj.next_interval
        t0 = time.time()
        sim = Sim(sc, X0.copy(), adjuster=adj, seed=seed + 400, **kw)
        r = sim.run()
        sim.check_invariants()
        r["wall_s"] = time.time() - t0
        out.write_text(json.dumps(dict(capacity_model="CAP-W1", case=tg, ctrl="ours_transfer_only_gainorder", pass_order="gain", result=r)))
    except Exception:
        import traceback
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
        a, b = OUT / f"{tg}.json", REF / f"{tg}.json"
        if a.exists() and b.exists():
            rows.append((tg, json.loads(b.read_text())["result"], json.loads(a.read_text())["result"]))
    print(f"{len(rows)} of {len(cases())} cases done")
    mv = lambda x: x["n_moved"] / x["n_completed"]
    mb = lambda x: x["mb_relocated"] / x["n_completed"]
    for tg, b, a in rows:
        print(f"{tg:12s} P99 {b['p99_makespan']:6.1f} -> {a['p99_makespan']:6.1f} ({(a['p99_makespan'] / b['p99_makespan'] - 1) * 100:+5.1f}%)"
              f"  moves/req {mv(b):.2f} -> {mv(a):.2f} ({(mv(a) / mv(b) - 1) * 100:+5.1f}%)  MB/req {mb(b):.1f} -> {mb(a):.1f}"
              f"  cold {b['cold_starts']} -> {a['cold_starts']}")
    if len(rows) < 6:
        return
    p = gm_ci([a["p99_makespan"] / b["p99_makespan"] for _, b, a in rows])
    m = gm_ci([mv(a) / mv(b) for _, b, a in rows])
    r = gm_ci([mb(a) / max(mb(b), 1e-9) for _, b, a in rows])
    cold = float(np.mean([a["cold_starts"] / max(b["cold_starts"], 1) for _, b, a in rows]))
    print(f"\nP99 gain-order / current     {p[0]:.3f} [{p[1]:.3f}, {p[2]:.3f}], better in {sum(a['p99_makespan'] < b['p99_makespan'] for _, b, a in rows)}/{len(rows)}")
    print(f"moves/req gain-order / current {m[0]:.3f} [{m[1]:.3f}, {m[2]:.3f}], lower in {sum(mv(a) < mv(b) for _, b, a in rows)}/{len(rows)}")
    print(f"relocated MB/req ratio         {r[0]:.3f} [{r[1]:.3f}, {r[2]:.3f}]; cold-start ratio {cold:.2f}")
    for rho in ("0.7", "0.85"):
        kk = [(b, a) for tg, b, a in rows if f"_r{rho}_" in tg]
        if kk:
            print(f"  rho {rho}: P99 {np.exp(np.mean([np.log(a['p99_makespan'] / b['p99_makespan']) for b, a in kk])):.3f}"
                  f"  moves/req {np.exp(np.mean([np.log(mv(a) / mv(b)) for b, a in kk])):.3f}")
    c1, c2 = p[2] <= 1.02, m[2] <= 0.95
    print(f"\nP99 not worse: {'met' if c1 else 'NOT met'}; moves >= 5% lower: {'met' if c2 else 'NOT met'} -> {'PASS' if c1 and c2 else 'FAIL'}"
          f"{'' if len(rows) == len(cases()) else ' (partial, not the pre-registered reading)'}")


if __name__ == "__main__":
    {"run": lambda: run(int(sys.argv[2]) if len(sys.argv) > 2 else 6), "report": report}[sys.argv[1]]()
