"""Summarise batch results: mean +- sd over workloads, paired differences vs DFPS, repeated-measures ANOVA (DFPS Sec.5.2)."""
import glob, json, sys
import numpy as np
from scipy import stats

M = ["SR", "SG", "DFPS", "HEU", "RL"]
d = sys.argv[1]
for scale in sys.argv[2].split(","):
    rows = {}
    for f in sorted(glob.glob(f"{d}/*_x{float(scale)}_s*.json")):
        r = json.load(open(f))["results"]
        rows[f] = {m: r[m] for m in M}
    n = len(rows)
    if not n: continue
    print(f"\n=== load x{scale}: {n} workloads ===")
    for key, label in [("avg_makespan", "avg makespan (s)"), ("utilization", "utilization"), ("cold_starts", "cold starts")]:
        A = np.array([[v[m][key] for m in M] for v in rows.values()])
        print(f"{label:18}" + "".join(f"{m:>16}" for m in M))
        print(" " * 18 + "".join(f"{A[:, i].mean():>9.2f}±{A[:, i].std(ddof=1):<6.2f}" for i in range(5)))
        if key == "avg_makespan":
            ms = A
    print("paired diff vs DFPS (method - DFPS), mean [95% CI], wins of DFPS:")
    for i, m in enumerate(M):
        if m == "DFPS": continue
        dd = ms[:, i] - ms[:, 2]
        ci = stats.t.interval(0.95, n - 1, dd.mean(), stats.sem(dd))
        print(f"  {m:5} {dd.mean():8.2f} [{ci[0]:7.2f},{ci[1]:7.2f}]  DFPS better in {int((dd > 0).sum())}/{n}")
    # repeated-measures one-way ANOVA (workloads = subjects, methods = conditions)
    k = ms.shape[1]
    gm = ms.mean()
    ss_c = n * ((ms.mean(0) - gm) ** 2).sum()
    ss_s = k * ((ms.mean(1) - gm) ** 2).sum()
    ss_t = ((ms - gm) ** 2).sum()
    ss_e = ss_t - ss_c - ss_s
    F = (ss_c / (k - 1)) / (ss_e / ((k - 1) * (n - 1)))
    print(f"RM-ANOVA over 5 methods: F({k-1},{(k-1)*(n-1)})={F:.1f}, p={stats.f.sf(F, k-1, (k-1)*(n-1)):.2e}")
