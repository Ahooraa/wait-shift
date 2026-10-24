---
title: "Post-G3 oracle-level ablations for the D1 mechanism (parked until after D2, D3 and G3)"
created: 2026-10-16
status: parked
author: llm (agreed with the user 2026-10-16)
---

# Post-G3 oracle-level ablations (D1 mechanism)

**When:** in the design step after G3 (Task 14 -> H4 / Task 15), only after D2 (incl. O2H) and D3 are analysed
and the user has made the G3 decision. Not part of the frozen D1-D3 grids; not run before then.

## Why (evidence so far)
- D1: all clairvoyant gain comes from O1+B* (anticipatory whole-placement switches on top of B*'s SA).
  P_TRUE (perfect forecasts fed into SA) and the reactive rate-change heuristic are worse than B*.
  Envelope headroom: F1 23.1% (median 20.8%), F2 42.2% (median 41.5%), F3 4.2%.
- D2: admission triples SLO-goodput, but the queue-threshold heuristic captures ~78% of it; O2H adds only
  ~20-28% beyond it (F1, partial F2).
- D2 capacity bound (`output/data-analysis/results/d2_capacity_bound.json`): offered work is only 0.8-1.3x
  total capacity over the window, yet O2H reaches only 15-31% of the pooled bound. The loss is capacity on the
  wrong functions during bursts (bottleneck x burst timing x deadlines), i.e. a placement-timing problem.

## Mechanism ideas
1. **Bottleneck-first switch targets:** hot functions get containers for util < ~0.8, the rest by affinity.
2. **Predicted-burst trigger:** change-point / trend detector; upstream workflow stages as early warning for
   downstream functions (stage-1 burst announces stage-2/3 bursts).
3. **Transient admission during switches:** threshold admission only during the cold-start dip / burst peak.
4. **Cost-aware switching:** switch iff predicted queueing saved > cold-start cost x containers moved.

## Ablations to run (oracle level, about 6-10 h total)
| ID | What | Scenarios | Question | Signal |
|---|---|---|---|---|
| A | O1+B* with bottleneck-first targets vs current affinity-greedy targets | D1 scenarios (F1-F3, 3 rho, seeds 1-10) | Does a better target raise the envelope headroom? | headroom clearly above 23% (F1) / 42% (F2) |
| B | O1+B* + queue-threshold admission vs HEUR alone and vs O2H | D2 overload scenarios | How much of D2's unexplained gap does re-placement recover beyond admission? | goodput above O2H |
| C | Offline: stage-1 burst as predictor of downstream function bursts | D1/D2 traces | Lead time and precision of the free workflow-internal forecast | lead >= one switch cost, precision useful |

Optional first: per-function, per-minute capacity bound with deadlines (about 15 min, no simulation) to split
the D2 gap into admission-reachable vs re-placement-only.

Related: [[bottleneck-register]], `knowledge/_meta/log.md` (2026-10-16 entries).
