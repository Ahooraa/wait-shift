"""Lambda sweep, Gate 0 -- free re-scoring (2026-10-26). Does the downstream-transfer weight in the move rule (lam=1.0 by
construction, never tested) have any leverage at all, before spending runs on an actual sweep?

Pre-registration: knowledge/synthesis/workflow-aware-decision-rules.md, "Lambda sweep" section.

6 runs, k in {1, 5, 10} x {F1, F2}, seed 1, controller "ours" only, full duration, lam=1.0 (unweighted, unchanged
behaviour -- verified bit-reproducible against the existing k=5 cell). churn["log_lambda_components"]=True makes
O3SimAdjuster log, at every evaluated move decision, the lam=1.0 decomposition (inp, service_estimate, out) of the
current node and every candidate it compared against (dfps/o3s.py: self.lambda_log). This needs no simulated lam' --
`analyze()` recomputes inp+service+lam'*out for each hypothetical lam' in {0, 0.5, 2} and asks whether the chosen action
(stay, or move to a specific node) would change. That is the flip rate. Caveat (restated from the pre-registration): this
ignores how a flipped decision would change later queue state, so it is a sensitivity diagnostic, not a P99 estimate.

  python lambda_probe.py run [workers] | analyze
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

RUNS = ROOT / "results" / "lambda_gate0"
RHO = 0.85
KS = (1, 5, 10)
FAMS = ("F1", "F2")
SEED = 1
LAM_PRIMES = (0.0, 0.5, 2.0)


def tag(fam, k):
    return f"{fam}_r{RHO}_k{k}_s{SEED}"


def one(args, duration=None, out=None):
    fam, k = args
    out = RUNS / f"{tag(fam, k)}.json" if out is None else out
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        return str(out)
    try:
        assert np.__version__.startswith("1."), "run with the Anaconda interpreter (numpy 1.26)"
        sc, X0 = p3.build(fam, k, SEED)
        kw = sim_kwargs("B_STAR", oe.ASSUME)
        kw.update(warmup=d.WARMUP, duration=d.DURATION if duration is None else duration, retry_min_interval=1.0, retry_max_attempts=10)
        cand, extra = oe.CTRLS["ours"]
        adj = O3SimAdjuster(make_adjuster("B_STAR", oe.ASSUME, seed=SEED + 300), MOVE_PERIOD_S[fam], epoch=60.0, horizon=120.0, K=5,
                            seed=SEED + 800, warmup=d.WARMUP, blind=True, cand_mode=cand,
                            churn=dict(FROZEN2, **extra, log_lambda_components=True))
        kw["interval"] = adj.next_interval
        t = time.time()
        sim = Sim(sc, X0, adjuster=adj, seed=SEED + 400, trace=True, **kw)
        r = sim.run()
        sim.check_invariants()
        r["wall_s"] = time.time() - t
        out.write_text(json.dumps(dict(fam=fam, rho=RHO, k=k, seed=SEED, result=r, lambda_log=adj.lambda_log)))
        return str(out)
    except Exception:
        import traceback
        out.with_suffix(".err").write_text(traceback.format_exc())
        return str(out) + " FAILED"


def run(workers):
    RUNS.mkdir(parents=True, exist_ok=True)
    jobs = [(f, k) for k in KS for f in FAMS]
    jobs = [j for j in jobs if not (RUNS / f"{tag(*j)}.json").exists()]
    print(f"{len(jobs)} runs", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        for r in ex.map(one, jobs):
            print("done", r, flush=True)


def _score(parts, lam):
    inp, svc, out = parts
    return inp + svc + lam * out


def flip_rate(lambda_log, lam_prime):
    """Fraction of logged decisions whose chosen action (stay, or move to a specific node) changes between lam=1 (the
    action actually taken, last element of each record) and lam_prime (recomputed from the logged lam=1 decomposition)."""
    n, flips = 0, 0
    for _now, cur_parts, cand_log, accepted_k2 in lambda_log:
        n += 1
        scores = {None: _score(cur_parts, lam_prime)}
        for k2, parts in cand_log:
            scores[k2] = _score(parts, lam_prime)
        new_best = min(scores, key=scores.get)
        new_action = new_best if scores[new_best] < scores[None] else None
        if new_action != accepted_k2:
            flips += 1
    return flips / n if n else float("nan"), n


def analyze():
    print("%-3s %3s | %7s | %8s %8s %8s" % ("fam", "k", "n_dec", "flip@0", "flip@0.5", "flip@2"))
    for fam in FAMS:
        for k in KS:
            f = RUNS / f"{tag(fam, k)}.json"
            if not f.exists():
                continue
            x = json.loads(f.read_text())
            log = x["lambda_log"]
            rates = [flip_rate(log, lp) for lp in LAM_PRIMES]
            n = rates[0][1]
            print("%-3s %3d | %7d | %7.1f%% %7.1f%% %7.1f%%" % (fam, k, n, 100*rates[0][0], 100*rates[1][0], 100*rates[2][0]))


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 4)
    else:
        analyze()
