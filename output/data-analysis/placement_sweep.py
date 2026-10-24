"""Placement variants in the simulator (2026-10-23). Same controller as the reference (busiest-first re-layout every 60 s, no B*,
finish-time request moves cap 300); only the rule that chooses WHICH NODES get the containers changes.
  km          incremental weighted k-median + improvement pass (offline: -58% conversions, -38% transfer cost)
  km_noimp    the same without the improvement pass (isolates the pass)
  km_scratch  k-median from scratch each minute (offline: -68% transfer cost, +56% conversions)
  km_noorig   incremental + improvement, origins not counted as demand points (ablates origin-awareness)
18 development cases (F1/F2 x 50/70/85% x seeds 1-3). Files <case>.O3S_h120_blind_nosim_nl_<variant>.json
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(ROOT))
import d3s_headroom as d  # noqa: E402
from new_layer_sweep import BASE  # noqa: E402

KM = {"placement": "kmedian"}
VARIANTS = {
    "km": dict(KM, improve=300, origin_weight=1.0),
    "km_noimp": dict(KM, improve=0, origin_weight=1.0),
    "km_scratch": dict(KM, improve=300, origin_weight=1.0, incremental=False),
    "km_noorig": dict(KM, improve=300, origin_weight=0.0),
    # decisive test (2026-10-23): is the reference placement's advantage its layout, or the request redistribution its churn
    # forces? (reference 11,770 forced reroutes per run vs 1,324 for k-median). Same k-median layout, request moves unlimited;
    # compare with the reference at an unlimited cap (nl_rmall).
    "km_rmall": dict(KM, improve=0, origin_weight=1.0, rebal_max=10 ** 9),
}

if __name__ == "__main__":
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 11
    only = sys.argv[2].split(",") if len(sys.argv) > 2 else list(VARIANTS)
    T = json.loads((d.OUT / "g2_tstar.json").read_text())
    T = {f: float(T["families"][f]["T_star"]) for f in ("F1", "F2")}
    jobs = []
    for name in only:
        part = []
        for f in ("F1", "F2"):
            for r in d.RHOS:
                for s in (1, 2, 3):
                    tg = d.tag(f, r, s)
                    part.append((tg, str(d.RUNS / f"{tg}.O3S_h120_blind_nosim_nl_{name}.json"), s, T[f], d.DURATION, 60.0,
                                 120.0, 5, True, None, "nosim", dict(BASE, **VARIANTS[name])))
        part.sort(key=lambda j: -float(j[0].split("_r")[1].split("_")[0]))
        jobs += part
    with ProcessPoolExecutor(workers) as ex:
        for done in ex.map(d.job, jobs):
            print("done", done, flush=True)
