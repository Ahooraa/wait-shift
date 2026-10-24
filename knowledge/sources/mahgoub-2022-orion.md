---
title: "Mahgoub et al. 2022 — ORION and the Three Rights: Sizing, Bundling, and Prewarming for Serverless DAGs"
type: source
created: 2026-10-20
updated: 2026-10-20
status: review
author: llm
bibkey: mahgoub-2022-orion
depth: standard
tags: [serverless, dag, prewarming, cold-start, performance-model, aws-lambda, g0-novelty, related-work]
relations:
  - target: cold-start
    type: mentions
    confidence: extracted
    because: "Pre-warming with the right look-ahead delay hides initialisation time (Sec. 3.4, p. 308)."
  - target: predictive-pre-deployment
    type: supplements
    confidence: extracted
    because: "Uses the DAG structure and function latency distributions to start pre-warming downstream stages before they are needed (Sec. 3.4, p. 308)."
  - target: speculative-execution
    type: contradicts
    confidence: extracted
    because: "Shows bundling beats Spock-style speculative re-execution on latency and cost (Sec. 5.3, p. 311)."
  - target: dynamic-dag-workflow
    type: mentions
    confidence: extracted
    because: "States it cannot support dynamic DAGs whose path depends on request content (Sec. 8, p. 316)."
  - target: container-keep-alive
    type: mentions
    confidence: extracted
    because: "Argues keep-alive is insufficient for rarely invoked DAGs, which have a median 50% cold-start share (Sec. 2.1, p. 305)."
---

# ORION and the Three Rights: Sizing, Bundling, and Prewarming for Serverless DAGs

## Bibliographic Details
Mahgoub, Ashraf; Yi, Edgardo Barsallo; Shankar, Karthick; Elnikety, Sameh; Chaterji, Somali; Bagchi, Saurabh. 2022. *ORION and the Three Rights: Sizing, Bundling, and Prewarming for Serverless DAGs*. 16th USENIX Symposium on Operating Systems Design and Implementation (OSDI 22), pp. 604-621. https://www.usenix.org/conference/osdi22/presentation/mahgoub. Code: github.com/icanforce/Orion-OSDI22.

> Page note: page refs are the printed USENIX pages 303-320 (PDF page + 301; PDF page 1 is the cover).

## Section map

| Covered | Section | pp. |
|---|---|---|
| ✓ F1 | 1 Introduction (key idea, contributions) | 303-304 |
| ✓ F1 | 2 Motivation: Azure Durable Functions workload characterisation; performance modelling | 304-306 |
| ✓ F1 | 3.1 E2E latency model (CONV and MAX, correlation) | 306-307 |
| ✓ F1 | 3.2 Right-sizing (best-first search over VM sizes) | 307-308 |
| ✓ F1 | 3.3 Bundling parallel invocations | 308-309 |
| ✓ F1 | 3.4 Right pre-warming delays | 309 |
| ✓ F1 | 3.5, 4 Design considerations; implementation (AWS Lambda, Step Functions) | 309-310 |
| ✓ F1 | 5 Evaluation (3 DAG apps, 3 baselines, microbenchmarks, Azure) | 310-314 |
| ✓ F1 | 6 Pre-warming policy simulator with oracle | 314-315 |
| ✓ F1 | 7-9 Related work, discussion, conclusion | 314-316 |

## Kernthesen

### 1. ⭐ Serverless DAG latency varies strongly: P95 is 80x P25 for the five most frequent Azure DAGs, so a distribution, not a mean, must be modelled (pp. 304-305)
Median depth 3, P95 depth 8; 65% linear chains; width up to 37 at P95; skew among parallel workers at least 2x for 98.2% of DAGs (Fig. 4-6).

### 2. ⭐ Rarely invoked DAGs are mostly cold: 80% of DAGs run under 100 times per day and have a median 50% cold starts; frequent ones (at least 100 per day) have a median 0.35% (p. 305, Fig. 7)
Hence keep-alive alone is not enough and pre-warming is needed.

### 3. ⭐ End-to-end latency is estimated by convolution for in-series stages and a max operation for parallel ones, with correlations handled by conditional distributions (Sec. 3.1, pp. 306-307)
Pearson threshold 0.4 decides dependent versus independent formulation; correlations were at most pairwise. Ignoring correlation over-estimates parallel stages (Eq. 1).

### 4. Per-function latency models come from profiling four VM sizes plus percentile-wise interpolation; 5-6 regions suffice (Sec. 3.2, p. 307)
About 300 profiling runs per application; the largest error source is interpolation (Sec. 5.4.2).

### 5. ⭐ Right-sizing is a best-first search over vectors of VM sizes (64 MB steps) that meets a latency target at minimum cost (Alg. 1, p. 308)
Each iteration takes 3-7.5 ms and explores under 1% of states; achieved latency is within -2.75% to +4.93% of target (Table 3, p. 314).

### 6. ⭐ Bundling co-locates parallel invocations in one larger VM so stragglers inherit freed resources; the best bundle size is found by multiplicative search (Sec. 3.3, p. 308-309)
Optimum 6 for Video Analytics, 2 for the network-bound Chatbot; beyond the VM core limit contention raises latency (Fig. 16, p. 314).

