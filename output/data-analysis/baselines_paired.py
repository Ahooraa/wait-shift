"""Paired test: published sizing rules vs busiest-first (2026-10-22). Same case (family, load, seed), same B*, same dispatcher, same
affinity placement and whole-layout re-plan every 60 s; only the sizing rule differs. Metric: P99 makespan.
Difference per case: d = (P99_rule - P99_busiest) / P99_busiest  (positive = busiest-first is better). Bootstrap 95% CI over cases,
plus sign count. Also 'share of B*-gain kept' = (B* - rule) / (B* - busiest), pooled over cases.
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from d1_rlla import BASE, D1, D3S, boot  # noqa: E402

M = "p99_makespan"
RULES = [("O3S_h120_blind_hpa", "HPA-style"), ("O3S_h120_blind_fifer", "Fifer-style"), ("O3S_h120_blind_kraken", "Kraken-style")]
REF = "O3S_h120_blind_nosim"
bstar = {}
for d_ in (D1, BASE):
    for f in d_.glob("*.json"):
        d = json.loads(f.read_text())
        if d.get("ctrl") == "B_STAR":
            bstar[(d["family"], d["rho"], d["seed"])] = d["result"][M]


def load(suf):
    out = {}
    for f in D3S.glob(f"*.{suf}.json"):
        d = json.loads(f.read_text())
        out[(d["family"], d["rho"], d["seed"])] = d["result"][M]
    return out


ref = load(REF)
res = {}
p = lambda b: f"{b['mean'] * 100:+.1f}% ({b['lo'] * 100:+.0f} to {b['hi'] * 100:+.0f})"  # noqa: E731
for suf, label in RULES:
    r = load(suf)
    for fam in ("F1", "F2", "both"):
        for rhos, rl in (((0.5,), "50%"), ((0.7, 0.85), "70-85%"), ((0.5, 0.7, 0.85), "all")):
            ks = [k for k in r if (fam == "both" or k[0] == fam) and k[1] in rhos and k in ref and k in bstar]
            if not ks:
                continue
            d = [(r[k] - ref[k]) / ref[k] for k in ks]
            kept = sum(bstar[k] - r[k] for k in ks) / sum(bstar[k] - ref[k] for k in ks)
            row = dict(n=len(ks), busiest_better_by=boot(d), busiest_wins=int(sum(x > 0 for x in d)), kept=kept)
            res[f"{suf}|{fam}|{rl}"] = row
            print(f"{label:12s} {fam:5s} {rl:7s} n={len(ks):2d} | busiest-first better by {p(row['busiest_better_by'])}"
                  f" | wins {row['busiest_wins']}/{len(ks)} | rule keeps {kept:.0%} of busiest-first's gain over B*")
(ROOT / "output" / "data-analysis" / "results" / "baselines_paired.json").write_text(json.dumps(res, indent=1))
