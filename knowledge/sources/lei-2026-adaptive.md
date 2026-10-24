---
title: "Lei et al. 2026 — Adaptive container scheduling for serverless workflows in cloud-edge collaborative computing (AUHS)"
type: source
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
bibkey: lei-2026-adaptive
depth: standard
tags: [serverless-workflows, cloud-edge, container-scheduling, novelty-gate-g0]
relations:
  - target: auhs
    type: mentions
    confidence: extracted
    because: "Proposes AUHS, an adaptive user-satisfaction-driven heuristic scheduler (abstract, p. 1)."
  - target: mean-user-satisfaction
    type: mentions
    confidence: extracted
    because: "MUS is the single optimisation objective (Eq. 1 and 4, p. 4)."
  - target: edgecloudsim
    type: cites
    confidence: extracted
    because: "Evaluation runs on a simulated testbed built on EdgeCloudSim [39] (Sect. 5.1.4, p. 10)."
  - target: alibaba-cluster-trace
    type: cites
    confidence: extracted
    because: "Workflow topologies reconstructed from the Alibaba Cluster Trace [35,36] (Sect. 5.1.1, p. 9)."
---

# Adaptive container scheduling for serverless workflows in cloud-edge collaborative computing

## Bibliographic Details
Lei, Yamin; Hou, Yucheng; Zhang, Yixin; Wang, Shuang. 2026. *Adaptive container scheduling for serverless workflows in cloud-edge collaborative computing*. *Journal of Parallel and Distributed Computing* 216: 105308 (14 pp.; received 7 Jan 2026, accepted 25 Jun 2026). https://doi.org/10.1016/j.jpdc.2026.105308. Page numbers below are the 14 printed article pages.

## Section map

| Covered | Section | pp. |
|---|---|---|
| ✓ F1 | 1. Introduction (challenges i-iii, contributions) | 1-2 |
| ✓ F1 | 2. Related work (static vs semi-dynamic vs dynamic "schedule-while-planning") | 2 |
| ✓ F1 | 3. System architecture and problem description (3.1 architecture, 3.2 MUS model, constraints Eq. 5-11) | 2-4 |
| ✓ F1 | 4.1 Batch-level optimal scheduling sequence (sub-deadline decomposition, task sorting, BOSSG) | 4-6 |
| ✓ F1 | 4.2 Function-level optimal scheduling plan (offloading and container reduction, OSP selection, worked example) | 5-9 |
| ✓ F1 | 4.3 Formal description of AUHS (Algorithm 2, complexity) | 9 |
| ✓ F1 | 5.1 Experimental setup (scenarios, baselines, metrics, EdgeCloudSim) | 9-10 |
| ✓ F1 | 5.2 Component calibration (ANOVA) | 10-11 |
| ✓ F1 | 5.3 Sensitivity to scenario configurations | 11 |
| ✓ F1 | 5.4 Performance comparison (effectiveness, efficiency) | 11-13 |
| ✓ F1 | 6. Conclusions and future work | 13 |

## Kernthesen

### 1. ⭐⭐ The objective is mean user satisfaction (MUS), not cost or energy (pp. 1, 4)
User satisfaction of a workflow is 1 if makespan is within the soft deadline and decays linearly to 0 at a maximum permissible completion time controlled by a tolerance factor (Eq. 1); MUS is its mean over all workflows (Eq. 4). The authors argue provider-centric metrics miss the "progressive degradation of user satisfaction" (p. 1). Cost is explicitly left to future work (p. 13).

### 2. ⭐ Three-level workflows are scheduled at function granularity on containers (pp. 1-3)
Workflow, tasks, functions; functions of a task run in parallel in single-concurrency containers (Eq. 11) on one cloud plus |E| edge base stations (EBSs). Containers are instantiated on demand and live only a keep-alive period after execution (p. 2). The authors say this short life cycle "tightly couples container selection with function offloading decisions" (p. 2).

### 3. ⭐ Fully online, stateless, interval-based scheduling; no re-planning (pp. 2, 4, 9)
The related work rejects static plan-then-schedule and semi-dynamic strategies ("frequent adjustments introduce additional computational and communication overhead", p. 2). AUHS decides per scheduling interval; each function's plan is stateless ("previous OSPs do not affect the current decision", p. 4). Placed functions are never revisited.

