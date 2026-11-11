#!/usr/bin/env python3
"""Calibration of the testbed itself: how many requests per second can the hub and the agents drive, and what do they add? (DEV-T7)

For each request rate the SAME scenario (one SeBS-Flow application, static placement, common random numbers) runs twice: in the plain
simulator, where nothing but the model costs time, and in LiveSim on the real agents. Requests are paired by id, so the difference of their
makespans is what the testbed adds (hub-to-agent round trips, Wi-Fi transfers, timer error, the hub's own compute) -- but ONLY for requests that
did not queue in either system: with queueing and heavy-tailed durations the two systems' trajectories diverge (the same long task blocks
different requests), and that is not testbed overhead (found 2026-11-11: a 2 s p99 "overhead" was a long `confirm` task blocking a
single container in both systems; the distributions matched within 3%). So the verdict uses: the overhead of queue-free requests, the
ratio of the live and simulated makespan distributions, and the hub's health. The highest rate that meets all criteria is the sustainable
rate; a load only counts as reachable for an application if its request rate is below it (input of the pre-registered inclusion rule).

    ~/venv-dfps/bin/python testbed/calibrate.py --rates 5,20,50,100,200 --app 6200.trip-booking     (agents must be running)

Results go to ~/testbed-results/ (local, not in the repository: they contain the addresses of the laptops).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))        # run as a script: the repository root must be importable (dfps, testbed)

from testbed import sebs_scenario as S                                  # noqa: E402
from testbed.livesim import LiveLink, LiveSim                           # noqa: E402
from dfps.nsga2 import PlacementProblem
from dfps.sim import Sim

CRITERIA = {"qfree_overhead_p95_x": 2.0,        # overhead of queue-free requests (p95) at most twice its value at the lowest rate
            "p99_ratio_range": (0.75, 1.33),    # live p99 makespan over simulated p99 makespan
            "late_event_fraction": 0.01, "completed_fraction": 0.99, "hub_cpu_fraction": 0.90}      # the definition of "sustained"


def transfer_stats(link):
    """Cross-laptop transfers of the run just finished, from the agents' own logs: how many, how many were slow, the slowest, connections opened."""
    nets, conns = [], 0
    for c in link.clients.values():
        for ln in c.call("get_log", since_seq=0, limit=1000000, timeout=60)["lines"]:
            r = json.loads(ln)
            if r["kind"] == "transfer_done" and not r["local"]:
                nets.append(r["net_s"])
        conns += c.call("status")["counters"]["peer_connections"]
    nets = np.array(nets) if nets else np.zeros(1)
    return {"transfers_cross": int(len(nets)), "transfers_over_0_5s": int((nets > 0.5).sum()), "transfers_over_1s": int((nets > 1.0).sum()),
            "transfer_net_max_s": float(nets.max()), "transfer_net_p50_ms": float(np.percentile(nets, 50) * 1e3), "peer_connections_opened": int(conns)}


def queue_free(sim, tol_s=0.005):
    """Ids of the requests none of whose tasks waited in a queue longer than tol_s (from the simulator's per-task trace)."""
    worst = {}
    for rid, _wf, _task, _plan, _node, t_first, t_start, _t_done, _nm in sim.trace["tasks"]:
        worst[rid] = max(worst.get(rid, 0.0), t_start - t_first)
    return {rid for rid, w in worst.items() if w <= tol_s}


def paired(ref_log, live_log):
    r = {i: m for i, _, m, _ in ref_log}
    pairs = [(r[i], m) for i, _, m, _ in live_log if i in r]
    a = np.array(pairs)
    return a[:, 0], a[:, 1]


def run_rate(link, rate, app="6200.trip-booking", seed=1, ne=20, duration=40.0, warmup=8.0, drain_s=40.0):
    sc, samp = S.build(seed, apps=[app], rho=0.95, ne=ne, duration_s=duration, rate_cap=rate)
    X = PlacementProblem(sc.network, sc.ecc, np.array([f.exec_time for f in sc.functions])).random(np.random.default_rng(seed))
    ref = Sim(sc, X, seed=1, warmup=warmup, duration=duration, exec_sampler=samp, record_requests=True, trace=True)
    ref_res = ref.run()
    live = LiveSim(sc, X, seed=1, warmup=warmup, duration=duration, exec_sampler=samp, record_requests=True, trace=True, link=link, drain_s=drain_s)
    t0 = time.time()
    res = live.run()
    wall = time.time() - t0
    slow = transfer_stats(link)
    sim_ms, live_ms = paired(ref.request_log, live.request_log)
    d = (live_ms - sim_ms) * 1e3
    tasks = sc.workflows[0].n
    free = queue_free(ref) & queue_free(live)
    r_ids = {i: m for i, _, m, _ in ref.request_log}
    dq = np.array([(m - r_ids[i]) * 1e3 for i, _, m, _ in live.request_log if i in r_ids and i in free]) if free else np.zeros(1)
    lv = res["live"]
    ops = lv["runs"] + lv["warm"] + lv["transfers"] + lv["relocation_transfers"]
    return {"rate_per_s": rate, "tasks_per_s": rate * tasks, "n_window_requests": int(len(live_ms)), "n_completed": res["n_completed"], "n_arrived": res["n_arrived"],
            "wall_s": round(wall, 1), "sim_p50_ms": float(np.percentile(sim_ms, 50) * 1e3), "live_p50_ms": float(np.percentile(live_ms, 50) * 1e3),
            "sim_p99_ms": float(np.percentile(sim_ms, 99) * 1e3), "live_p99_ms": float(np.percentile(live_ms, 99) * 1e3),
            "qfree_requests": int(len(dq)), "qfree_overhead_p50_ms": float(np.percentile(dq, 50)), "qfree_overhead_p95_ms": float(np.percentile(dq, 95)),
            "qfree_overhead_per_task_ms": float(dq.mean() / tasks), "p50_ratio": float(np.percentile(live_ms, 50) / np.percentile(sim_ms, 50)),
            "p99_ratio": float(np.percentile(live_ms, 99) / np.percentile(sim_ms, 99)),
            "overhead_mean_ms": float(d.mean()), "overhead_p50_ms": float(np.percentile(d, 50)), "overhead_p99_ms": float(np.percentile(d, 99)),
            "overhead_per_task_ms": float(d.mean() / tasks), "late_events": lv["late_events"], "inbox_max": lv["inbox_max"],
            "hub_cpu_fraction": lv["hub_cpu_fraction"], "agent_ops": lv["agent_ops"], "agent_timer_lateness_max_ms": max(a["lateness_s"]["max"] for a in lv["agents"].values()) * 1e3,
            "n_events_total": ops, **slow}


