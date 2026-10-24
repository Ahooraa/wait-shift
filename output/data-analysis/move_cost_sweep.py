"""Bandwidth / move-cost sensitivity (2026-10-23): does the controller's gain survive if relocating a queued request is
genuinely expensive?

Why: the gain is produced by the request-move mechanism, and this simulator charges a relocation only its own transfer time --
there is no link contention, so the 41% of extra state volume the moves generate slows nothing else down, and P99 improves
monotonically as their cap is lifted (233.5 s at cap 100 -> 141.0 s unlimited). `Sim(move_cost=m)` charges every relocation m
times its nominal transfer time, for EVERY controller alike (our moves, B*'s moves and the forced reroutes), which is a
first-order stand-in for the contention the moves cause.

Runs, on the 18 development cases (F1/F2 x 50/70/85% x seeds 1-3):
  ours  k-median placement, request moves unlimited   at m = 2, 5          files <case>.O3S_h120_blind_nosim_nl_mc<m>.json
  ours  k-median placement, request moves cap 300     at m = 5             files <case>.O3S_h120_blind_nosim_nl_mc5cap.json
        -> does the best cap become finite once moving is priced?
  B*    the reference the gain is measured against    at m = 2, 5          files <case>.B_STAR_mc<m>.json
        (B* moves queued requests heavily itself, so the surcharge may cost it more than it costs us)

  python output/data-analysis/move_cost_sweep.py run [workers]
  python output/data-analysis/move_cost_sweep.py analyze
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
from new_layer_sweep import BASE  # noqa: E402

import yaml  # noqa: E402

from dfps.o3s import O3SimAdjuster  # noqa: E402
from dfps.sim import Sim  # noqa: E402
from dfps.variants import make_adjuster, sim_kwargs  # noqa: E402

ASSUME = yaml.safe_load((ROOT / "config" / "assumptions.yaml").read_text(encoding="utf-8"))
KM = dict(BASE, placement="kmedian", improve=0, origin_weight=1.0, rebal_max=10 ** 9)
OURS = {"mc2": (2.0, KM), "mc5": (5.0, KM), "mc5cap": (5.0, dict(KM, rebal_max=300))}
FACTORS = (2.0, 5.0)


def bstar_job(args):
    """B* alone under a move-cost factor (same scenario, seeds and window as results/d1_headroom)."""
    tg, out_path, seed, period, m = args
    if Path(out_path).exists():
        return out_path
    assert np.__version__.startswith("1."), "run with the Anaconda interpreter (numpy 1.26)"
    try:
        sc = pickle.load(open(d.D1 / f"{tg}.pkl", "rb"))
        P = pickle.load(open(d.D1 / f"{tg}.prep.pkl", "rb"))
        kw = sim_kwargs("B_STAR", ASSUME)
        kw.update(warmup=d.WARMUP, duration=d.DURATION, retry_min_interval=1.0, retry_max_attempts=10,
                  interval=float(period), move_cost=m)
        t = time.time()
        sim = Sim(sc, P["X0"], adjuster=make_adjuster("B_STAR", ASSUME, seed=seed + 300), seed=seed + 400, **kw)
        r = sim.run()
        sim.check_invariants()
        r["wall_s"] = time.time() - t
        Path(out_path).write_text(json.dumps(dict(family=sc.meta["family"], rho=sc.meta["rho"], seed=seed, ctrl="B_STAR",
                                                  period=period, result=r, move_cost=m)))
        return out_path
    except Exception:
        import traceback
        Path(out_path).with_suffix(".err").write_text(traceback.format_exc())
        return out_path + " FAILED"


def ours_job(args):
    """Our controller under a move-cost factor: d3s_headroom._job with move_cost patched into Sim."""
    import dfps.sim as S
    m = args[-1]
    real = S.Sim.__init__

    def init(self, *a, **k):
        k.setdefault("move_cost", m)
        return real(self, *a, **k)
    S.Sim.__init__ = init
    try:
        return d.job(args[:-1])
    finally:
        S.Sim.__init__ = real


def run(workers):
    T = json.loads((d.OUT / "g2_tstar.json").read_text())
    T = {f: float(T["families"][f]["T_star"]) for f in ("F1", "F2")}
    cases = [(f, r, s) for f in ("F1", "F2") for r in d.RHOS for s in (1, 2, 3)]
    cases.sort(key=lambda c: -c[1])
    ours, bst = [], []
    for name, (m, churn) in OURS.items():
        for f, r, s in cases:
            tg = d.tag(f, r, s)
            ours.append((tg, str(d.RUNS / f"{tg}.O3S_h120_blind_nosim_nl_{name}.json"), s, T[f], d.DURATION, 60.0, 120.0, 5,
                         True, None, "nosim", churn, m))
    for m in FACTORS:
        for f, r, s in cases:
            tg = d.tag(f, r, s)
            bst.append((tg, str(d.RUNS / f"{tg}.B_STAR_mc{int(m)}.json"), s, T[f], m))
    with ProcessPoolExecutor(workers) as ex:
        for done in ex.map(bstar_job, bst):                       # B* first: it is the reference every number needs
            print("done", done, flush=True)
        for done in ex.map(ours_job, ours):
            print("done", done, flush=True)


def analyze():
    from d1_rlla import BASE as B1, D1, boot
    M = "p99_makespan"
    base = {}
    for d_ in (D1, B1):
        for f in d_.glob("*.json"):
            x = json.loads(f.read_text())
            if x.get("ctrl") in ("B_STAR", "RL", "RL_CAL"):
                base.setdefault((x["family"], x["rho"], x["seed"]), {})[x["ctrl"]] = x["result"]

    def load(pat, key="result"):
        out = {}
        for f in d.RUNS.glob(pat):
            x = json.loads(f.read_text())
            if x["seed"] <= 3:
                out[(x["family"], x["rho"], x["seed"])] = x[key]
        return out
    ours = {1: load("*.O3S_h120_blind_nosim_nl_km_rmall.json"), 2: load("*.O3S_h120_blind_nosim_nl_mc2.json"),
            5: load("*.O3S_h120_blind_nosim_nl_mc5.json")}
    ours_cap = load("*.O3S_h120_blind_nosim_nl_mc5cap.json")
    bst = {1: {k: v["B_STAR"] for k, v in base.items() if "B_STAR" in v}, 2: load("*.B_STAR_mc2.json"),
           5: load("*.B_STAR_mc5.json")}
    p = lambda b: f"{b['mean'] * 100:+6.1f}% ({b['lo'] * 100:+.0f} to {b['hi'] * 100:+.0f})"  # noqa: E731
    out = {}
    print("move cost = how many times its nominal transfer time each relocation is charged (1 = as published)\n")
    print("%-12s %10s %10s %12s %10s %10s" % ("move cost", "ours P99", "B* P99", "ours vs B*", "ours moves", "B* moves"))
    for m in (1, 2, 5):
        ks = sorted(set(ours[m]) & set(bst[m]))
        if not ks:
            continue
        g = [(bst[m][k][M] - ours[m][k][M]) / bst[m][k][M] for k in ks]
        row = dict(n=len(ks), ours=float(np.mean([ours[m][k][M] for k in ks])), bstar=float(np.mean([bst[m][k][M] for k in ks])),
                   gain=boot(g), wins=int(sum(x > 0 for x in g)),
                   ours_moves=float(np.mean([ours[m][k]["n_moved"] for k in ks])),
                   bstar_moves=float(np.mean([bst[m][k]["n_moved"] for k in ks])),
                   ours_cold=float(np.mean([ours[m][k]["cold_starts"] for k in ks])))
        out[f"m{m}"] = row
        print("%-12s %10.1f %10.1f %12s %10.0f %10.0f   wins %d/%d" % (m, row["ours"], row["bstar"], p(row["gain"]),
                                                                       row["ours_moves"], row["bstar_moves"], row["wins"], len(ks)))
    ks = sorted(set(ours_cap) & set(ours[5]) & set(bst[5]))
    if ks:
        d_cap = [(ours[5][k][M] - ours_cap[k][M]) / ours[5][k][M] for k in ks]
        g = [(bst[5][k][M] - ours_cap[k][M]) / bst[5][k][M] for k in ks]
        out["m5cap300"] = dict(n=len(ks), p99=float(np.mean([ours_cap[k][M] for k in ks])), vs_unlimited=boot(d_cap),
                               gain=boot(g), moves=float(np.mean([ours_cap[k]["n_moved"] for k in ks])))
        print(f"\nat move cost 5, capping request moves at 300: P99 {np.mean([ours_cap[k][M] for k in ks]):.1f} s"
              f" | better than unlimited by {p(boot(d_cap))} (wins {sum(x > 0 for x in d_cap)}/{len(ks)})"
              f" | vs B* {p(boot(g))} | moves {np.mean([ours_cap[k]['n_moved'] for k in ks]):.0f}")
        print("  -> a finite cap wins once moving is priced" if boot(d_cap)["lo"] > 0 else
              "  -> no finite cap needed even when moving is priced")
    (d.OUT / "move_cost_sweep.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 11)
    else:
        analyze()
