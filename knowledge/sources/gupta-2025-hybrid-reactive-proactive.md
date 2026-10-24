---
title: "Gupta, Islam & Buyya 2025 — A Hybrid Reactive-Proactive Auto-scaling Algorithm for SLA-Constrained Edge Computing"
type: source
created: 2026-10-20
updated: 2026-10-20
status: review
author: llm
bibkey: gupta-2025-hybrid-reactive-proactive
depth: standard
tags: [autoscaling, edge, hybrid-reactive-proactive, lstm, sla, kubernetes, g0-novelty, related-work]
relations:
  - target: model-predictive-control
    type: mentions
    confidence: inferred
    because: "Same family (forecast-driven control) but no receding-horizon optimisation: the controller only takes max(forecast replicas, reactive replicas) (Alg. 1, p. 5)."
  - target: cold-start
    type: mentions
    confidence: extracted
    because: "Defines cold-start time as deploy + register time of a replica and ties SLA violations to it (Eq. 2, Sec. 3.2, p. 4)."
  - target: predictive-pre-deployment
    type: supplements
    confidence: inferred
    because: "Forecast-ahead replica provisioning for edge microservices; same idea at replica-count level, not placement level."
---

# A Hybrid Reactive-Proactive Auto-scaling Algorithm for SLA-Constrained Edge Computing

## Bibliographic Details
Gupta, Suhrid; Islam, Muhammed Tawfiqul; Buyya, Rajkumar. 2025. *A Hybrid Reactive-Proactive Auto-scaling Algorithm for SLA-Constrained Edge Computing*. arXiv:2512.14290 (preprint, University of Melbourne). PDF: `library/pdf/gupta-2025-hybrid-reactive-proactive.pdf`.

> Page note: physical pages of the arXiv layout (10 pages); page refs are those positions.

## Section map

| Covered | Section | pp. |
|---|---|---|
| ✓ F1 | 1 Introduction; 2 Related work (reactive, proactive, hybrid autoscalers) | 1-3 |
| ✓ F1 | 3 System model: SLA categories, cold-start time, optimisation problem P | 3-4 |
| ✓ F1 | 4 Hybrid autoscaler: architecture, scheduler (Alg. 1), reactive HPA, pre-processor, LSTM | 4-6 |
| ✓ F1 | 5-6 Experiments (DeathStarBench-style social network, 3 SLA thresholds, GET/POST) | 6-10 |
| ✓ F1 | 7 Conclusions and future work | 10 |

## Kernthesen

### 1. ⭐ Pure reactive autoscalers lag behind demand and pure proactive ones fail without training data; a hybrid keeps both benefits (pp. 1-2)
Reactive threshold rules are simple but scale after the load has arrived; proactive ML forecasters need data and mis-forecast at the start.

### 2. ⭐ Cold-start time is modelled as replica deploy time plus control-plane registration time, and SLA violations grow with it (Eq. 2-3, p. 4)
C(t) = R_deploy(t) + R_register(t); image download is ignored as a one-time cost.

### 3. The scaling objective is a weighted sum of SLA latency and cost, x = y = 0.5, described as a knapsack-type NP-hard problem (Eq. 4-5, p. 4)
Solved only by approximation (rules or learning), not exactly.

### 4. ⭐ The hybrid rule is "take the larger of the forecast replica count and the reactive replica count" (Alg. 1, p. 5)
replicas_forecast = ceil(current × metric_forecast / metric_desired); replicas_reactive likewise on the current metric; desired = forecast if forecast > reactive, else reactive. No cost-aware arbitration and no look-ahead search.

### 5. The reactive part is the Kubernetes horizontal pod autoscaler with cooldowns set to 15 s (Sec. 4.3, p. 5)
Tolerance 0.1 default; moderate cooldown chosen for stability.

### 6. A feedback controller tunes the LSTM hyper-parameters when SLA violations are seen in a window (Sec. 4.1, p. 4)
A heuristic replaces manual hyper-parameter tuning; the learning rate is clamped by max(lr - 0.0005, 0.002) (p. 6).

### 7. A small, smoothed LSTM is trained online so it can run on resource-limited edge nodes (Sec. 4.4, pp. 5-6)
The data pre-processor removes noise before forecasting to reduce cost.

### 8. ⭐ Results: the hybrid has at most 5.41% SLA violations, state-of-the-art autoscalers 18.8-22.38% (pp. 9-10)
GET moderate threshold: default 8.74%, PPA 2.91%, hybrid 0.42%; strict: default 14.8%, hybrid 1.66%. POST strict: default 22.38%, reactive 18.8%, proactive 9.94%, hybrid 5.41%.

### 9. Violations appear in the first day because of missing training data and are then counteracted by hyper-parameter tuning (pp. 8-9)
The proactive component needs warm-up; the reactive part covers it.

### 10. ⭐ Stated limits: single-metric SLA, horizontal scaling only; future work covers multi-variate forecasting, vertical autoscaling, multi-SLA, cluster-level node management (p. 10)

## Figures and tables
Fig. 2 hybrid architecture (p. 4); Alg. 1 scheduler (p. 5); result tables for GET and POST under flexible, moderate and strict SLA thresholds (pp. 9-10).

## What this source does not address
Not serverless workflows or DAGs (a microservice deployment scaled by replica count); no placement of replicas across edge nodes (that is future "cluster-level auto-scaling"); no admission control; no simulation of the scheduler; no oracle or upper bound on what any controller could gain; no regime trigger beyond the forecast-versus-reactive comparison.

## Focus: prior art for look-ahead, simulation-judged and regime-aware container re-planning of serverless workflows at the edge (D1-D3) — 2026-10-20

**Carries Kernthesen 1, 2, 4, 8, 10.**

### What this focus needs beyond the Kernthesen
1. The rule is a hybrid at the level of a replica count for one deployment; our D1 hybrid is a layout (placement plus container counts) decision judged by cloning the live simulator.
2. "Take the larger of the two" is a first-order version of our finding that a reactive rule alone lags and a forecast alone is risky; it does not use workload regimes.
3. Reported gains are against Kubernetes-type autoscalers, not against an oracle, so they give no headroom estimate.

### Direct quotes
> "If the forecasted requirement is higher than current, the scheduler outputs the forecaster replica count as desired replicas. Otherwise, the reactive replica count is used." (p. 4, Sec. 4.2)

### Boundary of this focus
Related but not pre-empting: edge microservices, replica counts, no DAGs, no placement. Cite as hybrid reactive/proactive prior art.

## Mentioned entities
- Concepts: [[cold-start]], [[model-predictive-control]], [[predictive-pre-deployment]]

## Connections
- Hybrid forecast-and-reactive control related to [[model-predictive-control]] and [[predictive-pre-deployment]]; see also [[lei-2026-multi-agent]] for a purely reactive regime switch.
