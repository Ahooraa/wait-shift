import json, sys
import numpy as np
from pathlib import Path
ROOT = Path("D:/DFPS implementation"); sys.path.insert(0, str(ROOT / "output" / "data-analysis")); sys.path.insert(0, str(ROOT))
import capw1_ondemand as O, capw1_rows as C, capw1_heldout as H
cs = C.dev()
def J(c, a): return json.loads((O.OUT / f"{c}.{a}.json").read_text())
arms = {a: {c: J(c, a) for c in cs} for a in ("frozen3_od", "frozen3_od_e30", "frozen3_od_e15")}
filled = {c: C.frozen3(c) for c in cs}
print("err files:", len(list(O.OUT.glob("*.err"))), " cases filled:", sum(v is not None for v in filled.values()))
def gm(x): return float(np.exp(np.mean(np.log(x))))
RH = ("0.5", "0.7", "0.85")
print("P99 / filled FROZEN-3 (geo-mean, CI) and by load; mean makespan ratio; cold starts; memory share")
print("filled      mean P99 %.0f  mean makespan %.1f  cold %.0f" % (np.mean([filled[c]["p99_makespan"] for c in cs]), np.mean([filled[c]["avg_makespan"] for c in cs]), np.mean([filled[c]["cold_starts"] for c in cs])))
for a, d in arms.items():
    r = [d[c]["result"]["p99_makespan"] / filled[c]["p99_makespan"] for c in cs]
    m = [d[c]["result"]["avg_makespan"] / filled[c]["avg_makespan"] for c in cs]
    g = H.gm_ci(r)
    by = " ".join("%s:%.2f" % (x, gm([q for q, c in zip(r, cs) if f"_r{x}_" in c])) for x in RH)
    fam = " ".join("%s:%.2f" % (f, gm([q for q, c in zip(r, cs) if c.startswith(f)])) for f in ("F1", "F2"))
    print(f"{a:15s} P99 {g[0]:.2f} [{g[1]:.2f}, {g[2]:.2f}] lower than filled {sum(x<1 for x in r)}/18 | {by} | {fam} | mean {gm(m):.2f} | meanP99 {np.mean([d[c]['result']['p99_makespan'] for c in cs]):.0f} | cold {np.mean([d[c]['result']['cold_starts'] for c in cs]):.0f} | mem {np.mean([d[c]['info']['prov_mean']/d[c]['info']['capacity_total'] for c in cs]):.2f} | relayouts {np.mean([d[c]['info']['n_relayouts'] for c in cs]):.1f} | moves/100 {np.mean([100*d[c]['result']['n_moved']/d[c]['result']['n_completed'] for c in cs]):.0f}")
b = arms["frozen3_od"]
for a in ("frozen3_od_e30", "frozen3_od_e15"):
    r = [arms[a][c]["result"]["p99_makespan"] / b[c]["result"]["p99_makespan"] for c in cs]
    g = H.gm_ci(r)
    print(f"{a} / 60 s on-demand: P99 {g[0]:.2f} [{g[1]:.2f}, {g[2]:.2f}], lower in {sum(x<1 for x in r)}/18")
