#!/usr/bin/env python3
"""Where do FROZEN-4's tasks wait in a cell? Per function: tasks, mean/p95 wait (start - ready), exec time, containers over the run vs the concurrency the load needs."""
import argparse, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from testbed.diag.latency_breakdown import RecSim, RecOD, Rec          # noqa: E402
from testbed import frozen_live as FL, baselines_live as BL, sebs_scenario as S   # noqa: E402
from testbed.queue_runs import CELLS                                    # noqa: E402
from dfps.nsga2 import PlacementProblem                                 # noqa: E402


class RecN(RecSim):
    def _ev_done(self, ins, token, c):
        run = ins.run
        self.__dict__.setdefault("_nf", {})[(run.req.id, run.task)] = (run.run.node if False else ins.node, run.n_moves)
        # container counts of the task's function, sampled at completion
        self.__dict__.setdefault("_cnt", {}).setdefault(run.f, []).append(int(self.cnt[run.f].sum()))
        super()._ev_done(ins, token, c)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--app", default="680.excamera"); ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--arm", default="frozen4"); ap.add_argument("--ne", type=int, default=10)
    a = ap.parse_args()
    rho, cap, warm, window, drain = CELLS[a.app]; dur = warm + window; seed = a.seed
    sc, samp = S.build(seed, apps=[a.app], rho=rho, ne=a.ne, duration_s=dur, rate_cap=cap)
    X0 = PlacementProblem(sc.network, sc.ecc, np.array([f.exec_time for f in sc.functions])).random(np.random.default_rng(seed))
    sim, _ = FL.build(sc, X0, seed, arm=a.arm, warmup=warm, duration=dur, exec_sampler=samp, sim_cls=RecN)
    out = sim.run()
    wf = sc.workflows[0]; rate = sc.meta["rate_per_s"]
    F = len(sc.functions)
    print(f"{a.app} seed {seed}: {rate:.2f} req/s, {wf.n} tasks/request, {F} functions, nodes {a.ne}, slots total {int(np.sum(sc.ecc))}, P99 {out['p99_makespan']:.1f}, moved {out['n_moved']}")
    per_f = {}
    for (rid, t), (ready, start, done, cold) in sim._tl.items():
        r = sim._reqs[rid]
        if not sim.in_window(r.t_arr):
            continue
        f = r.wf.ft[t]
        per_f.setdefault(f, []).append((start - ready, done - start))
    tasks_per_req = np.bincount(wf.ft, minlength=F)
    print(f"{'f':>3}{'tasks/req':>10}{'tasks':>7}{'exec s':>8}{'need':>7}{'cont(X0)':>9}{'cont(avg)':>10}{'wait mean':>10}{'wait p95':>9}{'wait max':>9}{'share of all wait':>18}")
    tot = sum(sum(w for w, _ in v) for v in per_f.values())
    for f in sorted(per_f):
        w = np.array([x[0] for x in per_f[f]]); e = np.array([x[1] for x in per_f[f]])
        need = rate * tasks_per_req[f] * e.mean()
        print(f"{f:3d}{tasks_per_req[f]:10d}{len(w):7d}{e.mean():8.2f}{need:7.1f}{int(X0[:, f].sum()):9d}{np.mean(sim._cnt[f]):10.1f}{w.mean():10.2f}{np.percentile(w,95):9.2f}{w.max():9.2f}{100*w.sum()/tot:17.0f}%")
    # waits vs node and moved tasks
    nodes = {}
    mv = [[], []]
    for (rid, t), (k, nm) in sim._nf.items():
        ready, start, done, cold = sim._tl[(rid, t)]
        if not sim.in_window(sim._reqs[rid].t_arr):
            continue
        nodes.setdefault(k, []).append(start - ready); mv[nm > 0].append(start - ready)
    print("\nwait by node (mean s, tasks):", {k: (round(float(np.mean(v)), 2), len(v)) for k, v in sorted(nodes.items())})
    print(f"tasks never moved: n={len(mv[0])} mean wait {np.mean(mv[0]):.2f} s;  moved at least once: n={len(mv[1])} mean wait {np.mean(mv[1]) if mv[1] else float('nan'):.2f} s")
    print("slots per node:", [int(x) for x in sc.ecc], "  containers at end per node:", [int(x) for x in sim.cnt.sum(axis=0)])


if __name__ == "__main__":
    main()
