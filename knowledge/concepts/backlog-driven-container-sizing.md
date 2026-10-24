---
title: "Backlog-driven container sizing"
type: concept
created: 2026-10-22
updated: 2026-10-22
status: review
author: llm
tags: [autoscaling, container-scaling, queue-length, backlog, utilisation-target, g0-novelty]
---

# Backlog-driven container sizing

## Definition
Setting the number of containers of a function from its recent load plus the requests already waiting for it (its backlog), usually with a spare-capacity margin. Published forms: Fifer's reactive rule, containers = pending queue length / batch size, applied per stage of a function chain ([[gunasekaran-2020-fifer]], p. 5); Kraken's reactive scaler, extra = ceil(delayed requests / batch size) ([[bhasi-2021-kraken]], p. 160). The Kubernetes horizontal pod autoscaler computes desired = ceil(current x metric / target), which is a target-utilisation margin without a backlog term.

## Where it comes from
Per-function reactive autoscaling (HPA, Knative with a stable and a short panic window) was extended to function chains and DAGs because uniform scaling over-provisions stages with short run times. Fifer added slack-based batching and a cold-start test; Kraken added workflow-aware weights.

## How it is applied
On cloud clusters where containers can be added freely, for microservice chains and DAGs, with the cold-start cost as the guard against spawning too eagerly (spawn only if waiting costs more than a cold start). Results reported there: 76-80% fewer containers and 4x utilisation against non-batching baselines, with SLO violations at the baseline's level only when a forecast is added (Fifer, Kraken).

## Criticism
Reactive-only variants have worse tail latency and more SLO violations (Fifer's RScale: 10-12% more violations, up to 3x higher P99, p. 9). Both published works assume stable, profiled execution times and free capacity. A 2025 paper (arXiv 2502.14320, not yet read) argues that such rules under-provision under high execution-time variance.

## Not to be confused with
- **Keep-alive / pre-warming** ([[container-keep-alive]], [[predictive-pre-deployment]]): decides how long to keep or when to start containers, not how many each function gets.
- **Forecast-driven control** ([[nguyen-2025-taming]], [[gupta-2025-hybrid-reactive-proactive]]): the sizing signal is a forecast; here it is observed load and queue.
- **DFPS annealing**: moves one container per trial, scored by a queueing formula; no backlog signal.

## Relevance to this project
Our busiest-first rule sizes each function by (recent load + backlog x run time / 120 s) / 0.8, then fits the counts to a fixed number of slots and places them by data affinity. The sizing signal is therefore prior art, not our contribution; what differs is the fixed-capacity multi-node edge setting, the whole-layout re-plan over DFPS's initial placement, and the churn cap. Fifer's cold-start test is the published counterpart of the "is it worth it" check we lack. The baselines still to implement are an HPA-style rule (no backlog), a Fifer-style rule (queue length with the cold-start check) and a Kraken-style rule (smoothed load x invocation probability), adapted to our slot budget.

## Sources
[[gunasekaran-2020-fifer]], [[bhasi-2021-kraken]]; see also [[mahgoub-2022-orion]], [[daw-2020-xanadu]].

**Also cited here:** request-level container scheduling for serverless edge with deep reinforcement learning, no workflows (@chen-2026-scale, not ingested); keep-alive viewed as caching, which decides retention, not sizing (@fuerst-2021-faascache, not ingested).
