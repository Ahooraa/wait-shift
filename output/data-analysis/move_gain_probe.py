"""Phase 0, check 3 (2026-10-25): does the gain of an accepted move collapse near saturation?

If the mean/median move gain stays large across loads, the finish-time rule is finding good moves everywhere and there is
nothing to prune. If it collapses toward zero near overload, moves there are mostly churn (tiny-gain relocations) and a
dispersion-scaled margin is worth building. Controller "ours" only (the stack's shortest-queue rule has no AET gain concept).
k = 1 only, to isolate the LOAD axis from data intensity. Logs every accepted move's gain (O3SimAdjuster.gain_log, new
dfps/o3s.py churn["log_gain"]) over the full 900 s window, both families, 4 loads.
  python move_gain_probe.py run [workers] | analyze
"""
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(ROOT))
import d3s_headroom as d  # noqa: E402
import operating_envelope as oe  # noqa: E402
from frozen2 import FROZEN2, MOVE_PERIOD_S  # noqa: E402

from dfps.o3s import O3SimAdjuster  # noqa: E402
from dfps.sim import Sim  # noqa: E402
from dfps.variants import make_adjuster, sim_kwargs  # noqa: E402

RUNS = ROOT / "results" / "move_gain"
LOADS = (0.5, 0.7, 0.85, 0.92)
FAMS = ("F1", "F2")


def one(args, duration=None, out=None):
    fam, rho = args
    out = RUNS / f"{fam}_r{rho}.json" if out is None else out
    if out.exists():
        return str(out)
    try:
        assert np.__version__.startswith("1."), "run with the Anaconda interpreter (numpy 1.26)"
        T = json.loads((d.OUT / "g2_tstar.json").read_text())
        tstar = float(T["families"][fam]["T_star"])
        sc, X0 = oe.build(fam, rho, 1)
        kw = sim_kwargs("B_STAR", oe.ASSUME)
        kw.update(warmup=d.WARMUP, duration=d.DURATION if duration is None else duration, retry_min_interval=1.0, retry_max_attempts=10)
        adj = O3SimAdjuster(make_adjuster("B_STAR", oe.ASSUME, seed=oe.SEED + 300), MOVE_PERIOD_S[fam], epoch=60.0, horizon=120.0, K=5,
                            seed=oe.SEED + 800, warmup=d.WARMUP, blind=True, cand_mode="nosim", churn=dict(FROZEN2, log_gain=True))
        kw["interval"] = adj.next_interval
        t = time.time()
        sim = Sim(sc, X0, adjuster=adj, seed=oe.SEED + 400, **kw)
        r = sim.run()
        sim.check_invariants()
        dur = kw["duration"]
        gains = [g for t_, g in adj.gain_log if t_ < dur]   # drop the post-duration drain tail, as in staleness_probe.py
        out.write_text(json.dumps(dict(fam=fam, rho=rho, result={k: r[k] for k in ("p99_makespan", "n_moved", "n_completed")},
                                       gains=gains, wall_s=time.time() - t)))
        return str(out)
    except Exception:
        import traceback
        out.with_suffix(".err").write_text(traceback.format_exc())
        return str(out) + " FAILED"


def run(workers):
    RUNS.mkdir(parents=True, exist_ok=True)
    jobs = [(f, r) for r in LOADS for f in FAMS]
    jobs = [j for j in jobs if not (RUNS / f"{j[0]}_r{j[1]}.json").exists()]
    print(f"{len(jobs)} runs", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        for r in ex.map(one, jobs):
            print("done", r, flush=True)


def analyze():
    print("%-3s %5s | %8s | %10s %10s %10s %10s | %6s" % ("fam", "load", "n_moves", "mean", "median", "p10", "p90", "share<=0.5s"))
    for fam in FAMS:
        for rho in LOADS:
            f = RUNS / f"{fam}_r{rho}.json"
            if not f.exists():
                continue
            x = json.loads(f.read_text())
            g = np.array(x["gains"])
            if len(g) == 0:
                print(f"{fam:-3s} {rho:5.2f} | no moves logged")
                continue
            small = float((g <= 0.5).mean())
            print("%-3s %5.2f | %8d | %10.2f %10.2f %10.2f %10.2f | %6.1f%%" % (
                fam, rho, len(g), g.mean(), np.median(g), np.percentile(g, 10), np.percentile(g, 90), 100 * small))


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 4)
    else:
        analyze()
