#!/usr/bin/env python3
"""Preflight for the multi-laptop testbed (testbed/DESIGN.md, phase 1).

CHECK-ONLY: this script reads system state and prints it; it never changes a system setting. The commands that change
settings are listed in testbed/SETUP.md, for the person at the keyboard to run. Standard library only, so it runs before the
virtualenv exists.

  python testbed/preflight.py report  [--role agent|coordinator] [--measured] [--out FILE]
        collect this machine's state, check it against the targets, exit 1 on any FAIL
  python testbed/preflight.py compare REPORT.json REPORT.json ...
        every report must equal the first on the fields that must match (kernel, OS, Python, packages, commit, ...)
  python testbed/preflight.py netserver [--port 5201]
        answer probes (run on every machine before probing)
  python testbed/preflight.py netprobe --peers HOST[:PORT],HOST[:PORT] [--out FILE]
        round-trip time, clock offset and TCP throughput to each peer

--measured makes the settings for measured runs mandatory (text boot target, governor, no swap, updates off, AC power,
Wi-Fi power save off, chrony synchronised). Without it they are reported as WARN so a machine can be checked while it is
still being set up.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import socket
import statistics
import struct
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQUIREMENTS = Path(__file__).resolve().parent / "requirements.txt"
DATA_DIRS = ("input/data", "data", "library")          # needed by the coordinator only (it builds the scenario)
CHRONY_MAX_OFFSET_S = 0.005
DEFAULT_PORT = 5201


# ------------------------------------------------------------------------------------------------ helpers
def sh(*cmd, any_rc=False, timeout=8):
    """stdout of a command, or None if it is missing, times out or (unless any_rc) fails."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if p.returncode != 0 and not any_rc:
        return None
    return p.stdout.strip()


def read(path):
    try:
        return Path(path).read_text().strip()
    except OSError:
        return None


def norm(name):
    return re.sub(r"[-_.]+", "-", name).lower()


# ------------------------------------------------------------------------------------------------ parsers (unit-tested)
def parse_chrony_tracking(text):
    """-> {'offset_s': signed seconds (+ = local clock fast), 'stratum': int, 'leap': str} or None."""
    if not text:
        return None
    out = {}
    m = re.search(r"System time\s*:\s*([0-9.eE+-]+) seconds (fast|slow)", text)
    if m:
        out["offset_s"] = float(m.group(1)) * (1 if m.group(2) == "fast" else -1)
    m = re.search(r"Stratum\s*:\s*(\d+)", text)
    if m:
        out["stratum"] = int(m.group(1))
    m = re.search(r"Leap status\s*:\s*(.+)", text)
    if m:
        out["leap"] = m.group(1).strip()
    return out or None


def parse_periodic(text):
    """/etc/apt/apt.conf.d/20auto-upgrades -> {'Update-Package-Lists': '1', 'Unattended-Upgrade': '1', ...}"""
    return dict(re.findall(r'APT::Periodic::([A-Za-z-]+)\s+"(\d+)"', text or ""))


def parse_swaps(text):
    lines = (text or "").splitlines()[1:]
    return [ln.split()[0] for ln in lines if ln.strip()]


def pinned_requirements(path=REQUIREMENTS):
    pins = {}
    for ln in read(path).splitlines() if read(path) else []:
        ln = ln.split("#")[0].strip()
        if "==" in ln and not ln.startswith("-"):
            n, v = ln.split("==", 1)
            pins[norm(n)] = v.strip()
    return pins


def tree_manifest(root):
    """(file_count, total_bytes, blake2b over sorted relative path + size) of a directory; None if absent."""
    root = Path(root)
    if not root.is_dir():
        return None
    h, n, tot = hashlib.blake2b(digest_size=16), 0, 0
    for p in sorted(root.rglob("*")):
        if p.is_file():
            sz = p.stat().st_size
            h.update(f"{p.relative_to(root).as_posix()}\0{sz}\n".encode())
            n, tot = n + 1, tot + sz
    return {"files": n, "bytes": tot, "hash": h.hexdigest()}