### 4. Slack-based sub-deadline decomposition using critical-path dynamic programming (pp. 4-5)
Workflow slack = deadline minus earliest completion duration (Eq. 12), computed by critical-path DP over earliest start times (Eq. 13), with task execution time approximated by the maximum function time (Eq. 14). Three splitting rules: depth-based (DSD), earliest-completion-duration-based (ESD), weighted (WSD, Eq. 15).

### 5. ⭐ Cross-workflow iterative task sorting (p. 5)
Ready tasks from all workflows are sorted jointly each interval, not workflow by workflow, so urgent tasks are not delayed by backlogged less urgent ones. Priority rules: most successors first, most diverse functions first, earliest sub-deadline first (ESF). Calibration picks ESF (p. 11).

### 6. ⭐ Function-level plan = offloading location x container mode, reduced to seven candidates (pp. 5-7)
Locations: local EBS, nearest remote EBS, cloud. Container modes: new container (cold start), idle reuse, wait for a busy container. Seven feasible combinations; the minimum end-to-end non-execution latency (offloading time + container waiting time, Eq. 23-24) wins. Image fetching and function transmission cost are modelled from size, bandwidth and distance (Eq. 16-19).

### 7. Image availability at EBSs is the performance bottleneck (p. 11)
Image cache capacity per EBS is a fixed scenario parameter (4-20); with small capacity more functions are offloaded and MUS falls, "especially under high-load scenarios" (p. 11). Which images are cached where is not optimised by AUHS; it only fetches an image when cache space permits (Eq. 16, p. 6).

### 8. Keep-alive time is an input parameter, not a decision (pp. 9, 11)
Keep-alive in {2, 8, 14, 20} s (Table 3); MUS improves with longer keep-alive but saturates beyond 8 s (Fig. 6c, p. 11).

### 9. Graceful degradation with arrival rate (p. 11)
"The monotonic trend indicates that the scheduling performance of AUHS degrades progressively rather than collapses abruptly" (p. 11). No mechanism limits load; congestion simply lengthens queues.

### 10. Headline results (pp. 1, 11, 13)
Averaged over 1280 instances: MUS 0.91 vs 0.74-0.87 for HEFT/SKIPPY/IGA/PPO; DSR 77.43% vs 51-67%; mean tardiness 1.50 s vs 2.20/1.85/4.72/3.55 s (row assignment read from the extracted table, whose column headers were partly lost). The abstract claims at least +4.60% MUS, +15.14% DSR, -18.92% tardiness and +10.13% scheduling efficiency. SKIPPY beats AUHS on MUS at lambda = 20/s (p. 12).

### 11. Component calibration by ANOVA (pp. 10-11)
WSD with weight 0.6 and ESF give the best MUS over 23,040 test instances; DSD underperforms because shallow but heavy tasks get too little slack (p. 10).

### 12. Complexity and overhead (pp. 9, 13)
Slack computation in BOSSG dominates complexity; AUHS mean scheduling overhead is 86.79% below SKIPPY and 98.94% below PPO (p. 13).

### 13. Stated limitations (p. 13)
Only MUS, no joint cost optimisation; simulation only; real-platform validation under "network fluctuations and EBS failures" left open.

## Figures and tables
Fig. 1 framework (p. 3); Table 1 nomenclature (p. 3); Fig. 2-3 worked example and Gantt (pp. 7-8); Table 2 OSP latencies for 8 functions (p. 7); Table 3 parameters (p. 9); Fig. 4 workflow topologies (p. 10); Fig. 5-6 ANOVA mean plots (p. 11); Table 4 results (p. 11); Fig. 7-10 comparisons (pp. 12).

## What this source does not address
No demand forecasting, no robustness or worst-case guarantee, no admission control or load shedding, no reconfiguration trigger, no queueing-theoretic capacity model, no data or state transfer between tasks (inter-task communication delays are ignored, p. 4), no scale-to-zero cost trade-off or cost objective at all. No comparison with DFPS (Zolfaghari et al. 2025): the reference list (40 items, pp. 13-14) does not contain it. The closest edge-FaaS neighbours it does treat are SKIPPY ([14], Rausch et al.; library key rausch-2021-optimized) and the PPO function scheduler [26].

## Focus: Novelty gate G0 for plan faas-edge-adaptation (when to reconfigure, forecasts with guarantees, overload admission, placement-dispatch coupling) — 2026-10-13

**Carries Kernthesen 3, 5, 6, 7, 8, 9, 10, 13.**

