"""MV-4 with the staying-cost stop against MV-3 (arm fill1): same event hash? Results go to results/capW1_rows_mv4stop, the earlier MV-4 results stay. python mv4_stop_check.py <workers>"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path("D:/DFPS implementation")
sys.path[:0] = [str(ROOT / "output" / "data-analysis"), str(ROOT)]
CASES = [f"{f}_r{r}_s{s}" for s in (1, 2, 3, 7, 8, 9, 10) for f in ("F1", "F2") for r in (0.5, 0.7, 0.85)]
SUF = ("", "_p1", "_p2")
BASE, OUT = ROOT / "results" / "capW1_rows", ROOT / "results" / "capW1_rows_mv4stop"


def job(a):
    import capw1_rows as R
    R.OUT = OUT
    return R.run_job(a)


if __name__ == "__main__":
    todo = [(c, s) for c in CASES for s in SUF]
    with ProcessPoolExecutor(int(sys.argv[1])) as ex:
        for r in ex.map(job, [(c, "mv4" + s) for c, s in todo]):
            if "FAILED" in r:
                print(r, flush=True)
    same, diff, miss, tags, wall, moved = 0, 0, 0, {}, [0.0, 0.0], 0
    for c, s in todo:
        p = OUT / f"{c}.mv4{s}.json"
        if not p.exists():
            miss += 1
            continue
        x, y = json.loads(p.read_text())["result"], json.loads((BASE / f"{c}.fill1{s}.json").read_text())["result"]
        tags[x.get("mover_impl")] = tags.get(x.get("mover_impl"), 0) + 1
        wall[0] += x["wall_s"]
        wall[1] += y["wall_s"]
        moved += x["n_moved"]
        if x["event_hash"] == y["event_hash"]:
            same += 1
        else:
            diff += 1
            print("hash differs", c, s, x["p99_makespan"], y["p99_makespan"], x["n_moved"], y["n_moved"], flush=True)
    print(f"MV-4 + stop vs MV-3 event hashes: same {same}, different {diff}, missing {miss}; tags {tags}; wall s {wall[0]:.0f} vs {wall[1]:.0f}; moves {moved}")
