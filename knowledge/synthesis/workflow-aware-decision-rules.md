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

## D1 and D2 full-length results, applied against the pre-registered rules above (25 Oct)

### D1 verdict: event-triggered re-layout NOT built
- Criterion 1 (burstiness by family) PASSES: F2 (Huawei) CV > F1 (Azure) CV at every load (8.19 vs 4.75 at 50%, 4.76 vs 2.23 at 70%, 1.86 vs 1.59 at 85%; count-mismatch series).
- Criterion 2 (mismatch predicts loss) passes ONLY via backlog (mean-ish): corr(count or placement mismatch, backlog) > 0.3 in 4/6 cases. corr(mismatch, TAIL proxy -- p95 queue length, the one relevant to P99) > 0.3 in only 2/6, never above 0.47, and is near-zero or NEGATIVE at 85% load in both families (F1: -0.13/-0.41; F2: 0.02/0.07) -- the regime that matters most.
- Criterion 3 (cold-start saving over 30s, offline replay) NOT attempted.
- Since all three must hold and only #1 does cleanly, the trigger is not built. Finding: layout mismatch tracks congestion but not tail risk, consistent with this project's broader mean/tail divergence.
- Placement-mismatch calibration (15 points, full run): corr(proxy, true) = 0.22, below the 0.3 instrument-validity bar; true mismatch was negative in 13/15 samples (live layout about as good as a fresh greedy rebuild, or the fresh rebuild is simply not a strong enough baseline -- both readings are open).

### D2 verdict: mixed, no bucket fires cleanly, not closed
| Scenario | k | ours P99 | noaff P99 | change | cold ours/noaff | mv/req ours/noaff |
|---|---|---|---|---|---|---|
| mix 70% | 1 | 120.6 | 122.4 | +1.5% | 1627/1617 | 3.05/3.18 |
| mix 70% | 10 | 242.4 | 266.5 | +10.0% | 1595/1592 | 1.55/1.68 |
| mix 85% | 1 | 157.8 | 160.7 | +1.8% | 1551/1562 | 3.59/3.68 |
| mix 85% | 10 | 346.3 | 334.6 | -3.4% | 1458/1462 | 1.92/2.11 |
| chain12 | 1 | 231.7 | 238.7 | +3.0% | 1109/1100 | 7.04/7.18 |
| chain12 | 10 | 484.5 | 491.2 | +1.4% | 1042/1067 | 3.85/4.17 |

mix-70% k=10 reads "load-bearing" (large loss without affinity); mix-85% k=10 is NEGATIVE (noaff better); chain12 k=10 is the pre-registered "interesting middle row" (+1.4% loss despite the 10.6% re-binding ceiling measured for that exact scenario in bounds_run.py -- the current heuristic captures little of a real, large ceiling there). Cold starts flat in every row (confirms this is not churn-mediated); moves/request consistently higher without affinity in every row (planning changes which moves the finish-time rule accepts, so part of any P99 difference is move-mediated, as pre-registered). Single seed per scenario -- noisy, especially the negative mix-85% row. Not closed; chain12 is the one cell worth a second seed before any decision.

## Bounds table complete, all 6 scenarios (25 Oct, bounds_run.py; layered12 took ~4.7h wall time, the densest shape)

| Scenario | k | base P99 | slack (conservative/generous) | perfect co-location | perfect re-binding |
|---|---|---|---|---|---|
| chain12 | 10 | 485 | -4.9% / -11.4% | -13.9% | -10.6% |
| layered12 | 10 | 1016 | -0.7% / -2.7% | -0.9% | -0.4% |
| mix (Azure) | 10 | 346 | -6.9% / -22.0% | -9.2% | -7.4% |
| mix (Huawei) | 10 | 242 | -4.8% / -12.0% | -9.1% | -7.0% |
| wide16 | 10 | 363 | -2.4% / -12.6% | -2.5% | -2.1% |
| mix (Azure) | 1 | 158 | -1.8% / -8.6% | -2.8% | -2.7% |

