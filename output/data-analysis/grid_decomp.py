"""One-at-a-time decomposition of the final controller (2026-11-02, user request after the timing study).

Question: which of the three mechanisms carries the gain over B* / the best existing method? The earlier 2x2 (grid2x2_v2.py) varies two
mechanisms jointly (moves + dispatch together). Here every mechanism is switched off alone, and switched on alone, from the same 18
development cases (F1/F2 x rho 0.5/0.7/0.85 x seeds 1-3). Cells A-D are the existing grid2x2_v2 runs (results/grid2x2_v2); the new cells:

  D   ours = re-layout + moves + dispatch                      (grid2x2_v2)
  E   ours - dispatch      re-layout + moves, FIFO              CHURN_OURS
  C2  ours - moves         re-layout + dispatch, no moves       CHURN_OURS, rebal=False, prio
  B   ours - re-layout     fixed layout + moves + dispatch      (grid2x2_v2)
  A   nothing adapts                                            (grid2x2_v2)
  G   A + dispatch only                                         no_inner, no_relayout, prio
  H   A + moves only (FIFO)                                     CHURN_OURS, no_relayout
  C   A + re-layout only                                        (grid2x2_v2)
  F   B*'s own layout search + our moves + dispatch             CHURN_OURS, no_relayout, no_inner=False, prio; period = B*'s T* (4 s Azure, 8 s Huawei)
  F4  same as F with a 4 s clock on Huawei (F2 only; F1 is identical to F)

Exploratory, development seeds; no pre-registered bar. Files results/grid_decomp/<case>.<cell>.json

  python output/data-analysis/grid_decomp.py run [workers]   |   analyze
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
import d3s_headroom as d  # noqa: E402
import grid2x2_v2 as g  # noqa: E402
from frozen2 import MOVE_PERIOD_S  # noqa: E402

RUNS = ROOT / "results" / "grid_decomp"
OLD = g.RUNS
M = g.M
OURS = g.CHURN_OURS
T_STAR = {"F1": 4.0, "F2": 8.0}                      # B*'s own tuned replacement period
NEW = {
    "E": (dict(OURS), MOVE_PERIOD_S),
    "C2": (dict(OURS, rebal=False, prio=True), MOVE_PERIOD_S),
    "F": (dict(OURS, no_relayout=True, no_inner=False, prio=True), T_STAR),
    "F4": (dict(OURS, no_relayout=True, no_inner=False, prio=True), MOVE_PERIOD_S),
    "G": (dict(no_inner=True, no_relayout=True, prio=True), MOVE_PERIOD_S),
    "H": (dict(OURS, no_relayout=True), MOVE_PERIOD_S),
}
ORDER = ("A", "G", "H", "C", "C2", "B", "E", "D", "F", "F4")


def jobs():
    out = []
    for c, (churn, per) in NEW.items():
        for f in g.FAMS:
            if c == "F4" and f == "F1":
                continue
            for r in g.RHOS:
                for s in g.SEEDS:
                    tg = d.tag(f, r, s)
                    out.append((tg, str(RUNS / f"{tg}.{c}.json"), s, per[f], churn))
    return out


def run(workers):
    RUNS.mkdir(parents=True, exist_ok=True)
    js = [j for j in jobs() if not Path(j[1]).exists()]
    js.sort(key=lambda j: -float(j[0].split("_r")[1].split("_")[0]))        # heavy loads first
    print(f"{len(js)} runs, {workers} workers", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        for done in ex.map(g.job, js):
            print("done", done, flush=True)


def load_cell(c):
    out = {}
    folder = OLD if c in ("A", "B", "C", "D") else RUNS
    for f in folder.glob(f"*.{c}.json"):
        x = json.loads(f.read_text())
        out[(x["family"], x["rho"], x["seed"])] = x["result"][M]
    return out


def analyze():
    from d1_rlla import BASE, D1, boot
    bstar, best = {}, {}
    for d_ in (D1, BASE):
        for f in d_.glob("*.json"):
            x = json.loads(f.read_text())
            if x["family"] in g.FAMS and x.get("ctrl") in ("B_STAR", "RL", "RL_CAL"):
                k = (x["family"], x["rho"], x["seed"])
                best[k] = min(best.get(k, np.inf), x["result"][M])
                if x["ctrl"] == "B_STAR":
                    bstar[k] = x["result"][M]
    runs = {c: load_cell(c) for c in ORDER}
    p = lambda b: f"{b['mean'] * 100:+6.1f}% ({b['lo'] * 100:+.0f} to {b['hi'] * 100:+.0f})"  # noqa: E731
    lab = {"A": "A  nothing adapts", "G": "G  dispatch only", "H": "H  moves only (FIFO)", "C": "C  re-layout only",
           "C2": "C2 re-layout + dispatch (no moves)", "B": "B  moves + dispatch (fixed layout)", "E": "E  re-layout + moves (FIFO)",
           "D": "D  ours: all three", "F": "F  B*'s layout + moves + dispatch", "F4": "F4 same, 4 s clock (Huawei)"}
    res = {}
    for rl, rhos, fams in (("all 18 cases", (0.5, 0.7, 0.85), ("F1", "F2")), ("70-85% load", (0.7, 0.85), ("F1", "F2")),
                           ("50% load", (0.5,), ("F1", "F2")), ("Azure (F1)", (0.5, 0.7, 0.85), ("F1",)), ("Huawei (F2)", (0.5, 0.7, 0.85), ("F2",))):
        print(f"\n=== {rl}: P99 gain over B* (positive = lower P99); over best existing; geometric-mean P99 ===")
        for c in ORDER:
            ks = sorted(k for k in runs[c] if k[1] in rhos and k[0] in fams and k in bstar)
            if not ks:
                continue
            gb = boot([(bstar[k] - runs[c][k]) / bstar[k] for k in ks])
            ge = boot([(best[k] - runs[c][k]) / best[k] for k in ks])
            gm = float(np.exp(np.mean([np.log(runs[c][k]) for k in ks])))
            res[f"{c}|{rl}"] = dict(n=len(ks), vs_bstar=gb, vs_best=ge, gmean=gm)
            print(f"  {lab[c]:38s} n={len(ks):2d}  vs B* {p(gb)}  vs best {p(ge)}  P99 {gm:7.0f} s")
        for lbl, full, without in (("remove re-layout   (D vs B)", "D", "B"), ("remove moves      (D vs C2)", "D", "C2"),
                                   ("remove dispatch   (D vs E)", "D", "E"), ("add re-layout to A (C vs A)", "C", "A"),
                                   ("add moves to A     (H vs A)", "H", "A"), ("add dispatch to A  (G vs A)", "G", "A"),
                                   ("ours vs B*+our moves (D vs F)", "D", "F")):
            ks = sorted(k for k in runs[full] if k in runs[without] and k[1] in rhos and k[0] in fams)
            if not ks:
                continue
            b = boot([np.log(runs[without][k] / runs[full][k]) for k in ks])
            res[f"{lbl}|{rl}"] = b
            print(f"  log-P99 effect, {lbl}: x{np.exp(b['mean']):.2f}  ({np.exp(b['lo']):.2f} to {np.exp(b['hi']):.2f})  n={len(ks)}")
    (HERE / "results" / "grid_decomp.json").write_text(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    run(int(sys.argv[2]) if len(sys.argv) > 2 else 4) if sys.argv[1] == "run" else analyze()
