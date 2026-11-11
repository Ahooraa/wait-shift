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
  agents start|stop|status|check   run the node agents (testbed/agent.py) on every laptop, and measure them (timers, transfers, clocks)
  clock setup|status|undo      make the hub the time source of the other laptops (chrony), so their clocks agree to about a millisecond
  guard [--seconds N] [--cooldown S]  the check before a measured run (waits S s, default 90, after the last run first): no Wi-Fi scan source, no scan seen, link quality, recent impairment, settings, agent, monitor
  monitor start|stop|status|collect|report   the network monitor (testbed/netmon.py) on every laptop: Wi-Fi state and a UDP latency probe between laptops

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
    from testbed import runmark
except ImportError:                                    # run as a script: testbed/ is sys.path[0]
    import preflight as pf
    import runmark

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
def remote_status_cmd(lap, measured, watch_s=0):
    role = "coordinator" if lap.get("role") == "hub" else "agent"
    return ("cd ~/DFPS-implementation 2>/dev/null && ~/venv-dfps/bin/python testbed/preflight.py report "
            f"--role {role} {'--measured' if measured else ''} {f'--watch-scans {watch_s}' if watch_s else ''} --out /tmp/fleet_status.json >/dev/null 2>&1; cat /tmp/fleet_status.json")


def get_reports(laps, measured=False, watch_s=0):
    def one(lap):
        rc, out, err = sh(lap, remote_status_cmd(lap, measured, watch_s), timeout=180 + watch_s)
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


# ------------------------------------------------------------------------------------------------ node agents
AGENT_PORT = 5300
TOKEN_FILE = Path.home() / ".testbed" / "agent.token"

AGENT_START = r"""mkdir -p ~/testbed-logs ~/.testbed
if [ -f ~/.testbed/agent.pid ] && kill -0 "$(cat ~/.testbed/agent.pid)" 2>/dev/null; then
  echo "already running (pid $(cat ~/.testbed/agent.pid))"
else
  cd ~/DFPS-implementation && [ -f testbed/agent.py ] || {{ echo "FAILED: testbed/agent.py is not on this laptop (commit, then fleet.py sync)"; exit 1; }}
  (setsid nohup ~/venv-dfps/bin/python testbed/agent.py serve --port {port} --token-file ~/.testbed/agent.token --log-dir ~/testbed-logs >> ~/testbed-logs/agent.out 2>&1 < /dev/null & echo $! > ~/.testbed/agent.pid)
  sleep 1
  if kill -0 "$(cat ~/.testbed/agent.pid)" 2>/dev/null; then echo "started (pid $(cat ~/.testbed/agent.pid))"; else echo "FAILED to start"; tail -5 ~/testbed-logs/agent.out; exit 1; fi
fi"""
AGENT_STOP = r"""if [ -f ~/.testbed/agent.pid ] && kill -0 "$(cat ~/.testbed/agent.pid)" 2>/dev/null; then kill "$(cat ~/.testbed/agent.pid)"; rm -f ~/.testbed/agent.pid; echo stopped; else rm -f ~/.testbed/agent.pid; echo "not running"; fi"""


def hub_token(path=TOKEN_FILE):
    """The shared secret of the agents: created once on the hub (mode 600) and copied to every laptop by `agents start`."""
    path = Path(path)
    if not path.exists() or not path.read_text().strip():
        import secrets
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(mode=0o600)
        path.write_text(secrets.token_hex(16) + "\n")
    path.chmod(0o600)
    return path.read_text().strip()


def cmd_agents(laps, action, token_path=TOKEN_FILE, port=AGENT_PORT):
    token = hub_token(token_path)
    if action == "check":
        try:
            from testbed.agentcheck import run_check
        except ImportError:
            from agentcheck import run_check
        ok = run_check(laps, token, port)
        print("\nagent check: " + ("OK" if ok else "PROBLEMS (see above)"))
        return 0 if ok else 1
    if action == "status":
        try:
            from testbed.agentclient import AgentClient
        except ImportError:
            from agentclient import AgentClient

        def one(lap):
            try:
                c = AgentClient(lap.get("wifi_ip") or lap["ssh"], port, token, timeout=5)
                st = c.call("status")
                c.close()
                late = st["lateness_s"]
                return lap, True, (f"running, {st['instances']} instances, {st['counters']['tasks']} tasks, "
                                   f"lateness max {late['max'] * 1e3:.1f} ms over {late['n']} timers, speed {st['speed']:g}")
            except Exception as e:                                       # noqa: BLE001 - report any failure per laptop
                return lap, False, f"not reachable: {short(str(e), 80)}"
        bad = 0
        for lap, ok, info in pmap(one, laps):
            bad += not ok
            print(f"  {lap['name']:<8} {info}")
        return 1 if bad else 0

    def one(lap):
        if action == "start":
            if not lap.get("local"):
                rc, _, err = sh(lap, "mkdir -p ~/.testbed && umask 077 && cat > ~/.testbed/agent.token", input=token + "\n", timeout=30)
                if rc:
                    return lap, False, "could not place the token: " + short(err)
            rc, out, err = sh(lap, AGENT_START.format(port=port), timeout=60)
        else:
            rc, out, err = sh(lap, AGENT_STOP, timeout=30)
        return lap, rc == 0, short(out or err)
    bad = 0
    for lap, ok, info in pmap(one, laps):
        bad += not ok
        print(f"  {lap['name']:<8} {info}")
    return 1 if bad else 0


