"""Queue-balancing baselines (2026-10-22): same controller as the reference (busiest-first re-layout every 60 s, no B*, request moves
every B* period, cap 300) but the request-move rule is a textbook load balancer instead of the finish-time rule:
  jsq    join-the-shortest-queue          steal  work stealing
Development cases (F1/F2 x 50/70/85% x seeds 1-3 = 18 per rule). Files <case>.O3S_h120_blind_nosim_nl_<rule>.json; compare with
new_layer_compare.py."""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(ROOT))
import d3s_headroom as d  # noqa: E402
from new_layer_sweep import BASE, VARIANTS  # noqa: E402

if __name__ == "__main__":
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 11
    T = json.loads((d.OUT / "g2_tstar.json").read_text())
    T = {f: float(T["families"][f]["T_star"]) for f in ("F1", "F2")}
    jobs = []
    for name, cand, ch in [v for v in VARIANTS if v[0] in ("jsq", "steal")]:
        part = []
        for f in ("F1", "F2"):
            for r in d.RHOS:
                for s in (1, 2, 3):
                    tg = d.tag(f, r, s)
                    part.append((tg, str(d.RUNS / f"{tg}.O3S_h120_blind_nosim_nl_{name}.json"), s, T[f], d.DURATION, 60.0, 120.0, 5,
                                 True, None, cand, dict(BASE, **ch)))
        part.sort(key=lambda j: -float(j[0].split("_r")[1].split("_")[0]))
        jobs += part
    with ProcessPoolExecutor(workers) as ex:
        for done in ex.map(d.job, jobs):
            print("done", done, flush=True)
