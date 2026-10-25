"""Diagnostic: does the mismatch between the live layout and the ideal sizing grow steadily between re-layouts, or in bursts,
and does it predict a real cost? (2026-10-25, prompted by the lambda x T proposal -- see
knowledge/synthesis/novelty-register.md). If drift is bursty AND predicts loss AND the 30 s cadence's extra cold starts are a
real cost, an event-triggered re-layout (fire when the mismatch crosses a threshold, instead of a fixed clock) has room; a
30 s-equivalent P99 for fewer cold starts than 30 s is the target, not merely beating 60 s. Logs, every move-period tick via
O3SimAdjuster._staleness / _placement_mismatch / _queue_tail:
  count mismatch       sum|live per-function counts - ideal need right now| / slots (sizing only)
  placement mismatch   share of live containers sitting outside their function's own locality-best nodes (no-solve proxy;
                        a LOWER BOUND on placement staleness -- it ignores cross-function capacity contention; calibrated
                        against a real solve by `calibrate` below, once, on one case)
  backlog               sum of queued-work-per-function right now (a MEAN-ish loss proxy)
  tail                  95th percentile of current queue lengths (a TAIL loss proxy -- P99 and the mean diverge in this
                        system, e.g. the no-moves pair, so both are logged and the register states which one a trigger may
                        key on)
Burstiness is read by FAMILY, not against a fixed bar: Azure (F1) is the known-steadier trace, Huawei (F2) the known-bursty
one (see input/description), so CV_Huawei notably exceeding CV_Azure is the self-calibrating signal; six development cases
(50/70/85% load x Azure + Huawei) give three of each as the reference pair. Pre-registered thresholds: see
knowledge/synthesis/workflow-aware-decision-rules.md before reading the results.
  python staleness_probe.py run [workers] | analyze | calibrate
"""
import json
import pickle
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(ROOT))
import d3s_headroom as d  # noqa: E402
from frozen2 import FROZEN2, MOVE_PERIOD_S  # noqa: E402

import yaml  # noqa: E402

from dfps.o3s import O3SimAdjuster  # noqa: E402
from dfps.sim import Sim  # noqa: E402
from dfps.variants import make_adjuster, sim_kwargs  # noqa: E402

ASSUME = yaml.safe_load((ROOT / "config" / "assumptions.yaml").read_text(encoding="utf-8"))
RUNS = ROOT / "results" / "staleness"
CASES = [("F1", 0.5, 1), ("F1", 0.7, 1), ("F1", 0.85, 1), ("F2", 0.5, 1), ("F2", 0.7, 1), ("F2", 0.85, 1)]


def one(case, duration=None, out=None):
    f, r, s = case
    out = RUNS / f"{d.tag(f, r, s)}.json" if out is None else out
    if out.exists():
        return str(out)
    try:
        assert np.__version__.startswith("1."), "run with the Anaconda interpreter (numpy 1.26)"
        T = json.loads((d.OUT / "g2_tstar.json").read_text())
        tg = d.tag(f, r, s)
        sc = pickle.load(open(d.D1 / f"{tg}.pkl", "rb"))
        P = pickle.load(open(d.D1 / f"{tg}.prep.pkl", "rb"))
        kw = sim_kwargs("B_STAR", ASSUME)
        kw.update(warmup=d.WARMUP, duration=d.DURATION if duration is None else duration, retry_min_interval=1.0, retry_max_attempts=10)
        adj = O3SimAdjuster(make_adjuster("B_STAR", ASSUME, seed=s + 300), MOVE_PERIOD_S[f], epoch=60.0, horizon=120.0, K=5,
                            seed=s + 800, warmup=d.WARMUP, blind=True, cand_mode="nosim", churn=dict(FROZEN2, log_staleness=True))
        kw["interval"] = adj.next_interval
        sim = Sim(sc, P["X0"], adjuster=adj, seed=s + 400, **kw)
        res = sim.run()
        sim.check_invariants()
        dur = kw["duration"]
        # the adjuster's move-tick (and so staleness logging) is not gated by sim.now < duration, unlike the re-layout decision --
        # it keeps firing through the post-duration drain tail, where demand collapses toward zero and the mismatch is a drain
        # artifact, not operational drift. Keep only samples from the actual measured-window operation.
        staleness = [p for p in adj.staleness_log if p[0] < dur]
        relayout_times = [e["t"] for e in adj.log if e.get("switched")]
        out.write_text(json.dumps(dict(case=list(case), result={k: res[k] for k in ("p99_makespan", "avg_makespan", "cold_starts")},
                                       staleness=staleness, relayout_times=relayout_times)))
        return str(out)
    except Exception:
        import traceback
        out.with_suffix(".err").write_text(traceback.format_exc())
        return str(out) + " FAILED"


def run(workers):
    RUNS.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(workers) as ex:
        for r in ex.map(one, CASES):
            print("done", r, flush=True)


