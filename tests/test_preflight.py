"""Tests for testbed/preflight.py: parsers, the check logic, cross-machine comparison and a loopback probe."""
import copy
import json
import threading

import pytest

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


# ---- the Wi-Fi guard (2026-11-11: GNOME Settings open made three laptops scan every 15 s and stalled the testbed)
IW_LINK = """Connected to 00:00:5e:00:53:01 (on wlan0)
\tSSID: example
\tfreq: 2457.0
\tsignal: -36 dBm
\trx bitrate: 144.4 MBit/s MCS 15 short GI
\ttx bitrate: 130.0 MBit/s MCS 14 short GI
"""
IW_EVENT = ("1794423317.090903: wlan0 (phy #0): scan started\n1794423323.410147: wlan0 (phy #0): scan finished: 2412 2417\n"
            "1794423332.087665: wlan0 (phy #0): scan started\n1794423333.0: wlan0 (phy #0): connected to 00:00:5e:00:53:01\n")


def test_guard_parsers():
    assert pf.running_scan_sources("systemd\ngnome-shell\ngnome-control-c\nbash\nnm-applet\n") == ["gnome-control-c", "nm-applet"]
    assert pf.running_scan_sources("systemd\nbash\n") == [] and pf.running_scan_sources(None) == []
    assert pf.parse_iw_link(IW_LINK) == {"signal_dbm": -36.0, "tx_bitrate_mbps": 130.0, "freq_mhz": 2457.0}
    assert pf.parse_iw_link("Not connected.") == {}
    assert pf.count_scan_events(IW_EVENT) == 2 and pf.count_scan_events("") == 0
    ss = ("State Recv-Q Send-Q Local Address:Port Peer Address:Port Process\n"
          'SYN-SENT 0 1 192.0.2.9:41106 203.0.113.5:443 users:(("snapd",pid=799,fd=13))\n'
          'SYN-SENT 0 1 192.0.2.9:39702 203.0.113.9:443 users:(("snapd",pid=799,fd=14))\n')
    assert pf.parse_stalled_connections(ss) == (2, ["snapd"])
    assert pf.parse_stalled_connections("State Recv-Q Send-Q Local Address:Port Peer Address:Port\n") == (0, [])
    assert pf.parse_stalled_connections(None) == (0, [])


def guard_report(**kw):
    rep = good_report()
    rep["wifi"] = {"interface": "wlan0", "power_save": "off"}
    rep["wifi_guard"] = {"scan_sources": [], "link": {"signal_dbm": -40.0, "tx_bitrate_mbps": 144.4}, "scan_events": 0, "watch_s": 20,
                         "recent_impairment": {"seconds": 60, "impaired": 2, "fraction": 2 / 60, "age_s": 1.0}}
    rep["wifi_guard"].update(kw)
    return rep


def test_guard_passes_on_a_quiet_good_link_and_fails_on_each_problem_when_measured():
    rows = pf.evaluate(guard_report(), measured=True)
    assert not [r for r in rows if r[1] == pf.FAIL], rows
    cases = {"no Wi-Fi scan source running": {"scan_sources": ["gnome-control-c"]},
             "no Wi-Fi scan observed": {"scan_events": 4},
             "no half-open outbound connections": {"stalled_connections": 13, "stalled_owners": ["snapd"]},
             "Wi-Fi link quality": {"link": {"signal_dbm": -72.0, "tx_bitrate_mbps": 144.4}},
             "recent Wi-Fi impairment": {"recent_impairment": {"seconds": 60, "impaired": 30, "fraction": 0.5, "age_s": 1.0}}}
    for name, kw in cases.items():
        assert status(pf.evaluate(guard_report(**kw), measured=True), name) == pf.FAIL, name
        assert status(pf.evaluate(guard_report(**kw), measured=False), name) == pf.WARN, name          # only a warning while setting up
    assert status(pf.evaluate(guard_report(link={"signal_dbm": -40.0, "tx_bitrate_mbps": 72.2}), measured=True), "Wi-Fi link quality") == pf.FAIL   # the weak edge-4 link
    # an idle link's rate bounces (edge-2 showed 65 Mbit/s in 9% of seconds, median 130): with a monitor the median of the last minute decides
    bounce = {"seconds": 60, "impaired": 1, "fraction": 1 / 60, "age_s": 1.0, "median_signal_dbm": -41.0, "median_tx_mbps": 130.0}
    assert status(pf.evaluate(guard_report(link={"signal_dbm": -41.0, "tx_bitrate_mbps": 65.0}, recent_impairment=bounce), True), "Wi-Fi link quality") == pf.PASS
    low = dict(bounce, median_tx_mbps=72.0)
    assert status(pf.evaluate(guard_report(link={"signal_dbm": -41.0, "tx_bitrate_mbps": 144.4}, recent_impairment=low), True), "Wi-Fi link quality") == pf.FAIL


def test_guard_without_a_monitor_warns_and_a_wired_laptop_skips_the_wifi_checks():
    rows = pf.evaluate(guard_report(recent_impairment=None), measured=True)
    assert [s for n, s, d in rows if n == "recent Wi-Fi impairment"] == [pf.WARN]
    rep = good_report()                                                              # no wifi_guard at all (wired)
    assert not [n for n, s, d in pf.evaluate(rep, measured=True) if "Wi-Fi scan" in n]


def test_recent_impairment_reads_the_monitors_log(tmp_path):
    from testbed import netmon as N
    now = 1000.0
    def line(t, bad=False):
        return json.dumps({"t": t, "rtt": {"p": {"n": 10, "lost": 3 if bad else 0, "p50_ms": 3, "p99_ms": 6, "max_ms": 6}}})
    log = tmp_path / "m.jsonl"
    log.write_text("\n".join(line(940.0 + i, bad=(i % 10 == 0)) for i in range(60)) + "\n")      # 6 of the last 60 s impaired
    r = N.recent_impairment(log, seconds=60, now=now)
    assert r["seconds"] == 60 and r["impaired"] == 6 and r["fraction"] == pytest.approx(0.1)
    assert r["median_signal_dbm"] is None and r["median_tx_mbps"] is None      # these test records carry no link fields
    assert N.recent_impairment(log, now=now + 100) is None                              # stale: the monitor stopped
    assert N.recent_impairment(tmp_path / "missing.jsonl") is None
