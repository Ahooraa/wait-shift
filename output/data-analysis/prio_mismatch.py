"""FIFO versus criticality-order mismatch in the move rule's estimate (3 Nov 2026, user request). CAP-W1, matcher dispatcher, "ours" (FROZEN2, lam 0.5,
QueuePriority("full", aging=2.0)): the queue is SERVED by criticality, but the mover's AET counts the tasks "ahead" of a task by FIFO position.
Reading fixed in knowledge/synthesis/workflow-aware-decision-rules.md ("FIFO versus criticality-order mismatch").

  diag  logging only (churn log_prio_mismatch): for every accepted move, "ahead" at the source and at the destination in FIFO terms versus in
        service-order terms, and the gain of the move under both estimates. Six step-1 cases; event hash must equal results/capW1_light/{tg}.ours.json.
  arm   the same controller with the service-order estimate (churn prio_aet_peek) on the 18 CAP-W1 development cases, against the stored
        capW1_light ours runs.
  python prio_mismatch.py diag run [workers] | diag report | arm run [workers] | arm report
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
OUT_D, OUT_A = ROOT / "results" / "prio_mismatch_diag", ROOT / "results" / "prio_mismatch_arm"
W1 = ROOT / "results" / "capW1_light"
DUR, WARM, LAM = 900.0, 60.0, 0.5
CASES6 = [f"{f}_r{r}_s1" for f in ("F1", "F2") for r in (0.5, 0.7, 0.85)]
CASES18 = [f"{f}_r{r}_s{s}" for f in ("F1", "F2") for r in (0.5, 0.7, 0.85) for s in (1, 2, 3)]
C = dict(now=0, rid=1, task=2, f=3, i_f=4, i_p=5, qlen=6, d_f=7, d_p=8, tier=9, in0=10, svc0f=11, svc0p=12, out0=13, in1=14, svc1f=15, svc1p=16, out1=17)


def run_job(args):
    mode, tg = args
    outdir = OUT_D if mode == "diag" else OUT_A
    out = outdir / f"{tg}.json"
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
        kw.update(warmup=WARM, duration=DUR, retry_min_interval=1.0, retry_max_attempts=10)
        kw["queue_priority"] = QueuePriority("full", aging=2.0)
        extra = dict(log_prio_mismatch=True) if mode == "diag" else dict(prio_aet_peek=True)
        adj = O3SimAdjuster(make_adjuster("B_STAR", A, seed=seed + 300), MOVE_PERIOD_S[fam], epoch=60.0, horizon=30.0, K=8,
                            seed=seed + 800, warmup=WARM, blind=True, cand_mode="nosim", churn=dict(FROZEN2, lam=LAM, **extra))
        kw["interval"] = adj.next_interval
        t0 = time.time()
        sim = Sim(sc, X0.copy(), adjuster=adj, seed=seed + 400, **kw)
        r = sim.run()
        sim.check_invariants()
        stored = json.loads((W1 / f"{tg}.ours.json").read_text())["result"]["event_hash"]
        outdir.mkdir(parents=True, exist_ok=True)
        if mode == "diag":
            np.save(outdir / f"{tg}.npy", np.array(getattr(adj, "pm_log", []), dtype=float))
        out.write_text(json.dumps(dict(capacity_model="CAP-W1", case=tg, mode=mode, hash_matches_stored=(r["event_hash"] == stored), wall_s=time.time() - t0,
                                       result=r)))
    except Exception:
        import traceback
        outdir.mkdir(parents=True, exist_ok=True)
        out.with_suffix(".err").write_text(traceback.format_exc())
        return str(out) + " FAILED"
    return str(out)


def run(mode, workers):
    cs = CASES6 if mode == "diag" else CASES18
    outdir = OUT_D if mode == "diag" else OUT_A
    todo = [c for c in cs if not (outdir / f"{c}.json").exists()]
    todo.sort(key=lambda c: -float(c.split("_r")[1].split("_")[0]))
    print(len(todo), "runs", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        for r in ex.map(run_job, [(mode, c) for c in todo]):
            print("done", r, flush=True)


def diag_report():
    nflip = done = 0
    for tg in CASES6:
        p = OUT_D / f"{tg}.json"
        if not p.exists():
            print(tg, "missing")
            continue
        if not json.loads(p.read_text())["hash_matches_stored"]:
            print(tg, "EVENT HASH DIFFERS from the stored run -> not used")
            continue
        a = np.load(OUT_D / f"{tg}.npy")
        a = a[a[:, C["now"]] >= WARM]
        g = lambda k: a[:, C[k]]  # noqa: E731
        Gf = (g("in0") + g("svc0f") + LAM * g("out0")) - (g("in1") + g("svc1f") + LAM * g("out1"))
        Gp = (g("in0") + g("svc0p") + LAM * g("out0")) - (g("in1") + g("svc1p") + LAM * g("out1"))
        flip = (Gp <= 0).mean()
        done += 1
        nflip += flip >= 0.20
        tier = g("tier")
        tsh = " ".join(f"t{t}:{(tier == t).mean():.0%}" for t in (0, 1, 2, 3))
        print(f"{tg}: moves {len(a)}  source ahead FIFO {g('i_f').mean():.2f} vs service-order {g('i_p').mean():.2f} (differs {(g('i_f') != g('i_p')).mean():.0%}, service-order smaller {(g('i_p') < g('i_f')).mean():.0%}, larger {(g('i_p') > g('i_f')).mean():.0%})"
              f"\n          destination ahead FIFO {g('d_f').mean():.2f} vs service-order {g('d_p').mean():.2f} (differs {(g('d_f') != g('d_p')).mean():.0%})"
              f"  | wait at source {g('svc0f').mean():.2f}s -> {g('svc0p').mean():.2f}s, at destination {g('svc1f').mean():.2f}s -> {g('svc1p').mean():.2f}s"
              f"\n          estimated gain per move {Gf.mean():.2f}s (FIFO) -> {Gp.mean():.2f}s (service order); moves whose gain is <= 0 in service order {flip:.0%}; tier of the moved task {tsh}")
    if done == len(CASES6):
        print(f"\nmoves with service-order gain <= 0 are >= 20% in {nflip}/6 cases -> " + ("mismatch material" if nflip >= 4 else "mismatch not material" if nflip <= 2 else "mixed"))


def arm_report():
    rows = []
    for tg in CASES18:
        a, b = OUT_A / f"{tg}.json", W1 / f"{tg}.ours.json"
        if a.exists() and b.exists():
            rows.append((tg, json.loads(b.read_text())["result"], json.loads(a.read_text())["result"]))
    print(f"{len(rows)} of {len(CASES18)} cases done")
    lr = []
    for tg, m, g in rows:
        lr.append(np.log(g["p99_makespan"] / m["p99_makespan"]))
        print(f"{tg:12s} FIFO estimate {m['p99_makespan']:7.1f}  service-order estimate {g['p99_makespan']:7.1f} ({(g['p99_makespan']/m['p99_makespan']-1)*100:+.0f}%)"
              f"  cold {m['cold_starts']}/{g['cold_starts']}  moves/req {m['n_moved']/m['n_completed']:.2f}/{g['n_moved']/g['n_completed']:.2f}")
    if len(rows) >= 6:
        lr = np.array(lr)
        rng = np.random.default_rng(0)
        bs = [lr[rng.integers(0, len(lr), len(lr))].mean() for _ in range(10000)]
        lo, hi = np.exp(np.percentile(bs, [2.5, 97.5]))
        cold = np.mean([g["cold_starts"] / m["cold_starts"] for _, m, g in rows])
        print(f"\ngeometric-mean ratio {np.exp(lr.mean()):.3f}, 95% CI [{lo:.3f}, {hi:.3f}]; better in {sum(l < 0 for l in lr)}/{len(lr)}; cold-start ratio {cold:.2f}")
        verdict = "BETTER (CI upper <= 0.97)" if hi <= 0.97 else ("NOT WORSE (CI upper <= 1.02)" if hi <= 1.02 else "not shown to be non-inferior")
        print("verdict:", verdict + ("" if cold <= 1.2 else "; cold starts more than 20% higher -> fails the cold-start condition"),
              "" if len(rows) == len(CASES18) else f"(partial: {len(rows)} cases, not the pre-registered reading)")


if __name__ == "__main__":
    m, c = sys.argv[1], sys.argv[2]
    if c == "run":
        run(m, int(sys.argv[3]) if len(sys.argv) > 3 else 3)
    else:
        {"diag": diag_report, "arm": arm_report}[m]()
