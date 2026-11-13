#!/usr/bin/env python3
"""Run a list of testbed runs one after the other, unattended, and keep a record (the precursor of the phase 5 driver).

Each item is one `controller_check.py` call (one application, one seed, one system), which itself runs the guard (with its cooldown and retries) before
anything is measured. This script adds only what an unattended night needs:
  * resume: an item whose marker file exists is skipped, so the queue can be started again after any stop;
  * a refused guard is waited out (default 5 minutes, up to 6 times) and then the item is MOVED ON from, never run without the guard;
  * a crashed item gets one retry after the agents were restarted; a second failure is recorded and the queue goes on;
  * a file STOP in the queue's folder ends the queue after the item that is running (it never interrupts a run);
  * `status.json` and `queue.log` say at any time what ran, what failed and what is left; `meta.json` holds the commit and whether the tree was dirty.
Nothing here changes a result or a setting: it runs the same command a person would type.

    ~/venv-dfps/bin/python testbed/queue_runs.py --plan dev-protocol --dir ~/testbed-results/dev-protocol-20261112
"""
from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable

# the pre-registered cells (knowledge/synthesis/testbed-preregistration.md, section 4): application -> (rho, rate cap, warm-up, window, drain)
CELLS = {"690.ml": (0.56, None, 60, 300, 60), "660.map-reduce": (0.45, None, 60, 300, 60), "650.vid": (0.7, None, 60, 600, 60),
         "6200.trip-booking": (0.7, 42.0, 60, 300, 60), "680.excamera": (0.7, None, 180, 1800, 240)}
ORDER = ["690.ml", "660.map-reduce", "650.vid", "6200.trip-booking", "680.excamera"]


PLANS = {   # name -> (applications, seeds, systems); the order of the systems inside a block is drawn once per block. `systems` is a list, or a dict seed -> list
    "dev-protocol": (ORDER, (1, 2, 3), ["frozen4", "rl"]),                                                         # the overnight dry run of 12 Nov 2026 (30 items)
    "initial-f5-bstar": (["690.ml", "660.map-reduce", "650.vid", "680.excamera"], (1, 2), ["frozen5", "bstar"]),    # initial runs, development seeds 1 and 2 (user, 12 Nov): F5 and B* on the dry run's cells
    # 13 Nov (user): the steady-Poisson initial runs were stopped ("the steady Poisson ruined the experiment") and replaced by trace-driven arrivals: Azure 2019 only, extended
    # windows, two development seeds, five systems. Seed-major order, so a whole seed (every application, every system) is complete before the second starts.
    # 13 Nov (user): the CAP-U runs above are withdrawn; the rerun is on CAP-W2 (measured memory sizes, rounded to 0.01), FaaSPR and Graph-Aware are dropped from the live runs (user, 14 Nov: they stay in the simulator sweep), Heu is added back; four systems F5, B*, RL, Heu. The smoke plan runs the same code on one short cell per system before the queue.
    "azure-capw2": dict(apps=["690.ml", "660.map-reduce", "650.vid", "680.excamera"], seeds=(1, 2), arms=["frozen5", "bstar", "rl", "heu"], arrivals="azure", seed_major=True, weights="memory"),
    "smoke-heu": dict(apps=["690.ml"], seeds=(1,), arms=["heu"], arrivals="azure", weights="memory", cells={"690.ml": (0.5, 60, 240, 120)}),
    "smoke-capw2": dict(apps=["690.ml"], seeds=(1,), arms=["frozen5", "bstar", "rl"], arrivals="azure", weights="memory", cells={"690.ml": (0.5, 60, 240, 120)}),
    "azure-initial": dict(apps=["690.ml", "660.map-reduce", "650.vid", "680.excamera"], seeds=(1, 2), arms=["frozen5", "bstar", "rl", "faaspr", "ga"],
                          arrivals="azure", seed_major=True),
}


