"""Churn trade-off sweep for the busiest-first rule (user concern 2026-10-21: re-layout every minute costs migration / cold starts).

All variants: busiest-first ('nosim'), no future knowledge (--blind), Azure + Huawei, seeds 1-3, 3 loads = 18 cases each, run in ONE
process pool so the 11 variants x 18 cases balance across workers. Variant files: <case>.O3S_h120_blind_nosim_<variant>.json
Reference (already run): every-minute busiest-first = O3S_h120_blind_nosim, B*, RL.

  noinner   B*'s annealing swaps switched off (busiest-first is the only thing changing the layout)
  frac0.4/0.6   skip a re-layout unless at least 40% / 60% of all container slots would change
  cap50/100/200 change at most that many containers per re-layout (largest function gaps first)
  E120/180/300  re-layout every 120 / 180 / 300 s instead of 60 s
  bl1.0/2.0     skip a re-layout unless queued runs reach 1.0x / 2.0x the number of container slots
"""
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(ROOT))
import d3s_headroom as d  # noqa: E402

VARIANTS = {
    "noinner": (60.0, {"no_inner": True}),
    "frac0.4": (60.0, {"min_frac": 0.4}), "frac0.6": (60.0, {"min_frac": 0.6}),
    "cap50": (60.0, {"cap": 50}), "cap100": (60.0, {"cap": 100}), "cap200": (60.0, {"cap": 200}),
    "E120": (120.0, {}), "E180": (180.0, {}), "E300": (300.0, {}),
    "bl1.0": (60.0, {"min_backlog": 1.0}), "bl2.0": (60.0, {"min_backlog": 2.0}),
}

if __name__ == "__main__":
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    T = json.loads((d.OUT / "g2_tstar.json").read_text())
    T = {f: float(T["families"][f]["T_star"]) for f in ("F1", "F2")}
    jobs = []
    for name, (epoch, churn) in VARIANTS.items():
        for f in ("F1", "F2"):
            for r in d.RHOS:
                for s in (1, 2, 3):
                    tg = d.tag(f, r, s)
                    out = str(d.RUNS / f"{tg}.O3S_h120_blind_nosim_{name}.json")
                    jobs.append((tg, out, s, T[f], d.DURATION, epoch, 120.0, 5, True, None, "nosim", churn))
    jobs.sort(key=lambda j: -float(j[0].split("_r")[1].split("_")[0]))        # heaviest load first
    with ProcessPoolExecutor(workers) as ex:
        for done in ex.map(d.job, jobs):
            print("done", done, flush=True)
