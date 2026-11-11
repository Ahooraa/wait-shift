"""When did the last measured run end? The guard needs it to leave a cooldown after our own traffic.

The network monitor's "last 60 s" window contains whatever the testbed itself just sent. After a 50 requests/s run the guard saw 15 to 18% of the last minute
impaired on all four laptops and refused the next pass, although nothing outside had changed (2026-11-11, nine-run series; waiting 90 s cleared both
refusals). So every run stamps its end time here, on the hub, and the guard waits until COOLDOWN_S have passed since then before it looks at the monitor.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

COOLDOWN_S = 90.0          # longer than the monitor's 60 s window, so none of the run's own traffic is left in it


def mark_path():
    return Path(os.environ.get("TESTBED_RUN_MARK") or Path.home() / "testbed-logs" / "last-run-end")


def mark_run_end(now=None):
    """Record that a run has just ended. Never raises: a missing stamp only means the guard does not wait."""
    try:
        p = mark_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"{time.time() if now is None else now:.3f}\n")
    except OSError:
        pass


def last_run_end(path=None):
    """Epoch seconds when the last run ended, or None when no run has been recorded (or the stamp is unreadable)."""
    try:
        return float((path or mark_path()).read_text().strip())
    except (OSError, ValueError):
        return None


def cooldown_remaining(cooldown_s=COOLDOWN_S, now=None, path=None):
    """Seconds still to wait before the Wi-Fi may be judged; 0 when no run is recorded or the cooldown has passed."""
    end = last_run_end(path)
    if end is None:
        return 0.0
    now = time.time() if now is None else now
    return max(0.0, min(cooldown_s, end + cooldown_s - now))      # min(): a stamp from the future (clock step) never waits longer than the cooldown
