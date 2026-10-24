"""Compare O3S variants on the cases they share (F1/F2, seeds 1-3 unless more exist).

For each variant: gain vs B*, gain vs best existing (best of B*, RL, RL_CAL, Heu where run), share of the exact oracle's gain over B*
that it keeps, switch share, and decision compute time (median / p90 seconds per decision).
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from d1_rlla import BASE, D1, D3S, boot  # noqa: E402

M = "p99_makespan"
VARIANTS = [("O3S_h120", "oracle (exact future)"), ("O3S_h120_rateoracle", "rate oracle"), ("O3S_h120_blind", "no foresight"),
            ("O3S_h120_blind_nosim", "ablation: busiest-first, no sim check"), ("O3S_h120_blind_local_sim", "ablation: sim check, small swaps only"),
            ("O3S_h120_blind_H60", "speed: 5 cands, H 60 s"), ("O3S_h120_blind_keep_bottleneck", "speed: 2 cands, H 120 s"),
            ("O3S_h120_blind_keep_bottleneck_H30", "speed: 2 cands, H 30 s"),
            ("O3S_h120_blind_hpa", "baseline: HPA-style (load / 0.8)"), ("O3S_h120_blind_fifer", "baseline: Fifer-style (queue / batch)"),
            ("O3S_h120_blind_kraken", "baseline: Kraken-style (DAG weights)")]
base = {}
for d_ in (D1, BASE):
    for f in d_.glob("*.json"):
        d = json.loads(f.read_text())
        if "ctrl" in d:
            base.setdefault((d["family"], d["rho"], d["seed"]), {})[d["ctrl"]] = d["result"][M]
runs = {}
for suf, _ in VARIANTS:
    for f in D3S.glob(f"*.{suf}.json"):
        d = json.loads(f.read_text())
        runs.setdefault(suf, {})[(d["family"], d["rho"], d["seed"])] = d
EX = ("B_STAR", "RL", "RL_CAL", "HEU")
p = lambda b: f"{b['mean'] * 100:+.1f}% ({b['lo'] * 100:.0f} to {b['hi'] * 100:.0f})"  # noqa: E731
out = {}
for suf, label in VARIANTS:
    if suf not in runs:
        continue
    for fam in ("F1", "F2"):
        for rhos, rl in (((0.5,), "50%"), ((0.7, 0.85), "70-85%"), ((0.5, 0.7, 0.85), "all")):
            ks = [k for k in runs[suf] if k[0] == fam and k[1] in rhos and k[2] <= 3 and k in base and "B_STAR" in base[k]
                  and k in runs.get("O3S_h120", {})]
            if not ks:
                continue
            vb, ve, keep_n, keep_d, wall, sw = [], [], 0.0, 0.0, [], []
            for k in ks:
                c, r = base[k], runs[suf][k]["result"][M]
                be = min(c[m] for m in EX if m in c)
                ex = runs["O3S_h120"][k]["result"][M]
                vb.append((c["B_STAR"] - r) / c["B_STAR"])
                ve.append((be - r) / be)
                keep_n += c["B_STAR"] - r
                keep_d += c["B_STAR"] - ex
                wall += [x["wall_s"] for x in runs[suf][k]["decisions"]]
                sw.append(runs[suf][k]["n_switch"] / max(1, len(runs[suf][k]["decisions"])))
            row = dict(n=len(ks), vs_bstar=boot(vb), vs_best=boot(ve), keeps=keep_n / keep_d if keep_d > 0 else float("nan"),
                       wins_vs_best=int(sum(v > 0 for v in ve)), wall_med=float(np.median(wall)), wall_p90=float(np.percentile(wall, 90)),
                       switch=float(np.mean(sw)))
            out[f"{suf}|{fam}|{rl}"] = row
            print(f"{label:42s} {fam} {rl:6s} n={row['n']:2d} | vs B* {p(row['vs_bstar'])} | vs best existing {p(row['vs_best'])}"
                  f" wins {row['wins_vs_best']}/{row['n']} | keeps {row['keeps']:.0%} of oracle gain | decision {row['wall_med']:.0f}s"
                  f" (p90 {row['wall_p90']:.0f}s) | switch {row['switch']:.0%}")
(ROOT / "output" / "data-analysis" / "results" / "d3s_variants_compare.json").write_text(json.dumps(out, indent=1))
