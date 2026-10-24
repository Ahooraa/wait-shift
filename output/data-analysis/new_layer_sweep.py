"""Open caveats on the no-B* controller (2026-10-22): busiest-first re-layout every 60 s + request moves, B* off ("rebal", the
reference; request moves capped at 300 per round). Every variant changes ONE thing. 18 cases each (F1/F2 x 50/70/85% x seeds 1-3).
Files <case>.O3S_h120_blind_nosim_nl_<variant>.json, in priority order:
  1 cap tuning        rm100, rm1000, rmall   request moves capped at 100 / 1000 / unlimited per round (reference 300)
  2 sizing rules      hpa, fifer, kraken     the published rules in place of busiest-first (cand mode), same request moves
  3 churn cap         cap100, cap200         re-layout limited to 100 / 200 container changes
  4 rule ablation     u0.7, u0.9, c60, c240, randplace   utilisation target 0.7 / 0.9, backlog clearing 60 / 240 s, random placement
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(ROOT))
import d3s_headroom as d  # noqa: E402

BASE = {"no_inner": True, "rebal": True, "rebal_max": 300}
VARIANTS = [  # (name, cand mode, churn changes)
    ("rm100", "nosim", {"rebal_max": 100}), ("rm1000", "nosim", {"rebal_max": 1000}), ("rmall", "nosim", {"rebal_max": 10 ** 9}),
    ("hpa", "hpa", {}), ("fifer", "fifer", {}), ("kraken", "kraken", {}),
    ("cap100", "nosim", {"cap": 100}), ("cap200", "nosim", {"cap": 200}),
    ("u0.7", "nosim", {"util_cap": 0.7}), ("u0.9", "nosim", {"util_cap": 0.9}),
    ("c60", "nosim", {"clear_s": 60.0}), ("c240", "nosim", {"clear_s": 240.0}), ("randplace", "nosim", {"placement": "random"}),
    ("jsq", "nosim", {"rebal_rule": "jsq"}), ("steal", "nosim", {"rebal_rule": "steal"}),   # queue-balancing baselines (2026-10-22)
]
GROUPS = {"cap": 3, "rules": 6, "churn": 8, "ablation": 13}

if __name__ == "__main__":
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 11
    upto = int(sys.argv[2]) if len(sys.argv) > 2 else len(VARIANTS)
    T = json.loads((d.OUT / "g2_tstar.json").read_text())
    T = {f: float(T["families"][f]["T_star"]) for f in ("F1", "F2")}
    jobs = []
    for name, cand, ch in VARIANTS[:upto]:
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