# ------------------------------------------------------------------------------------------------ clock
# Each laptop synchronised to its own subset of internet servers, which disagree by tens of milliseconds, so the laptops differed by
# about 12 ms although each said it was within 2 ms. One clock for all four: the hub serves time to the LAN, the others follow only the hub.
CLOCK_HUB = r"""set -eu
mkdir -p /etc/chrony/conf.d
printf 'allow {subnet}\nlocal stratum 10\n' > /etc/chrony/conf.d/testbed-server.conf
systemctl restart chrony
echo "hub serves time to {subnet}"
"""
CLOCK_AGENT = r"""set -eu
mkdir -p /etc/chrony/conf.d
[ -f /etc/chrony/chrony.conf.testbed-orig ] || cp /etc/chrony/chrony.conf /etc/chrony/chrony.conf.testbed-orig
sed -i -e 's/^pool /#testbed-disabled# pool /' -e 's/^sourcedir \/run\/chrony-dhcp/#testbed-disabled# sourcedir \/run\/chrony-dhcp/' /etc/chrony/chrony.conf
printf 'server {hub} iburst prefer minpoll 3 maxpoll 5\n' > /etc/chrony/conf.d/testbed-client.conf
systemctl restart chrony
sleep 12
chronyc makestep >/dev/null
echo "now follows the hub only"
"""
CLOCK_UNDO_HUB = r"""rm -f /etc/chrony/conf.d/testbed-server.conf; systemctl restart chrony; echo "hub no longer serves time" """
CLOCK_UNDO_AGENT = r"""rm -f /etc/chrony/conf.d/testbed-client.conf
[ -f /etc/chrony/chrony.conf.testbed-orig ] && cp /etc/chrony/chrony.conf.testbed-orig /etc/chrony/chrony.conf
systemctl restart chrony; echo "back to the original internet servers" """
CLOCK_STATUS = r"""chronyc tracking | awk -F' : ' '/Reference ID|Stratum|System time/ {printf "%s=%s; ", $1, $2}'; echo; echo "sources: $(chronyc sources -n | grep -c '^[\^=#]'); selected: $(chronyc sources | awk '/^\^\*/ {print $2}')" """


def subnet_of(ip):
    return ".".join(ip.split(".")[:3]) + ".0/24"


def run_root(lap, script, timeout=120):
    import base64
    b64 = base64.b64encode(script.encode()).decode()
    return sh(lap, f"echo {b64} | base64 -d | sudo -n bash", timeout=timeout)


def cmd_clock(laps, action):
    hub = next((lap for lap in laps if lap.get("local")), None) or next(lap for lap in load_cluster() if lap.get("local"))
    hub_ip = hub.get("wifi_ip") or hub["ssh"]
    bad = 0
    if action == "status":
        for lap, (rc, out, err) in zip(laps, pmap(lambda lap: sh(lap, CLOCK_STATUS, timeout=30), laps)):
            bad += rc != 0
            print(f"  {lap['name']:<8} {short(out or err, 150)}")
        return 1 if bad else 0
    # the hub first (it must serve before the others ask), then the others in parallel
    hub_script = CLOCK_HUB.format(subnet=subnet_of(hub_ip)) if action == "setup" else CLOCK_UNDO_HUB
    others = [lap for lap in laps if not lap.get("local")]
    if any(lap.get("local") for lap in laps):
        rc, out, err = run_root(hub, hub_script)
        bad += rc != 0
        print(f"  {hub['name']:<8} {short(out or err)}")
    script = CLOCK_AGENT.format(hub=hub_ip) if action == "setup" else CLOCK_UNDO_AGENT
    for lap, (rc, out, err) in zip(others, pmap(lambda lap: run_root(lap, script, timeout=180), others)):
        bad += rc != 0
        print(f"  {lap['name']:<8} {short(out or err)}")
    return 1 if bad else 0


