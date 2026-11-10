import json, sys
import numpy as np
from pathlib import Path
ROOT = next(p for p in (Path("D:/DFPS implementation"), Path.home() / "DFPS-implementation") if p.exists()); sys.path.insert(0, str(ROOT / "output" / "data-analysis")); sys.path.insert(0, str(ROOT))
import capw1_ondemand as O, capw1_rows as C, capw1_heldout as H
cs = C.dev()
def J(c, a): return json.loads((O.OUT / f"{c}.{a}.json").read_text())
names = ("frozen3_od_e30", "frozen3_od_e30_u65", "frozen3_od_e30_u50")
arms = {a: {c: J(c, a) for c in cs} for a in names}
filled = {c: C.frozen3(c) for c in cs}
print("err files:", len(list(O.OUT.glob("*.err"))))
def gm(x): return float(np.exp(np.mean(np.log(x))))
print("30 s re-layout, on-demand FROZEN-3 over filled FROZEN-3 (P99 ratio); mem = share of cluster")
for a in names:
    d = arms[a]
    r = [d[c]["result"]["p99_makespan"] / filled[c]["p99_makespan"] for c in cs]
    m = [d[c]["result"]["avg_makespan"] / filled[c]["avg_makespan"] for c in cs]
    g = H.gm_ci(r)
    by = " | ".join("rho%s P99 %.2f mem %.2f" % (x, gm([q for q, c in zip(r, cs) if f"_r{x}_" in c]),
         np.mean([d[c]["info"]["prov_mean"] / d[c]["info"]["capacity_total"] for c in cs if f"_r{x}_" in c])) for x in ("0.5", "0.7", "0.85"))
    print(f"{a:20s} all {g[0]:.2f} [{g[1]:.2f}, {g[2]:.2f}] lower {sum(x<1 for x in r)}/18 mean {gm(m):.2f} cold {np.mean([d[c]['result']['cold_starts'] for c in cs]):.0f} mem {np.mean([d[c]['info']['prov_mean']/d[c]['info']['capacity_total'] for c in cs]):.2f} | {by}")
