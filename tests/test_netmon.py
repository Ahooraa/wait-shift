"""Tests for testbed/netmon.py (the network monitor) and the fleet commands that run it."""
import json
import socket
import subprocess
import threading
import time

import pytest

from testbed import fleet as fl
from testbed import netmon as N

STATION = """Station 00:00:5e:00:53:01 (on wlan0)
\tinactive time:\t37 ms
\trx bytes:\t1790126107
\trx packets:\t2259797
\ttx bytes:\t5722806215
\ttx packets:\t1270995
\ttx retries:\t351
\ttx failed:\t2
\tbeacon loss:\t1
\tbeacon rx:\t212107
\trx drop misc:\t1601
\tsignal:  \t-35 [-35, -35] dBm
\tsignal avg:\t-33 [-33, -33] dBm
\ttx bitrate:\t866.7 MBit/s VHT-MCS 9 80MHz short GI VHT-NSS 2
\ttx duration:\t0 us
\trx bitrate:\t702.0 MBit/s VHT-MCS 9 80MHz short GI VHT-NSS 2
"""
SNMP = "Tcp: RtoAlgorithm RtoMin RtoMax MaxConn ActiveOpens PassiveOpens AttemptFails EstabResets CurrEstab InSegs OutSegs RetransSegs InErrs\nTcp: 1 200 120000 -1 13891 10762 215 870 109 2951664 6205856 5942 211\n"


def rec(t, **kw):
    base = {"t": t, "host": "edge-9", "signal_dbm": -40.0, "tx_bitrate_mbps": 500.0, "d_tx_packets": 100.0, "d_tx_retries": 1.0, "d_tcp_retrans": 0,
            "d_beacon_loss": 0.0, "rtt": {"edge-2": {"n": 10, "lost": 0, "p50_ms": 3.0, "p99_ms": 6.0, "max_ms": 6.0}}}
    base.update(kw)
    return base


def test_parsers_read_the_real_formats():
    st = N.parse_station_dump(STATION)
    assert st["signal_dbm"] == -35 and st["signal_avg_dbm"] == -33 and st["tx_bitrate_mbps"] == 866.7 and st["rx_bitrate_mbps"] == 702.0
    assert (st["tx_retries"], st["tx_failed"], st["beacon_loss"], st["tx_packets"]) == (351, 2, 1, 1270995)
    assert N.parse_station_dump("") == {} and N.parse_station_dump("No such device")  == {}
    assert N.parse_tcp_snmp(SNMP)["RetransSegs"] == 5942 and N.parse_tcp_snmp("") == {}
    assert N.parse_freq_mhz("Connected to ...\n\tfreq: 5745.0\n") == 5745.0 and N.parse_freq_mhz("Not connected.") is None


def test_each_impairment_is_recognised_and_a_clean_second_is_clean():
    assert N.impaired_reasons(rec(1.0)) == []
    labels = lambda **kw: {lab for lab, _ in N.impaired_reasons(rec(1.0, **kw))}
    assert labels(rtt={"p": {"n": 10, "lost": 2, "p50_ms": 3, "p99_ms": 6, "max_ms": 6}}) == {"probe lost"}
    assert labels(rtt={"p": {"n": 10, "lost": 0, "p50_ms": 3, "p99_ms": 6, "max_ms": 450}}) == {"probe slow"}
    assert labels(d_tx_retries=40.0) == {"tx retries"}
    assert labels(d_tx_packets=5.0, d_tx_retries=5.0) == set()                       # too few packets to judge a retry ratio
    assert labels(d_tcp_retrans=5) == {"TCP retransmits"} and labels(d_tcp_retrans=2) == set()
    assert labels(d_beacon_loss=1.0) == {"beacon loss"} and labels(signal_dbm=-80.0) == {"low signal"}


def test_episodes_merge_nearby_impaired_seconds_and_summary_counts_them():
    recs = [rec(t) for t in range(100, 130)]
    for t in (105, 106, 108):                                                         # 105-108 (a clean second between) is one episode
        recs[t - 100] = rec(t, d_tcp_retrans=9)
    recs[20] = rec(120, rtt={"edge-2": {"n": 10, "lost": 3, "p50_ms": 3, "p99_ms": 6, "max_ms": 6}})
    eps = N.episodes(recs)
    assert [(e["t0"], e["t1"], e["seconds"]) for e in eps] == [(105, 108, 3), (120, 120, 1)]
    assert eps[0]["reasons"] == ["TCP retransmits"] and eps[1]["reasons"] == ["probe lost"]
    s = N.summary(recs)
    assert s["seconds"] == 30 and s["impaired_seconds"] == 4 and s["episodes"] == 2 and s["signal_dbm_min_p50"] == (-40.0, -40.0)


