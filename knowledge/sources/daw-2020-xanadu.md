---
title: "Daw, Bellur & Kulkarni 2020 — Xanadu: Mitigating Cascading Cold Starts in Serverless Function Chain Deployments"
type: source
created: 2026-10-20
updated: 2026-10-20
status: review
author: llm
bibkey: daw-2020-xanadu
depth: standard
tags: [serverless, workflows, cascading-cold-start, speculative-deployment, just-in-time, prewarming, g0-novelty, related-work]
relations:
  - target: predictive-pre-deployment
    type: supplements
    confidence: extracted
    because: "Speculative and just-in-time provisioning of sandboxes along the most likely path of a workflow (Sec. 3, pp. 360-363)."
  - target: cold-start
    type: mentions
    confidence: extracted
    because: "Cascading cold start overhead grows linearly with chain depth: 46% of a six-function chain with 5 s functions, up to 90% with 500 ms functions (Sec. 1, p. 357)."
  - target: dynamic-dag-workflow
    type: mentions
    confidence: extracted
    because: "Handles conditional (XOR-cast) chains by estimating the most likely path (Sec. 3.1, p. 360)."
  - target: apache-openwhisk
    type: mentions
    confidence: extracted
    because: "Baseline platform in the evaluation, with Knative (Sec. 5, p. 364)."
  - target: container-keep-alive
    type: mentions
    confidence: extracted
    because: "Measures reclaim after about 10 minutes of idle on AWS Step Functions and about 20 minutes on Azure Durable Functions (Sec. 2.3, p. 359); future work proposes shortening keep-alive (Sec. 7, p. 368)."
---

# Xanadu: Mitigating cascading cold starts in serverless function chain deployments

