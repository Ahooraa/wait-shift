---
title: "Liu, Zhou and Ma 2025 — Sdser: Online Deployment and Scheduling of Dynamic DAG Functions with Bayesian Prediction in Serverless Edge Computing"
type: source
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
bibkey: liu-2025-sdser
depth: standard
tags: [serverless, edge, dynamic-dag, bayesian-prediction, pre-deployment, cold-start, baseline-design]
relations:
  - target: sdser
    type: mentions
    confidence: extracted
    because: "Proposes the Sdser framework (abstract, p. 890)."
  - target: bayesian-hop-prediction
    type: builds-on
    confidence: extracted
    because: "Dirichlet prior over multinomial hop probabilities, posterior update per slot (Eq. 19-23, p. 894)."
  - target: dynamic-dag-workflow
    type: builds-on
    confidence: extracted
    because: "Decomposes dynamic-DAG paths into single-hop requests (Sect. II-A, pp. 891-892)."
  - target: predictive-pre-deployment
    type: builds-on
    confidence: extracted
    because: "PPS pre-deploys containers from expected requests each slot (Alg. 1, p. 894)."
  - target: cold-start
    type: mentions
    confidence: extracted
    because: "Cold start enters execution time as (1-y)*tau_cold (Eq. 2, p. 892)."
  - target: ski-rental
    type: cites
    confidence: extracted
    because: "Related work cites Pan et al. mapping container caching to ski rental (p. 898); Sdser itself does not use it."
  - target: deathstar-benchmark
    type: cites
    confidence: extracted
    because: "Empirical durations, cold starts and memory measured on DeathStar (Sect. IV-A, p. 896)."
  - target: tian-2024-sfsm
    type: supports
    confidence: inferred
    because: "Same edge DAG-scheduling problem family, but SFSM uses no forecasts and static DAGs; not cited by this source."
---

# Sdser: Online Deployment and Scheduling of Dynamic DAG Functions with Bayesian Prediction in Serverless Edge Computing

## Bibliographic Details
Liu, Wentao; Zhou, Ruiting; Ma, Yue. 2025. *Sdser: Online Deployment and Scheduling of Dynamic DAG Functions with Bayesian Prediction in Serverless Edge Computing*. 2025 IEEE 45th International Conference on Distributed Computing Systems (ICDCS): 890-900. https://doi.org/10.1109/ICDCS63083.2025.00091. Page numbers below are the printed pages 890-900 (PDF pages 1-11; PDF page 11 is references).

## Section map

| Covered | Section | pp. |
|---|---|---|
| ✓ F1 | I. Introduction (dynamic DAG challenges, contributions) | 890-891 |
| ✓ F1 | II-A. System overview, DAG structure, request definition (hop triple), decision variables | 891-892 |
| ✓ F1 | II-B. Transmission time, execution time, constraints, deployment cost | 892-893 |
| ✓ F1 | II-C. Problem formulation (quadratic integer program, NP-hard) | 893 |
| ✓ F1 | III-A/B. Main idea; linearisation (aux variables mu, eta) | 893 |
| ✓ F1 | III-C. Real-time function prediction (Dirichlet-multinomial) | 894 |
| ✓ F1 | III-D. PPS algorithm, randomized rounding (Alg. 1, 2) | 894-895 |
| — | III-E. Theoretical analysis (Lemmas 1-4, Theorem 1) | 895 |
| ✓ F1 | III-F. Mosa (Alg. 3, objective 24) | 895-896 |
| ✓ F1 | IV-A. Experiment setup (DeathStar, 15 servers, baselines) | 896 |
| ✓ F1 | IV-B. Results: overall, cold start, constraints, ablation | 896-898 |
| ✓ F1 | V. Related work | 898 |
| ✓ F1 | VI. Conclusion | 898 |
| — | Appendix A-E (proofs of Lemmas 1-4, Theorem 1) | 898-899 |

## Kernthesen

### 1. ⭐⭐ A dynamic DAG is modelled as a stream of single-hop "requests" (pp. 890-892)
Path randomness makes whole-path decisions coarse, so each hop becomes a request triple r = (server of completed function, completed function f_a, next function f_b). The first request uses a virtual server s0 and virtual function f0 with zero data (p. 892). Prediction and scheduling therefore operate per hop, not per path.

