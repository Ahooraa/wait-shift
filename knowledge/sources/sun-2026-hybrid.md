---
title: "Sun et al. 2026 — Hybrid scheduling for serverless function workflows in edge computing system (DQLWS)"
type: source
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
bibkey: sun-2026-hybrid
depth: standard
tags: [serverless-workflows, edge, lyapunov, ddqn, g0-novelty]
relations:
  - target: dqlws
    type: builds-on
    confidence: extracted
    because: "Defines the DQLWS method: Lyapunov drift-plus-penalty plus DDQN (contributions list, p. 2; Algorithm 1, p. 10)."
  - target: lyapunov-drift-plus-penalty
    type: builds-on
    confidence: extracted
    because: "Per-slot drift-plus-penalty objective Eq. 32 and bound Q_DQLWS <= Q_opt + B/V (Theorem 2, p. 8)."
  - target: delay-sensitive-tolerant-workflow-classes
    type: builds-on
    confidence: extracted
    because: "Classifies workflows by emergency factor P_i/D_i against a threshold (Eq. 1, p. 4)."
---

# Hybrid scheduling for serverless function workflows in edge computing system

> [!warning] Provenance: the PDF is the Elsevier **journal pre-proof** (accepted 14 Sep 2026, "will undergo additional copyediting"), not the Version of Record. Page numbers below are the **printed** manuscript pages (PDF page minus 1, because of the Elsevier cover page). Re-check against the final version when published.

## Bibliographic Details
Sun, Mengyu; Lu, Gang; Huang, Zhilan; Quan, Shuo; Zhang, Yaqiang; Tan, Yukai. 2026. *Hybrid scheduling for serverless function workflows in edge computing system*. Future Generation Computer Systems, art. 108822. DOI 10.1016/j.future.2026.108822. (Received 16 Apr 2026, accepted 14 Sep 2026.)

## Section map

| Covered | Section | pp. |
|---|---|---|
| ✓ F1 | Abstract; 1. Introduction (motivation, contributions) | 1-2 |
| ✓ F1 | 2. Related Works (heuristic / DRL / urgency-aware; cites DFPS as [12]) | 2-3 |
| ✓ F1 | 3. System Model (workflow, computation, transmission; emergency factor) | 3-5 |
| ✓ F1 | 4. Problem Formulation (constraints Eq. 10-13, objective Eq. 14-17) | 5-6 |
| ✓ F1 | 5.1-5.2 Lyapunov model, Theorems 1-2 | 6-9 |
| ✓ F1 | 5.3-5.4 MDP and DDQN workflow scheduling (Algorithm 1) | 9-11 |
| ✓ F1 | 6.1 Experimental settings (CloudSim, Tables 1-2, baselines, metrics) | 11-12 |
| ✓ F1 | 6.2 Results (threshold, proportion, weights, nodes, ablation, baselines) | 12-17 |
| ✓ F1 | 7. Conclusion and future works | 17 |
| — | References [1]-[29] | 17-18 |

## Kernthesen

### 1. ⭐ Workflows are split into delay-sensitive and delay-tolerant classes by a deadline-pressure factor (pp. 1, 4)
The emergency factor is lambda_i = P_i / D_i, where P_i is the *sum* of the hard (unqueued) execution times of all functions and D_i the deadline (Eq. 1). A workflow with lambda_i above a threshold (0.5 chosen) is delay-sensitive and all its functions get high priority. Queueing delay is deliberately excluded from lambda_i (p. 4).

### 2. ⭐ The scheduling problem is online, per time slot, with no workload prediction (pp. 6-7)
Slotted time; each slot's ready functions are assigned to edge nodes. The authors state global offline information is unobtainable and an online process is developed "without predicting system information" (p. 6).

### 3. ⭐ Lyapunov drift-plus-penalty turns the long-term delay-energy problem into per-slot problems (pp. 6-8)
Two virtual queues (sensitive, tolerant) per function, quadratic Lyapunov function (Eq. 20), drift bound (Theorem 1), simplified per-slot objective Eq. 32 (weighted delay and energy minus queue-backlog terms).

