#!/usr/bin/env bash
# Join the testbed from a laptop that has nothing installed. The hub prints the exact line to paste; it ends up running:
#     bash /tmp/join.sh HUB_IP TOKEN [PORT]
# Steps: 1 test the connection to the hub, 2 install the tools (asks first), 3 get the code from the hub (no GitHub login),
# 4 build the Python environment, 5 report to the hub and test the connection to every other laptop.
# It changes no system setting; the only system change is installing packages, and it asks before doing so.
# For testing only: SKIP_APT=1 SKIP_BOOTSTRAP=1 SKIP_JOIN=1 ASSUME_YES=1 DFPS_DIR=/some/dir
set -euo pipefail

HUB="${1:?usage: join.sh HUB_IP TOKEN [PORT]}"
TOKEN="${2:?usage: join.sh HUB_IP TOKEN [PORT]}"
PORT="${3:-8000}"
BASE="http://$HUB:$PORT"
Q="?t=$TOKEN"
REPO="${DFPS_DIR:-$HOME/DFPS-implementation}"

say()  { printf '\n== %s\n' "$*"; }
fail() { printf '\nSTOP: %s\n' "$*" >&2; exit 1; }
fetch() { curl -fsSL --max-time 300 "$BASE/$1$Q" -o "$2"; }

say "1/5  Can this laptop reach the hub at $HUB?"
if ping -c 2 -W 2 "$HUB" >/dev/null 2>&1; then echo "ping: ok"; else echo "ping: no reply (some routers drop ping; carrying on)"; fi
if ! timeout 5 bash -c "cat </dev/null >/dev/tcp/$HUB/$PORT" 2>/dev/null; then
  cat >&2 <<EOF

STOP: cannot open a connection to $HUB:$PORT.
 - Is this laptop on the same Wi-Fi network as the hub? Check:  nmcli -t -f ACTIVE,SSID device wifi | grep '^yes'
 - Is the hub still running (the terminal that printed the line you pasted)?
 - If both are fine, the router is probably blocking laptop-to-laptop traffic ("AP isolation" or a guest network). Turn that off in the
   router's Wi-Fi settings, then paste the line again.
EOF
  exit 1
fi
echo "connection to the hub: ok"

META="$(mktemp)"
fetch meta.txt "$META" || fail "the hub refused the request (wrong token?). Copy the line from the hub again."
BRANCH=""; COMMIT=""; ORIGIN=""; HUB_HOST=""
while IFS='=' read -r k v; do
  case "$k" in branch) BRANCH="$v";; commit) COMMIT="$v";; origin) ORIGIN="$v";; hub_host) HUB_HOST="$v";; esac
done <"$META"
[ -n "$BRANCH" ] || fail "the hub sent no branch name"
if [ "$(hostname)" = "$HUB_HOST" ]; then
  echo "WARNING: this laptop has the same name as the hub ($HUB_HOST). Give each laptop its own name first:"
  echo "         sudo hostnamectl set-hostname dfps-2     (use a different number on each laptop), then run this line again."
  if [ "${ASSUME_YES:-0}" = "1" ]; then ans=y; else read -r -p "Carry on anyway? [y/N] " ans </dev/tty || ans=n; fi
  case "$ans" in y|Y) ;; *) exit 1;; esac
fi

say "2/5  Install the tools (git, Python venv/pip, compiler, rsync, curl, iw, chrony)"
if [ "${SKIP_APT:-0}" = "1" ]; then
  echo "skipped (SKIP_APT=1)"
else
  echo "This runs:  sudo apt-get update  and  sudo apt-get install -y git python3-venv python3-pip build-essential rsync curl iw chrony"
  echo "It asks for your password. Nothing else on the system is changed."
  if [ "${ASSUME_YES:-0}" = "1" ]; then ans=y; else read -r -p "Continue? [Y/n] " ans </dev/tty || ans=y; fi
  case "$ans" in n|N) exit 1;; esac
  sudo apt-get update -qq
  sudo apt-get install -y git python3-venv python3-pip build-essential rsync curl iw chrony
fi

say "3/5  Get the code from the hub (branch $BRANCH)"
BUNDLE="$(mktemp --suffix=.bundle)"
fetch dfps.bundle "$BUNDLE" || fail "could not download the code from the hub"
if [ -d "$REPO/.git" ]; then
  [ -z "$(git -C "$REPO" status --porcelain --untracked-files=no)" ] || fail "$REPO has local changes; commit or discard them first"
  git -C "$REPO" fetch -q "$BUNDLE" "refs/heads/$BRANCH"
  git -C "$REPO" checkout -q "$BRANCH" 2>/dev/null || git -C "$REPO" checkout -q -b "$BRANCH" FETCH_HEAD
  git -C "$REPO" merge -q --ff-only FETCH_HEAD || fail "$REPO has its own commits on $BRANCH; cannot update it automatically"
else
  [ ! -e "$REPO" ] || fail "$REPO exists but is not a git repository; move it away first"
  git clone -q -b "$BRANCH" "$BUNDLE" "$REPO"
fi
[ -z "$ORIGIN" ] || git -C "$REPO" remote set-url origin "$ORIGIN"
HAVE="$(git -C "$REPO" rev-parse HEAD)"
if [ -n "$COMMIT" ] && [ "$HAVE" != "$COMMIT" ]; then fail "got commit ${HAVE:0:7}, the hub has ${COMMIT:0:7}"; fi
echo "code ready in $REPO at commit ${HAVE:0:7}"

say "4/5  Build the Python environment (a few minutes, about 500 MB)"
if [ "${SKIP_BOOTSTRAP:-0}" = "1" ]; then echo "skipped (SKIP_BOOTSTRAP=1)"; else bash "$REPO/testbed/bootstrap.sh"; fi

say "5/5  Report to the hub and test the connection to every other laptop"
if [ "${SKIP_JOIN:-0}" = "1" ]; then echo "skipped (SKIP_JOIN=1)"; exit 0; fi
exec "$HOME/venv-dfps/bin/python" "$REPO/testbed/connect.py" join --hub "$BASE" --token "$TOKEN"
