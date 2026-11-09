"""FROZEN-2 = FROZEN-1 + two small changes, decided 2026-10-24 on development seeds (user decision after the timing test).

  1 moves immediately after a re-layout   FROZEN-1 skipped the request-move step on the tick that applies a re-layout, so queued
                                          requests reached the new layout one move period later. Timing test (16 dev cases): P99
                                          +1.7% (+1 to +3), better in 12/16, cold starts unchanged.
  2 request-move period 4 s on both families   The period was B*'s tuned replacement period T* (4 s Azure, 8 s Huawei), inherited
                                          because the moves run on the clock B*'s annealing used. The moves are cheap, so the same
                                          4 s is used for Huawei. B* itself keeps its own tuned period (8 s on Huawei) in every
                                          comparison; only our controller's move clock changes.
Everything else is FROZEN-1 (re-layout every 60 s, soft-routing placement without the waiting term, unlimited moves, fixed slot
budget, no foresight). Cadence stays 60 s; the 30 s variant is reported separately as before.

This module is the single definition of the configuration; scripts import FROZEN2 and MOVE_PERIOD_S.

  python output/data-analysis/frozen2.py run [workers]   |   analyze      (development seeds 1-3, all loads: 18 runs)
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

FROZEN2 = dict(FROZEN, moves_after_relayout=True)
MOVE_PERIOD_S = {"F1": 4.0, "F2": 4.0}
# FROZEN-3 (2026-11-04, user decision; CAP-W1): FROZEN-2 + the gain-ordered request-move pass. Use it with the transfer_only
# dispatcher (dispatchers.DISPATCHERS[FROZEN3_DISPATCHER]), the router chosen the same day. Both choices are DESIGN DECISIONS taken
# after pre-registered confirmations that were NOT CONFIRMED on P99 (knowledge/synthesis/workflow-aware-decision-rules.md):
# gain order cuts moves ~8% (24 of 24 cases) and the median makespan 1.5-2% (24 of 24), P99 1.003 [0.984, 1.026], not shown within 2%.
FROZEN3_EXACT = dict(FROZEN2, pass_order="gain")        # the controller of every result before 7 Nov 2026 (exact re-layout, MV-2 engine)
# DEFAULT since 8 Nov 2026 (user decision): FROZEN3_EXACT + the MV-3 request mover (fast_order). MV-3 is exact: event hashes equal MV-2.
# The re-layout keeps its EXACT scoring (PL-1). Lazy scoring (FROZEN3_LAZY, PL-2) and thinning (place_thin = 32, PL-3) are scale-only switches:
# lazy cost P99 x1.093 [1.034, 1.166] on the 24 held-out cases (x1.004 on the 18 development cases), see independent-baselines-capw1, section 9.
FROZEN3_PL1 = dict(FROZEN3_EXACT, fast_order=True)         # MV-3 mover + the original exact scoring (PL-1): the reference for the headline results
# DEFAULT since 8 Nov 2026 (user decision): MV-3 + incremental scoring (PL-4). Same greedy and formula as PL-1, equal up to floating-point ties.
FROZEN3 = dict(FROZEN3_PL1, incr_place=True)
FROZEN3_INCR = FROZEN3               # PL-4: exact formula, incremental sums, priced only where the container fits; under test 8 Nov 2026
FROZEN3_LAZY = dict(FROZEN3_PL1, lazy_place=True)               # scale-only: re-layout under 3 s at ~1,280 servers; not the default
# FROZEN-4 (9 Nov 2026, user decision; the paper's controller): FROZEN-3 with the shortfall-first re-layout fill (PL-5: the function furthest below
# its target goes next, one container per pricing). DIFFERENT decisions from PL-4, hence a new controller version. FROZEN3 above stays as it was, so its results remain reproducible.
FROZEN4 = dict(FROZEN3, fill_order="shortfall")                 # PL-5: one container per pricing
FROZEN4_P8 = dict(FROZEN4, fill_passes=8)                       # PL-5p: 8 passes, the scale option
FROZEN3_FILL, FROZEN3_FILL8 = FROZEN4, FROZEN4_P8               # the names used while under test (arms fill1 = FROZEN-4, fill8 = its 8-pass option)
FROZEN3_DISPATCHER = "transfer_only"
FROZEN4_DISPATCHER = FROZEN3_DISPATCHER
M = "p99_makespan"


def jobs(cases, name, epoch=60.0):
    return [(d.tag(f, r, s), str(d.RUNS / f"{d.tag(f, r, s)}.O3S_h120_blind_nosim_nl_{name}.json"), s, MOVE_PERIOD_S[f], d.DURATION,
             float(epoch), 120.0, 5, True, None, "nosim", dict(FROZEN2)) for f, r, s in cases]


def run(workers):
    cs = [(f, r, s) for f in ("F1", "F2") for r in d.RHOS for s in (1, 2, 3)]
    todo = [j for j in jobs(cs, "fz2_60") if not Path(j[1]).exists()]
    todo.sort(key=lambda j: -float(j[0].split("_r")[1].split("_")[0]))
    print(f"{len(todo)} runs", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        for done in ex.map(d.job, todo):
            print("done", done, flush=True)


def analyze():
    from d1_rlla import BASE, D1, boot
    base = {}
    for d_ in (D1, BASE):
        for f in d_.glob("*.json"):
            x = json.loads(f.read_text())
            if x.get("ctrl") in ("B_STAR", "RL", "RL_CAL"):
                base.setdefault((x["family"], x["rho"], x["seed"]), {})[x["ctrl"]] = x["result"][M]

    def load(s):
        o = {}
        for f in d.RUNS.glob(f"*.O3S_h120_blind_nosim_{s}.json"):
            x = json.loads(f.read_text())
            if x["seed"] <= 3:
                o[(x["family"], x["rho"], x["seed"])] = x["result"]
        return o
    a, b = load("nl_qa_noqueue"), load("nl_fz2_60")
    p = lambda v: f"{v['mean'] * 100:+6.1f}% ({v['lo'] * 100:+.0f} to {v['hi'] * 100:+.0f})"  # noqa: E731
    print("FROZEN-2 vs FROZEN-1 (both 60 s cadence), development seeds 1-3; positive = FROZEN-2 faster\n")
    for lab, sel in (("all loads", lambda k: True), ("50% load", lambda k: k[1] == 0.5), ("70-85% load", lambda k: k[1] > 0.5),
                     ("Azure (same 4 s period as before)", lambda k: k[0] == "F1"), ("Huawei (period 8 s -> 4 s)", lambda k: k[0] == "F2")):
        ks = [k for k in b if k in a and sel(k)]
        if not ks:
            continue
        g = [(a[k][M] - b[k][M]) / a[k][M] for k in ks]
        be = [min(base[k].values()) for k in ks]
        print("  %-36s n=%2d  P99 change %s, better in %2d/%d | vs best existing: FROZEN-2 %+5.1f%% (FROZEN-1 %+5.1f%%) | cold %5.0f vs %5.0f | moves/request %.2f vs %.2f" % (
            lab, len(ks), p(boot(g)), sum(x > 0 for x in g), len(ks), 100 * np.mean([(x - b[k][M]) / x for x, k in zip(be, ks)]),
            100 * np.mean([(x - a[k][M]) / x for x, k in zip(be, ks)]), np.mean([b[k]["cold_starts"] for k in ks]),
            np.mean([a[k]["cold_starts"] for k in ks]), np.mean([b[k]["n_moved"] / b[k]["n_completed"] for k in ks]),
            np.mean([a[k]["n_moved"] / a[k]["n_completed"] for k in ks])))


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 6)
    else:
        analyze()
