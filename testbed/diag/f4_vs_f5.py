"""Simulator comparison of FROZEN-4 and FROZEN-5 on the planned cells (10 nodes, common random numbers, development and confirmation seeds 1-6; no held-out seed).
    ~/venv-dfps/bin/python testbed/diag/f4_vs_f5.py run [workers] | report"""
import json, sys, time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "results" / "f4_vs_f5"
CELLS = [("690.ml", 0.56, None), ("660.map-reduce", 0.45, None), ("650.vid", 0.5, None), ("650.vid", 0.7, None), ("6200.trip-booking", 0.7, 42.0),
         ("680.excamera", 0.5, None), ("680.excamera", 0.7, None)]
SEEDS = (1, 2, 3, 4, 5, 6)
WIN = {"690.ml": (60, 300), "660.map-reduce": (60, 300), "650.vid": (60, 600), "6200.trip-booking": (60, 300), "680.excamera": (180, 1800)}   # the dry run's windows


def one(job):
    app, rho, cap, seed, arm = job
    out = OUT / f"{app}.r{rho}.s{seed}.{arm}.json"
    if out.exists():
        return str(out)
    from testbed import frozen_live as FL, sebs_scenario as S
    from dfps.nsga2 import PlacementProblem
    warm, window = WIN[app]; dur = warm + window
    sc, samp = S.build(seed, apps=[app], rho=rho, ne=10, duration_s=dur, rate_cap=cap)
    X0 = PlacementProblem(sc.network, sc.ecc, np.array([f.exec_time for f in sc.functions])).random(np.random.default_rng(seed))
    sim, _ = FL.build(sc, X0, seed, arm=arm, warmup=warm, duration=dur, exec_sampler=samp)
    r = sim.run()
    OUT.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({k: r.get(k) for k in ("avg_makespan", "p50_makespan", "p95_makespan", "p99_makespan", "cold_starts", "n_moved", "n_completed", "n_unfinished", "event_hash")}, default=float))
    return str(out)


def load(app, rho, seed, arm):
    return json.loads((OUT / f"{app}.r{rho}.s{seed}.{arm}.json").read_text())


def gm(x):
    return float(np.exp(np.mean(np.log(x))))


def report():
    print(f"{'cell':26}{'P99 F4':>9}{'P99 F5':>9}{'ratio':>7}{'median':>8}{'P50':>7}{'mean':>7}{'P95':>7}{'cold':>6}{'moves':>7}   (geometric means over seeds 1-6; ratio = F5 / F4)")
    allp = []
    for app, rho, cap in CELLS:
        a = [load(app, rho, s, "frozen4") for s in SEEDS]; b = [load(app, rho, s, "frozen5") for s in SEEDS]
        r = lambda k: [y[k] / x[k] for x, y in zip(a, b)]
        p99 = r("p99_makespan"); allp += p99
        print(f"{app + ' @' + str(rho):26}{gm([x['p99_makespan'] for x in a]):9.2f}{gm([y['p99_makespan'] for y in b]):9.2f}{gm(p99):7.3f}{float(np.median(p99)):8.3f}{gm(r('p50_makespan')):7.3f}{gm(r('avg_makespan')):7.3f}{gm(r('p95_makespan')):7.3f}{gm([(y['cold_starts'] + 1) / (x['cold_starts'] + 1) for x, y in zip(a, b)]):6.2f}{gm([(y['n_moved'] + 1) / (x['n_moved'] + 1) for x, y in zip(a, b)]):7.3f}   per seed: {[round(v, 2) for v in p99]}")
    print(f"\nall {len(allp)} cases: geometric-mean P99 ratio {gm(allp):.3f}, median {float(np.median(allp)):.3f}, better in {sum(v < 1 for v in allp)}, worse by more than 2% in {sum(v > 1.02 for v in allp)}")


if __name__ == "__main__":
    if sys.argv[1] == "run":
        jobs = [(a, r, c, s, arm) for a, r, c in CELLS for s in SEEDS for arm in ("frozen4", "frozen5")]
        with ProcessPoolExecutor(int(sys.argv[2]) if len(sys.argv) > 2 else 8) as ex:
            for f in ex.map(one, jobs):
                pass
        print("done")
    else:
        report()
