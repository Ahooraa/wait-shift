"""Lazy re-layout scoring against the stored exact runs, 18 development cases (7 Nov 2026)."""
import json, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
ROOT = Path("D:/DFPS implementation"); sys.path.insert(0, str(ROOT / "output" / "data-analysis")); sys.path.insert(0, str(ROOT))
import capw1_ondemand as O, capw1_rows as C, capw1_heldout as H

ARM, REF = "frozen3_od_e30_u70_fo_lz", "frozen3_od_e30_u70"

if __name__ == "__main__":
    cs = C.dev()
    jobs = [(c, ARM, O.DURATION, str(O.OUT)) for c in cs]
    with ProcessPoolExecutor(4, initializer=O.H.I._low_priority) as ex:
        out = list(ex.map(O.run_job, jobs))
    bad = [r for r in out if r.endswith("FAILED")]
    print("failed:", len(bad), bad[:3])
    if bad:
        print(Path(bad[0].replace(" FAILED", "")).with_suffix(".err").read_text()[-900:])
    a = {c: json.loads((O.OUT / f"{c}.{ARM}.json").read_text()) for c in cs if (O.OUT / f"{c}.{ARM}.json").exists()}
    b = {c: json.loads((O.OUT / f"{c}.{REF}.json").read_text()) for c in a}
    r = [a[c]["result"]["p99_makespan"] / b[c]["result"]["p99_makespan"] for c in a]
    m = [a[c]["result"]["avg_makespan"] / b[c]["result"]["avg_makespan"] for c in a]
    g = H.gm_ci(r)
    print(f"cases {len(r)}, P99 lazy / exact {g[0]:.3f} [{g[1]:.3f}, {g[2]:.3f}], lazy lower in {sum(x < 1 for x in r)}, range {min(r):.3f} to {max(r):.3f}; mean makespan {np.exp(np.mean(np.log(m))):.3f}")
    print("cold starts ratio %.3f" % np.exp(np.mean(np.log([a[c]["result"]["cold_starts"] / b[c]["result"]["cold_starts"] for c in a]))),
          "| memory ratio %.3f" % np.exp(np.mean(np.log([a[c]["info"]["prov_mean"] / b[c]["info"]["prov_mean"] for c in a]))),
          "| moves ratio %.3f" % np.exp(np.mean(np.log([a[c]["result"]["n_moved"] / b[c]["result"]["n_moved"] for c in a]))),
          "| same hash:", sum(a[c]["result"]["event_hash"] == b[c]["result"]["event_hash"] for c in a), "| mover", {a[c]["result"].get("mover_impl") for c in a})
    print("wall s total: lazy %.0f, exact %.0f" % (sum(a[c]["result"]["wall_s"] for c in a), sum(b[c]["result"]["wall_s"] for c in a)))