# ------------------------------------------------------------------------------------------------ network monitor
MONITOR_START = r"""mkdir -p ~/testbed-logs ~/.testbed
if [ -f ~/.testbed/netmon.pid ] && kill -0 "$(cat ~/.testbed/netmon.pid)" 2>/dev/null; then
  echo "already running (pid $(cat ~/.testbed/netmon.pid))"
else
  cd ~/DFPS-implementation && [ -f testbed/netmon.py ] || {{ echo "FAILED: testbed/netmon.py is not on this laptop (commit, then fleet.py sync)"; exit 1; }}
  (setsid nohup python3 -I testbed/netmon.py run {peers} >> ~/testbed-logs/netmon.out 2>&1 < /dev/null & echo $! > ~/.testbed/netmon.pid)
  sleep 1
  if kill -0 "$(cat ~/.testbed/netmon.pid)" 2>/dev/null; then echo "started (pid $(cat ~/.testbed/netmon.pid))"; else echo "FAILED to start"; tail -5 ~/testbed-logs/netmon.out; exit 1; fi
fi"""
MONITOR_STOP = r"""if [ -f ~/.testbed/netmon.pid ] && kill -0 "$(cat ~/.testbed/netmon.pid)" 2>/dev/null; then kill "$(cat ~/.testbed/netmon.pid)"; rm -f ~/.testbed/netmon.pid; echo stopped; else rm -f ~/.testbed/netmon.pid; echo "not running"; fi"""
MONITOR_LAST = r"""f=$(ls -t ~/testbed-logs/netmon-*.jsonl 2>/dev/null | head -1); [ -n "$f" ] && tail -n 1 "$f" && echo "AGE $(( $(date +%s) - $(stat -c %Y "$f") ))" """


def monitor_start_cmd(lap, all_laps, echo_port=5301):
    peers = " ".join(f"--peer {o['name']}={o.get('wifi_ip') or o['ssh']}" for o in all_laps if o["name"] != lap["name"])
    return MONITOR_START.format(peers=peers)


def cmd_monitor(laps, action, all_laps=None, out_dir=None):
    all_laps = all_laps or laps
    if action in ("start", "stop"):
        bad = 0
        for lap, (rc, out, err) in zip(laps, pmap(lambda lap: sh(lap, monitor_start_cmd(lap, all_laps) if action == "start" else MONITOR_STOP, timeout=60), laps)):
            bad += rc != 0
            print(f"  {lap['name']:<8} {short(out or err)}")
        return 1 if bad else 0
    if action == "status":
        bad = 0
        for lap, (rc, out, err) in zip(laps, pmap(lambda lap: sh(lap, MONITOR_LAST, timeout=30), laps)):
            try:
                lines = out.strip().splitlines()
                rec, age = json.loads(lines[0]), int(lines[1].split()[1])
                worst = max([p["max_ms"] or 0 for p in rec["rtt"].values()] or [0])
                print(f"  {lap['name']:<8} last sample {age} s ago, signal {rec['signal_dbm']} dBm, link {rec['tx_bitrate_mbps']} Mbit/s, probe worst {worst:.1f} ms")
                bad += age > 10
            except (ValueError, IndexError):
                bad += 1
                print(f"  {lap['name']:<8} no samples (not running?) {short(err or out, 80)}")
        return 1 if bad else 0
    # collect / report: copy the newest monitor log and agent log of every laptop to a local, git-ignored results folder
    out = Path(out_dir or Path.home() / "testbed-results" / f"netmon-{time.strftime('%Y%m%d-%H%M%S')}")
    out.mkdir(parents=True, exist_ok=True)
    mons, ags = [], []
    for lap in laps:
        rc, listing, _ = sh(lap, "ls -t ~/testbed-logs/netmon-*.jsonl 2>/dev/null | head -1; ls -t ~/testbed-logs/agent-5300-*.jsonl 2>/dev/null | head -1", timeout=30)
        names = listing.split()
        for kind, remote, bucket in (("netmon", next((x for x in names if "netmon-" in x), None), mons), ("agent", next((x for x in names if "agent-5300" in x), None), ags)):
            if not remote:
                continue
            dest = out / f"{lap['name']}-{kind}.jsonl"
            if lap.get("local"):
                subprocess.run(["cp", remote, str(dest)], check=True)
            else:
                subprocess.run(["scp", "-q", *SSH_OPTS, f"{lap['user']}@{lap['ssh']}:{remote}", str(dest)], check=True, capture_output=True)
            bucket.append(str(dest))
    print(f"collected {len(mons)} monitor log(s) and {len(ags)} agent log(s) into {out}")
    if action == "collect":
        return 0
    try:
        from testbed import netmon as NM
    except ImportError:
        import netmon as NM
    return NM.main(["analyze", "--monitor", *mons, "--agent", *[a for m in mons for a in ags if Path(a).name.split("-")[0] == Path(m).name.split("-")[0]]])


# ------------------------------------------------------------------------------------------------ guard before a measured run
GUARD_CHECKS = ("no Wi-Fi scan source running", "no half-open outbound connections", "no Wi-Fi scan observed", "Wi-Fi link quality", "recent Wi-Fi impairment", "Wi-Fi power save off",
                "chrony synchronised", "cpu governor = performance", "swap off", "packages == testbed/requirements.txt")


