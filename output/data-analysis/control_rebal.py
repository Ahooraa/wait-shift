"""Control 1 + 50% load (2026-10-22): is the gain from busiest-first's re-layout, or from moving waiting requests alone?

Variants (no foresight, F1/F2 x 50/70/85% load x seeds 1-3; files <case>.O3S_h120_blind_nosim_<variant>.json):
  rebal        busiest-first re-layout every 60 s + request moves, no B*   (70-85% already run by bstar_role_diag.py; adds 50%)
  bstar_rebal  NO re-layout: B* as usual + request moves after each B* round
  x0_rebal     NO re-layout, NO B*: the initial NSGA-II placement stays fixed, only request moves
Request moves: every B* period, waiting requests go to the node where they would finish earliest, up to 300 per round.

  python output/data-analysis/control_rebal.py run [workers]
  python output/data-analysis/control_rebal.py analyze
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

RB = {"rebal": True, "rebal_max": 300}
VARIANTS = {"rebal": dict(RB, no_inner=True), "bstar_rebal": dict(RB, no_relayout=True),
            "x0_rebal": dict(RB, no_relayout=True, no_inner=True)}
LABELS = {"": "busiest-first + B* (old reference)", "rebal": "busiest-first + request moves (no B*)",
          "bstar_rebal": "B* + request moves (no re-layout)", "x0_rebal": "fixed initial placement + request moves"}
EX = ("B_STAR", "RL", "RL_CAL", "HEU")
M = "p99_makespan"


def run(workers):
    T = json.loads((d.OUT / "g2_tstar.json").read_text())
    T = {f: float(T["families"][f]["T_star"]) for f in ("F1", "F2")}
    jobs = []
    for name, churn in VARIANTS.items():
        for f in ("F1", "F2"):
            for r in d.RHOS:
                for s in (1, 2, 3):
                    tg = d.tag(f, r, s)
                    jobs.append((tg, str(d.RUNS / f"{tg}.O3S_h120_blind_nosim_{name}.json"), s, T[f], d.DURATION, 60.0, 120.0, 5,
                                 True, None, "nosim", churn))
    jobs.sort(key=lambda j: -float(j[0].split("_r")[1].split("_")[0]))
    with ProcessPoolExecutor(workers) as ex:
        for done in ex.map(d.job, jobs):                               # existing files are skipped by d.job
            print("done", done, flush=True)


def analyze():
    from d1_rlla import BASE, D1, boot
    base = {}
    for d_ in (D1, BASE):
        for f in d_.glob("*.json"):
            x = json.loads(f.read_text())
            if x.get("ctrl") in EX:
                base.setdefault((x["family"], x["rho"], x["seed"]), {})[x["ctrl"]] = x["result"]
    runs = {}
    for v in LABELS:
        suf = "O3S_h120_blind_nosim" + (f"_{v}" if v else "")
        for f in d.RUNS.glob(f"*.{suf}.json"):
            x = json.loads(f.read_text())
            if x["seed"] <= 3 and x["family"] in ("F1", "F2"):
                runs.setdefault(v, {})[(x["family"], x["rho"], x["seed"])] = x["result"]
    p = lambda b: f"{b['mean'] * 100:+6.1f}% ({b['lo'] * 100:+.0f} to {b['hi'] * 100:+.0f})"  # noqa: E731
    out = {}
    for rhos, rl in (((0.5,), "50% load"), ((0.7, 0.85), "70-85% load"), ((0.5, 0.7, 0.85), "all loads")):
        ks = sorted(k for k in set.intersection(*(set(r) for r in runs.values())) if k[1] in rhos and k in base and "B_STAR" in base[k])
        print(f"=== {rl}: {len(ks)} cases ===")
        for v, lab in LABELS.items():
            vb, ve = [], []
            for k in ks:
                b = base[k]["B_STAR"][M]
                be = min(base[k][m][M] for m in EX if m in base[k])
                r = runs[v][k][M]
                vb.append((b - r) / b)
                ve.append((be - r) / be)
            row = dict(n=len(ks), vs_bstar=boot(vb), vs_best=boot(ve), wins_vs_best=int(sum(x > 0 for x in ve)),
                       cold=float(np.mean([runs[v][k]["cold_starts"] for k in ks])))
            out[f"{v}|{rl}"] = row
            print(f"{lab:42s} vs B* {p(row['vs_bstar'])} | vs best existing {p(row['vs_best'])} wins {row['wins_vs_best']:2d}/{len(ks)}"
                  f" | cold starts {row['cold']:7.0f}")
        for m in EX:
            have = [k for k in ks if m in base[k]]
            if have:
                print(f"{m:42s} cold starts {np.mean([base[k][m].get('cold_starts', np.nan) for k in have]):7.0f} ({len(have)} cases)")
        # paired: busiest-first + moves vs the two no-re-layout controls
        for v in ("bstar_rebal", "x0_rebal"):
            dd = [(runs[v][k][M] - runs["rebal"][k][M]) / runs["rebal"][k][M] for k in ks]
            b = boot(dd)
            out[f"paired_rebal_vs_{v}|{rl}"] = dict(better_by=b, wins=int(sum(x > 0 for x in dd)))
            print(f"  paired: busiest-first + moves better than '{LABELS[v]}' by {p(b)}, wins {sum(x > 0 for x in dd)}/{len(ks)}")
    (d.OUT / "control_rebal.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 11)
    else:
        analyze()
