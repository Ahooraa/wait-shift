"""Match FaaSPR's own trace-generation and cluster setup, NOT its 6 named workflows (2026-10-26).

Why not the workflows too: tracked down all of the paper's own citations for Video Processing/Driver Searching/
ResNet50 Training/Checklist Review/Calculator/Travel Guide (refs [4]-[6], [38]-[41]) -- none give per-task execution
time or data-size numbers, two of the cited URLs no longer resolve to that content at all, and ref [40]'s own citation
is internally broken (wrong org, duplicate URL of ref [39]). Reproducing them would mean inventing timing/size numbers
from memory, which this project does not do. See knowledge/sources/jia-2025-faaspr.md section 15 and
knowledge/_meta/log.md (2026-10-26) for the full account. Per the user's explicit decision, this instead matches the
two axes that ARE fully recoverable from the paper's text, and keeps our own workflow/task DAG corpus (SeBS-Flow/
Alibaba mix) exactly as used everywhere else in the project:

  trace    Azure Function Dataset (F1) "top 2% frequent invocation traces" (p. 10), not this project's usual
           top-200-by-volume selection. Top-2% count derived empirically, not assumed: 46412 distinct
           (HashOwner,HashApp,HashFunction) triples on Azure-2019 day 1 -> ceil(0.02*46412) = 929 -- this is the BAND
           the paper draws from, not a sum. The paper's own sentence (verbatim, re-checked against the PDF after the
           first version of this script overloaded the cluster 7.7x): "the trace is extracted from the top 2%
           frequent invocation traces, with the average and peak invocation frequencies of 203.8 req/min and 264
           req/min, respectively" -- that describes ONE representative trace's own rate, not an aggregate over 929
           functions. Fixed by `rate_matched_rows()`: instead of a uniform-random draw across the whole top-929 band
           (whose per-function rate spans orders of magnitude, hence the overload), it selects the n_workflows traces
           whose own average per-minute count lands nearest 203.8, one per workflow -- same structural slot
           `trace_series()` fills elsewhere in this project, just rate-matched instead of randomly drawn. Raw per-minute
           counts are then converted DIRECTLY to Poisson arrival rates (no rescaling to a target utilisation rho) --
           the paper has no "rho" knob; its load level is whatever the real top-2% trace's own magnitude produces
           against its own cluster capacity, and matching that means not overriding it with our own project's rho
           convention. Residual mismatch, measured not assumed: the paper drives ONE workflow family at a time with
           this single trace; this project's convention runs 15 concurrent workflow types, each individually
           rate-matched to ~203.8 req/min, so the first version of this fix (one matched trace per workflow, no
           further scaling) measured offered_util_mean=3.61 against the matched 322-slot cluster -- confirmed
           saturated, not a units bug. Per the user's explicit decision, every workflow's matched trace is then scaled
           down by the SAME constant `1/n_workflows` (AGGREGATE_SCALE below) so the aggregate offered load across all
           15 concurrent types lands near what the paper's single-workflow run would offer that cluster, rather than
           ~15x it. This keeps the within-type trace *shape* rate-matched (still drawn from the 203.8-req/min
           neighbourhood) while making the many-workflow aggregate the comparable quantity -- replacing our 15-type
           corpus with the paper's single named workflow was rejected earlier in this investigation (workflow
           benchmarks are the one axis NOT being matched here, see above), so this is the practical proxy once that
           corpus is kept.
  cluster  8 worker servers (paper: CloudLab, 8 of 10 nodes as workers; the paper's own edge scenarios elsewhere use
           ne=80 -- this one-off setup is 8, not a typo), flat all-to-all topology (hop=1 to every other server, 0 to
           self -- the paper's workers sit behind one switch/rack, no multi-hop edge tiers, matching our own "hop=0
           within a node" abstraction), 50MB/s bandwidth (p. 10, their stated default). Per-server capacity drawn
           ~ Normal(mean, 0.8*mean) clipped to >= 1 slot (p. 10: "sampled from a normal distribution with a standard
           deviation of 0.8"), normalised to sum to an EQUIVALENT slot count derived from the paper's ~402GB total
           and its own 0.5-2GB per-instance memory range (mean ~1.25GB) -> ~322 slots, ~40/server average. This is a
           documented unit conversion, not a claim that our model has per-function memory: every instance occupies
           one uniform slot in our simulator (confirmed in dfps/controllers.py::faaspr_placement's own docstring,
           adaptation 2), same abstraction as every other baseline in this project.

What stays OURS (the user's explicit decision): the workflow/task DAG corpus (SeBS-Flow/Alibaba mix, n_workflows=15,
pool_size as elsewhere), per-task duration/cold-start/state-size ranges (DFPS Table 2), and per-node storage capacity
(esc) -- the paper gives no number to match for the last one, so it keeps our project's existing default range.

Reuses faaspr_fig11.py's instrumentation (transfer/cold/queue breakdown) unchanged.

  python -I output/data-analysis/faaspr_match_setup.py [variant,...]
"""
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(ROOT))

