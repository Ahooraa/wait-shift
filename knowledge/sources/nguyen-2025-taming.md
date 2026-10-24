---
title: "Nguyen, Bhuyan & Elmroth 2025 — Taming Cold Starts: Proactive Serverless Scheduling with MPC"
type: source
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
bibkey: nguyen-2025-taming
depth: standard
tags: [serverless, cold-start, model-predictive-control, prewarming, request-shaping, openwhisk, g0-novelty]
relations:
  - target: model-predictive-control
    type: builds-on
    confidence: extracted
    because: "Formulates cold-start mitigation as receding-horizon constrained optimisation: «MPC optimizes system behavior over a receding time horizon by solving a constrained optimization problem at each control step» (Sec. I)."
  - target: icebreaker
    type: builds-on
    confidence: extracted
    because: "Adopts and extends the Fourier forecaster of IceBreaker («inspired by [15]») and uses it as the main baseline (Secs. I, III-A, IV)."
  - target: icebreaker
    type: contradicts
    confidence: extracted
    because: "Claims IceBreaker «does not coordinate prewarming completion with request dispatch» and shows joint prewarm+dispatch MPC outperforms it (Sec. II, V-B)."
  - target: cold-start
    type: mentions
    confidence: extracted
    because: "The problem addressed throughout (Sec. I)."
  - target: apache-openwhisk
    type: mentions
    confidence: extracted
    because: "Implementation platform and default-policy baseline (Sec. IV)."
---

# Taming Cold Starts: Proactive Serverless Scheduling with Model Predictive Control

## Bibliographic Details
Nguyen, Chanh; Bhuyan, Monowar; Elmroth, Erik. 2025. *Taming Cold Starts: Proactive Serverless Scheduling with Model Predictive Control*. 2025 33rd Int. Symp. on Modeling, Analysis and Simulation of Computer and Telecommunication Systems (MASCOTS), pp. 1-8. DOI 10.1109/MASCOTS67699.2025.11283271. arXiv:2508.07640v2 (13 Jan 2026).

> Page note: the PDF read is the arXiv v2 layout (about 6 physical pages); page refs below are approximate positions in that file (p.1 abstract/intro, p.2 related work + forecasting, p.3 optimiser, p.4 actuators + setup, p.5 evaluation, p.6 limitation/conclusion). The section number is the stable anchor.

## Section map

| Covered | Section | pp. |
|---|---|---|
| ✓ F1 | I. Introduction (OpenWhisk cold-start example, request-shaping insight, contributions) | 1-2 |
| ✓ F1 | II. Related work (runtime-level vs scaling-based; LaSS, IceBreaker) | 2 |
| ✓ F1 | III-A Invocation forecast (quadratic trend + k Fourier harmonics, statistical clipping) | 2 |
| ✓ F1 | III-B Optimizer (cost terms, objective Eq. 9, dynamics/constraints Eq. 10-18, cvxpy) | 3 |
| ✓ F1 | III-C Actuators (dispatch Alg. 1, prewarm, reclaim Alg. 2) | 3-4 |
| ✓ F1 | IV. Experimental setup (k3s single node, EfficientDet, Azure + synthetic, baselines, metrics) | 4-5 |
| ✓ F1 | V-A to V-D Evaluation (forecast accuracy, response time, resources/keep-alive, overhead) | 5-6 |
| ✓ F1 | V-E Limitation; VI Conclusion and future work | 6 |

## Kernthesen

### 1. ⭐ Cold starts are a latency problem, and reactive platforms trigger them as soon as no warm container is free (pp. 1-2)
A 280 ms EfficientDet function suffers about 10.5 s on a cold start (38x), and 8 of 50 randomly-timed requests were cold (Fig. 1). Default platforms start a cold container immediately without deferring or batching (Sec. I).

### 2. ⭐ Predictive request shaping: briefly deferring a request until a soon-to-be-free warm container can beat starting a cold one (p. 2)
If r2 arrives shortly before r1 finishes and no other container is warm, waiting (t1 + exec) - t2 avoids a cold start (Fig. 2). The paper presents "predictive shaping" as its key insight beyond plain provisioning.

