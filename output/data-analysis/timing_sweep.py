"""Are re-layouts and request moves on time? (2026-10-24)

The layout-age test showed a re-layout applied 60 s late costs 44% in P99, so every source of delay matters. Three are checked here
against FROZEN-1 at 60 s (nl_qa_noqueue), on all 18 development cases:

  moves_now   the request moves run in the same tick as the re-layout. In FROZEN-1 the move step is skipped on a re-layout tick, so
              queued requests reach the new layout only one B* period later (4 s Azure, 8 s Huawei).
  delay5      the re-layout is applied 5 s after it is decided. The simulator charges no time for computing a re-layout (1-2 s of
              wall time measured) or for the control plane; this checks whether a realistic small lag matters.
  window60    the re-layout sizes from the last 60 s of arrivals instead of 120 s: the information a re-layout uses is on average
              half its window old (60 s for the 120 s window), which is another kind of layout age.

Files <case>.O3S_h120_blind_nosim_nl_tim_<name>.json.
  python output/data-analysis/timing_sweep.py run [workers]  |  analyze
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

VARIANTS = {  # name -> (rate window = horizon, churn)
    "moves_now": (120.0, dict(FROZEN, moves_after_relayout=True)),
    "delay5": (120.0, dict(FROZEN, relayout_delay=5.0)),
    "window60": (60.0, dict(FROZEN)),
}
M = "p99_makespan"


def run(workers):
    T = json.loads((d.OUT / "g2_tstar.json").read_text())
    T = {f: float(T["families"][f]["T_star"]) for f in ("F1", "F2")}
    jobs = []
    for n, (hz, ch) in VARIANTS.items():
        for f in ("F1", "F2"):
            for r in d.RHOS:
                for s in (1, 2, 3):
                    tg = d.tag(f, r, s)
                    out = d.RUNS / f"{tg}.O3S_h120_blind_nosim_nl_tim_{n}.json"
                    if not out.exists():
                        jobs.append((tg, str(out), s, T[f], d.DURATION, 60.0, hz, 5, True, None, "nosim", dict(ch)))
    jobs.sort(key=lambda j: -float(j[0].split("_r")[1].split("_")[0]))
    print(f"{len(jobs)} runs", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        for done in ex.map(d.job, jobs):
            print("done", done, flush=True)


def analyze():
    from d1_rlla import boot
    def load(s):
        o = {}
        for f in d.RUNS.glob(f"*.O3S_h120_blind_nosim_{s}.json"):
            x = json.loads(f.read_text())
            if x["seed"] <= 3:
                o[(x["family"], x["rho"], x["seed"])] = x["result"]
        return o
    ref = load("nl_qa_noqueue")
    p = lambda b: f"{b['mean'] * 100:+6.1f}% ({b['lo'] * 100:+.0f} to {b['hi'] * 100:+.0f})"  # noqa: E731
    print("P99 change against FROZEN-1 at 60 s (negative = slower), development seeds\n")
    for n in VARIANTS:
        r = load(f"nl_tim_{n}")
        for lab, rh in (("all loads", (0.5, 0.7, 0.85)), ("50%", (0.5,)), ("70-85%", (0.7, 0.85))):
            ks = [k for k in r if k in ref and k[1] in rh]
            if not ks:
                continue
            g = [(ref[k][M] - r[k][M]) / ref[k][M] for k in ks]
            print("  %-10s %-10s n=%2d  P99 %s, better in %2d/%d | cold %5.0f vs %5.0f | moves/request %.2f vs %.2f" % (
                n, lab, len(ks), p(boot(g)), sum(x > 0 for x in g), len(ks), np.mean([r[k]["cold_starts"] for k in ks]),
                np.mean([ref[k]["cold_starts"] for k in ks]), np.mean([r[k]["n_moved"] / r[k]["n_completed"] for k in ks]),
                np.mean([ref[k]["n_moved"] / ref[k]["n_completed"] for k in ks])))


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 11)
    else:
        analyze()