### 4. Performance bound: long-term cost <= optimum + B/V (pp. 8-9)
Theorem 2 / Eq. 33, 42: the guarantee is on the *average delay-energy cost*, controlled by V; Theorem 1 assumes i.i.d. arrivals (p. 7). It is not a worst-case guarantee against forecast error and not a deadline-satisfaction guarantee.

### 5. ⭐ A DDQN approximates the per-slot minimiser over a masked discrete action space (pp. 6, 9-11)
State s_t = (function queue, node resource occupation, bandwidth); action = node for each ready function; infeasible assignments are removed by an action mask (p. 6). Reward is a deadline-violation penalty only (Eq. 43, p. 9); the delay-energy objective enters via the Lyapunov layer. Offline training, online inference (p. 11).

### 6. Energy budget per node is a hard constraint (pp. 5-6)
Constraint (13) with residual energy; no energy supplement is modelled. Energy is a first-class objective (nJ), absent from the DFPS-style makespan view.

### 7. Evaluation is simulation with synthetic video-processing workflows (pp. 11-12)
CloudSim, 20-100 edge nodes, five video functions (Table 2), 1000-workflow sample set, wireless OFDMA transmission model; 50 runs per setting.

### 8. Headline results: DQLWS lowest delay and energy (pp. 15-17)
Table 4/6: DQLWS 74.34 ms, 404.54 nJ, 4.8% violation; versus TD3WS -4.50 ms (p<0.001), versus MPPOWS -1.86 ms (p=0.018). Ablation: removing DDQN is worst (88.46 ms, 14.6% violation), removing Lyapunov 11.7%, removing classification 8.9% (p. 15-16).

### 9. The threshold sweep shows a class-balance trade-off (pp. 12, 15)
Too low a threshold overloads the high-priority queue; too high starves urgent workflows. 0.5 gives 0.54% violations (Table 3).

### 10. Future work explicitly names missing mechanisms (p. 17)
Admission control and load shedding are to be explored; real Kubernetes/serverless deployment is also future work.

## What this source does not address
No cold starts, container/instance lifecycle, warm pools or replication; no real invocation traces (Azure, Huawei); no non-stationary popularity or load shifts; no forecasting; no admission control or load shedding (declared future work, p. 17); no critical-path analysis (priority uses the sum of execution times); no comparison against DFPS (Zolfaghari 2025), which is only cited in Related Works (p. 2) and described as "relatively static and non-real-time". Tail metrics (P99 makespan) are not reported, only means and violation rate.

## Focus: Novelty gate G0 for plan faas-edge-adaptation, does Sun 2026 pre-empt D1 (when to reconfigure), D2 (overload admission + critical-path dispatch), D3 (coupled placement-dispatch)? — 2026-10-13

**Carries Kernthesen 1, 2, 4, 5, 7, 10.**

### What this focus needs beyond the Kernthesen
1. (a) *When to reconfigure*: no trigger logic. Decisions happen every time slot for the ready-function queue (pp. 6, 9-10, Algorithm 1 loop "for each t"); no switching or migration cost, no change-point detection, no replacement period.
2. (b) *Forecast robustness*: none. The paper avoids prediction altogether (p. 6) and motivates Lyapunov as suited where future states cannot be accurately predicted (p. 2). The only formal guarantee is the average-cost bound of Theorem 2 (p. 8), which is not a robustness-consistency result.
3. (c) *Admission / overload*: no admission control. Overload shows up as violations: near 100% delay-sensitive load "it becomes impossible to satisfy the strict temporal constraints of all workflows" (p. 13). Priority classes are the only overload mechanism. An online admission test (Samimi et al., ref [8]) is cited in the introduction but not used.
4. (d) *Placement-dispatch coupling*: the single DDQN action assigns each ready function to a node, so node choice and dispatch order coincide in one per-slot decision (pp. 9-10). There is no persistent placement of function instances separate from dispatch, hence no decoupling to remove; equally no co-optimisation of placement stability and request routing.
5. *Workload/trace*: synthetic; video-processing DAG variants with Table 2 loads; 1000-workflow sample set, 200 per training round; no public traces (p. 11).
6. *Baselines*: RWS, UWS (urgency-based list scheduling, Cai et al.), GAWS (genetic algorithm), TD3WS, MPPOWS (p. 12). DFPS is not a baseline.
7. *Metrics*: mean response delay (ms), mean energy (nJ), temporal violation rate, convergence/stability (std over 50 runs); paired t-tests and Cohen's dz versus TD3WS and MPPOWS only (pp. 12, 16-17). No P99 makespan, no goodput, no cold-start or reconfiguration counts.

