#!/usr/bin/env bash
# Build the Python environment on a testbed machine (no sudo, changes no system setting).
# Run from the repository root after `git clone`:   bash testbed/bootstrap.sh
# The venv path is the same on every machine (~/venv-dfps) so scripts and docs can refer to it.
set -euo pipefail
cd "$(dirname "$0")/.."

for tool in git python3; do
  command -v "$tool" >/dev/null || { echo "missing: $tool (see testbed/SETUP.md, part A)"; exit 1; }
done
python3 -c 'import venv, ensurepip' 2>/dev/null || { echo "missing: python3-venv (sudo apt install python3-venv)"; exit 1; }

VENV="$HOME/venv-dfps"
[ -d "$VENV" ] || python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install --quiet --upgrade pip
"$VENV/bin/python" -m pip install --quiet -r testbed/requirements.txt
echo "environment ready: $VENV  (python $("$VENV/bin/python" -V | cut -d' ' -f2), numpy $("$VENV/bin/python" -c 'import numpy; print(numpy.__version__)'))"

echo "---- preflight (agent role; settings are WARN until you have applied SETUP.md Part 2)"
"$VENV/bin/python" testbed/preflight.py report --role agent || true