import d3s_headroom as d  # noqa: E402
import operating_envelope as oe  # noqa: E402
from frozen2 import FROZEN2, MOVE_PERIOD_S  # noqa: E402

import yaml  # noqa: E402

import faaspr_fig11 as fig11  # noqa: E402

from dfps.dispatchers import FaaSPRRouter  # noqa: E402
from dfps.network import Network  # noqa: E402
from dfps.o3s import O3SimAdjuster  # noqa: E402
from dfps.sim import Sim  # noqa: E402
from dfps.traces import load_counts, offered_load_profile, thin_arrivals  # noqa: E402
from dfps.variants import make_adjuster, sim_kwargs  # noqa: E402
from dfps.workload import build_scenario  # noqa: E402

ASSUME = yaml.safe_load((ROOT / "config" / "assumptions.yaml").read_text(encoding="utf-8"))
OUT = ROOT / "output" / "data-analysis" / "results"
N_SERVERS = 8
BW_MATCHED = 50.0                                    # MB/s (paper, p. 10, default bandwidth)
TOTAL_SLOTS = 322                                    # ~402GB / ~1.25GB-per-instance midpoint of the paper's 0.5-2GB range
SD_FRAC = 0.8                                         # paper's stated per-server capacity sd, as a fraction of the mean
TOP_FRAC = 0.02                                       # paper's "top 2% frequent invocation traces"
N_DISTINCT_F1 = 46412                                 # distinct Azure-2019 functions on day 1 (input/data/azure/.../d01.csv)
TOP_N = int(np.ceil(TOP_FRAC * N_DISTINCT_F1))        # 929
VARIANTS = {"ours": ("nosim", dict(lam=0.5), False), "fp_place": ("nosim", dict(placement="faaspr", lam=0.5), False),
            "fp_route": ("nosim", dict(lam=0.5), True), "fp_both": ("nosim", dict(placement="faaspr", lam=0.5), True)}
# lam=0.5 on every row (all keep our request moves) -- see faaspr_fig11.py's VARIANTS comment.


TARGET_AVG_REQ_MIN = 203.8                            # paper's own representative-trace average (p. 10)
N_WORKFLOWS = 15
AGGREGATE_SCALE = 1.0 / N_WORKFLOWS                   # 15 concurrent matched traces -> 1 paper-equivalent aggregate load


def rate_matched_rows(counts, n_rows, target_avg=TARGET_AVG_REQ_MIN):
    """Pick the n_rows traces from the top-2% pool whose own average per-minute count lands nearest the paper's
    203.8 req/min, one per workflow -- NOT a uniform-random draw across the whole band (see module docstring)."""
    avg = counts.mean(axis=1)
    order = np.argsort(np.abs(avg - target_avg))
    return order[:n_rows]


def matched_cluster(seed):
    """8 servers, flat topology, 50MB/s, capacity ~ Normal(mean, 0.8*mean) clipped >= 1, summing to TOTAL_SLOTS."""
    rng = np.random.default_rng(seed + 5000)
    mean = TOTAL_SLOTS / N_SERVERS
    ecc = rng.normal(mean, SD_FRAC * mean, N_SERVERS)
    ecc = np.maximum(np.round(ecc), 1).astype(int)
    diff = TOTAL_SLOTS - int(ecc.sum())
    step = 1 if diff > 0 else -1
    order = list(np.argsort(-ecc if diff > 0 else ecc))
    i = 0
    while diff != 0:
        j = order[i % N_SERVERS]
        if ecc[j] + step >= 1:
            ecc[j] += step
            diff -= step
        i += 1
    edges = [(a, b) for a in range(N_SERVERS) for b in range(a + 1, N_SERVERS)]
    net = Network(N_SERVERS, edges, bw=BW_MATCHED)
    return ecc, net


