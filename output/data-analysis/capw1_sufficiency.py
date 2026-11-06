"""FaaSPR path-sufficiency check (pre-registered in knowledge/synthesis/independent-baselines-capw1.md, section 5). Three development cases x 60/300/1500
sampled paths per workflow, 900 s, CAP-W1.   python capw1_sufficiency.py run [workers] | report"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import capw1_independent as I  # noqa: E402

OUT = I.ROOT / "results" / "capW1_suff"
CASES = ("F1_r0.7_s1", "F2_r0.7_s2", "F1_r0.85_s3")
NP = (60, 300, 1500)


def run(workers):
    jobs = [(c, "faaspr", I.DURATION, str(OUT / f"p{n}"), n) for n in NP[::-1] for c in CASES if not (OUT / f"p{n}" / f"{c}.faaspr.json").exists()]
    print(len(jobs), "runs", flush=True)
    with ProcessPoolExecutor(workers, initializer=I._low_priority) as ex:
        for r in ex.map(I.run_job, jobs):
            print("done", r, flush=True)


def report():
    R = {}
    for n in NP:
        for c in CASES:
            p = OUT / f"p{n}" / f"{c}.faaspr.json"
            if p.exists():
                R[(n, c)] = json.loads(p.read_text())
    print("case, paths | P99, avg | cold | slack LPs (in-window) | repaired req share | unplanned share | solve ms")
    for c in CASES:
        for n in NP:
            if (n, c) not in R:
                continue
            j = R[(n, c)]; r = j["result"]; i = j["info"]; w = i["window"]
            lg = [x for x in i["solve_log"] if x[0] < I.DURATION]
            slack = sum(x[2] for x in lg) / max(1, sum(x[1] for x in lg))
            rep = w["rep_req"] / max(1, w["pure"] + w["rep_req"])
            print(f"{c:12s} {n:5d} | {r['p99_makespan']:7.1f} {r['avg_makespan']:6.1f} | {r['cold_starts']:5d} | {slack:5.2f} | {rep:5.3f} | {w['unplanned'] / max(1, w['arrived']):5.3f} | {i['solve_ms_mean']:7.0f}")
    for n in (60, 300):
        lr = [np.log(R[(n, c)]["result"]["p99_makespan"] / R[(1500, c)]["result"]["p99_makespan"]) for c in CASES if (n, c) in R and (1500, c) in R]
        if lr:
            print(f"P99({n}) / P99(1500): geometric mean {np.exp(np.mean(lr)):.3f}, per case {[round(float(np.exp(x)), 3) for x in lr]}")
    lr = [np.log(R[(300, c)]["result"]["p99_makespan"] / R[(1500, c)]["result"]["p99_makespan"]) for c in CASES if (300, c) in R and (1500, c) in R]
    if len(lr) == len(CASES):
        gm = float(np.exp(np.mean(lr)))
        ok = abs(gm - 1) <= 0.03 and max(abs(np.exp(x) - 1) for x in lr) <= 0.10
        print("decision rule (300 within 3% geometric mean, no case beyond 10%):", "300 paths kept" if ok else "use 1500 paths for the held-out run")


if __name__ == "__main__":
    run(int(sys.argv[2]) if len(sys.argv) > 2 else 3) if sys.argv[1] == "run" else report()
