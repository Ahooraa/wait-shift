---
title: "Deng et al. 2022 — Dependent Function Embedding for Distributed Serverless Edge Computing"
type: source
created: 2026-10-20
updated: 2026-10-20
status: review
author: llm
bibkey: deng-2022-dependent-function-embedding
depth: standard
tags: [serverless, edge, dag, function-placement, makespan, dynamic-programming, offline, alibaba-trace, g0-novelty, related-work]
relations:
  - target: alibaba-cluster-trace
    type: mentions
    confidence: extracted
    because: "Evaluation samples 2119 DAGs from the Alibaba cluster trace and scales their demands (Sec. 5.1, pp. 2353-2354)."
  - target: dfps
    type: supplements
    confidence: inferred
    because: "Same problem family (DAG placement on heterogeneous edge servers to minimise completion time) solved offline for one DAG; DFPS is online and load-aware. Not stated in this source."
  - target: migration-minimizing-placement
    type: mentions
    confidence: inferred
    because: "A static optimal placement baseline; no migration or re-placement is modelled."
---

# Dependent Function Embedding for Distributed Serverless Edge Computing

## Bibliographic Details
Deng, Shuiguang; Zhao, Hailiang; Xiang, Zhengzhe; Zhang, Cheng; Jiang, Rong; Li, Ying; Yin, Jianwei; Dustdar, Schahram; Zomaya, Albert Y. 2022. *Dependent Function Embedding for Distributed Serverless Edge Computing*. IEEE Transactions on Parallel and Distributed Systems 33(10), pp. 2346-2357. DOI 10.1109/TPDS.2021.3137380.

> Page note: printed pages 2346-2357; a page-number marker in the extraction closes the page it follows, and refs below follow that rule.

## Section map

| Covered | Section | pp. |
|---|---|---|
| ✓ F1 | 1 Introduction (motivating examples, Fig. 1-2, contributions) | 2346-2347 |
| ✓ F1 | 2 Working example (surveillance video, KubeEdge) | 2348 |
| ✓ F1 | 3 System model (graph of servers and links, DAG, finish-time recursion, Eq. 1-3) | 2348-2349 |
| ✓ F1 | 4 Algorithm design: optimal substructure, OSM (Alg. 1), DPE (Alg. 2), complexity, path finding (Alg. 3), multiple DAGs | 2349-2353 |
| ✓ F1 | 5 Experiments (Alibaba trace; FixDoc, HEFT) | 2353-2355 |
| ✓ F1 | 6-7 Related work and conclusion | 2355-2356 |

## Kernthesen

### 1. ⭐ Optimising function placement alone leaves makespan on the table: how the data of each edge is routed over the links between edge servers also matters (pp. 2346-2347)
Fig. 1: the placement with the lower processing time is not the one with the lower makespan.

### 2. ⭐ Splitting one output stream over several network paths lowers makespan further (p. 2347)
The worked example gives 7.5 with splitting, 4.5 lower than without (Fig. 2).

### 3. "Function embedding" means placement of each function plus mapping of each data stream to paths (p. 2347)

### 4. The model: undirected connected graph of heterogeneous servers (power c_n) and virtual links (bandwidth b_max), a DAG with flop counts c_i and data sizes s_ij; computation is non-preemptive and can overlap communication (Sec. 3, p. 2348)
Intra-server transfer time is zero.

### 5. ⭐ Finish time of a function is the larger of its server's earliest idle time and the latest predecessor finish plus transfer, plus its own processing time (Eq. 1-3, p. 2349)
Transfer time = start-up cost + the slowest path among the split parts; bandwidth per stream is fixed and guaranteed (network-slice assumption); splitting and merging cost is ignored.

### 6. ⭐ The problem has an optimal substructure: given the earliest finish time of each predecessor, the best placement and data split of one dependent pair is a sub-problem, solved step by step (Sec. 4.1, Eq. 7, p. 2349)
Placement and stream mapping cannot be optimised at the same time but can be optimised in sequence.

