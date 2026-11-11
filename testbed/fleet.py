#!/usr/bin/env python3
"""Control all testbed laptops from the hub over SSH (testbed/DESIGN.md, "Control strategy").

Run on the hub (edge-1) with the venv python, from anywhere:  ~/venv-dfps/bin/python testbed/fleet.py COMMAND

  list                         every laptop in testbed/cluster.json (local file; see cluster.example.json): reachable?, live Wi-Fi address versus the file
  status [--measured]          preflight on every laptop, a one-line summary each, and the cross-machine comparison
  run [--on edge-2,edge-3] -- CMD...   run a shell command on every laptop (or the named ones), output per laptop
  sync [--allow-dirty] [--reset]  bring every laptop's code to the hub's commit (a git bundle over SSH; nothing from GitHub);
                               --reset also replaces a laptop whose branch diverged (it names how many local commits it drops)
  env [--fix]                  check the Python packages everywhere; --fix copies the hub's venv to any laptop that differs
  reboot [--on ...] --yes      reboot the laptops (never the hub) and wait until each is back
  discover [--write]           find the laptops on the LAN by name when their addresses changed; --write updates cluster.json

It uses the dedicated key ~/.ssh/testbed_ed25519, runs the laptops in parallel, and applies no system setting.
Exit status is 1 when any laptop failed.
"""
from __future__ import annotations

import argparse
import json
import shlex
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

try:
    from testbed import preflight as pf
except ImportError:                                    # run as a script: testbed/ is sys.path[0]
    import preflight as pf

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CLUSTER = HERE / "cluster.json"          # local, in .gitignore: real addresses must not go into the public repository
KEY = Path.home() / ".ssh" / "testbed_ed25519"
SSH_OPTS = ["-i", str(KEY), "-o", "BatchMode=yes", "-o", "IdentitiesOnly=yes", "-o", "ConnectTimeout=8",
            "-o", "StrictHostKeyChecking=accept-new"]


# ------------------------------------------------------------------------------------------------ cluster and execution
def load_cluster(path=CLUSTER):
    path = Path(path)
    if not path.exists():
        raise SystemExit(f"{path} not found. It holds the real addresses of your laptops, so it is local and not in git (the repository is "
                         f"public). Copy {path.with_name('cluster.example.json').name} to {path.name} and fill it in.")
    data = json.loads(path.read_text())
    laps = data["laptops"]
    for lap in laps:
        lap.setdefault("user", data.get("user"))
        if not lap["user"]:
            raise SystemExit(f"{path.name}: set \"user\" (the login name on the laptops)")
    return laps


def select(laps, names=None):
    if not names:
        return laps
    want = [n.strip() for n in names.split(",") if n.strip()]
    unknown = [n for n in want if n not in {lap["name"] for lap in laps}]
    if unknown:
        raise SystemExit(f"unknown laptop(s): {', '.join(unknown)}; known: {', '.join(lap['name'] for lap in laps)}")
    return [lap for lap in laps if lap["name"] in want]


def sh(lap, cmd, timeout=90, input=None):
    """Run a shell command on a laptop (locally for the hub). -> (returncode, stdout, stderr)."""
    argv = ["bash", "-c", cmd] if lap.get("local") else ["ssh", *SSH_OPTS, f"{lap['user']}@{lap['ssh']}", cmd]
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, input=input)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "timed out"


def pmap(fn, laps):
    with ThreadPoolExecutor(max_workers=max(1, len(laps))) as ex:
        return list(ex.map(fn, laps))


def short(text, n=160):
    text = " ".join((text or "").split())
    return text if len(text) <= n else text[: n - 1] + "…"


# ------------------------------------------------------------------------------------------------ list
WIFI_PROBE = ("d=$(nmcli -t -f DEVICE,TYPE device | awk -F: '$2==\"wifi\" && $1 !~ /^p2p/ {print $1; exit}'); "
              "echo \"$(hostname) $d $(cat /sys/class/net/$d/address 2>/dev/null) $(ip -4 -br addr show $d | awk '{print $3}' | cut -d/ -f1)\"")


