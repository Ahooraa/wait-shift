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


def build_plan(name):
    if name != "dev-protocol":
        raise SystemExit(f"unknown plan {name!r}")
    items = []
    for app in ORDER:
        rho, cap, warm, window, drain = CELLS[app]
        for seed in (1, 2, 3):                                     # development seeds only: the held-out seeds 7-10 are never in a dry run
            systems = ["frozen4", "rl"]
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
    return subprocess.run([PY, str(ROOT / "testbed" / "fleet.py"), *a], cwd=ROOT, capture_output=True, text=True, timeout=timeout)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plan", default="dev-protocol")
    ap.add_argument("--dir", required=True)
    ap.add_argument("--guard-wait", type=float, default=300.0)
    ap.add_argument("--guard-tries", type=int, default=6)
    a = ap.parse_args(argv)
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
                with open(d / "items" / f"{it['id']}.log", "a") as lf:
                    p = subprocess.run([PY, *it["argv"], "--out", str(d / "items")], cwd=ROOT, stdout=lf, stderr=subprocess.STDOUT, text=True)
                tail = (d / "items" / f"{it['id']}.log").read_text()[-3000:]
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
