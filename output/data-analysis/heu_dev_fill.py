"""Heu on the development cases that d1_vs_baselines.py did not run (2026-10-29): Farm 1 at 85% load and Farm 2 at
50/70/85%, seeds 1-3. Farm 1 at 50% and 70% (seeds 1-3) already exist and are skipped.

  python output/data-analysis/heu_dev_fill.py [workers]
"""
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import d1_vs_baselines as b  # noqa: E402

JOBS = [
    (b.tag(f, r, s), "HEU", s, str(b.RUNS / f"{b.tag(f, r, s)}.HEU.json"))
    for s in (1, 2, 3) for r in (0.5, 0.7, 0.85) for f in ("F1", "F2")
    if not Path(b.RUNS / f"{b.tag(f, r, s)}.HEU.json").exists()
]

if __name__ == "__main__":
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    b.RUNS.mkdir(parents=True, exist_ok=True)
    print(len(JOBS), "jobs,", workers, "workers", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        for done in ex.map(b.job, JOBS):
            print("done", done, flush=True)
