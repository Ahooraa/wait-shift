"""Tests for testbed/runmark.py: the stamp of the last run's end and the cooldown the guard derives from it."""
import pytest

from testbed import runmark as rm


def test_no_stamp_means_no_wait(tmp_path):
    assert rm.last_run_end(tmp_path / "missing") is None
    assert rm.cooldown_remaining(90, now=1000.0, path=tmp_path / "missing") == 0.0
    bad = tmp_path / "bad"
    bad.write_text("not a number\n")
    assert rm.last_run_end(bad) is None


def test_cooldown_counts_down_and_is_capped(tmp_path):
    rm.mark_run_end(now=1000.0)                                      # conftest points the stamp at a private file
    p = rm.mark_path()
    assert rm.last_run_end(p) == 1000.0
    assert rm.cooldown_remaining(90, now=1000.0) == 90.0
    assert rm.cooldown_remaining(90, now=1030.0) == pytest.approx(60.0)
    assert rm.cooldown_remaining(90, now=1090.0) == 0.0 and rm.cooldown_remaining(90, now=5000.0) == 0.0
    assert rm.cooldown_remaining(90, now=900.0) == 90.0              # a stamp from the future (clock step) never waits longer than the cooldown


def test_cooldown_is_longer_than_the_monitors_window():
    from testbed import netmon
    import inspect
    window = inspect.signature(netmon.recent_impairment).parameters["seconds"].default
    assert rm.COOLDOWN_S > window                                    # otherwise some of the run's own traffic would still be in the window


def test_unwritable_stamp_never_raises(monkeypatch, tmp_path):
    f = tmp_path / "afile"
    f.write_text("x")
    monkeypatch.setenv("TESTBED_RUN_MARK", str(f / "sub" / "stamp"))    # a directory below a regular file cannot be created
    rm.mark_run_end()                                                # must not raise


@pytest.mark.parametrize("script", ["testbed/fleet.py", "testbed/calibrate.py"])
def test_the_scripts_start_as_scripts(script):
    """pytest has the repository root on its path, a script started by hand does not: an import that only works under pytest broke `fleet.py guard`
    (2026-11-11) and no unit test noticed."""
    import subprocess
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    r = subprocess.run([sys.executable, str(root / script), "--help"], capture_output=True, text=True, cwd="/", timeout=60)
    assert r.returncode == 0, r.stderr[-400:]
