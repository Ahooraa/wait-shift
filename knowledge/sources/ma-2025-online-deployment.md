---
title: "Ma et al. 2025 — Online Deployment of Dynamic Edge DAG Serverless Functions Toward Fast Startup (EBRO, OPTS)"
type: source
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
bibkey: ma-2025-online-deployment
depth: standard
tags: [serverless-edge, dynamic-dag, prewarming, cold-start, novelty-gate-g0, baseline]
relations:
  - target: ebro
    type: mentions
    confidence: extracted
    because: "Offline pre-warm/deployment algorithm EBRO (Alg. 1, p. 5)."
  - target: opts
    type: mentions
    confidence: extracted
    because: "Online algorithm OPTS (Alg. 2, p. 6)."
  - target: function-calling-probability-prewarming
    type: builds-on
    confidence: extracted
    because: "Pre-warm iff EWMA calling probability >= P_pre (Eq. 1-2, p. 4)."
  - target: randomized-rounding
    type: builds-on
    confidence: extracted
    because: "EBRO relaxes to [0,1] and rounds randomly until feasible (Alg. 1, p. 5)."
  - target: cold-start
    type: mentions
    confidence: extracted
    because: "Cold-start time is the quantity minimised (abstract, p. 1)."
  - target: learning-augmented-online-algorithms
    type: contradicts
    confidence: inferred
    because: "Calls its OPTS result a competitive ratio (p. 2) but the ratio (Theorem 2, p. 7) has no prediction-error term, unlike learning-augmented guarantees."
---

# Online Deployment of Dynamic Edge DAG Serverless Functions toward Fast Startup

## Bibliographic Details
Ma, Yue; Liu, Wentao; Zhou, Ruiting; Tian, Haodong; Dong, Fang; Zeng, Yifan. 2025. *Online Deployment of Dynamic Edge DAG Serverless Functions Toward Fast Startup*. 2025 IEEE/ACM 33rd International Symposium on Quality of Service (IWQoS), pp. 1-10. https://doi.org/10.1109/IWQoS65803.2025.11143376. Page numbers below are the 10 printed pages. A technical report with the missing proofs is cited as [28] (p. 5) and was not read.

## Section map

| Covered | Section | pp. |
|---|---|---|
| — | I. Introduction (dynamic vs static DAG, challenges, contributions) | 1-2 |
| ✓ F1 | II. Related work (deployment; DAG scheduling) | 2-3 |
| ✓ F1 | III.A System overview, dynamic DAG, decision variables | 3 |
| ✓ F1 | III.B Pre-warm preparation (EWMA, threshold) | 4 |
| ✓ F1 | III.C-D Deployment model, problem (6) | 4 |
| ✓ F1 | IV. EBRO offline algorithm and Theorem 1 | 5-6 |
| ✓ F1 | V. OPTS: weights, slice-wise pre-warm adjustment, scheduling, Theorem 2 | 6-7 |
| ✓ F1 | VI.A Settings, baselines | 7 |
| ✓ F1 | VI.B-C Offline and online results | 7-9 |
| — | VII Conclusion | 9 |
| ✓ F1 | Appendix: proofs of Lemma 4, Thm 1, Lemma 6, Thm 2 | 9-10 |

## Kernthesen

### 1. ⭐ Dynamic DAGs break "pre-warm everything" (pp. 1-2)
Requests in a dynamic DAG run one path and trigger only a subset of functions, so warming all containers over-provisions, while a fixed pre-warm plan is ineffective when calling probabilities change. Static-DAG work is said to be unable to handle this (p. 2).

### 2. ⭐ The model: functions carry calling probabilities, paths carry products (pp. 3-4)
Ordinary functions have probability 1, dynamic ones lie in (0,1); path probability p_k is the product along the path. Resources are storage only (footnote 1, p. 3). Decision variables: x (cold or warm) and z (function-on-path to server).

### 3. ⭐ Prediction is a historical frequency with EWMA and a threshold (p. 4)
P_hist = N/T_o, min-max normalised, smoothed by EWMA (Eq. 1); a function is pre-warmed iff the estimate is at least P_pre (Eq. 2), independent of the server. P_pre is not learned but chosen from tests.

### 4. ⭐ Objective: probability-weighted mean path execution time (pp. 4-5)
Problem (6) minimises the sum over paths of p_k times path time, with constraints on demand probability (6a), per-server storage (6b) and precedence (6c-d). It is a quadratic integer program, called NP-hard (p. 4).

### 5. ⭐ EBRO: linearise, relax, round randomly until feasible (p. 5)
Fix x from the threshold, relax z to [0,1], solve with Gurobi, round with probability equal to the fractional value, repeat until feasible (Alg. 1).

### 6. ⭐⭐ Theorem 1: offline upper bound with high likelihood (pp. 5-6, 9)
M_alg <= (n/(2 delta1) + 2 + (nl-1) delta2/2) M_opt "with a high likelihood" (p. 6). Lemmas 1-3 give feasibility, precedence and storage "in expectation"; Lemmas 4-5 use a Chernoff bound (p. 9). The bound grows with function count n and server count l.

### 7. EBRO handles one request only (p. 6)
The text states EBRO "can only schedule a single request at a time", which motivates OPTS.

### 8. ⭐ OPTS: weight-ranked heads of per-request lists, earliest-start server (pp. 6-7)
Weight of f_v is the path-probability-weighted time over paths containing it (p. 6). Alg. 2 picks the highest-weight head and places it on the server with minimum earliest start time (Eq. 10-14).

