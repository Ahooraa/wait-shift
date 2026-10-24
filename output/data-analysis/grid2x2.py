"""2x2 grid (2026-10-22): re-layout (busiest-first, 60 s) x request moves (finish-time rule, cap 300); B* off in all four cells, same
dispatcher, no foresight, F1/F2 x 50/70/85% x seeds 1-3 (18 cases).
  A fixed layout, nothing adapts      (new: this script)       files ..._nosim_x0.json
  B fixed layout + request moves      (x0_rebal, run before)
  C re-layout only                    (noinner, run before)
  D both                              (rebal, the reference)
  python output/data-analysis/grid2x2.py run [workers]  |  analyze
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

M = "p99_makespan"
CELLS = {"A": "x0", "B": "x0_rebal", "C": "noinner", "D": "rebal"}


def run(workers):
    T = json.loads((d.OUT / "g2_tstar.json").read_text())
    T = {f: float(T["families"][f]["T_star"]) for f in ("F1", "F2")}
    jobs = []
    for f in ("F1", "F2"):
        for r in d.RHOS:
            for s in (1, 2, 3):
                tg = d.tag(f, r, s)
                jobs.append((tg, str(d.RUNS / f"{tg}.O3S_h120_blind_nosim_x0.json"), s, T[f], d.DURATION, 60.0, 120.0, 5, True, None,
                             "nosim", {"no_inner": True, "no_relayout": True}))
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
                bstar[(x["family"], x["rho"], x["seed"])] = x["result"][M]
    runs = {c: {} for c in CELLS}
    for c, suf in CELLS.items():
        for f in d.RUNS.glob(f"*.O3S_h120_blind_nosim_{suf}.json"):
            x = json.loads(f.read_text())
            if x["seed"] <= 3 and x["family"] in ("F1", "F2"):
                runs[c][(x["family"], x["rho"], x["seed"])] = x["result"][M]
    p = lambda b: f"{b['mean'] * 100:+7.1f}% ({b['lo'] * 100:+.0f} to {b['hi'] * 100:+.0f})"  # noqa: E731
    out = {}
    for rhos, rl in (((0.5,), "50% load"), ((0.7, 0.85), "70-85% load"), ((0.5, 0.7, 0.85), "all loads")):
        ks = sorted(k for k in set.intersection(*(set(r) for r in runs.values())) if k[1] in rhos and k in bstar)
        if not ks:
            continue
        print(f"=== {rl}: {len(ks)} cases; gain over B* (P99) ===")
        g = {c: [(bstar[k] - runs[c][k]) / bstar[k] for k in ks] for c in CELLS}
        for c, lab in (("A", "A fixed layout, nothing adapts"), ("B", "B fixed layout + request moves"),
                       ("C", "C re-layout only"), ("D", "D re-layout + request moves")):
            out[f"{c}|{rl}"] = boot(g[c])
            print(f"  {lab:34s} {p(out[f'{c}|{rl}'])}")
        # effects on the log-P99 scale so they add: effect = ln(P99_without / P99_with)
        L = {c: np.array([np.log(runs[c][k]) for k in ks]) for c in CELLS}
        e_moves_fixed, e_moves_relay = L["A"] - L["B"], L["C"] - L["D"]
        e_relay_nomoves, e_relay_moves = L["A"] - L["C"], L["B"] - L["D"]
        inter = (L["A"] - L["B"]) - (L["C"] - L["D"])          # 0 = additive; > 0: moves help more on a fixed layout than with re-layout
        for name, v in (("request moves, on a fixed layout   (A to B)", e_moves_fixed), ("request moves, with re-layout       (C to D)", e_moves_relay),
                        ("re-layout, without request moves   (A to C)", e_relay_nomoves), ("re-layout, with request moves      (B to D)", e_relay_moves),
                        ("interaction (A-B)-(C-D), 0 = additive", inter)):
            b = boot(v)
            out[f"{name.split('(')[0].strip()}|{rl}"] = b
            print(f"  log-P99 effect {name}: {b['mean']:+.2f} ({b['lo']:+.2f} to {b['hi']:+.2f})  [x{np.exp(b['mean']):.1f}]")
    (d.OUT / "grid2x2.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 11)
    else:
        analyze()
