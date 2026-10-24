---
title: "Farahani et al. 2026 — ClusterLess: Deadline-Aware Serverless Workflow Orchestration on Federated Edge Clusters"
type: source
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
bibkey: farahani-2026-clusterless
depth: standard
tags: [serverless-edge, workflow, deadline, multi-cluster, kubernetes, novelty-gate-g0]
relations:
  - target: clusterless
    type: mentions
    confidence: extracted
    because: "The system the paper introduces (abstract, p. 1)."
  - target: execution-mode-selection
    type: builds-on
    confidence: extracted
    because: "Four modes, Eq. 4 and Alg. 2 (pp. 3, 5-6)."
  - target: deadline-feasible-offloading
    type: builds-on
    confidence: extracted
    because: "Super-master EDF placement, Eqs. 8-10, Alg. 3 (pp. 3, 6)."
  - target: dfps
    type: contradicts
    confidence: inferred
    because: "Not compared in the paper; it decides per invocation, not by periodic re-placement, so it does not pre-empt D1 and is only a partial D2/D3 competitor."
  - target: bi-level-scheduling
    type: builds-on
    confidence: inferred
    because: "Local master plus super-master is a two-tier design (p. 3)."
  - target: cold-start
    type: mentions
    confidence: extracted
    because: "Cold scaling cost CS enters Eq. 4 (p. 3)."
---

# ClusterLess: Deadline-Aware Serverless Workflow Orchestration on Federated Edge Clusters

## Bibliographic Details
Farahani, Reza; Colosi, Mario; Murturi, Ilir; Nastic, Stefan; Villari, Massimo; Dustdar, Schahram; Prodan, Radu. 2026. *ClusterLess: Deadline-Aware Serverless Workflow Orchestration on Federated Edge Clusters*. arXiv:2605.04310v1 [cs.DC], 5 May 2026, 11 pp. https://doi.org/10.48550/arXiv.2605.04310. Preprint, no peer-reviewed version known. Page numbers are PDF pages 1-10 as laid out (the 11th holds references).

## Section map

| Covered | Section | pp. |
|---|---|---|
| ✓ F1 | I. Introduction, four execution modes, claim of novelty | 1 |
| ✓ F1 | II. Related work, Table I | 2 |
| ✓ F1 | III. Problem formulation (workflow, cluster, intra, inter, completion-time models) | 2-4 |
| ✓ F1 | IV. Architecture | 4 |
| ✓ F1 | V. Algorithms 1-3 and complexity | 5-6 |
| ✓ F1 | VI. Testbed, workflows, baselines, experimental design | 6-8 |
| ✓ F1 | VII. Results (load-aware super-master, completion time, deadlines, modes, CPU) | 8-10 |
| ✓ F1 | VIII. Conclusion | 10 |

## Kernthesen

### 1. ⭐ Single-cluster edge serverless does not extend to federations with E2E deadlines (p. 1)
The authors argue that K8s-based serverless works within one cluster but not across heterogeneous clusters where concurrent DAG workflows carry strict deadlines, because cold starts, fragmentation and inter-cluster delay propagate along dependencies.

### 2. ⭐ Four execution modes chosen per ready function (pp. 1, 3)
Warm execution, warm scaling, cold scaling and offloading, with serving times given in Eq. 4. The choice is made when the function becomes ready.

### 3. ⭐ Bottleneck-driven refinement to meet the deadline (pp. 5-6)
Alg. 2 loops while the workflow completion time exceeds A_w + D_w, picks the function with the largest completion time, advances its mode in fixed order, and re-plans the dependent functions. It stops as soon as the deadline holds.

### 4. ⭐ Super-master offloading with deadline-feasibility filter and EDF order (pp. 3, 6)
Offloaded functions are ordered by earliest workflow deadline, and only clusters with completion within the deadline and better than local are candidates; the minimum completion time wins (Eqs. 8-10, Alg. 3).

### 5. ⭐ Infeasible functions are not rejected (p. 3; Alg. 3 lines 11-12, p. 6)
If no feasible cluster exists the workflow is marked deadline-violated and the function stays at its origin. There is no admission test and no load shedding.

### 6. Super-master election is load- and failure-driven (pp. 2-3, 5)
Per epoch ΔT = 1 s, the coordinator is replaced when its heartbeat times out (T_fail = 5 s) or its normalised load exceeds l = 0.75 (Eqs. 1-3, Alg. 1). This is the only event-triggered rule in the paper and it concerns the coordinator, not function placement.

### 7. Completion-time model with dependency-aware start times (pp. 3-4)
Start time is the maximum over predecessors of finish time plus transfer delay (Eqs. 5-7); workflow completion is the maximum over functions (Eq. 15). Resource and bandwidth feasibility are Eqs. 11-13.

### 8. Evaluation on a 64-node, six-cluster testbed with two workflows (pp. 6-8)
T2SC (8 functions) and RT (6 functions), 3 sizes by 3 deadline classes = 18 configurations; Zipf (alpha 0.75) over configurations, Poisson arrivals in uniform, skewed and dynamic regimes; 4G LTE bandwidth traces (p. 7).

### 9. Headline results (pp. 1, 9)
Completion time down by up to 40%; deadline satisfaction 92.3/83.4/96.4% (uniform/skewed/dynamic) for ClusterLess versus 37.7/25.5/39.0% for native K8s; violations of single-digit seconds (Fig. 7, p. 9).

