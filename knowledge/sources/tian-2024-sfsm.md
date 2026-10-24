---
title: "Tian et al. 2024 — SFSM: A Serverless Function Scheduling Method for FaaS Applications over Edge Computing"
type: source
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
bibkey: tian-2024-sfsm
depth: standard
tags: [serverless, edge, dag-scheduling, lyapunov, multi-armed-bandit, novelty-gate-g0]
relations:
  - target: sfsm
    type: mentions
    confidence: extracted
    because: "Proposes SFSM (abstract, p. 1015)."
  - target: lyapunov-drift-plus-penalty
    type: builds-on
    confidence: extracted
    because: "Long-term time-average makespan under a cost budget decoupled per slot via a virtual cost queue and drift-plus-penalty (Sect. IV-B, pp. 1018-1019)."
  - target: linucb-contextual-bandit
    type: builds-on
    confidence: extracted
    because: "Scheduling per function via a LinUCB-style contextual combinatorial bandit; regret bound taken from [28] (Sect. IV-D/E, pp. 1020-1022)."
  - target: two-level-data-merging
    type: mentions
    confidence: extracted
    because: "Vertical and horizontal DAG merging, Alg. 2 (Sect. IV-C, pp. 1019-1020)."
  - target: alibaba-cluster-trace
    type: cites
    confidence: extracted
    because: "Alibaba cluster trace v2018, 20,000 sampled applications (Sect. V-A2, p. 1022)."
  - target: cold-start
    type: mentions
    confidence: extracted
    because: "Start-up latency is a model parameter; cold start deferred to future work (pp. 1017, 1024)."
  - target: sun-2026-hybrid
    type: supports
    confidence: inferred
    because: "Same family (Lyapunov per-slot decomposition for serverless edge DAG scheduling, online, no forecasts); not cited by this source, which predates it."
---

# SFSM: A Serverless Function Scheduling Method for FaaS Applications over Edge Computing

## Bibliographic Details
Tian, Hao; Chen, Cheng; Dai, Fei; Dou, Wanchun. 2024. *SFSM: A Serverless Function Scheduling Method for FaaS Applications over Edge Computing*. 2024 IEEE International Conference on Web Services (ICWS): 1015-1024. https://doi.org/10.1109/ICWS62655.2024.00120. Page numbers below are the printed pages 1015-1024 (PDF pages 1-10).

## Section map

| Covered | Section | pp. |
|---|---|---|
| ✓ F1 | I. Introduction (challenges, contributions) | 1015-1016 |
| ✓ F1 | II. Related work (DAG scheduling in heterogeneous edge; serverless function optimisation) | 1016 |
| ✓ F1 | III. Application scenario and problem formulation (edge graph, DAG model, makespan, cost, problem P1) | 1016-1018 |
| ✓ F1 | IV-A/B. Framework; Lyapunov-based problem decomposition (Lemma 1, P2, P3, Alg. 1) | 1018-1019 |
| ✓ F1 | IV-C. Two-level data merging (Alg. 2, Fig. 3) | 1019-1020 |
| ✓ F1 | IV-D. Online MAB-based scheduling (context vector, Alg. 3, Eq. 16-18) | 1020-1021 |
| ✓ F1 | IV-E. Regret analysis (Lemmas 2-3, Theorem 1) | 1021-1022 |
| ✓ F1 | V-A. Experiment settings (simulator, Alibaba trace, baselines) | 1022 |
| ✓ F1 | V-B. Performance analysis (scheduling performance, arrival rate, control parameters V and alpha) | 1022-1024 |
| ✓ F1 | VI. Conclusion and future work | 1024 |

## Kernthesen

### 1. ⭐⭐ The problem is online DAG scheduling over edge nodes with incomplete information (pp. 1015-1016)
The authors argue that dependent-function scheduling on heterogeneous, dynamic edge networks cannot assume complete system-wide information, and that the function-priority orderings used by most DAG schedulers ignore data-communication overlap between functions, producing redundant cross-node transfers (p. 1015). SFSM is the answer for "FaaS applications without complete knowledge of transmission and computing information of edge nodes" (p. 1016).

### 2. ⭐⭐ Objective: long-term time-average makespan under a long-term average cost budget (pp. 1017-1018)
Problem P1 (Eq. 8) minimises the limit of the time-average of summed per-slot makespan O(t) subject to precedence (8a), start-up (8b), a time-average cost constraint with budget C_avg (8c) and per-node capacity (8d, 8e). The authors state that P1 is NP-hard because of the coupled long-term cost constraint (p. 1018), citing [25]. There is no deadline, no SLO and no user-satisfaction term.