### What this focus needs beyond the Kernthesen
- **(a) When to reconfigure: not addressed.** AUHS decides at the end of each scheduling interval (Algorithm 2, p. 9) and each plan is stateless (p. 4); re-planning is dismissed as costly (p. 2). Keep-alive and image cache are fixed inputs (Table 3, p. 9). No event- or cost-triggered replacement; nothing is reconfigured.
- **(b) Forecasts and robustness: absent.** The paper says prior knowledge of workflows is "rarely available" (p. 2) and uses none; arrivals are generated as Poisson (p. 9) but never predicted. No worst-case or learning-augmented guarantee; uncertainty (network fluctuation, EBS failure) is future work (p. 13).
- **(c) Admission and overload: absent.** Workflows are queued "without rejection" (p. 3); overload only lowers MUS gradually (p. 11). ESF sub-deadline sorting (p. 5) is an urgency-ordered dispatch, but nothing is rejected or deferred, and the objective is the mean MUS.
- **(d) Placement-dispatch coupling: partial.** Node and container are chosen jointly per function, online, with cross-workflow ordering (Sect. 4.2, pp. 5-7). But what is placed where (image cache contents, container pool) is not optimised or reconfigured; no data-affinity or state-transfer term (p. 4).
- **Workload / trace:** Poisson arrivals at lambda in {5,10,15,20}/s per EBS; six workflow topologies reconstructed from Alibaba Cluster Trace v2018 [35,36]; image size and cold-start delay from Alibaba Function Compute cold-start traces [37]; EBS coordinates from the EUA Melbourne CBD dataset; 10-25 EBSs; 1280 random instances; EdgeCloudSim (pp. 9-10). No real production arrival trace (burstiness, diurnal change).
- **Baselines:** SAUHS (ablation), RANDOM, HEFT [38], SKIPPY [14], IGA [18], PPO [26] (pp. 9-10).
- **Metrics:** MUS (primary), deadline satisfaction ratio, mean tardiness, mean scheduling overhead (p. 10). No P99 makespan, no SLO-goodput, no cold-start counts, no cost.
- **Compared to DFPS (Zolfaghari 2025)?** No. DFPS is neither cited nor a baseline (pp. 13-14).

### Direct quotes (for the draft)
> "queued in the workflow pool without rejection" (p. 3)

> "frequent adjustments introduce additional computational and communication overhead" (p. 2)

> "This determination process is stateless, i.e., previous OSPs do not affect the current decision." (p. 4)

> "degrades progressively rather than collapses abruptly" (p. 11)

> "Joint optimization of MUS and resource cost in workflow scheduling should be further explored." (p. 13)

### Examples & illustrations (for later drafting)
- Worked plan selection for workflow w11 with eight functions across three EBSs and the cloud, showing REO-WBC chosen over REO-NCC (Table 2, Figs. 2-3, pp. 7-8).
- Why DSD fails: a shallow task with four heavy functions gets the smallest sub-deadline (p. 10).

### Boundary of this focus
Judged from the paper text only; Table 4 column headers were partly lost in PDF text extraction, so the MT/MSO row assignment is inferred from consistency with the percentages in the text (p. 13). Novelty statements concern this paper, not a corpus search.

## G0 verdict

- **D1 (when to reconfigure): clear.** AUHS makes per-interval stateless decisions and never re-plans or reconfigures; keep-alive and cache capacity are fixed inputs, and re-planning is dismissed as costly (pp. 2, 4, 9); no forecasts or worst-case guarantees (pp. 2, 13).
- **D2 (overload admission + critical-path dispatch): partially overlapping.** Critical-path slack DP and earliest-sub-deadline-first cross-workflow ordering (pp. 4-5) overlap the dispatch half, but there is no admission control ("without rejection", p. 3) and the objective is mean satisfaction, not SLO-goodput or tail under overload (p. 11).
- **D3 (coupled placement-dispatch): partially overlapping.** Node plus container choice per function is made online jointly with cross-workflow ordering (pp. 5-7), but placement itself (image cache contents, container pool) is a fixed input and there is no state or data-transfer coupling (pp. 4, 9, 11); no comparison with DFPS.

## Mentioned entities
- Algorithms/software: [[auhs]], [[edgecloudsim]]
- Datasets: [[alibaba-cluster-trace]]
- Concepts: [[mean-user-satisfaction]]

## Connections
- Uses SKIPPY (Rausch et al. 2021, library key rausch-2021-optimized) as a baseline (p. 10); no page yet, so no typed relation.
- Does not cite or compare with DFPS (Zolfaghari et al. 2025).
