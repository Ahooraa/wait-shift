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
moves the AET rule accepts (a different move count), a P99 difference could be move-mediated rather than
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

mix-70% k=10 reads "load-bearing" (large loss without affinity); mix-85% k=10 is NEGATIVE (noaff better); chain12 k=10 is the pre-registered "interesting middle row" (+1.4% loss despite the 10.6% re-binding ceiling measured for that exact scenario in bounds_run.py -- the current heuristic captures little of a real, large ceiling there). Cold starts flat in every row (confirms this is not churn-mediated); moves/request consistently higher without affinity in every row (planning changes which moves the AET rule accepts, so part of any P99 difference is move-mediated, as pre-registered). Single seed per scenario -- noisy, especially the negative mix-85% row. Not closed; chain12 is the one cell worth a second seed before any decision.

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

The move rule's AET estimate (dfps/solution.py:Sol.aet) is `inp + service_estimate + out`, where `out` is the
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

**Decision (26 Oct), REVERSED (26 Oct, same day, user):** the stop-refining call below was overturned -- the user
asked to run the additional-seeds experiment despite the cost/payoff argument. Proceeding with seeds 3-10 at k=10,
all 6 lam values, both families (output/data-analysis/lambda_seeds_probe.py; see result entry below once it lands).
The reasoning that follows was the basis for the (overturned) stop decision and is kept for the record.

