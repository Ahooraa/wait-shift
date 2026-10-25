---
title: "Decision rules for workflow-aware improvements (written before the stress pilot results)"
type: synthesis
created: 2026-10-25
updated: 2026-10-25
tags: [workflow-awareness, pre-registration, stress-pilot, decision-rules]
sources:
  - "[[zolfaghari-2025-dynamic-function-placement]]"
  - "[[jia-2025-faaspr]]"
  - "[[gunasekaran-2020-fifer]]"
status: draft
author: llm
bibliography: ../../output/bibtex/references.bib
---

# Decision rules, fixed before the pilot results

Written 2026-10-25, with no run of `output/data-analysis/workflow_stress.py` finished (0 of 144). One earlier look exists and is declared here: a single short diagnostic run (ours, Azure, 70% load, seed 1, 130 s window; 19 tail requests) showed local edges falling from 38.6% planned to 17.7% executed, 66% of edges fractured, 41% of the wait on tasks off the realised critical path, and a join gap of 10 s. These rules were chosen after seeing that run, so they are not blind with respect to it; they ARE fixed before any full-length pilot result.

Source of every quantity: the `diag` block of each pilot run (`dfps/diagnostics.py`), tail = requests at or above the 99th percentile of sojourn, full-length runs, controller `ours`. Scenario groups: mix 70%, mix 85%, chain12, layered12, wide16 (each with data scales as in the script).

## What counts as a reason to build

| Candidate | Build only if | Why this threshold |
|---|---|---|
| **R1 Re-bind the unstarted descendants of a moved task** | at data scale k = 10, the tail's mean extra first-hop transfer (`tail_extra_first_hop`) is at least 5% of the tail sojourn in at least 3 of the 5 scenario groups | this is the part of the fracture cost the rule can recover; below 5% the best possible gain is inside the noise of a P99 comparison (about 2%) |
| **R2 Slack-aware queue ordering** | in the tail, wait on tasks off the critical path is at least 30% of the tail's total wait (`tail_wait_off_path` / (`tail_wait_off_path` + `tail_wait_on_path`)) in at least 3 of 5 groups, at k = 1 AND k = 10 | reordering can only help the wait that sits off the path, and only if there is enough of it |
| **R3 Critical-path-weighted placement** | the random-placement stack (`kstack`) is at least 10% worse than the stack with our placement (`stack`) in P99 at k = 10 in at least 3 of 5 groups | if placement does not matter for P99 at all, weighting it cannot |

If none holds, no new mechanism is built, and the finding is the scaling result itself.

## What counts as success for anything built

On the 18 development cases (Azure and Huawei, 50/70/85%, seeds 1-3) against the unchanged controller: P99 better by at least 3% with a bootstrap interval of the per-case log ratio excluding zero; not worse than 1% in the same comparison at k = 1; cold starts not more than 20% higher. Then one confirmation on fresh seeds (11 and up). Summary statistic for noisy ratios: median per-case ratio and ratio of geometric means, not the mean of (x - ref) / x.

## Time limits

The instrumentation check is finished (sums verified, trace on or off checked below). The pilot is not delayed by any diagnostic change; further trace additions go into a follow-up run.

## Novelty check recorded 2026-10-25 (web search, abstract level)

Slack-aware and critical-path-aware ordering is published: Archipelago (shortest remaining slack first, extended to DAGs by recomputing slack after each predecessor), GrandSLAm (reorders requests with low computational slack), Fifer (distributes the slack over stages), Llama (dynamic slack over DAG paths), the EDF versus shortest-remaining-slack-first study for serverless DAGs at the edge (EdgeSys 2022), METIS (SoCC 2025, critical-path prioritisation at the OS level). R2 would therefore not be a new idea; at most a measured application inside a move-based controller under a fixed container budget. Re-binding (R1) has ClusterFlow as its nearest precedent (see [[baseline-matrix]]).

## Evaluation of the rules on the partial pilot (25 Oct, 87 of 144 runs; controller `ours`, tail = slowest 1%)
Data scale k = 10 is complete for all five groups; k = 1 lacks mix 70% so far.

| Group (k = 10) | extra first-hop transfer / tail sojourn (R1, needs >= 5%) | off-critical-path share of tail wait (R2, needs >= 30%) |
|---|---|---|
| chain12 | 8.8% | 0.0% |
| layered12 | -1.4% | 41.7% |
| mix 70% | 4.2% | 38.3% |
| mix 85% | 0.5% | 39.2% |
| wide16 | -8.3% | 51.3% |
| groups meeting the threshold | **1 of 5: R1 does not fire** | **4 of 5 at k = 10, 3 of 4 so far at k = 1: R2 fires** |

R3 (random-placement stack at least 10% worse than the stack with our placement at k = 10): fires in every group (about 50% worse in mix 70%), but the random-placement stack also re-randomises the layout every minute (about 8,500 cold starts against about 1,300), so this measures churn as much as data-obliviousness and is not a clean test of critical-path placement.
Consequence: re-binding of descendants is NOT built (fracture exists, local edges fall from 47% to 26% in mix 70%, but its first-hop transfer cost is small against the tail). Slack-aware ordering passes its threshold but has published precedents (see above). Final numbers to be recomputed when the pilot completes.

