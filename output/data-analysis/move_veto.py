"""Randomised move veto (4 Nov 2026, user request): do the mover's moves pay? At a task's first accepted move the move is vetoed with probability
0.1 (own RNG); a vetoed task is never moved. Vetoed and moved tasks are then compared on the wait from the decision to the start, on the request's
remaining sojourn from the decision, and on the share whose request ends in the run's slowest 1%. CAP-W1, controller "ours", six step-1 cases.
Reading fixed in knowledge/synthesis/workflow-aware-decision-rules.md ("Randomised move veto").
  python move_veto.py run [workers] | report | smoke
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
OUT = ROOT / "results" / "move_veto"
W1 = ROOT / "results" / "capW1_light"
CASES = [f"{f}_r{r}_s1" for f in ("F1", "F2") for r in (0.5, 0.7, 0.85)]
DURATION, WARMUP = 900.0, 60.0
VETO_P = 0.1


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
                            seed=seed + 800, warmup=WARMUP, blind=True, cand_mode="nosim",
                            churn=dict(FROZEN2, lam=0.5, veto_p=VETO_P, veto_seed=seed + 900))
        kw["interval"] = adj.next_interval
        t0 = time.time()
        sim = Sim(sc, X0.copy(), adjuster=adj, seed=seed + 400, **kw)
        r = sim.run()
        sim.check_invariants()
        stored = json.loads((W1 / f"{tg}.ours.json").read_text())["result"]
        OUT.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(dict(capacity_model="CAP-W1", case=tg, veto_p=VETO_P, p99=r["p99_makespan"], p99_stored=stored["p99_makespan"],
                                       moves_per_req=r["n_moved"] / max(r["n_completed"], 1),
                                       moves_per_req_stored=stored["n_moved"] / max(stored["n_completed"], 1),
                                       wall_s=time.time() - t0, tasks=sim.trace["tasks"], reqs=sim.trace["reqs"], veto=getattr(adj, "veto_log", []))))
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


def _eff(a, b, rng, reps=1000):
    """mean(a) - mean(b) and a bootstrap 95% CI (tasks resampled within each arm)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) < 2 or len(b) < 2:
        return float("nan"), float("nan"), float("nan")
    bs = [a[rng.integers(0, len(a), len(a))].mean() - b[rng.integers(0, len(b), len(b))].mean() for _ in range(reps)]
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return float(a.mean() - b.mean()), float(lo), float(hi)


def report():
    rng = np.random.default_rng(0)
    pay = low_ok = done = 0
    neg = {}
    for tg in CASES:
        p = OUT / f"{tg}.json"
        if not p.exists():
            print(tg, "missing")
            continue
        d = json.loads(p.read_text())
        st = {(t[0], int(t[2])): t[6] for t in d["tasks"]}             # task start time
        rq = {q[0]: (q[2], q[3]) for q in d["reqs"]}                    # request arrival, completion
        thr = np.quantile([b - a for a, b in rq.values()], 0.99)
        V = np.array(d["veto"], dtype=float)                            # (now, rid, task, f, est. gain, tier, pos, qlen, vetoed)
        V = V[V[:, 0] >= WARMUP]
        rows = []
        for now, rid, task, f, gain, tier, pos, ql, veto in V:
            k = (int(rid), int(task))
            if k not in st or int(rid) not in rq:
                continue
            ta, td = rq[int(rid)]
            rows.append((gain, tier, veto, st[k] - now, td - now, float(td - ta >= thr)))
        R = np.array(rows)
        if len(R) == 0:
            print(tg, "no randomised decisions")
            continue
        done += 1
        vv = R[:, 2] == 1
        terc = np.digitize(R[:, 0], np.quantile(R[:, 0], [1 / 3, 2 / 3]))
        w = _eff(R[vv, 3], R[~vv, 3], rng)
        s = _eff(R[vv, 4], R[~vv, 4], rng)
        t_ = _eff(R[vv, 5], R[~vv, 5], rng)
        pay += s[1] > 0
        print(f"{tg}: randomised {len(R)} (vetoed {int(vv.sum())})  P99 {d['p99']:.1f} (stored {d['p99_stored']:.1f})"
              f"  moves/req {d['moves_per_req']:.2f} (stored {d['moves_per_req_stored']:.2f})"
              f"\n          vetoed minus moved: wait to start {w[0]:+.2f} s [{w[1]:+.2f}, {w[2]:+.2f}]  remaining sojourn {s[0]:+.2f} s [{s[1]:+.2f}, {s[2]:+.2f}]"
              f"  request in slowest 1% {100 * t_[0]:+.2f} pts [{100 * t_[1]:+.2f}, {100 * t_[2]:+.2f}]")
        parts = []
        groups = [("gain low", terc == 0), ("gain mid", terc == 1), ("gain high", terc == 2)] + [(f"tier {k}", R[:, 1] == k) for k in (0, 1, 2, 3)]
        for name, sel in groups:
            nv = int((sel & vv).sum())
            if nv < 100:
                parts.append(f"{name}: n_veto {nv} (too few)")
                continue
            e = _eff(R[sel & vv, 4], R[sel & ~vv, 4], rng)
            parts.append(f"{name}: {e[0]:+.2f} s [{e[1]:+.2f}, {e[2]:+.2f}] (n_veto {nv})")
            if name == "gain low":
                low_ok += e[0] >= 0
            neg[name] = neg.get(name, 0) + (e[2] < 0)
        print("          remaining sojourn, vetoed minus moved, by group: " + "; ".join(parts))
    if done == len(CASES):
        some = [g for g, c in neg.items() if c >= 4]
        print(f"\nvetoed slower (CI lower > 0) in {pay}/6 cases; lowest-gain third not better when vetoed in {low_ok}/6; "
              f"groups where vetoing is better (CI upper < 0) in >= 4/6 cases: {some or 'none'}")
        if some:
            print("-> some moves do not pay: reported as a finding; mover-side tuning already made P99 worse twice (margin, service-order"
                  " estimate), so the headroom is likely inaccessible; no mechanism is built; spatial line closed")
        elif pay >= 4 and low_ok >= 4:
            print("-> moves mostly pay: the mover is at its limit; spatial line closed")
        else:
            print("-> inconclusive, reported as such; spatial line closed")


if __name__ == "__main__":
    {"run": lambda: run(int(sys.argv[2]) if len(sys.argv) > 2 else 3), "report": report,
     "smoke": lambda: print(run_job("F1_r0.85_s1", 150.0))}[sys.argv[1]]()