### 7. ⭐ Pre-warming delay for stage s is the time from DAG start to the start of initialising that stage's VMs; the optimal vector minimises E2E latency subject to a target utilisation (Eq. 2, p. 309)
The first stage's delay is fixed at zero because predicting DAG arrivals is "challenging in the general case".

### 8. The delay vector is found by best-first search in 100 ms steps; the search takes 0.4-3 s (Sec. 3.4, 4; pp. 309, 310)
Early pre-warming wastes utilisation, late pre-warming adds latency (Fig. 10).

### 9. ⭐ Right pre-warming lowers P95 latency against no pre-warming and keeps utilisation higher than starting everything at zero delay (Fig. 15, Sec. 5.4.1, p. 312)
The figure labels give improvements over ORION Cold-Start (P95 latency) and over Zero-Delay (utilisation) per application; I did not map each label to its application from the extracted text. Latency gains are larger for Video Analytics and ML Pipeline than for Chatbot because of heavier initialisation (p. 312).

### 10. ⭐ ORION achieves up to 90% lower P95 latency at equal cost, or up to 53% lower cost at equal P95, compared with Best-Memory, Speculative-Execution and CherryPick (Abstract, Sec. 5.3, pp. 303, 311-312)
CherryPick needs 10K profiles against ORION's 300.

### 11. A simulator with an oracle that knows exact runtimes gives the theoretical best utilisation for pre-warming (Sec. 6, Fig. 19, p. 315)
The oracle's per-invocation delay search space grows exponentially with DAG width; ORION's deterministic per-stage delay is the 0% variability point.

### 12. ⭐ Stated limits: no dynamic DAGs, no queueing model (assumes near-unlimited provider capacity), models are retrained when the workload changes, pre-warming is a hint (Sec. 8, p. 316)
"Cloud providers operate large serverless platforms, providing virtually infinite capacity, reducing queuing delays to primarily cold-start latencies."

## Figures and tables
Fig. 1 overview (p. 304); Fig. 4-7 Azure characterisation (pp. 305-306); Fig. 9 bundling example (p. 309); Fig. 10 pre-warming cases (p. 309); Fig. 11-14 end-to-end; Fig. 15 pre-warming vs utilisation (p. 312); Table 1-3 correlation, estimation error, configurations (pp. 312-314); Fig. 19 oracle simulation (p. 315).

## What this source does not address
Not edge: unlimited-capacity cloud (AWS Lambda, Azure), no placement across servers, no data-transfer or locality cost; no queueing or overload (hence no admission control); no prediction of when a DAG request arrives (first-stage delay fixed at 0); no re-planning at run time based on observed bursts; no dynamic DAGs. It does not compare against RL or DFPS-type schedulers.

## Focus: prior art for look-ahead, simulation-judged and regime-aware container re-planning of serverless workflows at the edge (D1-D3) — 2026-10-20

**Carries Kernthesen 2, 3, 7, 8, 11, 12.**

### What this focus needs beyond the Kernthesen
1. Pre-warming here is within one request: when stage k starts, the delay before warming stage k+1 comes from latency CDFs. Our D1/D3 look-ahead is across requests: forecast aggregate load and re-plan the layout.
2. The ORION utilisation-versus-latency trade-off (early versus late pre-warming, Fig. 10) is the same trade-off as our look-ahead length; its oracle (Fig. 19) is an upper-bound device in the same spirit as our cheaters, but it bounds only the delay choice, not layout.
3. The model assumes no queueing; our edge setting is queue-dominated, which is why a clone of the live simulator replaces the formula (compare our failed O3 queueing surrogate).

### Direct quotes
> "Cloud providers operate large serverless platforms, providing virtually infinite capacity, reducing queuing delays to primarily cold-start latencies" (p. 316, Sec. 8)

> "For the first stage in the DAG, we have the degenerate case and set its delay (d1) to zero. This is because pre-warming requires predicting when the DAG will be invoked, which is challenging in the general case." (p. 309, Sec. 3.4)

### Examples & illustrations
- Fig. 9: four parallel workers needing 7, 1, 3, 1 time steps; separate VMs take 7, a bundle of four cores takes 3 at equal cost (p. 309).
- Fig. 10: chain F1-F2 under no, early, right and late pre-warming (p. 309).

### Boundary of this focus
ORION is the closest prior art on the "stage-k warms stage k+1 with the right look-ahead" idea and on oracle-style bounds, but in an unlimited-capacity cloud without placement or queueing; it does not touch edge layouts, overload, or arrival forecasting.

## Mentioned entities
- Concepts: [[cold-start]], [[predictive-pre-deployment]], [[speculative-execution]], [[dynamic-dag-workflow]], [[container-keep-alive]]

## Connections
- Pre-warms by DAG structure like [[daw-2020-xanadu]] (Xanadu cannot determine the optimal pre-warming time, p. 315); contrasts with [[speculative-execution]] baselines.
- Complements [[nguyen-2025-taming]] (aggregate forecast) and [[ray-2020-proactive-placement]] (prefetch along a workflow); static DAG placement baseline: [[deng-2022-dependent-function-embedding]].

