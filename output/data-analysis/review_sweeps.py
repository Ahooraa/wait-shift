"""Experiments asked for by the second review (2026-10-24), on development seeds only (the held-out seeds stay reserved).

  age   Layout-age test: FROZEN-1 with every re-layout DECIDED on schedule but APPLIED 60 / 120 / 300 s late, request moves
        unlimited throughout (Sim-level: O3SimAdjuster churn 'relayout_delay'). This isolates a stale capacity layout from everything
        else and asks how gracefully the fast request moves degrade when the slow allocator is late. Delay 0 is FROZEN-1 itself
        (nl_qa_noqueue). Cases: 70-85% load (12), where the layout matters most.
  grid  The 2x2 re-run with the FROZEN-1 settings: cell B = fixed starting layout + request moves with NO cap (the earlier grid capped
        them at 300); cell C = re-layout with the soft-routing placement and no moves. Cell A (fixed layout, no moves) does not depend
        on placement or the cap and is reused (x0); cell D is FROZEN-1 (nl_qa_noqueue). Cases: all 18.

Files <case>.O3S_h120_blind_nosim_nl_<name>.json; existing files are skipped.

  python output/data-analysis/review_sweeps.py run [workers] [age,grid]  |  analyze
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(ROOT))
import d3s_headroom as d  # noqa: E402
from frozen_sweep import FROZEN  # noqa: E402

PLACE = {k: FROZEN[k] for k in ("placement", "origin_weight", "tau", "queue_term")}
AGE = {f"age{s}": dict(FROZEN, relayout_delay=float(s)) for s in (60, 120, 300)}
GRID = {"grid_B": dict(no_relayout=True, no_inner=True, rebal=True, rebal_max=10 ** 9),     # fixed layout + unlimited moves
        "grid_C": dict(PLACE, no_inner=True)}                                              # soft-routing re-layout, no moves
M = "p99_makespan"


def cases(rhos):
    return [(f, r, s) for f in ("F1", "F2") for r in rhos for s in (1, 2, 3)]


def run(workers, which):
    T = json.loads((d.OUT / "g2_tstar.json").read_text())
    T = {f: float(T["families"][f]["T_star"]) for f in ("F1", "F2")}
    plan = []
    if "age" in which:
        plan += [(n, ch, cases((0.85, 0.7))) for n, ch in AGE.items()]
    if "grid" in which:
        plan += [(n, ch, cases((0.85, 0.7, 0.5))) for n, ch in GRID.items()]
    jobs = []
    for n, ch, cs in plan:
        for f, r, s in cs:
            tg = d.tag(f, r, s)
            out = d.RUNS / f"{tg}.O3S_h120_blind_nosim_nl_{n}.json"
            if not out.exists():
                jobs.append((tg, str(out), s, T[f], d.DURATION, 60.0, 120.0, 5, True, None, "nosim", dict(ch)))
    print(f"{len(jobs)} runs", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        for done in ex.map(d.job, jobs):
            print("done", done, flush=True)


def load(suffix):
    o = {}
    for f in d.RUNS.glob(f"*.O3S_h120_blind_nosim_{suffix}.json"):
        x = json.loads(f.read_text())
        if x["seed"] <= 3:
            o[(x["family"], x["rho"], x["seed"])] = x["result"]
    return o


def analyze():
    from d1_rlla import boot
    p = lambda b: f"{b['mean'] * 100:+6.1f}% ({b['lo'] * 100:+.0f} to {b['hi'] * 100:+.0f})"  # noqa: E731
    ref = load("nl_qa_noqueue")
    print("=== Layout age: FROZEN-1 with re-layouts applied late (70-85% load, development seeds) ===")
    print("%-22s %3s | %8s | %-26s | %6s | %7s" % ("re-layout applied", "n", "P99 s", "P99 change vs on time", "cold", "parked"))
    ks0 = [k for k in ref if k[1] in (0.7, 0.85)]
    print("%-22s %3d | %8.1f | %-26s | %6.0f | %7.1f" % ("on time (FROZEN-1)", len(ks0), np.mean([ref[k][M] for k in ks0]), "—",
          np.mean([ref[k]["cold_starts"] for k in ks0]), np.mean([ref[k]["n_parked"] for k in ks0])))
    for n in AGE:
        r = load(f"nl_{n}")
        ks = [k for k in ks0 if k in r]
        if not ks:
            continue
        g = [(r[k][M] - ref[k][M]) / ref[k][M] for k in ks]
        print("%-22s %3d | %8.1f | %-26s | %6.0f | %7.1f" % (f"{n[3:]} s late", len(ks), np.mean([r[k][M] for k in ks]), p(boot(g)),
              np.mean([r[k]["cold_starts"] for k in ks]), np.mean([r[k]["n_parked"] for k in ks])))
    print("\n=== 2x2 with FROZEN-1 settings (all loads, development seeds; raw P99 seconds) ===")
    cells = {"A": load("x0"), "B": load("nl_grid_B"), "C": load("nl_grid_C"), "D": ref}
    ks = sorted(set.intersection(*(set(v) for v in cells.values())))
    if not ks:
        print("no complete cases yet")
        return
    lg = {c: np.log([v[k][M] for k in ks]) for c, v in cells.items()}
    for c, lab in (("A", "fixed layout, no moves"), ("B", "fixed layout + unlimited moves"), ("C", "soft-routing re-layout, no moves"),
                   ("D", "FROZEN-1 (both)")):
        print("  %s %-34s n=%2d  mean %7.1f  geo-mean %7.1f" % (c, lab, len(ks), np.mean([cells[c][k][M] for k in ks]), np.exp(lg[c].mean())))
    for lab, v in (("moves on a fixed layout (A to B)", lg["A"] - lg["B"]), ("moves with re-layout (C to D)", lg["C"] - lg["D"]),
                   ("re-layout without moves (A to C)", lg["A"] - lg["C"]), ("re-layout with moves (B to D)", lg["B"] - lg["D"])):
        b = boot(v)
        print("  %-36s x%.1f (x%.1f to x%.1f)" % (lab, np.exp(b["mean"]), np.exp(b["lo"]), np.exp(b["hi"])))
    b = boot((lg["A"] - lg["B"]) - (lg["C"] - lg["D"]))
    print("  interaction (log): %.2f (%.2f to %.2f)" % (b["mean"], b["lo"], b["hi"]))


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 6, sys.argv[3].split(",") if len(sys.argv) > 3 else ["age", "grid"])
    else:
        analyze()