### Direct quotes (for the draft)
> "an online optimization process is developed in the following section without predicting system information." (p. 6)

> "dynamic penalty mechanisms, admission control, and load-shedding strategies, will be explored to improve adaptability under dynamic scenarios." (p. 17)

> "These works mainly target relatively static and non-real-time systems" (p. 2, on Zolfaghari et al. [12])

> "it becomes impossible to satisfy the strict temporal constraints of all workflows simultaneously." (p. 13)

### Examples & illustrations (for later drafting)
- Video-processing workflow of five stages (frame extraction, DNN processing, object detection, colour filtering, encoding) with Table 2 cycle and MB ranges (pp. 11-12).
- Delay-sensitive proportion sweep 0-100%: violations appear from about 60% and the system saturates near 100% (p. 13).

### Boundary of this focus
Only the four G0 dimensions plus workload, baselines and metrics were read closely; the communication model (Eq. 4-9) and Lyapunov proofs (Eq. 27-31) were skimmed.

## Mentioned entities
- Methods: [[dqlws]]
- Concepts: [[lyapunov-drift-plus-penalty]], [[delay-sensitive-tolerant-workflow-classes]]
- Compared systems (no wiki pages): DFPS (Zolfaghari 2025), UWS/Cai 2025, GAWS/Jiang 2025, TD3WS/Wang 2025, MPPOWS/Xu and Li 2026

## Connections
- Builds on: [[lyapunov-drift-plus-penalty]], [[dqlws]], [[delay-sensitive-tolerant-workflow-classes]].
- Cites DFPS (Zolfaghari 2025) in related work only, as static and non-real-time (p. 2); no typed relation yet because the DFPS source page may not exist; add a `cites` relation once it does.

## G0 verdict
Evidence base: this paper only (journal pre-proof).

- **D1 (when to reconfigure): CLEAR.** Sun decides per time slot with no trigger, switching cost or forecast, and deliberately avoids prediction (pp. 6, 9-10); its only guarantee is an average-cost Lyapunov bound (Theorem 2, p. 8), not robustness to forecast error.
- **D2 (overload admission + critical-path dispatch): PARTIALLY OVERLAPPING.** Deadline-aware two-class priority (Eq. 1, p. 4) and a violation-rate metric overlap with the dispatch half, but P_i is a sum of execution times rather than a critical path, overload is left as unavoidable violations (p. 13), and admission control and load shedding are listed as future work (p. 17), so the admission half is open.
- **D3 (coupled placement-dispatch): PARTIALLY OVERLAPPING.** One DDQN action jointly picks the node for each ready function (pp. 9-10), coupling node choice with dispatch at function granularity; but there are no persistent instances, cold starts or replication, and no decoupled placement-then-dispatch baseline such as DFPS is compared (p. 12), so a framing around DFPS-style decoupling is not pre-empted, though Sun should be cited as related work.

Net for G0: Sun 2026 does not pre-empt D1-D3; closest neighbour for D2/D3. Caveat: based on the pre-proof, read once, no search for later versions.
