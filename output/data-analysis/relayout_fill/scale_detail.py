"""Absolute numbers per seed behind the scale ratios; PL-4 timing next to PL-5; which fields a run file holds."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import scale_run as SR

keys = None
for budget, name in (("", "on-demand"), ("fixed", "fixed-budget")):
    print("=====", name)
    for n, f, w in SR.SIZES:
        print(f" -- N{n} F{f}")
        for fast, lab in (("4", "PL-4"), ("5", "PL-5"), ("6", "PL-5p")):
            rows = []
            for seed in range(1, 6):
                p = SR.path(fast, budget, n, f, w, seed)
                d = json.loads(p.read_text())
                keys = keys or sorted(d.keys())
                rows.append(d)
            print(f"   {lab:6s} P99 by seed " + " ".join(f"{d['p99_makespan']:7.2f}" for d in rows)
                  + " | mean " + " ".join(f"{d['avg_makespan']:6.3f}" for d in rows)
                  + f" | re-layout later median {np.median([d['relayout_later']['median'] for d in rows]):7.0f} ms, max incl. first {max(d['relayout']['max'] for d in rows):7.0f} ms"
                  + f" | move p99 {np.median([d['move']['p99'] for d in rows]):6.0f} ms")
print("fields:", keys)
d = json.loads(SR.path("4", "", 1280, 480, 240, 1).read_text())
print({k: v for k, v in d.items() if not isinstance(v, (list, dict))})
print("relayout", d["relayout"], "later", d["relayout_later"], "move", d["move"])