# Azure-arrival cells: application -> (mean rho, warm-up, window, drain). One mean load for every application (0.5, the lower of the two levels agreed on 12 Nov); where the busiest
# minute would offer more than 300 tasks per second (the hub's limit) the whole series is scaled down (meta rho_effective / rho_peak say what was offered). The window is 15 minutes
# (15 minute-bins of the trace) for every application; ExCamera keeps its longer warm-up. The drain is a MAXIMUM of 600 s, not a fixed wait: a live run ends as soon as every request
# has completed (livesim.py: no events left), so the drain only costs time for a system that has a backlog; requests still unfinished after it are reported (n_unfinished), never dropped.
AZURE_CELLS = {"690.ml": (0.5, 60, 900, 600), "660.map-reduce": (0.5, 60, 900, 600), "650.vid": (0.5, 60, 900, 600), "680.excamera": (0.5, 180, 900, 600)}


def build_azure_plan(spec):
    items = []
    blocks = [(app, seed) for seed in spec["seeds"] for app in spec["apps"]] if spec.get("seed_major") else [(app, seed) for app in spec["apps"] for seed in spec["seeds"]]
    for app, seed in blocks:
        rho, warm, window, drain = spec.get("cells", AZURE_CELLS)[app]
        systems = list(spec["arms"])
        random.Random(f"azure-{app}-{seed}").shuffle(systems)            # the order inside a block is drawn once, per block, and recorded
        for arm in systems:
            argv = ["testbed/controller_check.py", "--arm", arm, "--app", app, "--ne", "10", "--rho", str(rho), "--duration", str(warm + window), "--warmup", str(warm),
                    "--drain", str(drain), "--seeds", str(seed), "--arrivals", spec["arrivals"], "--weights", spec.get("weights", "memory")]   # 13 Nov: CAP-W2, never CAP-U
            items.append({"id": f"{app}.s{seed}.{arm}", "argv": argv})
    return items


def build_plan(name):
    if name not in PLANS:
        raise SystemExit(f"unknown plan {name!r}; known: {sorted(PLANS)}")
    if isinstance(PLANS[name], dict):
        return build_azure_plan(PLANS[name])
    apps, seeds, arms = PLANS[name]
    items = []
    for app in apps:
        rho, cap, warm, window, drain = CELLS[app]
        for seed in seeds:                                         # development seeds only: the held-out seeds 7-10 are never in a dry run or an initial run
            systems = list(arms[seed] if isinstance(arms, dict) else arms)
            random.Random(f"{app}-{seed}").shuffle(systems)        # the order inside a block is drawn once, per block, and recorded
            for arm in systems:
                argv = ["testbed/controller_check.py", "--arm", arm, "--app", app, "--ne", "10", "--rho", str(rho), "--duration", str(warm + window),
                        "--warmup", str(warm), "--drain", str(drain), "--seeds", str(seed)]
                if cap:
                    argv += ["--rate-cap", str(cap)]
                items.append({"id": f"{app}.s{seed}.{arm}", "argv": argv})
    return items


def git_state():
    def g(*a):
        return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    return {"commit": g("rev-parse", "HEAD"), "dirty_files": g("status", "--short", "--untracked-files=no").splitlines()}