### 2. ⭐⭐ Joint deployment and scheduling is a quadratic integer program (pp. 892-893)
Per request, x (which server executes f_b) and y (which server gets a pre-deployed container, at most one, only where x=1; Eq. 3-5). Execution time is [(1-y)*tau_cold + d_b/v_q]*x (Eq. 2). Constraints: compute capacity (Eq. 6) and memory for pre-deployed containers (Eq. 7). Objective (10): execution plus transmission time plus alpha times deployment cost. Declared NP-hard (p. 893).

### 3. ⭐ Deployment cost counts only containers new in this slot (p. 893)
L(t) = sum over servers and functions of g_k * max[(#containers requested) - phi_{q,k}(t), 0], where phi is the number deployed in the previous slot (Eq. 8-9). Containers kept from the last slot are free; this is the only memory of past slots in the optimisation.

### 4. ⭐ Linearisation by auxiliary variables (p. 893)
mu = x*y (Eq. 11-13) and eta replacing max() (Eq. 14-17) give a linear program (18) solved by a general LP solver such as Gurobi (p. 894).

### 5. ⭐⭐ Bayesian hop prediction (p. 894)
Successor of f_k ~ multinomial with Dirichlet prior, beta initialised to 1 (unbiased prior); after each slot beta_{k,l} += observed hop count (Eq. 20-22). The initial function f0 is assumed Poisson, estimated from history. Predicted f_b is sampled (not argmax) from Multi(Theta) (Eq. 23). Claimed benefit: sampling randomness dampens anomalous traffic (p. 894). See [[bayesian-hop-prediction]].

### 6. ⭐⭐ PPS: predict, solve relaxed LP, round, pre-deploy (pp. 894-895)
Per slot: collect executing f_a requests, add new ones from the f0 flow estimate, predict f_b, solve the single-slot LP, round randomly (Alg. 2, independent Bernoulli draws with the LP values, repeated until constraints hold), deploy containers where y-hat=1, then observe real requests and update the posterior (Alg. 1, p. 894). No multi-slot look-ahead: "virtually no offline algorithm" can optimise all future slots (p. 894).

### 7. Approximation guarantee 7/2 Upsilon (p. 895)
With high probability the rounded solution is feasible (Lemma 1) and its objective is at most (7/2 + ln|R|/(2E[Q']) + sqrt(|R||S| ln|R|/2)/E[H]) times the optimum, converging to 7/2 as |R| grows (Theorem 1). The bound concerns the rounding step relative to the LP of the predicted requests, not forecast error.

### 8. ⭐⭐ Mosa: three-priority online correction (pp. 895-896)
Priority 1: a real request whose f_b equals the predicted one is scheduled by the preliminary solution. Priority 2: unmatched requests are assigned to residual pre-deployed containers (sorted by cold-start time, then server spare compute), choosing the request with minimum transmission time. Priority 3: remaining requests (all cold) are placed by re-solving objective (24) with y, mu, eta fixed (x only), via Alg. 2 or ILP when small. This is the only forecast-error handling.

### 9. ⭐ Evaluation: DeathStar measurements, 15 servers, three baselines (p. 896)
Durations, cold starts and memory measured with wrk and Jaeger on DeathStar; Poisson arrivals; 15 servers with 30 cores and 500 MB each, 5-15 GFLOPs, 0.5-1.5 MB/s links. Baselines OLC, GSP, Gendoc. High load lambda=300, medium lambda=200.

### 10. ⭐ Headline results and ablation (pp. 890, 896-898)
Up to 27.05% lower total overhead and 31.36% lower cold-start rate (abstract). Removing prediction raises cold-start time and rate most; removing Mosa raises computation time (Fig. 10-11, pp. 897-898). Sdser stays steady when compute is scarce; GSP suffers when memory is small (p. 897).

### 11. Related-work positioning (p. 898)
Path-level predictors (Kraken, Xanadu) ignore function-level hop frequency; cloud-oriented methods do not transfer to edge where servers share no container pool and communication cost matters. Static-DAG edge methods over-provision for every path.

## Figures and tables
Fig. 1 system overview (p. 892); Table I notation (p. 892); Fig. 2-3 overall overhead and cold start (p. 896); Fig. 4-9 sensitivity to compute, memory and alpha (p. 897); Fig. 10-11 ablation (pp. 897-898).

## What this source does not address
No heavy-tailed or bursty arrivals (Poisson only); no test of non-stationary hop probabilities; no confidence bound on forecast error; no scale-to-zero or idle-cost dynamics beyond the per-slot deployment cost; no queueing at servers; no fan-out or parallel branches (the hop model is sequential); no controller-overhead or LP solve-time report; slot length is not stated in the text. Workflow-level makespan is absent because requests are scored individually. Whole-workflow placement on edge nodes is treated in [[tian-2024-sfsm]] and by DFPS itself.

## Focus: Prediction and pre-deployment as baseline design — 2026-10-13

Focus string: prediction and pre-deployment as baseline design: what Bayesian prediction predicts, when containers are pre-deployed, scheduling rule for dynamic DAGs, workloads/baselines/metrics, forecast-error handling, and what an Sdser-style controller needs (plan Task 3/17).

**Carries Kernthesen 1, 2, 3, 5, 6, 8, 9, 10.**

### What this focus needs beyond the Kernthesen
1. **What is predicted:** only the next function f_b given the executing function f_a (a categorical successor distribution per function), plus the count of new initial requests from f0 (Poisson flow estimate). It does not predict arrival times, durations or data sizes (pp. 892-894).
2. **When pre-deployment happens:** once per time slot t, before the slot's real requests arrive (Alg. 1, lines 10-13, p. 894). It is periodic by slot, with prediction input drawn from requests currently executing f_a ("when f_a is executing", p. 894). The slot length is not given in the text.
3. **Scheduling rule:** three-priority Mosa (Kernthese 8). Priority 1 uses the preliminary x from LP rounding; priority 2 is greedy by minimum transmission time on leftover containers; priority 3 minimises tau_cold + d/(c v) + transmission (Eq. 24, p. 896). Per request, not per DAG; no critical-path or makespan reasoning.
4. **Metrics:** total overhead (execution = cold start + calculation, transmission, alpha-weighted deployment cost), average cold-start time, cold-start rate (pp. 896-897). No tail latency, SLO or throughput.
5. **Forecast-error and overload handling:** forecast error is repaired only by Mosa (reuse residual containers, then cold start). There is no forecast-uncertainty bound, no admission control and no explicit overload rule. Constraint (6) caps compute per server, but the text does not say what happens if no feasible x exists; under high load the memory limit is reached and average deployment cost per request falls (p. 896).
6. **To implement an Sdser-style controller you need:** (a) DAG successor sets and per-function d_k, c_k, m_k, g_k, tau_cold_k; (b) per-server C_q, M_q, v_q and pairwise rates u; (c) a hop counter per (f_k, f_l) holding Dirichlet state beta; (d) an arrival-rate estimator for f0; (e) an LP solver (Gurobi in the paper, p. 894) for the relaxed problem (18); (f) randomized rounding with feasibility retry; (g) previous-slot container counts phi; (h) the Mosa three-stage dispatcher. Left open and to be chosen by the implementer: slot length, how many predicted requests to sample per f_a, retry cap in Alg. 2, solver settings, and container eviction (the paper only counts new deployments).

### Direct quotes (for the draft)
> "we decompose the dynamic DAG paths into individual function hops, modeling each hop as a request triple." (p. 890)

> "Bayesian estimation imparts certain randomness during the generation of hop probabilities, mitigating the effect of anomalous traffic data." (p. 894)

> "there is virtually no offline algorithm capable of predicting and optimizing requests for all future time slots." (p. 894)

### Examples & illustrations (for later drafting)
- Social-network microservice: after MAKE POST the call may go to URL SHORTENER, USER TAG, MEDIA or TEXT; invocation frequency varies by up to 70% (p. 890).
- Ablation: Sdser w/o pred has the highest cold-start time and rate; Sdser w/o adjust has higher computation time (pp. 897-898).

### Boundary of this focus
Sdser is a per-hop predictive pre-deployment baseline for stationary-probability dynamic DAGs. It says nothing about workflow-level makespan, heavy-tailed workloads, admission control or forecast guarantees, which matter for a comparison with DFPS.

## Mentioned entities
- Methods: [[sdser]], [[sfsm]]
- Concepts: [[bayesian-hop-prediction]], [[dynamic-dag-workflow]], [[predictive-pre-deployment]], [[cold-start]], [[ski-rental]]
- Benchmarks: [[deathstar-benchmark]]

## Connections
- Cites: [[ski-rental]] (related work only, p. 898).
- Builds on: [[bayesian-hop-prediction]], [[dynamic-dag-workflow]], [[predictive-pre-deployment]].
- Same edge DAG-scheduling family: [[tian-2024-sfsm]] (no forecasts, Lyapunov, static DAGs).
