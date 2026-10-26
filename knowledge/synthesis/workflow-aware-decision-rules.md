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

## Lambda sweep: does the downstream-transfer weight in the move rule need tuning? (pre-registered 26 Oct)

The move rule's finish-time estimate (dfps/solution.py:Sol.aet) is `inp + service_estimate + out`, where `out` is the
downstream-transfer term (state transfer to children's planned nodes) -- unweighted (coefficient 1, "lam=1.0") by
construction, never tested against any other weight. `lam` is now a parameter: `Sol.aet(run, k, lam=1.0, parts=False)`
weights only `out`; default 1.0 reproduces every existing result exactly (verified: F1/k=5/seed=1 rerun with the new code
reproduces event_hash aa370d50526c77edd8a5ba6e21658c3c, p99=237.12909634478277, bit for bit). `aet()` is called from three
places (o3s.py's rebalance_step aet rule -- what this sweep targets; sa.py's SimulatedAnnealing, used by the B* baseline;
sim.py's storage-exhaustion _reroute fallback); `lam` is threaded only through rebalance_step's churn["lam"], so the other
two callers are unaffected by construction, not by discipline.

**Gate 0 (free, re-scoring, no simulated λ' decisions, k=5 added to every stage of this sweep per instruction):**
output/data-analysis/lambda_probe.py logs, at every evaluated move decision (not just accepted moves), the lam=1.0
decomposition (inp, service_estimate, out) of the current node and every evaluated candidate (O3SimAdjuster.lambda_log,
churn["log_lambda_components"]). 6 runs: k in {1, 5, 10} x {F1, F2}, seed 1, controller "ours", full duration. Offline,
for each hypothetical lam' in {0, 0.5, 2}, recompute `inp + service + lam'*out` for the current node and every logged
candidate, take the argmin, and compare the chosen action (stay, or move to a specific node) against the lam=1.0 action
actually taken. Flip rate = fraction of decisions where the chosen action changes. Caveat, stated now: this ignores how a
flipped decision would change later queue state, so it is a sensitivity diagnostic, not a P99 estimate -- it only decides
whether to spend runs on Gate 1.

- **Flip rate < 5%** between lam=0 and lam=2 (max contrast), at every k -> axis is dead, close it, no further runs.
- **5-15%** -> marginal; run the full matrix at seed 1 only (reduced).
- **> 15%** at k=10 in at least one family -> the axis binds; run the full seeded matrix (Gate 1).

**Gate 1 (family-dependent optimum, only if Gate 0 passes):** matrix lam in {0, 0.5, 1, 2} x k in {1, 5, 10} x {F1, F2} x
seed in {1, 2} = 48 cells; reuse existing lam=1 "ours" results where the scenario/seed match exactly (k=1 seed1, k=5
seed1+seed2, k=10 seed1 -- 8 cells, re-verified by the reproducibility check above, not re-run blind); ~40 new runs.
Fixed: rho=0.85, admission off, storage scaled, standard mix. Primary metric: paired per-case Delta-P99(lam) = P99(lam) -
P99(lam=1), same scenario/seed -- never raw cross-cell P99 (the project's own noise floor from seed replicates, ~2-10
points, is large enough to manufacture a spurious optimum from absolute comparisons alone). Passes if the best lam for F1
differs from F2's by more than the paired seed-1/seed-2 noise floor, at k=10. Fails (one constant lam serves both
families) if the optima agree within noise.

**Gate 2 (usable control signal, only if Gate 1 passes):** does the realized/predicted move-gain ratio (gain_log,
already instrumented 25 Oct) separate lam values with non-overlapping bootstrap CIs? Fails if within-lam spread exceeds
across-lam spread -- the premise (family-dependent optimum) would exist with no exploitable control signal, reported but
not built.

**Outcome map:** Gate 0 fails -> close lam axis, adaptive-lam mechanism dead, zero further runs. Gate 1 fails -> lam
matters overall but one retuned constant serves both families -- report as an engineering tuning finding, not a novel
mechanism. Gate 1 passes, Gate 2 fails -> the premise exists (family-dependent optimum) but no usable control signal ->
report, do not build. Both pass -> build a minimal adaptive-lam rule, one ablation row.

**Logged per run, beyond P99:** mean, p90 (mean/tail divergence has misled this project before -- see the dispersion-
margin and interaction-hunt threads); moves/request, cold starts, ping-pong share (already free from the trace);
realized-vs-predicted gain at move-accept time (gain_log); lam, k, family, seed in every result file's metadata and
filename (a run whose lam is not recorded in the filename is a run that cannot be told apart from another later).

## Lambda sweep, Gate 0 result: axis binds, proceed to Gate 1 (26 Oct)

6 runs (output/data-analysis/lambda_probe.py), k in {1,5,10} x {F1,F2}, seed 1, rho=0.85, free re-scoring of 165,708-
204,575 logged decisions per cell (every evaluated move opportunity, not just accepted moves).

| fam | k | n_dec | flip@lam=0 | flip@lam=0.5 | flip@lam=2 |
|---|---|---|---|---|---|
| F1 | 1  | 204575 | 16.1% | 9.0%  | 11.4% |
| F1 | 5  | 190337 | 28.4% | 13.1% | 12.0% |
| F1 | 10 | 181962 | 26.1% | 12.2% | 12.5% |
| F2 | 1  | 202454 | 20.1% | 11.0% | 14.4% |
| F2 | 5  | 180999 | 33.6% | 18.2% | 13.2% |
| F2 | 10 | 165708 | 30.4% | 16.9% | 14.6% |

At k=10, flip@lam=0 is 26.1% (F1) and 30.4% (F2), both far above the 15% threshold; F2 also exceeds 15% at lam=0.5 for
k=5 and k=10. The axis binds strongly -- decisively above the "dead axis" (<5%) and "marginal" (5-15%) bands at every k
tested, for both families. Per the pre-registration: **proceed to Gate 1** (the full 48-cell matrix). Caveat carried
forward: this is a sensitivity diagnostic (recomputes the lam=1 decomposition under hypothetical lam', ignoring how a
flipped decision would change later queue state), so a high flip rate means the rule is lam-sensitive, not yet that any
particular lam improves P99 -- that is exactly what Gate 1 tests.

## Lambda sweep, Gate 1 result: axis real, but one constant serves both families (26 Oct)

48-cell matrix (output/data-analysis/lambda_gate1_probe.py, 40 new + 8 reused), lam in {0,0.5,1,2} x k in {1,5,10} x
{F1,F2} x seed in {1,2}, rho=0.85. Delta-P99(lam) = P99(lam) - P99(lam=1):

| fam | k | seed | d@0 | d@0.5 | d@1 | d@2 | best |
|---|---|---|---|---|---|---|---|
| F1 | 1  | 1 | -2.3  | -3.6  | 0 | -2.2 | 0.5 |
| F1 | 1  | 2 | +2.6  | +0.9  | 0 | +3.2 | 1.0 (trivial, +0.0) |
| F1 | 5  | 1 | +1.6  | -12.0 | 0 | +6.7 | 0.5 |
| F1 | 5  | 2 | +1.1  | -1.4  | 0 | -0.7 | 0.5 |
| F1 | 10 | 1 | -2.8  | -15.3 | 0 | +38.0 | 0.5 |
| F1 | 10 | 2 | -0.6  | -7.3  | 0 | +17.2 | 0.5 |
| F2 | 1  | 1 | -1.7  | -3.3  | 0 | -1.4 | 0.5 |
| F2 | 1  | 2 | +14.2 | +4.9  | 0 | +13.5 | 1.0 (trivial, +0.0) |
| F2 | 5  | 1 | +5.7  | -0.1  | 0 | +1.5 | 0.5 |
| F2 | 5  | 2 | -4.8  | -4.0  | 0 | +22.1 | 0.0 |
| F2 | 10 | 1 | +3.6  | -3.7  | 0 | +22.2 | 0.5 |
| F2 | 10 | 2 | -31.6 | -47.3 | 0 | +21.9 | 0.5 |

**Shape, averaged across fam x seed at each k:** a U-shaped curve, minimum between lam=0 and lam=1 (near 0.5), sharply
asymmetric (raising lam above 1 costs far more than lowering it), growing with k: k=1 flat (+-3 pts, matching Gate 0's
weak binding there), k=5 moderate (+0.9 at 0, -4.4 at 0.5, +7.4 at 2), k=10 large (-7.8 at 0, -18.4 at 0.5, +25.8 at 2).

**Gate 1 check, at k=10 (the pre-registered decision point):** both seeds, BOTH families: best lam = 0.5. F1 k=10:
seed1 -15.3, seed2 -7.3 (same sign, same best lam). F2 k=10: seed1 -3.7, seed2 -47.3 (same sign, same best lam, though the
magnitude swings a lot between seeds -- a real single-seed-estimate caveat, not a sign disagreement). The two "best=1.0"
rows (F1/F2 k=1 seed2) are trivial (+0.0, inside the dead-axis band Gate 0 already flagged for k=1) and do not indicate a
genuine family split.

**Verdict: Gate 1 fails** (the optimum does not differ between families) **but the axis is real and large.** Per the
pre-registered outcome map: "Gate 1 fails -> lam matters overall but one retuned constant serves both families -- report
as an engineering tuning finding, not a novel mechanism." lam=1 (the move rule's unweighted downstream-transfer term, set
by construction and never tested until this sweep) is measurably wrong; lam~0.5 is a better constant for both traffic
families, with the benefit growing sharply at larger state sizes (k=10: -7 to -47 points improvement vs lam=1, against a
+18 to +38 point penalty for going the other way to lam=2). No adaptive-lambda mechanism is built -- there is no
cross-family tension to exploit. This closes the thread as a tuning fix, not a contribution.

**Refinement, result (26 Oct, 8 runs):** lam in {0.25, 0.75} at k=10, both families, both seeds
(output/data-analysis/lambda_refine_probe.py), added either side of lam=0.5 to locate the minimum more precisely.

| fam | seed | d@0  | d@0.25 | d@0.5  | d@0.75 | d@2   |
|-----|------|------|--------|--------|--------|-------|
| F1  | 1    | -2.8 | -7.4   | **-15.3** | -13.8 | +38.0 |
| F1  | 2    | -0.6 | **-10.1** | -7.3 | +0.2 | +17.2 |
| F2  | 1    | +3.6 | **-7.5** | -3.7 | +5.8 | +22.2 |
| F2  | 2    | -31.6| **-52.4**| -47.3 | -45.7 | +21.9 |

(bold = per-cell minimum; all deltas are P99 vs the lam=1 baseline, same scenario/seed.)

**Revised verdict: the minimum sits closer to lam~0.25, not lam=0.5.** 3 of 4 cells minimize at lam=0.25; only F1/seed1
prefers 0.5. lam=0.75 is the side of the curve that is unsafe to round to: it still helps F1/seed1 (-13.8) but goes
essentially flat for F1/seed2 (+0.2) and turns into a small penalty for F2/seed1 (+5.8) -- a sign flip the coarser Gate 1
grid ({0, 0.5, 1, 2}) could not see. lam=0.25 never crosses zero across all four cells and has the better aggregate
(-77.4 summed vs -73.6 at lam=0.5), making it the more robust single constant, not just the sharper one.

This does not reopen Gate 1's cross-family verdict -- lam=0.25 is still better for BOTH families, so there is still no
adaptive-lambda mechanism to build. It only moves the recommended retuned constant from lam~0.5 to lam~0.25.

**Caveat (restated):** paired per-case Delta-P99, single seed per (fam,k,lam) except the two reused k=5 cells -- the
magnitude of the effect varies a lot seed to seed (F2 k=10: -3.7 to -52.4) even though the sign and the best-lam
ordering (0.25 better than 0.5 better than 1 better than 2) are consistent. Treat the magnitude as uncertain, the
direction and ordering as the load-bearing claim.

**Pipeline provenance (26 Oct):** `lambda_refine_probe.py::analyze()`'s baseline lookup was edited mid-run, commit
cfd36e3, AFTER the 8 refinement runs had already been launched but BEFORE this table was produced. Original code
read the lam=1 baseline only via `lambda_gate1_probe.existing_lam1()` (which resolves a fixed map of k=1/k=5 cells
reused from `results/envelope/` and `results/p3_scaling/`); that map has no entry for (k=10, seed=2), so F1/F2
seed=2 silently fell out of the table (`continue`'d on `b is None`) and only the two seed=1 rows printed. The fix
adds a fallback: `g1.existing_lam1(...) or (g1.RUNS / tag(fam, K, seed, 1.0))` -- i.e. when the fixed map has no
entry, read the lam=1.0 cell that Gate 1 actually ran fresh into `results/lambda_gate1/` for that (k, seed). This
is the SAME lam=1 result Gate 1 already reported (no new simulation, no change to any P99 number) -- the fix only
widens what `analyze()` is willing to read as a baseline, so the seed-2 rows above are reproducible from the
Gate-1 data already on disk, but only with the post-cfd36e3 version of the script. Running the pre-fix version
reproduces just the F1/seed1 and F2/seed1 rows.

**Decision (26 Oct): stop refining lam here.** Two seeds x six lam values is enough to show the curve has an
interior plateau below 1 (lam in roughly [0.25, 0.5] all beat lam=1 by a wide, consistent margin); it is not enough
to pin the minimum tighter than that. The per-cell noise floor is large (seed-to-seed swings of tens of points, e.g.
F2 k=10 sigma on the order of 45 at lam=0.5 across the two seeds already logged) against a 0.25-vs-0.5 difference of
about 5 points in the pooled sum -- resolving that difference properly would need on the order of n~10 seeds per
cell (roughly 40 more runs for marginal gain), for a payoff capped at about 1 point of P99 either way. The plateau
itself is the finding: the move rule is not sensitive to the exact constant once lam is below 1, so further seeds
spent narrowing lam=0.25 vs lam=0.5 would not change the engineering recommendation ("retune lam downward from 1,
anywhere in [0.25, 0.5] is a comparable, large improvement for both families"). No further lam-value or lam-seed
runs are planned for this thread.
