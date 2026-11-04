---
title: "Heterogeneous container sizes: audit of the uniform-slot assumption and the change"
type: synthesis
created: 2026-11-02
updated: 2026-11-02
status: review
author: llm
tags: [capacity-model, container-size, audit, profiles, placement, baselines]
sources:
  - "[[zolfaghari-2025-dynamic-function-placement]]"
  - "[[jia-2025-faaspr]]"
  - "[[schmid-2025-sebs-flow]]"
bibliography: ../../output/bibtex/references.bib
---

# Heterogeneous container sizes: audit of the uniform-slot assumption and the change

## Why this page exists
Until 2 Nov 2026 every experiment ran on a capacity model in which a node `k` holds `ecc_k` containers and every
container, whatever its function, occupies one slot. That was presented as DFPS's model. Checking the paper (physical
p. 4, Sec. 3.1) shows what it actually says: "Each container requires a fixed, specific amount of CPU and memory
resources. Therefore, each edge e_k can accommodate a limited number of containers based on its available resources,
which is denoted by ecc_k (container capacity)." That bounds the number of containers per node. It does not say that all
functions are one size, and no per-function sizes are published (the parameter table has `ecc` 5-25 and storage 10-30 GB,
nothing per function). One slot per container was our reading; real functions differ in size, so the reading is retired.
See [[problem-scope]] section 2 for the model.

## The new model
- Each function has a container weight `w_f` (`Scenario.fw`); a node holds any containers whose weights sum to at most
  `ecc_k`. `ecc_k` is in units of the average container, so total capacity stays comparable with the uniform runs.
- **Weights come from profiles** (`dfps/profiles.py`): Alibaba cluster-trace-v2018 `plan_mem` per task
  ([[alibaba-cluster-trace]]) and the per-workflow `memory` setting of each SeBS-Flow benchmark ([[schmid-2025-sebs-flow]]).
  The DFPS Fig. 1 workflow has no published profile and takes the reference size.
- Memory is the capacity dimension (a warm container holds it whether it runs or not). `plan_cpu` is kept in the profile
  file for the contention extension and does not enter `w_f`.
- Scales: each source is divided by its own median (Alibaba 0.30 over all 6,298,698 kept tasks; SeBS-Flow 640 MB), then a
  function takes the **mean** over the tasks mapped to it, clipped to [0.25, 4] and normalised to mean 1 over the functions
  in use. **These are assumptions, not measurements.** `max` is available but saturates under the random task-to-function
  pool (A-16): on one development scenario 14 of 30 function types took the weight of the one large SeBS-Flow workflow.
- Result on the 18 development scenarios: weights run from 0.27 to 2.33 (coefficient of variation 0.47-0.54). The exact
  job behind each workflow is recovered by replaying the scenario build and checking it against the pickle (0 ambiguous in
  all 18); new scenarios record `meta['workflow_jobs']`.
- With real-valued weights a node cannot be filled exactly. DFPS invariant D-7 ("every slot always holds an instance")
  becomes "no container of any function still fits"; in the uniform case nothing changes.

## Audit: where the assumption lived, and what was done
Status: **changed** = weight-aware now, uniform path unchanged; **guarded** = raises `NotImplementedError` on a weighted
scenario instead of silently overfilling; **open** = not touched, listed so it is not forgotten.

