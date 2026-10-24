"""Does a 30 s re-layout cadence help at 50% load, without selecting the cases? (2026-10-23)

hard50.py found that re-laying out every 30 s instead of 60 s cut P99 by 9.2% (+1 to +19, 5 of 6 better) on the SIX HARDEST 50%-load
cases, with 8% more cold starts. Those cases were chosen because they were hard, so the gain is probably overstated (regression to
the mean). This runs the final controller (busiest-first sizing, incremental k-median placement, finish-time request moves with no
cap, no B*) at 30 s and 60 s on ALL 20 cases at 50% load (Azure and Huawei, seeds 1-10) and reports the six hard cases and the
fourteen others separately.

Files <case>.O3S_h120_blind_nosim_nl_hardE30 / hardE60 .json (names shared with hard50.py; existing files are skipped). For seeds
1-3 the 60 s run is the same configuration as nl_km_rmall, so that result is copied instead of recomputed.

  python output/data-analysis/cadence_sweep.py run [workers]   |   analyze
"""
import json
import shutil
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(ROOT))
import d3s_headroom as d  # noqa: E402
from hard50 import FINAL, HARD  # noqa: E402

CASES = [(f, s) for f in ("F1", "F2") for s in range(1, 11)]
M = "p99_makespan"


def run(workers):
    d.RUNS.mkdir(parents=True, exist_ok=True)
    T = json.loads((d.OUT / "g2_tstar.json").read_text())
    T = {f: float(T["families"][f]["T_star"]) for f in ("F1", "F2")}
    for fam, s in CASES:                                              # seeds 1-3 at 60 s = nl_km_rmall (same configuration)
        src = d.RUNS / f"{d.tag(fam, 0.5, s)}.O3S_h120_blind_nosim_nl_km_rmall.json"
        dst = d.RUNS / f"{d.tag(fam, 0.5, s)}.O3S_h120_blind_nosim_nl_hardE60.json"
        if s <= 3 and src.exists() and not dst.exists():
            shutil.copyfile(src, dst)
    jobs = []
    for e in (30, 60):
        for fam, s in CASES:
            tg = d.tag(fam, 0.5, s)
            jobs.append((tg, str(d.RUNS / f"{tg}.O3S_h120_blind_nosim_nl_hardE{e}.json"), s, T[fam], d.DURATION, float(e), 120.0, 5,
                         True, None, "nosim", dict(FINAL)))
    todo = [j for j in jobs if not Path(j[1]).exists()]
    print(f"{len(todo)} runs to do ({len(jobs) - len(todo)} already exist)", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        for done in ex.map(d.job, todo):
            print("done", done, flush=True)


def analyze():
    from d1_rlla import BASE as B1, D1, boot
    base = {}
    for d_ in (D1, B1):
        for f in d_.glob("*.json"):
            x = json.loads(f.read_text())
            if x.get("ctrl") in ("B_STAR", "RL"):
                base.setdefault((x["family"], x["rho"], x["seed"]), {})[x["ctrl"]] = x["result"]
    r = {30: {}, 60: {}}
    for e in (30, 60):
        for fam, s in CASES:
            f = d.RUNS / f"{d.tag(fam, 0.5, s)}.O3S_h120_blind_nosim_nl_hardE{e}.json"
            if f.exists():
                r[e][(fam, s)] = json.loads(f.read_text())["result"]
    ks = sorted(set(r[30]) & set(r[60]))
    hard = set(HARD)
    p = lambda b: f"{b['mean'] * 100:+6.1f}% ({b['lo'] * 100:+.0f} to {b['hi'] * 100:+.0f})"  # noqa: E731
    print(f"{len(ks)} of 20 cases at 50% load have both cadences\n")
    print("%-34s %3s | %-26s %5s | %7s %7s | %6s %6s" % ("subset", "n", "P99 gain of 30 s over 60 s", "wins", "P99 30", "P99 60", "cold30", "cold60"))
    out = {}
    for lab, sel in (("all cases", lambda k: True), ("the 6 hard cases (selected)", lambda k: k in hard),
                     ("the 14 others (not selected)", lambda k: k not in hard), ("Azure", lambda k: k[0] == "F1"), ("Huawei", lambda k: k[0] == "F2")):
        kk = [k for k in ks if sel(k)]
        if not kk:
            continue
        g = [(r[60][k][M] - r[30][k][M]) / r[60][k][M] for k in kk]
        b = boot(g)
        out[lab] = dict(n=len(kk), gain=b, wins=int(sum(x > 0 for x in g)))
        print("%-34s %3d | %-26s %2d/%2d | %7.1f %7.1f | %6.0f %6.0f" % (lab, len(kk), p(b), sum(x > 0 for x in g), len(kk),
              np.mean([r[30][k][M] for k in kk]), np.mean([r[60][k][M] for k in kk]),
              np.mean([r[30][k]["cold_starts"] for k in kk]), np.mean([r[60][k]["cold_starts"] for k in kk])))
    print("\nagainst the best existing method at 50% load (B*, RL), P99 gain, all cases with a reference:")
    for e in (60, 30):
        kk = [k for k in ks if (k[0], 0.5, k[1]) in base and "RL" in base[(k[0], 0.5, k[1])]]
        be = [min(base[(k[0], 0.5, k[1])]["B_STAR"][M], base[(k[0], 0.5, k[1])]["RL"][M]) for k in kk]
        g = [(b_ - r[e][k][M]) / b_ for b_, k in zip(be, kk)]
        b = boot(g)
        out[f"vs_best_E{e}"] = dict(n=len(kk), gain=b, wins=int(sum(x > 0 for x in g)))
        print("  cadence %2d s: %s, wins %d/%d" % (e, p(b), sum(x > 0 for x in g), len(kk)))
    (d.OUT / "cadence_sweep.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 6)
    else:
        analyze()
