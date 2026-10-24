---
title: "Liao et al. 2025 — Adaptive GNN-based scheduling of serverless workflows in dynamic edge environments (EGAT + PPO)"
type: source
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
bibkey: liao-2025-adaptive
depth: standard
tags: [serverless-workflows, edge, gnn, reinforcement-learning, novelty-gate-g0]
relations:
  - target: egat-scheduler
    type: mentions
    confidence: extracted
    because: "Proposes the EGAT-based two-stage scheduler (abstract, p. 117)."
  - target: event-driven-two-stage-scheduling
    type: mentions
    confidence: extracted
    because: "Its event-driven, two-stage framing is why the paper was flagged at gate G0 (abstract, p. 117; Sect. III, p. 119)."
  - target: alibaba-cluster-trace
    type: cites
    confidence: inferred
    because: "Workflow statistics are adapted from an Alibaba production data-analytics trace [7] (Sect. IV-A, p. 121); [7] is the 2017 trace analysis, so the version relation to v2018 is unclear."
---

# Adaptive GNN-based scheduling of serverless workflows in dynamic edge environments

## Bibliographic Details
Liao, Lecheng; Li, Zhengze; Liu, Shuyi; Lu, Hancheng. 2025. *Adaptive GNN-Based Scheduling of Serverless Workflows in Dynamic Edge Environments*. 2025 11th International Conference on Computer and Communications (ICCC), pp. 117-122. https://doi.org/10.1109/ICCC68654.2025.11437925. Page numbers below are the printed pages 117-122 (6 PDF pages). The PDF is an IEEE Xplore download of the published version; extraction was clean except for equations.

## Section map

| Covered | Section | pp. |
|---|---|---|
| F1 | I. Introduction (offline / quasi-real-time / online / learning-based survey, three gaps, contribution) | 117-118 |
| F1 | II. System model (A model, B timing Eq. 1-5, C load model Eq. 6-9, D objective Eq. 11, constraints C1-C5) | 118-119 |
| F1 | III.A Function-graph encoding and ready-task selection (EGAT, Gumbel-softmax) | 120 |
| F1 | III.B Resource-graph encoding and location decision | 120 |
| F1 | III.C PPO policy optimisation, critical-path-shaped reward (Eq. 22-29) | 120-121 |
| F1 | IV Experiments (setup, baselines, metrics, Figs. 4-6) | 121-122 |
| F1 | V Conclusions | 122 |

## Kernthesen

### 1. The scheduler is "event-driven" only in the sense that requests arrive as an event stream (pp. 117-118)
Requests arrive as a stream R with arrival times (p. 118); a function enters a FIFO queue once its dependencies are satisfied (p. 118). Each decision is taken when a task is ready. "Event-driven" names this per-arrival decision mode and serverless invocation semantics (p. 117); it does not denote a trigger that decides when to re-plan.

### 2. Two stages = pick a ready function, then pick a server (pp. 119-120)
Stage 1 selects one ready function from all active workflows using node, workflow and global embeddings (Eq. 15-17, p. 120); stage 2 enhances the resource graph for that function and selects a server (Eq. 19-20, p. 120). The policy factorises as pi1(f*|s) pi2(v*|f*, s) (Eq. 21, p. 120). The action is one (function, server) pair per step.

### 3. Selection is a global, cross-workflow ranking with critical-path shaping (pp. 118, 120-121)
Pooling workflow embeddings into a global context z "captures both workflow-level critical dependencies and inter-workflow competition" (p. 120). The reward is piecewise: tasks on the realised critical path get a latency-normalised penalty, all tasks get a load-balance term (Eq. 23, p. 121). So the critical path enters only as a learned reward signal, not as an explicit dispatch rule.

### 4. Resource features include container readiness and data locality (p. 120)
Server features include available cores/memory, queued workload W, predecessor-output locality Q and container readiness L (0 if warm, else expected cold-start delay); link features carry bandwidth and concurrent transfers (p. 120). Cold-start delay depends on server and function (delta^cold_{k,i}, p. 118), and the data-transfer term s_jk/b_jk is modelled (Eq. 1, p. 118).

### 5. Objective is mean makespan plus load imbalance (p. 119)
min alpha * mean(T_finish) + beta * sqrt(variance of normalised busy time) (Eq. 11, p. 119). No deadline, SLO, tail-latency, cost or energy term.

### 6. Constraints guarantee only per-decision feasibility (p. 119)
C1-C5 give unique placement, memory and core caps, container-before-execution and eligibility; infeasible servers are masked to -inf (p. 120). Nothing limits arrivals; the FIFO queue absorbs excess load (p. 118).

### 7. Node churn is handled by re-encoding the resource graph, not by re-placing (pp. 118, 121)
"Our dynamic graph encoding naturally captures changes in the resource graph, such as node churn" (p. 118). Churn is simulated by randomly disabling and re-enabling nodes (p. 121), and 0-4 of 8 nodes join or leave in Fig. 6 (p. 122). The effect is on subsequent decisions; already-placed functions are not migrated.

### 8. Evaluation is small-scale simulation (pp. 121-122)
4-8 heterogeneous nodes, 2-20-function workflows, 5000 request arrivals per experiment; cold start 0.1-2 s; a PyTorch simulator (p. 121). Result: about 14% average and up to 20% lower makespan than DRL-WGNN, lowest load imbalance, smallest degradation under churn (p. 122). Results are shown as figures; no numeric tables, no confidence intervals ("repeated trials", p. 121).