## Bibliographic Details
Daw, Nilanjan; Bellur, Umesh; Kulkarni, Purushottam. 2020. *Xanadu: Mitigating cascading cold starts in serverless function chain deployments*. Proceedings of the 21st International Middleware Conference (Middleware '20), Delft, pp. 356-370. DOI 10.1145/3423211.3425690.

> Page note: page refs are the printed ACM pages 356-370.

## Section map

| Covered | Section | pp. |
|---|---|---|
| ✓ F1 | 1 Introduction (cascading cold starts, contributions) | 356-357 |
| ✓ F1 | 2 Background: function chains, empirical analysis of AWS/Azure/Knative/OpenWhisk, cost metrics | 357-360 |
| ✓ F1 | 3 Key ideas: most likely path, aggressiveness, JIT deployment, implicit chains | 360-363 |
| ✓ F1 | 4 Implementation (Node.js testbed) | 363-364 |
| ✓ F1 | 5 Evaluation | 364-368 |
| ✓ F1 | 6-8 Related work, future work, conclusion | 368 |

## Kernthesen

### 1. ⭐ In a function chain, cold starts cascade: one trigger can cause one cold start per function, so the overhead grows linearly with chain depth (pp. 357-358)
5 s functions: 46% of a six-function chain's duration is cold-start overhead; 500 ms functions: up to 90%.

### 2. Public clouds show the effect: cold overhead was 48.5% of run time on AWS Step Functions and 41.2% on Azure Durable Functions, against 13.2% and 13.8% warm (p. 358)
Linear fits R^2 0.993 and 0.953.

### 3. Keep-alive does not hide it for rare workflows: AWS reclaims workflow resources after about 10 minutes idle, Azure after about 20, and about 45% of Azure functions run at most once per hour (p. 359)
At about 2 requests per hour, 78.1% (ASF) and 62.5% (ADF) of requests suffered cascading cold starts.

### 4. Stronger isolation raises the cost: containers add 2.5x to 2.9x overhead over processes or V8 isolates (p. 360)

### 5. ⭐ Two overhead costs are defined: latency overhead C_D (extra latency beyond the longest path's run time) and resource overhead C_R (resource-time held before use); their product phi is the figure of merit (Eq. 1-2, pp. 358, 360)
Naive over-provisioning lowers C_D but raises C_R.

### 6. ⭐ Xanadu estimates the Most Likely Path (MLP) of a workflow from branch probabilities, kept by exponential averaging, and only provisions along it (Sec. 3.1, Alg. 1, pp. 360-361)
It converged within 7-8 triggers on a branching test DAG, on average 2 requests for workflows up to 4 functions and 5.3 for more than eight (p. 365).

### 7. ⭐ A prediction miss can make speculative provisioning worse than no optimisation: three misses gave 17.7 s with speculation against 17.17 s without (Table 1, p. 362)

### 8. ⭐ A provider-side "deployment aggressiveness" parameter sets how far down the chain sandboxes are pre-provisioned, trading cost overrun against cold start (Sec. 3.2.1, p. 362)

### 9. ⭐ Just-in-time deployment plans a timeline from profiled cold-start and warm-start times and starts each sandbox just before its expected invocation; on a prediction miss, all planned provisioning stops (Sec. 3.2.2, Alg. 2, p. 362-363)
Warm-start time stands in for a function's lifetime because the platform cannot see inside the runtime; for a barrier node the slowest parent sets the delay.

### 10. Implicit chains are detected by patching HTTP libraries so each call carries the caller's identity; branch probabilities are updated per request (Sec. 3.3, Alg. 3, p. 363)

### 11. ⭐ Results: speculation keeps overhead nearly constant (4.85 s at depth 10 against 76.34 s Knative and 44.38 s OpenWhisk); JIT costs only 0.9% more CPU than cold mode but 2.18x more memory; Speculative can cost 250x more memory (Sec. 5.1-5.2, pp. 364-365)
Phi_cpu improves 5.8x and phi_memory 1.7x over Xanadu Cold; JIT also beats speculative on latency because Docker cannot start many sandboxes at once.

### 12. ⭐ Under prediction misses on 100 random trees, speculative and JIT gain 37% and 34% latency on average over cold; limits and future work: miss recovery only stops speculation, keep-alive could drop to seconds, integration needs function profiles (Sec. 5.4, 7; pp. 365, 368)
Single 64-core machine; load generated by JMeter; baselines at default settings.

## Figures and tables
Fig. 1 cascading overhead; Fig. 2 chain relationships; Fig. 3-7 platform measurements; Fig. 8-9 MLP; Table 1 miss costs (p. 362); Fig. 10 JIT sequence; Fig. 12-16 evaluation; Fig. 17 case studies (e-commerce, image pipeline).

## What this source does not address
Not edge and not multi-node: one 64-core host, no placement, no data-transfer cost; it predicts which functions of one request run next, not the volume of future requests; no overload, queueing or admission; no look-ahead simulation of a scheduler; no comparison with learned (RL) or placement schedulers. ORION (2022) notes Xanadu "cannot determine the optimal pre-warming time" ([[mahgoub-2022-orion]], p. 315).

## Focus: prior art for look-ahead, simulation-judged and regime-aware container re-planning of serverless workflows at the edge (D1-D3) — 2026-10-20

**Carries Kernthesen 1, 5, 6, 7, 8, 9, 12.**

### What this focus needs beyond the Kernthesen
1. "When stage 1 starts, warm stage 2" (JIT) is the stage-based form of pre-warming. Our look-ahead is over aggregate downstream load across requests and over layouts on many edge nodes. This is the closest prior art for the parked ablation C.
2. Aggressiveness (fraction of chain depth to look ahead) is the same dial as our look-ahead length; the paper tunes it by hand ("tuned dynamically based on function chain characteristics and deployment costs", p. 357) but gives no sweep or oracle bound.
3. The miss penalty result (Kernthese 7) matches our D1 finding that a wrong forecast can be worse than doing nothing, which is why we judge switches by a simulator clone.
4. Evaluation is against Knative and OpenWhisk defaults, not against optimised schedulers.

### Direct quotes
> "This parameter controls the fraction of the total depth to which execution sandboxes for functions should be provisioned or how much should the pre-provisioning algorithm look ahead." (p. 362, Sec. 3.2.1)

> "JIT deployment stops all planned proactive provisioning as soon as it detects a prediction miss." (p. 362, Sec. 3.2.2)

### Examples & illustrations
- Fig. 8-9: an XOR-cast DAG with a 70% branch; the MLP is mostly correct after Round 5 and stable after 7 triggers (pp. 360-361).
- Table 1: depth-5 chain with three conditional points, average and worst-case misses (p. 362).

### Boundary of this focus
The sections read in full: all. Pre-empts "predict the next stage and pre-warm just in time" for single-node chains; does not touch multi-node edge layouts or overload.

## Mentioned entities
- Concepts: [[predictive-pre-deployment]], [[cold-start]], [[dynamic-dag-workflow]], [[container-keep-alive]]
- Systems: [[apache-openwhisk]]

## Connections
- Same stage-based idea as [[mahgoub-2022-orion]] (which adds latency distributions and a utilisation target) and [[ray-2020-proactive-placement]] (prefetch along a workflow).
- Contrasts with the aggregate forecasting in [[nguyen-2025-taming]].

