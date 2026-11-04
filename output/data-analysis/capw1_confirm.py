"""transfer_only confirmation on fresh seeds 4-6 (CAP-W1; pre-registered 4 Nov 2026 in knowledge/synthesis/workflow-aware-decision-rules.md,
"transfer_only confirmation on fresh seeds 4-6"). 18 cases (F1/F2 x 50/70/85% x seeds 4-6), scenarios weighted exactly as capw1_light.py prep,
three arms with controller "ours" (FROZEN-2, lam 0.5, criticality queue order); only the dispatcher differs:
  matcher (default dispatcher), greedy_eft, transfer_only.
  CONFIRMED = C1 (P99 transfer_only / matcher CI upper <= 1.02, cold-start ratio <= 1.2) and C2 (P99 transfer_only / greedy_eft CI upper <= 1.00).

  python capw1_confirm.py prep [workers] | run [workers] | report
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
import capw1_light as L  # noqa: E402  (prep_job writes results/capW1_light/{tag}.sc.pkl; seeds 4-6 do not clash with 1-3)

CAP = "CAP-W1"
OUT = ROOT / "results" / "capW1_confirm"
DURATION, WARMUP = 900.0, 60.0
ARMS = ("matcher", "greedy_eft", "transfer_only")


def cases():
    return [f"{f}_r{r}_s{s}" for f in ("F1", "F2") for r in (0.5, 0.7, 0.85) for s in (4, 5, 6)]


def run_job(args):
    tg, arm = args
    out = OUT / f"{tg}.{arm}.json"
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
        P = pickle.load(open(L.OUT / f"{tg}.sc.pkl", "rb"))
        sc, X0 = P["sc"], P["X0"]
        assert sc.meta.get("capacity_model") == CAP
        seed, fam = int(tg.split("_s")[1]), tg.split("_r")[0]
        kw = sim_kwargs("B_STAR", A)
        kw.update(warmup=WARMUP, duration=DURATION, retry_min_interval=1.0, retry_max_attempts=10)
        if arm != "matcher":
            kw["dispatcher"] = D.DISPATCHERS[arm]
        kw["queue_priority"] = QueuePriority("full", aging=2.0)
        adj = O3SimAdjuster(make_adjuster("B_STAR", A, seed=seed + 300), MOVE_PERIOD_S[fam], epoch=60.0, horizon=30.0, K=8,
                            seed=seed + 800, warmup=WARMUP, blind=True, cand_mode="nosim", churn=dict(FROZEN2, lam=0.5))
        kw["interval"] = adj.next_interval
        t0 = time.time()
        sim = Sim(sc, X0.copy(), adjuster=adj, seed=seed + 400, **kw)
        r = sim.run()
        sim.check_invariants()
        r["wall_s"] = time.time() - t0
        out.write_text(json.dumps(dict(capacity_model=CAP, case=tg, ctrl=f"ours_{arm}", arm=arm, result=r,
                                       rho_u=P["rho_u"], rho_w=P["rho_w"], fill_x0=P["fill_x0"])))
    except Exception:
        import traceback
        out.with_suffix(".err").write_text(traceback.format_exc())
        return str(out) + " FAILED"
    return str(out)


def prep(workers):
    with ProcessPoolExecutor(workers) as ex:
        for r in ex.map(L.prep_job, cases()):
            print("prep", r, flush=True)


def run(workers):
    jobs = [(c, a) for c in cases() for a in ARMS if not (OUT / f"{c}.{a}.json").exists()]
    slow = {"matcher": 0, "greedy_eft": 1, "transfer_only": 2}       # longest first
    jobs.sort(key=lambda j: (slow[j[1]], -float(j[0].split("_r")[1].split("_")[0])))
    print(len(jobs), "runs", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        for r in ex.map(run_job, jobs):
            print("done", r, flush=True)


def gm_ci(x, seed=0):
    x = np.log(np.asarray(x, float))
    rng = np.random.default_rng(seed)
    bs = [x[rng.integers(0, len(x), len(x))].mean() for _ in range(10000)]
    lo, hi = np.exp(np.percentile(bs, [2.5, 97.5]))
    return float(np.exp(x.mean())), float(lo), float(hi)


def report():
    R = {}
    for c in cases():
        ps = {a: OUT / f"{c}.{a}.json" for a in ARMS}
        if all(p.exists() for p in ps.values()):
            R[c] = {a: json.loads(p.read_text())["result"] for a, p in ps.items()}
    print(f"{len(R)} of {len(cases())} cases complete")
    if not R:
        return
    p99 = lambda x: x["p99_makespan"]
    mv = lambda x: x["n_moved"] / x["n_completed"]
    mb = lambda x: x["mb_relocated"] / x["n_completed"]
    for c, x in R.items():
        print(f"{c:12s} P99 M {p99(x['matcher']):6.1f} G {p99(x['greedy_eft']):6.1f} T {p99(x['transfer_only']):6.1f}"
              f" | moves/req {mv(x['matcher']):.2f} {mv(x['greedy_eft']):.2f} {mv(x['transfer_only']):.2f}"
              f" | plan ms {x['matcher']['plan_ms_mean']:.1f} {x['greedy_eft']['plan_ms_mean']:.1f} {x['transfer_only']['plan_ms_mean']:.1f}")
    ks = list(R)

    def ratio(f, a, b):
        return gm_ci([f(R[k][a]) / max(f(R[k][b]), 1e-9) for k in ks])

    def wins(f, a, b):
        return sum(f(R[k][a]) < f(R[k][b]) for k in ks)
    c1 = ratio(p99, "transfer_only", "matcher")
    cold = float(np.mean([R[k]["transfer_only"]["cold_starts"] / max(R[k]["matcher"]["cold_starts"], 1) for k in ks]))
    c2 = ratio(p99, "transfer_only", "greedy_eft")
    print(f"\nC1 P99 transfer_only / matcher   {c1[0]:.3f} [{c1[1]:.3f}, {c1[2]:.3f}] better {wins(p99, 'transfer_only', 'matcher')}/{len(ks)}, cold-start ratio {cold:.2f}")
    print(f"C2 P99 transfer_only / greedy_eft {c2[0]:.3f} [{c2[1]:.3f}, {c2[2]:.3f}] better {wins(p99, 'transfer_only', 'greedy_eft')}/{len(ks)}")
    g = ratio(p99, "greedy_eft", "matcher")
    print(f"   P99 greedy_eft / matcher       {g[0]:.3f} [{g[1]:.3f}, {g[2]:.3f}]")
    for nm, f in (("moves/req", mv), ("reloc MB/req", mb), ("plan ms", lambda x: x["plan_ms_mean"])):
        a, b = ratio(f, "transfer_only", "greedy_eft"), ratio(f, "transfer_only", "matcher")
        print(f"   {nm:12s} T/G {a[0]:.3f} [{a[1]:.3f}, {a[2]:.3f}]   T/M {b[0]:.3f} [{b[1]:.3f}, {b[2]:.3f}]")
    for rho in ("0.5", "0.7", "0.85"):
        kk = [k for k in ks if f"_r{rho}_" in k]
        if kk:
            v = [p99(R[k]["transfer_only"]) / p99(R[k]["greedy_eft"]) for k in kk]
            w = [p99(R[k]["transfer_only"]) / p99(R[k]["matcher"]) for k in kk]
            print(f"   rho {rho}: P99 T/G {np.exp(np.mean(np.log(v))):.3f}  T/M {np.exp(np.mean(np.log(w))):.3f}")
    ok1 = c1[2] <= 1.02 and cold <= 1.2
    ok2 = c2[2] <= 1.00
    print(f"\nC1 {'met' if ok1 else 'NOT met'}, C2 {'met' if ok2 else 'NOT met'} -> {'CONFIRMED' if ok1 and ok2 else 'NOT CONFIRMED'}"
          f"{'' if len(ks) == len(cases()) else f' (partial: {len(ks)} cases, not the pre-registered reading)'};"
          f" BETTER vs matcher: {'yes' if c1[2] <= 0.97 else 'no'}")


if __name__ == "__main__":
    w = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    {"prep": lambda: prep(w), "run": lambda: run(w), "report": report}[sys.argv[1]]()