### 9. ⭐ Pre-warm adjustment per time slice (p. 6)
Phase 1, before each slice: warm containers from EBRO's x. Phase 2, within the slice: new warm containers y_{v,i} appear when the earliest-start rule picks a "pre-warmed or cold-started" path (Eq. 12-13); remaining memory follows Eq. 9; q resets at slice end. Slice length and any eviction are not specified.

### 10. ⭐⭐ Theorem 2: ratio l/l' + 8/5, under equal memory and equal link rates (pp. 7, 10)
Lemma 6 bounds EBRO-placed completion by 8/5 of optimal assuming t_exe >= c*d and infinite servers (pp. 9-10); Lemmas 7-8 bound idle time; l' is the number of servers with pre-warmed f_v (p. 7).

### 11. Evaluation: SocialNetwork on six servers (p. 7)
DeathStar SocialNetwork in three sizes (11/15/18 functions; 7/14/21 paths), Kubernetes + OpenFaaS, 6 servers with 0.5-3 GB, 10 Gbps. Inputs are measured historical times and probabilities.

### 12. Reported gains (pp. 8-9)
Offline: up to 78.4% / 88.5% (request time / cold start) vs HEFT, DPE, Gendoc. Online: 25.2% (FCFS) and 21.6% (Fixed) makespan; cold-start time down 80.1% and 76.9%. P_pre about 0.3 is best (p. 8).

## Figures and tables
Figs. 2-14 (pp. 8-9): warm/cold delay, execution time, cold-start rate vs requests, servers, threshold, path count; makespan and cold start for OPTS. No tables.

## What this source does not address
No forecast-error analysis or distribution drift test; no tail latency, SLO or cost; no overload, rejection or admission; no data on arrival process; no relocation or eviction of containers. Keep-alive and pre-warm timing literature is [[shahrad-2020-serverless-wild]] and [[icebreaker]]; learning-augmented guarantees are in [[purohit-2018-online-algorithms-predictions]].

## Focus: prediction and pre-deployment as baseline design (plan Task 3) — 2026-10-13

**Carries Kernthesen 3, 5, 6, 8, 9, 10, 11, 12.**

### What this focus needs beyond the Kernthesen
- **Trigger for (re)deployment:** two triggers only. (i) Beginning of each fixed time slice: warm containers from EBRO's x and recompute with the P_pre rule (p. 6). (ii) At dispatch: if the earliest-start server lacks a ready container, a new one is pre-warmed on the spot (y_{v,i}, Eq. 12-13, p. 7). No load-, queue- or cost-based trigger; no re-optimisation of placement when probabilities shift mid-slice. Eviction is not described.
- **Guarantees:** Theorem 1 (p. 6, proofs pp. 9-10) offline, probabilistic; Theorem 2 (p. 7, proof p. 10) "approximation ratio" l/l' + 8/5, called "competitive ratio" (p. 2). Neither includes prediction error: x and rho are treated as given at solve time, and the proof of Lemma 6 uses the LP relaxation and the assumption t_exe >= c*d. Theorem 2 needs equal memory (R(m_i)=R(m_j)) and equal transmission rate (p. 7). Inferred: since l >= l', the ratio is at least 2.6, so the guarantee is weak in absolute terms; the definition of l' as a sum of x over functions (p. 7) looks inconsistent with its use as a server count, not checked against the technical report.
- **Assumptions:** historical frequency is a usable stand-in for rho; path probability is the product of rho (independence, p. 3); t_exe, t_cold, r_{v,i}, c_{i,j} known; storage as the only resource; central knowledge of server state.
- **Workload:** SocialNetwork only, 20-80 requests offline (p. 7); online "different numbers of requests within a short time frame" (p. 8); arrival process, burstiness and probability drift are not reported although changing calling probabilities motivate the paper (p. 1).
- **Baselines / metrics:** offline HEFT, DPE [6], Gendoc [30]; online FCFS [31] and "Fixed" (OPTS with fixed pre-warm count) (p. 7). Metrics: mean request execution time, cold-start time and rate, makespan; no P95/P99, SLO or goodput, no decision latency of Gurobi/EBRO.
- **Overload / admission:** none. Memory (6b, Eq. 9) caps pre-warming only; surplus requests queue (pp. 5-6).
- **Relation to DFPS (Zolfaghari 2025):** not cited. DFPS assumes warm slots always exist and all functions are used; this paper models conditional paths and cold start, so it is a predictive pre-deployment baseline that DFPS lacks, but it provides no replacement or relocation of running instances.

### Direct quotes (for the draft)
> "can only schedule a single request at a time" (p. 6, on EBRO)

> "Rigorous algorithmic proofs ensure an upper bound for EBRO." (p. 2)

> "independent of any specific edge server" (p. 4, on the pre-warm decision)

### Examples & illustrations (for later drafting)
- Social media post: like, comment or share trigger different sub-paths (p. 1).
- SocialNetwork DAG sizes 11/18 functions and 7/21 paths (p. 7).

### Boundary of this focus
Does not give a robustness or consistency result against forecast error; use [[purohit-2018-online-algorithms-predictions]] for that class of result.

## Mentioned entities
- Methods: [[ebro]], [[opts]]
- Concepts: [[function-calling-probability-prewarming]], [[randomized-rounding]], [[cold-start]], [[learning-augmented-online-algorithms]]

## Connections
- Builds on: [[function-calling-probability-prewarming]], [[randomized-rounding]].
- Contrasts with the learning-augmented guarantee class: [[learning-augmented-online-algorithms]] (inferred).
- Neighbouring pre-warm literature: [[shahrad-2020-serverless-wild]], [[icebreaker]].