def verdict(rows):
    """Mark each rate sustained or not against CRITERIA; the overhead criterion is relative to the lowest rate that ran."""
    ok_rows = [r for r in rows if "failed" not in r]
    base = max(ok_rows[0]["qfree_overhead_p95_ms"], 1.0) if ok_rows else 1.0
    lo, hi = CRITERIA["p99_ratio_range"]
    for r in rows:
        if "failed" in r:
            continue
        r["completed_fraction"] = r["n_completed"] / max(1, r["n_arrived"])
        r["late_event_fraction"] = r["late_events"] / max(1, r["n_events_total"])
        r["sustained"] = bool(r["qfree_overhead_p95_ms"] <= CRITERIA["qfree_overhead_p95_x"] * base and lo <= r["p99_ratio"] <= hi
                              and r["late_event_fraction"] <= CRITERIA["late_event_fraction"] and r["completed_fraction"] >= CRITERIA["completed_fraction"]
                              and r["hub_cpu_fraction"] <= CRITERIA["hub_cpu_fraction"])
    ok = [r["rate_per_s"] for r in rows if r.get("sustained")]
    return max(ok) if ok else None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rates", default="5,20,50,100,200")
    ap.add_argument("--app", default="6200.trip-booking")
    ap.add_argument("--ne", type=int, default=20)
    ap.add_argument("--duration", type=float, default=40.0)
    ap.add_argument("--out", default=str(Path.home() / "testbed-results"))
    a = ap.parse_args(argv)
    from testbed.fleet import hub_token, load_cluster
    laps = load_cluster()
    link = LiveLink.from_cluster(laps, hub_token(), a.ne)
    rows = []
    print(f"{'req/s':>6} {'tasks/s':>8} {'done':>9} {'queue-free overhead p50/p95 ms':>31} {'per task':>9} {'p50 ratio':>9} {'p99 ratio':>9} {'late ev':>8} {'inbox':>6} {'hub cpu':>8}")
    for rate in [float(x) for x in a.rates.split(",")]:
        try:
            r = run_rate(link, rate, a.app, ne=a.ne, duration=a.duration)
        except RuntimeError as e:                    # the testbed gave out at this rate: that is the finding, record it and stop
            rows.append({"rate_per_s": rate, "failed": str(e), "sustained": False})
            print(f"{rate:>6.0f} FAILED: {e}  (the testbed cannot drive this rate)", flush=True)
            break
        rows.append(r)
        print(f"{r['rate_per_s']:>6.0f} {r['tasks_per_s']:>8.0f} {r['n_completed']:>4}/{r['n_arrived']:<4} {r['qfree_overhead_p50_ms']:>14.1f} /{r['qfree_overhead_p95_ms']:>8.1f} ({r['qfree_requests']:>4} req) "
              f"{r['qfree_overhead_per_task_ms']:>7.2f}ms {r['p50_ratio']:>9.2f} {r['p99_ratio']:>9.2f} {r['late_events']:>8} {r['inbox_max']:>6} {r['hub_cpu_fraction']:>7.0%}", flush=True)
    best = verdict(rows)
    print(f"\nsustainable rate (criteria {CRITERIA}): {best} requests/s -> {best * rows[0]['tasks_per_s'] / rows[0]['rate_per_s']:.0f} tasks/s" if best else "\nno rate met the criteria")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    f = out / f"calibration-{time.strftime('%Y%m%d-%H%M%S')}.json"
    f.write_text(json.dumps({"app": a.app, "ne": a.ne, "criteria": CRITERIA, "sustainable_rate_per_s": best, "rows": rows}, indent=1, default=float))
    print("saved", f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
