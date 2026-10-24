"""Request-move period (2026-10-24): is 4 s the right clock for the moves?  FROZEN-2 with the move period at 2 s on both families.

Halving the Huawei period from 8 s to 4 s gave +8.2% P99 (9/9 cases) while moves per request rose from 2.9 to 3.9 with cold starts
unchanged, so a shorter period may help further. Same 18 development cases, re-layout still every 60 s, moves right after a re-layout.
Compared with FROZEN-2 at 4 s (nl_fz2_60). File <case>.O3S_h120_blind_nosim_nl_fz2_p2.json.
  python output/data-analysis/period_sweep.py run [workers] | analyze
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
from frozen2 import FROZEN2  # noqa: E402

PERIOD = 2.0
M = "p99_makespan"


def run(workers):
    cs = [(f, r, s) for f in ("F1", "F2") for r in d.RHOS for s in (1, 2, 3)]
    jobs = [(d.tag(f, r, s), str(d.RUNS / f"{d.tag(f, r, s)}.O3S_h120_blind_nosim_nl_fz2_p2.json"), s, PERIOD, d.DURATION, 60.0, 120.0, 5,
             True, None, "nosim", dict(FROZEN2)) for f, r, s in cs]
    jobs = [j for j in jobs if not Path(j[1]).exists()]
    jobs.sort(key=lambda j: -float(j[0].split("_r")[1].split("_")[0]))
    print(f"{len(jobs)} runs", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        for done in ex.map(d.job, jobs):
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
    a, b = load("nl_fz2_60"), load("nl_fz2_p2")
    p = lambda v: f"{v['mean'] * 100:+6.1f}% ({v['lo'] * 100:+.0f} to {v['hi'] * 100:+.0f})"  # noqa: E731
    print("Move period 2 s vs 4 s (FROZEN-2), development seeds; positive = 2 s faster\n")
    for lab, sel in (("all loads", lambda k: True), ("50% load", lambda k: k[1] == 0.5), ("70-85% load", lambda k: k[1] > 0.5),
                     ("Azure", lambda k: k[0] == "F1"), ("Huawei", lambda k: k[0] == "F2")):
        ks = [k for k in b if k in a and sel(k)]
        if not ks:
            continue
        g = [(a[k][M] - b[k][M]) / a[k][M] for k in ks]
        be = [min(base[k].values()) for k in ks]
        print("  %-12s n=%2d  P99 %s, better in %2d/%d | vs best existing: 2 s %+5.1f%% (4 s %+5.1f%%) | cold %5.0f vs %5.0f | moves/request %.2f vs %.2f" % (
            lab, len(ks), p(boot(g)), sum(x > 0 for x in g), len(ks), 100 * np.mean([(x - b[k][M]) / x for x, k in zip(be, ks)]),
            100 * np.mean([(x - a[k][M]) / x for x, k in zip(be, ks)]), np.mean([b[k]["cold_starts"] for k in ks]),
            np.mean([a[k]["cold_starts"] for k in ks]), np.mean([b[k]["n_moved"] / b[k]["n_completed"] for k in ks]),
            np.mean([a[k]["n_moved"] / a[k]["n_completed"] for k in ks])))


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 6)
    else:
        analyze()
