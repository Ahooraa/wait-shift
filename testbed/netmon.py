#!/usr/bin/env python3
"""Network monitor for the testbed laptops (testbed/DESIGN.md, calibration; DEV-T7).

Wi-Fi stall episodes (agent-to-agent transfers of 0.5 to 3.7 s for a stretch of time, independent of the load) made single runs unreliable,
and their cause is unknown. This monitor runs on every laptop next to the agents and records, once per second, what the network was doing:

  * Wi-Fi link state from `iw dev <iface> station dump`: signal, bit rates, and the change since the last second of tx retries, tx failures,
    beacon losses and dropped frames (the kernel's counters are cumulative);
  * the change in TCP retransmitted segments (/proc/net/snmp) and in interface packet counters, and the load average;
  * a UDP round-trip probe from every laptop to every other, 10 per second, independent of the agents and of the hub: if the probe is
    clean while the agents' transfers stall, the cause is in our software; if the probe stalls too, it is the network.

One JSON line per second goes to ~/testbed-logs/netmon-<time>.jsonl on the laptop. Peers are named by laptop name, not address, so the
log holds no addresses. `analyze` merges the logs of all laptops, finds impaired seconds and merges them into episodes, and (given the
agents' logs) tells how many slow transfers fall inside an episode. Standard library only (the Wi-Fi fields need `iw`).

  python testbed/netmon.py run --peer edge-2=ADDRESS --peer edge-3=ADDRESS [--iface wlo1] [--out DIR]     (fleet.py monitor start does this)
  python testbed/netmon.py analyze --monitor LOG [LOG ...] [--agent AGENT_LOG [...]]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import signal
import socket
import sys
import threading
import time
from pathlib import Path

ECHO_PORT = 5301
RTT_IMPAIRED_MS = 100.0               # a probe round trip above this marks the second as impaired
RETRY_RATIO_IMPAIRED = 0.25           # tx retries per tx packet above this (with at least 20 packets)
TCP_RETRANS_IMPAIRED = 3              # retransmitted TCP segments in one second
SIGNAL_IMPAIRED_DBM = -75


# ------------------------------------------------------------------------------------------------ parsers (unit-tested)
def wifi_iface():
    for n in sorted(os.listdir("/sys/class/net")):
        if os.path.isdir(f"/sys/class/net/{n}/wireless"):
            return n
    return None


def parse_station_dump(text):
    """The fields of `iw dev X station dump` that matter; the counters are cumulative. {} if not associated."""
    out = {}
    num = lambda m: float(m.group(1)) if m else None
    pats = {"signal_dbm": r"\n\s*signal:\s*(-?\d+)", "signal_avg_dbm": r"signal avg:\s*(-?\d+)", "tx_bitrate_mbps": r"tx bitrate:\s*([\d.]+)",
            "rx_bitrate_mbps": r"rx bitrate:\s*([\d.]+)", "tx_retries": r"tx retries:\s*(\d+)", "tx_failed": r"tx failed:\s*(\d+)",
            "beacon_loss": r"beacon loss:\s*(\d+)", "rx_drop_misc": r"rx drop misc:\s*(\d+)", "tx_packets": r"tx packets:\s*(\d+)",
            "rx_packets": r"rx packets:\s*(\d+)", "inactive_ms": r"inactive time:\s*(\d+)"}
    for k, p in pats.items():
        v = num(re.search(p, "\n" + text))
        if v is not None:
            out[k] = v
    return out


def parse_tcp_snmp(text):
    lines = [ln for ln in text.splitlines() if ln.startswith("Tcp:")]
    if len(lines) < 2:
        return {}
    return dict(zip(lines[0].split()[1:], (int(x) for x in lines[1].split()[1:])))


def parse_freq_mhz(text):
    m = re.search(r"freq:\s*([\d.]+)", text)
    return float(m.group(1)) if m else None


def read(path):
    try:
        return Path(path).read_text()
    except OSError:
        return ""


def run_text(*cmd, timeout=3):
    import subprocess
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.stdout if p.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


# ------------------------------------------------------------------------------------------------ the monitor
def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(p * len(xs)))] if xs else None


class Monitor:
    def __init__(self, peers, out_path, iface=None, interval=1.0, probe_hz=10.0, echo_port=ECHO_PORT, bind="0.0.0.0", probe_timeout=0.5):
        self.peers = dict(peers)                 # name -> (host, port) the peer's echo responder
        self.out_path, self.iface = Path(out_path), iface if iface is not None else wifi_iface()
        self.interval, self.probe_gap, self.probe_timeout = interval, 1.0 / probe_hz, probe_timeout
        self.stop_event = threading.Event()
        self.lock, self.rtts = threading.Lock(), {n: [] for n in self.peers}      # per peer: round trips in ms, None for a lost probe
        self.echo = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.echo.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.echo.bind((bind, echo_port))
        self.echo_port = self.echo.getsockname()[1]
        self.threads = []
        self.host = socket.gethostname()

    # -- the responder and the probes
    def _echo_loop(self):
        self.echo.settimeout(0.5)
        while not self.stop_event.is_set():
            try:
                data, addr = self.echo.recvfrom(256)
                self.echo.sendto(data, addr)
            except (socket.timeout, OSError):
                continue

    def _probe_loop(self, name, addr):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(self.probe_timeout)
        seq = 0
        while not self.stop_event.is_set():
            seq += 1
            t0 = time.perf_counter()
            try:
                s.sendto(b"%d" % seq, addr)
                while True:                                           # skip late replies of earlier probes
                    data, _ = s.recvfrom(256)
                    if data == b"%d" % seq:
                        rtt = (time.perf_counter() - t0) * 1e3
                        break
            except socket.timeout:
                rtt = None
            except OSError:
                rtt = None
            with self.lock:
                self.rtts[name].append(rtt)
            self.stop_event.wait(max(0.0, self.probe_gap - (time.perf_counter() - t0)))

    # -- the sampler
    def _snapshot(self):
        snap = {"station": parse_station_dump(run_text("iw", "dev", self.iface, "station", "dump")) if self.iface else {},
                "tcp": parse_tcp_snmp(read("/proc/net/snmp"))}
        return snap

    def _record(self, prev, cur, t, extra_freq):
        d = lambda sec, k: (cur[sec].get(k) - prev[sec].get(k)) if k in cur[sec] and k in prev[sec] else None
        st = cur["station"]
        with self.lock:
            rtts, self.rtts = self.rtts, {n: [] for n in self.peers}
        probes = {}
        for n, xs in rtts.items():
            ok = [x for x in xs if x is not None]
            probes[n] = {"n": len(xs), "lost": len(xs) - len(ok), "p50_ms": pct(ok, .5), "p99_ms": pct(ok, .99), "max_ms": max(ok) if ok else None}
        return {"t": t, "host": self.host, "freq_mhz": extra_freq, "signal_dbm": st.get("signal_dbm"), "tx_bitrate_mbps": st.get("tx_bitrate_mbps"),
                "rx_bitrate_mbps": st.get("rx_bitrate_mbps"), "d_tx_retries": d("station", "tx_retries"), "d_tx_failed": d("station", "tx_failed"),
                "d_tx_packets": d("station", "tx_packets"), "d_beacon_loss": d("station", "beacon_loss"), "d_rx_drop": d("station", "rx_drop_misc"),
                "d_tcp_retrans": d("tcp", "RetransSegs"), "d_tcp_out": d("tcp", "OutSegs"), "load1": os.getloadavg()[0], "rtt": probes}

    def run(self):
        self.out_path.parent.mkdir(parents=True, exist_ok=True)
        self.threads = [threading.Thread(target=self._echo_loop, daemon=True)] + \
                       [threading.Thread(target=self._probe_loop, args=(n, a), daemon=True) for n, a in self.peers.items()]
        for t in self.threads:
            t.start()
        freq = parse_freq_mhz(run_text("iw", "dev", self.iface, "link")) if self.iface else None
        prev, n = self._snapshot(), 0
        with open(self.out_path, "a", buffering=1) as f:
            while not self.stop_event.wait(self.interval - (time.time() % self.interval) if self.interval >= 1 else self.interval):
                cur = self._snapshot()
                f.write(json.dumps(self._record(prev, cur, time.time(), freq), separators=(",", ":")) + "\n")
                prev, n = cur, n + 1
                if n % 60 == 0:
                    freq = parse_freq_mhz(run_text("iw", "dev", self.iface, "link")) if self.iface else freq
        return n

    def stop(self):
        self.stop_event.set()


# ------------------------------------------------------------------------------------------------ analysis (unit-tested)
def load_records(path):
    out = []
    for ln in Path(path).read_text().splitlines():
        try:
            out.append(json.loads(ln))
        except ValueError:
            continue
    return out


def impaired_reasons(r):
    """Why this second counts as impaired: a list of (label, detail); empty = clean."""
    why = []
    for peer, p in (r.get("rtt") or {}).items():
        if p.get("lost"):
            why.append(("probe lost", f"{p['lost']} to {peer}"))
        if p.get("max_ms") is not None and p["max_ms"] > RTT_IMPAIRED_MS:
            why.append(("probe slow", f"{p['max_ms']:.0f} ms to {peer}"))
    pk, rt = r.get("d_tx_packets"), r.get("d_tx_retries")
    if pk is not None and rt is not None and pk >= 20 and rt / pk > RETRY_RATIO_IMPAIRED:
        why.append(("tx retries", f"{rt / pk:.0%}"))
    if (r.get("d_tcp_retrans") or 0) >= TCP_RETRANS_IMPAIRED:
        why.append(("TCP retransmits", str(int(r["d_tcp_retrans"]))))
    if (r.get("d_beacon_loss") or 0) > 0:
        why.append(("beacon loss", str(int(r["d_beacon_loss"]))))
    if r.get("signal_dbm") is not None and r["signal_dbm"] < SIGNAL_IMPAIRED_DBM:
        why.append(("low signal", f"{r['signal_dbm']:.0f} dBm"))
    return why


def recent_impairment(path, seconds=60, now=None, max_age_s=15.0):
    """Share of the last `seconds` of a monitor log that were impaired: {'seconds', 'impaired', 'fraction', 'age_s'}, or None when the log is
    missing, empty or stale (the monitor is not running, so nothing can be said about the last minute)."""
    try:
        recs = load_records(path)
    except OSError:
        return None
    if not recs:
        return None
    now = time.time() if now is None else now
    last = max(r["t"] for r in recs)
    if now - last > max_age_s:
        return None
    win = [r for r in recs if now - seconds <= r["t"] <= now]
    if not win:
        return None
    bad = sum(1 for r in win if impaired_reasons(r))
    return {"seconds": len(win), "impaired": bad, "fraction": bad / len(win), "age_s": now - last}


def episodes(records, gap_s=2.0):
    """Impaired seconds merged into episodes: [{'t0', 't1', 'seconds', 'reasons'}]; seconds closer than gap_s belong together."""
    eps = []
    for r in sorted(records, key=lambda x: x["t"]):
        labels = {lab for lab, _ in impaired_reasons(r)}
        if not labels:
            continue
        if eps and r["t"] - eps[-1]["t1"] <= gap_s:
            eps[-1]["t1"], eps[-1]["seconds"] = r["t"], eps[-1]["seconds"] + 1
            eps[-1]["reasons"] |= labels
        else:
            eps.append({"t0": r["t"], "t1": r["t"], "seconds": 1, "reasons": set(labels)})
    for e in eps:
        e["reasons"] = sorted(e["reasons"])
    return eps


def summary(records):
    ok = sorted(records, key=lambda x: x["t"])
    eps = episodes(ok)
    sig = [r["signal_dbm"] for r in ok if r.get("signal_dbm") is not None]
    br = [r["tx_bitrate_mbps"] for r in ok if r.get("tx_bitrate_mbps") is not None]
    rt = [p["p99_ms"] for r in ok for p in (r.get("rtt") or {}).values() if p.get("p99_ms") is not None]
    return {"host": ok[0].get("host") if ok else None, "seconds": len(ok), "impaired_seconds": sum(e["seconds"] for e in eps), "episodes": len(eps),
            "signal_dbm_min_p50": (min(sig), pct(sig, .5)) if sig else None, "tx_bitrate_min_p50_mbps": (min(br), pct(br, .5)) if br else None,
            "probe_rtt_p99_ms_max_p50": (max(rt), pct(rt, .5)) if rt else None, "episode_list": eps}


def correlate(slow_transfers, eps_by_host, margin_s=1.0):
    """slow_transfers: [{'t_start', 'net_s', 'host'}] (host = the sender's laptop). Counts those that overlap an impaired episode of the sender
    (or of any laptop), with margin_s of slack: tells whether the stalls the agents saw coincide with something the monitors saw."""
    own = anyhost = 0
    for tr in slow_transfers:
        a, b = tr["t_start"] - margin_s, tr["t_start"] + tr["net_s"] + margin_s
        hit = lambda eps: any(e["t0"] - margin_s <= b and e["t1"] + margin_s >= a for e in eps)
        own += hit(eps_by_host.get(tr["host"], []))
        anyhost += any(hit(e) for e in eps_by_host.values())
    return {"slow_transfers": len(slow_transfers), "inside_sender_episode": own, "inside_any_episode": anyhost}


def run_starts_from_agent_log(path):
    """Wall-clock start of every LiveSim run: each run begins by configuring the agents, which logs a `configured` event."""
    out = []
    for ln in Path(path).read_text().splitlines():
        try:
            r = json.loads(ln)
        except ValueError:
            continue
        if r.get("kind") == "configured":
            out.append(r["t"])
    return out


def impaired_per_run(records_by_host, run_starts):
    """For each run (from its start to the next run's start): seconds monitored, impaired seconds per laptop, and seconds with 3 or more laptops
    impaired at once (a shared disturbance of the medium rather than one laptop's problem)."""
    imp = {h: {int(r["t"]) for r in rs if impaired_reasons(r)} for h, rs in records_by_host.items()}
    secs = sorted({int(r["t"]) for rs in records_by_host.values() for r in rs})
    bounds = list(run_starts) + [float("inf")]
    rows = []
    for i in range(len(run_starts)):
        win = [t for t in secs if bounds[i] <= t < bounds[i + 1]]
        if win:
            rows.append({"run": i + 1, "seconds": len(win), "impaired": {h: sum(t in imp[h] for t in win) for h in sorted(imp)},
                         "shared_3plus": sum(1 for t in win if sum(t in imp[h] for h in imp) >= 3)})
    return rows


def within_span(transfers, span):
    """The transfers that started inside the time span [t0, t1] covered by the monitors."""
    return [t for t in transfers if span[0] <= t["t_start"] <= span[1]]


def slow_transfers_from_agent_log(path, host, threshold_s=0.5):
    out = []
    for ln in Path(path).read_text().splitlines():
        try:
            r = json.loads(ln)
        except ValueError:
            continue
        if r.get("kind") == "transfer_done" and not r.get("local") and r.get("net_s", 0) > threshold_s:
            out.append({"t_start": r["t_start"], "net_s": r["net_s"], "host": host})
    return out


# ------------------------------------------------------------------------------------------------ command line
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--peer", action="append", default=[], help="NAME=ADDRESS of another laptop (repeatable)")
    r.add_argument("--iface")
    r.add_argument("--out", default=str(Path.home() / "testbed-logs"))
    r.add_argument("--echo-port", type=int, default=ECHO_PORT)
    r.add_argument("--probe-hz", type=float, default=10.0)
    a = sub.add_parser("analyze")
    a.add_argument("--monitor", nargs="+", required=True)
    a.add_argument("--agent", nargs="*", default=[], help="agent logs, one per monitor log in the same order (the sender's laptop)")
    x = ap.parse_args(argv)
    if x.cmd == "run":
        peers = {}
        for p in x.peer:
            name, _, addr = p.partition("=")
            peers[name] = (addr, x.echo_port)
        path = Path(x.out).expanduser() / f"netmon-{time.strftime('%Y%m%d-%H%M%S')}.jsonl"
        mon = Monitor(peers, path, x.iface, probe_hz=x.probe_hz, echo_port=x.echo_port)
        signal.signal(signal.SIGTERM, lambda *_: mon.stop())
        print(f"monitoring {mon.iface}, probing {len(peers)} peer(s), log {path}", flush=True)
        try:
            mon.run()
        except KeyboardInterrupt:
            mon.stop()
        return 0
    eps_by_host, slow, span, recs_by_host = {}, [], [float("inf"), 0.0], {}
    for i, f in enumerate(x.monitor):
        recs = load_records(f)
        if recs:
            recs_by_host[recs[0].get("host")] = recs
        if recs:
            span = [min(span[0], recs[0]["t"]), max(span[1], recs[-1]["t"])]
        s = summary(recs)
        eps_by_host[s["host"]] = s["episode_list"]
        print(f"{s['host']}: {s['seconds']} s, {s['impaired_seconds']} s impaired in {s['episodes']} episode(s); signal min/median {s['signal_dbm_min_p50']}, "
              f"tx bitrate min/median {s['tx_bitrate_min_p50_mbps']}, probe p99 RTT max/median {s['probe_rtt_p99_ms_max_p50']} ms")
        for e in s["episode_list"][:6]:
            print(f"    {time.strftime('%H:%M:%S', time.localtime(e['t0']))}  {e['seconds']:>3} s  {', '.join(e['reasons'])}")
        if i < len(x.agent):
            slow += slow_transfers_from_agent_log(x.agent[i], s["host"])
    if x.agent:
        starts = run_starts_from_agent_log(x.agent[0])
        rows = impaired_per_run(recs_by_host, starts)
        if rows:
            print("impaired seconds per run (a run starts when the agents are configured); 3+ = three or more laptops impaired in the same second:")
            for r in rows:
                print(f"   run {r['run']:>2}: {r['seconds']:>3} s monitored; " + "; ".join(f"{h} {n}" for h, n in r["impaired"].items()) + f"; 3+ laptops {r['shared_3plus']} s")
        covered = within_span(slow, span)                      # only transfers that happened while the monitors were running
        print(f"slow agent transfers (> 0.5 s): {len(slow)} in the agent logs, {len(covered)} while the monitors ran; against monitor episodes:",
              correlate(covered, eps_by_host))
    return 0


if __name__ == "__main__":
    sys.exit(main())
