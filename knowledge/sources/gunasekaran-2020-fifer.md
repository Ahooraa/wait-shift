---
title: "Gunasekaran et al. 2020 — Fifer: Tackling Resource Underutilization in the Serverless Era"
type: source
created: 2026-10-22
updated: 2026-10-22
status: review
author: llm
bibkey: gunasekaran-2020-fifer
depth: standard
based_on: preprint
tags: [serverless, function-chains, container-scaling, batching, slack, queue-length, cold-start, g0-novelty, baseline]
relations:
  - target: backlog-driven-container-sizing
    type: supports
    confidence: extracted
    because: "Reactive rule: Nc = pending queue length / batch size, spawned only if the queuing delay exceeds the cold start (Df > Cd), p. 5."
  - target: cold-start
    type: mentions
    confidence: extracted
    because: "Cold start of 2-9 s per new container drives the queue-versus-spawn decision (pp. 3, 10)."
  - target: predictive-pre-deployment
    type: supplements
    confidence: extracted
    because: "LSTM load forecast spawns containers ahead of demand, complementing the reactive path (Alg. 1, p. 6)."
  - target: container-keep-alive
    type: mentions
    confidence: extracted
    because: "Idle containers are removed after a 10-minute timeout; least-free-slot scheduling lets lightly used containers drain early (p. 6)."
---

# Fifer: Tackling Resource Underutilization in the Serverless Era