### 10. Control-plane load stays bounded by moving the coordinator (p. 8-9)
When C1 reaches l, the super-master role moves to C2 and intra-cluster latency is unchanged (Fig. 4).

### 11. Learning-based and multi-objective orchestration are future work (p. 10)
The conclusion lists them as future work. No forecasting appears in the method.

## What this source does not address
No forecasting or prediction, no learning, no periodic or triggered re-placement of function instances, no reconfiguration cost, no warm-pool sizing policy, no admission control or shedding, no SLO-goodput or P99 metric, no public traces (Azure, Huawei), no simulator, no comparison with DFPS or any published workflow scheduler, and no worst-case guarantee. Prediction and pre-deployment are treated in [[ma-2025-online-deployment]] and [[liu-2025-sdser]]; periodic re-placement in [[zolfaghari-2025-dynamic-function-placement]].

## Focus: Novelty gate G0, does ClusterLess pre-empt D1 (when to reconfigure), D2 (overload admission + critical-path dispatch), D3 (coupled placement-dispatch)? — 2026-10-13

**Carries Kernthesen 3, 4, 5, 6, 9, 11.**

### What this focus needs beyond the Kernthesen
1. Test (a), re-placement trigger: none. Decisions are taken when a function becomes ready (p. 3); there is no re-placement of existing instances, no switching cost, no clock. Only the coordinator is re-elected on failure or overload (Alg. 1, p. 5). Answer: no.
2. Test (b), forecasts with guarantees: none. The time estimator uses monitored state (p. 4); learning-based methods are future work (p. 10). No guarantee of any kind. Answer: no.
3. Test (c), admission or shedding: no. Infeasible work is kept and counted as violated (p. 3, Alg. 3 p. 6). EDF ordering and a deadline-feasibility filter exist (Eqs. 9-10, p. 3), and violation duration is reported (Fig. 7b, p. 9), but the primary metric is deadline satisfaction rate, not SLO-goodput.
4. Test (d), coupling and critical-path dispatch: partly. Placement, mode and start time are decided together per workflow from dependency-aware finish times (Eqs. 6-7, p. 3; Alg. 2, p. 5), and the bottleneck function is the one with the largest completion time. EDF is said to prioritise functions on critical deadline paths (p. 6), but critical-path analysis is not defined as such. There is no standing placement of function instances separate from dispatch, so the DFPS decoupling is bypassed rather than studied.
5. Workloads: two real workflows (T2SC 8 functions, RT 6 functions), 18 size-deadline configurations, Zipf plus Poisson, three load regimes, 6 clusters, 64 nodes (pp. 6-8). Baselines: NKS, CLI, RRX, RNX, all built by the authors (p. 7). Metrics: mean completion time, deadline satisfaction rate, violation duration, offloaded share, mode shares, CPU utilisation (pp. 8-10). No DFPS comparison.
6. Comparison with DFPS: both are DAG-aware and edge-focused. DFPS re-places periodically with a simulated-annealing search and a queueing model ([[dfps]], [[periodic-replacement-and-rescheduling]]); ClusterLess never re-places and has no search. ClusterLess adds a deadline and an offload tier that DFPS lacks, but not forecasts, cost-aware timing, or overload admission.

### Direct quotes (for the draft)
> "Future work will explore multi-objective and learning-based orchestration." (p. 10)

> "If Kf = ∅, no deadline-feasible inter-cluster placement exists; function f is declared infeasible, and workflow w is marked as deadline-violated." (p. 3)

> "CLU consistently limits violation duration to single-digit seconds" (p. 9)

### Examples & illustrations (for later drafting)
- Skewed regime, strict deadlines: ClusterLess satisfies 74.5%, CLI 35.8%, NKS 18.2% (p. 9).
- Super-master handover from C1 to C2 at load 0.75 (Fig. 4, p. 9).

### Boundary of this focus
Read for the four G0 tests only; hardware, CPU and super-master analyses were skimmed for what they do not contain.

### G0 verdict
- **D1 (when to reconfigure, forecasts with guarantees): clear.** No re-placement trigger, switching cost or forecast exists (p. 3; p. 10 lists learning as future work), and the only event rule moves the coordinator (Alg. 1, p. 5).
- **D2 (overload admission and critical-path dispatch): partially overlapping.** It has deadline-feasibility filtering, EDF ordering and bottleneck-first dispatch (Eqs. 9-10, p. 3; Alg. 2-3, pp. 5-6), but no admission control or shedding, no goodput metric, and infeasible workflows stay in the system (p. 3), so the admission half of D2 is clear.
- **D3 (coupled placement and dispatch): partially overlapping.** Mode, placement and start times are decided jointly per workflow with dependency-aware finish times (Eqs. 6-7, p. 3; Alg. 2, p. 5), but the work is reactive, per function and unevaluated against a decoupled-placement baseline such as DFPS (p. 7); persistent instance placement is not addressed.

## Mentioned entities
- Systems: [[clusterless]], [[dfps]]
- Concepts: [[execution-mode-selection]], [[deadline-feasible-offloading]], [[bi-level-scheduling]], [[cold-start]], [[periodic-replacement-and-rescheduling]]

## Connections
- Builds on (two-tier design): [[bi-level-scheduling]]
- Contrasted with (inferred, not compared in the paper): [[dfps]]
- Related G0 sources: [[ma-2025-online-deployment]], [[liu-2025-sdser]], [[zolfaghari-2025-dynamic-function-placement]]
