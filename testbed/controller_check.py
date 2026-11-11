#!/usr/bin/env python3
"""Phase 4 check: the paper's controller (FROZEN-4) on the real laptops against the same run in the simulator, and the hub's health while it runs.

For every seed: the guard (with its cooldown), the simulator run (the reference: same scenario, same layout, same common random numbers), a warm-up of the
controller's compiled code on the hub, then the live run on the agents. The two are NOT expected to match request by request (the live run has the
controller's real compute time and real transfers, so its trajectory differs; the noise floor of a single run is about 1.5% on P99). What is checked:
  * every request completes, none is lost; cold starts and moved requests of the same order as in the simulator;
  * the live makespan distribution against the simulated one (P50 and P99 ratios);
  * the hub with the controller running: late events, queued events, CPU, and how long the controller's decisions took (adjust_ms, plan_ms).

    ~/venv-dfps/bin/python testbed/controller_check.py --app 660.map-reduce --ne 10 --rho 0.3 --duration 240 --seeds 1

Results go to ~/testbed-results/ (local, not in the repository).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))        # run as a script: the repository root must be importable

from testbed import frozen_live as FL                                   # noqa: E402
from testbed import runmark                                             # noqa: E402
from testbed import sebs_scenario as S                                  # noqa: E402
from testbed.livesim import LiveLink, LiveSim                           # noqa: E402
from dfps.nsga2 import PlacementProblem                                 # noqa: E402

KEYS = ("n_arrived", "n_completed", "n_unfinished", "p50_makespan", "p99_makespan", "cold_starts", "n_adjust", "n_noop_adjust", "n_moved",
        "adjust_ms_p95", "plan_ms_p95", "plan_ms_mean", "mover_impl", "mover_pass", "event_hash")


def pick(r):
    return {k: r.get(k) for k in KEYS}


def one_seed(link, args, seed):
    sc, samp = S.build(seed, apps=[args.app], rho=args.rho, ne=args.ne, duration_s=args.duration, rate_cap=args.rate_cap)
    X0 = PlacementProblem(sc.network, sc.ecc, np.array([f.exec_time for f in sc.functions])).random(np.random.default_rng(seed))
    ref_sim, _ = FL.build(sc, X0, seed, arm=args.arm, warmup=args.warmup, duration=args.duration, exec_sampler=samp)
    t0 = time.time()
    ref = ref_sim.run()
    ref_wall = time.time() - t0
    FL.warm_up_kernels(sc, X0, seed=seed, arm=args.arm)
    sim, adj = FL.build(sc, X0, seed, arm=args.arm, warmup=args.warmup, duration=args.duration, exec_sampler=samp, sim_cls=LiveSim, link=link, drain_s=args.drain)
    t0 = time.time()
    live = sim.run()
    wall = time.time() - t0
    lv = live["live"]
    ops = lv["runs"] + lv["warm"] + lv["transfers"] + lv["relocation_transfers"]
    out = {"seed": seed, "rate_per_s": sc.meta["rate_per_s"], "rho_effective": sc.meta["rho_effective"], "tasks_per_s": sc.meta["rate_per_s"] * sc.workflows[0].n,
           "sim": pick(ref), "live": pick(live), "sim_wall_s": round(ref_wall, 1), "live_wall_s": round(wall, 1),
           "p50_ratio": live["p50_makespan"] / ref["p50_makespan"], "p99_ratio": live["p99_makespan"] / ref["p99_makespan"],
           "cold_ratio": live["cold_starts"] / max(1, ref["cold_starts"]), "moved_ratio": (live.get("n_moved") or 0) / max(1, ref.get("n_moved") or 0),
           "late_events": lv["late_events"], "late_event_fraction": lv["late_events"] / max(1, ops), "inbox_max": lv["inbox_max"],
           "hub_cpu_fraction": lv["hub_cpu_fraction"], "agent_ops": lv["agent_ops"], "events_total": ops,
           "relocation_transfers": lv["relocation_transfers"], "agent_timer_lateness_max_ms": max(a["lateness_s"]["max"] for a in lv["agents"].values()) * 1e3}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--app", default="660.map-reduce")
    ap.add_argument("--ne", type=int, default=10)
    ap.add_argument("--rho", type=float, default=0.3)
    ap.add_argument("--rate-cap", type=float, default=None, help="most requests per second to drive (rho_effective says what load that is)")
    ap.add_argument("--duration", type=float, default=240.0)
    ap.add_argument("--warmup", type=float, default=60.0)
    ap.add_argument("--drain", type=float, default=60.0)
    ap.add_argument("--arm", default="frozen4", choices=sorted(FL.ARMS))
    ap.add_argument("--seeds", default="1")
    ap.add_argument("--out", default=str(Path.home() / "testbed-results"))
    ap.add_argument("--guard-retries", type=int, default=2, help="how often a refused guard is retried (after --guard-wait seconds) before the run is given up")
    ap.add_argument("--guard-wait", type=float, default=60.0)
    ap.add_argument("--no-guard", action="store_true", help="skip the check that the Wi-Fi and the laptops are ready (not for measured runs)")
    a = ap.parse_args(argv)
    from testbed import fleet
    laps = fleet.load_cluster()
    rows = []
    for seed in [int(x) for x in a.seeds.split(",")]:
        refusals = 0
        while not a.no_guard and fleet.cmd_guard(laps, cooldown_s=runmark.COOLDOWN_S):
            refusals += 1                                                  # recorded with the result: a refused guard is part of the record, never hidden
            if refusals > a.guard_retries:
                raise SystemExit(f"the guard refused {refusals} times (listed above); fix the problem or use --no-guard for a trial run")
            print(f"guard refused ({refusals} of {a.guard_retries} retries); waiting {a.guard_wait:.0f} s", flush=True)
            time.sleep(a.guard_wait)
        link = LiveLink.from_cluster(laps, fleet.hub_token(), a.ne)      # AFTER the guard: an agent keeps ONE control connection and the guard's check of it replaces ours
        r = one_seed(link, a, seed)
        r["guard_refusals_before"] = refusals
        rows.append(r)
        print(f"seed {seed}: {r['rate_per_s']:.1f} req/s ({r['tasks_per_s']:.0f} tasks/s), done {r['live']['n_completed']}/{r['live']['n_arrived']} "
              f"(sim {r['sim']['n_completed']}/{r['sim']['n_arrived']}); p50 ratio {r['p50_ratio']:.2f}, p99 ratio {r['p99_ratio']:.2f}; cold {r['live']['cold_starts']} "
              f"(sim {r['sim']['cold_starts']}); moved {r['live']['n_moved']} (sim {r['sim']['n_moved']}); late events {r['late_events']}, inbox {r['inbox_max']}, "
              f"hub cpu {r['hub_cpu_fraction']:.0%}; adjust p95 {r['live']['adjust_ms_p95']:.1f} ms (sim {r['sim']['adjust_ms_p95']:.1f}), plan p95 {r['live']['plan_ms_p95']:.1f} ms; "
              f"wall {r['live_wall_s']:.0f} s", flush=True)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    f = out / f"controller-{a.arm}-{time.strftime('%Y%m%d-%H%M%S')}.json"
    f.write_text(json.dumps({"args": vars(a), "rows": rows}, indent=1, default=float))
    print("saved", f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
