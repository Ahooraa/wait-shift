"""Tests for testbed/fleet.py: no SSH, no real laptops (the hub's own shell and canned reports stand in)."""
import json

import pytest

from testbed import fleet as fl


def write_cluster(tmp_path, laptops=None):
    laps = laptops or [{"name": "edge-1", "role": "hub", "local": True, "ssh": "10.0.0.1", "wifi_ip": "10.0.0.1"},
                       {"name": "edge-2", "ssh": "10.0.0.2", "wifi_ip": "10.0.0.2"},
                       {"name": "edge-3", "ssh": "10.0.0.3", "wifi_ip": "10.0.0.3", "user": "other"}]
    p = tmp_path / "cluster.json"
    p.write_text(json.dumps({"user": "ahoora", "laptops": laps}))
    return p


def test_load_cluster_defaults_user_and_select(tmp_path):
    laps = fl.load_cluster(write_cluster(tmp_path))
    assert [lap["user"] for lap in laps] == ["ahoora", "ahoora", "other"]
    assert [lap["name"] for lap in fl.select(laps, "edge-3,edge-1")] == ["edge-1", "edge-3"]
    assert len(fl.select(laps, None)) == 3
    with pytest.raises(SystemExit, match="unknown laptop"):
        fl.select(laps, "edge-9")


def test_shipped_example_is_consistent_and_holds_no_real_addresses():
    ex = fl.HERE / "cluster.example.json"
    laps = fl.load_cluster(ex) if json.loads(ex.read_text())["user"] else []
    assert [lap["name"] for lap in laps] == ["edge-1", "edge-2", "edge-3", "edge-4"]
    assert sum(bool(lap.get("local")) for lap in laps) == 1
    text = ex.read_text()
    assert "192.0.2." in text and "192.168." not in text and "10." not in text.replace("0.0.0", "")   # documentation addresses only


def test_missing_cluster_file_explains_why_it_is_local(tmp_path):
    with pytest.raises(SystemExit, match="public"):
        fl.load_cluster(tmp_path / "cluster.json")


def test_real_cluster_file_is_not_tracked_by_git():
    import subprocess
    tracked = subprocess.run(["git", "-C", str(fl.ROOT), "ls-files", "testbed/cluster.json"], capture_output=True, text=True).stdout
    assert tracked.strip() == ""


def test_run_uses_local_shell_and_reports_failure(capsys):
    laps = [{"name": "a", "local": True, "user": "u", "ssh": "x"}, {"name": "b", "local": True, "user": "u", "ssh": "y"}]
    assert fl.cmd_run(laps, ["echo", "hello"]) == 0
    out = capsys.readouterr().out
    assert out.count("hello") == 2 and "===== a (exit 0)" in out
    assert fl.cmd_run(laps, ["exit", "3"]) == 1


def good_report(host, head="a" * 40, governors=("performance",)):
    pins = {"numpy": "1.26.4"}
    return {"hostname": host, "kernel": {"release": "7.0"}, "os": {"pretty": "U"}, "python": {"version": "3.12", "packages": pins},
            "repo": {"head": head}, "boot": {"default_target": "graphical.target"}, "cpu": {"governors": list(governors), "model": "m", "logical": 4},
            "mem": {"total_mb": 8000}, "updates": {"apt_held": [], "periodic": {}}, "time": {"chrony": {"offset_s": 0.001}},
            "wifi": {"ssid": "net", "rate": "270"}, "checks": [{"name": "packages == testbed/requirements.txt", "status": "PASS", "detail": ""}]}


def test_status_summarises_and_flags_differences(monkeypatch, capsys, tmp_path):
    laps = fl.load_cluster(write_cluster(tmp_path))
    reps = {"edge-1": good_report("edge-1"), "edge-2": good_report("edge-2"), "edge-3": good_report("edge-3")}
    monkeypatch.setattr(fl, "get_reports", lambda laps, measured=False: [(lap, reps[lap["name"]], "") for lap in laps])
    assert fl.cmd_status(laps) == 0
    out = capsys.readouterr().out
    assert "edge-3" in out and "[PASS] repo.head" in out
    reps["edge-3"] = good_report("edge-3", head="b" * 40, governors=("powersave",))
    assert fl.cmd_status(laps) == 1
    out = capsys.readouterr().out
    assert "[FAIL] repo.head" in out and "[FAIL] cpu.governors" in out


def test_status_reports_a_laptop_without_report(monkeypatch, capsys, tmp_path):
    laps = fl.load_cluster(write_cluster(tmp_path))
    monkeypatch.setattr(fl, "get_reports", lambda laps, measured=False: [(lap, None, "no report (repo or venv missing?)") for lap in laps])
    assert fl.cmd_status(laps) == 1
    assert "NO REPORT" in capsys.readouterr().out