**Original decision (26 Oct, superseded above): stop refining lam here.** Two seeds x six lam values is enough to show the curve has an
interior plateau below 1 (lam in roughly [0.25, 0.5] all beat lam=1 by a wide, consistent margin); it is not enough
to pin the minimum tighter than that. The per-cell noise floor is large (seed-to-seed swings of tens of points, e.g.
F2 k=10 sigma on the order of 45 at lam=0.5 across the two seeds already logged) against a 0.25-vs-0.5 difference of
about 5 points in the pooled sum -- resolving that difference properly would need on the order of n~10 seeds per
cell (roughly 40 more runs for marginal gain), for a payoff capped at about 1 point of P99 either way. The plateau
itself is the finding: the move rule is not sensitive to the exact constant once lam is below 1, so further seeds
spent narrowing lam=0.25 vs lam=0.5 would not change the engineering recommendation ("retune lam downward from 1,
anywhere in [0.25, 0.5] is a comparable, large improvement for both families"). No further lam-value or lam-seed
runs are planned for this thread.

## Placement-objective additions: what does a more workflow-aware placement buy? (pre-registered 1 Nov 2026, before any run)

**Question (user, 1 Nov 2026).** Our placement (`queue_aware_placement`, frozen settings) sees only (a) request origins for root tasks and (b) DIRECT edges, with state volume as weight, summed per function pair over all workflows; hop time uses the cluster-wide mean state size; the waiting term is off. It does not see: functions two steps away; joins and forks (parallel branches that must meet or start together); which edges lie on a workflow's critical path; each function's own state sizes when functions compete for good nodes. The user expects headroom there. This is the controlled test of how much each addition gives, one at a time and all together.

**What we already know, stated before running (so the result cannot be read as a surprise either way).** Offline ceilings for perfect co-location (`bounds_run.py`, table above): mix k=1 -2.8%; mix k=10 -9.1% to -9.2%; chain12 k=10 -13.9%; layered12 k=10 -0.9%; wide16 k=10 -2.5%. Dropping the partner term altogether (D2 above) cost +1.5% to +3.0% at k=1 and mixed results at k=10. Placement quality with moves uncapped: no detectable P99 effect (paired +0.2%). The waiting term: +0.9% on the 18 development cases. Prior expectation: at standard state size no addition can exceed about 3% (the noise floor of a 3-seed comparison, see run-noise-floor); only the large-state and structure-heavy cases can show more. We run it anyway because the ceilings are offline replays, not what a built rule achieves.

**Variants.** Each is an option of the placement cost, default off; V0 (all off) must reproduce the current controller bit-for-bit (P99 and event hash on one case before any variant run). Constants are fixed here and are not tuned.

| Id | Addition | Definition (per workflow w, rate r_w, edge (u,v) with state size s_uv, tasks of function types a, b, c) | Targets |
|---|---|---|---|
| V1 | own state size in hop time | seconds per hop for function f = delay + (rate-weighted mean size of the states f sends or receives, incl. request input for roots) / bandwidth, instead of the cluster-wide mean. Changes which function wins a node in the grow step | heavy (states x10) |
| V2 | two-hop partners (chains) | for a directed path a -> b -> c with a != c: add gamma x r_w x min(s_ab, s_bc) to the pull between a and c; gamma = 0.5 | chain, composite |
| V3 | join cohesion | for a task with >= 2 parents of different types a, b: add gamma x r_w x min(s_a, s_b) to the pull between a and b; gamma = 0.5 | diamond, grid, composite |
| V4 | fork cohesion | for a task with >= 2 children of different types b, c: add gamma x r_w x min(s_b, s_c) to the pull between b and c; gamma = 0.5 | diamond, grid, composite |
| V5 | critical-path weighting | multiply each direct edge's pull by max(0.25, 1 - slack/CP), slack = CP - longest path through the edge, from mean run times | composite, diamond, grid |
| V6 | waiting term on | the existing `queue_term=True` switch (M/M/1 per container). Anchor: measured +0.9% on 18 cases | none specific |
| V7 | ALL | V1 + V2 + V3 + V4 + V5 | all |

Built-in checks (must hold exactly, otherwise there is an implementation error): on the chain archetype V3, V4 and V5 are identical to V0 (no joins, no forks, every edge has zero slack).

**Testbeds.**
- **T1: the 18 development cases** (Azure/Huawei x 50/70/85% x seeds 1-3), controller config D of `grid2x2_v2.py` (FROZEN2 + lam 0.5 + criticality dispatch, 60 s re-layout, 4 s moves, NSGA-II start). Reference: the existing `results/grid2x2_v2/*.D.json` (bit-identity checked), plus two placebo runs per case (move period 4.001 s and 3.999 s).
- **T2: the DAG Topology Suite** (`dag_suite.py`: chain, diamond, grid, composite, heavy x seeds 1-3), config `base` of `dag_suite_run.py` (FROZEN2 + lam 0.5, FIFO dispatch, 2 s moves). Reference: the existing `base`, `P1`, `P2` runs of each archetype and seed. Statistic: P99 of requests arriving after the 120 s burn-in, as in `dag_suite_run.py`.

**Reading rule (noise-floor-referenced, run-noise-floor).** For each case k the null reference is the geometric mean of the three null runs (base, placebo 1, placebo 2). Effect of variant v on case k = ln(P99_v,k) - ln(null reference_k); negative = better. Per-run noise sigma = standard deviation of the null runs' deviations from their own reference, pooled per testbed.

**A variant "pays" on T1 if ALL hold:** geometric-mean P99 ratio versus the null reference <= 0.97 (3% better); the 95% bootstrap interval (over the 18 per-case log effects) excludes zero; cold starts at most 20% higher; and it is no worse than 1% at the 50%-load cases. (This is the project's standing success criterion, above.)
**A variant "pays structurally" on T2 if, for an archetype it targets:** the mean effect over the 3 seeds is <= -3%, all 3 seeds are negative, and the mean effect exceeds the largest absolute null deviation measured in that archetype.
**Verdicts.** Pays on T1 -> candidate for the controller, confirm on fresh seeds (11 and up) before any claim. Pays structurally only -> reported as a structure-specific effect, not a general improvement. Neither -> the blind spot is not where the headroom is, at these settings; report the effect sizes and intervals in full. A dose check (gamma = 1.0) is run only for a variant that pays, and is labelled post hoc. Secondary metrics for every cell: mean and P90 (mean and tail have diverged before), cold starts, moves per request, relocated MB. Nothing is dropped from the report if it fails.

**Compute.** About 270 runs, roughly 30 CPU-hours (T1 5.5 min per run, T2 3-12 min), run in the background on the project machine.

**Novelty status.** Every variant has a published antecedent in spirit (FaaSFlow-style grouping along the critical path, ClusterFlow's weighted cut, FaaSPR's expected transfer saved). They are tested as measured applications inside a move-based controller on a fixed container budget, not claimed as new ideas. See [[novelty-register]] P8.

### Placement-objective additions: result, stopped early by the user (1-2 Nov 2026, 162 of 258 runs)

Stopped on the user's decision to move to the request-move mechanism. Full partial report: `results/placement_ext_report_partial.txt`; runner `output/data-analysis/placement_extensions.py`; V0 re-runs reproduced the stored results exactly (event hash and P99) before any variant was launched.

**Coverage.** T2 (DAG suite): grid, diamond, composite, heavy complete (3 seeds, all seven variants); chain only V3/V4/V5 (identical to V0 by construction), V1, V2, V6, V7 not run. T1 (18 development cases): variant runs exist for Azure 50% (all), 70% (all), and part of 85%; Huawei not started; 8 of 18 cases have both placebos, so the pre-registered reading covers 8 cases.

**T1 (8 cases, effect vs the geometric mean of three null runs, per-run noise sigma 2.8%).** V1 +2.8% (0/8 better), V2 +1.0%, V3 +1.5%, V4 +1.7%, V5 +2.4%, V6 +3.1%, V7 +1.5%. No variant pays; none is better in more than 3 of 8 cases; cold starts unchanged (within 0.1%); moves per request unchanged except V6 (-6%).

**T2 (mean over 3 seeds, % vs null reference; null max deviation in brackets).** diamond (2.6): V1 -0.6, V2 -0.8, V3 +0.4, V4 -0.3, V5 +0.7, V6 -2.8, V7 +0.3. grid (3.0): -0.8, -0.0, +1.7, -0.7, +0.3, -4.3, +0.6. composite (2.5): -1.2, -0.2, -1.5, -0.9, -1.2, -2.3, -0.6. heavy (2.1): -2.5, +0.2, -3.9, +3.4, -2.8, -1.0, -2.9.

**Verdicts against the pre-registered rules.**
- No variant "pays" on T1 (partial) and none "pays structurally" on T2: no targeted archetype has a mean of -3% or better with all three seeds negative and above the null spread.
- The one cell that numerically qualifies is heavy V3 (-3.9%, seeds -1.8, -2.4, -7.3), but heavy was not a pre-registered target for V3. It is post hoc and not a finding; the large seed is seed 3, where six unrelated variants (V1, V3, V5, V6, V7 and others) all land within 2% of each other at -7% to -8% against the three null runs (419-433 s), while V4 lands at +9%.
- V6 (the existing waiting term, an anchor, not a new addition) is better in all nine seeds on diamond, grid and composite (-2.3% to -4.3% on average) but worse on the 8 development cases (+3.1%). Unresolved; not pre-registered as a target.

**What this says.** At standard state size, none of the workflow-aware additions to the placement cost (own state size, two-hop partners, join and fork cohesion, critical-path weights, or all together) gives a P99 gain distinguishable from run-to-run variation, consistent with the offline ceiling of about 3% measured earlier. The test is incomplete for Huawei traffic, for 85% load, and for the chain archetype; this is "no evidence of a payoff", not "closed".

**Method note.** The placebo runs (move clock +-1 ms) understate the variation that follows from changing the layout: on heavy seed 3 the null runs agree within 1.5%, yet a single changed layout moves P99 by -8% or +9% in either direction (hypothesis, one seed: the run can fall onto a different trajectory). Per-run sigma on the development cases was 2.8%, above the 1.5% in the earlier placebo study. Future placement or move comparisons should use more seeds, not more placebo clock shifts.

## Request-move mechanism: what could still add gain? (plan written 2 Nov 2026, before any run; not yet approved by the user)

**Request (user, 2 Nov 2026).** Move on from placement and test variants of the request-move rule, hoping for both a more distinctive mechanism and a larger gain. Working rule (diagnose-then-novelty): read what is already known, find what has NOT been varied, and put cheap diagnostics before any build.

**What is already known about the move layer (all in `knowledge/_meta/log.md`, 26-29 Oct).** The move layer is the largest single contributor: moves x2.4 on a fixed layout, x7.9-8.3 with re-layout (2x2 grid). Every tested change to its SCORE has been null or worse: the margin theta (+2.0% to +3.5% worse, 0.25 mu), urgency ordering (+0.2%), join gating (inert: about 0.1% of decisions changed), edge-relevance weights (dropped: more bytes, no gain), ping-pong and fracture penalties (single-run readings inside noise), the downstream weight lam (retuned 1.0 -> 0.5: the one real gain), priority-aware AET estimate (+2.7% worse on heavy), shortest-queue instead of AET (+11.3% worse). Period 2 s instead of 4 s: +2.2% for +29% moves (diminishing). The headroom that Step A found was in DISPATCH ORDER (mechanism 3, established), not in the move score. Offline ceiling for moved-task handling: -0.7% to -4.7% when only unmoved tasks are credited. Run-to-run noise on the 18 development cases: sigma 2.8% per run (measured 2 Nov, placement experiment), so a 3-seed mean detects about 3% reliably.

**Consequence for this plan.** More terms in the same AET score have a strong prior of null. The variants below differ in kind: what the estimate predicts, when a pass runs, in what order candidates are served, and for whom it protects the tail.

**What the current rule does (dfps/o3s.py `rebalance_step`, dfps/solution.py `aet`).** Every 4 s, queues are visited longest first, each from its back; a waiting request moves to the node already holding its function with the lowest estimate (input transfer + list-scheduled service estimate with the mean run time for every queued request ahead + lam x downstream transfer), if that beats staying; a queue stops at the first request that does not move. The estimate is a MEAN; destinations are evaluated at the present queue, not at the arrival time; passes are periodic; order is queue length.

| Id | Variant (default off, V0 bit-identical) | What changes | Nearest published work (snippet level, 2 Nov search; not a novelty claim) |
|---|---|---|---|
| M1 | tail-aware estimate | compare stay and move on mean + kappa x sd of the AET (sd approx. mu x sqrt((ahead+1)/containers), exponential service), kappa = 1; P99 is a tail objective but the rule is risk-neutral | power-of-d and LL(d) show queue length is a coarse waiting-time signal and use workload, not quantiles; no quantile-based queue migration found |
| M2 | transit-aware destination | at the destination, add the arrivals expected during the relocation delay (measured rate of the function at that node x transfer time) to the requests ahead; large relocation delays (heavy states) make the present queue a stale prediction | none found |
| M3 | idle-initiated pull | when a container of f becomes idle with an empty queue, it pulls the best candidate at once (receiver-initiated), in addition to the 4 s pass | work stealing in general; an idle-edge-node stealing patent (USPTO 12058047) and an OpenWhisk GSoC proposal, neither evaluated; Llumnix and Hermod for LLM serving |
| M4 | gain-ordered pass | visit queues by the best attainable gain of their back request instead of by queue length, so the scarce good destination slots go to the largest gains | none found; ordering of batch assignment is a standard matching question |

**Gate 0 (cheap, before building any variant fully).** M1 and M2: re-score the logged decisions offline (each evaluated stay/move decision with its ahead count, container count, mean run time, transit time and rate), as the lam probe did. Flip rate (share of decisions whose chosen action changes) below 5% -> dead, no runs; 5-15% -> marginal, run at one seed on the 6 hardest cases; above 15% -> proceed. M3: share of container-seconds spent idle while a request of the same function waits at another node that already holds the function, measured on the logged baseline; below 2% -> dead. M4: replay each pass offline in gain order versus length order; share of accepted moves that differ below 5% -> dead.

**Gate 1 (only for variants that pass Gate 0).** The 18 development cases, config D of `grid2x2_v2.py`, effect against the geometric mean of the three null runs (base + two placebos with the move period +-1 ms), as in the placement experiment. A variant "pays" if: mean P99 at least 3% better with the 95% bootstrap interval excluding zero; moves per request at most 30% higher; cold starts at most 20% higher; no worse than 1% at the 50%-load cases. Then confirmation on fresh seeds 11-16 before any claim. Dose or constant (kappa) is fixed above and is not tuned; a sensitivity run only for a variant that pays, labelled post hoc.

**Compute.** Gate 0 needs one logged baseline per case (18 runs, about 6 CPU-hours). Gate 1 is 18 runs per surviving variant plus 36 placebo runs (placebos are reusable across variants): about 1.7 CPU-hours per variant, so roughly 10-15 CPU-hours for all four, about 1-2 hours of wall time on 10 workers.

**What this plan does not claim.** That any variant will pay. The prior is null, for the reasons above. The value of the plan is a clean, cheap answer on the four dimensions not yet varied.

### Request-move mechanism, gap diagnosis step 1: how wrong is the AET estimate, and how much of the error can be removed? (2 Nov 2026, free: existing Step A log, one F3 run, no new simulation)

Data: `output/data-analysis/results/penalty_stepA/stepA.pkl` (70,430 logged relocations of the baseline controller, FROZEN2 lam 0.5, 900 s F3). Used: 44,425 in-window rule moves whose request started at the destination of that move. Predicted time to start at the destination = transfer + (service estimate - mean run time); realised = start time - move time. Held-out half for every fit.

- The estimate explains 44% of the variance (held-out R2 0.437, rmse 5.38 s; realised mean 8.0 s, predicted 7.2 s, median error 0).
- The error is systematic, not only noise. For destinations predicted idle, the request starts LATER than predicted, and the lateness grows with the transfer time: +0.4, +1.2, +2.2, +3.9, +6.4 s for transfers of under 2, 2-5, 5-10, 10-20, over 20 s (arrivals at the destination queue during the transfer are not counted). For destinations predicted to have a long wait the request starts EARLIER than predicted: -2 to -3 s at 5-20 s predicted wait, -10 to -15 s above 20 s (the list-scheduling estimate with the mean run time overstates long waits; part of this is selection, because the rule picks destinations that look best).
- Recalibrating with two coefficients only, realised = a + 1.26 x transfer + 0.55 x predicted wait, raises held-out R2 to 0.535 (rmse 4.89 s, -9%). Adding queue length, container count, mean run time and an interaction adds nothing (R2 0.540). The remaining error (4.9 s of a 7.2 s spread) is not predictable from queue state: it is mostly service-time randomness.
- Reading. The estimator has a modest, reducible bias: transfer under-weighted (1.26 instead of 1) and queue wait over-weighted (0.55 instead of 1). The project has tuned only the weight on the DOWNSTREAM transfer (lam 1 -> 0.5); the weights on the input transfer and on the wait were never varied. Most of the remaining error cannot be removed by any estimator that sees only the queue, which bounds M1 (tail-aware) and any foresight-free variant.
- Caveats: one scenario (F3, not the 18 development cases), one run, errors measured on moves the rule chose (selection), R2 on time-to-start rather than P99. Not a result about P99.
- Consequence for the plan: M2 (transit-aware destination) is supported by the lateness-grows-with-transfer pattern; a new candidate M5 (re-weighted estimate: alpha x input transfer + beta x queue wait + mean run time + lam x downstream) follows from the fitted coefficients and costs nothing to implement; M3 and M4 are not informed by this step.

### Request-move mechanism, gap diagnosis step 2: pre-registered 2 Nov 2026, before any run (user go-ahead 2 Nov)

Two cheap measurements on the 18 development cases (config D of `grid2x2_v2.py`), script `output/data-analysis/move_gap_probe.py`.

**(a) Timing rung (bounds M3, idle-initiated pull).** Same controller with the move period at 1 s and 0.5 s (baseline 4 s; 2 s earlier gave +2.2% for +29% moves). Reference: geometric mean of the three null runs per case (D, and the placebo runs with the period +-1 ms). Reading: M3 is DEAD if the 0.5 s rung is less than 3% better than the null reference or its 95% bootstrap interval (over the 18 per-case log effects) includes zero. It stays ALIVE if the 0.5 s rung is at least 3% better with the interval excluding zero; moves per request and cold starts are reported alongside and are not a bar (a gain bought with several times the moves is a different mechanism from a cheap pull). A faster clock is an upper bound on an event-driven pull, since a pull acts at the moment a container idles.

**(b) Estimate-error replication (bounds M2 and M5).** Logging-only runs of the baseline (bit-identical to the stored D results, checked by event hash). Same analysis as step 1: time to start at the destination of each rule move, predicted (transfer + wait) versus realised; fit realised = a + b x transfer + c x predicted wait on the moves of half the CASES, test on the other half (not a random split of moves: moves within one case are correlated), two random case splits. The finding REPLICATES if, pooled over held-out cases, the recalibrated fit lowers the rmse by at least 5% AND b > 1.1 and c < 0.8 in at least 4 of the 6 (family, load) cells. If it replicates, M5 (re-weighted estimate) goes to Gate 1 with the pooled coefficients, rounded to one decimal and fixed before any run; they are fitted on the same development cases that Gate 1 uses, so Gate 1 is optimistic and fresh seeds 11-16 are required before any claim. If it does not replicate, M5 is dropped; M2 stays alive on the lateness-grows-with-transfer pattern only if that pattern (error of the idle-predicted destinations rising with transfer time, at least +2 s at over 10 s transfers) holds in at least 4 of 6 cells.

**Compute.** Placebo runs missing from the placement experiment (to complete three null runs per case), 18 logging runs, 36 rung runs; roughly 14 CPU-hours.

### Request-move mechanism, gap diagnosis step 2: results (2 Nov 2026; 18 development cases, all runs complete, 0 errors; report `results/move_gap_report.txt`)

All 18 logging-only runs reproduced the stored D runs exactly (event hash and P99: 18 of 18). Null reference = three runs per case (D at 4 s, placebos P1/P2), all 18 cases complete.

**(a) Timing rung (M3, idle-initiated pull): DEAD.** Move period 1 s: P99 +0.8% versus the null reference (95% interval -0.4 to +2.0, better in 6 of 18), moves per request 5.45 versus 3.21 (+70%), cold starts unchanged. Move period 0.5 s: P99 +4.3% WORSE (+1.9 to +6.7, better in 5 of 18), moves per request 7.41 (+131%). Neither rung is 3% better, so by the pre-registered rule a faster or event-driven pass has no headroom; acting more often is, if anything, harmful. A plausible reason, not tested: the estimate is noisy (below), so each extra decision opportunity adds more harmful moves than good ones.

**(b) Estimate error, case-level split (18 cases).** The AET estimate explains 34-35% of the variance of the time a moved request takes to start (test R2 0.353 and 0.338, rmse 6.2-6.3 s). Recalibrating with two coefficients lowers the rmse by 7.7% and 10.1% (mean 8.9%, needs 5%: met), R2 to 0.449 and 0.465. Fitted weights: transfer 1.14-1.16, predicted wait 0.50-0.56. Per (family, load) cell: weight on the predicted wait 0.44 to 0.64 in all 6 cells (the condition c < 0.8 holds in 6 of 6); weight on the transfer 1.06 to 1.13 (above 1.1 in only 1 of 6). Lateness of idle-predicted destinations at transfers over 10 s: +1.5, +1.4, +2.6, +1.1, +2.5, +5.0 s (needs at least +2 s in 4 of 6 cells; met in 3).
- Verdict as pre-registered: M5 (re-weighted estimate) does NOT replicate (needs transfer above 1.1 and wait below 0.8 together in 4 of 6 cells; met in 1). M2 (transit-aware destination) dropped (lateness criterion met in 3 of 6; needs 4).
- What the data say beyond the rule, labelled post hoc: the over-weighting of the predicted wait (about a factor of two) is large and present in every cell, in both families and at all loads; the under-weighting of the transfer is small and the lateness pattern is monotone in transfer time in every cell but strongest at 85% load (+5.0 s on Huawei). These do not change the verdicts above. A re-scoped "wait weight only" variant would be a new hypothesis and needs its own pre-registration before any run.
- Remaining error: about 5.5-5.9 s rmse after recalibration, mostly service-time randomness that no queue-state estimate can remove.

**Reading for the gap question.** On the two dimensions measured, timing and the point accuracy of the estimate, there is no large reducible gap: faster passes do not help, and the best recalibration removes about 9% of the error. Not covered by these diagnostics: tail-aware comparison (M1), pass ordering (M4), and the interaction between a noisy estimate and the decision threshold.

### Request-move mechanism: wait-weight test, pre-registered 2 Nov 2026, before any run (user choice 2 Nov: "test the wait weight first")

**What and why.** The step-2 replication fitted weight about 0.5 on the predicted queue wait in all six (family, load) cells, post hoc, while the pre-registered M5 rule did not fire. This is therefore a new, narrower hypothesis, and a retuning of one constant of the existing rule in the same sense as the earlier downstream weight (lam), not a new mechanism. Change: in the AET estimate, `service_estimate` is split into mean run time mu and predicted wait (service_estimate minus mu); the wait is multiplied by `wait_w` (churn key, default 1.0, `Sol.aet(..., wait_w=)`). Run with `wait_w = 0.5`, nothing else changed (cell D, lam 0.5, period 4 s). Default 1.0 is bit-identical to the stored runs (checked by event hash before any variant run).

**One test, one value.** Only 0.5 is run. No sweep of other values on these cases (a sweep on the development cases would choose the value from the same data it is scored on).

**Reading on the 18 development cases (script `output/data-analysis/wait_weight.py`).** Reference = geometric mean of the three null runs per case. Passes the development bar if ALL hold: (1) mean P99 at least 3% better than the null reference; (2) the 95% bootstrap interval over the 18 per-case log effects excludes zero; (3) cold starts at most +20%; (4) at 50% load not more than 1% worse. Otherwise the variant is closed as a null. Moves per request, P95 and per-cell effects are reported, not a bar. Passing the bar means only "worth confirming": a confirmation on fresh seeds 11-16 (not used for the choice of 0.5) is required before any claim, and the weight is a retuned constant, so it would be reported as an engineering finding unless the fresh seeds show a family- or load-dependent optimum.

**Compute.** 18 runs, about 1.7 CPU-hours.

#### Wait-weight test: result (2 Nov 2026; 18 of 18 runs, 0 errors)

Default `wait_w = 1.0` reproduced the stored runs exactly (event hash and P99, T1 and two T2 cases) before the variant ran. `wait_w = 0.5` versus the null reference (geometric mean of three runs per case): P99 **+2.0% WORSE** (95% interval +1.0 to +3.0), better in 2 of 18. By cell: F1 +2.1/+1.3/+2.3% (50/70/85% load), F2 +1.1/-0.0/+5.0%. Moves per request 2.86 versus 3.21, cold starts unchanged, P95 +1.0%, 50% load +1.6%. **Fails the pre-registered bar; closed as a null.** The weight of about 0.5 fitted to the realised wait does not improve decisions when applied to the rule; plausibly the rule's threshold and the over-weighted wait already act as a hysteresis against noisy moves (not tested). No fresh-seed run. Script `output/data-analysis/wait_weight.py`, results `results/placement_ext/T1/*.W05.json`.

### Request-move mechanism, gap diagnosis step 3: logging for M1 and M4, pre-registered 2 Nov 2026, before any run (user go-ahead 2 Nov)

Logging-only runs of the baseline (cell D, 18 development cases, bit-identical to the stored D runs, checked by event hash), `output/data-analysis/move_ctx_probe.py`. Logged for every decision of every 4th rebalance pass: the estimate's parts at the current node and at every evaluated candidate, their queue lengths and container counts, the accepted destination. No new decision rule is run; both readings below are free offline re-scoring and are sensitivity diagnostics (they ignore how a changed decision alters later queue state), exactly like the earlier lambda Gate 0.

**M1 (tail-aware comparison).** Score each location by mean + z x sd of its start time, sd = c x mu x sqrt(queue ahead per container + 1), c fitted once from the step-2 realised-versus-predicted residuals (pooled). Flip rate of the chosen action versus the baseline for z = 0.5 and 1.0, reported overall and among the decisions that moved. Reading, fixed now: flip rate below 5% at z = 1.0 -> M1 dead, no runs; 5-15% -> marginal, one run of the 18 cases at z = 0.5; above 15% -> run z = 0.5 and 1.0 on the 18 cases (then the success bar of this file). Also reported: whether the calibration shows the sd growing with queue per container (if the sd is flat, the tail-aware term cannot distinguish locations and M1 is dead regardless of the flip rate).

**M4 (gain-ordered pass).** The pass has no move cap (unlimited), so order can only matter through moves that interact. Reported per sampled pass: moves per pass, share of passes with at least two moves, share of those with two moves into the same (function, node) queue, and the correlation between processing order and gain. Reading, fixed now: M4 dead if fewer than 20% of the passes with moves contain two moves into the same (function, node) queue (nothing to reorder); otherwise it stays open and needs an online test (order cannot be re-scored offline).

**Compute.** 18 runs, about 1.7 CPU-hours.

#### Step 3 results (2 Nov 2026; 18 logging runs, identical to the stored D runs: 18 of 18; 492,193 logged decisions, 283,262 of them moves; `move_ctx_probe.py report`)

**M1 calibration.** The spread of (realised - predicted) start time grows with queue per container: sd/mu 0.71, 0.80, 1.42, 1.95, 3.05, 5.90 for queue per container 0-0.5, 0.5-1, 1-2, 2-4, 4-8, over 8. The model c x mu x sqrt(r + 1) with pooled c = 0.78 over-states the spread at short queues and under-states it above 4 per container (model 2.5 and 3.4 where the data show 3.05 and 5.9): the growth is steeper than the square root. **M1 Gate 0:** z = 0.5 flips 10.8% of decisions (16.2% of the moves); z = 1.0 flips 15.5% (21.2% of the moves). By the pre-registered reading (above 15% at z = 1.0) M1 goes to runs at z = 0.5 and 1.0 on the 18 cases; the flip rate is just over the line and, as with the lambda Gate 0, says only that the choice is sensitive, not that flipped choices are better.
**M4 structure.** 1,117 sampled passes with moves, 253.6 moves per such pass, 98% of them contain two moves into the same (function, node) queue, so reordering is not excluded (dead below 20%). Correlation between processing position and gain within a pass: mean -0.41, i.e. the current order (longest queues first, tail of the queue first) already puts the larger gains earlier; the headroom from a gain-ordered pass is therefore probably smaller than the 98% suggests, and it can only be measured online.

### Request-move mechanism, M1 (tail-aware comparison): pre-registered 2 Nov 2026, before any run (user go-ahead 2 Nov)

Per the step-3 reading (flip rate 15.5% at z = 1.0). Change: `churn["tail_z"]` (default 0 = off, bit-identical); each location (the request's current node and every candidate) is scored by estimate + z x 0.78 x mu x sqrt(queue ahead per container + 1), exactly the model of the Gate 0 (known to under-state the spread above 4 requests per container; not retuned). Runs: z = 0.5 (T05) and z = 1.0 (T10) on the 18 development cases, nothing else changed (cell D). Reading, same as the wait-weight test: mean P99 at least 3% better than the null reference (geometric mean of three null runs per case), 95% bootstrap interval excluding zero, cold starts at most +20%, at 50% load not more than 1% worse; a pass means only a fresh-seed (11-16) confirmation is warranted. Two values are run and scored separately; with two tests the interval for a pass is judged against the larger of the two intervals, and a pass of one value only counts if the other is not clearly worse. Default-off identity checked first (same check as before). Compute 36 runs, about 3.4 CPU-hours.

#### M1 (tail-aware comparison): result (2 Nov 2026; 36 of 36 runs, 0 errors; default `tail_z = 0` re-checked bit-identical on the edited code)

Versus the null reference (geometric mean of three runs per case), 18 development cases: **z = 0.5: P99 +0.2% (95% interval -0.5 to +0.9), better in 7 of 18; z = 1.0: +0.5% (-0.1 to +1.2), better in 7 of 18.** Moves per request 3.23 and 3.26 versus 3.21, cold starts unchanged, P95 -0.4% and -0.2%; at 50% load -0.4% and +0.3%. Neither value is 3% better, so **M1 is closed as a null** (no fresh seeds run). Reading: the 11-16% of decisions that flip under a spread-aware score are, on average, neither better nor worse for P99 (the effect is inside the run-to-run noise of about 1-3% per case), so the point estimate of the AET is not what limits the rule. Caveat: the spread model (0.78 x mu x sqrt(queue per container + 1)) under-states the spread above 4 requests per container (step-3 calibration); a steeper model was not tried (a retuning, not a new mechanism). Script `output/data-analysis/wait_weight.py report T05|T10`, results `results/placement_ext/T1/*.T05.json|T10.json`.

**State of the move-rule gap diagnosis after steps 1-3:** timing (M3), estimate re-weighting (M5, and the wait weight alone), transit-aware destinations (M2) and tail-aware comparison (M1) are all closed null or dead; only M4 (gain-ordered pass) remains untested online, with probably small headroom (the current order already puts larger gains earlier, mean correlation -0.41). The data found no reducible gap in the AET rule on any dimension measured.

### Terminology correction (2 Nov 2026): AET is the paper's "actual execution time"

The DFPS paper (p. 8) defines AET(rq, e) as the actual execution time of a request at a node: "the input/output state transfer time of rq to/from node e, and the actual service time of rq on e, considering the current requests waiting" (the node with the lowest AET among those holding a warm instance is chosen; the relocation gain is the AET difference, Eq. 8). Earlier notes and the talk called it the "finish-time estimate" / "estimated finish time"; that label was ours and is replaced by "AET (actual execution time)". Where our `Sol.aet` differs from the paper's definition (already DEVIATIONS D-2 and the lam sweep): (1) the service time is not actual but computed by list scheduling over the instances' availability with the mean run time; (2) the output-transfer term is weighted lam = 0.5 in our controller (the paper and B* use weight 1); (3) a destination must have free storage for the request's input states (D-4, A-23); (4) the paper applies AET only inside the annealing trial (forced relocations and pulls to a new instance); our rule applies it as a periodic pass over all queues, back first, with a stop rule and no cap. Older sections below keep their wording of "AET estimate", which is correct for what the code computes.

### Dispatcher replacement, step 1: do arrival-time plans go stale? (pre-registered 3 Nov 2026, before any run; user go-ahead 3 Nov)

Aim: replace the DFPS graph-pattern-matching dispatcher by an own, workflow-aware one that fits the other three mechanisms (60 s re-layout, 4 s request moves, criticality queue order), on CAP-W1. The matcher plans every task of a request at arrival; a deep task runs long after its plan was made, and the mover repairs plans at the price of a second state transfer. Step 1 asks whether that costs anything, before any dispatcher is built. Existing context: with moves on, matcher, greedy EFT and Graph-Aware are within about 2% of each other on P99 (CAP-U, 18 cases), so a better solver of the same objective has little headroom; the tail is mostly queueing (moved-task wait 35-51% of the tail extra time), transfer only 7-11% of the critical path.

Runs: `output/data-analysis/stale_plan_probe.py` re-runs "ours" under CAP-W1 with the trace on (F1 and F2, 50/70/85% load, seed 1: 6 runs). The trace additionally logs every request move (transfer delay, time since the task first joined a queue); this changes no dynamics. A case is used only if its event hash equals the stored `results/capW1_light` run.

Readings, fixed now:
- **STALE.** Plan age of a task = time from its request arrival to its first enqueue; non-root tasks only. Off-plan share = tasks that run on a node other than their planned node. Ratio = off-plan share in the oldest age quartile / youngest quartile. Late binding is worth building only if the ratio is >= 1.5 in at least 4 of 6 cases. Reported with it: moves per task by quartile, and the ratio with age split at the median inside each (workflow, task) cell, which removes the depth confound (a deep task is both older and further from its plan; the quartile ratio alone cannot separate age from depth, so the cell-controlled ratio is the one to trust if they disagree).
- **REPAIR.** Transfer seconds of all moves of the tail requests (sojourn at or above the case P99) divided by the tail mean sojourn, and the part made within one move period (4 s) of the task first joining a queue. An upper bound, since not every move is on the critical path. Below 2% in at least 4 of 6 cases: repairs cost too little for late binding to recover; then the cheaper replacement is an upfront finish-time list scheduler with the mover's own estimate.
- Both must point the same way to decide: STALE fires and REPAIR is not below 2% -> build late binding (step 2). STALE does not fire, or REPAIR below 2% -> do not build late binding; report the null.

Caveats stated in advance: one seed per case (seeds draw different workflow sets, so they are not replicates); age is observed, not randomised; the diagnosis shows an association, and the binding-time experiment (arrival vs first-parent-finish vs ready, mover on/off) is what would show the effect.

### Dispatcher calibration: why does a per-task finish-time dispatcher beat the DFPS matcher with moves on? (pre-registered 3 Nov 2026, before any run; user request 3 Nov)

Context: 5 of 18 CAP-U reference runs (all 85% load, seed 1) show Graph-Aware (beta 4) 4-23% faster on P99 than the matcher with moves on, greedy EFT about the same; fewer moves (-2 to -13%), fewer re-layout reroutes (-17 to -26%), cold starts +5 to +18%; gain grows with state size. Cause unknown. Both dispatchers rank nodes with the same simulator quantity FST, so the first question is whether the matcher's choices are worse calibrated against what the tasks then realise.

Runs (`output/data-analysis/dispatch_calibration.py`, CAP-W1, "ours" controller with criticality queue order, only the dispatcher differs): arms matcher / greedy EFT / Graph-Aware beta 4, on F1 85%, F2 85%, F1 70%, seed 1 (9 runs). The trace logs, per task, the FST of the chosen node at planning (new trace-only line in `Sim._plan`) and the realised wait (first enqueue to start, including waits after moves). The matcher arm must reproduce the stored capW1_light event hash.

Reading, fixed now: error = realised wait minus predicted FST, by arm, for root tasks (planned moments before they run, so a pure selection effect) and non-root tasks (adds staleness); mean error, mean absolute error, and the Spearman correlation between predicted and realised wait. **CAL:** the matcher is worse calibrated if its mean absolute error on non-root tasks is at least 1.2x greedy EFT's in at least 2 of 3 cases. If so and the root-task error also differs, the cause is the selection; if the root errors agree, it is staleness. If CAL does not hold, estimate quality does not explain the gain, and the cause lies in sibling spreading or the transfer-versus-queue balance. Caveat: the three cases are 70-85% load, one seed each, and say nothing about low load.

### Greedy EFT as dispatcher on the 18 CAP-W1 cases (pre-registered 3 Nov 2026, before any run; user request 3 Nov)

Context: on the 9 finished CAP-U reference cases (all 85% load, seed 1) Graph-Aware and greedy EFT beat the matcher with moves on; greedy EFT has no tuned constant and no dependence on DFPS's graph matching, so it is the natural first independent dispatcher. This tests it in the setting the project now uses.

Runs (`output/data-analysis/capw1_ccag.py`, results in `results/capW1_ccag/`): the 18 CAP-W1 development cases, same scenario, start layout, arrivals, seeds and controller as the stored `results/capW1_light` "ours" runs (60 s re-layout, 4 s moves, criticality queue order, lam 0.5); only the dispatcher is `dispatchers.greedy_eft` (per task: input transfer + FST). Matcher results are the stored ones, not re-run.

Readings, fixed now: primary = per-case ratio P99(greedy EFT) / P99(matcher), geometric mean with a bootstrap 95% CI over the 18 log ratios (cases are the unit). **Not worse** (accepted as a replacement) if the CI upper end is <= 1.02 and mean cold-start ratio <= 1.2. **Better** only if the CI upper end is <= 0.97. Also reported: wins of 18, P50/P95, moves per request, cold starts, plan time. A result on fewer than 18 cases is partial and not the pre-registered reading. Caveats: one seed per case; the matcher results were produced earlier on the same code path (the hash of the stored runs was reproduced on 4 traced re-runs on 3 Nov).

### Replay diagnostic: would a planner that uses the mover's finish-time view have picked the nodes the mover later chose? (pre-registered 3 Nov 2026, before any run; user go-ahead 3 Nov)

Context: greedy EFT is NOT WORSE than the matcher on the 18 CAP-W1 cases (geometric-mean P99 ratio 0.996, CI 0.984-1.006); step 1 found 26-45% of non-root tasks run off their planned node, not explained by plan age, and tail moves' transfer is 15-23% of tail sojourn. Candidate mechanism: a dispatcher that prices the expected later repair, i.e. is consistent with the mover. Before building it, ask whether the mover's corrections go toward what a finish-time planner would have chosen at planning time.

Runs (`output/data-analysis/replay_diag.py`, CAP-W1, "ours" controller, the six step-1 cases): the same runs as step 1, plus a trace-only line in `Sim._plan` that also computes `greedy_eft` at the moment of planning (the plan actually used stays the matcher's; greedy EFT is a pure function of the state, so the event hash must still equal the stored run, else the case is not used). Per non-root task: matcher plan, greedy EFT counterfactual (cf), node it finally ran on (exec).

Readings, fixed now: AGREE_plan = share of non-root tasks with exec = plan; AGREE_cf = share with exec = cf. **Premise supported** if AGREE_cf exceeds AGREE_plan by >= 10 percentage points in at least 4 of 6 cases (a finish-time planner would have avoided a real share of repairs); in that case the repair-priced dispatcher is worth building. Otherwise (difference < 10 points in at least 3 of 6) the mover does not move tasks toward the finish-time choice, and the repair-priced term is dropped. Also reported: among off-plan tasks, the share with exec = cf; the share with cf = plan (the two planners already agree); mean number of nodes holding the function (the chance level of agreement). Caveat: exec is the node after the mover has acted on the matcher's trajectory; it is not what the mover would do after a different plan. One seed per case.

### Parent-finish binding, trace check: which tasks carry the early repair cost? (pre-registered 3 Nov 2026, before the analysis; user go-ahead 3 Nov)

Context: the replay diagnostic (0 of 6) dropped the repair-priced term; step 1 showed that 10-16 of the 15-23 points of tail move cost (tail moves' transfer / tail mean sojourn) are moves made within one move period (4 s) of the task's first enqueue. Candidate mechanism: choose a task's node when its parent finishes (current queues, greedy EFT score), keeping the arrival plan and its storage reservation as fallback; first version for single-parent tasks only (joins keep their plan). Roots are planned and sent at arrival, so binding changes nothing for them.

Analysis (`output/data-analysis/bind_trace_split.py`, existing step-1 traces in `results/stale_plan_probe/`, no new runs): tail = requests with sojourn at or above the case P99, as in step 1. Tail move transfer seconds split by the moved task's in-degree (root / single parent / join, >= 2 parents) and by timing (within 4 s of first enqueue / later), each as a share of the tail's total move transfer and as points of tail mean sojourn. Also the same split over all requests.

Reading, fixed now: **SINGLE.** If single-parent tasks carry at least half of the within-4 s tail move cost in at least 4 of 6 cases, build the single-parent version first. If they carry less than half in at least 3 of 6, the first version cannot recover much: joins have to be handled first (design question for the user). Caveat: move cost is an upper bound on what binding can save (not every move is on the critical path, and a rebind may itself be followed by a move).

### Join binding at last-parent finish: what does holding the states cost? (pre-registered 3 Nov 2026, before the analysis; user go-ahead 3 Nov)

Context: the trace check above found joins carry most of the early tail move cost (single-parent share < 50% in 4 of 6), so joins come first. Option 1: a join's node is chosen when its LAST parent finishes; earlier parents' output states stay on the node that produced them until then. It cannot be stale and sends no state twice, but the early parents' transfers no longer overlap with waiting for the last parent.

Analysis (`output/data-analysis/join_hold_cost.py`, step-1 traces, no new runs). Per join task (>= 2 parents) of a request in the window, with d_p the finish time of parent p, n_p its node, k the node the join finally ran on, STT the network's transfer time: today's input-ready time at k is max_p(d_p + STT(s_p, n_p, k)) (pipelined); under option 1 it is max_p d_p + max_p STT(s_p, n_p, k). HOLD = the difference (>= 0), the delay option 1 adds. SAVE = transfer seconds of the join's own request moves (all; and within 4 s of first enqueue), the most option 1 can save. Reported for joins of tail requests (sojourn >= case P99; primary) and of all requests: mean HOLD, mean SAVE, share of joins with HOLD = 0, and the gap last-minus-first parent finish against the largest input transfer.

Reading, fixed now: **HOLD.** Option 1 is worth building if mean HOLD < mean SAVE (all moves) for tail joins in at least 4 of 6 cases. If mean HOLD >= mean SAVE in at least 3 of 6, holding costs more than the repairs it avoids, and option 3 (arrival-time choice by expected maximum) or option 2 is next. Caveats: HOLD is computed at the node the join ran on, not the node option 1 would pick; SAVE is an upper bound (a rebound join may still be moved, and not every move is on the critical path); no link contention in the model, so held transfers starting together cost no extra.

### Join binding at last-parent finish on the 18 CAP-W1 cases (pre-registered 3 Nov 2026, before any full run; user go-ahead 3 Nov)

Mechanism (`Sim(join_bind=True)`, `dfps/sim.py::_bind_join`): a join task (>= 2 parents) is bound when its last parent finishes; earlier parents' output states stay on their producing nodes until then; the node is re-chosen with the queues of that moment by the greedy EFT score (summed input transfer from the parents' actual nodes + FST) among nodes holding the function with room for its inputs; the arrival-time plan and its storage reservation are the fallback, and the reservation moves only if the new node has room. Simplification: held states stay accounted on the planned node's storage until binding. Single-parent and root tasks are bound at arrival as before. The mover, re-layout and criticality order are unchanged; the mover's own-plan penalty refers to the bound node.

Runs (`output/data-analysis/capw1_joinbind.py`, results in `results/capW1_joinbind/`): the 18 CAP-W1 development cases; baseline = the stored `results/capW1_ccag` runs (greedy EFT, all tasks bound at arrival), identical otherwise. Off-check: F2_r0.5_s1 with join_bind=False must reproduce the stored capW1_ccag event hash; if it does not, the comparison is not used. Smoke (F1 85%, 120 s): invariants hold, 82% of joins bound to a node other than their arrival plan.

Readings, fixed now: per-case ratio P99(join-bind) / P99(arrival), geometric mean with a bootstrap 95% CI over the 18 log ratios. **Not worse** if CI upper <= 1.02 and mean cold-start ratio <= 1.2; **better** only if CI upper <= 0.97. Also reported: wins of 18, P50/P95, moves per request, share of joins rebound. Mechanism check (secondary, not a decision rule): moves per request should fall; if P99 improves but moves do not fall, the gain is not from avoided repairs. Caveats: one seed per case; development cases (a "better" verdict needs fresh-seed confirmation before it is claimed).


### Why does the mover move tasks? (pre-registered 3 Nov 2026, before any run; user request 3 Nov)

Context: three dispatcher variants (greedy EFT, repair pricing, join binding) tied with the matcher or were dropped; moves per request barely change (join binding: -1 to -3% while 65-84% of joins were rebound). The rule in force is the plain AET rule (`O3SimAdjuster.rebalance_step`, lam = 0.5): a queued task moves to the host that minimises input transfer + service estimate (queue wait by FIFO position) + 0.5 x the transfer of its output states to its children's PLANNED nodes (`req.plan[c]`). The last term ties the mover to the dispatcher's plan. This diagnostic splits every accepted move's predicted gain into its terms.

Runs (`output/data-analysis/move_why_diag.py`, CAP-W1, "ours" controller, the six step-1 cases): same runs as step 1 with `churn["log_move_why"]`, which only logs at the accept point of the rule (no change to dynamics; the event hash must equal the stored run, else the case is not used). Per accepted move: time, task, queue position and length, containers at source and destination, queue length at the destination, the three terms of the estimate at the source and at the destination (input transfer, service estimate, downstream transfer), whether source/destination is the planned node, whether the destination hosts a planned child, time since the task's first enqueue, prior moves.

Predicted gain G = a0 - a = (in0 - in1) + (svc0 - svc1) + 0.5 (out0 - out1) = dIN + dSVC + dOUT; dIN is a cost (the state is at the source), dSVC and dOUT are the benefits. A move is WAIT-driven if dSVC >= half of the gross benefit max(dSVC,0) + max(dOUT,0), else PULL-driven (downstream transfer toward planned children).

Readings, fixed now: **WAIT** if WAIT-driven moves are >= 60% of moves in at least 4 of 6 cases: the mover mostly equalises queue waits, i.e. it reacts to queue state that changed or was unbalanced at planning. **PULL** if PULL-driven moves are >= 30% in at least 4 of 6 cases: the mover is substantially driven by the dispatcher's plan for the children, so dispatcher and mover interact through that term (a dispatcher that plans children knowing this is a real mechanism). Both can hold. Also reported: share of moves whose source is the planned node and whose destination is the planned node; share with a predicted-idle destination (queue shorter than its containers); share of repeat moves; source vs destination queue length per container; mean G and its terms. Caveats: the estimate is the mover's belief, not the realised effect (earlier work, CAP-U, found R2 0.35-0.45 for predicted vs realised start); one seed per case; whether a move helps is not measured here.


### Traced join binding: did it cut the early repair cost on joins? (pre-registered 3 Nov 2026, before any run; user go-ahead 3 Nov)

Context: join binding left P99 unchanged on the 18 cases (geometric-mean ratio 1.002, CI 0.990-1.014) and moves per request fell only 1-3%, although 65-84% of joins were bound to a node other than their arrival plan. The 18 runs carry no trace, so the early move cost on joins (the quantity the mechanism targets) was not measured.

Runs (`output/data-analysis/joinbind_traced.py`, CAP-W1, greedy EFT dispatcher, "ours" controller, the six step-1 cases, trace on): arm arr = arrival binding, arm jb = join binding. Each arm's event hash must equal the stored untraced run (`capW1_ccag` for arr, `capW1_joinbind` for jb), else the case is not used. Per arm, for the tail requests (sojourn at or above the case P99): move transfer seconds as points of tail mean sojourn, by the moved task's kind (root / single parent / join) and by timing (within 4 s of first enqueue = early).

Reading, fixed now: **REMOVES** if the early join move cost falls by at least 25% (relative, arr to jb) in at least 4 of 6 cases: join binding removes the early join repairs it targets, and the null on P99 then means the saved transfers did not reach the tail. If it falls in at most 2 of 6, the early join repairs are not caused by the arrival-time plan, whatever the mover then does. Also reported: early cost of single-parent and root tasks (does the cost move to other kinds?), late join cost, tail total, moves per request, P99. Caveat: one seed per case; upper-bound cost (not every move is on the critical path).

#### Why does the mover move tasks: result (3 Nov 2026; 6 of 6 runs, event hashes identical to the stored capW1_light runs; `move_why_diag.py report`, CAP-W1)
- Rules as pre-registered: WAIT (>= 60% of moves wait-driven in >= 4 of 6 cases) **holds** (6/6); PULL (>= 30% pull-driven in >= 4 of 6) **not shown** (0/6, 0-1% of moves).
- A move is wait-driven when the saving in service-start wait is at least half of the positive parts of the saving. 99-100% of the 29,909-92,616 logged moves per case are.
- Mean estimated gain per move 6.4-10.0 s = input transfer -1.4 to -2.6 s (the destination is farther from the parents) + wait +8.0 to +12.7 s + output pull -0.25 to -0.40 s. The mover buys a worse transfer to avoid a queue.
- The task leaves its planned node in 86-94% of moves, lands on a node that is not its plan in 99%, and the destination already hosts a planned child in only 5-7% (source: 24-38%). The destination is predicted idle in 86-98% of moves at 50-70% load and 60-63% at 85% load. Queue per container: source 1.5-4.5 vs destination 0.1-1.5. Median task age since first enqueue 1.7-2.2 s. 6-14% are repeat moves.
- Reading: the request mover is a queue balancer, not a graph-locality repair. Consistent with the replay diagnostic (moves do not go toward the greedy-EFT choice) and with the trace check (root tasks carry 20-32% of early move cost). Still untested: the estimate uses the FIFO position while queues are served by criticality.

#### Traced join binding: result (3 Nov 2026; 12 of 12 runs, event hashes identical to the stored arr/jb runs; `joinbind_traced.py report`, CAP-W1, greedy EFT)
- Pre-registered rule: early join move cost down by >= 25% in >= 4 of 6 cases -> removes; <= 2 of 6 -> not removed. Result **0 of 6: early join repairs are not removed.**
- Early join move cost (points of tail mean sojourn), arrival binding -> join binding: F1 r0.5 2.0->2.2, F1 r0.7 2.1->4.0, F1 r0.85 4.3->5.5, F2 r0.5 6.1->7.5, F2 r0.7 7.7->7.0, F2 r0.85 11.0->10.1 (up in 4 cases, down in 2, at most -10%).
- Moves per request fall by only 1-6% (e.g. 2.63->2.55 at F2 r0.85). Tail total move cost and P99 move in both directions (P99 89->89, 102->104, 143->138, 73->75, 84->86, 123->118). Late join cost falls in 5 of 6 cases (largest F2 r0.85, 8.0->4.5): a small side effect, not the pre-registered quantity.
- Together with the 18-case result (gm ratio 1.002 [0.990, 1.014], NOT WORSE, no gain): the mechanism claim "binding joins late prevents congestion that relocation later cleans up" is **not supported**. Not recorded as a contribution.

### FIFO versus criticality-order mismatch in the move estimate (pre-registered 3 Nov 2026, before any run; user request 3 Nov)
**Question.** The queue is served by criticality (`QueuePriority("full", aging=2.0)`), but `rebalance_step` counts the tasks "ahead" of a task by FIFO position (source: queue index; destination: queue length). Earlier test of a priority-aware estimate (`prio_aet`, 28 Oct): +2.7% worse, one scenario, CAP-U, key read through the dispatcher's refreshing call. Not yet looked at: how large the mismatch is, and in which direction. A task moved from the back of a FIFO queue is predicted a long wait; if it is high-tier it will in fact start early (move unnecessary), if it is tier 0 it will wait longer than predicted.
**Step 1, diagnostic (logging only).** `churn log_prio_mismatch`: at every accepted rule move, ahead at the source and at the destination in FIFO and in service order (tasks whose key is larger, or equal and older), the three AET terms, the tier of the moved task. Key read with `QueuePriority.peek` (no refresh of the dispatcher's statistics, so the dispatcher's behaviour cannot change). Six step-1 cases (F1, F2 x rho 0.5, 0.7, 0.85, seed 1), CAP-W1, controller `ours`; each event hash must equal `results/capW1_light/{tg}.ours.json`, else the case is not used. Script `output/data-analysis/prio_mismatch.py diag`.
- Reading: estimated gain recomputed with the service-order wait. Moves with gain <= 0 in service order >= 20% of moves in >= 4 of 6 cases -> **mismatch material**; <= 2 of 6 -> **not material**; else mixed. Also reported: how often ahead differs, in which direction, by tier.
- Limit: only accepted moves are logged; tasks that FIFO keeps but service order would move are visible only in step 2.
**Step 2, intervention (run regardless of step 1, same session).** `churn prio_aet_peek`: the mover's `ahead` uses service order for both source and destination, key by `peek`. 18 CAP-W1 development cases (F1, F2 x rho 0.5, 0.7, 0.85 x seeds 1-3), against the stored `capW1_light` ours runs, same reading as the greedy-EFT test: per-case P99 ratio, geometric mean with a bootstrap 95% CI over the 18 log ratios (cases are the unit); NOT WORSE if CI upper <= 1.02 and cold-start ratio <= 1.2; BETTER only if CI upper <= 0.97 (then fresh-seed confirmation). Run-to-run noise ~1.5% per run. Prior: null or worse (every earlier change to the move score was).

### Live-state replay: would a router scoring on the live state have picked where tasks ended up? (pre-registered 3 Nov 2026, before any run; user go-ahead 3 Nov)
**Why.** The earlier replay (above) and the join binding test both scored with the formula estimate (`fst_vec`, from arrival rate and queue length), not with the mover's AET on the live instance state. So "the mover's choices are not what a finish-time router picks" is shown only for the formula estimate. This replay uses the mover's own estimate.
**Probe (trace only, `Sim._live_probe`, `trace_live`).** When the last parent of a non-root task finishes: over the nodes holding the task's function with room for its input states, score = input transfer from the parents' nodes + `Sol.service_estimate` at the current queue length + 0.5 x output transfer to the children's planned nodes; the argmin is logged with the plan node and the score of the plan node. Dynamics unchanged: each event hash must equal `results/capW1_light/{tg}.ours.json`, else the case is not used. Six step-1 cases (F1, F2 x rho 0.5, 0.7, 0.85, seed 1), CAP-W1, controller `ours`; script `output/data-analysis/live_replay.py`.
**Measured over non-root tasks:** exec = plan; exec = live choice; live choice = plan; among off-plan tasks (exec != plan) the share with exec = live choice; chance level = mean of 1 / (nodes holding the function); among on-plan tasks the share where the live choice would leave the plan.
**Reading.** Live-state binding is worth building if exec = live exceeds exec = plan by >= 10 points in >= 4 of 6 cases (the bar of the earlier replay), or if >= 30% of off-plan tasks have exec = live in >= 4 of 6 cases (the formula estimate gave 1.9-4.9%). Not supported if both are met in <= 2 of 6. Else mixed. The probe is at last-parent finish; execution happens later (transfer + queue + the mover's moves), so agreement is an upper-bound-style test of "the mover goes where a live-state router would".

### Live-state replay, in-transit variant: do tasks bound or relocated but not yet queued explain the poor agreement? (pre-registered 4 Nov 2026, before any run; user request 4 Nov)
**Hypothesis (from the live-state replay result, untested then).** The live estimate counts only queued tasks. A task is invisible between its binding (last parent finished, state in transfer to its planned node) or its relocation and its enqueue. Binds that happen close together then see the same short queue and the live choice differs from where the task later waits.
**Probe (trace only, `trace_live`, extends `Sim._live_probe`).** Counter of tasks bound or relocated to (function, node) and not yet enqueued, kept from the first bind of the run (outside the window too). At each in-window bind the probe additionally scores every candidate with `service_estimate(queue length + in-transit count)` and logs the argmin, the total queued and total in-transit count over the candidates, and the in-transit count at the original live choice. Dynamics unchanged (event hash must equal `results/capW1_light/{tg}.ours.json`, else the case is not used). The six step-1 cases, CAP-W1, controller `ours`; script `output/data-analysis/live_replay2.py`, results `results/live_replay2/`.
**Reading.** exec = live+in-transit minus exec = live (non-root tasks): >= 10 points in >= 4 of 6 cases -> **in-transit tasks are a main reason**; <= 3 points in >= 4 of 6 -> **not the reason**; else mixed. Also reported: in-transit count as a share of the queued count over candidate nodes, the share of binds where the original live choice already had >= 1 task in transit toward it, off-plan agreement for both variants, and whether live+in-transit reaches the arrival plan's agreement (a binder is worth building only then).

#### FIFO versus criticality-order mismatch: results (3-4 Nov 2026; CAP-W1)
**Step 1, diagnostic (6 of 6 cases, event hashes identical to the stored capW1_light runs; `prio_mismatch.py diag report`).** Reading: moves with gain <= 0 in service order >= 20% in >= 4 of 6 cases -> material. Result: **0 of 6 (1-16% of moves): not material.**
- The mismatch has one direction: the service-order count of tasks ahead is never larger than the FIFO count at the source (0% larger), so the FIFO estimate overstates the wait of a task taken from the back of a queue. Ahead at source FIFO -> service order: F1 1.00->0.82, 2.23->1.69, 4.12->3.04; F2 0.90->0.76, 2.10->1.54, 5.27->3.90 (rho 0.5, 0.7, 0.85). The source count differs for 8-10% of moves at rho 0.5 and 44-53% at rho 0.85.
- Estimated gain per move FIFO -> service order: F1 6.90->6.32, 8.69->7.09, 9.74->7.21 s; F2 6.42->5.99, 7.88->6.37, 9.97->6.89 s. Moves with gain <= 0 in service order: 2%, 6%, 14% (F1), 1%, 7%, 16% (F2).
- Tier of the moved task: tier 1 (aged) 56% (F1) and 71% (F2) at rho 0.5; tier 0 88-89% at rho 0.85. Only accepted moves are logged.
**Step 2, intervention (18 of 18 cases; `prio_mismatch.py arm report`; `churn prio_aet_peek`, the mover counts "ahead" in service order at source and destination, key read without refreshing the dispatcher's statistics).** Result: **geometric-mean P99 ratio 1.075, 95% CI [1.055, 1.096], better in 1 of 18, cold-start ratio 1.00: not shown to be non-inferior (worse).** Per case +3% to +17% except F2 rho 0.5 seed 1 (-2%). Moves per request rise by about 20-50% (e.g. 3.05 -> 4.57, 7.71 -> 12.17). Same direction as the 28 Oct `prio_aet` test (+2.7%, CAP-U, one scenario).
- Reading: the overstated FIFO wait acts as a brake on moves. Counting the wait in service order makes more destinations look better, the mover moves more, and P99 gets worse. The mismatch is not a hidden gain. Not recorded as a contribution.

#### Live-state replay: result (3 Nov 2026; 6 of 6 cases, event hashes identical to the stored runs; `live_replay.py report`, CAP-W1)
Rule as pre-registered: worth building if exec = live minus exec = plan >= 10 points in >= 4 of 6 cases, or off-plan agreement >= 30% in >= 4 of 6. Result: **0 of 6 and 2 of 6: not supported.**
- exec = plan -> exec = live (points): F1 0.5 66.5% -> 47.8%; F1 0.7 58.2% -> 30.9%; F1 0.85 54.8% -> 19.9%; F2 0.5 73.9% -> 49.2%; F2 0.7 65.0% -> 31.4%; F2 0.85 55.1% -> 16.5%. Chance level 2.4-3.1%.
- Off-plan tasks with exec = live: 30.5, 20.4, 14.6 (F1) and 37.2, 22.1, 13.9% (F2), against 1.9-4.9% for the formula estimate (earlier replay). So live state explains part of where moved tasks go (well above chance), but at parent finish it predicts the final node worse than the arrival plan does. On-plan tasks where the live choice would leave the plan: 43-81%, rising with load.
- Consistent with the mover's choices being set by the queue state about 2 s after enqueue (median task age at move 1.7-2.2 s, 99-100% wait-driven moves), which an earlier snapshot predicts poorly. Not tested directly.
- The in-transit variant (do tasks bound or relocated but not yet queued explain it) is pre-registered above and still running; first case (F1 0.7): counting them lowers agreement by 4.0 points.

### Graph-Aware on CAP-W1, and what the port does with size (pre-registered 4 Nov 2026, before any run; user request 4 Nov)
**Size audit of the Graph-Aware port against the paper (Liang et al. 2026, Future Internet 18:265; read from the user's converted copy, Secs. 3-4).** The paper's size-related inputs: a task has memory demand and computation demand (Sec. 3.1); a node has available CPU, memory, queue length, price (Sec. 3.2); feasibility: a task's resource demand may not exceed the node's available capacity (Sec. 3.3, candidate set R(v_i), Sec. 4.2); the execution term is c_i / u_j with u_j the *currently available service capacity*, "may be augmented with queueing delay" (Sec. 4.3); residual CPU and memory margins after the assignment enter only the compatibility vector p_ij, which feeds the correction delta_ij (eta); the state update Psi adjusts available compute, memory and queue occupancy after each assignment (Sec. 4.4). Mapping in our model, checked in `dfps/dispatchers.py`: feasibility = the node holds a container of the task's function (the real count `sim.cnt`, which CAP-W1 layouts fill by container weight) and has free state storage for the task's input states, reserved task by task inside the plan (the memory update of Psi); execution term = FST (uses the real container count) plus Psi's per-plan occupancy (work placed / containers); the compute demand over capacity is the same on every node here (functions have their own mean execution time, nodes do not differ in speed). Nothing the paper uses for size is dropped except the residual-margin features inside delta, which the port sets to zero (eta = 0) because the paper does not publish its encoders or the fixed weights of g, and its own Sec. 5.6 finds eta has a limited effect. The container weights act through `cnt`: they decide how many containers of a function fit on a node, and the dispatcher only chooses among nodes that already hold one. One CAP-W1 subtlety shared by every dispatcher (matcher included): `cnt` counts containers that wait for room on their node (`pending_add`) as present, so FST may count a not-yet-started container.
**Runs.** `output/data-analysis/capw1_ga.py` (template `capw1_ccag.py`): the 18 CAP-W1 development cases, controller `ours` (FROZEN-2, lam 0.5, criticality queue order), only the dispatcher differs. Arm 1 (primary): beta = 4.0, frozen on 26 Oct by the pre-registered rule on four CAP-U development cases; alpha = 1. Arm 2 (sensitivity, no selection between the arms): beta = 1.0, inside the paper's range 0.2-1.1. Baseline: stored `capW1_light` ours runs.
**Reading (as for greedy EFT).** Per-case P99 ratio, geometric mean with a bootstrap 95% CI over the 18 log ratios (cases are the unit); NOT WORSE if CI upper <= 1.02 and the mean cold-start ratio <= 1.2; BETTER only if CI upper <= 0.97 (then fresh-seed confirmation). Reported: wins, P50/P95, moves per request, cold starts, plan time. Beta 4 lies outside the paper's own range because our normalised scores differ in scale; it is reported as a boundary choice, not as the paper's setting.
**Calibration test** (pre-registered above, "Dispatcher calibration"): started 4 Nov with the matcher and greedy EFT arms only (6 of 9 runs); the Graph-Aware arm is added after this audit.

#### Live-state replay, in-transit variant: result (4 Nov 2026; 6 of 6 cases, event hashes identical to the stored runs; `live_replay2.py report`, CAP-W1)
Rule as pre-registered: live+in-transit minus live >= 10 points in >= 4 of 6 cases -> main reason; <= 3 points in >= 4 of 6 -> not the reason. Result: **>= 10 points in 0/6, <= 3 points (here: lower, -0.4 to -4.0) in 6/6: in-transit tasks are not the reason.** Live+in-transit reaches the arrival plan's agreement in 0/6.
- exec = live -> exec = live+in-transit: F1 47.8 -> 45.3, 30.9 -> 26.9, 19.9 -> 19.0; F2 49.2 -> 47.2, 31.4 -> 28.1, 16.5 -> 16.0 (rho 0.5, 0.7, 0.85); exec = plan 66.5, 58.2, 54.8 and 73.9, 65.0, 55.1.
- The invisible mass is large: in-transit tasks are 44-128% of the queued count over candidate nodes (largest at rho 0.5), and the original live choice already had at least one task in transit toward it in 24-70% of binds (rising with load). Counting them nevertheless does not raise agreement with the executing node; off-plan agreement rises by only 0.4-3.6 points (e.g. 30.5 -> 34.1%, 22.1 -> 23.6%).
- So the live estimate's poor prediction of the final node is not caused by unseen in-transit tasks. What remains consistent with the data: the final node is set by the mover from the queue state about 2 s after enqueue (wait-driven moves, 99-100%), which an earlier snapshot predicts poorly. Not tested directly (snapshot at bind versus snapshot at about 2 s after enqueue).

### Last two spatial tests: snapshot stability and randomised move veto (pre-registered 4 Nov 2026, before any run; user decision 4 Nov)
**Stopping rule (user decision 4 Nov).** These two are the last diagnostics of the spatial line (router, binding, mover). After they finish, no further spatial diagnostics are run, whatever the outcome. No mover-side mechanism is built from either result. Priority: the Graph-Aware CAP-W1 runs and the calibration test (baseline comparisons for the results table) finish first; these two are queued behind them.
**Skipped (user decision 4 Nov): router quality under priced moves (`move_cost` 2 and 4).** The simulator has no link contention, so cost multipliers would be a synthetic sweep without a justification for the values. A boundary claim would need cost values grounded in a contention measurement first.

**1. Snapshot stability (trace only; `Sim.trace_snap`, script `output/data-analysis/snapshot_stability.py`, results `results/snapshot_stability/`).**
- Question: does the best node for a task move between its binding and the mover's passes, and does the node the task executes on follow the later state? This measures the "the target moves" explanation; it does not by itself prove that this is why routers cannot match the mover.
- Probe: for a deterministic half of the in-window requests (even request id), each non-root task is scored with the live AET on every feasible node (input transfer from the parents' nodes, i.e. the counterfactual "bind it now"; service estimate at its own queue position where it already waits, else the queue length; 0.5 x output transfer to the children's planned nodes) at binding (last parent finished), at first enqueue, and at 2 s and 4 s after the first enqueue (fired before the first event at or after the due time; reads state only). Tasks that have started by a snapshot are recorded as not waiting. Regret of the bind-time choice at a snapshot = its score minus the best score then (infinite if it is no longer feasible).
- Six step-1 cases (F1, F2 x rho 0.5, 0.7, 0.85, seed 1), CAP-W1, controller `ours`. The event hash must equal `results/capW1_light/{tg}.ours.json`, else the case is not used; a match also shows that the default-off move-veto code (below) is inert.
- Reading. A: the bind-time choice is >= 1 s worse than the best at +2 s for >= 30% of the tasks still waiting at +2 s, in >= 4 of 6 cases. B: among tasks still waiting at +2 s, exec = best at +2 s exceeds exec = best at bind by >= 10 points, in >= 4 of 6 cases. **Measured** if A and B both hold in >= 4 of 6; **not shown** if both hold in <= 2 of 6; else mixed. Caveat on B: the mover scores with a similar estimate (from the task's current node, not from the parents), so part of the agreement at +2 s is the mover following its own estimate; B shows that the final node is decided by the later state, not that the later estimate is correct.

**2. Randomised move veto (changes dynamics; churn `veto_p` = 0.1, own RNG seeded seed + 900; script `output/data-analysis/move_veto.py`, results `results/move_veto/`).**
- At a task's first accepted move (it has not been moved before), the move is vetoed with probability 0.1; a vetoed task is never moved afterwards (the mover skips it and continues with the rest of that queue). Logged per randomised decision: time, task, estimated gain (a0 - best), priority tier, queue position. Same six cases and controller; trace on. P99 and moves per request are reported against the stored runs (a 10% veto of first moves is expected to change P99 slightly).
- Outcomes (vetoed minus moved, with a bootstrap 95% CI, tasks resampled within each arm): wait from the decision to the task's start; the request's remaining sojourn from the decision (primary); the share of tasks whose request ends in the run's slowest 1%. Groups: estimated-gain thirds (per case) and tiers 0-3 (a group needs >= 100 vetoed tasks).
- Decision rule, fixed now:
  - **Some moves do not pay** if the same group has remaining-sojourn effect with CI upper < 0 (vetoing is better) in >= 4 of 6 cases. Reported as a finding. Both the margin test (theta, +2.0% to +3.5% worse) and the service-order estimate (+7.5% worse) already showed that mover-side tuning makes P99 worse, so the headroom is likely inaccessible. No mechanism is built.
  - **Moves mostly pay** (else) if vetoed tasks have longer remaining sojourn (CI lower > 0) in >= 4 of 6 cases and the lowest-gain third is not better when vetoed (point estimate >= 0) in >= 4 of 6. Then the mover is at its limit.
  - Otherwise: inconclusive, reported as such.
  - In every outcome the spatial line is closed.

#### Graph-Aware on CAP-W1, beta = 4 (primary arm): result (4 Nov 2026; 18 of 18 cases; `GA_BETA=4.0 capw1_ga.py report`)
- **Geometric-mean P99 ratio Graph-Aware / matcher 0.985, 95% CI [0.960, 1.015]; better in 15 of 18; cold-start ratio 1.00 -> NOT WORSE** (CI upper <= 1.02); not BETTER (CI upper > 0.97).
- Per case -11% to +18%: largest gains on the heavy F2 cases (F2 r0.85 s2 -11%, F2 r0.7 s2 -9%, F2 r0.85 s1 -6%), two clear losses (F2 r0.7 s3 +18%, F2 r0.85 s3 +7%), the rest -4% to +3%.
- Moves per request lower in 18 of 18 (-2% to -21%, e.g. 3.50 -> 3.07, 7.71 -> 6.62, 3.38 -> 2.66). Plan time 2.2-6.9 ms per request vs 10-90 ms for the matcher. P50 and P95 lower or equal in all 18.
- Compared with greedy EFT on the same cases (gm 0.996 [0.984, 1.006]): same verdict (NOT WORSE), slightly lower point estimate, wider CI. The beta = 1 arm (sensitivity) is still running; no selection between the arms.

#### Dispatcher calibration: matcher and greedy EFT arms (4 Nov 2026; 6 of 9 runs, matcher event hashes identical to the stored runs; `dispatch_calibration.py report`)
- Pre-registered CAL rule: matcher MAE on non-root tasks >= 1.2 x greedy EFT's in >= 2 of 3 cases -> worse calibrated. Result: **0 of 3 -> estimate quality does not explain the CAP-U gain.** Non-root MAE matcher / greedy EFT: 6.9 / 6.8 s (F1 0.85), 5.0 / 5.1 s (F2 0.85), 4.8 / 4.8 s (F1 0.7); bias and off-plan shares within 1-3 points.
- Side finding (not pre-registered as a rule, reported as observed): **the FST estimate at planning does not rank the realised waits at all.** Spearman correlation between the predicted FST of the chosen node and the realised wait (first enqueue to start, including waits after moves) is -0.20 to +0.03 for both dispatchers, for root tasks (planned moments before they run, so no staleness) as well as non-root tasks. Bias: realised waits exceed FST by 4.4-7.2 s for root tasks at rho 0.85, and fall below it by 1-2 s at rho 0.7. This is consistent with the router layer having little leverage: the quantity every router here ranks nodes by carries almost no information about the wait a task will see under the mover.
- The Graph-Aware arm (3 runs) started 4 Nov after the size audit.

#### Dispatcher calibration: Graph-Aware arm (4 Nov 2026; 3 of 3 runs; all 9 runs of the test now done)
- Observed (the CAL rule compares matcher and greedy EFT only; this is reported, not a pre-registered reading): Graph-Aware (beta 4) picks nodes whose FST at planning is 2-3x higher (non-root 12.3-15.4 s vs 5.9-6.2 s for matcher and greedy EFT), yet the realised waits of its tasks are equal or lower (non-root 3.9 / 5.8 / 8.2 s vs 4.0-4.3 / 6.2-6.5 / 8.3-8.6 s), fewer tasks run off-plan (38-41% vs 41-45%), and its predicted waits rank the realised ones slightly better (Spearman +0.08 to +0.12 non-root, +0.17 to +0.26 root, vs -0.20 to +0.03).
- Reading offered as an explanation of the Graph-Aware gain (inference, not tested): with beta = 4 the communication term dominates the min-max-normalised score, so the dispatcher trades the FST signal (which carries almost no information about the realised wait under the mover, see above) for data locality (which it does carry: transfer times are deterministic here). The mover then corrects the waits, as it does for every dispatcher, but has less to repair (moves per request -2% to -21% on the 18 cases) and the saved transfers stay saved. Consistent with the CAP-U gain growing with state size.

#### Graph-Aware on CAP-W1, beta = 1 (sensitivity arm): result (4 Nov 2026; 18 of 18 cases)
- Geometric-mean P99 ratio vs matcher **0.983, 95% CI [0.965, 1.000]; better in 13 of 18; cold-start ratio 1.00 -> NOT WORSE** (CI upper 1.000, just above the 0.97 BETTER bar). Per case -10% to +6%: F2 r0.7 s2 -10%, F2 r0.85 s2 -7%; losses F2 r0.85 s3 +6%, F2 r0.7 s3 +5%; the rest -4% to +1%. Same verdict as beta 4 (0.985 [0.960, 1.015]) with a narrower CI; no selection between the arms.

#### Snapshot stability: result (4 Nov 2026; 6 of 6 cases, event hashes identical to the stored runs, so the default-off veto code is inert; `snapshot_stability.py report`)
Rule: A (bind-time choice >= 1 s worse than the best at +2 s for >= 30% of tasks still waiting) and B (exec = best at +2 s exceeds exec = best at bind by >= 10 points) in >= 4 of 6 -> measured. Result: **A 6/6, B 0/6 -> mixed.**
- **The best node moves (A, measured).** Among tasks still waiting, the best node differs from the bind-time best in 12-39% at first enqueue, 44-74% at +2 s and 59-84% at +4 s, rising with load. The bind-time choice is >= 1 s worse than the best at +2 s for 34-65% of them (median regret 0.0, 0.0 s at rho 0.5; 0.9-1.3 s at 0.7; 3.8-4.3 s at 0.85).
- **The executing node does not follow the later snapshot either (B not shown).** Among tasks still waiting at +2 s, exec agrees with the bind-time best 10-30%, with the +2 s best 13-34% (+2 to +3 points), with the +4 s best 12-31%. No snapshot of the live estimate predicts where a waiting task runs.
- Many tasks never see the change: 28-76% start within 2 s of first enqueue (more at low load).
- Reading: the "target moves" half of the explanation is measured; the other half (the mover follows the later state, so an earlier decision cannot anticipate it) is not supported by B. Together with the calibration finding (FST does not rank realised waits) and the live-state replays, the consistent statement is that the wait-relevant state changes faster than any estimate here tracks it; neither a router nor a later snapshot pins down the final node.

#### Randomised move veto: result (4 Nov 2026; 6 of 6 runs, veto share 10.0-10.1% of first moves; `move_veto.py report`)
Rule as pre-committed: some moves do not pay if one group has CI upper < 0 in >= 4/6; moves mostly pay if vetoed tasks are slower (CI lower > 0) in >= 4/6 and the lowest-gain third is not better when vetoed in >= 4/6; else inconclusive. Result: **vetoed slower in 6/6; lowest-gain third not better in 3/6; no group where vetoing is better in >= 4/6 -> inconclusive by the rule. Spatial line closed.**
- Moves pay on average. Vetoed minus moved, remaining request sojourn: +1.90, +2.03, +2.12 s (F1 rho 0.5, 0.7, 0.85), +2.20, +2.52, +3.15 s (F2), every CI above 0. Wait to start: +3.5 to +5.4 s. Share of tasks whose request ends in the slowest 1%: +0.06 to +0.89 points (CI above 0 in 2 of 6).
- The estimated gain ranks the real benefit well. Remaining-sojourn effect by estimated-gain third: low -0.45 to +1.15 s (CI includes 0 in 5 of 6; point estimate negative in 3 of 6: F1 0.5, F1 0.7, F2 0.5), mid +1.5 to +2.6 s, high +3.7 to +6.9 s (all CIs above 0). So low-gain moves are worth about nothing, not harmful; the rule's "mostly pay" fails only on that third.
- By tier: tier 0 +2.0 to +3.5 s (all CIs above 0), tier 1 +0.2 to +3.5 s; tiers 2-3 mostly too few vetoed tasks.
- P99 with 10% of first moves vetoed vs stored: 88.8 / 88.1, 108.1 / 101.7, 141.3 / 145.1, 76.5 / 77.2, 87.8 / 83.9, 118.7 / 121.5 (mixed, -3% to +6%); moves per request -5% to -8%.
- Reading (no mechanism built, per the stopping rule): the mover's moves are worth their cost on average and in proportion to the estimated gain; the only candidate saving, skipping the lowest-gain third, is worth about zero per move, and the margin test (+2.0% to +3.5% worse) already showed that cutting moves by a threshold does not pay at the P99 level.

**Spatial line: closed 4 Nov 2026** (stopping rule above). Summary of what it established: router choice has little leverage under the mover (matcher ~ greedy EFT ~ Graph-Aware, all NOT WORSE, none BETTER); binding later (join, live-state, in-transit) does not help; the wait estimate routers rank by carries almost no information about realised waits; the best node moves after binding but no snapshot predicts the final node; moves pay on average, in proportion to their estimated gain.

### Router line: conclusion (4 Nov 2026, written with the user)
**Statement.** The mover is a good *local* predictor and a bad *global* one: its estimated gain ranks the real benefit of a move (veto test: low third ~0 s, mid +1.5 to +2.6 s, high +3.7 to +6.9 s), but no snapshot of its live estimate predicts where a task will finally run (snapshot test B 0/6, +2 to +3 points). A router is asked the global question at planning time and cannot answer it: the wait estimate every router here ranks by (FST) has rank correlation -0.20 to +0.03 with the realised wait, root tasks included (calibration test). So a router should not try to predict the final node.
**What works instead: a division of labour.** The router should settle what is exact at planning time (state transfer times, deterministic in this model) and leave what only becomes visible later (queue wait) to the mover. Graph-Aware with a large transfer weight does this: it picks nodes with 2-3x higher predicted wait, its tasks wait no longer (non-root 3.9 / 5.8 / 8.2 s vs 4.0-4.3 / 6.2-6.5 / 8.3-8.6 s for matcher and greedy EFT), fewer run off-plan (38-41% vs 41-45%), and on the 18 CAP-W1 cases it is NOT WORSE on P99 (beta 4: 0.985 [0.960, 1.015]; beta 1: 0.983 [0.965, 1.000]) with fewer moves per request in 18 of 18 (-2% to -21%) and 3-30x faster planning (2.2-6.9 ms vs 10-90 ms per request). This is the baseline row with a mechanistic explanation.
**Correction to an earlier phrasing.** This is not "aligning with the mover's objective". The mover's objective is mostly queue wait: 99-100% of its moves are wait-driven and it accepts about 2 s of worse input transfer to leave a queue. The router and the mover optimise different terms of the same cost; that is why they complement each other.
**Status of the evidence.** Measured: the FST/realised-wait correlation, the snapshot results, the veto results, the Graph-Aware P99, moves and plan time. Inference, not tested: that trading FST for transfer is *why* Graph-Aware needs fewer moves (from the calibration arm, not pre-registered; Graph-Aware's edge over greedy EFT is small, 0.985 vs 0.996 with overlapping CIs).
**Line reopened by the user (4 Nov 2026)** for one experiment that tests this directly: routers that optimise only the deterministic part, or the mover's own score, against the matcher on P99 and against Graph-Aware on cost (section below).

### Objective-aligned routers: lower cost at the same P99? (pre-registered 4 Nov 2026, before any run; user request 4 Nov, reopens the router line for this experiment)
**Question.** If the router should settle the exact part of the cost and leave the wait to the mover (conclusion above), does a router that goes further in that direction than Graph-Aware keep P99 and lower the cost?
**Arms** (`dfps/dispatchers.py`, new, existing dispatchers unchanged; runner `output/data-analysis/capw1_align.py`, results `results/capW1_align_{arm}/`): (1) `transfer_only`: each task to the feasible node with the smallest summed input-transfer time from its parents' planned nodes (origin for roots), ties by FST; no wait term. (2) `mover_aet`: input transfer + the mover's own service estimate (`Sol.service_estimate`, live instance availability, at the current queue length plus the tasks of this plan already placed there); the mover's output term is left out because every edge is priced once as the child's input. Controller `ours` (FROZEN-2, lam 0.5, criticality queue order), 18 CAP-W1 development cases, only the dispatcher differs.
**Reading.** Performance: P99 vs the matcher (stored `capW1_light` ours), NOT WORSE if the CI upper end of the geometric-mean ratio <= 1.02 and the cold-start ratio <= 1.2. Cost vs Graph-Aware beta 4 (`results/capW1_ga_b4`, the best-cost baseline so far): moves per completed request and relocated MB per completed request, geometric mean of the case ratios with a bootstrap 95% CI. **Lower cost** if the moves ratio's CI upper end <= 0.90 and the relocated-MB ratio's point estimate <= 1.00. **Success = NOT WORSE and lower cost**, per arm, no selection between the arms afterwards. Also reported: P99 vs Graph-Aware, plan time.
**Prior.** `transfer_only` may concentrate roots on the nodes nearest their origin and give the mover more to repair; `mover_aet` is close to the live-state choice that predicted the final node worse than the plan did (live-state replay), but prediction is not what is being tested here.

#### Objective-aligned routers: result (4 Nov 2026; 18 of 18 cases per arm, 0 errors; `capw1_align.py report`)
Rule: success = P99 NOT WORSE vs matcher AND lower cost vs Graph-Aware beta 4 (moves/req ratio CI upper <= 0.90 and relocated-MB/req ratio <= 1.00), per arm. **Result: neither arm succeeds.**
- **`transfer_only`: NOT WORSE, cost not lower.** P99 / matcher **0.973 [0.957, 0.988]**, better in 15/18, cold-start ratio 1.00 (the lowest point estimate of any router so far; CI upper 0.988 > 0.97, so not BETTER by the project rule); P99 / Graph-Aware 0.988 [0.965, 1.008]. Cost vs Graph-Aware: moves/req **1.042 [1.034, 1.051]**, relocated MB/req 1.046 [1.038, 1.055] -- about 4% *more* moves than Graph-Aware in every case, still 2-11% fewer than the matcher. Plan time 0.5-1.4 ms per request (matcher 10-90 ms, Graph-Aware 2.2-6.9 ms). Per case -10% to +4% vs matcher; the losses are F2 r0.7 s3 +4%, F2 r0.7 s1 +2%, F1 r0.85 s3 +1%.
- **`mover_aet`: NOT WORSE, cost not lower by the rule.** P99 / matcher 0.994 [0.978, 1.011], better in 13/18; P99 / Graph-Aware 1.009 [0.985, 1.037]. Cost vs Graph-Aware: moves/req **0.932 [0.868, 1.002]** (CI upper above 0.90), relocated MB/req 0.970 [0.907, 1.039].
- **The cost effect of `mover_aet` depends on load.** At rho 0.5 it has 5-31% fewer moves than Graph-Aware (F1 1.55 / 1.31 / 1.49 vs 2.13 / 1.68 / 1.80; F2 1.14 / 4.47 / 1.46 vs 1.65 / 4.69 / 1.77) and 2-26% less relocated MB; at rho 0.85 it has more on 5 of 6 cases (e.g. F2 s1 2.91 vs 2.51, F2 s2 7.81 vs 6.62). Consistent with the snapshot test: the best node changes more after binding as load rises (44-74% at +2 s), so a live wait estimate at planning helps when the state is stable and hurts when it is not. Observed, not pre-registered.
- Reading: pricing only the exact part (transfer) gives the best P99 point estimate but not fewer moves than Graph-Aware; adding the live wait gives fewer moves at low load only. Graph-Aware stays the lowest-cost baseline across all loads. The router line closes again (the reopening covered this one experiment).

### transfer_only confirmation on fresh seeds 4-6 (pre-registered 4 Nov 2026, before any run; user go-ahead 4 Nov)
**Why.** On the 18 development cases (seeds 1-3) `transfer_only` beat greedy EFT head to head: P99 0.977 [0.963, 0.991] (14/18), moves/req 0.969 [0.948, 0.989], relocated MB/req 0.974 [0.954, 0.995], plan time 0.37x, with the P99 gap growing with load (0.994 / 0.982 / 0.956 at rho 0.5 / 0.7 / 0.85). That comparison was made *after* the results were seen and picked `transfer_only` out of four routers, so it is optimistic. This confirmation decides whether `transfer_only` may replace the matcher as the paper's router.
**Design.** Seeds 4, 5, 6 (never used in any CAP-W1 run), F1/F2 x rho 0.5/0.7/0.85 = 18 cases. Scenarios from `results/d1_headroom/{tag}.pkl`, weighted and normalised exactly as `capw1_light.py prep` (profile weights, agg mean, load-preserving scale; NSGA-II start layout that respects the weights). Three arms on the same scenario, layout, arrivals and seeds, controller `ours` (FROZEN-2, lam 0.5, criticality queue order), only the dispatcher differs: matcher (default), `greedy_eft`, `transfer_only`. Runner `output/data-analysis/capw1_confirm.py`, results `results/capW1_confirm/{tag}.{arm}.json`, capacity model CAP-W1.
**Reading** (cases are the unit; geometric mean of the case ratios, bootstrap 95% CI over the 18 log ratios):
- **C1 (non-inferiority to the matcher):** P99 `transfer_only` / matcher CI upper <= 1.02 and cold-start ratio <= 1.2.
- **C2 (better than greedy EFT):** P99 `transfer_only` / greedy EFT CI upper <= 1.00.
- **CONFIRMED = C1 and C2.** Then `transfer_only` may replace the matcher as the paper's router (the user decides; it would be a new frozen controller name, not a silent edit of FROZEN-2). **Not confirmed:** the matcher stays; the routers are reported as a sensitivity table with the development-case numbers, labelled post hoc.
- Reported, not part of the rule: moves/req and relocated MB/req vs greedy EFT and vs matcher, plan time, BETTER vs matcher (CI upper <= 0.97), the per-load P99 ratios, and the development-case numbers next to the fresh ones.
- No other router arm, no Graph-Aware beta, no re-run with other seeds after the result.

#### transfer_only confirmation: result (4 Nov 2026; 18 of 18 cases x 3 arms, 0 errors; `capw1_confirm.py report`; CAP-W1, seeds 4-6)
**NOT CONFIRMED.** Neither condition is met.
- **C1 (vs matcher): not met.** P99 transfer_only / matcher **0.998 [0.974, 1.029]**, better in 13/18, cold-start ratio 1.00. CI upper 1.029 > 1.02, so non-inferiority is not shown (the point estimate is level with the matcher).
- **C2 (vs greedy EFT): not met, at the boundary.** P99 transfer_only / greedy EFT 0.985 [0.969, 1.0000126], better in 11/18. The upper end is 1.0000126, i.e. 1.3e-5 above the pre-registered 1.00; the rule is applied as written (not met), and the point estimate is not a claim of superiority.
- **The development-case effect did not replicate.** Development cases: 0.973 vs matcher, 0.977 vs greedy EFT, growing with load (0.994 / 0.982 / 0.956). Fresh seeds: 0.998 and 0.985, no load trend (T/G 0.976 / 1.013 / 0.968; T/M 0.968 / 1.010 / 1.016). The 'wins at high load' pattern was a feature of seeds 1-3.
- **Heavy-tailed cases drive the spread.** F2 seeds 5-6 at rho >= 0.7 have P99 vs matcher 1.18 / 0.94 / 1.06 / 1.15 (matcher P99 up to 380 s); the matcher does better on them. The other 14 cases are within about +-5%.
- **Cost and planning time (reported, not part of the rule).** moves/req T/G 0.992 [0.974, 1.012] (no difference), T/M 0.960 [0.934, 0.991]; relocated MB/req T/G 0.997, T/M 0.966 [0.936, 1.000]; plan time 0.03x the matcher (1.5 vs 7-95 ms), 0.96x greedy EFT. greedy EFT / matcher P99 1.013 [0.987, 1.049].
- **Reading.** The router choice is not a P99 lever (matcher ~ greedy EFT ~ transfer_only, all within 2%, CIs overlapping, on two disjoint seed sets). Its leverage is planning time (30x) and a few percent of moves. **The matcher stays in FROZEN-2.** The router comparison is reported as a sensitivity table with both seed sets side by side; the development-case ranking is labelled post hoc. This is the pre-registered stop: no further router arms.

#### Router decision (4 Nov 2026, user decision after the confirmation)
The user chose `transfer_only` as the router of the paper's controller ("good enough"), although the pre-registered confirmation was NOT CONFIRMED (C1 0.998 [0.974, 1.029], C2 0.985 [0.969, 1.0000126]). This is recorded as a **design decision, not a confirmed result**. Basis: P99 level with the matcher on 36 cases (seeds 1-6: 0.973 development, 0.998 fresh; pooled point estimate about 0.985, not tested), 3-4% fewer moves than the matcher, planning 30x faster, simplest rule (input-transfer time only, ties by FST, no wait term). Not claimed: that it improves P99; that it beats greedy EFT or Graph-Aware. The controller is FROZEN-2 with the `transfer_only` dispatcher and keeps its stored seed 1-6 results (`results/capW1_align_transfer_only`, `results/capW1_confirm`); the matcher/greedy EFT/Graph-Aware rows stay as the sensitivity table. Any text must say "chosen for planning cost and simplicity, P99 not distinguishable from the matcher".

### Mover speed-up without behaviour change (4 Nov 2026, user request; implementation only, not a new mechanism)
**Profile** (F1 rho 0.85 s4, 400 s, cProfile): the mover (`rebalance_step`) is 190 s of 214 s wall (89%). It makes 8.2M `Sol.aet` calls in 260 passes; of the cost, `Network.stt` (one call per input state and per child, per candidate node) is 79 s, the `sum` generators 117 s cumulative, `service_estimate` 28 s.
**Change** (`dfps/o3s.py`, `_rebalance_fast`, opt-in `churn["fast_rebal"]`, default off; falls back to the original loop if any diagnostic switch is on): (1) input and output transfer terms vectorised over candidate nodes, accumulated in the original order, so each float is the same; (2) `service_estimate` cached per (function, node, queue length) for the pass (availability entries are constant inside a pass) and the per-host row updated only for the destination of a move; (3) a request's position in its own queue read from the tail (it is always the last, as the loop works from the back) instead of `list.index`; (4) argmin over candidates (first minimum, same tie-break as the strict `<` scan).
**Equivalence check.** Whole result dict compared (all fields except wall-clock ms fields), 250 s runs: F1 r0.85 s4 and F2 r0.5 s5, original versus fast, `transfer_only` dispatcher, FROZEN-2 lam 0.5: **identical** (same moves, 69,576 and 24,754; same P99; every field equal).
**Speed** (two runs at a time on the same machine): F1 r0.85 s4 159 s -> 32 s (4.9x); F2 r0.5 s5 64 s -> 36 s (1.8x). The mover itself went from about 89% of the wall time to about 45% in the profile; the rest is the simulator and the dispatcher.
**Full-length check (900 s, 6 cases, fast path versus the stored `capW1_confirm` transfer_only runs made with the original mover):** F1 r0.85 s4, F2 r0.85 s5, F2 r0.7 s4, F1 r0.7 s5, F2 r0.5 s5, F1 r0.5 s6: **all 6 identical** (every non-wall-clock field equal, including moves 28,939 to 83,345 and P99). Wall time per run 271 -> 47 s, 245 -> 70, 154 -> 37, 123 -> 42, 64 -> 38, 58 -> 29 (stored runs at 5 in parallel, check runs at 6 in parallel). This also shows the rest of the code is unchanged since the confirmation batch.
**Remaining caveat:** the wall-clock controller-latency fields (`adjust_ms_*`) change by design, which matters if the paper reports controller overhead. The flag is still off by default; runs reported in the paper should state which mover implementation produced them (results are identical either way).
**Default and tag (4 Nov 2026, user decision after the 6 of 6 check).** `fast_rebal` now defaults to on (`churn.get("fast_rebal", True)`; any diagnostic switch still falls back to the original loop). Every result carries `mover_impl`: **MV-2** vectorised mover, **MV-1** original loop (untagged results are MV-1), written by `Sim` from the adjuster like `capacity_model`; convention added to CLAUDE.md. Checked after the change: F2 r0.5 s5, 250 s, default (MV-2) and `fast_rebal=False` (MV-1) both reproduce the original reference result field by field. Stored results of earlier batches are MV-1 and stay valid; results can be pooled across the two tags.

### Mover pass order and early stop: counterfactual Gate 0 (pre-registered 4 Nov 2026, before any run; user go-ahead 4 Nov, reopens the mover line)
**Question.** The pass visits (function, node) queues by request count, longest first, walks each from the back and stops a queue at the first request with no improving move. Would a different order or no early stop make different, larger-gain moves? Ordering can matter only through moves that compete: two moves into the same (function, node) queue (found in 98% of passes with moves, 2 Nov), or moves of different functions competing for one node's storage (never measured).
**Variants** (all on the same state, only the pass logic differs; estimate = the mover's own AET, lam 0.5):
- **V0** current: count order, from the back, early stop (re-implemented in the probe; must reproduce the real pass's moves exactly, a self-check).
- **V1** no early stop: V0's order, but a request with no improving move is skipped and the scan continues to the front of the queue.
- **V2** wait order: queues sorted by the estimated queue wait of their back request at pass start (service estimate minus mean run time), longest first; from the back, early stop.
- **V3** gain order (M4): lazy greedy over queues; always take next the queue whose back request has the largest estimated gain (recomputed on pop; accepted only if still at least the next stored gain), early stop per queue.
- **Storage count** (V0): share of evaluated requests where some host is excluded by storage, and share where the best host without the storage limit is storage-blocked (storage changed the decision).
**Design.** Logging only: on every 4th pass the probe runs V0-V3 on fresh copies of the solution state (`Sol(sim)`, side-effect free), then the real pass runs unchanged (MV-2). Event hash and every result field must equal the stored run (`results/capW1_align_transfer_only`, MV-1), proving the probe is inert. 18 CAP-W1 development cases (seeds 1-3), controller FROZEN-2 + `transfer_only` dispatcher (the user's router decision). Runner `output/data-analysis/order_cf.py`, results `results/order_cf/`.
**Metrics per variant vs V0**, pooled per (family, load) cell over seeds and sampled passes: (a) share of moves that differ, 1 - |V0 & Vx| / max(|V0|, |Vx|), a move = (request, task, destination); (b) moves ratio; (c) summed estimated gain ratio (gain = staying estimate minus best estimate at the moment of the move).
**Reading, fixed now.** A variant goes to an online 18-case run only if (a) >= 5% AND (c) >= 1.05 in at least 4 of the 6 cells. Otherwise it is dead (no run). The estimated gain is used because it ranks the realised benefit of moves (veto test); it is not P99, so a variant that passes must still win P99 online (NOT WORSE / BETTER rule of this file). Storage count: if the storage limit changes fewer than 1% of decisions, ordering across functions cannot matter and only the within-function order is relevant.

#### Mover pass order and early stop: result (4 Nov 2026; 18 of 18 runs, 0 errors; `order_cf.py report`; CAP-W1, MV-2)
**Checks.** Probe inert: all 18 runs equal the stored `capW1_align_transfer_only` runs field by field. V0 reproduces the real pass's moves in 954 of 954 sampled passes (measured window).
**By the pre-registered rule all three variants are dead** (cells passing, need 4 of 6: V1 0/6, V2 0/6, V3 3/6).

| cell | V0 moves/pass | V1 differ / gain | V2 differ / gain | V3 differ / moves / gain | storage changed decision |
|---|---|---|---|---|---|
| F1 r0.5 | 150 | 0.7% / 1.001 | 5.3% / 1.000 | 27.0% / 0.982 / 1.015 | 0.000% |
| F1 r0.7 | 262 | 2.4% / 1.001 | 18.1% / 1.003 | 49.8% / 0.947 / 1.047 | 0.006% |
| F1 r0.85 | 355 | 4.1% / 1.001 | 36.7% / 1.006 | 63.7% / 0.894 / **1.064** | 0.466% |
| F2 r0.5 | 152 | 0.6% / 1.000 | 7.0% / 1.001 | 25.0% / 0.984 / 1.016 | 0.000% |
| F2 r0.7 | 267 | 2.0% / 1.000 | 24.0% / 1.004 | 49.0% / 0.943 / **1.052** | 0.065% |
| F2 r0.85 | 370 | 3.5% / 1.000 | 43.9% / 1.009 | 63.0% / 0.889 / **1.068** | 0.444% |

- **V1 (no early stop): the early stop is sound.** Scanning to the front of the queue finds 0.2-1.1% more moves and 0.0-0.1% more estimated gain. Requests ahead of the first non-mover almost never have an improving move.
- **V2 (wait order instead of count order): different moves, same gain.** It changes 5-44% of the moves but adds at most 0.9% estimated gain. Count and wait order pick different requests for the contested destination slots, of about equal value.
- **Storage hardly ever decides** (at most 0.47% of evaluations, at rho 0.85), so ordering across functions cannot matter; only the order within a function's queues does (as reasoned before the run).
- **V3 (gain order, M4): close to the bar at high load, not over it.** 5-7% more estimated gain with 5-11% FEWER moves at rho >= 0.7 (gain per move +11 to +20%); passes the bar in 3 of 6 cells (F1 r0.7 misses at 1.047), +1.5% at rho 0.5. Observed, not part of the rule: the effect grows with load. Caveats: the gain is the mover's own estimate summed within one pass, on the same state; the next pass starts from a different state online, and the estimate is not P99.
- Reading: the current pass logic (count order, from the back, early stop) leaves little on the table on its own estimate; the only ordering with headroom is gain order, at high load, and it misses the pre-registered bar. No online run follows from this rule.

### V3 follow-up: gain-ordered move selection online (pre-registered 4 Nov 2026, before any run; user's wording, user go-ahead 4 Nov)
**Status of this test.** The post-hoc concern is acknowledged: by the Gate 0 rule above V3 was dead (3 of 6 cells passing, the bar was 4 of 6). This is a **pre-registered follow-up of a diagnostic signal, not a post-hoc claim**. The trace-only result it follows up: V3 showed +5-7% extra estimated gain and 5-11% fewer moves at rho >= 0.7, 3 of 6 cells passing the 4 of 6 bar, a narrow miss at F1 rho 0.7 (1.047 vs 1.05).
**Hypothesis.** Gain-ordered move selection reduces moves per request at rho >= 0.7 without worsening P99.
**Test.** 12 CAP-W1 cases: F1/F2 x rho 0.7/0.85 x seeds 1-3 (the seeds of the primary development suite). Arm: FROZEN-2 + `transfer_only` dispatcher, mover pass in gain order (V3 of the Gate 0: lazy greedy over queues by the estimated gain of their back request, recomputed on pop, early stop per queue; `churn["pass_order"] = "gain"`). Comparison: the current mover with the same dispatcher (stored `results/capW1_align_transfer_only`, which MV-2 reproduces field by field). Runner `output/data-analysis/v3_online.py`, results `results/v3_online/`.
**Success criteria** (geometric mean of the 12 case ratios, bootstrap 95% CI):
- P99 not worse: gm ratio CI upper <= 1.02.
- Moves per request >= 5% lower: gm ratio CI upper <= 0.95.
- Both must hold.
**Consequence, fixed now.** This is the last mover experiment. If it fails: report the trace-only probe result (V3 shows a directional signal but does not clear the online test) and close the mover line permanently. If it passes: report it as a cost improvement and move to writing. No further mover variants regardless. Reported, not part of the rule: cold starts, relocated MB per request, per-case ratios, and rho 0.7 and 0.85 separately.

#### V3 follow-up: result (4 Nov 2026; 12 of 12 cases, 0 errors; `v3_online.py report`; CAP-W1)
**FAIL.** P99 not worse: **not met**, gain-order / current **1.008 [0.985, 1.037]** (CI upper above 1.02), better in 7 of 12. Moves per request >= 5% lower: **met**, **0.922 [0.907, 0.938]**, lower in 12 of 12; relocated MB/req 0.923 [0.909, 0.938]; cold starts unchanged (ratio 1.00).
- By load: rho 0.7 P99 1.016, moves/req 0.948; rho 0.85 P99 0.999, moves/req 0.896. The cost effect grows with load, as in the probe.
- The P99 interval is widened mainly by F2 r0.7 s3 (+14.6%, 120.3 -> 137.9 s); the other 11 cases range -4.7% to +4.8%. Not grounds to re-read the rule.
- **Reported as pre-registered:** V3 shows a directional signal (trace-only: +5-7% estimated gain, 5-11% fewer moves at rho >= 0.7; online: 8% fewer moves and 8% less relocated data in 12 of 12 cases) but does not clear the online test, because P99 non-inferiority is not shown.
- **Mover line closed permanently** (pre-registered consequence; no further mover variants). The current mover (count order, from the back, early stop; MV-2) stays. `churn["pass_order"] = "gain"` remains in the code, default off.

### V3 confirmation on fresh seeds 4-6 (pre-registered 4 Nov 2026, before any run; user go-ahead 4 Nov, reopens the mover line closed above)
**Why.** The V3 follow-up failed its pre-registered P99 bar (1.008 [0.985, 1.037]) but cut moves in 12 of 12 cases (0.922 [0.907, 0.938]); a look at the other makespan percentiles **after** the result (not pre-registered, four metrics inspected) found median 0.982 [0.975, 0.988] (12 of 12 better), mean 0.987 [0.978, 0.997], P95 0.995 [0.982, 1.007]. This is a lead from a post-hoc look; this test decides it on fresh data.
**Design.** 12 new runs: gain-ordered mover (`churn["pass_order"] = "gain"`), FROZEN-2 + `transfer_only`, F1/F2 x rho 0.7/0.85 x seeds 4-6 (never used for V3). Comparison: the current mover with the same dispatcher on the same cases (stored `results/capW1_confirm/{tag}.transfer_only.json`). Runner `output/data-analysis/v3_confirm.py`, results `results/v3_confirm/`, CAP-W1.
**Criteria** (geometric mean of case ratios, bootstrap 95% CI over cases):
1. Moves per request, fresh 12 cases: CI upper <= 0.95.
2. Median makespan, fresh 12 cases: CI upper < 1.00.
3. P99, pooled 24 cases (seeds 1-3 from the follow-up and seeds 4-6): CI upper <= 1.02.
**CONFIRMED = all three.** Then gain order may be adopted as a tested cost and median improvement with a non-inferior tail. **Otherwise** the current mover stays and gain order is reported only as a discussion point (directional cost signal), and the mover line closes. No further mover variants either way.

#### V3 confirmation: result (4 Nov 2026; 12 of 12 fresh runs, 0 errors; `v3_confirm.py report`; CAP-W1)
**NOT CONFIRMED** (criteria 1 and 2 met, 3 not met).
1. Moves per request, fresh: **0.922 [0.903, 0.940]**, lower in 12 of 12 -- met (replicates the follow-up's 0.922 exactly).
2. Median makespan, fresh: **0.985 [0.979, 0.991]**, better in 12 of 12 -- met (replicates the post-hoc 0.982; over both seed sets the median is better in 24 of 24).
3. P99 pooled over 24 cases: **1.003 [0.984, 1.026]** -- not met (CI upper above 1.02); fresh alone 0.999 [0.969, 1.032].
- Also: mean 0.990 [0.983, 0.997], P95 1.000 [0.987, 1.014], cold starts unchanged.
- Per case P99 moves both ways: -7.1% to +11.8% on fresh seeds (F2 r0.85 s6 +11.8%, F1 r0.85 s5 +8.9%, F2 r0.7 s6 +6.9%; F2 r0.7 s5 -7.1%, F2 r0.85 s5 -5.5%). Gain order does not shift the P99 on average (point estimate 1.003) but changes individual tails by several percent in either direction, so non-inferiority within 2% is not shown.
- **Reading, as pre-registered:** the current mover stays. Gain order is reported as a discussion point: across 24 cases it cuts moves by about 8% and the median makespan by about 1.5-2% in every case, with the P99 not distinguishable from the current mover but not shown within 2%. Mover line closed; no further mover variants.

#### Mover decision (4 Nov 2026, user decision after the V3 confirmation)
The user adopted the gain-ordered pass ("the reduction in cost is consistent"), although the confirmation was NOT CONFIRMED on P99. Recorded as a **design decision, not a confirmed result**. The paper's controller is now **FROZEN-3** = FROZEN-2 + gain-ordered pass + `transfer_only` dispatcher (`output/data-analysis/frozen2.py`: `FROZEN3`, `FROZEN3_DISPATCHER`); results record `mover_pass`. Basis: moves per request -8% and median makespan -1.5 to -2% in 24 of 24 cases, mean -1%, cold starts unchanged. Not claimed: any P99 improvement; P99 within 2% of the count-order mover (1.003 [0.984, 1.026]). Text must say "chosen for lower move cost; P99 not distinguishable from the count-order pass, non-inferiority within 2% not shown; individual-case P99 varies by -7% to +12%". FROZEN-3 results already exist for 24 cases at rho >= 0.7 (`results/v3_online`, `results/v3_confirm`); rho 0.5 has none.