## Pre-registered thresholds for the two diagnostics of 25 Oct (written before any full-length run; smoke tests only confirmed the scripts run), revised after a review caught three readability risks

### D1 -- layout staleness probe (output/data-analysis/staleness_probe.py)
Logs, every move tick, FOUR series: count mismatch (sizing only, `_staleness`), placement mismatch (a no-solve lower bound on
locality staleness, `_placement_mismatch`), backlog (a MEAN-ish loss proxy), and the 95th percentile of current queue lengths
(a TAIL loss proxy, `_queue_tail`) -- added because this system's mean and P99 diverge (the no-moves pair: routing improved
the mean 23% while P99 stayed 7.9x worse), so a trigger tuned to backlog could do nothing for P99. Six development cases,
50/70/85% load, Azure + Huawei.

Build an event-triggered re-layout (fire on mismatch crossing a threshold, not a fixed clock) only if ALL THREE hold:
1. **Bursty, not steady drift, read by FAMILY, not an absolute bar:** Azure (F1) is the known-steadier trace, Huawei (F2) the
   known-bursty one; CV of within-epoch increments must be notably higher for F2 than F1 (the three-vs-three cases already
   give this comparison for free). An absolute "CV > 1" bar has no reference point and is not used.
2. **Mismatch predicts loss -- state which proxy, backlog or tail, supports it, and use only that one downstream:**
   corr(mismatch, next-tick backlog) > 0.3 OR corr(mismatch, next-tick tail) > 0.3, in at least 4 of 6 cases, for the count OR
   placement mismatch series. If only backlog correlates, a trigger may be built but is not justified as a P99 fix.
3. **Cold starts are a real cost to save -- the exact numbers (hard50 six cases, knowledge/_meta/log.md 23 Oct):** 60 s =
   1,409 cold starts; 30 s = 1,526 (+8.3%, +117) for P99 +9.2% (+1 to +19); 15 s = 1,647 (+16.9%, +238) for P99 +9.4% (-2 to
   +21, no further gain over 30 s). The trigger's target is matching the 30 s P99 gain for FEWER than 1,526 cold starts --
   not merely beating 60 s's 1,409. If a threshold trigger cannot be shown offline (replay of the logged series) to
   approximate this, do not build it.
If condition 1 or 2 fails, the fixed 60 s period is already close to right and the direction is closed.

**Calibration caveat (`_placement_mismatch` is a LOWER bound):** it ignores cross-function capacity contention (a real
re-solve would fight over the same good node), so a FAILED correlation for the placement series alone is inconclusive, not
necessarily a true null -- the instrument may be too weak to see a real effect. `staleness_probe.py calibrate` checks this
once: one case, 15 points, correlating the cheap proxy against `_true_placement_mismatch` (a real solve via
`queue_aware_placement` + `placement_cost`, both new in dfps/controllers.py and dfps/o3s.py). Run `calibrate` before
trusting a null on the placement-mismatch series specifically; the count-mismatch series needs no such calibration (it is
computed exactly, not approximated).

4-point pilot of `calibrate` (25 Oct, F1 70% s1, 150 s window, too few points for a correlation verdict): proxy 0.16-0.38,
true -0.23 to +0.34, same order of magnitude, no NaN/inf -- the mechanics work. `_true_placement_mismatch`'s "fresh" layout
is itself a greedy rebuild (`queue_aware_placement` from scratch), not a guaranteed optimum, so `true` can be negative (the
live layout scored cheaper than the fresh greedy solve); read a near-zero or negative `true` as "live is about as good as a
fresh greedy rebuild", not as "no staleness". The real 15-point, full-length `calibrate` run is queued.

### D2 -- data-aware planning ablation (output/data-analysis/affinity_probe.py)
NOT a clean placement-objective ablation (see the script's docstring): it changes the plans the move rule is priced against,
so it ablates planning as a whole.

- **Current term is load-bearing, no further work:** ours_noaff >= 3% worse at k = 10 (near the 9-14% re-binding/co-location
  ceilings bounds_run.py measured) AND <= 1% worse at k = 1, in a majority of scenarios.
- **Direction reopens with evidence (the result to watch for):** ours_noaff is SMALL (well under the ceiling, e.g. 2-4%)
  worse at k = 10 despite the 9-14% ceiling existing -- the current heuristic is capturing little of the available headroom.
  This is the only outcome that would justify building a better data-aware placement term.
- **Direction closes cleanly:** flat (<1%) at both k = 1 and k = 10.

Also reported per cell: moves/request (`n_moved / n_completed`) for `ours` vs `ours_noaff`. If affinity-off changes which
moves the finish-time rule accepts (a different move count), a P99 difference could be move-mediated rather than
planning-mediated, and that must be said explicitly rather than attributed to placement alone.

Smoke-test numbers from either script are NOT findings and must not be read as preliminary results; they only confirm the
code runs and produces plausible magnitudes.
