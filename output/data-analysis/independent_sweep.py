"""Independent variant of busiest-first (2026-10-22): no B* underneath; its own small-move layer (dfps/o3s.py fine_step) instead.

Same cases as the churn sweep (F1/F2 x 3 loads x seeds 1-3, blind, 60 s re-layouts). Variants:
  indep       big re-layout every 60 s + up to 75 small moves every B* period (75 = what a B* round changes), no B*
  indep_cap200   same, with the re-layout capped at 200 containers
Files: <case>.O3S_h120_blind_nosim_<variant>.json
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(ROOT))
import d3s_headroom as d  # noqa: E402

VARIANTS = {"indep": {"no_inner": True, "fine": 75}, "indep_cap200": {"no_inner": True, "fine": 75, "cap": 200}}

if __name__ == "__main__":
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    T = json.loads((d.OUT / "g2_tstar.json").read_text())
    T = {f: float(T["families"][f]["T_star"]) for f in ("F1", "F2")}
    jobs = []
    for name, churn in VARIANTS.items():
        for f in ("F1", "F2"):
            for r in d.RHOS:
                for s in (1, 2, 3):
                    tg = d.tag(f, r, s)
                    out = str(d.RUNS / f"{tg}.O3S_h120_blind_nosim_{name}.json")
                    jobs.append((tg, out, s, T[f], d.DURATION, 60.0, 120.0, 5, True, None, "nosim", churn))
    jobs.sort(key=lambda j: -float(j[0].split("_r")[1].split("_")[0]))
    with ProcessPoolExecutor(workers) as ex:
        for done in ex.map(d.job, jobs):
            print("done", done, flush=True)