def calibrate():
    """One case, with calibrate_placement=True: compares the cheap no-solve `_placement_mismatch` proxy against a real-solve
    ground truth (`_true_placement_mismatch`) at 15 points spread over the run. Answers whether a failed loss-correlation
    test on the proxy (in `analyze`) is a real null or a weak-instrument artifact."""
    RUNS.mkdir(parents=True, exist_ok=True)
    out = RUNS / "calibration.json"
    f, r, s = "F1", 0.7, 1
    tg = d.tag(f, r, s)
    T = json.loads((d.OUT / "g2_tstar.json").read_text())
    sc = pickle.load(open(d.D1 / f"{tg}.pkl", "rb"))
    P = pickle.load(open(d.D1 / f"{tg}.prep.pkl", "rb"))
    kw = sim_kwargs("B_STAR", ASSUME)
    kw.update(warmup=d.WARMUP, duration=d.DURATION, retry_min_interval=1.0, retry_max_attempts=10)
    adj = O3SimAdjuster(make_adjuster("B_STAR", ASSUME, seed=s + 300), MOVE_PERIOD_S[f], epoch=60.0, horizon=120.0, K=5,
                        seed=s + 800, warmup=d.WARMUP, blind=True, cand_mode="nosim",
                        churn=dict(FROZEN2, calibrate_placement=True, calibrate_placement_n=15))
    kw["interval"] = adj.next_interval
    sim = Sim(sc, P["X0"], adjuster=adj, seed=s + 400, **kw)
    sim.run()
    sim.check_invariants()
    out.write_text(json.dumps(dict(case=[f, r, s], calib=adj.calib_log)))
    proxy = np.array([p[1] for p in adj.calib_log])
    true = np.array([p[2] for p in adj.calib_log])
    corr = float(np.corrcoef(proxy, true)[0, 1]) if len(proxy) > 2 else float("nan")
    print(f"n={len(proxy)} | corr(proxy, true) = {corr:.2f}")
    for t_, p_, tr_ in adj.calib_log:
        print("  t=%6.1f  proxy=%.3f  true=%+.3f" % (t_, p_, tr_))


def analyze():
    cv_by_family = {"F1": [], "F2": []}
    for f in sorted(RUNS.glob("*.json")):
        if f.name == "calibration.json":
            continue
        x = json.loads(f.read_text())
        t = np.array([p[0] for p in x["staleness"]])
        m = np.array([p[1] for p in x["staleness"]])                 # count mismatch (sizing)
        pm = np.array([p[2] for p in x["staleness"]])                # placement mismatch (locality, lower bound)
        bl = np.array([p[3] for p in x["staleness"]])                # backlog (mean-ish loss proxy)
        tl = np.array([p[4] for p in x["staleness"]])                # queue-length p95 (tail loss proxy)
        relayouts = sorted(set(round(rt) for rt in x["relayout_times"]))
        since = np.full(len(t), np.nan)                              # seconds since the last re-layout, per sample
        for i, ti in enumerate(t):
            past = [rt for rt in relayouts if rt <= ti]
            if past:
                since[i] = ti - past[-1]
        buckets = [(0, 15), (15, 30), (30, 45), (45, 60), (60, 90)]
        shape = ["%2.0f-%2.0fs: %.3f/%.3f (n=%d)" % (a, b,
                 np.nanmean(m[(since >= a) & (since < b)]) if ((since >= a) & (since < b)).any() else float("nan"),
                 np.nanmean(pm[(since >= a) & (since < b)]) if ((since >= a) & (since < b)).any() else float("nan"),
                 int(((since >= a) & (since < b)).sum())) for a, b in buckets]
        # burstiness: coefficient of variation of the INCREMENT (m[i] - m[i-1]) restricted to within-epoch points (since > period)
        p0 = MOVE_PERIOD_S[x["case"][0]]
        within = since > p0 + 1e-6
        inc = np.diff(m)
        inc_within = inc[within[1:] & within[:-1]] if len(inc) else np.array([])
        cv = float(np.std(inc_within) / (abs(np.mean(inc_within)) + 1e-9)) if len(inc_within) else float("nan")
        cv_by_family[x["case"][0]].append(cv)
        inc_pm = np.diff(pm)[within[1:] & within[:-1]] if len(pm) > 1 else np.array([])
        cv_pm = float(np.std(inc_pm) / (abs(np.mean(inc_pm)) + 1e-9)) if len(inc_pm) else float("nan")
        # loss proxies: does mismatch (count, placement) predict backlog / tail, lagged one tick?
        def corr(a, b):
            return float(np.corrcoef(a[:-1], b[1:])[0, 1]) if len(a) > 2 else float("nan")
        print("%-14s P99 %7.1f | mean mismatch (count/placement) %.3f / %.3f | CV of increments %.2f / %.2f | corr(count mismatch, backlog/tail) %.2f / %.2f | corr(placement mismatch, backlog/tail) %.2f / %.2f" % (
            d.tag(*x["case"]), x["result"]["p99_makespan"], np.nanmean(m), np.nanmean(pm), cv, cv_pm,
            corr(m, bl), corr(m, tl), corr(pm, bl), corr(pm, tl)))
        print("   drift shape, count/placement mismatch by time since the last re-layout: " + " | ".join(shape))
    print("\nburstiness by family (Azure/F1 = known-steadier reference, Huawei/F2 = known-bursty reference):")
    print("  F1 (Azure)  CV = %s" % ["%.2f" % v for v in cv_by_family["F1"]])
    print("  F2 (Huawei) CV = %s" % ["%.2f" % v for v in cv_by_family["F2"]])


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 4)
    elif sys.argv[1] == "calibrate":
        calibrate()
    else:
        analyze()