### 3. ⭐ Cold-start mitigation is formulated as an MPC problem that jointly decides prewarm, reclaim and dispatch (pp. 1-3)
At every control interval: forecast H steps, solve an H-step optimisation, execute only the current-step actions (Sec. III). Joint treatment of admission, provisioning and reclamation is the stated reason for choosing MPC (Sec. I).

### 4. ⭐ The forecaster is a quadratic trend plus k Fourier harmonics, clipped to [0, mean + beta*std] (p. 2)
Eq. (1)-(2); borrowed and extended from IceBreaker; the authors state forecasting "is not the central contribution". Clipping is the only robustness device (no uncertainty set, no worst-case bound).

### 5. ⭐ The objective is a weighted sum of six per-step costs (p. 3)
Cold-delay penalty, queue-wait cost, over-provisioning penalty, cold-start cost, reclaim reward, smoothness penalty (Eq. 3-9). Weights are hand-tuned scalars.

### 6. Plant model: aggregate queue/warm-pool dynamics with a deterministic discrete cold-start delay (p. 3)
q_{k+1} = q_k + lambda_k - s_k; warm containers gain readyCold(k) = x_{k-D}; service rate mu = 1/L_warm; constraints Eq. 11-18 including mutual exclusivity of cold starts and reclaims. One function, homogeneous containers, no per-request structure.

### 7. The convex program is solved with cvxpy in about 38 ms per step; forecasting costs 0.1 ms (pp. 3, 6)
Overhead is shown to be negligible (Sec. V-D, Fig. 8).

### 8. Actuators: batch dispatch from a Redis queue; prewarm via forcePrewarm invocations; safe reclaim via a Loki completion check (p. 4)
Algorithms 1-2. Implemented as middleware with no OpenWhisk core change.

### 9. Fourier forecasting beats ARIMA on the Azure trace (86.2% vs 82.5%) and ties on synthetic data (95.3% vs 95.9%) (p. 5)
Fourier is over 100x faster than ARIMA (0.1 ms vs 10 ms) (Sec. V-A, Fig. 4).

### 10. ⭐ On a bursty synthetic workload MPC cuts mean/P90/P95 response time by 82.9/85.5/82.6% vs OpenWhisk; on the steady Azure-derived workload only 17.9/20.6/23.6% (p. 5)
IceBreaker gets 67.7/51.1/45.4% (synthetic) and 13.9/17.1/18% (Azure). The MPC advantage over IceBreaker is attributed to joint dispatch+prewarm despite identical forecasters (Sec. V-B).

### 11. Resource use: warm containers -34.8% and keep-alive -64.3% on Azure (-19.1% / -15.7% on synthetic) vs the 10-minute default (p. 6)
IceBreaker: 17.4%/43% and 14.8%/11.3% (Sec. V-C).

### 12. ⭐ Stated limitations: accuracy depends on the forecast; gains are marginal on steady traffic; parameters (horizon, weights) were calibrated empirically and are workload-specific (p. 6)
The authors propose automated online tuning (Bayesian optimisation, RL, meta-learning) and heterogeneous multi-platform / edge-cloud orchestration as future work (Sec. V-E, VI).

## Figures and tables
Fig. 1 cold-start example (p. 1); Fig. 2 deferral illustration (p. 2); Fig. 3 architecture (p. 2); Table I symbols (p. 3); Fig. 4 forecast error (p. 5); Fig. 5-7 response time, containers, keep-alive (pp. 5-6); Fig. 8 control overhead (p. 6).

## What this source does not address
No workflows or DAGs (one EfficientDet function, one function per request); no edge placement or multi-node topology (single k3s node; edge-cloud is future work); no explicit admission control or load shedding (the queue is bounded only by capacity; "admission" here means how many queued requests to dispatch now); no worst-case or robustness guarantee and no sensitivity study of forecast error; no event- or cost-triggered reconfiguration (fixed-interval control). Placement/heterogeneity appears only via [[icebreaker]], where it was disabled in the evaluation.

## Focus: G0 novelty gate for D1/D2/D3 (plan faas-edge-adaptation) — 2026-10-13

**Carries Kernthesen 3, 4, 5, 6, 10, 12.**

