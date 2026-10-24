"""Churn trade-off table: busiest-first variants vs B*, RL and the every-minute rule (Azure + Huawei, seeds 1-3, 18 cases each).

Per variant: P99 gain vs B* and vs the best existing method (split 50% / 70-85% load), cold starts per run (in the measured window
and in total), re-layouts applied per run, containers changed per re-layout (from the decision logs), decision time.
Cases are matched: only cases that exist for BOTH the variant and the every-minute reference are used.
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from d1_rlla import BASE, D1, D3S  # noqa: E402

M = "p99_makespan"
EX = ("B_STAR", "RL", "RL_CAL", "HEU")
VARIANTS = [("O3S_h120_blind_nosim", "every minute (reference)"), ("O3S_h120_blind_nosim_noinner", "no B* swaps underneath"),
            ("O3S_h120_blind_nosim_frac0.4", "skip unless >=40% of slots change"), ("O3S_h120_blind_nosim_frac0.6", "skip unless >=60% of slots change"),
            ("O3S_h120_blind_nosim_cap50", "cap 50 containers per re-layout"), ("O3S_h120_blind_nosim_cap100", "cap 100 per re-layout"),
            ("O3S_h120_blind_nosim_cap200", "cap 200 per re-layout"), ("O3S_h120_blind_nosim_indep", "INDEPENDENT (own small moves, no B*)"), ("O3S_h120_blind_nosim_indep_cap200", "INDEPENDENT + cap 200"), ("O3S_h120_blind_nosim_E120", "every 2 minutes"),
            ("O3S_h120_blind_nosim_E180", "every 3 minutes"), ("O3S_h120_blind_nosim_E300", "every 5 minutes"),
            ("O3S_h120_blind_nosim_bl1.0", "only if backlog >= 1.0x slots"), ("O3S_h120_blind_nosim_bl2.0", "only if backlog >= 2.0x slots")]

base = {}
for d_ in (D1, BASE):
    for f in d_.glob("*.json"):
        d = json.loads(f.read_text())
        if "ctrl" in d:
            base.setdefault((d["family"], d["rho"], d["seed"]), {})[d["ctrl"]] = d["result"]
runs = {}
for suf, _ in VARIANTS:
    for f in D3S.glob(f"*.{suf}.json"):
        d = json.loads(f.read_text())
        runs.setdefault(suf, {})[(d["family"], d["rho"], d["seed"])] = d
ref = runs.get("O3S_h120_blind_nosim", {})


def row(name, label, sel):
    ks = [k for k in runs[name] if k in ref and k in base and "B_STAR" in base[k] and sel(k)]
    if not ks:
        return None
    g_b, g_e, cs_w, cs_t, lay, per_lay = [], [], [], [], [], []
    for k in ks:
        r = runs[name][k]["result"]
        b = base[k]
        be = min(b[m][M] for m in EX if m in b)
        g_b.append((b["B_STAR"][M] - r[M]) / b["B_STAR"][M])
        g_e.append((be - r[M]) / be)
        cs_w.append(r["cold_starts"])
        cs_t.append(r["cold_starts_total"])
        dec = runs[name][k]["decisions"]
        lay.append(runs[name][k]["n_switch"])
        ap = [x.get("n_applied") for x in dec if x.get("switched") and x.get("n_applied") is not None]
        if ap:
            per_lay.append(np.mean(ap))
    return dict(n=len(ks), vs_b=np.mean(g_b), vs_best=np.mean(g_e), cs_w=np.mean(cs_w), cs_t=np.mean(cs_t), lay=np.mean(lay),
                per=np.mean(per_lay) if per_lay else float("nan"))


for title, sel in (("50% load", lambda k: k[1] == 0.5), ("70-85% load", lambda k: k[1] in (0.7, 0.85)), ("all loads", lambda k: True)):
    print(f"=== {title} ===")
    print(f"{'variant':38s} {'n':>3s} {'vs B*':>8s} {'vs best':>8s} {'cold(win)':>10s} {'cold(tot)':>10s} {'layouts':>8s} {'chg/layout':>10s}")
    for name, label in VARIANTS:
        if name in runs:
            r = row(name, label, sel)
            if r:
                print(f"{label:38s} {r['n']:3d} {r['vs_b'] * 100:+7.1f}% {r['vs_best'] * 100:+7.1f}% {r['cs_w']:10.0f} {r['cs_t']:10.0f} {r['lay']:8.1f} {r['per']:10.0f}")
    ks = [k for k in ref if k in base and "B_STAR" in base[k] and sel(k)]
    if ks:
        for m, lab in (("B_STAR", "B* alone"), ("RL", "RL")):
            if all(m in base[k] for k in ks):
                g = np.mean([(base[k]["B_STAR"][M] - base[k][m][M]) / base[k]["B_STAR"][M] for k in ks])
                print(f"{lab:38s} {len(ks):3d} {g * 100:+7.1f}% {'':8s} {np.mean([base[k][m]['cold_starts'] for k in ks]):10.0f} "
                      f"{np.mean([base[k][m]['cold_starts_total'] for k in ks]):10.0f}")