### 3. ⭐⭐ System model: discrete slots, per-request DAGs, FCFS non-preemptive nodes, start-up latency as an input (pp. 1016-1017)
Edge nodes form a connected, symmetric-rate graph; each application is a DAG with dummy entry/exit nodes (p. 1016). Time is slotted; at each slot a user requests an application if a condition threshold is met (p. 1017, Eq. 1). Nodes serve functions FCFS, non-preemptively, with parallel execution up to computing power (p. 1017). A start-up latency per function (package download, runtime init) enters the finish-time recursion (Eq. 3-4) as a given quantity (p. 1017); there is no container pool, keep-alive or pre-warming decision.

### 4. ⭐⭐ Lyapunov decomposition via a virtual cost queue turns P1 into per-slot problem P3 (pp. 1018-1019)
Virtual queue Q(t+1)=[Q(t)+C(t)-C_avg]+ (Eq. 9), quadratic Lyapunov function and drift (Eq. 10), and per-slot minimisation of drift plus V times makespan (P2, Eq. 11). Lemma 1 (p. 1018) bounds drift-plus-penalty by B + V O(t) + Q(t)(C(t)-C_avg) with B = 1/2((C_max)^2 + C_avg^2), proven by squaring Eq. 9 (pp. 1018-1019). P3 (Eq. 15) is solved per slot with current information only. The paper proves only this one-slot bound: it states no theorem on queue stability, on the time-average cost constraint holding, or on an O(1/V) optimality gap.

### 5. ⭐ Alg. 1 is the slot loop: on each request arrival merge, schedule, update the queue (p. 1019)
For each slot and each user, if request i arrives, obtain the merged DAG via Alg. 2, derive the placement via Alg. 3, compute O_i and C_i, then update the virtual cost queue by Eq. 9 (Alg. 1, p. 1019). The only "trigger" is request arrival; nothing decides whether or when to revise a policy.

### 6. ⭐ Two-level data merging fuses chains and same-level functions to cut cross-node transfers (pp. 1019-1020)
Vertical merging fuses a function with out-degree 1 and its successor whose only predecessor it is, so both run on one node and transfer time is zero (Alg. 2, lines 1-10; example nodes 8 and 10, p. 1020). Horizontal merging groups same-level functions up to the node parallel degree p, sorted by resource demand in descending order and merged from both ends for load balance (lines 11-26, p. 1020). Data dependencies are preserved. This is a graph pre-processing step, orthogonal to placement.

### 7. ⭐⭐ Placement uses a contextual combinatorial bandit (LinUCB) with a seven-feature context (pp. 1020-1021)
The context of request i is a 7-vector: node IDs, node level, node cost (computation along the longest path to the exit), computation-plus-transmission cost of the longest path, computation requirement, predecessor data volume and successor data volume (p. 1021). Each edge node keeps (A_e, b_e); theta_e = A_e^-1 b_e (Eq. 17); a function goes to argmin over e of theta_e^T x - alpha sqrt(x^T A_e^-1 x) (Eq. 18, Alg. 3). The longest-path features make the context partly critical-path-aware, but they are only features of a learned linear model, not a dispatch rule.