## Bibliographic Details
Gunasekaran, Jashwant Raj; Thinakaran, Prashanth; Chidambaram (Nachiappan), Nachiappan; Kandemir, Mahmut T.; Das, Chita R. 2020. *Fifer: Tackling Resource Underutilization in the Serverless Era*. Proceedings of the 21st International Middleware Conference (Middleware '20), pp. 280-295. DOI 10.1145/3423211.3425683. arXiv:2008.12819 (v1, 28 Aug 2020).

> [!warning] Provenance: based on the **arXiv preprint** ("PrePrint Version"), not the published ACM version.
> Page references are the preprint's PDF pages 1-15. Final claims and numbers may differ; the user approved ingesting the open-access copy (2026-10-22). Re-ingest the original when acquired.

## Section map

| Covered | Section | pp. |
|---|---|---|
| ✓ F1 | 1 Introduction (three inefficiencies, contributions) | 1-2 |
| ✓ F1 | 2 Background and motivation (chains, cold start on AWS Lambda, stage variation) | 2-4 |
| ✓ F1 | 3 Preamble: request-batching resource manager, Eq. 1 | 4 |
| ✓ F1 | 4.1-4.2 Execution time, slack, load balancing, reactive scaling (RScale) | 5-6 |
| ✓ F1 | 4.3-4.4 Function scheduling (least slack first), greedy container and node selection | 6 |
| ✓ F1 | 4.5 Proactive scaling with an LSTM predictor | 6-7 |
| ✓ F1 | 5 Implementation (Brigade, Kubernetes) and large-scale simulation | 7-8 |
| ✓ F1 | 6 Results: prototype, trace-driven simulation, cold-start effects | 9-12 |
| ✓ F1 | 7-8 Related work, conclusion | 12-13 |

## Kernthesen

### 1. ⭐ Platforms scale containers per function in isolation and map one request to one container, so function chains are over-provisioned (pp. 1-2)
Three causes are named: frameworks meet each function's own SLO and ignore the chain's end-to-end SLO, so they scale every stage uniformly; one-to-one request-to-container mapping spawns too many containers in a burst; and naive batching onto a static pool breaks SLOs for strict functions. The remedy is stage-aware provisioning that uses leftover slack.

### 2. ⭐ Stages of a chain differ strongly in run time, so per-stage sizing beats uniform sizing (p. 3)
In the Detect-Fatigue chain, stage 1 is 81% of the total execution time and the other stages together under 20% (Fig. 3a). Uniform batching across stages would give poor utilisation; each stage needs its own batch size and container count.

### 3. ⭐ Queueing on an existing container beats starting a new one when the cold start is longer than the wait (p. 3)
Cold starts add about 2-7.5 s on AWS Lambda (Fig. 2), often more than the run time of millisecond functions. "Hence, the decision to queue versus starting up a new container depends on the SLO, execution times of the application and the cold-start latencies of the containers." This is the cost check that later work (Kraken) reuses.

### 4. Slack is the gap between the end-to-end response SLO and the chain's execution time, and is split over stages in proportion to their run time (pp. 4-5)
The SLO is fixed at 1000 ms; slack per chain is 572-788 ms (Table 4, p. 8). Proportional split is chosen over equal split because it gives better per-stage utilisation (p. 5).

### 5. ⭐ Batch size per stage is slack divided by execution time (Eq. 1, p. 4)
B_size = Stage_Slack / Stage_Exec_Time. In the worked example a baseline manager spawns 24 containers (8 per stage) while the batching manager needs 10 (Fig. 4). Batching cannot hide cold starts, which motivates proactive spawning.

### 6. ⭐ Reactive scaling (RScale): add Nc = pending queue length / batch size containers, but only when queuing delay would exceed the cold start (p. 5)
Every monitoring interval the load monitor checks the last 10 s of jobs. With Td = PQlen x Sr and L = sum of batch sizes over the stage's containers, the queuing delay is Df = Td / L; "If Df > Cd, then LB spawns additional containers (Nc) for each stage." (Cd = cold-start delay, Sr = per-stage response latency = slack + execution time). Algorithm 1 also uses the condition delay >= stage.slack (p. 6).

### 7. ⭐ Proactive scaling uses an LSTM forecast of the arrival rate and spawns the shortfall per stage (Alg. 1, p. 6)
Every 10 s Fifer samples the arrival rate in 5 s windows over the last 100 s, keeps the maximum, and predicts the maximum over the next 10 minutes. For each stage, if forecast load exceeds current containers x batch size, it adds (forecast - capacity) / batch size containers. LSTM had the lowest RMSE of eight predictors (MWA, EWMA, linear and logistic regression, feed-forward, WeaveNet, DeepAR, LSTM) and about 85% accuracy on 800 s of the WITS trace (p. 7).

### 8. Reactive and proactive paths are complementary: mispredictions are caught by the reactive path, at the price of cold starts (p. 6)
If the forecast is right, no SLO is violated; if not, the reactive policy detects stage delays and spawns containers that cold-start.

### 9. Placement is greedy bin-packing on the least-free-slot container and least-resource node (pp. 6-7)
Requests go to the container with the fewest free slots, idle containers are removed after 10 minutes, and containers go to the lowest-numbered server with the least available cores that still fits, so empty servers can be switched off. Shared stages use Least Slack First scheduling.

### 10. Implementation and set-up: Brigade on Kubernetes, 5K lines of JavaScript, an 80-core cluster, and a 2,500-core simulator (pp. 7-8)
Containers use 0.5 CPU and are pulled from Docker Hub, giving cold starts of 2-9 s. Workloads are ML microservice chains from Djinn&Tonic (Face Security, IMG, IPA, Detect-Fatigue) in three mixes by slack, driven by Poisson arrivals (lambda = 50) and the Wiki and WITS traces.

### 11. ⭐ Results: up to 80% fewer containers, 4x container utilisation and 31% less energy than a non-batching baseline, with the baseline's SLO violation level (abstract, pp. 9-11)
Compared policies: Bline (one container per request when none is idle), SBatch (static pool, equal slack), BPred (EWMA forecasting, as in Archipelago), RScale, Fifer. RScale alone has about 10-12% more SLO violations than Bline and up to 3x higher P99, because aggressive batching with reactive spawning congests the queues (p. 9). On the Wiki trace RScale and BPred spawn up to 3.5x more containers than Fifer (p. 11).

### 12. ⭐ Stated assumptions: execution times known offline and stable, tenants supply the SLO, chains only (pp. 2, 4, 8)
Execution-time standard deviation is within 20 ms over 100 runs for the ML services (p. 4); communication and storage bottlenecks are out of scope (p. 2); RScale is noted as akin to the dynamic batching of GrandSLAm (p. 8). There are no DAG branches, no multi-node placement and no fixed capacity.

## Figures and tables
Fig. 1 chain architecture (p. 3); Fig. 2 cold and warm start on Lambda (p. 3); Fig. 3 per-stage execution times (p. 3); Fig. 4 baseline versus batching example (p. 4); Fig. 5 design overview (p. 5); Fig. 6 predictor comparison (p. 7); Table 4 chains and slack (p. 8); Fig. 8-15 results (pp. 9-11); Table 6 latencies (p. 11).

## What this source does not address
No branching workflows (that is [[bhasi-2021-kraken]]); no edge setting, no fixed total of container slots, no multi-node placement by data affinity, no data-transfer cost; no migration or churn limit (containers are only added and removed by queue and forecast); the scaling rule works per stage and does not re-plan a whole layout. Latency percentiles other than P99 and SLO percentage are not reported; there is no oracle bound.

## Focus: prior art for backlog-driven per-function container sizing at the edge (busiest-first rule, fixed capacity, churn) — 2026-10-22

**Carries Kernthesen 3, 5, 6, 7, 8, 11, 12.**

### What this focus needs beyond the Kernthesen
1. The reactive rule is queue length / batch size with a cold-start check; our busiest-first rule uses (load + backlog x run time / 120 s) / 0.8. Fifer's check "only add if waiting costs more than a cold start" is the cost test our rule lacks, and is the natural basis for a churn-aware variant.
2. Fifer adds containers without a capacity limit; in a fixed-slot edge cluster the same demand estimate has to be fitted to the total by proportional shrinking, which is a design choice of ours, not Fifer's.
3. Fifer's own ablation shows reactive-only scaling (RScale) loses on tail latency and SLO, matching our concern that a purely reactive rule is fragile under bursts.

### Direct quotes (for the draft)
> "the decision to queue versus starting up a new container depends on the SLO, execution times of the application and the cold-start latencies of the containers" (p. 3)

> "If Df > Cd, then LB spawns additional containers (Nc) for each stage. We refer to this as dynamic reactive scaling (RScale) policy." (p. 5)

### Examples & illustrations (for later drafting)
- Fig. 4: the same requests need 24 containers without batching and 10 with slack-aware batching (p. 4).
- Fig. 11: container shares per stage of the IPA chain under each policy; stage 2 (under 2% of run time) gets few containers (p. 10).

### Boundary of this focus
Cloud cluster, chains of ML microservices, containers added freely; evidence is relevant to the sizing rule and its cold-start check, not to edge placement or migration cost. Page numbers are the preprint's.

## Mentioned entities
- Concepts: [[backlog-driven-container-sizing]], [[cold-start]], [[predictive-pre-deployment]], [[container-keep-alive]]

## Connections
- Same sizing idea, extended to branching DAGs, in [[bhasi-2021-kraken]] (which names Fifer as a baseline and criticises it for ignoring workflow activation patterns).
- Stage-wise look-ahead pre-warming: [[daw-2020-xanadu]], [[mahgoub-2022-orion]]. Forecast-driven controller: [[nguyen-2025-taming]]; max(forecast, reactive) rule: [[gupta-2025-hybrid-reactive-proactive]].
