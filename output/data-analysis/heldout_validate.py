"""Held-out validation (2026-10-22): the FROZEN controller, run once, on seeds 4-10 that were never used while developing it.
Controller = busiest-first re-layout every 60 s (utilisation target 0.8, backlog cleared in 120 s, data-affinity placement), no B*,
request moves capped at 300 per round, no foresight (observed last 2 min only). Nothing is tuned on these seeds.
Reference set: B*, RL, RL_CAL for seeds 1-10 (Heu exists for seeds 1-3 only, so it is left out of 'best existing' here).
Cases: F1/F2 x 50/70/85% load x seeds 4-10 = 42. Files <case>.O3S_h120_blind_nosim_rebal.json (same suffix as the development run).

  python output/data-analysis/heldout_validate.py run [workers]
  python output/data-analysis/heldout_validate.py analyze
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

CHURN = {"no_inner": True, "rebal": True, "rebal_max": 300}
SEEDS = tuple(range(4, 11))
EX = ("B_STAR", "RL", "RL_CAL")
M = "p99_makespan"


def run(workers):
    T = json.loads((d.OUT / "g2_tstar.json").read_text())
    T = {f: float(T["families"][f]["T_star"]) for f in ("F1", "F2")}
    jobs = []
    for f in ("F1", "F2"):
        for r in d.RHOS:
            for s in SEEDS:
                tg = d.tag(f, r, s)
                jobs.append((tg, str(d.RUNS / f"{tg}.O3S_h120_blind_nosim_rebal.json"), s, T[f], d.DURATION, 60.0, 120.0, 5,
                             True, None, "nosim", CHURN))
    jobs.sort(key=lambda j: -float(j[0].split("_r")[1].split("_")[0]))
    with ProcessPoolExecutor(workers) as ex:
        for done in ex.map(d.job, jobs):
            print("done", done, flush=True)


def analyze():
    from d1_rlla import BASE, D1, boot
    base = {}
    for d_ in (D1, BASE):
        for f in d_.glob("*.json"):
            x = json.loads(f.read_text())
            if x.get("ctrl") in EX:
                base.setdefault((x["family"], x["rho"], x["seed"]), {})[x["ctrl"]] = x["result"]
    new = {}
    for f in d.RUNS.glob("*.O3S_h120_blind_nosim_rebal.json"):
        x = json.loads(f.read_text())
        new[(x["family"], x["rho"], x["seed"])] = x["result"]
    p = lambda b: f"{b['mean'] * 100:+6.1f}% ({b['lo'] * 100:+.0f} to {b['hi'] * 100:+.0f})"  # noqa: E731
    out = {}
    for tag_, seeds in (("held-out seeds 4-10", range(4, 11)), ("development seeds 1-3 (same reference set)", range(1, 4))):
        print(f"##### {tag_}")
        for fam in ("F1", "F2", "both"):
            for rhos, rl in (((0.5,), "50% load"), ((0.7, 0.85), "70-85% load"), ((0.5, 0.7, 0.85), "all loads")):
                ks = [k for k in new if k[2] in seeds and k[1] in rhos and (fam == "both" or k[0] == fam)
                      and all(m in base.get(k, {}) for m in EX)]
                if not ks:
                    continue
                vb = [(base[k]["B_STAR"][M] - new[k][M]) / base[k]["B_STAR"][M] for k in ks]
                be = {k: min(base[k][m][M] for m in EX) for k in ks}
                ve = [(be[k] - new[k][M]) / be[k] for k in ks]
                vr = [(base[k]["RL"][M] - new[k][M]) / base[k]["RL"][M] for k in ks]
                cold = float(np.mean([new[k]["cold_starts"] for k in ks]))
                row = dict(n=len(ks), vs_bstar=boot(vb), vs_rl=boot(vr), vs_best=boot(ve), wins_best=int(sum(x > 0 for x in ve)), cold=cold)
                out[f"{tag_}|{fam}|{rl}"] = row
                print(f"{fam:5s} {rl:12s} n={len(ks):2d} | vs B* {p(row['vs_bstar'])} | vs RL {p(row['vs_rl'])} | vs best {p(row['vs_best'])}"
                      f" wins {row['wins_best']:2d}/{len(ks)} | cold {cold:6.0f}")
    (d.OUT / "heldout_validate.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 11)
    else:
        analyze()