# ------------------------------------------------------------------------------------------------ collection
def collect_cpu():
    info = read("/proc/cpuinfo") or ""
    m = re.search(r"model name\s*:\s*(.+)", info)
    govs = []
    for p in sorted(Path("/sys/devices/system/cpu").glob("cpu[0-9]*/cpufreq/scaling_governor")):
        govs.append(read(p))
    return {"model": m.group(1).strip() if m else platform.processor(), "logical": os.cpu_count(),
            "governors": sorted(set(g for g in govs if g)) or None,
            "driver": read("/sys/devices/system/cpu/cpu0/cpufreq/scaling_driver"),
            "no_turbo": read("/sys/devices/system/cpu/intel_pstate/no_turbo")}


def collect_mem():
    mi = read("/proc/meminfo") or ""
    kb = lambda key: int(re.search(rf"{key}:\s*(\d+) kB", mi).group(1)) if re.search(rf"{key}:", mi) else None
    swaps = parse_swaps(read("/proc/swaps"))
    return {"total_mb": (kb("MemTotal") or 0) // 1024, "swap_total_mb": (kb("SwapTotal") or 0) // 1024, "swaps": swaps}


def collect_time():
    chrony = parse_chrony_tracking(sh("chronyc", "tracking"))
    ts = sh("timedatectl", "show", "-p", "NTPSynchronized", "-p", "NTP", any_rc=True) or ""
    return {"chrony": chrony, "chrony_installed": sh("which", "chronyc") is not None,
            "timedatectl": dict(ln.split("=", 1) for ln in ts.splitlines() if "=" in ln)}


def collect_updates():
    timers = {t: sh("systemctl", "is-enabled", t, any_rc=True) for t in ("apt-daily.timer", "apt-daily-upgrade.timer")}
    snap = sh("snap", "refresh", "--time", any_rc=True)
    return {"apt_timers": timers, "periodic": parse_periodic(read("/etc/apt/apt.conf.d/20auto-upgrades")),
            "unattended_installed": "install ok installed" in (sh("dpkg-query", "-W", "-f=${Status}", "unattended-upgrades", any_rc=True) or ""),
            "snap_refresh_held": ("hold:" in snap) if snap is not None else None,
            "apt_held": sorted((sh("apt-mark", "showhold") or "").split())}


def collect_power():
    ac, bat = None, None
    for d in sorted(Path("/sys/class/power_supply").glob("*")):
        t = read(d / "type")
        if t == "Mains":
            ac = read(d / "online") == "1"
        elif t == "Battery":
            bat = read(d / "status")
    return {"ac_online": ac, "battery_status": bat}


def collect_wifi():
    out = {"interface": None}
    for ln in (sh("nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device") or "").splitlines():
        dev, typ, state = (ln.split(":") + ["", "", ""])[:3]
        if typ == "wifi" and state.startswith("connected"):
            out["interface"] = dev
    if out["interface"]:
        for ln in (sh("nmcli", "-t", "-f", "IN-USE,SSID,CHAN,RATE,SIGNAL", "device", "wifi", any_rc=True) or "").splitlines():
            if ln.startswith("*"):
                f = ln.split(":")
                out.update(ssid=f[1], channel=f[2], rate=f[3], signal=f[4])
        ps = sh("iw", "dev", out["interface"], "get", "power_save", any_rc=True)
        out["power_save"] = ps.split(":")[-1].strip() if ps and "Power save" in ps else None
    return out


def collect_python():
    import importlib.metadata as md
    pins = pinned_requirements()
    pk = {}
    for n in pins:
        try:
            pk[n] = md.version(n)
        except md.PackageNotFoundError:
            pk[n] = None
    numba_ok = None
    try:
        import numba
        numba_ok = bool(numba.njit(lambda x: x + 1)(1) == 2)
    except Exception as e:                                          # noqa: BLE001 - report, don't crash
        numba_ok = f"error: {type(e).__name__}"
    return {"version": platform.python_version(), "executable": sys.executable, "venv": sys.prefix != sys.base_prefix,
            "packages": pk, "numba_jit_works": numba_ok}


def collect_repo():
    git = lambda *a: sh("git", "-C", str(ROOT), *a)
    return {"head": git("rev-parse", "HEAD"), "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
            "dirty_tracked": bool(git("status", "--porcelain", "--untracked-files=no"))}


def collect(role="agent"):
    du = os.statvfs(ROOT)
    rep = {"role": role, "hostname": socket.gethostname(), "time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "os": {"pretty": (re.search(r'PRETTY_NAME="(.+)"', read("/etc/os-release") or "") or [None, None])[1]},
           "kernel": {"release": platform.release(), "running_pinned_by_hold": None},
           "cpu": collect_cpu(), "mem": collect_mem(), "time": collect_time(), "boot": {"default_target": sh("systemctl", "get-default")},
           "updates": collect_updates(), "power": collect_power(), "wifi": collect_wifi(), "python": collect_python(),
           "repo": collect_repo(), "loadavg_1m": os.getloadavg()[0], "disk_free_gb": round(du.f_bavail * du.f_frsize / 2**30, 1)}
    held = rep["updates"]["apt_held"]
    rep["kernel"]["running_pinned_by_hold"] = any(h.startswith("linux-image") or h == "linux-generic" for h in held)
    if role == "coordinator":
        rep["data"] = {d: tree_manifest(ROOT / d) for d in DATA_DIRS}
    return rep


# ------------------------------------------------------------------------------------------------ checks
PASS, WARN, FAIL, INFO = "PASS", "WARN", "FAIL", "INFO"


def evaluate(rep, measured=False):
    """List of (name, status, detail). Settings for measured runs are FAIL under --measured, WARN otherwise."""
    soft = FAIL if measured else WARN
    out = []
    add = lambda n, ok, d, bad=FAIL: out.append((n, PASS if ok else bad, d))

    govs = rep["cpu"]["governors"]
    add("cpu governor = performance", govs == ["performance"], f"{govs}", soft)
    add("swap off", rep["mem"]["swap_total_mb"] == 0, f"{rep['mem']['swap_total_mb']} MB {rep['mem']['swaps']}", soft)
    tm = rep["time"]
    ch = tm["chrony"]
    if ch and "offset_s" in ch:
        add("chrony synchronised", ch.get("leap") == "Normal" and abs(ch["offset_s"]) < CHRONY_MAX_OFFSET_S,
            f"offset {ch['offset_s'] * 1e3:+.3f} ms, stratum {ch.get('stratum')}, leap {ch.get('leap')}", soft)
    else:
        add("chrony synchronised", False, "chronyc not installed or not running"
            f" (systemd-timesyncd synchronised: {tm['timedatectl'].get('NTPSynchronized')})", soft)
    add("boot target = multi-user (text)", rep["boot"]["default_target"] == "multi-user.target", f"{rep['boot']['default_target']}", soft)
    u = rep["updates"]
    timers_off = all(v in ("disabled", "masked") for v in u["apt_timers"].values())
    periodic_off = u["periodic"].get("Update-Package-Lists", "0") == "0" and u["periodic"].get("Unattended-Upgrade", "0") == "0"
    add("apt auto-update off", timers_off and periodic_off, f"timers {u['apt_timers']}, periodic {u['periodic'] or 'not set'}", soft)
    add("snap auto-refresh held", u["snap_refresh_held"] in (True, None), f"{u['snap_refresh_held']} (None = no snap)", soft)
    add("kernel pinned (apt-mark hold)", rep["kernel"]["running_pinned_by_hold"], f"running {rep['kernel']['release']}, held {u['apt_held']}", soft)
    pw = rep["power"]
    add("on AC power", pw["ac_online"] is True or (pw["ac_online"] is None and pw["battery_status"] is None), f"{pw}", soft)
    wf = rep["wifi"]
    if wf["interface"]:
        add("Wi-Fi power save off", wf.get("power_save") == "off", f"{wf.get('power_save')} (None = 'iw' not installed)", soft)
        out.append(("Wi-Fi link", INFO, f"{wf.get('ssid')} ch {wf.get('channel')} {wf.get('rate')} signal {wf.get('signal')}"))
    # always required
    py = rep["python"]
    pins = pinned_requirements()
    bad = {n: (v, pins[n]) for n, v in py["packages"].items() if v != pins.get(n)}
    add("packages == testbed/requirements.txt", not bad, f"mismatch (installed, pinned): {bad}" if bad else f"{len(pins)} pinned packages match")
    add("running inside a venv", py["venv"], py["executable"])
    add("numba compiles a function", py["numba_jit_works"] is True, f"{py['numba_jit_works']}")
    add("repo: tracked files unmodified", not rep["repo"]["dirty_tracked"], f"HEAD {str(rep['repo']['head'])[:7]} on {rep['repo']['branch']}")
    add("load average (1 min) < 0.5", rep["loadavg_1m"] < 0.5, f"{rep['loadavg_1m']:.2f}", WARN)
    add("free disk >= 5 GB", rep["disk_free_gb"] >= 5, f"{rep['disk_free_gb']} GB")
    if rep["role"] == "coordinator":
        for d, m in rep["data"].items():
            add(f"data present: {d}", m is not None and m["files"] > 0, f"{m['files']} files, {m['bytes'] / 2**30:.2f} GB" if m else "missing")
    out.append(("hardware", INFO, f"{rep['cpu']['model']}, {rep['cpu']['logical']} threads, {rep['mem']['total_mb']} MB RAM"))
    return out


# fields that must be identical on every machine (dotted paths); hardware is reported, not required to match
MUST_MATCH = ["os.pretty", "kernel.release", "python.version", "python.packages", "repo.head", "boot.default_target",
              "cpu.governors", "kernel.running_pinned_by_hold", "updates.periodic"]
# (the exact list of held kernel packages is not compared: a laptop with an older kernel installed holds more packages)
REPORT_ONLY = ["cpu.model", "cpu.logical", "mem.total_mb"]


def dig(d, path):
    for k in path.split("."):
        d = d.get(k) if isinstance(d, dict) else None
    return d


def compare(reports):
    """-> list of (field, status, detail) comparing every report with the first; data manifests among coordinators."""
    ref, out = reports[0], []
    for f in MUST_MATCH:
        vals = {r["hostname"]: dig(r, f) for r in reports}
        same = all(v == dig(ref, f) for v in vals.values())
        out.append((f, PASS if same else FAIL, "identical" if same else json.dumps(vals, default=str)))
    for f in REPORT_ONLY:
        out.append((f, INFO, json.dumps({r["hostname"]: dig(r, f) for r in reports})))
    coord = [r for r in reports if r.get("data")]
    if len(coord) > 1:
        same = all(r["data"] == coord[0]["data"] for r in coord)
        out.append(("data manifests", PASS if same else FAIL, "identical" if same else "differ between coordinators"))
    offs = {r["hostname"]: (dig(r, "time.chrony") or {}).get("offset_s") for r in reports}
    known = [abs(v) for v in offs.values() if v is not None]
    out.append(("chrony offsets (ms)", INFO if known else WARN, json.dumps({h: (None if v is None else round(v * 1e3, 3)) for h, v in offs.items()})))
    return out


def show(rows, title):
    print(f"\n== {title}")
    w = max(len(r[0]) for r in rows)
    for n, s, d in rows:
        print(f"  [{s:4}] {n:<{w}}  {d}")


# ------------------------------------------------------------------------------------------------ network and clock probe
def _recvn(sock, n):
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(min(1 << 20, n - len(buf)))
        if not chunk:
            raise ConnectionError("peer closed")
        buf += chunk
    return bytes(buf)


def _handle(conn):
    conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    try:
        while True:
            cmd = conn.recv(1)
            if not cmd:
                return
            if cmd == b"T":                                        # time exchange: reply with (receive time, send time)
                t1 = time.time()
                conn.sendall(struct.pack("!dd", t1, time.time()))
            elif cmd == b"U":                                      # sink n bytes, then acknowledge
                n = struct.unpack("!Q", _recvn(conn, 8))[0]
                _recvn(conn, n)
                conn.sendall(b"k")
            elif cmd == b"D":                                      # source n bytes
                n = struct.unpack("!Q", _recvn(conn, 8))[0]
                conn.sendall(b"\0" * n)
            else:
                return
    except (ConnectionError, OSError):
        pass
    finally:
        conn.close()


def serve(port=DEFAULT_PORT, host="0.0.0.0", ready=None):
    """Blocking probe server. ready(port) is called once listening (port 0 = pick a free one; used by tests)."""
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
    srv.listen(8)
    if ready:
        ready(srv.getsockname()[1])
    while True:
        conn, _ = srv.accept()
        threading.Thread(target=_handle, args=(conn,), daemon=True).start()


def probe(host, port=DEFAULT_PORT, pings=200, mb=8, rounds=3, connect_timeout=30):
    s = socket.create_connection((host, port), timeout=connect_timeout)
    s.settimeout(60)
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    samples = []                                                   # (delay, offset): NTP-style four-timestamp exchange
    for _ in range(pings):
        t0 = time.time()
        s.sendall(b"T")
        t1, t2 = struct.unpack("!dd", _recvn(s, 16))
        t3 = time.time()
        samples.append(((t3 - t0) - (t2 - t1), ((t1 - t0) + (t2 - t3)) / 2))
        time.sleep(0.005)
    delays = sorted(d for d, _ in samples)
    best = sorted(samples)[: max(1, pings // 10)]                  # offset from the 10% lowest-delay samples
    n, up, down = mb * 2**20, [], []
    for _ in range(rounds):
        t = time.perf_counter()
        s.sendall(b"U" + struct.pack("!Q", n) + b"\0" * n)
        _recvn(s, 1)
        up.append(mb / (time.perf_counter() - t))
        t = time.perf_counter()
        s.sendall(b"D" + struct.pack("!Q", n))
        _recvn(s, n)
        down.append(mb / (time.perf_counter() - t))
    s.close()
    q = lambda p: delays[min(len(delays) - 1, int(p * len(delays)))] * 1e3
    return {"peer": f"{host}:{port}", "rtt_ms": {"min": round(delays[0] * 1e3, 3), "median": round(q(0.5), 3), "p95": round(q(0.95), 3),
                                                 "p99": round(q(0.99), 3), "max": round(delays[-1] * 1e3, 3)},
            "clock_offset_ms_peer_minus_local": round(statistics.median(o for _, o in best) * 1e3, 3),
            "up_MBps": round(statistics.median(up), 2), "down_MBps": round(statistics.median(down), 2),
            "up_MBps_all": [round(x, 2) for x in up], "down_MBps_all": [round(x, 2) for x in down], "payload_MB": mb}


# ------------------------------------------------------------------------------------------------ command line
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("report")
    r.add_argument("--role", choices=("agent", "coordinator"), default="agent")
    r.add_argument("--measured", action="store_true")
    r.add_argument("--out")
    c = sub.add_parser("compare")
    c.add_argument("reports", nargs="+")
    s = sub.add_parser("netserver")
    s.add_argument("--port", type=int, default=DEFAULT_PORT)
    p = sub.add_parser("netprobe")
    p.add_argument("--peers", required=True)
    p.add_argument("--mb", type=int, default=8)
    p.add_argument("--out")
    a = ap.parse_args(argv)

    if a.cmd == "report":
        rep = collect(a.role)
        rows = evaluate(rep, a.measured)
        rep["checks"] = [{"name": n, "status": s_, "detail": d} for n, s_, d in rows]
        if a.out:
            Path(a.out).write_text(json.dumps(rep, indent=1, default=str))
        show(rows, f"{rep['hostname']} ({a.role}{', measured' if a.measured else ''})")
        n_fail = sum(1 for _, s_, _ in rows if s_ == FAIL)
        n_warn = sum(1 for _, s_, _ in rows if s_ == WARN)
        print(f"\n{n_fail} FAIL, {n_warn} WARN" + (f"; report written to {a.out}" if a.out else ""))
        return 1 if n_fail else 0
    if a.cmd == "compare":
        reps = [json.loads(Path(f).read_text()) for f in a.reports]
        rows = compare(reps)
        show(rows, "comparison against " + reps[0]["hostname"])
        return 1 if any(s_ == FAIL for _, s_, _ in rows) else 0
    if a.cmd == "netserver":
        print(f"probe server on port {a.port}; Ctrl-C to stop", flush=True)
        serve(a.port)
    if a.cmd == "netprobe":
        res = []
        for peer in a.peers.split(","):
            host, _, port = peer.partition(":")
            res.append(probe(host, int(port or DEFAULT_PORT), mb=a.mb))
            x = res[-1]
            print(f"{x['peer']:<24} rtt min/med/p99 {x['rtt_ms']['min']}/{x['rtt_ms']['median']}/{x['rtt_ms']['p99']} ms  "
                  f"clock offset {x['clock_offset_ms_peer_minus_local']:+} ms  up {x['up_MBps']} MB/s  down {x['down_MBps']} MB/s")
        if a.out:
            Path(a.out).write_text(json.dumps({"from": socket.gethostname(), "time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                               "probes": res}, indent=1))
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
