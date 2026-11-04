"""Wait-weight test (pre-registered 2 Nov 2026, knowledge/synthesis/workflow-aware-decision-rules.md, "Wait-weight test").
The move rule's finish-time estimate with the predicted queue wait weighted 0.5 (churn["wait_w"] = 0.5, variant W05 of
placement_extensions.EXTRA); everything else is cell D of grid2x2_v2.py. The 18 development cases. Reference = geometric mean of
the three null runs per case (D at 4 s, and the placebos P1/P2), exactly as in move_gap_probe.py.

  python wait_weight.py run [workers]    18 runs (resumable)
  python wait_weight.py check            wait_w = 1.0 (default) still reproduces a stored D run exactly?
  python wait_weight.py report           the pre-registered reading
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
import placement_extensions as pe  # noqa: E402
import move_gap_probe as mg  # noqa: E402

NAME = sys.argv[2] if len(sys.argv) > 2 and sys.argv[1] != "run" else "W05"   # report: name of the variant (W05, T05, T10)


def run(workers, names=(NAME,)):
    todo = [("T1", pe.tag(f, r, s), n, s, f, "T1") for n in names for f, r, s in mg.cases()
            if not (pe.RES / "T1" / f"{pe.tag(f, r, s)}.{n}.json").exists()]
    print(f"{len(todo)} runs, {workers} workers", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        for r in ex.map(pe.job, todo):
            print("done", r, flush=True)


def report():
    ref, runs = pe.t1_load()
    nulls = {k: [ref[k]["p99_makespan"]] + [runs[p][k]["p99_makespan"] for p in pe.PLACEBO if p in runs and k in runs[p]]
             for k in sorted(ref)}
    ks = [k for k in nulls if len(nulls[k]) == 3 and NAME in runs and k in runs[NAME]]
    if not ks:
        print("no complete cases yet")
        return
    w = runs[NAME]
    e = [np.log(w[k]["p99_makespan"]) - np.mean(np.log(nulls[k])) for k in ks]
    lo, hi = mg.boot_ci(e)
    pct = lambda v: (np.exp(v) - 1) * 100
    print(f"=== {NAME} vs the geometric mean of three null runs ({len(ks)} of 18 cases) ===")
    print(f"P99 {pct(np.mean(e)):+.1f}%  95% CI [{pct(lo):+.1f}, {pct(hi):+.1f}]%  better in {sum(x < 0 for x in e)}/{len(ks)}")
    for fam in pe.FAMS:
        for rho in pe.RHOS:
            kk = [k for k in ks if k[0] == fam and k[1] == rho]
            ee = [np.log(w[k]["p99_makespan"]) - np.mean(np.log(nulls[k])) for k in kk]
            print(f"  {fam} {int(rho * 100):2d}%: {pct(np.mean(ee)):+6.1f}%  per seed " + " ".join(f"{pct(x):+5.1f}" for x in ee))
    mv0 = np.mean([ref[k]["n_moved"] / max(1, ref[k]["n_completed"]) for k in ks])
    mv = np.mean([w[k]["n_moved"] / max(1, w[k]["n_completed"]) for k in ks])
    cold = np.mean([w[k]["cold_starts"] / ref[k]["cold_starts"] for k in ks]) - 1
    p95 = np.exp(np.mean([np.log(w[k]["p95_makespan"]) - np.log(ref[k]["p95_makespan"]) for k in ks])) - 1
    print(f"moves/request {mv:.2f} vs {mv0:.2f}   cold starts {cold * 100:+.1f}%   P95 {p95 * 100:+.1f}%")
    e50 = [np.log(w[k]["p99_makespan"]) - np.mean(np.log(nulls[k])) for k in ks if k[1] == 0.5]
    m50 = pct(np.mean(e50)) if e50 else float("nan")
    ok = pct(np.mean(e)) <= -3 and hi < 0 and cold <= 0.20 and (np.isnan(m50) or m50 <= 1.0)
    print(f"50% load: {m50:+.1f}%")
    print("verdict:", "PASSES the development bar -> confirm on fresh seeds 11-16" if ok else "FAILS the development bar")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "run":
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 8, tuple(sys.argv[3:]) or ("W05",))
    elif cmd == "check":
        pe.check()
    else:
        report()
