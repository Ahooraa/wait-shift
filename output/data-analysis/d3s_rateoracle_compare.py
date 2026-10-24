"""Rate oracle vs exact oracle O3S (120 s look-ahead) on the cases both ran (seeds 1-3).

exact  = the clone replays the true upcoming arrivals (knows the random clumps)
rate   = the clone replays a fresh Poisson draw of the true rate series (knows where traffic is heading, not the clumps)
Reports, per family and per load: gain vs B*, gain vs the best existing method (best of B*, RL, RL_CAL, Heu where run),
and the share of the exact oracle's gain over B* that the rate oracle keeps (ratio of mean gains).
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from d1_rlla import BASE, D1, D3S, boot  # noqa: E402

M = "p99_makespan"
res = {}
for d_ in (D1, BASE):
    for f in d_.glob("*.json"):
        d = json.loads(f.read_text())
        if "ctrl" in d:
            res.setdefault((d["family"], d["rho"], d["seed"]), {})[d["ctrl"]] = d["result"][M]
for suf, name in ((".O3S_h120.json", "EXACT"), (".O3S_h120_rateoracle.json", "RATE")):
    for f in D3S.glob("*" + suf):
        if not f.name.endswith(suf):
            continue
        d = json.loads(f.read_text())
        res.setdefault((d["family"], d["rho"], d["seed"]), {})[name] = d["result"][M]
        res[(d["family"], d["rho"], d["seed"])][name + "_switch"] = d["n_switch"] / max(1, len(d["decisions"]))

EX = ("B_STAR", "RL", "RL_CAL", "HEU")
out, lines = {}, []
for fam in ("F1", "F2", "F3"):
    agg = {k: [] for k in ("ex_b", "ra_b", "ex_best", "ra_best", "ra_vs_ex")}
    for rho in (0.5, 0.7, 0.85):
        ks = [k for k in res if k[0] == fam and k[1] == rho and all(m in res[k] for m in ("B_STAR", "EXACT", "RATE"))]
        cell = {k: [] for k in agg}
        for k in ks:
            c = res[k]
            be = min(c[m] for m in EX if m in c)
            cell["ex_b"].append((c["B_STAR"] - c["EXACT"]) / c["B_STAR"])
            cell["ra_b"].append((c["B_STAR"] - c["RATE"]) / c["B_STAR"])
            cell["ex_best"].append((be - c["EXACT"]) / be)
            cell["ra_best"].append((be - c["RATE"]) / be)
            cell["ra_vs_ex"].append((c["EXACT"] - c["RATE"]) / c["EXACT"])
        for k in agg:
            agg[k] += cell[k]
        if ks:
            keep = np.mean(cell["ra_b"]) / np.mean(cell["ex_b"]) if np.mean(cell["ex_b"]) > 0 else float("nan")
            lines.append(f"{fam} {int(rho * 100)}% n={len(ks)} | vs B*: exact {np.mean(cell['ex_b']) * 100:+.1f}%, rate {np.mean(cell['ra_b']) * 100:+.1f}%"
                         f" (keeps {keep:.0%}) | vs best existing: exact {np.mean(cell['ex_best']) * 100:+.1f}%, rate {np.mean(cell['ra_best']) * 100:+.1f}%")
    if agg["ex_b"]:
        keep = np.mean(agg["ra_b"]) / np.mean(agg["ex_b"])
        out[fam] = {k: boot(v) for k, v in agg.items()} | dict(keep_share=float(keep))
        p = lambda b: f"{b['mean'] * 100:+.1f}% ({b['lo'] * 100:.1f} to {b['hi'] * 100:.1f})"  # noqa: E731
        lines.append(f"{fam} ALL n={len(agg['ex_b'])} | vs B*: exact {p(out[fam]['ex_b'])}, rate {p(out[fam]['ra_b'])}, rate keeps {keep:.0%} of the exact gain"
                     f" | vs best existing: exact {p(out[fam]['ex_best'])}, rate {p(out[fam]['ra_best'])} | rate vs exact {p(out[fam]['ra_vs_ex'])}")
print("\n".join(lines))
(ROOT / "output" / "data-analysis" / "results" / "d3s_rateoracle_compare.json").write_text(json.dumps(out, indent=1))
