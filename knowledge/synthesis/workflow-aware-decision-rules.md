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
