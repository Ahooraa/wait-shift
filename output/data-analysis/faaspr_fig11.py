"""FaaSPR Fig. 11 reproduction: time-consumption breakdown by data transfer / cold start / request queuing,
for ours / fp_place / fp_route, on our own F1/F2 corpus (2026-10-26).

Fig. 11 of the FaaSPR paper (Jia et al., IEEE/ACM ToN 2025) breaks a workflow's end-to-end processing time
into Data Transfer, Cold Start and Request Queuing for a representative setup (Video Processing, normalized
resources, 50MB/s). We do not have the per-task timing/size data to rebuild their six named workflows (see
knowledge/sources/jia-2025-faaspr.md -- Fig. 7 gives only qualitative control-flow diagrams), so per the
user's confirmed choice this reuses our already-validated F1/F2 corpus and reports the same three categories
for our own three variants, instrumented without changing the simulator.

Cold-start attribution: makespan_breakdown.py's plan_wait/transfer/reroute/queue/exec split folds cold-start
delay into "queue" (its own docstring says so -- "not separable here"). This script separates it: at the
instant an instance created COLD (via add_instance / _convert) first serves a request, the overlap between
[instance creation, instance warm_at] and [that request's own enqueue-to-start wait] is charged to "cold",
once per instance (its first dispatch only -- later dispatches on the same, now-warm instance are ordinary
queueing); the remainder of the wait stays "queue". The five-way split (plan_wait/transfer/reroute/cold/queue/
exec) still sums exactly to the makespan (checked).

  python -I output/data-analysis/faaspr_fig11.py [variant,...]
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
from frozen2 import FROZEN2, MOVE_PERIOD_S  # noqa: E402

import yaml  # noqa: E402

import p3_scaling_probe as p3  # noqa: E402

from dfps.dispatchers import FaaSPRRouter  # noqa: E402
from dfps.o3s import O3SimAdjuster  # noqa: E402
from dfps.sim import Sim  # noqa: E402
from dfps.variants import make_adjuster, sim_kwargs  # noqa: E402

ASSUME = yaml.safe_load((ROOT / "config" / "assumptions.yaml").read_text(encoding="utf-8"))
OUT = ROOT / "output" / "data-analysis" / "results"
CASES = [("F1", 0.7, 5, 1), ("F2", 0.7, 5, 1)]        # family, rho, k, seed -- one representative load x state-size point per family
VARIANTS = {"ours": ("nosim", dict(lam=0.5), False), "fp_place": ("nosim", dict(placement="faaspr", lam=0.5), False),
            "fp_route": ("nosim", dict(lam=0.5), True), "fp_both": ("nosim", dict(placement="faaspr", lam=0.5), True)}
# lam=0.5 (2026-10-26, user decision): the lambda sweep's Gate 1 finding (both families, k=10, best lam=0.5;
# knowledge/synthesis/workflow-aware-decision-rules.md). lam weights our request-move rule, and every fp_* row keeps our moves, so it
# is set on all four rows; each fp_* row then differs from "ours" only in the FaaSPR component it swaps in.


def instrument(sim):
    T = {}                                            # (rid, task) -> dict of timestamps
    sim.t_plan = {}                                   # rid -> planning time (Req has __slots__)
    exp_arr = {}                                      # (rid, child) -> list of (arrival time, parent)
    cold = {}                                         # id(instance) -> dict(created, warm_at, charged) -- Instance has __slots__
    net = sim.net

    def rec(r, t):
        return T.setdefault((r.id, t), {})

    o_plan, o_state, o_enq, o_start, o_done = sim._plan, sim._ev_state, sim._enqueue, sim._start, sim._ev_done
    o_convert, o_add = sim._convert, sim.add_instance

    def _plan(r):
        ok = o_plan(r)
        if ok:
            sim.t_plan[r.id] = sim.now
            for root in r.wf.roots:
                exp_arr.setdefault((r.id, root), []).append((sim.now + net.stt(r.wf.input_size, r.origin, r.plan[root]), None))
        return ok

    def _ev_state(r, task, c):
        if r.pending[task] == 1:
            rec(r, task)["ready"] = sim.now
        return o_state(r, task, c)

    def _enqueue(run, k):
        o_enq(run, k)
        if getattr(run, "t_enq", None) is not None:
            rec(run.req, run.task)["enq"] = run.t_enq

    def _convert(ins, g):
        o_convert(ins, g)
        cold[id(ins)] = dict(created=sim.now, warm_at=ins.warm_at, charged=False)

    def _add(k, f):
        ok = o_add(k, f)
        if ok:
            ins = sim.inst[k][f][-1]
            cold[id(ins)] = dict(created=sim.now, warm_at=ins.warm_at, charged=False)
        return ok

    def _start(ins, run):
        rec(run.req, run.task)["start"] = sim.now
        c = cold.get(id(ins))
        chg = 0.0
        if c is not None and not c["charged"]:
            lo, hi = max(c["created"], run.t_enq), min(c["warm_at"], sim.now)
            chg = max(0.0, hi - lo)
            c["charged"] = True
        rec(run.req, run.task)["cold"] = chg
        return o_start(ins, run)

    def _ev_done(ins, token, c):
        run = ins.run
        if run is not None and token == ins.token:
            r, t, k = run.req, run.task, ins.node
            rec(r, t)["finish"] = sim.now
            for ch in r.wf.children[t]:
                exp_arr.setdefault((r.id, ch), []).append((sim.now + net.stt(r.wf.ss[(t, ch)], k, r.plan[ch]), t))
        return o_done(ins, token, c)

    sim._plan, sim._ev_state, sim._enqueue, sim._start, sim._ev_done = _plan, _ev_state, _enqueue, _start, _ev_done
    sim._convert, sim.add_instance = _convert, _add
    return T, exp_arr


def breakdown(sim, T, exp_arr, reqs):
    seg = {k: [] for k in ("plan_wait", "transfer", "reroute", "cold", "queue", "exec", "makespan")}
    for r in reqs:
        wf = r.wf
        last = max(range(wf.n), key=lambda t: T[(r.id, t)]["finish"])
        tp = sim.t_plan[r.id]
        s = dict(plan_wait=tp - r.t_arr, transfer=0.0, reroute=0.0, cold=0.0, queue=0.0, exec=0.0)
        t = last
        while True:
            dd = T[(r.id, t)]
            s["exec"] += dd["finish"] - dd["start"]
            s["cold"] += dd.get("cold", 0.0)
            s["queue"] += (dd["start"] - dd["enq"]) - dd.get("cold", 0.0)
            s["reroute"] += dd["enq"] - dd["ready"]
            arr = max(exp_arr[(r.id, t)])                # the input that arrived last gates the task
            parent = arr[1]
            if parent is None:
                s["transfer"] += dd["ready"] - tp
                break
            s["transfer"] += dd["ready"] - T[(r.id, parent)]["finish"]
            t = parent
        ms = r.t_done - r.t_arr
        assert abs(sum(s.values()) - ms) < 1e-6, (sum(s.values()), ms)
        for k, v in s.items():
            seg[k].append(v)
        seg["makespan"].append(ms)
    return {k: float(np.mean(v)) for k, v in seg.items()} | {"n": len(reqs)}


def run_one(fam, rho, k, seed, variant, duration=140.0, sc=None, X0=None, sizing_cache=None):
    """sc/X0/sizing_cache: pass the SAME scenario+initial layout and a dict shared across a case's variants so the
    exogenous sizing schedule (dfps/o3s.py::bottleneck_first_placement) is computed once and replayed identically to
    all of them (2026-10-27 fix), rather than left to be merely numerically identical by construction. Omit to build
    a fresh (still-correct, still-exogenous) scenario/cache for a single standalone call."""
    cand, extra, routing = VARIANTS[variant]
    if sc is None:
        p3.RHO = rho                                      # p3_scaling_probe.build reads this module global
        sc, X0 = p3.build(fam, k, seed)
    kw = sim_kwargs("B_STAR", ASSUME)
    kw.update(warmup=d.WARMUP, duration=duration, retry_min_interval=1.0, retry_max_attempts=10)
    router = FaaSPRRouter(seed=seed + 900, n_paths=int(os.environ.get("FP_PATHS", 300))) if routing else None
    if router is not None:
        kw["dispatcher"] = router
    adj = O3SimAdjuster(make_adjuster("B_STAR", ASSUME, seed=seed + 300), MOVE_PERIOD_S[fam], epoch=60.0, horizon=120.0, K=5,
                         seed=seed + 800, warmup=d.WARMUP, blind=True, cand_mode=cand, churn=dict(FROZEN2, **extra),
                         sizing_cache=sizing_cache)
    kw["interval"] = adj.next_interval
    sim = Sim(sc, X0.copy(), adjuster=adj, seed=seed + 400, **kw)
    T, exp_arr = instrument(sim)
    done = []
    o_done = sim._ev_done

    def watch(ins, token, c, o_done=o_done):
        run = ins.run
        o_done(ins, token, c)
        if run is not None and run.req.t_done is not None and sim.in_window(run.req.t_arr) and run.req not in done:
            done.append(run.req)
    sim._ev_done = watch
    res = sim.run()
    b = breakdown(sim, T, exp_arr, done)
    b["p99_makespan"] = res["p99_makespan"]
    return b


if __name__ == "__main__":
    names = sys.argv[1].split(",") if len(sys.argv) > 1 else list(VARIANTS)
    out = {}
    for fam, rho, k, seed in CASES:
        p3.RHO = rho
        sc, X0 = p3.build(fam, k, seed)
        sizing_cache = {}                                 # shared across this case's variants: one sizing schedule, computed once
        for v in names:
            key = f"{fam}_r{rho}_k{k}_s{seed}_{v}"
            print(key, flush=True)
            b = run_one(fam, rho, k, seed, v, sc=sc, X0=X0, sizing_cache=sizing_cache)
            out[key] = b
            print(f"  makespan {b['makespan']:6.1f} (p99 {b['p99_makespan']:6.1f}) = plan_wait {b['plan_wait']:5.1f} + "
                  f"transfer {b['transfer']:5.1f} + reroute {b['reroute']:5.1f} + cold {b['cold']:5.1f} + queue {b['queue']:5.1f} + "
                  f"exec {b['exec']:5.1f} | Fig11-style (transfer/cold/queue) = {b['transfer']:.2f}/{b['cold']:.2f}/{b['queue']:.2f} | n {b['n']}",
                  flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "faaspr_fig11_breakdown.json").write_text(json.dumps(out, indent=1))