def guard_extra(lap, port=None):
    """The agent answers and the network monitor is running and fresh; a list of problems (empty = fine)."""
    problems = []
    try:
        from testbed.agentclient import AgentClient
    except ImportError:
        from agentclient import AgentClient
    try:
        AgentClient(lap.get("wifi_ip") or lap["ssh"], port or AGENT_PORT, hub_token(), timeout=5).close()
    except Exception as e:                                           # noqa: BLE001 - any failure to connect is a problem to report
        problems.append(("agent reachable", f"no: {short(str(e), 60)}"))
    rc, out, err = sh(lap, MONITOR_LAST, timeout=30)
    try:
        age = int(out.strip().splitlines()[1].split()[1])
        if age > 10:
            problems.append(("network monitor running", f"last sample {age} s ago"))
    except (ValueError, IndexError):
        problems.append(("network monitor running", "no samples"))
    return problems


def cmd_guard(laps, seconds=20, reports=None, extra=None, out=print, cooldown_s=0.0, sleep=time.sleep, now=None):
    """Refuse-to-run check for a measured run, on every laptop in parallel: no Wi-Fi scan source (a Settings window makes a laptop scan every 15 s
    and stalls the whole testbed), no scan seen in `seconds`, link quality, recent impairment seen by the monitor, plus the software and setting
    checks of the preflight (--measured), the agent and the monitor. Prints one line per laptop; returns 1 if any laptop fails."""
    if cooldown_s:                    # our own run's traffic is still in the monitor's last minute: wait it out, then look (testbed/runmark.py)
        wait = runmark.cooldown_remaining(cooldown_s, now=now)
        if wait > 0:
            out(f"cooling down {wait:.0f} s: the last run ended less than {cooldown_s:.0f} s ago and its own traffic would count as Wi-Fi impairment")
            sleep(wait)
    got = reports if reports is not None else get_reports(laps, measured=True, watch_s=seconds)
    extras = pmap((extra or guard_extra), laps) if extra is not False else [[] for _ in laps]
    bad = 0
    for (lap, rep, err), ex in zip(got, extras):
        if rep is None:
            bad += 1
            out(f"  {lap['name']:<8} FAIL  no report: {err}")
            continue
        fails = [(c["name"], c["detail"]) for c in rep.get("checks", []) if c["status"] == "FAIL" and c["name"] in GUARD_CHECKS] + list(ex)
        warns = [c["name"] for c in rep.get("checks", []) if c["status"] == "WARN" and c["name"] in GUARD_CHECKS]
        ran = [c["name"] for c in rep.get("checks", []) if c["name"] in GUARD_CHECKS]
        if fails:
            bad += 1
            out(f"  {lap['name']:<8} FAIL  " + "; ".join(f"{n}: {short(d, 90)}" for n, d in fails))
        else:
            out(f"  {lap['name']:<8} ok    {len(ran)} checks" + (f", warnings: {', '.join(warns)}" if warns else ""))
    out("guard: " + ("all laptops ready for a measured run" if not bad else f"{bad} laptop(s) NOT ready; fix them (nothing was changed) before measuring"))
    return 1 if bad else 0


# ------------------------------------------------------------------------------------------------ command line
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cluster", default=str(CLUSTER))
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("list", "status", "run", "sync", "env", "reboot", "discover", "agents", "clock", "monitor", "guard"):
        p = sub.add_parser(name)
        if name in ("status", "run", "env", "reboot", "agents", "clock", "monitor", "guard"):
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
        if name == "agents":
            p.add_argument("action", choices=("start", "stop", "status", "check"))
        if name == "clock":
            p.add_argument("action", choices=("setup", "status", "undo"))
        if name == "monitor":
            p.add_argument("action", choices=("start", "stop", "status", "collect", "report"))
        if name == "guard":
            p.add_argument("--seconds", type=int, default=20, help="how long to watch the Wi-Fi driver for scans")
            p.add_argument("--cooldown", type=float, default=None, help="seconds to leave after the last run before judging the Wi-Fi (default 90, 0 = no wait)")
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
    if a.cmd == "agents":
        return cmd_agents(laps, a.action)
    if a.cmd == "clock":
        return cmd_clock(laps, a.action)
    if a.cmd == "monitor":
        return cmd_monitor(laps, a.action, load_cluster(a.cluster))
    if a.cmd == "guard":
        return cmd_guard(laps, a.seconds, cooldown_s=runmark.COOLDOWN_S if a.cooldown is None else a.cooldown)
    return cmd_discover(load_cluster(a.cluster), a.write, a.cluster)


if __name__ == "__main__":
    sys.exit(main())
