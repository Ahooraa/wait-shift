#!/usr/bin/env python3
"""Per-request makespan breakdown on the critical path: transfer, queueing, cold-start wait, execution (simulator only, development seeds).

For each completed in-window request the chain of tasks that ends last is walked back through the parent that finished last. On that chain
    makespan = sum( transfer + queue + cold + exec )
with transfer = (task ready) - (last parent done, or the arrival for a root), queue + cold = start - ready, exec = done - start.
`cold` is only identified for the on-demand system (a container started cold for that task); in FROZEN-4 a wait for a container still starting is inside `queue`.

    nice -n 19 taskset -c 11 ~/venv-dfps/bin/python testbed/diag/latency_breakdown.py --out ~/testbed-results/breakdown.json
"""
import argparse, json, sys, time
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from testbed import baselines_live as BL, frozen_live as FL, sebs_scenario as S          # noqa: E402
from testbed.queue_runs import CELLS, ORDER                                              # noqa: E402
from dfps.nsga2 import PlacementProblem                                                  # noqa: E402
from dfps.ondemand import OnDemandSim                                                    # noqa: E402
from dfps.sim import Sim                                                                 # noqa: E402
from dfps.solution import COLD                                                           # noqa: E402


class Rec:
    def _start(self, ins, run):
        self.__dict__.setdefault("_cold", {})[(run.req.id, run.task)] = (ins.state == COLD)
        super()._start(ins, run)

    def _ev_done(self, ins, token, c):
        run = ins.run
        r = run.req
        ready = run.t_first if run.t_first is not None else run.t_enq
        self.__dict__.setdefault("_tl", {})[(r.id, run.task)] = (ready, run.t_start, self.now, self._cold.get((r.id, run.task), False))
        self.__dict__.setdefault("_reqs", {})[r.id] = r
        super()._ev_done(ins, token, c)


class RecSim(Rec, Sim):
    pass


class RecOD(Rec, OnDemandSim):
    pass


def breakdown(sim):
    rows, bad = [], 0
    by = {}
    for (i, t) in sim._tl:                                   # tasks of each request, indexed once (the scan per request was quadratic)
        by.setdefault(i, []).append(t)
    for rid, r in sim._reqs.items():
        if r.left != 0 or not sim.in_window(r.t_arr):
            continue
        wf = r.wf
        t = max(by[rid], key=lambda t: sim._tl[(rid, t)][2])
        tr = qu = co = ex = 0.0
        steps = 0
        while True:
            ready, start, done, cold = sim._tl[(rid, t)]
            par = list(wf.parents[t])
            pd = max((sim._tl[(rid, p)][2] for p in par), default=r.t_arr)
            tr += ready - pd
            w = start - ready
            c = min(float(sim.cold_start[wf.ft[t]]), w) if cold else 0.0
            co += c
            qu += w - c
            ex += done - start
            steps += 1
            if not par:
                break
            t = max(par, key=lambda p: sim._tl[(rid, p)][2])
        ms = sim._tl[(rid, max(by[rid], key=lambda t: sim._tl[(rid, t)][2]))][2] - r.t_arr
        if abs(tr + qu + co + ex - ms) > 1e-6 * max(1.0, ms):
            bad += 1
        rows.append((ms, tr, qu, co, ex, steps))
    return np.array(rows), bad


def summarise(a):
    ms = a[:, 0]
    top = a[ms >= np.percentile(ms, 95)]
    f = lambda x: {"makespan": x[:, 0].mean(), "transfer": x[:, 1].mean(), "queue": x[:, 2].mean(), "cold": x[:, 3].mean(), "exec": x[:, 4].mean(), "path_tasks": x[:, 5].mean(), "n": len(x)}
    return {"all": f(a), "top5pct": f(top)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--apps", default=",".join(ORDER))
    ap.add_argument("--seeds", default="1,2,3")
    ap.add_argument("--ne", type=int, default=10)
    a = ap.parse_args()
    res = []
    for app in a.apps.split(","):
        rho, cap, warm, window, drain = CELLS[app]
        dur = warm + window
        for seed in [int(x) for x in a.seeds.split(",")]:
            sc, samp = S.build(seed, apps=[app], rho=rho, ne=a.ne, duration_s=dur, rate_cap=cap)
            X0 = PlacementProblem(sc.network, sc.ecc, np.array([f.exec_time for f in sc.functions])).random(np.random.default_rng(seed))
            for arm in ("frozen4", "rl"):
                t0 = time.time()
                if arm == "rl":
                    sim, _ = BL.build_rl(sc, seed, warmup=warm, duration=dur, sim_cls=RecOD, exec_sampler=samp)
                else:
                    sim, _ = FL.build(sc, X0, seed, arm="frozen4", warmup=warm, duration=dur, exec_sampler=samp, sim_cls=RecSim)
                out = sim.run()
                arr, bad = breakdown(sim)
                res.append({"app": app, "seed": seed, "arm": arm, "p99": out["p99_makespan"], "p50": out["p50_makespan"], "cold_starts": out["cold_starts"],
                            "chain_mismatch": bad, **summarise(arr)})
                print(app, seed, arm, f"{time.time()-t0:.0f}s", "mismatch", bad, flush=True)
    Path(a.out).write_text(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    main()