| Where | What assumed one slot per container | Status |
|---|---|---|
| `dfps/model.py` `Scenario.fw` | (the weight vector; default all ones) | existing since 27 Oct |
| `dfps/sim.py` `Sim.__init__`, `add_instance` | capacity check | already weighted (27 Oct); new flag `Sim.hetero` |
| `dfps/sim.py` `apply_placement` | pairs removals with additions 1-for-1 (swap) | **changed**: weighted layouts apply as removals, then additions |
| `dfps/sim.py` `check_invariants` | D-7 exact fill | **changed**: weighted final capacity <= `ecc_k` |
| `dfps/sim.py` `results` (utilisation), `traces.scale_to_rho` | capacity = `ecc.sum()` containers | **open**: now capacity units. `rho` is offered busy-container-seconds per capacity unit; with mean weight 1 it is close but not identical to a container-count load |
| `dfps/sa.py` `compute_neighbor` (B* annealing) | a replacement leaves the node's capacity unchanged | **changed**: a replacement that does not fit is rejected |
| `dfps/nsga2.py` `random`, `mutate`, `proportionality` (B* start layout) | multinomial draw of `ecc_k` slots; +1/-1 mutation; FEN uses slot share | **changed**: draws until nothing fits; mutation must fit; FEN = `S mu_l / sum mu fw` (printed formula when `fw` = 1) |
| `experiments/run.py` `initial_placements` | called NSGA-II without sizes | **changed**: passes `fw` |
| `dfps/controllers.py` `queue_aware_placement` (our placement) | free slots, counts sum to slots | **changed**: free capacity in weight units, a container must fit, evict-lightest-donor if nothing fits, post-fill with best-gain container that fits |
| `dfps/controllers.py` `proportional_counts`; `o3s.bottleneck_first_placement` sizing | | already weight-aware (27 Oct) |
| `dfps/o3s.py` `_fit_counts`, `baseline_layout` (HPA/Fifer/Kraken swaps) | slot budget | **changed**: pass `fw` |
| `controllers.py` `affinity_placement_v2`, `transport_placement`, `kmedian_placement`, `affinity_greedy_placement`, `faaspr_placement` | fill every slot of every node | **guarded** (decorator `_uniform_only`) |
| `dfps/o3s.py` `random_placement` (ablation) | | **guarded** |
| `dfps/ondemand.py` `OnDemandSim` (Heu, RL) | `tot >= ecc`, `ecc - occ` free slots | **changed**: room for a container = weights fit, idle containers of other functions recycled (LRU) until it fits, all-or-nothing; `prewarm` (look-ahead cheater) refuses |
| `dfps/heu.py`, `dfps/rl.py`, `dfps/rlla.py` | policies read `sim.ecc`, `sim.tot` as slot counts (RL's network was trained on them) | **open, by design**: the published methods are size-blind; they see capacity in average-container units and the simulator enforces real sizes |
| `dfps/o3s.py` `limit_changes` | 1-for-1 replacement pairs | **open**: used only when a change cap is set; the frozen controller sets none |
| `dfps/controllers.py` `QueueThresholdAdmission`, `dfps/d3.py`, `dfps/oracles.py` | `theta x ecc.sum()`, slot counts | **open**: not reviewed |

## Effect on earlier results
Every number in the deck and the wiki to date (slides 2 and 34, the 2x2 and one-at-a-time decomposition, the held-out
check) was measured under **uniform capacity**. Which of them survive unequal sizes is not known; sizing and placement
both interact with packing. The comparison between methods was like-for-like (one simulator, one capacity model), so the
ranking is not in question by this alone, but the size of the gains may be.

## Checks run
- `tests/test_hetero.py` (8 tests): defaults are ones; NSGA-II draws and mutations fit and are maximal; weighted
  `proportional_counts` fits; weighted `queue_aware_placement` is feasible, filled to within the lightest container and
  incremental; the equal-size-only rules refuse; a weighted `Sim` and `apply_placement` keep the invariants; a weighted
  `OnDemandSim` never exceeds capacity. The existing 78 tests pass file by file (the combined `pytest` run crashes in
  this environment before it reports, independent of these changes).
- Smoke: B* with annealing on a profiled development scenario runs 150 s with invariants intact.
- Uniform path: an end-to-end re-run of a stored development case (2x2 grid cell D, F1 rho 0.5 seed 1, 900 s, full
  controller) under the changed code gives the same event hash and the same P99 (99.127 s) as the stored run.

## Evidence base
[[zolfaghari-2025-dynamic-function-placement]] (the sentence and the parameter table), the Alibaba v2018
`batch_task` table ([[alibaba-cluster-trace]]) and SeBS-Flow `config.json` memory settings ([[schmid-2025-sebs-flow]]);
FaaSPR ([[jia-2025-faaspr]]) is the one baseline that models container sizes natively. Code: `dfps/profiles.py`,
`experiments/extract_alibaba_profiles.py`, `data/alibaba_dags_lt60s_profiles.json`.

## What stays open
- No weighted scenario set, initial layouts or runs exist yet; nothing above has been measured on weighted scenarios beyond
  smoke tests. The next step is to build them for the 18 development cases and rerun the controller, B*, Heu and RL.
- Mean versus max over a function's tasks, and mixing two profile sources by their own medians, are choices that need a
  sensitivity run.
- Alibaba `plan_mem` is a normalised fraction of an unspecified machine; no absolute container sizes follow from it.
- Heu and RL stay size-blind; whether a size-aware variant of either is a fairer baseline is a decision for the project.
- CPU contention is not modelled; `plan_cpu` is stored but unused.

## Capacity-model versions (named 2 Nov 2026, so every experiment says which one it used)
| Version | Definition | Used by |
|---|---|---|
| **CAP-U** | Uniform slots: every container, whatever its function, takes one slot; a node holds `ecc_k` containers (5-25). Our earlier reading of DFPS Sec. 3.1. | Every experiment, deck number and wiki result up to 2 Nov 2026 (no capacity tag = CAP-U). |
| **CAP-W1** | Weighted: function `f` has container weight `w_f`; a node holds any containers with `Σ w_f ≤ ecc_k`. Weights from the profiles (`dfps/profiles.py`, `agg="mean"`, clip [0.25, 4], mean 1 over the functions in use), then **scaled once per scenario so the offered load in capacity units equals the nominal load** (load-preserving normalisation; without it the same arrivals load the cluster more, because busy functions are on average heavier: 0.70 -> 0.87 on F1 70% seed 1). | `output/data-analysis/capw1_light.py`, results in `results/capW1_light/` (every scenario has `meta['capacity_model'] = "CAP-W1"`, every result file `capacity_model`). |

Rule from now on: a script or result directory that uses weighted sizes carries the version in its name or metadata; a later change of the weight model (another aggregation, CPU as a second dimension, a different normalisation) becomes CAP-W2 and so on, never a silent edit of CAP-W1.

## Consistency fixes made before the light test (2 Nov 2026; equal-size behaviour unchanged, checked by event hash)
- **Dropped container additions (ours).** `Sim.apply_placement` on weighted scenarios removed, then added; when a removed container was still busy, its capacity stayed held until the run ended and the addition was silently dropped (`n_add_blocked`), so the controller's layout was not realised. Now the addition joins the count and waits for room (`Sim.pending_add`), and starts as soon as the busy container leaves (`n_add_deferred` counts these).
- **Conversions could overfill a node (B*).** A busy instance replaced by the annealing converts when its run ends; with unequal sizes the new container could exceed the node next to other instances still waiting to convert (the invariant only checked the final counts). Now it waits for room in the same way, and `check_invariants` also checks live capacity.
- **Waiting containers are visible to the estimates.** `live_availability` reports a waiting container (available when the first leaving instance ends, plus its cold start), and a replacement of a waiting container re-targets it; before, B*'s annealing crashed on a counted container with no instance.
- **B*'s trial on a misfit.** DFPS draws the new function at random; with sizes it may not fit after removing one instance. The trial now redraws among the functions that fit (never `f_r`) instead of wasting the trial; with equal sizes everything fits and nothing changes.
- **Our controller called an equal-size-only rule.** `O3SimAdjuster.candidates` computed the published affinity layout on every re-layout and discarded it in the frozen (`nosim`) mode; on weighted scenarios that rule refuses. It is now computed only in the modes that use it (deterministic, so no result changes).
- Request moves need no change: they move requests between existing containers and never place one; their storage check is unchanged.
- Still open: Heu and RL stay size-blind (not in the light test); the admission rule and oracles still count slots.

## Light test: ours and B* on CAP-W1 (pre-registered 2 Nov 2026, before any full-length run; smoke test only)
The 18 development cases (F1/F2 x 50/70/85% x seeds 1-3); per case the stored scenario and arrivals, CAP-W1 weights, a new NSGA-II start layout that respects them, then ours (cell D: frozen controller, lam 0.5, criticality dispatch) and B* (period as in its stored CAP-U run) on the same scenario, layout and seeds. One run per controller and case (36 runs). Primary metric P99 makespan; reference = the stored CAP-U runs of the same case (ours: grid2x2_v2 cell D; B*: d1_headroom).
Reading, fixed now: ratio r = P99(ours) / P99(B*) per case.
- **SURVIVES** if ours is lower than B* in at least 16 of 18 cases and the geometric mean of r is at most 0.5; **REVERSED** if the geometric mean of r is 1 or more; otherwise **SHRINKS**.
- **Change of the gap**: d = log(r_CAP-W1 / r_CAP-U) per case, 95% bootstrap interval over the 18 cases. The gap **grows** if the interval is entirely below 0, **shrinks** if entirely above 0, otherwise no detectable change. Caveat stated now: the start layout differs (a new NSGA-II run per case), and one run per case carries the run-to-run noise of about 1.5-3% per case, so d mixes the size effect with the layout and noise; the light test can show a large change, not a small one.
- Reported, not a bar: per (family, load) cell, cold starts, moves per request, deferred additions, the raw (unscaled) weighted load.

### Light test, extension: Heu and RL on CAP-W1 (pre-registered 2 Nov 2026, user request, before their runs; ours and B* still running)
Same 18 CAP-W1 scenarios. Heu and RL run as in their stored CAP-U runs (`results/d1_baselines/`): empty start (no initial placement), same seeds and policy file (`results/rl_policy.pt`, trained under CAP-U). Their policies stay size-blind (they read capacity as average-container units); the simulator (`OnDemandSim`) enforces the real sizes: a new container starts only if it fits, idle containers of other functions are recycled least-recently-used first until it does, otherwise the run waits. Reading, per baseline b in {Heu, RL}: r_b = P99(ours) / P99(b) per case; reported as wins and geometric mean under CAP-U and CAP-W1, and the change d_b = log(r_b,W / r_b,U) with a 95% bootstrap interval: gap over b **grows** if the interval is below 0, **shrinks** if above 0, otherwise no detectable change. Same caveats as above (one run per case; Heu is slow, so its cases may finish later and are reported as they complete).

### Light test, interim diagnosis (2 Nov 2026): why ours lost most of its edge at 85% load, and the fix
Interim result (17 of 18 cases, pre-fix): ours still below B* in 17 of 17, geometric-mean ratio 0.24 (CAP-U) -> 0.21 (CAP-W1), but by load the gap widened at 50-70% and narrowed at 85% (F1 0.17 -> 0.37, F2 0.17 -> 0.24), where our P99 rose 2-3x (e.g. 147 -> 486 s) with 2x the cold starts and reroutes and 2-4x the warm-idle capacity.
**Cause: a sizing bug in `proportional_counts` (our autoscaler stand-in), not the mechanisms.** When the containers the load needs do not all fit (`Σ need x w > S`, which with CAP-W1 happens exactly at 85% load: 1,337 of 1,230 capacity units on F1 85% seed 3, but not at 70%: 1,088), the budget is cut back in proportion to each function's busy-container count, then each function gets share / w_f containers. Capacity should follow demand x weight; sharing by count gives a heavy function fewer containers than its load needs and a light one too many. Offline on F1 85% seed 3: 11 of 30 functions above 95% utilisation (maximum 1.69, i.e. overloaded), utilisation correlated +0.99 with the weight; with the share in proportion to demand x weight, maximum 0.88 and none above 0.95. At 70% the needs fit and the cut-back branch is not taken, which is why the problem appears only at 85%. Fixed in `dfps/controllers.py::proportional_counts` (share in proportion to `demand x fw`; identical when fw is all ones). B*, Heu and RL do not use this function.
Consequence: the 18 CAP-W1 runs of ours made before the fix are invalid for the reading; they are moved to `results/capW1_light/pre_sizing_fix/` and ours is re-run on all 18 cases (the leftover share at 50-70% changes too). B* runs stay valid.

### Light test, result: ours vs B* on CAP-W1 after the sizing fix (2 Nov 2026; 18 of 18 cases)
- **Verdict (pre-registered): SURVIVES.** Ours is below B* in 18 of 18 cases. The geometric-mean ratio P99(ours)/P99(B*) goes from 0.24 (CAP-U) to 0.15 (CAP-W1).
- **The gap grows**: d = log(r_W / r_U), mean −0.48 (×0.62), 95% CI [−0.64, −0.33]. By cell (CAP-U → CAP-W1):
  - F1: 50% 0.44 → 0.22; 70% 0.20 → 0.14; 85% 0.17 → 0.12.
  - F2: 50% 0.31 → 0.17; 70% 0.21 → 0.14; 85% 0.20 → 0.12.
  The 85% narrowing seen before the fix is gone.
- **Where the change comes from: mostly B*.**
  - Ours' P99 is almost unchanged (mean 127.6 → 123.9 s, geometric-mean change ×0.97).
  - B*'s P99 rises by ×1.57 (579 → 909 s), and B* has 5.5× our cold starts (11,556 vs 2,091 per run).
  - Not diagnosed yet: why B* degrades under sizes. The guess is that its SA swaps now have to respect fit, but this is not tested.
- **Caveats** (as pre-registered): one run per case, and a new NSGA-II start layout per case. So d mixes the size effect with the change of layout. The noise floor (~1.5–3% per case) is far below the observed change.
- **Also seen:** the raw (unscaled) weighted load differs from nominal in some seeds, e.g. F1/F2 seed 1 at 85% would be 1.05–1.08. The load-preserving scaling removes this by design.