def test_env_without_fix_names_the_laptop_that_differs(monkeypatch, capsys, tmp_path):
    laps = fl.load_cluster(write_cluster(tmp_path))
    bad = good_report("edge-3")
    bad["checks"][0]["status"] = "FAIL"
    reps = {"edge-1": good_report("edge-1"), "edge-2": good_report("edge-2"), "edge-3": bad}
    monkeypatch.setattr(fl, "get_reports", lambda laps, measured=False: [(lap, reps[lap["name"]], "") for lap in laps])
    assert fl.cmd_env(laps, fix=False) == 1
    out = capsys.readouterr().out
    assert "edge-2   packages match" in out and "edge-3   packages DIFFER" in out and "edge-1" not in out


def test_reboot_never_touches_the_hub_and_waits_for_a_new_boot_id(monkeypatch, capsys, tmp_path):
    laps = fl.load_cluster(write_cluster(tmp_path))
    calls, state = [], {}

    def fake_sh(lap, cmd, timeout=90, input=None):
        calls.append((lap["name"], cmd))
        if "boot_id" in cmd:
            state[lap["name"]] = state.get(lap["name"], 0) + 1          # per laptop: the first read is the old boot, later ones the new
            return (0, "old\n", "") if state[lap["name"]] == 1 else (0, "new\n", "")
        return 0, "", ""
    monkeypatch.setattr(fl, "sh", fake_sh)
    assert fl.cmd_reboot(laps, wait_s=30, sleep=lambda s: None) == 0
    assert "edge-1" not in {n for n, _ in calls}
    assert sum("systemctl reboot" in c for _, c in calls) == 2
    assert "back after" in capsys.readouterr().out


def test_reboot_reports_a_laptop_that_does_not_return(monkeypatch, capsys, tmp_path):
    laps = fl.select(fl.load_cluster(write_cluster(tmp_path)), "edge-2")
    monkeypatch.setattr(fl, "sh", lambda lap, cmd, timeout=90, input=None: (0, "same\n", ""))
    assert fl.cmd_reboot(laps, wait_s=0.2, sleep=lambda s: None) == 1
    assert "did not come back" in capsys.readouterr().out


def test_sync_refuses_when_the_hub_has_uncommitted_work(monkeypatch, capsys, tmp_path):
    laps = fl.load_cluster(write_cluster(tmp_path))
    answers = {("rev-parse", "--abbrev-ref", "HEAD"): "main", ("rev-parse", "HEAD"): "c" * 40}
    monkeypatch.setattr(fl, "hub_git", lambda *a: answers.get(a, " M somefile"))
    monkeypatch.setattr(fl.subprocess, "run", lambda *a, **k: pytest.fail("must not build or send anything"))
    assert fl.cmd_sync(laps) == 1
    assert "uncommitted" in capsys.readouterr().out


def test_discover_updates_changed_addresses_only_with_write(monkeypatch, capsys, tmp_path):
    path = write_cluster(tmp_path)
    monkeypatch.setattr(fl, "hub_ip", lambda: "10.0.0.1")
    live = {"10.0.0.22": "edge-2 wlp2 aa:bb:cc:00:00:02 10.0.0.22", "10.0.0.3": "edge-3 wlp3 aa:bb:cc:00:00:03 10.0.0.3"}
    monkeypatch.setattr(fl, "sh", lambda lap, cmd, timeout=90, input=None: (0, live[lap["ssh"]] + "\n", ""))
    laps = fl.load_cluster(path)
    fl.cmd_discover(laps, write=False, path=path, scan=list(live))
    assert json.loads(path.read_text())["laptops"][1]["ssh"] == "10.0.0.2"
    fl.cmd_discover(laps, write=True, path=path, scan=list(live))
    data = json.loads(path.read_text())["laptops"]
    assert data[1]["ssh"] == "10.0.0.22" and data[1]["wifi_mac"] == "aa:bb:cc:00:00:02"
    assert data[2]["wifi_ip"] == "10.0.0.3" and data[0]["ssh"] == "10.0.0.1"


def test_agent_token_is_created_once_with_private_mode(tmp_path):
    import os
    path = tmp_path / "d" / "agent.token"
    t1 = fl.hub_token(path)
    assert len(t1) == 32 and oct(os.stat(path).st_mode & 0o777) == "0o600"
    assert fl.hub_token(path) == t1


def test_agent_start_and_stop_scripts_are_valid_bash():
    import subprocess
    for script in (fl.AGENT_START.format(port=5300), fl.AGENT_STOP):
        assert subprocess.run(["bash", "-n"], input=script, text=True).returncode == 0
    assert "--port 5300" in fl.AGENT_START.format(port=5300) and "--token-file" in fl.AGENT_START


def test_subnet_of():
    assert fl.subnet_of("192.0.2.77") == "192.0.2.0/24"


