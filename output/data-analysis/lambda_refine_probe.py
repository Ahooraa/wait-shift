"""Lambda sweep refinement (2026-10-26): pin down the minimum near k=10, where Gate 1's U-shaped curve was steepest and
most informative (lam=0.5 beat both lam=0 and lam=1 there, by a widening margin as k grew; see
knowledge/synthesis/workflow-aware-decision-rules.md, "Lambda sweep" section). Reuses lambda_gate1_probe.one() directly --
no new simulation logic, just two more lam values at the one k where the curve's shape matters most.

8 cells: lam in {0.25, 0.75} x {F1, F2} x seed in {1, 2}, k=10 fixed.

  python lambda_refine_probe.py run [workers] | analyze
"""
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import lambda_gate1_probe as g1  # noqa: E402

K = 10
LAMS = (0.25, 0.75)


def run(workers):
    jobs = [(fam, K, seed, lam) for lam in LAMS for fam in g1.FAMS for seed in g1.SEEDS]
    jobs = [j for j in jobs if not (g1.RUNS / f"{g1.tag(*j)}.json").exists()]
    print(f"{len(jobs)} runs", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        for r in ex.map(g1.one, jobs):
            print("done", r, flush=True)


def analyze():
    import json
    base = {}
    for fam in g1.FAMS:
        for seed in g1.SEEDS:
            f = g1.existing_lam1(fam, K, seed) or (g1.RUNS / f"{g1.tag(fam, K, seed, 1.0)}.json")
            base[(fam, seed)] = json.loads(f.read_text())["result"]["p99_makespan"] if f.exists() else None
    print("%-3s %4s | %7s %7s %7s %7s %7s %7s" % ("fam", "seed", "d@0", "d@0.25", "d@0.5", "d@0.75", "d@1", "d@2"))
    for fam in g1.FAMS:
        for seed in g1.SEEDS:
            b = base[(fam, seed)]
            if b is None:
                continue
            ds = []
            for lam in (0.0, 0.25, 0.5, 0.75, 1.0, 2.0):
                f = g1.RUNS / f"{g1.tag(fam, K, seed, lam)}.json"
                v = json.loads(f.read_text())["result"]["p99_makespan"] if f.exists() else None
                ds.append("%+7.1f" % (v - b) if v is not None else "   --  ")
            print("%-3s %4d | %s" % (fam, seed, " ".join(ds)))


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 4)
    else:
        analyze()
