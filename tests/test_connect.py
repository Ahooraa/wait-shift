"""Tests for testbed/connect.py: hub and joining laptops on loopback (no network, no apt, no git push)."""
import json
import socket
import threading
import urllib.error
import urllib.request

import pytest

from testbed import connect as cn
from testbed import preflight as pf

TOKEN = "abc123"
KW = dict(pings=8, mb=1, rounds=1, connect_timeout=2)


def stub_report(host):
    return lambda: {"hostname": host, "checks": [{"name": "x", "status": "WARN", "detail": ""}]}


def start_hub(tmp_path, laptops, turn_timeout=60.0, files=None):
    hub = cn.Hub(laptops, TOKEN, tmp_path / "out", turn_timeout, files or {}, {"branch": "b", "commit": "c" * 40}, log=lambda m: None)
    srv, port = cn.serve_hub(hub, "127.0.0.1", 0)
    return hub, srv, f"http://127.0.0.1:{port}"


def client(url, name, results, **kw):
    def run():
        results[name] = cn.run_client(url, TOKEN, listen_port=0, advertise_ip="127.0.0.1", report_fn=stub_report(name),
                                      probe_kw=KW, wait_s=40, log=lambda m: None, hostname=name, **kw)
    t = threading.Thread(target=run, daemon=True)
    t.start()
    return t


def test_all_pairs_connect_and_files_are_written(tmp_path):
    hub, srv, url = start_hub(tmp_path, 3)
    res = {}
    ts = [client(url, n, res) for n in ("alpha", "beta", "gamma")]
    assert hub.done.wait(40), hub.summary_text
    for t in ts:
        t.join(10)
    assert hub.ok is True
    assert "6 of 6 laptop pairs connected" in hub.summary_text
    for n in ("alpha", "beta", "gamma"):
        assert len(res[n]) == 2 and all("error" not in r for r in res[n].values())
    run = hub.run_dir
    assert (run / "summary.txt").exists() and (run / "mesh.json").exists() and len(list(run.glob("report_*.json"))) == 3
    srv.shutdown()


def test_unreachable_laptop_is_reported_with_a_hint(tmp_path):
    hub, srv, url = start_hub(tmp_path, 3, turn_timeout=3.0)
    res = {}
    ts = [client(url, n, res) for n in ("alpha", "beta")]
    dead = socket.socket()                                           # a laptop that registered but listens nowhere
    dead.bind(("127.0.0.1", 0))
    dead_port = dead.getsockname()[1]
    dead.close()
    body = json.dumps({"host": "ghost", "ip": "127.0.0.1", "port": dead_port}).encode()
    urllib.request.urlopen(urllib.request.Request(f"{url}/register?t={TOKEN}", body, {"Content-Type": "application/json"}))
    assert hub.done.wait(40)
    assert hub.ok is False
    assert "FAILED" in hub.summary_text and "ghost" in hub.summary_text and "What this usually means" in hub.summary_text
    for t in ts:
        t.join(10)
    srv.shutdown()


def test_wrong_token_and_unknown_paths_are_refused(tmp_path):
    hub, srv, url = start_hub(tmp_path, 2, files={"join.sh": tmp_path / "x"})
    for bad in (f"{url}/peers", f"{url}/peers?t=nope", f"{url}/join.sh?t=nope"):
        with pytest.raises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(bad)
        assert e.value.code == 403
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(f"{url}/etc/passwd?t={TOKEN}")
    assert e.value.code == 404
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(urllib.request.Request(f"{url}/register?t={TOKEN}", b"not json"))
    assert e.value.code == 400
    meta = urllib.request.urlopen(f"{url}/meta.txt?t={TOKEN}").read().decode()
    assert "branch=b" in meta
    srv.shutdown()


def test_duplicate_hostname_is_flagged(tmp_path):
    logs = []
    hub = cn.Hub(2, TOKEN, tmp_path, log=logs.append)
    hub.register({"host": "ubuntu", "ip": "10.0.0.2", "port": 5201})
    hub.register({"host": "ubuntu", "ip": "10.0.0.3", "port": 5201})
    assert any("also called 'ubuntu'" in m for m in logs)


def test_lan_ip_returns_an_address():
    assert cn.lan_ip("127.0.0.1").count(".") == 3


def test_join_script_is_valid_bash():
    import subprocess
    assert subprocess.run(["bash", "-n", str(cn.HERE / "join.sh")]).returncode == 0