### 7. ⭐ Each sub-problem reduces to infinity-norm minimisations with analytical solutions; Algorithm 1 (OSM) computes the optimal split, Algorithm 2 (DPE) is the dynamic programme (Sec. 4.2-4.3, pp. 2350-2351)
Optimality is "for an arbitrary DAG when the topological order of functions is given" (p. 2356).

### 8. Complexity of DPE is O(|N| · |E| · max(|N|, max |P_ij|)) in the worst case (Theorem 2, p. 2351)
Simple-path enumeration for all server pairs is NP-hard (Proposition 1) and done once after the cluster is created, with local updates when the topology changes (Sec. 4.4, p. 2352).

### 9. Several DAGs are handled by concatenating them with dummy head and tail functions into one augmented DAG (Sec. 4.5, p. 2353)
So multiple requests are scheduled in one offline batch, not as an arriving stream.

### 10. ⭐ Setup: 2119 DAGs sampled from the Alibaba cluster trace (20,365 unique DAGs, over 3 million jobs), demands scaled to 1-1000 gflops and 5-1500 MB; 10 edge servers by default with 20-40 gflops and 3000-8000 MB/s (Sec. 5.1, pp. 2353-2354)

### 11. ⭐ DPE reduces average completion time by 43.19% against FixDoc and 40.71% against HEFT, and beats both on 100% of the DAGs (Sec. 5.2.1, p. 2354)
Maximum DPE completion time is 124 s; fewer than 94% of the baselines' completion times stay below it.

### 12. ⭐ Gains grow with the number of servers and the number of simple paths; the algorithm's run time is the lowest of the three (Fig. 9-10, p. 2354)
Stated limits: the algorithm is offline; online scenarios are future work (p. 2356). Not modelled: queueing of concurrent requests, container start-up (functions are assumed pre-installed, p. 2354), changing network status (bandwidth fixed by QoS).

## Figures and tables
Fig. 1-2 motivating examples (p. 2347); Fig. 3 surveillance pipeline; Table 1 notation (p. 2348); Fig. 4 data splitting (p. 2349); Fig. 5 DPE example (p. 2351); Fig. 6-12 evaluation (pp. 2354-2355).

## What this source does not address
No arrival process, no request stream, no queueing across concurrent requests (the offline batch model only), no cold starts or container lifecycle, no re-placement over time, no forecast, no admission control, no learning baseline and no comparison with DFPS (a 2025 paper). The optimality claim is for the model, not for a running system.

## Focus: prior art for look-ahead, simulation-judged and regime-aware container re-planning of serverless workflows at the edge (D1-D3) — 2026-10-20

**Carries Kernthesen 4, 5, 6, 9, 10, 11, 12.**

### What this focus needs beyond the Kernthesen
1. Static optimal DAG placement on heterogeneous edge servers: a clean baseline for "what a one-shot placement can reach". Its own reported gain over HEFT (about 41%) is of the same scale as our headroom, but against weaker baselines and with no arrivals.
2. The same Alibaba DAG source as DFPS and our experiments; but DPE scales demands and uses the DAGs in batch.
3. Assumes network status fixed by QoS slices; our setting has load-driven queueing, which is what makes timing of layout changes matter.

### Direct quotes
> "The algorithms proposed in this paper is an offline algorithm. We leave the extension to online scenarios to our future work." (p. 2356, Sec. 7)

> "the optimal placement of functions and optimal mapping of data streams cannot be obtained at the same time. Nevertheless, we can solve it optimally step-by-step based on its optimal substructure" (p. 2349, Sec. 4.1)

### Examples & illustrations
- Fig. 1-2: a three-function chain on six servers where the placement with lower compute time loses on makespan (p. 2347).

### Boundary of this focus
Pre-empts nothing about online re-planning; it states that its own scope is offline. Cite as the static-placement end of the spectrum.

## Mentioned entities
- Datasets: [[alibaba-cluster-trace]]
- Concepts: [[migration-minimizing-placement]]
- Systems: [[dfps]] (related, not cited)

## Connections
- Offline counterpart of the online setting of [[dfps]]; online edge work in this wiki that re-plans over time: [[nguyen-2025-taming]] (single node), [[ray-2020-proactive-placement]] (one mobile user).