def cmd_list(laps):
    def one(lap):
        t = time.time()
        rc, out, err = sh(lap, WIFI_PROBE, timeout=20)
        ms = (time.time() - t) * 1e3
        if rc != 0 or len(out.split()) < 4:
            return lap, None, ms, short(err or out)
        host, iface, mac, ip = out.split()[:4]
        return lap, (host, iface, mac, ip), ms, ""
    bad = 0
    print(f"{'laptop':<8} {'control address':<16} {'hostname':<8} {'Wi-Fi address (live)':<21} {'ms':>5}  notes")
    for lap, live, ms, err in pmap(one, laps):
        if live is None:
            bad += 1
            print(f"{lap['name']:<8} {lap['ssh']:<16} {'UNREACHABLE':<8} {'':<21} {'':>5}  {err}")
            continue
        host, iface, mac, ip = live
        notes = []
        if host != lap["name"]:
            notes.append(f"hostname is {host}, expected {lap['name']}")
        if ip != lap.get("wifi_ip"):
            notes.append(f"Wi-Fi address is {ip}, file says {lap.get('wifi_ip')}: run discover --write")
        if lap["ssh"] != ip:
            notes.append("controlled over another interface than Wi-Fi")
        print(f"{lap['name']:<8} {lap['ssh']:<16} {host:<8} {ip:<21} {ms:>5.0f}  {'; '.join(notes) or 'ok'}")
    return 1 if bad else 0


# ------------------------------------------------------------------------------------------------ status
def remote_status_cmd(lap, measured):
    role = "coordinator" if lap.get("role") == "hub" else "agent"
    return ("cd ~/DFPS-implementation 2>/dev/null && ~/venv-dfps/bin/python testbed/preflight.py report "
            f"--role {role} {'--measured' if measured else ''} --out /tmp/fleet_status.json >/dev/null 2>&1; cat /tmp/fleet_status.json")


def get_reports(laps, measured=False):
    def one(lap):
        rc, out, err = sh(lap, remote_status_cmd(lap, measured), timeout=180)
        try:
            return lap, json.loads(out), ""
        except ValueError:
            return lap, None, short(err or out or "no report (repo or venv missing?)")
    return pmap(one, laps)


def check(rep, name):
    return next((c["status"] for c in rep.get("checks", []) if c["name"] == name), "?")


def cmd_status(laps, measured=False, verbose=False):
    got = get_reports(laps, measured)
    print(f"{'laptop':<8} {'commit':<8} {'kernel':<20} {'packages':<9} {'FAIL':>4} {'WARN':>4}  Wi-Fi")
    reps, bad = [], 0
    for lap, rep, err in got:
        if rep is None:
            bad += 1
            print(f"{lap['name']:<8} NO REPORT: {err}")
            continue
        reps.append(rep)
        checks = rep.get("checks", [])
        nf = sum(c["status"] == "FAIL" for c in checks)
        nw = sum(c["status"] == "WARN" for c in checks)
        bad += nf > 0
        wf = rep.get("wifi", {})
        print(f"{lap['name']:<8} {str((rep.get('repo') or {}).get('head'))[:7]:<8} {rep['kernel']['release']:<20} "
              f"{check(rep, 'packages == testbed/requirements.txt'):<9} {nf:>4} {nw:>4}  {wf.get('ssid')} {wf.get('rate')}")
        if verbose:
            for c in checks:
                if c["status"] in ("FAIL", "WARN"):
                    print(f"           [{c['status']}] {c['name']}: {short(c['detail'], 110)}")
    if len(reps) >= 2:
        rows = pf.compare(reps)
        print("\nSame on every laptop? (hardware lines are information only)")
        for n, s, d in rows:
            print(f"  [{s:4}] {n:<22} {short(d, 100) if s != 'PASS' else 'identical'}")
        bad += any(s == "FAIL" for _, s, _ in rows)
    return 1 if bad else 0


# ------------------------------------------------------------------------------------------------ run
def cmd_run(laps, command):
    cmd = " ".join(command)
    bad = 0
    for lap, (rc, out, err) in zip(laps, pmap(lambda lap: sh(lap, cmd, timeout=600), laps)):
        bad += rc != 0
        print(f"===== {lap['name']} (exit {rc})")
        text = (out + (("\n[stderr]\n" + err) if err.strip() else "")).rstrip()
        if text:
            print(text)
    return 1 if bad else 0


# ------------------------------------------------------------------------------------------------ sync
SYNC_SCRIPT = r'''set -e
BR={branch}; BUNDLE=/tmp/fleet.bundle; REPO="$HOME/DFPS-implementation"; ORIGIN={origin}
if [ -d "$REPO/.git" ]; then
  [ -z "$(git -C "$REPO" status --porcelain --untracked-files=no)" ] || {{ echo LOCAL_CHANGES; exit 3; }}
  git -C "$REPO" fetch -q "$BUNDLE" "refs/heads/$BR"
  git -C "$REPO" checkout -q "$BR" 2>/dev/null || git -C "$REPO" checkout -q -b "$BR" FETCH_HEAD
  if ! git -C "$REPO" merge -q --ff-only FETCH_HEAD; then
    [ "{reset}" = "1" ] || {{ echo DIVERGED; exit 4; }}
    echo "RESET: dropping $(git -C "$REPO" rev-list --count FETCH_HEAD..HEAD) local commit(s) that are not in the hub's branch" >&2
    git -C "$REPO" reset -q --hard FETCH_HEAD
  fi
else
  git clone -q -b "$BR" "$BUNDLE" "$REPO"
fi
[ -z "$ORIGIN" ] || git -C "$REPO" remote set-url origin "$ORIGIN"
rm -f "$BUNDLE"
git -C "$REPO" rev-parse HEAD
'''