def fleet(*a, timeout=180):
    try:
        return subprocess.run([PY, str(ROOT / "testbed" / "fleet.py"), *a], cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    except Exception as e:                                          # an unreachable laptop must not end the queue: the next item's guard will say what is wrong
        return subprocess.CompletedProcess(a, returncode=1, stdout="", stderr=f"fleet {' '.join(a)} failed: {e!r}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plan", default="dev-protocol")
    ap.add_argument("--dir", required=True)
    ap.add_argument("--guard-wait", type=float, default=300.0)
    ap.add_argument("--guard-tries", type=int, default=6)
    ap.add_argument("--item-timeout", type=float, default=5400.0, help="hard limit on one item in seconds (a run that hangs is killed and treated as a crash; the longest normal item is under 45 minutes)")
    a = ap.parse_args(argv)
    try:
        import numpy, numba                                         # noqa: F401  (12 Nov 2026: a start with the system Python, which has neither, turned every crash into a "refused guard")
    except ImportError as e:
        raise SystemExit(f"this Python ({sys.executable}) cannot run the testbed ({e}); start with ~/venv-dfps/bin/python")
    d = Path(a.dir).expanduser()
    (d / "items").mkdir(parents=True, exist_ok=True)
    items = build_plan(a.plan)
    (d / "meta.json").write_text(json.dumps({"plan": a.plan, "started": time.strftime("%Y-%m-%d %H:%M:%S"), "git": git_state(), "n_items": len(items), "order": [i["id"] for i in items]}, indent=1))
    log = open(d / "queue.log", "a", buffering=1)

    def say(msg):
        line = f"{time.strftime('%H:%M:%S')} {msg}"
        print(line, flush=True)
        log.write(line + "\n")

    status = {"done": [], "failed": [], "skipped_guard": []}

    def save():
        status["left"] = [i["id"] for i in items if i["id"] not in status["done"] + [f["id"] for f in status["failed"]] + status["skipped_guard"]]
        (d / "status.json").write_text(json.dumps(status, indent=1))

    say(f"queue {a.plan}: {len(items)} items, commit {git_state()['commit'][:7]}")
    for n, it in enumerate(items, 1):
        marker = d / "items" / f"{it['id']}.ok"
        if marker.exists():
            status["done"].append(it["id"])
            continue
        if (d / "STOP").exists():
            say("STOP file found: ending the queue before the next item")
            break
        outcome = None
        for attempt in (1, 2):
            for g in range(1, a.guard_tries + 1):
                t0 = time.time()
                logfile = d / "items" / f"{it['id']}.log"
                offset = logfile.stat().st_size if logfile.exists() else 0      # only what THIS attempt wrote counts: old text of an earlier attempt once read as a refusal
                with open(logfile, "a") as lf:
                    try:
                        p = subprocess.run([PY, *it["argv"], "--out", str(d / "items")], cwd=ROOT, stdout=lf, stderr=subprocess.STDOUT, text=True, timeout=a.item_timeout)
                    except subprocess.TimeoutExpired:       # 13 Nov 2026: without a limit one hung run (an agent that stops answering) would hold the whole night
                        lf.write(f"\nitem hung: killed after {a.item_timeout:.0f} s by the queue runner\n")
                        p = subprocess.CompletedProcess(it["argv"], returncode=-9)
                tail = logfile.read_bytes()[offset:].decode(errors="replace")[-3000:]
                if p.returncode == 0:
                    outcome = "ok"
                    break
                if "the guard refused" in tail:
                    say(f"[{n}/{len(items)}] {it['id']}: guard refused ({g}/{a.guard_tries}); waiting {a.guard_wait:.0f} s")
                    time.sleep(a.guard_wait)
                    if (d / "STOP").exists():
                        break
                    continue
                outcome = "crash"
                break
            if outcome == "ok":
                break
            if outcome is None:
                outcome = "guard"
                break
            if attempt == 1:
                say(f"[{n}/{len(items)}] {it['id']}: crashed (exit {p.returncode}); restarting the agents and trying once more")
                fleet("agents", "stop")
                time.sleep(5)
                fleet("agents", "start")
                time.sleep(20)
                outcome = None
        if outcome == "ok":
            line = next((ln for ln in tail.splitlines() if ln.startswith("seed ")), "")
            marker.write_text(line + "\n")
            status["done"].append(it["id"])
            say(f"[{n}/{len(items)}] {it['id']} done in {time.time() - t0:.0f} s: {line[:230]}")
        elif outcome == "guard":
            status["skipped_guard"].append(it["id"])
            say(f"[{n}/{len(items)}] {it['id']}: SKIPPED, the guard kept refusing (it was not bypassed)")
        else:
            status["failed"].append({"id": it["id"], "tail": tail[-400:]})
            say(f"[{n}/{len(items)}] {it['id']}: FAILED twice: {tail[-200:]!r}")
        save()
    save()
    say(f"queue ended: {len(status['done'])} done, {len(status['failed'])} failed, {len(status['skipped_guard'])} skipped by the guard, {len(status['left'])} left")
    return 0


if __name__ == "__main__":
    sys.exit(main())
