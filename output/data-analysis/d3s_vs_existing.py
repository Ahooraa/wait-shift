"""O3S_120 against B* and against the best existing method on all instances that have the baselines.

best existing = min P99 of B_STAR, RL, RL_CAL (and HEU where it was run), per case.
envelope = best of all cheaters present per case (O3S120, O1_BSTAR, O1, P_TRUE), floored at best existing.
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from d1_rlla import BASE, D1, D3S, RUNS, boot  # noqa: E402

res = {}
for d_ in (D1, BASE, RUNS):
    for f in d_.glob("*.json"):
        d = json.loads(f.read_text())
        if "ctrl" in d:
            res.setdefault((d["family"], d["rho"], d["seed"]), {})[d["ctrl"]] = d["result"]["p99_makespan"]
for f in D3S.glob("*.O3S_h120.json"):
    d = json.loads(f.read_text())
    res.setdefault((d["family"], d["rho"], d["seed"]), {})["O3S120"] = d["result"]["p99_makespan"]

EX = ("B_STAR", "RL", "RL_CAL", "HEU")
CH = ("O3S120", "O1_BSTAR", "O1", "P_TRUE")
out = {}
rows = []
for fam in ("F1", "F2", "F3"):
    allb, alle, allenv, allbst = [], [], [], []
    for rho in (0.5, 0.7, 0.85):
        ks = [k for k in res if k[0] == fam and k[1] == rho and "O3S120" in res[k] and all(m in res[k] for m in ("B_STAR", "RL", "RL_CAL"))]
        vb, ve, vv, win, bx, rx, ex_, ox = [], [], [], 0, [], [], [], []
        for k in ks:
            c = res[k]
            be = min(c[m] for m in EX if m in c)
            vb.append((c["B_STAR"] - c["O3S120"]) / c["B_STAR"])
            ve.append((be - c["O3S120"]) / be)
            env = min([be] + [c[m] for m in CH if m in c])
            vv.append((be - env) / be)
            win += c["O3S120"] < be
            bx.append(c["B_STAR"]); rx.append(c["RL"]); ex_.append(be); ox.append(c["O3S120"])
        rows.append(dict(fam=fam, rho=rho, n=len(ks), B=np.mean(bx), RL=np.mean(rx), best=np.mean(ex_), O3S=np.mean(ox),
                         vs_best=boot(ve), win=int(win)))
        allb += vb; alle += ve; allenv += vv
    out[fam] = dict(vs_bstar=boot(allb), vs_best=boot(alle), envelope=boot(allenv),
                    median_vs_best=float(np.median(alle)), win=int(sum(np.array(alle) > 0)), n=len(alle),
                    median_env=float(np.median(allenv)))
p = lambda b: f"{b['mean']*100:+.1f}% ({b['lo']*100:.1f} to {b['hi']*100:.1f})"  # noqa: E731
for r in rows:
    print(r["fam"], r["rho"], "n", r["n"], "B* %.0f RL %.0f best %.0f O3S %.0f" % (r["B"], r["RL"], r["best"], r["O3S"]), "vs best", p(r["vs_best"]), "win", r["win"])
for f, v in out.items():
    print(f, "n", v["n"], "vs B*", p(v["vs_bstar"]), "| vs best existing", p(v["vs_best"]), "median %.1f%%" % (100 * v["median_vs_best"]),
          "win", v["win"], "| envelope", p(v["envelope"]), "median %.1f%%" % (100 * v["median_env"]))
(ROOT / "output" / "data-analysis" / "results" / "d3s_vs_existing.json").write_text(json.dumps(dict(families=out, rows=[{k: (v if not isinstance(v, (np.floating,)) else float(v)) for k, v in r.items()} for r in rows]), indent=1, default=float))