def test_clock_scripts_are_valid_bash_and_the_sed_is_safe_to_repeat(tmp_path):
    import re
    import subprocess
    for sc in (fl.CLOCK_HUB.format(subnet="192.0.2.0/24"), fl.CLOCK_AGENT.format(hub="192.0.2.11"), fl.CLOCK_UNDO_HUB, fl.CLOCK_UNDO_AGENT, fl.CLOCK_STATUS):
        assert subprocess.run(["bash", "-n"], input=sc, text=True).returncode == 0
    conf = tmp_path / "chrony.conf"
    conf.write_text("confdir /etc/chrony/conf.d\npool ntp.ubuntu.com iburst maxsources 4\nsourcedir /run/chrony-dhcp\nsourcedir /etc/chrony/sources.d\nrtcsync\n")
    sed = re.search(r"sed -i (.*) /etc/chrony/chrony.conf", fl.CLOCK_AGENT).group(1)
    subprocess.run(f"sed -i {sed} {conf}", shell=True, check=True)
    once = conf.read_text()
    assert "#testbed-disabled# pool ntp.ubuntu.com" in once and "#testbed-disabled# sourcedir /run/chrony-dhcp" in once
    assert {"sourcedir /etc/chrony/sources.d", "rtcsync", "confdir /etc/chrony/conf.d"} <= set(once.splitlines())
    subprocess.run(f"sed -i {sed} {conf}", shell=True, check=True)
    assert conf.read_text() == once


def test_clock_setup_serves_from_the_hub_first_and_points_the_others_at_it(monkeypatch, capsys, tmp_path):
    laps = fl.load_cluster(write_cluster(tmp_path))
    order = []
    monkeypatch.setattr(fl, "run_root", lambda lap, script, timeout=120: (order.append((lap["name"], script)), (0, "ok\n", ""))[1])
    assert fl.cmd_clock(laps, "setup") == 0
    assert order[0][0] == "edge-1" and "allow 10.0.0.0/24" in order[0][1]
    assert {n for n, _ in order[1:]} == {"edge-2", "edge-3"} and all("server 10.0.0.1 " in sc for _, sc in order[1:])
    order.clear()
    assert fl.cmd_clock(laps, "undo") == 0
    assert "testbed-server.conf" in order[0][1] and all("testbed-orig" in sc for _, sc in order[1:])


def test_guard_reports_each_laptop_and_fails_if_any_fails(capsys, tmp_path):
    laps = fl.load_cluster(write_cluster(tmp_path))
    ok = {"checks": [{"name": "no Wi-Fi scan source running", "status": "PASS", "detail": "none"}, {"name": "Wi-Fi link quality", "status": "PASS", "detail": ""}]}
    scan = {"checks": [{"name": "no Wi-Fi scan source running", "status": "FAIL", "detail": "gnome-control-c"}, {"name": "Wi-Fi link quality", "status": "PASS", "detail": ""}]}
    other = {"checks": [{"name": "boot target = multi-user (text)", "status": "FAIL", "detail": "graphical.target"}]}   # not required: not the guard's business
    swap = {"checks": [{"name": "swap off", "status": "FAIL", "detail": "4095 MB"}]}                  # a setting the guard does check
    lines = []
    rc = fl.cmd_guard(laps, reports=[(laps[0], ok, ""), (laps[1], scan, ""), (laps[2], other, "")], extra=lambda lap: [], out=lines.append)
    text = "\n".join(lines)
    assert rc == 1 and "edge-2   FAIL  no Wi-Fi scan source running: gnome-control-c" in text and "edge-1   ok" in text and "edge-3   ok" in text
    assert "1 laptop(s) NOT ready" in text
    lines.clear()
    assert fl.cmd_guard(laps, reports=[(laps[0], ok, ""), (laps[1], ok, ""), (laps[2], swap, "")], extra=lambda lap: [], out=lines.append) == 1
    assert "swap off: 4095 MB" in "\n".join(lines)
    lines.clear()
    assert fl.cmd_guard(laps, reports=[(laps[0], ok, ""), (laps[1], ok, ""), (laps[2], ok, "")], extra=lambda lap: [], out=lines.append) == 0
    assert lines[-1].startswith("guard: all laptops ready")
    lines.clear()
    assert fl.cmd_guard(laps, reports=[(laps[0], ok, ""), (laps[1], ok, ""), (laps[2], None, "no report")], extra=lambda lap: [], out=lines.append) == 1
    lines.clear()
    assert fl.cmd_guard(laps, reports=[(laps[0], ok, ""), (laps[1], ok, ""), (laps[2], ok, "")], extra=lambda lap: [("network monitor running", "no samples")] if lap["name"] == "edge-2" else [],
                        out=lines.append) == 1                                                       # the monitor is not running on edge-2


def test_calibration_refuses_to_start_when_the_guard_fails(monkeypatch, tmp_path):
    from testbed import calibrate as C
    monkeypatch.setattr(fl, "load_cluster", lambda *a, **k: [{"name": "edge-1", "ssh": "x", "user": "u"}])
    monkeypatch.setattr(fl, "cmd_guard", lambda laps, *a, **k: 1)
    monkeypatch.setattr(C.LiveLink, "from_cluster", classmethod(lambda cls, *a, **k: pytest.fail("must not connect when the guard fails")))
    with pytest.raises(SystemExit, match="guard found problems"):
        C.main(["--rates", "5", "--out", str(tmp_path)])
