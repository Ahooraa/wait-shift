"""FROZEN-5 confirmation (pre-registered 12 Nov 2026): SeBS applications, 10 nodes, seeds 4, 5, 6; FROZEN-4 and FROZEN-5 on the same scenario, layout and common random numbers
(simulator), RL on the same cells for the comparison. Readings C1, C2, C4 exactly as registered in knowledge/synthesis/workflow-aware-decision-rules.md.
    ~/venv-dfps/bin/python testbed/diag/f5_confirm.py run [workers] | report
Results: results/f5_confirm/<app>.s<seed>.<arm>.json. Nothing is re-run after the report has been read."""
import json, sys, time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "results" / "f5_confirm"
APPS = ["690.ml", "660.map-reduce", "650.vid", "680.excamera", "6200.trip-booking"]
Q1 = APPS[:4]
SEEDS = (4, 5, 6)
ARMS = ("frozen4", "frozen5", "rl")


def one(job):
    app, seed, arm = job
    out = OUT / f"{app}.s{seed}.{arm}.json"
    if out.exists():
        return str(out)
    from testbed import baselines_live as BL, frozen_live as FL, sebs_scenario as S
    from testbed.queue_runs import CELLS
    from dfps.nsga2 import PlacementProblem
    rho, cap, warm, window, drain = CELLS[app]; dur = warm + window
    sc, samp = S.build(seed, apps=[app], rho=rho, ne=10, duration_s=dur, rate_cap=cap)
    X0 = PlacementProblem(sc.network, sc.ecc, np.array([f.exec_time for f in sc.functions])).random(np.random.default_rng(seed))
    t0 = time.time()
    if arm == "rl":
        sim, _ = BL.build_rl(sc, seed, warmup=warm, duration=dur, exec_sampler=samp)
    else:
        sim, _ = FL.build(sc, X0, seed, arm=arm, warmup=warm, duration=dur, exec_sampler=samp)
    r = sim.run()
    OUT.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"app": app, "seed": seed, "arm": arm, "wall_s": time.time() - t0,
                               **{k: r.get(k) for k in ("p50_makespan", "p99_makespan", "cold_starts", "n_moved", "n_completed", "n_unfinished", "event_hash", "mover_impl")},
                               "late_bind_ms": list(getattr(sim, "late_bind_ms", []))}, default=float))
    return str(out)


def load(app, seed, arm):
    return json.loads((OUT / f"{app}.s{seed}.{arm}.json").read_text())


def gm(x):
    return float(np.exp(np.mean(np.log(x))))


def report():
    rng = np.random.default_rng(0)
    ratios = {}
    print(f"{'app':18}{'seed':>5}{'F4 P99':>9}{'F5 P99':>9}{'F5/F4':>7}{'P50 F5/F4':>10}{'cold F5/F4':>11}{'moves F4':>9}{'moves F5':>9}{'RL P99':>9}{'F5/RL':>7}")
    for app in APPS:
        for s in SEEDS:
            a, b, c = load(app, s, "frozen4"), load(app, s, "frozen5"), load(app, s, "rl")
            ratios[(app, s)] = (b["p99_makespan"] / a["p99_makespan"], b["p50_makespan"] / a["p50_makespan"], b["cold_starts"] / max(1, a["cold_starts"]))
            print(f"{app:18}{s:5d}{a['p99_makespan']:9.2f}{b['p99_makespan']:9.2f}{ratios[(app, s)][0]:7.3f}{ratios[(app, s)][1]:10.3f}{ratios[(app, s)][2]:11.2f}{a['n_moved']:9d}{b['n_moved']:9d}{c['p99_makespan']:9.2f}{b['p99_makespan']/c['p99_makespan']:7.2f}")
    q1 = np.log([ratios[(a, s)][0] for a in Q1 for s in SEEDS])
    bs = [rng.choice(q1, len(q1)).mean() for _ in range(10000)]
    lo, hi = np.exp(np.percentile(bs, 2.5)), np.exp(np.percentile(bs, 97.5))
    c1 = hi <= 0.97
    print(f"\nC1  Q1 applications, 12 pairs: geometric-mean P99 ratio F5/F4 {np.exp(q1.mean()):.3f}, 95% bootstrap CI [{lo:.3f}, {hi:.3f}]; better in {int((q1 < 0).sum())} of 12  -> {'MET' if c1 else 'NOT MET'} (upper end <= 0.97)")
    c2 = True
    for app in APPS:
        g = gm([ratios[(app, s)][0] for s in SEEDS]); cs = gm([ratios[(app, s)][2] for s in SEEDS])
        ok = g <= 1.03 and cs <= 1.2
        c2 &= ok
        print(f"C2  {app:18} geometric-mean P99 ratio {g:.3f} (<= 1.03), cold-start ratio {cs:.2f} (<= 1.2)  -> {'ok' if ok else 'FAILS'}")
    ms = [x for app in APPS for s in SEEDS for x in load(app, s, "frozen5")["late_bind_ms"]]
    p99 = float(np.percentile(ms, 99)); c4 = p99 <= 10.0
    print(f"C4  decision time of the rule over {len(ms)} decisions: p99 {p99:.3f} ms, max {max(ms):.2f} ms (<= 10 ms)  -> {'MET (simulator part; live part pending)' if c4 else 'NOT MET'}")
    print(f"C3  met on the development cases (0.966 [0.948, 0.982]), recorded before this run")
    med = float(np.median([ratios[(a, s)][0] for a in Q1 for s in SEEDS]))
    print(f"\nmedian case ratio over the 12 Q1 pairs {med:.3f};  mover_impl {sorted({load(a, s, 'frozen5')['mover_impl'] for a in APPS for s in SEEDS})};  incomplete runs {sum(load(a, s, r)['n_unfinished'] > 0 for a in APPS for s in SEEDS for r in ARMS)}")
    print(f"\nSIMULATOR PART OF THE REGISTERED READING: {'CONFIRMED (C1, C2, C3, C4 simulator part), live checks pending' if (c1 and c2 and c4) else 'NOT CONFIRMED'}")


if __name__ == "__main__":
    if sys.argv[1] == "run":
        w = int(sys.argv[2]) if len(sys.argv) > 2 else 6
        jobs = [(a, s, r) for a in APPS for s in SEEDS for r in ARMS]
        with ProcessPoolExecutor(w) as ex:
            for f in ex.map(one, jobs):
                print("done", Path(f).name, flush=True)
    else:
        report()
