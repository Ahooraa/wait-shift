"""Missing CAP-W1 rows for the final results table (4 Nov 2026, user request).
  stack    textbook stack: FROZEN-2 with HPA sizing (size-aware: _fit_counts with sc.fw) and join-shortest-queue moves, default dispatcher
           (the CAP-U definition in final_ablation.py, ported unchanged to the weighted scenarios)
  RL_CAL   the RL baseline retrained on the calibrated reproduction scenario WITH size features (results/rl_policy_cal_capw1.pt,
           train_rl.py --calibrated --capw1), on-demand container model as RL
  frozen3  FROZEN-3 (frozen2.FROZEN3 + FROZEN3_DISPATCHER): the paper's controller; here rho 0.5, seeds 1-6 (rho 0.7/0.85 exist in
           results/v3_online and results/v3_confirm)
Development cases F1/F2 x rho 0.5/0.7/0.85 x seeds 1-3 (stack, RL_CAL). Results results/capW1_rows/{tag}.{arm}.json, CAP-W1.
  python capw1_rows.py run [workers] [arm ...] | table
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
OUT = ROOT / "results" / "capW1_rows"
W1 = ROOT / "results" / "capW1_light"
DURATION, WARMUP = 900.0, 60.0
CAP = "CAP-W1"


def dev(seeds=(1, 2, 3), rhos=(0.5, 0.7, 0.85)):
    return [f"{f}_r{r}_s{s}" for f in ("F1", "F2") for r in rhos for s in seeds]


def jobs(arms):
    out = []
    for a in arms:
        cs = dev(seeds=(1, 2, 3, 4, 5, 6), rhos=(0.5,)) if a == "frozen3" else dev()
        out += [(c, a) for c in cs]
    return out


# placebo nulls: the same controller with the move clock shifted by 1 ms (no systematic effect, the trajectory diverges); see run-noise-floor
PLACEBO = {f"{a}_p{i}": (a, d) for a in ("frozen3m", "frozen3i", "fill1", "fill8", "mv4") for i, d in ((1, 0.001), (2, -0.001))}


def run_job(args):
    tg, arm_name = args
    arm, d_move = PLACEBO.get(arm_name, (arm_name, 0.0))
    out = OUT / f"{tg}.{arm_name}.json"
    if out.exists():
        return str(out)
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        import numpy as _np
        assert _np.__version__.startswith("1."), "run with the Anaconda interpreter (numpy 1.26)"
        import yaml
        A = yaml.safe_load((ROOT / "config" / "assumptions.yaml").read_text(encoding="utf-8"))
        P = pickle.load(open(W1 / f"{tg}.sc.pkl", "rb"))
        sc, X0 = P["sc"], P["X0"]
        assert sc.meta.get("capacity_model") == CAP
        seed, fam = int(tg.split("_s")[1]), tg.split("_r")[0]
        t0 = time.time()
        if arm == "RL_CAL":
            from experiments.run import load_rl_policy
            from dfps.ondemand import OnDemandSim
            pol = load_rl_policy(str(ROOT / "results" / "rl_policy_cal_capw1.pt"), seed + 600, sizes=True)
            sim = OnDemandSim(sc, pol, seed=seed + 400, duration=DURATION, warmup=WARMUP)
        else:
            from dfps import dispatchers as D
            from dfps.dispatch_priority import QueuePriority
            from dfps.o3s import O3SimAdjuster
            from dfps.sim import Sim
            from dfps.variants import make_adjuster, sim_kwargs
            from frozen2 import FROZEN2, FROZEN3_EXACT, FROZEN3_FILL, FROZEN3_FILL8, FROZEN3_INCR, FROZEN3_LAZY, FROZEN3_PL1, FROZEN3_DISPATCHER, FROZEN4_MV4, MOVE_PERIOD_S
            kw = sim_kwargs("B_STAR", A)
            kw.update(warmup=WARMUP, duration=DURATION, retry_min_interval=1.0, retry_max_attempts=10)
            if arm in ("frozen3", "frozen3f", "frozen3m", "frozen3i", "fill1", "fill8", "mv4"):
                kw["dispatcher"] = D.DISPATCHERS[FROZEN3_DISPATCHER]
                kw["queue_priority"] = QueuePriority("full", aging=2.0)
                cand, churn = "nosim", dict({"frozen3": FROZEN3_EXACT, "frozen3f": FROZEN3_LAZY, "frozen3m": FROZEN3_PL1, "frozen3i": FROZEN3_INCR, "fill1": FROZEN3_FILL, "fill8": FROZEN3_FILL8, "mv4": FROZEN4_MV4}[arm], lam=0.5)
                # frozen3 = exact (MV-2), frozen3f = MV-3 + lazy scoring (PL-2), frozen3m = MV-3, exact scoring (PL-1); frozen3i = MV-3 + PL-4, the default since 8 Nov 2026
            elif arm == "stack":                                  # as final_ablation.py VARIANTS["stack"]: hpa sizing + jsq moves on FROZEN-2
                cand, churn = "hpa", dict(FROZEN2, rebal_rule="jsq")
            else:
                raise ValueError(arm)
            adj = O3SimAdjuster(make_adjuster("B_STAR", A, seed=seed + 300), MOVE_PERIOD_S[fam] + d_move, epoch=60.0, horizon=30.0, K=8,
                                seed=seed + 800, warmup=WARMUP, blind=True, cand_mode=cand, churn=churn)
            kw["interval"] = adj.next_interval
            sim = Sim(sc, X0.copy(), adjuster=adj, seed=seed + 400, **kw)
        r = sim.run()
        sim.check_invariants()
        r["wall_s"] = time.time() - t0
        out.write_text(json.dumps(dict(capacity_model=CAP, case=tg, ctrl=arm_name, result=r)))
    except Exception:
        import traceback
        out.with_suffix(".err").write_text(traceback.format_exc())
        return str(out) + " FAILED"
    return str(out)


def run(workers, arms):
    todo = [j for j in jobs(arms) if not (OUT / f"{j[0]}.{j[1]}.json").exists()]
    todo.sort(key=lambda j: -float(j[0].split("_r")[1].split("_")[0]))
    print(len(todo), "runs", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        for r in ex.map(run_job, todo):
            print("done", r, flush=True)


def frozen3(tg):
    s = int(tg.split("_s")[1])
    if "_r0.5_" in tg:
        p = OUT / f"{tg}.frozen3.json"
    else:
        p = ROOT / "results" / ("v3_online" if s <= 3 else "v3_confirm") / f"{tg}.json"
    return json.loads(p.read_text())["result"] if p.exists() else None


def rows(tg):
    R = {}
    for ctrl, p in (("B*", W1 / f"{tg}.B_STAR.json"), ("RL", W1 / f"{tg}.RL.json"), ("RL_CAL", OUT / f"{tg}.RL_CAL.json"),
                    ("Textbook stack", OUT / f"{tg}.stack.json"), ("FROZEN-2", W1 / f"{tg}.ours.json")):
        if p.exists():
            R[ctrl] = json.loads(p.read_text())["result"]
    f3 = frozen3(tg)
    if f3:
        R["FROZEN-3"] = f3
    return R


def table():
    cs = dev()
    allr = {c: rows(c) for c in cs}
    names = ["B*", "RL", "RL_CAL", "Textbook stack", "FROZEN-2", "FROZEN-3"]
    print("CAP-W1, 18 development cases (seeds 1-3); coverage:", {n: sum(n in allr[c] for c in cs) for n in names})
    for fam in ("F1", "F2"):
        print(f"\n{fam}  P99 makespan (s), mean over seeds 1-3")
        print("rho   " + "".join(f"{n:>16s}" for n in names))
        for rho in (0.5, 0.7, 0.85):
            kk = [c for c in cs if c.startswith(f"{fam}_r{rho}_")]
            vals = []
            for n in names:
                v = [allr[c][n]["p99_makespan"] for c in kk if n in allr[c]]
                vals.append(f"{np.mean(v):16.1f}" if len(v) == len(kk) else f"{'-':>16s}")
            print(f"{rho:<6}" + "".join(vals))
    ok = [c for c in cs if all(n in allr[c] for n in names)]
    if ok:
        print(f"\nFROZEN-3 P99 gain over each row (mean of (row - F3)/row over {len(ok)} cases), and over best existing (min of B*, RL, RL_CAL):")
        for n in names[:-1]:
            g = [(allr[c][n]["p99_makespan"] - allr[c]["FROZEN-3"]["p99_makespan"]) / allr[c][n]["p99_makespan"] for c in ok]
            print(f"  vs {n:15s} {np.mean(g) * 100:+6.1f}%  wins {sum(x > 0 for x in g)}/{len(ok)}")
        be = [min(allr[c][n]["p99_makespan"] for n in ("B*", "RL", "RL_CAL")) for c in ok]
        g = [(b - allr[c]["FROZEN-3"]["p99_makespan"]) / b for b, c in zip(be, ok)]
        print(f"  vs best existing    {np.mean(g) * 100:+6.1f}%  wins {sum(x > 0 for x in g)}/{len(ok)}")


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 6, sys.argv[3:] or ["frozen3", "stack", "RL_CAL"])
    else:
        table()