def hub_git(*a):
    return subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True, check=True).stdout.strip()


def cmd_sync(laps, allow_dirty=False, tmpdir="/tmp", reset=False):
    branch, commit = hub_git("rev-parse", "--abbrev-ref", "HEAD"), hub_git("rev-parse", "HEAD")
    dirty = hub_git("status", "--porcelain", "--untracked-files=no") or hub_git("status", "--porcelain", "--", "testbed", "tests")
    if dirty and not allow_dirty:
        print("The hub has uncommitted changes (including new files under testbed/ or tests/); the other laptops would get\n"
              "the committed code only. Commit first, or use --allow-dirty to sync the committed state anyway.")
        return 1
    try:
        origin = hub_git("remote", "get-url", "origin")
    except subprocess.CalledProcessError:
        origin = ""
    bundle = str(Path(tmpdir) / "fleet-hub.bundle")
    subprocess.run(["git", "-C", str(ROOT), "bundle", "create", bundle, branch], capture_output=True, check=True)
    remote = [lap for lap in laps if not lap.get("local")]

    def one(lap):
        p = subprocess.run(["scp", "-q", *SSH_OPTS, bundle, f"{lap['user']}@{lap['ssh']}:/tmp/fleet.bundle"], capture_output=True, text=True)
        if p.returncode:
            return lap, False, short(p.stderr)
        rc, out, err = sh(lap, "bash -s", timeout=300, input=SYNC_SCRIPT.format(branch=shlex.quote(branch), origin=shlex.quote(origin), reset="1" if reset else "0"))
        last = (out.strip().splitlines() or [""])[-1]
        if rc == 3:
            return lap, False, "has local changes to tracked files; not touching it"
        if rc == 4:
            return lap, False, "has commits that are not in the hub's branch (history rewritten?); check them, then use --reset to replace them"
        reset_line = next((ln for ln in err.splitlines() if ln.startswith("RESET")), "")
        note = f" ({reset_line[7:].strip()})" if reset_line else ""
        return lap, rc == 0 and last == commit, (last[:7] + note) if rc == 0 else short(err or out)
    bad = 0
    print(f"hub: {branch} at {commit[:7]}")
    for lap, ok, info in pmap(one, remote):
        bad += not ok
        print(f"  {lap['name']:<8} {'ok, at ' + commit[:7] + (info[7:] if len(info) > 7 else '') if ok else 'FAILED: ' + info}")
    return 1 if bad else 0


# ------------------------------------------------------------------------------------------------ env
def cmd_env(laps, fix=False):
    got = get_reports(laps)
    bad = 0
    for lap, rep, err in got:
        if lap.get("local"):
            continue
        ok = rep is not None and check(rep, "packages == testbed/requirements.txt") == "PASS"
        if ok:
            print(f"  {lap['name']:<8} packages match")
            continue
        if not fix:
            bad += 1
            print(f"  {lap['name']:<8} packages DIFFER or missing; run: fleet.py env --fix --on {lap['name']}")
            continue
        e = "ssh " + " ".join(shlex.quote(o) for o in SSH_OPTS)
        t = time.time()
        p = subprocess.run(["rsync", "-a", "--delete", "-e", e, f"{Path.home()}/venv-dfps/", f"{lap['user']}@{lap['ssh']}:venv-dfps/"],
                           capture_output=True, text=True)
        bad += p.returncode != 0
        print(f"  {lap['name']:<8} " + (f"copied the hub's venv in {time.time() - t:.0f} s" if p.returncode == 0 else "COPY FAILED: " + short(p.stderr)))
    return 1 if bad else 0