### 9. Stated limitations are few (p. 122)
The conclusion lists no limitations. Trained with PPO per environment; no discussion of generalisation, training cost or inference overhead.

### 10. Related work is a taxonomy: offline, quasi-real-time, online, learning-based, with three stated gaps (pp. 117-118)
Offline DAG placement [2], quasi-real-time EDF (RT-FaaS [3]), online Hermod [4], and learning-based [5], [6] are all said to rely on static assumptions or fixed rules. The three gaps claimed: myopic local-ready task selection, cold start treated as a fixed cost, and flattened static resource topologies (p. 118). The paper's contribution is framed against these three, not against reconfiguration, forecasting or admission.

## What this source does not address
No arrival-rate or demand forecasting, no worst-case or robustness guarantee, no admission control or load shedding, no SLO or deadline, no scale-to-zero or keep-alive decision, no cost model, no reconfiguration or migration of placed functions, no switching-cost model. Cold start is a per-decision feature, not a lever the scheduler controls (pre-warming, keep-alive). No real platform; no real trace of invocation arrivals.

## Focus: Novelty gate G0 for plan faas-edge-adaptation (when to reconfigure, forecasts with guarantees, overload admission, placement-dispatch coupling) — 2026-10-13

**Carries Kernthesen 1, 2, 3, 5, 6, 7, 8, 10.**

### What this focus needs beyond the Kernthesen
- **(a) When to re-schedule / re-place: not addressed.** The trigger is the readiness of a function (p. 118; "event-driven", p. 117), so the scheduler decides what to do with this task now, never whether to re-plan or reconfigure. No cost-triggered or event-triggered re-placement, no switching-cost model; node churn only changes the inputs of later decisions (pp. 118, 121-122).
- **(b) Forecasts with robustness guarantees: absent.** No prediction of arrivals, load or function demand; only a learned policy under stochastic simulated variability. The only "robustness" is empirical degradation under 0-4 churned nodes (Fig. 6, p. 122).
- **(c) Admission control / overload: absent.** FIFO queue, no rejection (p. 118); load growth is measured only through load imbalance, not goodput or deadline hit rate (Fig. 5, p. 122).
- **(d) Placement-dispatch coupling: yes in the per-step sense.** The two stages are trained end-to-end (pp. 119-121) and stage 2 is conditioned on the function chosen in stage 1 (Eq. 19, p. 120). But "placement" here is the per-function server choice; there is no standing placement of function images or containers that is reconfigured over time.
- **Workload / trace:** Synthetic. Workflow statistics adapted from an Alibaba data-analytics trace (ref. [7], p. 121), 2-20 functions, compute 1-100 GHz.s, memory 0.5-4 GB, transfer 20-200 MB; 5000 arrivals; arrival process not specified.
- **Baselines:** RAND, HEFT, DRL-Flat, DRL-WGNN (p. 121). Not SKIPPY, AUHS, DFPS or any cold-start / keep-alive policy.
- **Metrics:** average makespan and load imbalance (variance of normalised busy time) (p. 122). No P99, SLO attainment, cost, cold-start count.
- **Compared to DFPS (Zolfaghari 2025)?** No: DFPS is neither cited nor a baseline (reference list [1]-[7], p. 122).

### Direct quotes (for the draft)
> "an event-driven, two-stage scheduling framework based on an Edge-enhanced Graph Attention Network (EGAT)" (abstract, p. 117)

> "Functions are dispatched via a first-in-first-out (FIFO) queue." (p. 118)

> "our dynamic graph encoding naturally captures changes in the resource graph, such as node churn and fluctuating link conditions" (p. 118)

> "reducing completion time by about 14% on average and up to 20% compared with the strongest baseline (DRL-WGNN)" (p. 122)

### Boundary of this focus
Judged from this 6-page paper only; equations were read from text extraction, and figure curves (Figs. 4-6) were not inspected numerically. Novelty statements concern this paper, not a corpus search.

## G0 verdict

- **D1 (when to reconfigure): clear.** "Event-driven" means per-arrival, per-ready-task decisions (pp. 117-118); there is no re-planning trigger, switching-cost model, forecast or guarantee, and churn only alters later inputs (pp. 118, 121-122).
- **D2 (overload admission + critical-path dispatch): clear.** Dispatch uses a FIFO queue with no rejection (p. 118); the critical path is only a reward-shaping term (Eq. 23, p. 121), and overload is measured as load imbalance, not goodput or tail latency (p. 122).
- **D3 (coupled placement-dispatch): partially overlapping.** Stage 1 (which function) and stage 2 (which server) are trained jointly and conditioned (Eq. 19-21, p. 120), a coupling in the per-task sense, but there is no standing placement to reconfigure and no workflow-level switching or state cost (pp. 119-121).

## Mentioned entities
- Algorithms/software: [[egat-scheduler]]
- Datasets: [[alibaba-cluster-trace]]
- Concepts: [[event-driven-two-stage-scheduling]]

## Connections
- Related edge workflow schedulers: [[lei-2026-adaptive]], [[sun-2026-hybrid]] (no typed relation: no stance toward this paper).
- Builds on Long et al. 2024 (GLOBECOM, ref. [5]) and Huang et al. 2024 (ref. [6]), which are not in the library.
- Does not cite or compare with DFPS (Zolfaghari et al. 2025).
