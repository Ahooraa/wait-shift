---
title: "Bhasi et al. 2021 — Kraken: Adaptive Container Provisioning for Deploying Dynamic DAGs in Serverless Platforms"
type: source
created: 2026-10-22
updated: 2026-10-22
status: review
author: llm
bibkey: bhasi-2021-kraken
depth: standard
based_on: preprint
tags: [serverless, dynamic-dag, container-provisioning, invocation-probability, batching, proactive-reactive, g0-novelty, baseline]
relations:
  - target: backlog-driven-container-sizing
    type: supports
    confidence: extracted
    because: "Reactive scaler spawns containers for queued requests whose wait exceeds the cold start: extra = ceil(delayed requests / batch size) (Alg. 2, p. 160)."
  - target: dynamic-dag-workflow
    type: supports
    confidence: extracted
    because: "Targets dynamic DAGs where the invoked path depends on the request (Sec. 2.1.2, p. 154)."
  - target: daw-2020-xanadu
    type: contradicts
    confidence: extracted
    because: "Argues that provisioning only along the most likely path under-provisions off-path functions and, in its experiments, over-provisions by 32% (p. 155)."
  - target: gunasekaran-2020-fifer
    type: builds-on
    confidence: extracted
    because: "Uses slack-aware batching as in Fifer and adds workflow-aware weights; Fifer spawns 76% more containers because it ignores workflow activation patterns (p. 161)."
  - target: deathstar-benchmark
    type: mentions
    confidence: extracted
    because: "Evaluated on Social Network, Media Service and Hotel Reservation from DeathStarBench (p. 160)."
  - target: cold-start
    type: mentions
    confidence: extracted
    because: "Cold-start spillover from under-provisioned critical functions to their descendants (p. 156)."
---

# Kraken: Adaptive Container Provisioning for Deploying Dynamic DAGs in Serverless Platforms