# ------------------------------------------------------------------------------------------------ reboot
def cmd_reboot(laps, wait_s=300, sleep=time.sleep):
    laps = [lap for lap in laps if not lap.get("local")]
    if not laps:
        print("nothing to reboot (the hub is never rebooted by this command)")
        return 0

    def one(lap):
        rc, boot0, _ = sh(lap, "cat /proc/sys/kernel/random/boot_id", timeout=20)
        if rc != 0:
            return lap, False, "unreachable before reboot"
        sh(lap, "sudo -n systemctl reboot", timeout=20)
        sleep(10)
        t_end = time.time() + wait_s
        while time.time() < t_end:
            rc, boot1, _ = sh(lap, "cat /proc/sys/kernel/random/boot_id", timeout=15)
            if rc == 0 and boot1.strip() and boot1.strip() != boot0.strip():
                return lap, True, f"back after about {wait_s - (t_end - time.time()):.0f} s"
            sleep(5)
        return lap, False, f"did not come back within {wait_s} s"
    bad = 0
    for lap, ok, info in pmap(one, laps):
        bad += not ok
        print(f"  {lap['name']:<8} {info}")
    return 1 if bad else 0


# ------------------------------------------------------------------------------------------------ discover
def hub_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()


def port_open(ip, port=22, timeout=0.6):
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except OSError:
        return False


def cmd_discover(laps, write=False, path=CLUSTER, scan=None):
    mine = hub_ip()
    prefix = ".".join(mine.split(".")[:3])
    cands = [f"{prefix}.{i}" for i in range(1, 255) if f"{prefix}.{i}" != mine]
    with ThreadPoolExecutor(max_workers=64) as ex:
        open_ips = [ip for ip, ok in zip(cands, ex.map(port_open, cands)) if ok] if scan is None else scan
    print(f"SSH answers on {len(open_ips)} address(es) of {prefix}.0/24")
    found = {}
    for ip in open_ips:
        probe = {"name": "?", "user": laps[0]["user"], "ssh": ip}
        rc, out, _ = sh(probe, WIFI_PROBE, timeout=20)
        if rc == 0 and len(out.split()) >= 4:
            host, iface, mac, wip = out.split()[:4]
            found.setdefault(host, []).append({"ssh": ip, "wifi_iface": iface, "wifi_mac": mac, "wifi_ip": wip})
    changed = False
    data = json.loads(Path(path).read_text())
    for lap in data["laptops"]:
        if lap.get("local"):
            continue
        hits = found.get(lap["name"])
        if not hits:
            print(f"  {lap['name']:<8} NOT FOUND (off, off the Wi-Fi, or its key is missing)")
            continue
        pick = next((h for h in hits if h["ssh"] == lap["ssh"]), hits[0])
        diff = {k: v for k, v in pick.items() if lap.get(k) != v}
        print(f"  {lap['name']:<8} found at {', '.join(h['ssh'] for h in hits)}" + (f"; changes: {diff}" if diff else "; unchanged"))
        if diff and write:
            lap.update(diff)
            changed = True
    if write and changed:
        Path(path).write_text(json.dumps(data, indent=2) + "\n")
        print(f"updated {path}")
    return 0


# ------------------------------------------------------------------------------------------------ command line
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cluster", default=str(CLUSTER))
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("list", "status", "run", "sync", "env", "reboot", "discover"):
        p = sub.add_parser(name)
        if name in ("status", "run", "env", "reboot"):
            p.add_argument("--on", help="comma-separated laptop names (default: all)")
        if name == "status":
            p.add_argument("--measured", action="store_true")
            p.add_argument("--verbose", "-v", action="store_true")
        if name == "run":
            p.add_argument("command", nargs=argparse.REMAINDER)
        if name == "sync":
            p.add_argument("--allow-dirty", action="store_true")
            p.add_argument("--reset", action="store_true", help="when a laptop's branch diverged, replace it with the hub's (drops its local commits)")
        if name == "env":
            p.add_argument("--fix", action="store_true")
        if name == "reboot":
            p.add_argument("--yes", action="store_true", help="required: this reboots the laptops")
        if name == "discover":
            p.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    laps = select(load_cluster(a.cluster), getattr(a, "on", None))
    if a.cmd == "list":
        return cmd_list(laps)
    if a.cmd == "status":
        return cmd_status(laps, a.measured, a.verbose)
    if a.cmd == "run":
        cmd = a.command[1:] if a.command and a.command[0] == "--" else a.command
        if not cmd:
            raise SystemExit("usage: fleet.py run [--on edge-2,edge-3] -- COMMAND")
        return cmd_run(laps, cmd)
    if a.cmd == "sync":
        return cmd_sync(laps, a.allow_dirty, reset=a.reset)
    if a.cmd == "env":
        return cmd_env(laps, a.fix)
    if a.cmd == "reboot":
        if not a.yes:
            raise SystemExit("this reboots " + ", ".join(lap["name"] for lap in laps if not lap.get("local")) + "; add --yes to do it")
        return cmd_reboot(laps)
    return cmd_discover(load_cluster(a.cluster), a.write, a.cluster)


if __name__ == "__main__":
    sys.exit(main())
