"""Tests for testbed/preflight.py: parsers, the check logic, cross-machine comparison and a loopback probe."""
import copy
import threading

from testbed import preflight as pf

CHRONY = """Reference ID    : A9FEA97B (169.254.169.123)
Stratum         : 4
System time     : 0.000012345 seconds slow of NTP time
Last offset     : +0.000000123 seconds
Leap status     : Normal
"""


def test_parse_chrony_tracking():
    r = pf.parse_chrony_tracking(CHRONY)
    assert r == {"offset_s": -1.2345e-05, "stratum": 4, "leap": "Normal"}
    assert pf.parse_chrony_tracking("System time : 0.5 seconds fast of NTP time")["offset_s"] == 0.5
    assert pf.parse_chrony_tracking(None) is None


def test_parse_periodic_and_swaps():
    assert pf.parse_periodic('APT::Periodic::Update-Package-Lists "1";\nAPT::Periodic::Unattended-Upgrade "0";') == {
        "Update-Package-Lists": "1", "Unattended-Upgrade": "0"}
    assert pf.parse_swaps("Filename Type Size Used Priority\n/swap.img file 2097148 0 -2\n") == ["/swap.img"]
    assert pf.parse_swaps("Filename Type Size Used Priority\n") == []


def test_pinned_requirements_pin_numpy_1():
    pins = pf.pinned_requirements()
    assert pins["numpy"].startswith("1.")           # capw1_rows.py asserts numpy 1.x
    assert pins["pyyaml"] and "scikit-learn" in pins


def good_report():
    pins = pf.pinned_requirements()
    return {"role": "agent", "hostname": "a", "os": {"pretty": "Ubuntu 24.04.5 LTS"}, "kernel": {"release": "6.8.0-1", "running_pinned_by_hold": True},
            "cpu": {"model": "X", "logical": 8, "governors": ["performance"], "driver": None, "no_turbo": None},
            "mem": {"total_mb": 16000, "swap_total_mb": 0, "swaps": []},
            "time": {"chrony": {"offset_s": 0.0001, "stratum": 3, "leap": "Normal"}, "chrony_installed": True, "timedatectl": {}},
            "boot": {"default_target": "multi-user.target"},
            "updates": {"apt_timers": {"apt-daily.timer": "disabled", "apt-daily-upgrade.timer": "disabled"},
                        "periodic": {"Update-Package-Lists": "0", "Unattended-Upgrade": "0"}, "unattended_installed": False,
                        "snap_refresh_held": True, "apt_held": ["linux-image-generic"]},
            "power": {"ac_online": True, "battery_status": "Full"}, "wifi": {"interface": None},
            "python": {"version": "3.12.3", "executable": "/v/bin/python", "venv": True, "packages": dict(pins), "numba_jit_works": True},
            "repo": {"head": "a" * 40, "branch": "main", "dirty_tracked": False}, "loadavg_1m": 0.1, "disk_free_gb": 50.0}


def status(rows, name):
    return next(s for n, s, _ in rows if n == name)


def test_good_machine_has_no_fail_in_measured_mode():
    rows = pf.evaluate(good_report(), measured=True)
    assert not [r for r in rows if r[1] == pf.FAIL], rows


def test_setting_failures_are_warn_unless_measured():
    rep = good_report()
    rep["cpu"]["governors"] = ["powersave"]
    rep["mem"]["swap_total_mb"] = 4096
    rep["boot"]["default_target"] = "graphical.target"
    for name in ("cpu governor = performance", "swap off", "boot target = multi-user (text)"):
        assert status(pf.evaluate(rep, False), name) == pf.WARN
        assert status(pf.evaluate(rep, True), name) == pf.FAIL


def test_wrong_package_and_dirty_repo_always_fail():
    rep = good_report()
    rep["python"]["packages"]["numpy"] = "2.5.4"
    rep["repo"]["dirty_tracked"] = True
    rows = pf.evaluate(rep, False)
    assert status(rows, "packages == testbed/requirements.txt") == pf.FAIL
    assert status(rows, "repo: tracked files unmodified") == pf.FAIL


def test_chrony_offset_limit():
    rep = good_report()
    rep["time"]["chrony"]["offset_s"] = 0.02
    assert status(pf.evaluate(rep, True), "chrony synchronised") == pf.FAIL
    rep["time"]["chrony"] = None
    assert status(pf.evaluate(rep, True), "chrony synchronised") == pf.FAIL


def test_compare_flags_any_difference_and_reports_hardware():
    a, b = good_report(), copy.deepcopy(good_report())
    b["hostname"], b["cpu"]["logical"], b["mem"]["total_mb"] = "b", 4, 8000      # hardware may differ
    rows = {n: s for n, s, _ in pf.compare([a, b])}
    assert rows["kernel.release"] == pf.PASS and rows["cpu.logical"] == pf.INFO
    b["kernel"]["release"] = "6.8.0-2"
    b["repo"]["head"] = "b" * 40
    rows = {n: s for n, s, _ in pf.compare([a, b])}
    assert rows["kernel.release"] == pf.FAIL and rows["repo.head"] == pf.FAIL


def test_tree_manifest_detects_change(tmp_path):
    (tmp_path / "x").write_bytes(b"123")
    m1 = pf.tree_manifest(tmp_path)
    (tmp_path / "y").write_bytes(b"4")
    m2 = pf.tree_manifest(tmp_path)
    assert (m1["files"], m1["bytes"], m2["files"], m2["bytes"]) == (1, 3, 2, 4) and m1["hash"] != m2["hash"]
    assert pf.tree_manifest(tmp_path / "missing") is None


def test_collect_runs_on_this_machine():
    rep = pf.collect("agent")
    for k in ("hostname", "kernel", "cpu", "mem", "time", "boot", "updates", "power", "python", "repo"):
        assert k in rep
    assert rep["python"]["packages"]["numpy"] is not None
    assert len(pf.evaluate(rep, False)) > 10


def test_loopback_probe_measures_rtt_clock_and_throughput():
    port_box, ev = [], threading.Event()
    threading.Thread(target=pf.serve, kwargs={"port": 0, "host": "127.0.0.1", "ready": lambda p: (port_box.append(p), ev.set())},
                     daemon=True).start()
    assert ev.wait(5)
    r = pf.probe("127.0.0.1", port_box[0], pings=40, mb=2, rounds=2)
    assert r["rtt_ms"]["min"] >= 0 and r["rtt_ms"]["median"] < 50
    assert abs(r["clock_offset_ms_peer_minus_local"]) < 5          # same machine: same clock
    assert r["up_MBps"] > 1 and r["down_MBps"] > 1