def test_correlation_tells_which_slow_transfers_fall_inside_an_episode(tmp_path):
    eps = {"edge-1": [{"t0": 100.0, "t1": 104.0, "seconds": 5, "reasons": ["probe slow"]}], "edge-2": []}
    slow = [{"t_start": 101.0, "net_s": 1.2, "host": "edge-1"},                      # inside the sender's episode
            {"t_start": 103.0, "net_s": 1.0, "host": "edge-2"},                      # the sender's monitor saw nothing, another laptop's did
            {"t_start": 300.0, "net_s": 2.0, "host": "edge-2"}]                      # nothing anywhere: a stall the monitors did not see
    c = N.correlate(slow, eps)
    assert c == {"slow_transfers": 3, "inside_sender_episode": 1, "inside_any_episode": 2}
    log = tmp_path / "agent.jsonl"
    log.write_text("\n".join(json.dumps(r) for r in [{"kind": "transfer_done", "local": False, "net_s": 0.9, "t_start": 5.0},
                                                      {"kind": "transfer_done", "local": True, "net_s": 3.0, "t_start": 6.0},
                                                      {"kind": "transfer_done", "local": False, "net_s": 0.01, "t_start": 7.0}, {"kind": "task_done"}]) + "\nnot json\n")
    assert N.slow_transfers_from_agent_log(log, "edge-3") == [{"t_start": 5.0, "net_s": 0.9, "host": "edge-3"}]


def test_monitor_writes_one_record_per_second_with_probe_statistics(tmp_path):
    log = tmp_path / "m.jsonl"
    peer = N.Monitor({}, tmp_path / "peer.jsonl", iface=None, echo_port=0, bind="127.0.0.1")        # a second monitor, used only as echo responder
    threading.Thread(target=peer._echo_loop, daemon=True).start()
    dead = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dead.bind(("127.0.0.1", 0))
    dead_port = dead.getsockname()[1]
    dead.close()                                                                       # nothing listens there: probes are lost
    mon = N.Monitor({"good": ("127.0.0.1", peer.echo_port), "dead": ("127.0.0.1", dead_port)}, log, iface=None, echo_port=0, bind="127.0.0.1", probe_timeout=0.2)
    t = threading.Thread(target=mon.run)
    t.start()
    time.sleep(3.4)
    mon.stop()
    peer.stop()
    t.join(5)
    recs = N.load_records(log)
    assert 2 <= len(recs) <= 4 and all(r["host"] == socket.gethostname() for r in recs)
    good = [r["rtt"]["good"] for r in recs[1:]]
    assert all(g["n"] >= 5 and g["lost"] == 0 and g["max_ms"] < 50 for g in good)    # about 10 probes per second, all answered
    assert all(r["rtt"]["dead"]["lost"] >= 1 for r in recs[1:])                       # and the dead peer shows as lost
    assert any(lab == "probe lost" for lab, _ in N.impaired_reasons(recs[-1]))
    assert all(r["d_tcp_retrans"] is not None and r["load1"] >= 0 for r in recs)


def test_fleet_monitor_commands_probe_the_other_laptops_and_are_valid_bash():
    laps = [{"name": "edge-1", "ssh": "10.0.0.1", "wifi_ip": "10.0.0.1"}, {"name": "edge-2", "ssh": "10.0.0.2", "wifi_ip": "10.0.0.22"},
            {"name": "edge-3", "ssh": "10.0.0.3"}]
    cmd = fl.monitor_start_cmd(laps[1], laps)
    assert "--peer edge-1=10.0.0.1" in cmd and "--peer edge-3=10.0.0.3" in cmd and "edge-2=" not in cmd          # not itself; wifi_ip preferred, ssh as fallback
    for sc in (cmd, fl.MONITOR_STOP, fl.MONITOR_LAST):
        assert subprocess.run(["bash", "-n"], input=sc, text=True).returncode == 0


def test_only_transfers_inside_the_monitored_time_span_are_counted():
    tr = [{"t_start": 50.0, "net_s": 1.0, "host": "a"}, {"t_start": 150.0, "net_s": 1.0, "host": "a"}, {"t_start": 400.0, "net_s": 1.0, "host": "a"}]
    assert [t["t_start"] for t in N.within_span(tr, [100.0, 300.0])] == [150.0]


def test_impaired_seconds_are_counted_per_run_and_shared_ones_are_found(tmp_path):
    bad = lambda t: rec(t, d_tcp_retrans=9)
    a = [rec(t) for t in range(100, 110)] + [rec(t) for t in range(110, 120)]
    b = list(a)
    for t in (102, 103):
        a[t - 100], b[t - 100] = bad(t), bad(t)                     # run 1: both laptops impaired at the same two seconds
    b[15] = bad(115)                                                # run 2: only one laptop, one second
    rows = N.impaired_per_run({"a": a, "b": b}, [100.0, 110.0])
    assert rows == [{"run": 1, "seconds": 10, "impaired": {"a": 2, "b": 2}, "shared_3plus": 0},
                    {"run": 2, "seconds": 10, "impaired": {"a": 0, "b": 1}, "shared_3plus": 0}]
    c = list(a)
    rows3 = N.impaired_per_run({"a": a, "b": b, "c": c}, [100.0])
    assert rows3[0]["shared_3plus"] == 2                           # seconds 102 and 103: all three laptops impaired
    log = tmp_path / "agent.jsonl"
    log.write_text(json.dumps({"kind": "configured", "t": 5.0}) + "\n" + json.dumps({"kind": "task_done"}) + "\n" + json.dumps({"kind": "configured", "t": 9.0}) + "\n")
    assert N.run_starts_from_agent_log(log) == [5.0, 9.0]
