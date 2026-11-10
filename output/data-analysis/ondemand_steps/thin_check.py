"""Step 5c (7 Nov 2026). (1) Exact speed-ups: event hashes against the stored lazy runs, 6 cases. (2) Second approximation: demand-point thinning M = 32, 16 against lazy, 18 development cases."""
import json, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
ROOT = next(p for p in (Path("D:/DFPS implementation"), Path.home() / "DFPS-implementation") if p.exists()); sys.path.insert(0, str(ROOT / "output" / "data-analysis")); sys.path.insert(0, str(ROOT))
import capw1_ondemand as O, capw1_rows as C, capw1_heldout as H

REF = "frozen3_od_e30_u70_fo_lz"
DIR = ROOT / "results" / "capW1_fast_identity2"
THIN = (REF + "_t32", REF + "_t16")

if __name__ == "__main__":
    cs = C.dev()
    id_cases = [c for c in cs if c.endswith("_s1")]
    jobs = [(c, REF, O.DURATION, str(DIR)) for c in id_cases] + [(c, a, O.DURATION, str(O.OUT)) for a in THIN for c in cs]
    with ProcessPoolExecutor(4, initializer=O.H.I._low_priority) as ex:
        out = list(ex.map(O.run_job, jobs))
    bad = [r for r in out if r.endswith("FAILED")]
    print("failed:", len(bad))
    if bad:
        print(Path(bad[0].replace(" FAILED", "")).with_suffix(".err").read_text()[-900:])
    same = 0
    for c in id_cases:
        x = json.loads((DIR / f"{c}.{REF}.json").read_text())["result"]
        y = json.loads((O.OUT / f"{c}.{REF}.json").read_text())["result"]
        same += x["event_hash"] == y["event_hash"]
        print(c, "hash same", x["event_hash"] == y["event_hash"], "P99", round(x["p99_makespan"], 2), round(y["p99_makespan"], 2), "moved", x["n_moved"], y["n_moved"], "wall", round(x["wall_s"]), round(y["wall_s"]))
    print("exact speed-ups: hash equal in", same, "of", len(id_cases))
    b = {c: json.loads((O.OUT / f"{c}.{REF}.json").read_text()) for c in cs}
    for arm in THIN:
        a = {c: json.loads((O.OUT / f"{c}.{arm}.json").read_text()) for c in cs if (O.OUT / f"{c}.{arm}.json").exists()}
        r = [a[c]["result"]["p99_makespan"] / b[c]["result"]["p99_makespan"] for c in a]
        g = H.gm_ci(r)
        gm = lambda k: np.exp(np.mean(np.log([a[c]["result"][k] / b[c]["result"][k] for c in a])))
        print(f"{arm}: cases {len(r)}, P99 over lazy {g[0]:.3f} [{g[1]:.3f}, {g[2]:.3f}], lower in {sum(x < 1 for x in r)}, range {min(r):.3f} to {max(r):.3f}; mean makespan {gm('avg_makespan'):.3f}; cold starts {gm('cold_starts'):.3f}; memory {np.exp(np.mean(np.log([a[c]['info']['prov_mean'] / b[c]['info']['prov_mean'] for c in a]))):.3f}; same hash {sum(a[c]['result']['event_hash'] == b[c]['result']['event_hash'] for c in a)}")
