#!/usr/bin/env python3
"""Connect the testbed laptops to each other automatically (testbed/DESIGN.md, phase 1).

  hub  (on ONE laptop):   ~/venv-dfps/bin/python testbed/connect.py hub [--laptops 4] [--port 8000]
  join (on the others):   run for you by testbed/join.sh; the hub prints the one line to paste.

The hub serves the code to bare laptops (so they need no GitHub login), collects every laptop's preflight report, and then has the
laptops probe each other ONE AT A TIME (so the measurements do not disturb each other): round-trip time, clock offset and TCP
throughput for every pair. At the end it prints a reachability matrix and a verdict, runs the cross-machine comparison and writes
everything to ~/testbed-reports/<time>/.

Standard library only. The hub accepts requests only with the random token it prints, and serves just the code bundle and the
join script; it changes no system setting.
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

try:
    from testbed import preflight as pf
except ImportError:                                    # run as a script: testbed/ is sys.path[0]
    import preflight as pf

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DEFAULT_HTTP_PORT = 8000
MAX_POST = 2 * 2**20


def lan_ip(target="8.8.8.8"):
    """Address of the interface that would be used to reach `target` (a UDP connect sends no packet)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect((target, 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def now():
    return time.strftime("%H:%M:%S")


# ------------------------------------------------------------------------------------------------ hub
class Hub:
    """State of one connection session: who joined, their reports, and the probe matrix. Probing goes in turns."""

    def __init__(self, laptops, token, out_dir, turn_timeout=180.0, files=None, meta=None, log=None):
        self.laptops, self.token, self.out_dir = laptops, token, Path(out_dir)
        self.turn_timeout, self.files, self.meta = turn_timeout, files or {}, meta or {}
        self.log = log or (lambda m: print(f"[{now()}] {m}", flush=True))
        self.lock = threading.Lock()
        self.peers, self.reports, self.mesh = [], {}, {}
        self.turn, self.turn_t0 = 0, None
        self.done, self.ok, self.summary_text, self.run_dir = threading.Event(), None, "", None
        self._finished = False

    # -- called by the HTTP handler
    def register(self, info):
        with self.lock:
            pid = f"p{len(self.peers)}"
            peer = {"id": pid, "host": info["host"], "ip": info["ip"], "port": int(info["port"]), "wifi": info.get("wifi")}
            dup = any(q["host"] == peer["host"] for q in self.peers)
            self.peers.append(peer)
            if len(self.peers) == self.laptops:
                self.turn, self.turn_t0 = 0, time.time()
            n = len(self.peers)
        self.log(f"joined ({n}/{self.laptops}): {peer['host']} at {peer['ip']}"
                 + (f"  WARNING: another laptop is also called '{peer['host']}'; rename one with sudo hostnamectl set-hostname" if dup else ""))
        return pid

    def add_report(self, pid, rep):
        with self.lock:
            self.reports[pid] = rep
            host = next((p["host"] for p in self.peers if p["id"] == pid), pid)
        checks = rep.get("checks") or []
        nf = sum(1 for c in checks if c["status"] == "FAIL")
        nw = sum(1 for c in checks if c["status"] == "WARN")
        self.log(f"report from {host}: {nf} FAIL, {nw} WARN")

    def add_mesh(self, pid, results, complete):
        with self.lock:
            self.mesh[pid] = {"results": results, "complete": bool(complete)}
            advance = complete and self._turn_id() == pid
        if advance:
            self._advance()
        else:
            self._maybe_finish()

    def state(self):
        stale = None
        with self.lock:
            tid = self._turn_id()
            if tid and self.turn_t0 and time.time() - self.turn_t0 > self.turn_timeout:
                stale = tid
        if stale:
            self.log(f"{self._label(stale)} did not finish its turn in {self.turn_timeout:.0f} s; skipping it")
            with self.lock:
                self.mesh.setdefault(stale, {"results": {}, "complete": True})["complete"] = True
                self.mesh[stale]["skipped"] = True
            self._advance()
        with self.lock:
            return {"laptops": self.laptops, "peers": list(self.peers), "turn": self._turn_id(), "done": self.done.is_set()}

    # -- internals
    def _turn_id(self):
        return self.peers[self.turn]["id"] if len(self.peers) >= self.laptops and self.turn < len(self.peers) else None

    def _label(self, pid):
        p = next((q for q in self.peers if q["id"] == pid), None)
        return f"{p['host']} ({p['ip']})" if p else pid

    def _advance(self):
        with self.lock:
            self.turn += 1
            self.turn_t0 = time.time()
        self._maybe_finish()

    def _maybe_finish(self):
        with self.lock:
            fin = len(self.peers) >= self.laptops and self.turn >= len(self.peers) and not self._finished
            if fin:
                self._finished = True
        if fin:
            self.finish()

    def summarize(self):
        peers = self.peers
        names = {}
        for p in peers:
            names[p["id"]] = p["host"] if sum(q["host"] == p["host"] for q in peers) == 1 else f"{p['host']}@{p['ip']}"
        w = max([len(n) for n in names.values()] + [8])
        lines = ["Reachability matrix: median round-trip ms | up MB/s | down MB/s   (row = laptop probing, column = laptop probed)", ""]
        lines.append(" " * (w + 2) + "".join(f"{names[p['id']]:<{w + 2}}" for p in peers))
        bad, ok_pairs = [], 0
        for a in peers:
            res = self.mesh.get(a["id"], {}).get("results", {})
            row = f"{names[a['id']]:<{w + 2}}"
            for b in peers:
                if a["id"] == b["id"]:
                    cell = "-"
                else:
                    r = res.get(b["id"])
                    if r and "error" not in r:
                        ok_pairs += 1
                        cell = f"{r['rtt_ms']['median']:.1f}|{r['up_MBps']:.0f}|{r['down_MBps']:.0f}"
                    else:
                        cell = "FAILED"
                        bad.append((a, b, (r or {}).get("error", "not tested")))
                row += f"{cell:<{w + 2}}"
            lines.append(row)
        total = len(peers) * (len(peers) - 1)
        lines += ["", f"{ok_pairs} of {total} laptop pairs connected."]
        speeds = [r["up_MBps"] for a in peers for r in self.mesh.get(a["id"], {}).get("results", {}).values() if "error" not in r]
        if speeds:
            lines.append(f"Wi-Fi throughput between laptops: {min(speeds):.0f} to {max(speeds):.0f} MB/s (one pair at a time).")
        offs = [abs(r["clock_offset_ms_peer_minus_local"]) for a in peers for r in self.mesh.get(a["id"], {}).get("results", {}).values()
                if "error" not in r]
        if offs:
            lines.append(f"Clock difference between laptops: up to {max(offs):.1f} ms.")
        ssids = {(p.get("wifi") or {}).get("ssid") for p in peers}
        if len(ssids - {None}) > 1:
            lines.append(f"WARNING: the laptops are on different Wi-Fi networks: {sorted(s for s in ssids if s)}")
        if bad:
            lines += ["", "Problems:"]
            for a, b, err in bad:
                lines.append(f"  {names[a['id']]} -> {names[b['id']]}: {err}")
            lines.append("")
            lines.append("What this usually means: if every laptop fails to reach every other but all reach the hub, the router isolates "
                         "Wi-Fi clients ('AP isolation' / guest network): turn it off in the router. If only one laptop cannot be "
                         "reached, its firewall is on (sudo ufw status) or it left the Wi-Fi.")
        reps = [self.reports[p["id"]] for p in peers if p["id"] in self.reports]
        if len(reps) >= 2:
            rows = pf.compare(reps)
            lines += ["", "Comparison of the laptops' reports (every line must be PASS or INFO):"]
            w2 = max(len(r[0]) for r in rows)
            lines += [f"  [{s:4}] {n:<{w2}}  {d}" for n, s, d in rows]
            cmp_fail = any(s == "FAIL" for _, s, _ in rows)
        else:
            cmp_fail = False
        return "\n".join(lines), (not bad) and not cmp_fail and total > 0, ok_pairs, total

    def finish(self):
        text, ok, ok_pairs, total = self.summarize()
        self.summary_text, self.ok = text, bool(ok_pairs == total and total > 0)
        run = self.out_dir / time.strftime("%Y%m%d-%H%M%S")
        try:
            run.mkdir(parents=True, exist_ok=True)
            (run / "peers.json").write_text(json.dumps(self.peers, indent=1))
            (run / "mesh.json").write_text(json.dumps(self.mesh, indent=1))
            for p in self.peers:
                if p["id"] in self.reports:
                    (run / f"report_{p['host']}_{p['id']}.json").write_text(json.dumps(self.reports[p["id"]], indent=1, default=str))
            (run / "summary.txt").write_text(text + "\n")
            self.run_dir = run
        except OSError as e:
            self.log(f"could not write {run}: {e}")
        print("\n" + text + (f"\n\nFiles saved in {self.run_dir}" if self.run_dir else ""), flush=True)
        self.done.set()


def make_handler(hub):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _path(self):
            u = urlparse(self.path)
            tok = parse_qs(u.query).get("t", [""])[0]
            if not secrets.compare_digest(tok.encode(), hub.token.encode()):
                self.send_error(403, "bad token")
                return None
            return u.path

        def _send(self, body, ctype="application/json"):
            if isinstance(body, (dict, list)):
                body = json.dumps(body).encode()
            elif isinstance(body, str):
                body = body.encode()
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path = self._path()
            if path is None:
                return
            if path in ("/join.sh", "/dfps.bundle") and path[1:] in hub.files:
                self._send(Path(hub.files[path[1:]]).read_bytes(), "application/octet-stream")
            elif path == "/meta.txt":
                self._send("".join(f"{k}={v}\n" for k, v in hub.meta.items()), "text/plain")
            elif path == "/peers":
                self._send(hub.state())
            else:
                self.send_error(404)

        def do_POST(self):
            path = self._path()
            if path is None:
                return
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAX_POST:
                self.send_error(413)
                return
            try:
                data = json.loads(self.rfile.read(n) or b"{}")
                if path == "/register":
                    self._send({"id": hub.register(data)})
                elif path == "/report":
                    hub.add_report(data["id"], data["report"])
                    self._send({"ok": True})
                elif path == "/mesh":
                    hub.add_mesh(data["id"], data["results"], data["complete"])
                    self._send({"ok": True})
                else:
                    self.send_error(404)
            except (KeyError, ValueError, TypeError):
                self.send_error(400)

    return Handler


def serve_hub(hub, host="0.0.0.0", port=DEFAULT_HTTP_PORT):
    srv = ThreadingHTTPServer((host, port), make_handler(hub))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


# ------------------------------------------------------------------------------------------------ joining laptop
def _http(url, data=None, timeout=20):
    req = urllib.request.Request(url, data=None if data is None else json.dumps(data, default=str).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read() or b"null")


def default_report():
    rep = pf.collect("agent")
    rep["checks"] = [{"name": n, "status": s, "detail": d} for n, s, d in pf.evaluate(rep, False)]
    return rep


def start_listener(port):
    """Run the probe server in a thread; returns the port, or None if something already listens there (fine)."""
    box, ev = [], threading.Event()

    def run():
        try:
            pf.serve(port, ready=lambda p: (box.append(p), ev.set()))
        except OSError:
            ev.set()
    threading.Thread(target=run, daemon=True).start()
    ev.wait(5)
    return box[0] if box else port if port else None


def run_client(hub_url, token, listen_port=pf.DEFAULT_PORT, advertise_ip=None, report_fn=None, probe_kw=None, wait_s=1800, log=print,
               hostname=None):
    """Register with the hub, send the preflight report, then probe every other laptop when it is our turn."""
    q = f"?t={token}"
    host = urlparse(hub_url).hostname
    ip = advertise_ip or lan_ip(host)
    port = start_listener(listen_port)
    wifi = pf.collect_wifi()
    hostname = hostname or socket.gethostname()
    me = _http(f"{hub_url}/register{q}", {"host": hostname, "ip": ip, "port": port, "wifi": wifi})["id"]
    log(f"[{now()}] registered with the hub as {hostname} ({ip})")
    _http(f"{hub_url}/report{q}", {"id": me, "report": (report_fn or default_report)()}, timeout=60)
    log(f"[{now()}] report sent; waiting for the other laptops")
    kw = dict(pings=100, mb=8, rounds=2, connect_timeout=5)
    kw.update(probe_kw or {})
    results, probed, t_end, lost = {}, False, time.time() + wait_s, 0
    while time.time() < t_end:
        try:
            st = _http(f"{hub_url}/peers{q}")
            lost = 0
        except (urllib.error.URLError, OSError):
            lost += 1
            if lost >= 3:
                log(f"[{now()}] the hub is no longer reachable; stopping")
                return results
            time.sleep(1.5)
            continue
        if st["done"]:
            return results
        if st["turn"] == me and not probed:
            log(f"[{now()}] my turn: testing the connection to every other laptop")
            for p in st["peers"]:
                if p["id"] == me:
                    continue
                try:
                    results[p["id"]] = pf.probe(p["ip"], p["port"], **kw)
                    r = results[p["id"]]
                    log(f"    -> {p['host']} ({p['ip']}): {r['rtt_ms']['median']} ms, up {r['up_MBps']} MB/s, down {r['down_MBps']} MB/s")
                except (OSError, ConnectionError) as e:
                    results[p["id"]] = {"error": f"{type(e).__name__}: {e}"}
                    log(f"    -> {p['host']} ({p['ip']}): FAILED ({type(e).__name__}: {e})")
                _http(f"{hub_url}/mesh{q}", {"id": me, "results": results, "complete": False})
            _http(f"{hub_url}/mesh{q}", {"id": me, "results": results, "complete": True})
            probed = True
        time.sleep(1.5)
    return results


# ------------------------------------------------------------------------------------------------ command line
def build_bundle(dest):
    """git bundle of the current branch (code only, no data); returns (branch, commit, origin, dirty)."""
    git = lambda *a: subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True, check=True).stdout.strip()
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    subprocess.run(["git", "-C", str(ROOT), "bundle", "create", str(dest), branch], capture_output=True, check=True)
    try:
        origin = git("remote", "get-url", "origin")
    except subprocess.CalledProcessError:
        origin = ""
    # uncommitted work is not in the bundle: modified tracked files anywhere, and new files under testbed/ or tests/
    dirty = bool(git("status", "--porcelain", "--untracked-files=no")) or bool(git("status", "--porcelain", "--", "testbed", "tests"))
    return branch, git("rev-parse", "HEAD"), origin, dirty


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("hub")
    h.add_argument("--laptops", type=int, default=4, help="total number of laptops including this one")
    h.add_argument("--port", type=int, default=DEFAULT_HTTP_PORT)
    h.add_argument("--out", default=str(Path.home() / "testbed-reports"))
    h.add_argument("--turn-timeout", type=float, default=180.0)
    j = sub.add_parser("join")
    j.add_argument("--hub", required=True, help="http://HUB_IP:PORT")
    j.add_argument("--token", required=True)
    a = ap.parse_args(argv)

    if a.cmd == "join":
        res = run_client(a.hub, a.token)
        print(f"\n[{now()}] the hub has finished; its summary is on the hub laptop. This laptop probed {len(res)} peer(s).")
        return 0

    tmp = Path(tempfile.mkdtemp(prefix="testbed-hub-"))
    branch, commit, origin, dirty = build_bundle(tmp / "dfps.bundle")
    token = secrets.token_hex(3)
    ip, wifi = lan_ip(), pf.collect_wifi()
    meta = {"branch": branch, "commit": commit, "origin": origin, "hub_host": socket.gethostname(), "laptops": a.laptops}
    hub = Hub(a.laptops, token, a.out, a.turn_timeout, {"join.sh": HERE / "join.sh", "dfps.bundle": tmp / "dfps.bundle"}, meta)
    try:
        _, port = serve_hub(hub, "0.0.0.0", a.port)
    except OSError as e:
        print(f"cannot listen on port {a.port}: {e}")
        return 1
    line = f'curl -fsSL "http://{ip}:{port}/join.sh?t={token}" -o /tmp/join.sh && bash /tmp/join.sh {ip} {token} {port}'
    print(f"""
Hub ready on {ip}:{port}   Wi-Fi: {wifi.get('ssid')} (channel {wifi.get('channel')}, {wifi.get('rate')})
Code that will be handed out: branch {branch}, commit {commit[:7]}{'  WARNING: uncommitted changes (including new testbed files) are NOT included; commit first' if dirty else ''}

On each OTHER laptop (same Wi-Fi), open a terminal and paste this ONE line:

  {line}

If a laptop already has the code and Python environment (for example after a first run), it can instead run:

  ~/venv-dfps/bin/python ~/DFPS-implementation/testbed/connect.py join --hub http://{ip}:{port} --token {token}

Waiting for {a.laptops} laptops (including this one). Press Ctrl+C to stop.
""", flush=True)
    threading.Thread(target=run_client, kwargs=dict(hub_url=f"http://127.0.0.1:{port}", token=token, advertise_ip=ip,
                                                   log=lambda m: print(m, flush=True)), daemon=True).start()
    try:
        hub.done.wait()
        time.sleep(8)                                  # let the joined laptops see "done"
    except KeyboardInterrupt:
        print("\nstopped before all laptops finished")
        return 1
    return 0 if hub.ok else 2


if __name__ == "__main__":
    sys.exit(main())
