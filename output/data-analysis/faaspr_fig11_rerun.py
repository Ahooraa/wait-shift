"""One-off driver (2026-10-26): re-run faaspr_fig11's CASES x VARIANTS now that "ours" uses lam=0.5, saving every
breakdown field (not just p99/transfer) so a richer comparison table can be built. Scratch script, not part of the
permanent pipeline -- faaspr_fig11.py itself is unchanged except the VARIANTS lam=0.5 edit.

  python -I output/data-analysis/faaspr_fig11_rerun.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import faaspr_fig11 as fig11

OUT = Path(__file__).parent / "results" / "fig11_rich"
OUT.mkdir(parents=True, exist_ok=True)

for fam, rho, k, seed in fig11.CASES:
    for v in fig11.VARIANTS:
        out = OUT / f"{fam}_r{rho}_k{k}_s{seed}.{v}.json"
        if out.exists():
            print("skip (exists)", out.name, flush=True)
            continue
        print("running", fam, v, flush=True)
        b = fig11.run_one(fam, rho, k, seed, v, duration=140.0)
        out.write_text(json.dumps(dict(fam=fam, rho=rho, k=k, seed=seed, variant=v, result=b)))
        print("  done", fam, v, "p99=%.1f" % b["p99_makespan"], flush=True)
print("ALL DONE", flush=True)