def build(seed, duration_s):
    sc = build_scenario(seed, "uniform", 1.0, ne=N_SERVERS, n_workflows=N_WORKFLOWS,
                        pool_size=oe.ASSUME["A17_function_pool_size"], duration_s=duration_s, dags=oe.alibaba_dags())
    ecc, net = matched_cluster(seed)
    sc.ecc, sc.network = ecc, net
    counts = load_counts("F1", "dev", top=TOP_N)
    rng = np.random.default_rng(seed + 1000)
    bin_s = 60.0
    n_bins = int(np.ceil(duration_s / bin_s))
    need_min = n_bins + 1
    offset = int(rng.integers(0, max(1, counts.shape[1] - need_min)))
    rows = rate_matched_rows(counts, len(sc.workflows))
    rel = np.zeros((len(sc.workflows), n_bins))
    for i, r in enumerate(rows):
        series = counts[r].astype(float)
        idx = (offset + np.arange(n_bins)) % len(series)      # bin_s == 60.0 == the trace's own bin width here
        rel[i] = series[idx]
    rel = np.maximum(rel, 0.0) * AGGREGATE_SCALE
    rate_per_s = rel / bin_s                           # real-trace rate, no rho-rescaling (the paper has none); only
                                                        # AGGREGATE_SCALE applied, for the 15-concurrent-workflows reason above
    sc.arrivals = thin_arrivals(rate_per_s, bin_s, duration_s, sc.network.ne, rng)
    prof = offered_load_profile(sc, rate_per_s, bin_s)
    sc.meta = dict(sc.meta, family="F1-matched-setup", kind="faaspr-matched-trace", top_n=TOP_N,
                   n_arrivals=len(sc.arrivals), offered_util_mean=float(prof.mean()),
                   offered_util_median=float(np.median(prof)), ecc=ecc.tolist(), bw=BW_MATCHED)
    X0 = oe.initial_layout(sc, seed, oe.ASSUME["A06_generations"])
    return sc, X0


def path(v, seed):
    return OUT / f"faaspr_matched_setup_{v}_s{seed}.json"


def one(variant, seed=1, duration=None, out=None):
    out = path(variant, seed) if out is None else out
    if out.exists():
        return str(out)
    try:
        assert np.__version__.startswith("1."), "run with the Anaconda interpreter (numpy 1.26)"
        cand, extra, routing = VARIANTS[variant]
        sc, X0 = build(seed, d.DURATION if duration is None else duration)
        kw = sim_kwargs("B_STAR", ASSUME)
        kw.update(warmup=d.WARMUP, duration=d.DURATION if duration is None else duration,
                  retry_min_interval=1.0, retry_max_attempts=10)
        router = FaaSPRRouter(seed=seed + 900, n_paths=int(os.environ.get("FP_PATHS", 300))) if routing else None
        if router is not None:
            kw["dispatcher"] = router
        adj = O3SimAdjuster(make_adjuster("B_STAR", ASSUME, seed=seed + 300), MOVE_PERIOD_S["F1"], epoch=60.0,
                            horizon=120.0, K=5, seed=seed + 800, warmup=d.WARMUP, blind=True, cand_mode=cand,
                            churn=dict(FROZEN2, **extra))
        kw["interval"] = adj.next_interval
        sim = Sim(sc, X0, adjuster=adj, seed=seed + 400, **kw)
        T, exp_arr = fig11.instrument(sim)
        done = []
        o_done = sim._ev_done

        def watch(ins, token, c, o_done=o_done):
            run = ins.run
            o_done(ins, token, c)
            if run is not None and run.req.t_done is not None and sim.in_window(run.req.t_arr) and run.req not in done:
                done.append(run.req)
        sim._ev_done = watch
        res = sim.run()
        sim.check_invariants()
        b = fig11.breakdown(sim, T, exp_arr, done)
        b["p99_makespan"] = res["p99_makespan"]
        b["avg_makespan"] = res["avg_makespan"]
        b["mean_containers"] = res["mean_containers"]
        b["offered_util_mean"] = sc.meta["offered_util_mean"]
        b["n_arrivals"] = sc.meta["n_arrivals"]
        if router is not None:
            b["router"] = dict(unplanned=router.n_unplanned, repaired_req=router.n_repaired_req, pure=router.n_pure)
        out.write_text(json.dumps(dict(variant=variant, seed=seed, result=b)))
        return str(out)
    except Exception:
        import traceback
        out.with_suffix(".err").write_text(traceback.format_exc())
        return str(out) + " FAILED"


if __name__ == "__main__":
    names = sys.argv[1].split(",") if len(sys.argv) > 1 else list(VARIANTS)
    for v in names:
        print(v, flush=True)
        r = one(v)
        if r.endswith("FAILED"):
            print("  FAILED:", Path(r[:-7]).with_suffix(".err").read_text()[-1500:], flush=True)
            continue
        x = json.loads(Path(r).read_text())["result"]
        print(f"  p99 {x['p99_makespan']:7.1f} avg {x['avg_makespan']:6.1f} containers {x['mean_containers']:5.2f} | "
              f"transfer {x['transfer']:5.2f} cold {x['cold']:5.2f} queue {x['queue']:5.2f} | "
              f"offered_util {x['offered_util_mean']:.3f} n_arrivals {x['n_arrivals']} | router {x.get('router')}",
              flush=True)