## Bibliographic Details
Bhasi, Vivek M.; Gunasekaran, Jashwant Raj; Thinakaran, Prashanth; Mishra, Cyan Subhra; Kandemir, Mahmut Taylan; Das, Chita. 2021. *Kraken: Adaptive Container Provisioning for Deploying Dynamic DAGs in Serverless Platforms*. ACM Symposium on Cloud Computing (SoCC '21), pp. 153-167. DOI 10.1145/3472883.3486992.

> [!warning] Provenance: based on the **NSF public-access manuscript** (par.nsf.gov), not the final ACM typeset version.
> The extract carries the printed page numbers 153-167 of the SoCC version; wording and numbers may still differ from the final text. The user approved ingesting the open-access copy (2026-10-22). Re-ingest the original when acquired.

## Section map

| Covered | Section | pp. |
|---|---|---|
| ✓ F1 | 1 Introduction (two inefficiencies, PWS, RS, batching) | 153-154 |
| ✓ F1 | 2 Background: static and dynamic DAGs, related-work table, two challenges | 154-156 |
| ✓ F1 | 3 Function probability estimation (Markov model, NC formula) | 156-158 |
| ✓ F1 | 4.1 Proactive Weighted Scaler (probability, Connectivity, Commonality, Alg. 1) | 158-159 |
| ✓ F1 | 4.2-4.3 Request batching and Reactive Scaler (Alg. 2) | 159-160 |
| ✓ F1 | 5 Implementation (OpenFaaS), methodology, simulator | 160-161 |
| ✓ F1 | 6 Results: real system and simulation, sensitivity (Oracle, sparse load, SLO) | 161-165 |
| ✓ F1 | 7 Concluding remarks | 165 |

## Kernthesen

### 1. ⭐ Platforms assume static DAGs and spawn containers for all functions in proportion to the application load, which over-provisions dynamic DAGs (p. 154)
Dynamic branch points make the invoked subset of functions depend on the request. Xanadu provisions along the single most likely path and under-provisions functions when requests deviate; the paper wants containers for every possible path in proportion to a weight.

### 2. ⭐ A function's weight starts from its invocation probability, estimated with a Markov model over the DAG (Sec. 3, pp. 156-157)
The DAG becomes a transition matrix T; the probability vector at depth d is P_d = T^d x P_0, and the containers needed at depth d are NC = ceil(PL x (T^d x P_0)), with PL the predicted load. A variable-order Markov model splits context-dependent states when the path depends on predecessors (Media Service).

### 3. ⭐ Two DAG-structure parameters raise the weight of important functions: Connectivity (descendants / all functions) and Commonality (share of unique paths containing the function) (pp. 158-159)
In Algorithm 1: required = ceil(load x probability); extra = ceil((Comm + Conn) x required); required += extra. Both parameters are capped to limit over-provisioning. Ablations "Comm Only" and "Conn Only" are weaker at the tail, especially when the SLO is tightened (p. 165).

### 4. Cold-start spillover: under-provisioning a critical function hurts end-to-end latency more than under-provisioning a leaf, because queues trickle down to its descendants (p. 156)
On average, end-to-end response time and SLO compliance were 24 ms and 0.25% worse (Fig. 3). This is the reason for the Connectivity weight.

### 5. ⭐ The Proactive Weighted Scaler predicts load with an EWMA over a window PW chosen as the time needed to scale all functions, then converts it to containers per function (Alg. 1, p. 159)
Containers are provisioned in advance so end users do not see cold starts; the number actually spawned is divided by the batch size and kept at or above a minimum.

### 6. ⭐ Request batching: BatchSize(f) = floor(StageSLO(f) / ExecTime(f)), with the stage SLO allotted in proportion to execution time and requests packed like first-fit bin packing (pp. 159-160)
This is Fifer's slack idea with the batch size defined per function; it reduces containers by the batch factor.

### 7. ⭐ The Reactive Scaler spawns containers for requests whose queue wait exceeds the cold start, and a Function Idler removes excess containers gradually (Alg. 2, p. 160)
extra containers = ceil(#delayed requests / batch size). "requests that have to wait longer than the cold start would be served faster at a newly created container than by waiting at an overloaded container." It corrects mispredictions of the proactive path.

### 8. Implementation on OpenFaaS and Kubernetes: the default alert manager is disabled, Prometheus supplies metrics, and the DAG is given by a developer-written descriptor (p. 160)
A one-time DAG descriptor stays manual; automatic offline DAG profiling is left as future work. The simulator mimics an 11,000-core cluster (70x the real system, p. 161).

### 9. Evaluation set-up: five 32-core nodes, DeathStarBench Social Network, Media Service and Hotel Reservation, Wiki and Twitter traces of about an hour, SLO 1000 ms (p. 161)
Function run times are emulated by sleeps; transition probabilities vary about 20% around a seed and are hidden from Kraken. Baselines: Arch (Archipelago), Fifer, Xanadu, plus SProb and DProb (probabilities without Commonality and Connectivity).

### 10. ⭐ Results: Arch, Fifer and Xanadu spawn 2.41x, 76% and 30% more containers than Kraken; up to 76% fewer containers, 4x utilisation, 48% less energy, 99.97% of requests within the SLO (pp. 153-154, 161)
Fifer batches but ignores workflow activation patterns; Xanadu is workflow-aware but does not batch, and 34% of its containers come from reactive scaling after path mispredictions (p. 161).

### 11. Against a clairvoyant Oracle, Kraken spawns about 7% more containers (10% on Media Service) and lags the trace because of prediction error (p. 164)
The gap is attributed to load and path probability errors and to the extra weight from Commonality and Connectivity. This is a rare oracle bound for a provisioning policy.

### 12. ⭐ Limits: cloud cluster with containers added freely, mean-based execution times from sleep emulation, sparse-load case needs a modified policy (pp. 164-165)
Under tight SLOs (500, 910, 809 ms) Kraken keeps at least 99.5% compliance and spawns 50%, 34% and 15% fewer containers than Arch, Fifer and Xanadu (p. 165). No edge nodes, no placement choice, no migration cost, no capacity limit.

## Figures and tables
Table 1 feature comparison (p. 155); Table 2 workflow variability (p. 155); Fig. 1 DAGs (p. 156); Fig. 2 containers per function by policy (p. 156); Fig. 3 critical-function underprovisioning (p. 156); Fig. 5 transition matrix (p. 157); Fig. 6 architecture (p. 158); Fig. 7 slack per function (p. 160); Alg. 1 and 2 (pp. 159-160); Fig. 8-16 results (pp. 161-164); Table 7 varying SLO (p. 165).

## What this source does not address
Static chains and simple per-stage queues are Fifer's setting ([[gunasekaran-2020-fifer]]); Kraken does not consider an edge cluster, a fixed total of container slots, placement by data affinity, data-transfer or migration cost, nor a limit on how many containers change per round. No re-layout of an existing placement; no comparison with simulation-judged or search-based placement such as DFPS.

## Focus: prior art for backlog-driven per-function container sizing at the edge (busiest-first rule, fixed capacity, churn) — 2026-10-22

**Carries Kernthesen 2, 3, 5, 6, 7, 10, 11, 12.**

### What this focus needs beyond the Kernthesen
1. For workflows with fan-out and branches, a per-function weight (probability, Connectivity, Commonality) is the closest published analogue to how our rule splits slots between functions; our rule uses measured load and backlog instead of path probabilities, and workflows in our test set are mostly static DAGs.
2. The reactive scaler's cold-start test ("wait longer than a cold start") is a per-request cost-benefit check on spawning; a churn cap or break-even rule for whole-layout changes is the layout-level counterpart.
3. The Oracle comparison (about 7% above a clairvoyant policy) is a template for reporting the headroom left above a practical provisioning policy.

### Direct quotes (for the draft)
> "requests that have to wait longer than the cold start would be served faster at a newly created container than by waiting at an overloaded container" (p. 160)

> "Kraken spawns up to 76% fewer containers" (p. 153, abstract)

### Examples & illustrations (for later drafting)
- Fig. 2: containers per function for static provisioning, probability-based scaling and Xanadu on Social Network, Media Service and Hotel Reservation; Xanadu over-provisions by 32% under moderate and heavy load (pp. 155-156).
- Transition matrix of the Social Network DAG (11 functions, 7 paths), Fig. 5 (p. 157).

### Boundary of this focus
Evidence concerns how many containers a function should get and when to spawn more; it says nothing about where containers go on a multi-node edge cluster or what a re-layout costs.

## Mentioned entities
- Concepts: [[backlog-driven-container-sizing]], [[dynamic-dag-workflow]], [[cold-start]]
- Benchmarks: [[deathstar-benchmark]]

## Connections
- Builds on [[gunasekaran-2020-fifer]] (slack batching) and contradicts the most-likely-path provisioning of [[daw-2020-xanadu]]. Typed in `relations:`.
- Named by [[mahgoub-2022-orion]] as work on cascading cold starts in dynamic DAGs that cannot determine the optimal pre-warming time.
