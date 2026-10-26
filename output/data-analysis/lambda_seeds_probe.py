"""Lambda sweep, seed expansion (2026-10-26): more seeds at k=10, not more lam values -- the refinement
(lambda_refine_probe.py) located a plateau (lam in [0.25, 0.5] both beat lam=1 by a wide margin) but could not
resolve the 0.25-vs-0.5 difference (~5 pooled points) against the seed-to-seed noise floor (seed swings of tens of
points). Originally decided NOT worth ~10 seeds/cell for a ~1-point payoff (see
knowledge/synthesis/workflow-aware-decision-rules.md, "Lambda sweep" section) -- decision reversed by the user same
day; this script runs it anyway.

Reuses lambda_gate1_probe.one() directly (same sim, same output schema, same RUNS dir) -- no new simulation logic.

8 new seeds (3-10) x 6 lam values x 2 families = 96 runs, k=10 fixed.

  python lambda_seeds_probe.py run [workers] | analyze
"""
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import lambda_gate1_probe as g1  # noqa: E402

K = 10
LAMS = (0.0, 0.25, 0.5, 0.75, 1.0, 2.0)
SEEDS = tuple(range(3, 11))


def run(workers):
    jobs = [(fam, K, seed, lam) for lam in LAMS for fam in g1.FAMS for seed in SEEDS]
    jobs = [j for j in jobs if not (g1.RUNS / f"{g1.tag(*j)}.json").exists()]
    print(f"{len(jobs)} runs", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        for r in ex.map(g1.one, jobs):
            print("done", r, flush=True)


def analyze():
    import json
    import statistics as st

    print("%-3s %4s | " % ("fam", "seed") + " | ".join("lam=%s" % l for l in LAMS))
    per_lam = {(fam, lam): [] for fam in g1.FAMS for lam in LAMS}
    for fam in g1.FAMS:
        for seed in (1, 2) + SEEDS:
            vals = {}
            for lam in LAMS:
                f = g1.RUNS / f"{g1.tag(fam, K, seed, lam)}.json"
                if not f.exists() and lam == 1.0:
                    e = g1.existing_lam1(fam, K, seed)
                    f = e if e is not None else f
                vals[lam] = json.loads(f.read_text())["result"]["p99_makespan"] if f.exists() else None
            if any(v is None for v in vals.values()):
                continue
            base = vals[1.0]
            ds = {l: vals[l] - base for l in LAMS}
            for l in LAMS:
                per_lam[(fam, l)].append(ds[l])
            print("%-3s %4d | " % (fam, seed) + " | ".join("%+7.1f" % ds[l] for l in LAMS))

    print("\nper (fam, lam): mean dP99, stdev, n (pools all seeds with complete rows above)")
    for fam in g1.FAMS:
        for lam in LAMS:
            xs = per_lam[(fam, lam)]
            if len(xs) < 2:
                continue
            print(f"  {fam} lam={lam}: mean={st.mean(xs):+.1f} sd={st.stdev(xs):.1f} n={len(xs)}")

    print("\n0.25 vs 0.5, paired per seed (same fam, same seed):")
    for fam in g1.FAMS:
        diffs = []
        n = min(len(per_lam[(fam, 0.25)]), len(per_lam[(fam, 0.5)]))
        for i in range(n):
            diffs.append(per_lam[(fam, 0.25)][i] - per_lam[(fam, 0.5)][i])
        if diffs:
            print(f"  {fam}: mean(d0.25 - d0.5)={st.mean(diffs):+.2f} sd={st.stdev(diffs) if len(diffs)>1 else 0:.2f} n={len(diffs)}")


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 4)
    else:
        analyze()
