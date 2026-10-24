"""Does the controller depend on DFPS's graph-pattern-matching dispatcher?  (2026-10-24)

The dispatcher fixes where every task of an arriving request runs (dfps/dispatchers.py); the layout and request moves are the controller's
and do not change. Four simpler dispatchers replace DFPS's matcher: greedy_eft (per-task earliest finish), locality (data gravity), jsq
(shortest queue) and random. Each is run under B* (annealing, its tuned period) AND under FROZEN-2, so the gain of FROZEN-2 over B* is
measured with the SAME dispatcher on both sides, and the cost of using a weaker dispatcher is measured for each controller.
Cases: Azure and Huawei x 50/70/85% load x development seeds 1-2 = 12; 4 dispatchers x 2 controllers = 96 runs.
The DFPS-dispatcher reference runs already exist (B*: results/d1_headroom; FROZEN-2: nl_fz2_60).
Files <case>.O3S_h120_blind_nosim_nl_disp_<dispatcher>_<ctrl>.json   (ctrl: bstar | fz2)
  python output/data-analysis/dispatcher_sweep.py run [workers] | analyze
"""
import json
import pickle
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(ROOT))
import d3s_headroom as d  # noqa: E402
from frozen2 import FROZEN2, MOVE_PERIOD_S  # noqa: E402

import yaml  # noqa: E402

from dfps.dispatchers import DISPATCHERS  # noqa: E402
from dfps.o3s import O3SimAdjuster  # noqa: E402
from dfps.sim import Sim  # noqa: E402
from dfps.variants import make_adjuster, sim_kwargs  # noqa: E402

ASSUME = yaml.safe_load((ROOT / "config" / "assumptions.yaml").read_text(encoding="utf-8"))
CASES = [(f, r, s) for f in ("F1", "F2") for r in (0.5, 0.7, 0.85) for s in (1, 2)]
M = "p99_makespan"


def tagc(c):
    return f"{c[0]}_r{c[1]}_s{c[2]}"


def outpath(disp, ctrl, c):
    return d.RUNS / f"{tagc(c)}.O3S_h120_blind_nosim_nl_disp_{disp}_{ctrl}.json"


def one(args):
    disp, ctrl, c, tstar = args
    out = outpath(disp, ctrl, c)
    if out.exists():
        return str(out)
    try:
        assert np.__version__.startswith("1."), "run with the Anaconda interpreter (numpy 1.26)"
        sc = pickle.load(open(d.D1 / f"{tagc(c)}.pkl", "rb"))
        P = pickle.load(open(d.D1 / f"{tagc(c)}.prep.pkl", "rb"))
        seed = c[2]
        kw = sim_kwargs("B_STAR", ASSUME)
        kw.update(warmup=d.WARMUP, duration=d.DURATION, retry_min_interval=1.0, retry_max_attempts=10, dispatcher=DISPATCHERS[disp])
        if ctrl == "bstar":
            kw["interval"] = float(tstar)
            adj = make_adjuster("B_STAR", ASSUME, seed=seed + 300)
        else:
            adj = O3SimAdjuster(make_adjuster("B_STAR", ASSUME, seed=seed + 300), MOVE_PERIOD_S[c[0]], epoch=60.0, horizon=120.0, K=5,
                                seed=seed + 800, warmup=d.WARMUP, blind=True, cand_mode="nosim", churn=dict(FROZEN2))
            kw["interval"] = adj.next_interval
        t = time.time()
        sim = Sim(sc, P["X0"], adjuster=adj, seed=seed + 400, **kw)
        r = sim.run()
        sim.check_invariants()
        r["wall_s"] = time.time() - t
        out.write_text(json.dumps(dict(dispatcher=disp, ctrl=ctrl, case=list(c), result=r)))
        return str(out)
    except Exception:
        import traceback
        out.with_suffix(".err").write_text(traceback.format_exc())
        return str(out) + " FAILED"


def run(workers):
    T = json.loads((d.OUT / "g2_tstar.json").read_text())
    jobs = [(disp, ctrl, c, float(T["families"][c[0]]["T_star"])) for c in sorted(CASES, key=lambda c: -c[1]) for disp in DISPATCHERS
            for ctrl in ("fz2", "bstar")]
    jobs = [j for j in jobs if not outpath(j[0], j[1], j[2]).exists()]
    print(f"{len(jobs)} runs", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        for done in ex.map(one, jobs):
            print("done", done, flush=True)


def analyze():
    from d1_rlla import boot
    ref_b = {}
    for f in d.D1.glob("*.B_STAR.json"):
        x = json.loads(f.read_text())
        ref_b[(x["family"], x["rho"], x["seed"])] = x["result"]
    ref_f = {}
    for f in d.RUNS.glob("*.O3S_h120_blind_nosim_nl_fz2_60.json"):
        x = json.loads(f.read_text())
        ref_f[(x["family"], x["rho"], x["seed"])] = x["result"]
    R = {}
    for f in d.RUNS.glob("*.O3S_h120_blind_nosim_nl_disp_*.json"):
        x = json.loads(f.read_text())
        R[(x["dispatcher"], x["ctrl"], tuple(x["case"]))] = x["result"]
    p = lambda b: f"{b['mean'] * 100:+6.1f}% ({b['lo'] * 100:+.0f} to {b['hi'] * 100:+.0f})"  # noqa: E731
    rows = [("dfps (graph matching)", ref_b, ref_f)] + [
        (n, {c: R[(n, "bstar", c)] for c in CASES if (n, "bstar", c) in R}, {c: R[(n, "fz2", c)] for c in CASES if (n, "fz2", c) in R})
        for n in DISPATCHERS]
    print("P99 (seconds, mean over the cases both controllers have) and the gain of FROZEN-2 over B* with the SAME dispatcher\n")
    print("%-22s %3s | %9s %9s | %-28s | %5s | %-30s | %7s %7s" % (
        "dispatcher", "n", "B* P99", "FZ2 P99", "gain of FROZEN-2 over B*", "wins", "FROZEN-2 vs its DFPS-dispatcher run", "mv/req", "plan ms"))
    for n, b, f in rows:
        ks = [c for c in CASES if c in b and c in f]
        if not ks:
            continue
        g = [(b[c][M] - f[c][M]) / b[c][M] for c in ks]
        vs = [(ref_f[c][M] - f[c][M]) / ref_f[c][M] for c in ks if c in ref_f]
        print("%-22s %3d | %9.0f %9.0f | %-28s | %2d/%2d | %-30s | %7.2f %7.2f" % (
            n, len(ks), np.mean([b[c][M] for c in ks]), np.mean([f[c][M] for c in ks]), p(boot(g)), sum(x > 0 for x in g), len(ks),
            p(boot(vs)) if vs else "—", np.mean([f[c]["n_moved"] / f[c]["n_completed"] for c in ks]), np.mean([f[c]["plan_ms_mean"] for c in ks])))
    print("\nby load, gain of FROZEN-2 over B* with the same dispatcher:")
    for rho in (0.5, 0.7, 0.85):
        s = "  %2.0f%%:" % (100 * rho)
        for n, b, f in rows:
            ks = [c for c in CASES if c in b and c in f and c[1] == rho]
            if ks:
                s += "  %s %+.0f%%" % (n.split()[0], 100 * np.mean([(b[c][M] - f[c][M]) / b[c][M] for c in ks]))
        print(s)


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 6)
    else:
        analyze()