All six replay exactly (error 0.0). Pattern: ceilings are large for simple, serial structure (chain12) and shrink toward
zero for wide, dense structure (layered12 has the SMALLEST ceilings of any shape, smaller even than wide16, despite having
the densest cross-layer edges and the largest off-critical-path wait share measured in the earlier diagnostic, 41.7%). A
dense DAG has many parallel near-critical paths; fixing the one nominal critical path barely moves P99 because the tail is
set by the slowest of several comparable paths, not a single fixable one. This reinforces the R1/R2/D1/D2 pattern: single
workflow-aware fixes have the least room exactly where a workflow has the most structure to exploit.

## P3 scaling probe: Delta-gap(k) invariance, pre-registered before the fine sweep (25 Oct)

**Starting point, zero new runs** (results/envelope/*.json, k in {1,10}, 4 loads, both families, both controllers):
Delta-gap(k=1->10) = gap(k=10) - gap(k=1) clusters at 30-43 points for every (fam, load) cell at <=85% load (F1: 33.9,
38.5, 39.0; F2: 42.8, 39.5, 29.6), while raw gap(k=1) alone ranges 7.6-28.7% over the same cells -- the INCREMENT looks
family/load-invariant even though the baseline is not. At 92% load this breaks in opposite directions per family: F1 drops
to +17.5, F2 goes to -14.4 (negative -- more data makes the gap SMALLER for Huawei at 92%). This is a different mechanism
(the stack's relative move-rule collapse near saturation, already established in the envelope result) and is excluded from
this fit by design, reported as its own regime.

tau (measured transfer share of the critical path, diag["all_transfer"]/diag["all_soj"], already stored by every envelope
run via summarize()) correlates with Delta-gap at r=0.249 on those 6 existing <=85%-load points; 95% CI (Fisher z,
n=6) = [-0.71, 0.88] -- indistinguishable from zero. tau is an EXPLORATORY secondary variable in this probe, not the
mechanism claim: the primary claim is the k-invariance of Delta-gap itself, true or not regardless of what tau does. (This
is the third time in the project a mechanistic variable looked promising at coarse resolution; the discipline that killed
the other six candidates applies here too -- see [[novelty-register]].)

**Design** (output/data-analysis/p3_scaling_probe.py), rho=0.85 only, to isolate k from load:
- fine sweep: k in {0.5, 2, 3, 5, 7} x {F1,F2} x {ours,stack}, seed 1 = 20 runs
- noise check: k in {3, 5} x {F1,F2} x {ours,stack}, seed 2 = 8 runs
- 28 runs total; k=1 and k=10 at rho=0.85 read from the existing envelope grid, not re-run.

**Dependent variable:** Delta-gap(k) = gap(k) - gap(k=1), fit regime = rho<=0.85 only. 92% load reported as a separate
collapse regime with its own sentence, not included in the fit.

**Independent variables:** k (primary, operational). tau (secondary, exploratory -- see above).

**Forms to compare** (committed now): linear, log, power-law, saturating-exponential. Fit on F1, validate on F2 (and
reverse); report held-out residual, not R^2 alone (R^2 across forms with different parameter counts is not a valid
comparison, and 6-7 single-seed points cannot identify a functional form by R^2 regardless).

**Success:** Delta-gap(k) is monotone in k within the fit regime, and the F1-fit predicts F2's Delta-gap within the
seed-1-vs-seed-2 noise estimate (at k=3 and k=5).

**Failure:** Delta-gap(k) is flat within that noise estimate -> report as a null: "no detectable state-size dependence
beyond the k=1 baseline," not a law.

**Mechanism test (exploratory, not required for success):** does Delta-tau track Delta-gap once the finer points are in?
If not, the honest conclusion is "the increment is universal in k but not explained by transfer share," which points at
the move rule's absolute-vs-relative behaviour (already established) as the explanation instead -- itself a result, not a
failure of the probe.

**Crossover (k=0.5 cell):** if gap at k=0.5 is still positive, report "the crossover lies below k=0.5 and is not located."
Do not extrapolate past the measured range.

**Caveats stated regardless of outcome:** single load (0.85) for the fine sweep; single seed except k=3,5; 92% excluded
by design as a separate regime; the shape rests on single-seed points outside the two noise-check k's.

## P3 scaling probe: result (25 Oct, 28 runs, rho=0.85)

Full table (output/data-analysis/p3_scaling_probe.py, results/p3_scaling/):

| fam | k | gap% | Delta-gap | tau (ours) | Delta-tau |
|---|---|---|---|---|---|
| F1 | 0.5 | 24.2 | +10.5 | 0.043 | -0.024 |
| F1 | 1   | 13.6 | 0     | 0.067 | 0 |
| F1 | 2   | 28.6 | +15.0 | 0.098 | +0.031 |
| F1 | 3   | 36.2 | +22.5 | 0.122 | +0.055 |
| F1 | 5   | 43.0 | +29.4 | 0.151 | +0.084 |
| F1 | 7   | 48.9 | +35.3 | 0.173 | +0.105 |
| F1 | 10  | 52.6 | +39.0 | 0.210 | +0.142 |
| F2 | 0.5 | 31.3 | +2.6  | 0.038 | -0.022 |
| F2 | 1   | 28.7 | 0     | 0.061 | 0 |
| F2 | 2   | 29.2 | +0.5  | 0.085 | +0.025 |
| F2 | 3   | 33.8 | +5.2  | 0.106 | +0.045 |
| F2 | 5   | 38.2 | +9.6  | 0.132 | +0.071 |
| F2 | 7   | 41.8 | +13.1 | 0.147 | +0.087 |
| F2 | 10  | 58.2 | +29.6 | 0.173 | +0.113 |

Noise check (seed1 vs seed2 at k=3,5): |diff| = 2.2 (F1 k=3), 4.9 (F1 k=5), 10.3 (F2 k=3), 2.7 (F2 k=5) -> noise floor
~2-10 points, max 10.3.

**Check 1, monotonicity -- PASS for both.** F1 strictly monotone (10.5/15.0/22.5/29.4/35.3/39.0). F2 dips 2.6->0.5 from
k=0.5->2 (a 2.1-point wobble, inside the 10.3-point noise floor) then climbs monotonically. Both families: more state size
-> larger advantage, monotonically, within noise.

**Check 2, cross-family validation -- FAILS.** Family gap in Delta-gap at matched k: 7.9 (k=0.5), 14.5 (k=2), 17.3 (k=3),
19.8 (k=5), 22.2 (k=7), 9.4 (k=10) -- mostly well above the ~2-10 point noise floor. F1 (Azure) climbs earlier and faster
than F2 (Huawei); they converge only near the two extremes tested. The "family-invariant universal increment" read off the
coarse 2-point (k=1,10 only) data in the pre-registration's starting point does NOT survive once the curve is filled in --
that regularity was an artefact of having only two points per family.

**Mechanism check (exploratory, not required for success).** Within each family, Delta-tau tracks Delta-gap tightly:
r=0.979 (F1), r=0.837 (F2). But it does not unify the families: at matched Delta-tau ~ 0.085, F1's Delta-gap is 29.4 while
F2's is 13.1 -- a 2.2x difference at the same transfer-share increment. tau explains the within-family shape but not the
between-family magnitude; some other factor (plausibly the already-established absolute-vs-relative move-rule asymmetry,
or a Huawei-specific traffic effect, consistent with Phase 0 Check 1's earlier "mixed" finding) accounts for the family
gap, and this probe does not resolve which.

**Verdict:** a monotone, family-DEPENDENT empirical curve, not a universal law. Both families show increasing returns to
state size at rho=0.85, strongly correlated with transfer share within each family, but the rate of increase is not
family-invariant, so P3 is reported as two related but distinct curves (one per family) with a shared qualitative shape
(monotone, tau-correlated within family), not as a single predictive law. Weaker than the "best sentence" framing from
the design discussion, but a decisive, honest result rather than a null -- see [[novelty-register]].