### 8. ⭐⭐ The only formal guarantee is a LinUCB-style regret bound, imported from prior work (pp. 1021-1022)
Lemma 2 (confidence bound; requires ||theta||<=S, ||x||<=L, probability at least 1-delta) and Lemma 3 are cited from Qin et al. [28] (Lemma 3's proof is "omitted", p. 1021). Theorem 1 states R_T <= C beta_T sqrt(8 T d log(1+kTL^2/(d lambda))) (Eq. 21, p. 1021), proved via a Lipschitz step (a) with a "universal constant" C (p. 1022). The bound is sublinear in T with respect to the best linear arm and concerns the per-slot objective value (P3), not makespan against an offline optimum or cost-constraint satisfaction.

### 9. ⭐⭐ The "no prior" claim means no knowledge of link rates or node status, not no knowledge of the DAG (pp. 1016, 1020)
SFSM needs only the request's contextual features (DAG topology, data sizes, computation amounts) and learns node behaviour from feedback (p. 1020). There is no forecasting of arrivals or workload, and no learned workload predictor beyond the linear reward model.

### 10. ⭐ Experiments: simulation with Alibaba v2018 DAGs, Bernoulli arrivals, three workload regimes (p. 1022)
Python 3.10 simulation, 10 fully connected edge nodes, 20-100 users, link rate 20-800 Mbps, node power 50-1000 GFLOPS, cost factors 0.8, C_avg = 5, Bernoulli request arrivals, parallel degree 3 (p. 1022). Three regimes (data-intensive, computation-intensive, both). Alibaba cluster trace v2018 (about 4000 machines, 8 days): 20,000 applications sampled in four size bands of 2-10, 11-50, 51-100 and over 100 functions (p. 1022).

### 11. ⭐⭐ Baselines are two online list schedulers, one static DP method and an ablation; metrics are time-average makespan and cost (p. 1022)
OnDoc [16] (online b-level priority lists), PASS [17] (priority-based, direct vs remote-storage path), LSS (static, dynamic programming, given complete request information), and SFSM without Alg. 2 (p. 1022). Metrics: time-average makespan O(t) and time-average cost C(t) against number of users, arrival rate, V and alpha (Figs. 4-7, pp. 1023-1024). Baselines OnDoc, PASS and LSS "do not follow the long-term cost constraint" (p. 1022).

### 12. ⭐⭐ Headline numbers, and where SFSM loses (pp. 1022-1023)
In the data-and-computation-intensive setting SFSM reduces time-average makespan by 37.2% on average over the baselines and execution cost by 91.7% (p. 1023). Across arrival rates, makespan improves by 164%, 95.7%, 23.7% and 54.2% over OnDoc, PASS, LSS and SFSM w/o, and cost by factors 3.36x, 3.16x, 1.71x, 1.54x (p. 1023). In computation-intensive settings the static LSS achieves lower makespan than SFSM (Fig. 4c, p. 1022).

### 13. ⭐ Sensitivity: V trades queue backlog against makespan; alpha sets exploration (pp. 1023-1024)
Fig. 7a shows average queue backlog rising then converging over 100 slots for V from 50 to 10000; the text says larger V "more actively" reduces backlog (p. 1023), which is the reverse of the usual drift-plus-penalty reading (larger V weights the penalty and enlarges backlog); the text is unclear. Fig. 7b: the bandit converges "after 10 learning times" (p. 1023).

### 14. ⭐ Related-work positioning (p. 1016)
Static DAG/function schedulers ([16], [17], [21], [24]) "fail to implement in the practical real-time multirequesting scenarios"; DRL and MAB schedulers ([8], [18], [22]) assume complete information or ignore transfer overhead; serverless optimisers ([3], [7], [14], [23]) lack long-term completion-time and cost optimisation (p. 1016).

### 15. Future work: start-up cost and cold start (p. 1024)
"In the future, the practical function start-up cost and cold-start problems will be further considered" (p. 1024).

## Figures and tables
Fig. 1 scenario (p. 1017); Fig. 2 framework (p. 1019); Fig. 3 merging example on ten functions (p. 1020); Figs. 4-6 makespan/cost curves (p. 1023); Fig. 7 V and alpha sensitivity (p. 1023). No tables. No figures extracted.

## What this source does not address
No deadlines, SLOs or user satisfaction (see [[lei-2026-adaptive]] and [[sun-2026-hybrid]] for deadline-aware work); no overload or admission control: every request is scheduled, and cost is controlled only through the virtual queue; no container lifecycle, keep-alive, pre-warming or cold-start model (deferred, p. 1024); no workload forecasting and no non-stationary arrival model (Bernoulli only); no reconfiguration trigger; no queue-stability or optimality-gap theorem; no real-system deployment; no comparison to forecast-driven or learning-augmented schedulers.

## Focus: G0 novelty gate (plan faas-edge-adaptation Task 3): online guarantees and their assumptions, scheduling/trigger logic, workloads/baselines/metrics, relation to DFPS and D1/D2/D3 — 2026-10-13

**Carries Kernthesen 2, 4, 5, 7, 8, 9, 11, 12.**

### What this focus needs beyond the Kernthesen
1. **What is proved (theorem inventory).** Lemma 1 (one-slot drift-plus-penalty bound, p. 1018), Lemmas 2-3 (confidence and elliptical-potential bounds, cited from [28], p. 1021), Theorem 1 (regret, Eq. 21, p. 1021). Nothing else: no theorem on cost-constraint satisfaction, queue stability, or competitive/approximation ratio.
2. **Assumptions each result needs.** Lemma 1: C(t) bounded by C_max (p. 1018). Lemmas 2-3 and Theorem 1: linear reward model with ||theta||<=S and ||x||<=L, a Lipschitz link with universal constant C, fixed horizon T and parameters k, lambda (pp. 1021-1022); noise assumptions are implicit in [28]. The experiments use Bernoulli (i.i.d.) arrivals (p. 1022), consistent with the stationarity such analyses presuppose; the paper never states a stationarity assumption or tests drift in arrivals.
3. **Quality flags on the proof.** Lemma 3's proof is omitted and Lemma 2's is "similar to [28]" (p. 1021); step (a) uses a Lipschitz constant without verification (p. 1022); the bandit reward is the P3 objective, which depends on the virtual queue Q(t) and so is non-stationary by construction, an interaction the regret analysis does not address (inferred, not stated). Treat Theorem 1 as a borrowed template, not a verified result for this system.
4. **Trigger/scheduling logic.** Event-driven: per request arrival inside each slot (Alg. 1, p. 1019); per function in topological order, all |E| nodes scored (Alg. 3, p. 1021). No periodic re-optimisation, no drift detector, no decision on when to change policy. Direct contrast with D1 (when to reconfigure).
5. **Overload.** No admission: a request is scheduled whenever it arrives (Alg. 1); overload shows only as larger makespan and queue growth (Fig. 4, p. 1023). Contrast with D2.
6. **Placement-dispatch coupling.** Placement is dispatch: a function is bound to a node at decision time, with the node's FCFS queue as the only ordering (p. 1017); critical-path information enters only as bandit features (Kernthese 7). Instance provisioning is absent, so there is nothing to couple. Contrast with D3.

### Direct quotes (for the draft)
> "SFSM incorporates an online multi-armed bandit-based scheduling algorithm that only requires the context of requests without complete information of edge networks." (p. 1015, abstract)

> "In the future, the practical function start-up cost and cold-start problems will be further considered." (p. 1024)

> "solving P3 only needs the current information rather than future input data" (p. 1019)

### Examples & illustrations (for later drafting)
- Merging example on a ten-function DAG: nodes 8 and 10 fused vertically, then same-level nodes 3-4 and 6-5 horizontally (Fig. 3, p. 1020).
- Computation-intensive regime where static LSS beats SFSM on makespan (Fig. 4c, p. 1022), showing the cost of operating without prior information.

### Boundary of this focus
Not an evaluation of the merging algorithm's merit or of the bandit's learning efficiency beyond what bears on guarantees and the D1/D2/D3 comparison.

## Mentioned entities
- Methods: [[sfsm]], [[dqlws]]
- Concepts: [[lyapunov-drift-plus-penalty]], [[linucb-contextual-bandit]], [[two-level-data-merging]], [[cold-start]]
- Datasets: [[alibaba-cluster-trace]]

## Connections
- Builds on [[lyapunov-drift-plus-penalty]] and [[linucb-contextual-bandit]].
- Same family as [[sun-2026-hybrid]] (Lyapunov per-slot decomposition, online, no forecasts; SFSM uses a bandit where [[dqlws]] uses a double DQN); compare deadline-aware [[lei-2026-adaptive]].
- Uses [[alibaba-cluster-trace]] for DAG topologies, as does [[lei-2026-adaptive]].

## G0 verdict (relation to DFPS and D1/D2/D3)
- **D1 (when to reconfigure; forecasts with guarantees): clear.** No trigger logic, no forecasts, no drift model; guarantees are a one-slot Lyapunov bound and an imported regret bound under linear-reward assumptions (Kernthesen 4, 8, 9).
- **D2 (overload admission + critical-path dispatch): clear on admission, minor on critical path.** No admission control; longest-path quantities appear only as bandit context features (Kernthese 7).
- **D3 (coupled placement-dispatch): clear.** Placement is node binding with FCFS dispatch; no instances, no cold start (Kernthesen 3, 15).
- **Relation to DFPS:** a Lyapunov plus online-learning baseline family that needs no forecasts, useful as a comparison class (OnDoc/PASS-style list scheduling plus a cost queue), and a cautionary example that "guarantee" in this literature means regret with respect to a learned per-slot objective rather than robustness to forecast error. The verdicts rest on this reading of the full text, not on a search of later work.
