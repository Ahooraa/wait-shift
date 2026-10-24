"""Step 1 diagnostic (2026-10-22): which of B*'s two actions carries busiest-first's gain?

B* does two things each round: (1) container swaps on single nodes, (2) moving waiting requests to the new container (and moving
queues off a node that lost its last instance of a function). Variants, busiest-first every 60 s, no foresight, F1/F2 x 70-85% load
x seeds 1-3 (12 cases each), files <case>.O3S_h120_blind_nosim_<variant>.json:
  log      busiest-first + B* exactly as the reference, with a per-round swap log (must reproduce the reference P99)
  swaps    B*'s container swaps only; its request moves are dropped (orphaned queues still rerouted)
  rebal    no B*; every B* period, waiting requests are moved to the node where they would finish earliest (up to 300 per round)

  python output/data-analysis/bstar_role_diag.py run [workers]
  python output/data-analysis/bstar_role_diag.py analyze
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

VARIANTS = {"log": {"log_swaps": True}, "swaps": {"swaps_only": True}, "rebal": {"no_inner": True, "rebal": True, "rebal_max": 300}}
LABELS = {"": "busiest-first + B* (reference)", "log": "reference re-run with swap log", "swaps": "B* container swaps only",
          "rebal": "request moves only (no B*)", "noinner": "re-layout only (no small moves)", "indep": "independent (count balancing)"}
M = "p99_makespan"


def run(workers):
    T = json.loads((d.OUT / "g2_tstar.json").read_text())
    T = {f: float(T["families"][f]["T_star"]) for f in ("F1", "F2")}
    jobs = []
    for name, churn in VARIANTS.items():
        for f in ("F1", "F2"):
            for r in (0.7, 0.85):
                for s in (1, 2, 3):
                    tg = d.tag(f, r, s)
                    jobs.append((tg, str(d.RUNS / f"{tg}.O3S_h120_blind_nosim_{name}.json"), s, T[f], d.DURATION, 60.0, 120.0, 5,
                                 True, None, "nosim", churn))
    jobs.sort(key=lambda j: -float(j[0].split("_r")[1].split("_")[0]))
    with ProcessPoolExecutor(workers) as ex:
        for done in ex.map(d.job, jobs):
            print("done", done, flush=True)


def analyze():
    from d1_rlla import BASE, D1, boot
    bstar = {}
    for d_ in (D1, BASE):
        for f in d_.glob("*.json"):
            x = json.loads(f.read_text())
            if x.get("ctrl") == "B_STAR":
                bstar[(x["family"], x["rho"], x["seed"])] = x["result"]
    runs = {}
    for v in LABELS:
        suf = "O3S_h120_blind_nosim" + (f"_{v}" if v else "")
        for f in d.RUNS.glob(f"*.{suf}.json"):
            x = json.loads(f.read_text())
            if x["rho"] > 0.5 and x["seed"] <= 3:
                runs.setdefault(v, {})[(x["family"], x["rho"], x["seed"])] = x
    ks = sorted(set.intersection(*(set(r) for r in runs.values())) & set(bstar))
    print(f"{len(ks)} cases common to all variants (70-85% load, F1/F2, seeds 1-3)")
    out = {}
    for v, lab in LABELS.items():
        g = [(bstar[k][M] - runs[v][k]["result"][M]) / bstar[k][M] for k in ks]
        res = [runs[v][k]["result"] for k in ks]
        row = dict(gain=boot(g), cold=float(np.mean([r["cold_starts"] for r in res])),
                   moved=float(np.mean([r["n_moved"] - r["n_rerouted"] for r in res])),
                   rerouted=float(np.mean([r["n_rerouted"] for r in res])), parked=float(np.mean([r["n_parked"] for r in res])))
        out[v] = row
        b = row["gain"]
        print(f"{lab:36s} P99 gain over B* {b['mean'] * 100:+6.1f}% ({b['lo'] * 100:+.0f} to {b['hi'] * 100:+.0f}) | cold starts {row['cold']:7.0f}"
              f" | requests moved by the small-move layer {row['moved']:7.0f} | forced reroutes {row['rerouted']:6.0f} | parked {row['parked']:5.0f}")
    b0 = [bstar[k] for k in ks]
    print(f"{'B* alone':36s} cold starts {np.mean([r['cold_starts'] for r in b0]):7.0f} | requests moved {np.mean([r['n_moved'] - r['n_rerouted'] for r in b0]):7.0f}")
    # swap log of the reference: when and what B* does
    rows = [r for k in ks for r in (runs["log"][k].get("swap_log") or [])]
    if rows:
        a = np.array([[np.nan if r[1] is None else r[1], r[2], r[3], r[4], r[5]] for r in rows], dtype=float)
        sw, mv = a[:, 1].sum(), a[:, 2].sum()
        print(f"swap log: {len(rows)} B* rounds, {sw:.0f} container changes, {mv:.0f} request moves")
        print(f"  container-change ends (one removal + one addition per change) that reverse the last re-layout: {a[:, 3].sum() / max(2 * sw, 1):.0%}; to functions with a backlog: {a[:, 4].sum() / max(sw, 1):.0%}")
        for lo, hi in ((0, 10), (10, 20), (20, 40), (40, 61)):
            m = (a[:, 0] >= lo) & (a[:, 0] < hi)
            print(f"  {lo:2d}-{hi:2d} s after a re-layout: {m.sum():5d} rounds, {a[m, 1].mean() if m.any() else 0:6.1f} container changes"
                  f" and {a[m, 2].mean() if m.any() else 0:6.1f} request moves per round")
        out["swap_log"] = dict(rounds=len(rows), swaps=float(sw), moves=float(mv), undo_share=float(a[:, 3].sum() / max(2 * sw, 1)),
                               to_backlog_share=float(a[:, 4].sum() / max(sw, 1)))
    (d.OUT / "bstar_role_diag.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 11)
    else:
        analyze()
