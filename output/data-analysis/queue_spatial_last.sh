#!/usr/bin/env bash
# Queue (4 Nov 2026): the last two spatial tests start only after the baseline runs for the results table are done
# (Graph-Aware beta 1 on 18 CAP-W1 cases, Graph-Aware arm of the calibration test), then snapshot stability, then the move veto.
# Stops if any of those jobs left an .err file.
cd "$(dirname "$0")"
R=../../results
count() { ls "$R/$1"/*.json 2>/dev/null | grep -v smoke | wc -l; }
while true; do
  if ls "$R"/capW1_ga_b1/*.err "$R"/dispatch_calibration/*.err >/dev/null 2>&1; then
    echo "$(date) an upstream run failed (.err present) - not starting"; exit 1
  fi
  if [ "$(count capW1_ga_b1)" -ge 18 ] && [ "$(count dispatch_calibration)" -ge 9 ]; then break; fi
  sleep 300
done
echo "$(date) baselines done - starting snapshot stability"
python snapshot_stability.py run 3 || exit 1
if ls "$R"/snapshot_stability/*.err >/dev/null 2>&1; then echo "$(date) snapshot run failed - veto not started"; exit 1; fi
echo "$(date) starting move veto"
python move_veto.py run 3
echo "$(date) queue finished"
