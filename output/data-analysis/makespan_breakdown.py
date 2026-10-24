"""Makespan breakdown at low load (calibration diagnostic, 2026-10-17).

  python -I output/data-analysis/makespan_breakdown.py

Why: at the lightest calibration load our Uniform makespan floor is about 20-30 s, the paper's about 12 s, even with single-task
jobs, so the floor is not explained by workflow length. This script instruments one run per (scenario, method) WITHOUT changing the
simulator (method wrappers on the instance) and splits every in-window request's makespan along its realised critical path into:
  plan_wait   arrival -> successful planning (A-24 wait-and-retry list)
  transfer    input state in flight (request input from the origin for root tasks; parent output for the others)
  reroute     ready -> joined a queue (A-25 rerouting / parking when the planned node lost the function)
  queue       waiting in the instance queue
  cold        part of the queue wait spent on instances still cold-starting (not separable here: reported inside queue)
  exec        execution
The segments sum to the makespan exactly (checked).
"""
from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402
from dfps.sim import Sim  # noqa: E402
from dfps.variants import make_adjuster, sim_kwargs  # noqa: E402

ASSUME = yaml.safe_load((ROOT / "config" / "assumptions.yaml").read_text(encoding="utf-8"))
CAL = ROOT / "results" / "calibration_fig5"
OUT = ROOT / "output" / "data-analysis" / "results"
CASES = [("screen_load0.25_uniform_x0.25_s1", "load x0.25, Uniform x0.25"),
         ("combo_L025_single_uniform_x0.25_s1", "load x0.25 + single-task jobs, Uniform x0.25"),
         ("screen_base_uniform_x0.25_s1", "base, Uniform x0.25")]


def instrument(sim):
    T = {}                                   # (rid, task) -> dict of timestamps
    sim.t_plan = {}                          # rid -> planning time (Req has __slots__)
    exp_arr = {}                             # (rid, child) -> list of (arrival time, parent)
    net = sim.net

    def rec(r, t):
        return T.setdefault((r.id, t), {})

    o_plan, o_state, o_enq, o_start, o_done = sim._plan, sim._ev_state, sim._enqueue, sim._start, sim._ev_done

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

    def _start(ins, run):
        rec(run.req, run.task)["start"] = sim.now
        rec(run.req, run.task)["cold"] = 0.0
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
    return T, exp_arr


def breakdown(sim, T, exp_arr, reqs):
    seg = {k: [] for k in ("plan_wait", "transfer", "reroute", "queue", "exec", "makespan", "depth")}
    for r in reqs:
        wf = r.wf
        last = max(range(wf.n), key=lambda t: T[(r.id, t)]["finish"])
        tp = sim.t_plan[r.id]
        s = dict(plan_wait=tp - r.t_arr, transfer=0.0, reroute=0.0, queue=0.0, exec=0.0)
        t, depth = last, 0
        while True:
            d = T[(r.id, t)]
            depth += 1
            s["exec"] += d["finish"] - d["start"]
            s["queue"] += d["start"] - d["enq"]
            s["reroute"] += d["enq"] - d["ready"]
            arr = max(exp_arr[(r.id, t)])                      # the input that arrived last gates the task
            parent = arr[1]
            if parent is None:
                s["transfer"] += d["ready"] - tp
                break
            s["transfer"] += d["ready"] - T[(r.id, parent)]["finish"]
            t = parent
        ms = r.t_done - r.t_arr
        assert abs(sum(s.values()) - ms) < 1e-6, (sum(s.values()), ms)
        for k, v in s.items():
            seg[k].append(v)
        seg["makespan"].append(ms)
        seg["depth"].append(depth)
    return {k: float(np.mean(v)) for k, v in seg.items()} | {"n": len(reqs)}


def run_case(tag):
    from experiments.run import initial_placements
    sc = pickle.load(open(CAL / f"{tag}.pkl", "rb"))
    x_sr, x_sg, _ = initial_placements(sc, 1, ASSUME["A06_generations"], "abs")
    out = {}
    for m in ("SR", "SG", "DFPS"):
        kw = sim_kwargs("B_STAR", ASSUME)
        adj = make_adjuster("B_STAR", ASSUME, seed=1 + 300) if m == "DFPS" else None
        sim = Sim(sc, x_sr if m == "SR" else x_sg, adjuster=adj, seed=1 + 400, **kw)
        done = []
        T, exp_arr = instrument(sim)
        o_done = sim._ev_done

        def watch(ins, token, c, o_done=o_done):
            run = ins.run
            o_done(ins, token, c)
            if run is not None and run.req.t_done is not None and sim.in_window(run.req.t_arr) and run.req not in done:
                done.append(run.req)
        sim._ev_done = watch
        res = sim.run()
        b = breakdown(sim, T, exp_arr, done)
        b["avg_makespan_sim"] = res["avg_makespan"]
        b["utilization"] = res["utilization"]
        b["unloaded_critical_path_exec"] = float(np.mean([sim.crit_path[r.wf.id] for r in done]))
        out[m] = b
    return out


if __name__ == "__main__":
    res = {}
    for tag, label in CASES:
        res[label] = run_case(tag)
        print(label)
        for m, b in res[label].items():
            print(f"  {m:4s} makespan {b['makespan']:6.1f} = plan_wait {b['plan_wait']:5.1f} + transfer {b['transfer']:5.1f} + "
                  f"reroute {b['reroute']:5.1f} + queue {b['queue']:5.1f} + exec {b['exec']:5.1f} | critical-path depth {b['depth']:.2f} "
                  f"| unloaded exec CP {b['unloaded_critical_path_exec']:.1f} | util {b['utilization']*100:.1f}% | n {b['n']}", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "makespan_breakdown_lowload.json").write_text(json.dumps(res, indent=1))
