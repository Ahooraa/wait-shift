"""Do the exact speed-ups change anything? Event-hash check on 6 development cases against the stored frozen3_od_e30_u70 runs (7 Nov 2026)."""
import json, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
ROOT = Path("D:/DFPS implementation"); sys.path.insert(0, str(ROOT / "output" / "data-analysis")); sys.path.insert(0, str(ROOT))
import capw1_ondemand as O

CASES = [f"{f}_r{r}_s1" for f in ("F1", "F2") for r in ("0.5", "0.7", "0.85")]
BASE = "frozen3_od_e30_u70"
ARMS = (BASE, BASE + "_fo", BASE + "_fo_fp")
DIR = ROOT / "results" / "capW1_fast_identity"

if __name__ == "__main__":
    jobs = [(c, a, O.DURATION, str(DIR)) for c in CASES for a in ARMS]
    with ProcessPoolExecutor(3, initializer=O.H.I._low_priority) as ex:
        list(ex.map(O.run_job, jobs))
    keys = ("p99_makespan", "avg_makespan", "n_completed", "cold_starts", "n_moved")
    tot = {a: 0.0 for a in ARMS}
    for c in CASES:
        ref = json.loads((O.OUT / f"{c}.{BASE}.json").read_text())["result"]
        print(c, "stored wall %.0fs hash %s" % (ref["wall_s"], ref["event_hash"][:10]))
        for a in ARMS:
            p = DIR / f"{c}.{a}.json"
            if not p.exists():
                print("  ", a, "FAILED", (DIR / f"{c}.{a}.err").read_text()[-300:] if (DIR / f"{c}.{a}.err").exists() else "")
                continue
            x = json.loads(p.read_text())["result"]
            tot[a] += x["wall_s"]
            print(f"   {a:28s} hash same {x['event_hash'] == ref['event_hash']!s:5s} fields same {all(x[k] == ref[k] for k in keys)!s:5s} P99 {x['p99_makespan']:.2f} (stored {ref['p99_makespan']:.2f}) cold {x['cold_starts']} ({ref['cold_starts']}) moved {x['n_moved']} ({ref['n_moved']}) wall {x['wall_s']:.0f}s", flush=True)
    print("total wall s", {a: round(v) for a, v in tot.items()})
