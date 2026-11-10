"""MV-4 against MV-3 (arm fill1): same event hash? python mv4_check.py smoke | run <workers>"""
import sys, json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
ROOT = next(p for p in (Path("D:/DFPS implementation"), Path.home() / "DFPS-implementation") if p.exists())
sys.path[:0] = [str(ROOT / "output" / "data-analysis"), str(ROOT)]
CASES = [f"{f}_r{r}_s{s}" for s in (1, 2, 3, 7, 8, 9, 10) for f in ("F1", "F2") for r in (0.5, 0.7, 0.85)]
SUF = ("", "_p1", "_p2")
OUT = ROOT / "results" / "capW1_rows"


def job(a):
    import capw1_rows as R
    return R.run_job(a)


def compare(todo):
    same, diff, miss, tags, wall = 0, 0, 0, {}, [0.0, 0.0]
    for c, s in todo:
        p, q = OUT / f"{c}.mv4{s}.json", OUT / f"{c}.fill1{s}.json"
        if not p.exists():
            miss += 1
            continue
        x, y = json.loads(p.read_text())["result"], json.loads(q.read_text())["result"]
        tags[x.get("mover_impl")] = tags.get(x.get("mover_impl"), 0) + 1
        wall[0] += x["wall_s"]; wall[1] += y["wall_s"]
        if x["event_hash"] == y["event_hash"]:
            same += 1
        else:
            diff += 1
            print("hash differs", c, s, x["p99_makespan"], y["p99_makespan"], x["n_moved"], y["n_moved"])
    print(f"MV-4 vs MV-3 event hashes: same {same}, different {diff}, missing {miss}; tags {tags}; wall s {wall[0]:.0f} vs {wall[1]:.0f}")


if __name__ == "__main__":
    if sys.argv[1] == "smoke":
        print(job(("F1_r0.85_s7", "mv4")))
        compare([("F1_r0.85_s7", "")])
    else:
        todo = [(c, s) for c in CASES for s in SUF]
        with ProcessPoolExecutor(int(sys.argv[2])) as ex:
            for r in ex.map(job, [(c, "mv4" + s) for c, s in todo]):
                if "FAILED" in r:
                    print(r, flush=True)
        compare(todo)
