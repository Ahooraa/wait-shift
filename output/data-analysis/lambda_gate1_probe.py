"""Lambda sweep, Gate 1 (2026-10-26): the full matrix, run only because Gate 0 passed decisively (flip rate 16-34% at
lam=0, vs the 15% threshold -- see knowledge/synthesis/workflow-aware-decision-rules.md, "Lambda sweep" section).

Matrix: lam in {0, 0.5, 1, 2} x k in {1, 5, 10} x {F1, F2} x seed in {1, 2} = 48 cells. lam=1 cells that already exist
(bit-verified reproducible) are read from their original locations instead of re-run:
  k=1, seed=1         -> results/envelope/{fam}_r0.85_k1.ours.json
  k=5, seed in {1,2}  -> results/p3_scaling/{fam}_r0.85_k5_s{seed}.ours.json
  k=10, seed=1        -> results/envelope/{fam}_r0.85_k10.ours.json
Missing lam=1 cells (k=1 seed=2, k=10 seed=2) are run fresh, same as every lam != 1 cell. 40 new runs total.

Primary metric: paired per-case Delta-P99(lam) = P99(lam) - P99(lam=1), same (fam, k, seed) -- never raw cross-cell P99.
Gate 1 passes if the best lam for F1 differs from F2's by more than the paired seed-1/seed-2 noise floor, at k=10.

  python lambda_gate1_probe.py run [workers] | analyze
"""
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(ROOT))

import d3s_headroom as d  # noqa: E402
import operating_envelope as oe  # noqa: E402
import p3_scaling_probe as p3  # noqa: E402
from frozen2 import FROZEN2, MOVE_PERIOD_S  # noqa: E402

from dfps.o3s import O3SimAdjuster  # noqa: E402
from dfps.sim import Sim  # noqa: E402
from dfps.variants import make_adjuster, sim_kwargs  # noqa: E402

RUNS = ROOT / "results" / "lambda_gate1"
RHO = 0.85
LAMS = (0.0, 0.5, 1.0, 2.0)
KS = (1, 5, 10)
FAMS = ("F1", "F2")
SEEDS = (1, 2)

# where an existing lam=1 cell can be read from instead of being re-run: (k, seed) -> (dir, filename template)
_EXISTING_LAM1 = {
    (1, 1): ("envelope", "{fam}_r0.85_k1.ours.json"),
    (5, 1): ("p3_scaling", "{fam}_r0.85_k5_s1.ours.json"),
    (5, 2): ("p3_scaling", "{fam}_r0.85_k5_s2.ours.json"),
    (10, 1): ("envelope", "{fam}_r0.85_k10.ours.json"),
}


def tag(fam, k, seed, lam):
    return f"{fam}_r{RHO}_k{k}_s{seed}_lam{lam}"


def existing_lam1(fam, k, seed):
    key = (k, seed)
    if key not in _EXISTING_LAM1:
        return None
    sub, tmpl = _EXISTING_LAM1[key]
    f = ROOT / "results" / sub / tmpl.format(fam=fam)
    return f if f.exists() else None


def one(args, duration=None, out=None):
    fam, k, seed, lam = args
    out = RUNS / f"{tag(fam, k, seed, lam)}.json" if out is None else out
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        return str(out)
    try:
        assert np.__version__.startswith("1."), "run with the Anaconda interpreter (numpy 1.26)"
        sc, X0 = p3.build(fam, k, seed)
        kw = sim_kwargs("B_STAR", oe.ASSUME)
        kw.update(warmup=d.WARMUP, duration=d.DURATION if duration is None else duration, retry_min_interval=1.0, retry_max_attempts=10)
        cand, extra = oe.CTRLS["ours"]
        adj = O3SimAdjuster(make_adjuster("B_STAR", oe.ASSUME, seed=seed + 300), MOVE_PERIOD_S[fam], epoch=60.0, horizon=120.0, K=5,
                            seed=seed + 800, warmup=d.WARMUP, blind=True, cand_mode=cand, churn=dict(FROZEN2, **extra, lam=lam))
        kw["interval"] = adj.next_interval
        t = time.time()
        sim = Sim(sc, X0, adjuster=adj, seed=seed + 400, trace=True, **kw)
        r = sim.run()
        sim.check_invariants()
        r["wall_s"] = time.time() - t
        from dfps.diagnostics import summarize
        try:
            diag = summarize(sim)
        except Exception:
            diag = {}
        out.write_text(json.dumps(dict(fam=fam, rho=RHO, k=k, seed=seed, lam=lam, result=r, diag=diag)))
        return str(out)
    except Exception:
        import traceback
        out.with_suffix(".err").write_text(traceback.format_exc())
        return str(out) + " FAILED"


def run(workers):
    RUNS.mkdir(parents=True, exist_ok=True)
    jobs = []
    for lam in LAMS:
        for k in KS:
            for fam in FAMS:
                for seed in SEEDS:
                    if lam == 1.0 and existing_lam1(fam, k, seed) is not None:
                        continue
                    jobs.append((fam, k, seed, lam))
    jobs = [j for j in jobs if not (RUNS / f"{tag(*j)}.json").exists()]
    print(f"{len(jobs)} runs", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        for r in ex.map(one, jobs):
            print("done", r, flush=True)


def p99(fam, k, seed, lam):
    if lam == 1.0:
        f = existing_lam1(fam, k, seed)
        if f is not None:
            return json.loads(f.read_text())["result"]["p99_makespan"]
    f = RUNS / f"{tag(fam, k, seed, lam)}.json"
    if not f.exists():
        return None
    return json.loads(f.read_text())["result"]["p99_makespan"]


def analyze():
    print("%-3s %3s %4s | " % ("fam", "k", "seed") + " | ".join("lam=%s" % l for l in LAMS) + " | dP99@best")
    noise = []
    for fam in FAMS:
        for k in KS:
            for seed in SEEDS:
                vals = {lam: p99(fam, k, seed, lam) for lam in LAMS}
                if any(v is None for v in vals.values()):
                    continue
                base = vals[1.0]
                dvals = {lam: vals[lam] - base for lam in LAMS}
                best_lam = min(dvals, key=lambda l: dvals[l])
                print("%-3s %3d %4d | " % (fam, k, seed) + " | ".join("%+7.1f" % dvals[l] for l in LAMS) +
                      " | best=%s (%+.1f)" % (best_lam, dvals[best_lam]))

    print("\nnoise floor (seed1 vs seed2, lam=1 baseline P99, matched fam/k):")
    for fam in FAMS:
        for k in KS:
            p1, p2 = p99(fam, k, 1, 1.0), p99(fam, k, 2, 1.0)
            if p1 is not None and p2 is not None:
                print(f"  {fam} k={k}: P99 seed1={p1:.1f} seed2={p2:.1f} |diff|={abs(p1-p2):.1f}")

    print("\nbest lam per (fam, k), seed1 vs seed2 -- Gate 1 check at k=10:")
    for fam in FAMS:
        for k in KS:
            bests = []
            for seed in SEEDS:
                vals = {lam: p99(fam, k, seed, lam) for lam in LAMS}
                if any(v is None for v in vals.values()):
                    continue
                best_lam = min(vals, key=lambda l: vals[l])
                bests.append((seed, best_lam, vals[best_lam] - vals[1.0]))
            print(f"  {fam} k={k}: " + ", ".join(f"seed{s}: lam={bl} (dP99={d:+.1f})" for s, bl, d in bests))


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 4)
    else:
        analyze()
