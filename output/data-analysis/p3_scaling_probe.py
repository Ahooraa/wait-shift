"""P3 scaling probe (2026-10-25): does the data-intensity advantage over the stack grow as a family/load-invariant
increment in k, or a law in tau (measured transfer share of the critical path)?

Pre-registration: knowledge/synthesis/workflow-aware-decision-rules.md, "P3 scaling probe" section.

Starting point (zero new runs, from the existing results/envelope/*.json grid, k in {1,10}, 4 loads, both families):
Delta-gap(k=1->10) = gap(k=10) - gap(k=1) clusters at 30-43 points for every (fam, load) cell at <=85% load, while raw
gap(k=1) alone ranges 7.6-28.7% -- i.e. the INCREMENT looks family/load-invariant even though the baseline is not. At 92%
load this breaks down in OPPOSITE directions per family (F1 drops to +17.5, F2 goes to -14.4) -- a different, load-collapse
mechanism (see novelty-register.md), excluded from this fit by design. tau (measured transfer share, from diag["all_transfer"]
/ diag["all_soj"], already stored by every envelope run) correlates with Delta-gap at only r=0.249 on those 6 existing
points (95% CI roughly [-0.71, 0.88] -- indistinguishable from zero at n=6). tau is therefore an EXPLORATORY secondary
variable here, not the mechanism claim: the primary claim is the k-invariance of Delta-gap itself, true or not regardless
of what tau does.

Design (rho = 0.85 only, to isolate k from load; the existing 4-load x {k=1,10} grid is the load cross-check, not part of
this fit):
  - fine sweep:   k in {0.5, 2, 3, 5, 7} x {F1,F2} x {ours,stack}, seed 1           = 20 runs
  - noise check:  k in {3, 5} x {F1,F2} x {ours,stack}, seed 2                      = 8 runs
  28 runs total. k=0.5 locates (or fails to locate) the crossover where the advantage reaches zero; do not extrapolate
  past it if the gap there is still positive. k=1 and k=10 at rho=0.85 are read from results/envelope/, not re-run.

  python p3_scaling_probe.py run [workers] | analyze
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
import workflow_stress as w  # noqa: E402
from frozen2 import FROZEN2, MOVE_PERIOD_S  # noqa: E402

from dfps.o3s import O3SimAdjuster  # noqa: E402
from dfps.sim import Sim  # noqa: E402
from dfps.variants import make_adjuster, sim_kwargs  # noqa: E402

RUNS = ROOT / "results" / "p3_scaling"
RHO = 0.85
FAMS = ("F1", "F2")
CTRLS = oe.CTRLS
FINE_KS = (0.5, 2, 3, 5, 7)
NOISE_KS = (3, 5)
NOISE_SEED = 2


def build(fam, k, seed):
    """Same as operating_envelope.build, generalised over seed (oe.build hardcodes SEED=1)."""
    sc = __import__("dfps.traces", fromlist=["x"]).build_trace_scenario(
        fam, RHO, seed, "dev", d.DURATION + d.WARMUP, 60.0, ne=80, n_workflows=15,
        alibaba_dags=oe.alibaba_dags(), pool_size=oe.ASSUME["A17_function_pool_size"],
        counts=__import__("dfps.traces", fromlist=["x"]).load_counts(fam, "dev"))
    sc = w.scale(sc, k)
    X0 = oe.initial_layout(sc, seed, oe.ASSUME["A06_generations"])
    return sc, X0


def tag(fam, k, seed, ctrl):
    return f"{fam}_r{RHO}_k{k}_s{seed}.{ctrl}"


def one(args, duration=None, out=None):
    fam, k, seed, ctrl = args
    out = RUNS / f"{tag(fam, k, seed, ctrl)}.json" if out is None else out
    if out.exists():
        return str(out)
    try:
        assert np.__version__.startswith("1."), "run with the Anaconda interpreter (numpy 1.26)"
        sc, X0 = build(fam, k, seed)
        kw = sim_kwargs("B_STAR", oe.ASSUME)
        kw.update(warmup=d.WARMUP, duration=d.DURATION if duration is None else duration, retry_min_interval=1.0, retry_max_attempts=10)
        cand, extra = CTRLS[ctrl]
        adj = O3SimAdjuster(make_adjuster("B_STAR", oe.ASSUME, seed=seed + 300), MOVE_PERIOD_S[fam], epoch=60.0, horizon=120.0, K=5,
                            seed=seed + 800, warmup=d.WARMUP, blind=True, cand_mode=cand, churn=dict(FROZEN2, **extra))
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
        out.write_text(json.dumps(dict(fam=fam, rho=RHO, k=k, seed=seed, ctrl=ctrl, result=r, diag=diag)))
        return str(out)
    except Exception:
        import traceback
        out.with_suffix(".err").write_text(traceback.format_exc())
        return str(out) + " FAILED"


def run(workers):
    RUNS.mkdir(parents=True, exist_ok=True)
    jobs = [(f, k, 1, c) for k in FINE_KS for f in FAMS for c in CTRLS]
    jobs += [(f, k, NOISE_SEED, c) for k in NOISE_KS for f in FAMS for c in CTRLS]
    jobs = [j for j in jobs if not (RUNS / f"{tag(*j)}.json").exists()]
    print(f"{len(jobs)} runs", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        for r in ex.map(one, jobs):
            print("done", r, flush=True)


def _tau(diag):
    return diag["all_transfer"] / diag["all_soj"] if diag.get("all_soj") else float("nan")


def analyze():
    rows = {}
    for f in RUNS.glob("*.json"):
        x = json.loads(f.read_text())
        rows[(x["fam"], x["k"], x["seed"], x["ctrl"])] = x
    # also pull k=1, k=10, seed=1 from the existing envelope grid at rho=0.85
    for f in (ROOT / "results" / "envelope").glob(f"*_r{RHO}_k*.json"):
        x = json.loads(f.read_text())
        rows[(x["fam"], x["k"], 1, x["ctrl"])] = x

    all_ks = sorted(set(k for (_, k, s, _) in rows if s == 1))
    print("%-4s %4s %4s | %8s %8s %7s | %7s" % ("fam", "k", "seed", "ours P99", "stack P99", "gap%", "tau_o"))
    cells = {}
    for fam in FAMS:
        for seed in (1, NOISE_SEED):
            for k in all_ks if seed == 1 else NOISE_KS:
                a, b = rows.get((fam, k, seed, "ours")), rows.get((fam, k, seed, "stack"))
                if not a or not b:
                    continue
                ra, rb = a["result"], b["result"]
                gap = 100 * (rb["p99_makespan"] - ra["p99_makespan"]) / rb["p99_makespan"]
                tau_o = _tau(a.get("diag", {}))
                print("%-4s %4s %4d | %8.1f %8.1f %6.1f%% | %6.3f" % (fam, k, seed, ra["p99_makespan"], rb["p99_makespan"], gap, tau_o))
                cells[(fam, k, seed)] = (gap, tau_o)

    print("\nDelta-gap(k) = gap(k) - gap(k=1), seed 1 only:")
    for fam in FAMS:
        base = cells.get((fam, 1, 1))
        if not base:
            continue
        g1, t1 = base
        for k in all_ks:
            if k == 1 or (fam, k, 1) not in cells:
                continue
            gk, tk = cells[(fam, k, 1)]
            print(f"  {fam} k={k:>4}: dGap={gk - g1:+6.1f}  dTau={tk - t1:+.3f}")

    print("\nnoise check (seed1 vs seed2 at matched k):")
    for fam in FAMS:
        for k in NOISE_KS:
            c1, c2 = cells.get((fam, k, 1)), cells.get((fam, k, NOISE_SEED))
            if c1 and c2:
                print(f"  {fam} k={k}: gap seed1={c1[0]:.1f}%  seed2={c2[0]:.1f}%  |diff|={abs(c1[0]-c2[0]):.1f}")


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 4)
    else:
        analyze()