### What this focus needs beyond the Kernthesen
1. MPC horizon: H is a symbol only; the paper gives no numeric H and no control interval, and lists horizon as a sensitive, empirically calibrated parameter (Sec. III, V-E, pp. 2, 6).
2. Trigger policy: periodic. The scheduler "is executed at every control interval" (Sec. III, p. 2); no event- or cost-triggered re-solve, no switching-cost-aware choice of when to reconfigure. The only temporal-stability mechanism is the smoothness penalty on (w_k - w_{k-1})^2 and (x_k - x_{k-1})^2 (Eq. 8, p. 3).
3. Robustness to forecast error: none formal. Only clipping of the forecast to [0, mean + beta*std] (Eq. 2, p. 2); forecast error is reported (Fig. 4) but never injected into the control loop; the limitation section concedes reliance on forecast accuracy (p. 6).
4. Workload/trace: Microsoft Azure Functions trace (Shahrad et al.), only inter-arrival times from two weeks of logs, replayed for 60 min on one function; synthetic bursty arrivals (bursts 1-5 s, idle 50-800 s, 5-300 req/s) (Sec. IV, p. 4). Baselines: OpenWhisk default (10-min keep-alive) and IceBreaker adapted to a homogeneous setting. Metrics: total response time (queue + cold start + exec; mean, P90, P95), warm-container count, keep-alive duration (pp. 4-5). No makespan, SLO-goodput or state-transfer metric.
5. Testbed: single k3s node, 32 vCPU, up to 64 replicas of 256 MB / 0.5 vCPU; controller on a separate machine (p. 4).

### Direct quotes (for the draft)
> "Our key insight is that cold start delays can be reduced not just through provisioning, but also through predictive shaping" (pp. 1-2, Sec. I)

> "the MPC scheduler is executed at every control interval" (p. 2, Sec. III)

> "performance is sensitive to choices like the control horizon and objective weights. Our parameters were empirically calibrated, but this ad hoc approach is workload-specific." (p. 6, Sec. V-E)

> "As our contribution centers on scheduling logic and request shaping rather than container placement or distributed orchestration, a single-node deployment is sufficient" (p. 4, Sec. IV)

### Examples & illustrations (for later drafting)
- Fig. 2 deferral example: r2 waits for r1's container instead of paying a 10.5 s cold start (p. 2).
- EfficientDet robotics function: 280 ms warm vs 10.5 s cold (pp. 1, 4).

### Boundary of this focus
Evidence is single-function, single-node, fixed-interval; nothing here speaks to DAG critical paths, overload shedding, state locality or edge placement. Page numbers are approximate (arXiv layout).

## Mentioned entities
- Concepts: [[model-predictive-control]], [[cold-start]]
- Software/systems: [[apache-openwhisk]], [[icebreaker]]

## Connections
- Builds on and outperforms [[icebreaker]] (same Fourier forecaster; adds dispatch deferral). Typed in `relations:`.
- Applies [[model-predictive-control]] to [[cold-start]] mitigation on [[apache-openwhisk]].

## G0 verdict (plan faas-edge-adaptation, Task 2)
- **D1 (when to reconfigure): partially overlapping.** The paper is a forecast-driven receding-horizon controller (H-step plan, only the first step executed, Sec. III, p. 2) with a smoothness penalty (Eq. 8, p. 3), so forecast-based proactive reconfiguration is pre-empted for single functions; but the trigger is a fixed periodic interval, there is no cost- or event-triggered decision of when to re-solve, no worst-case guarantee under forecast error (only clipping, Eq. 2, p. 2; limitation, p. 6), no workflows and no edge (Sec. IV, p. 4), so "when to reconfigure" and "robust to forecast error" stay open.
- **D2 (overload admission + critical-path dispatch): clear.** Requests are queued and dispatched in batches bounded by warm capacity (Alg. 1, p. 4) with a queue-wait cost (Eq. 4, p. 3); there is no load shedding or SLO-aware admission, no overload regime (the Azure trace is steady and gains marginal, pp. 5-6), and no DAG or critical-path notion (single function, Sec. IV).
- **D3 (coupled placement-dispatch): clear.** Single-node testbed with placement explicitly out of scope (Sec. IV, p. 4); the only placement mechanism in the comparison (IceBreaker heterogeneity) was disabled (p. 4); the paper's "joint optimization" couples prewarming with dispatch timing, not placement with dispatch, and edge-cloud is future work (Sec. VI, p. 6). Caution: its prewarm-dispatch coupling is a related-work item D3 must distinguish from.
