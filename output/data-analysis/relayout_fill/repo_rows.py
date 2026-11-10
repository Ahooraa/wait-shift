"""Re-run PL-5 and PL-5p on the 42 cases x 3 clocks through the repo code, then compare event hashes with the prototype runs. python repo_rows.py run <workers> | check"""
import sys, json, os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = next(p for p in (Path("D:/DFPS implementation"), Path.home() / "DFPS-implementation") if p.exists())
sys.path.insert(0, str(ROOT / "output" / "data-analysis"))
CASES = [f"{f}_r{r}_s{s}" for s in (1, 2, 3, 7, 8, 9, 10) for f in ("F1", "F2") for r in (0.5, 0.7, 0.85)]
MAP = {"fill1": "ratio1", "fill8": "ratio8"}
SUF = ("", "_p1", "_p2")


def job(a):
    import capw1_rows as R
    return R.run_job(a)


if __name__ == "__main__":
    if sys.argv[1] == "run":
        todo = [(c, a + s) for a in MAP for c in CASES for s in SUF]
        with ProcessPoolExecutor(int(sys.argv[2])) as ex:
            for r in ex.map(job, todo):
                if "FAILED" in r:
                    print(r, flush=True)
    same, diff, miss, tags = 0, 0, 0, {}
    for a, b in MAP.items():
        for c in CASES:
            for s in SUF:
                p, q = ROOT / "results" / "capW1_rows" / f"{c}.{a}{s}.json", ROOT / "results" / "relayout_fill" / f"{c}.{b}{s}.json"
                if not (p.exists() and q.exists()):
                    miss += 1
                    continue
                x, y = json.loads(p.read_text())["result"], json.loads(q.read_text())["result"]
                tags[x.get("place_impl")] = tags.get(x.get("place_impl"), 0) + 1
                if x["event_hash"] == y["event_hash"]:
                    same += 1
                else:
                    diff += 1
                    print("hash differs", c, a + s, x["p99_makespan"], y["p99_makespan"])
    print(f"repo vs prototype event hashes: same {same}, different {diff}, missing {miss}; tags {tags}")
