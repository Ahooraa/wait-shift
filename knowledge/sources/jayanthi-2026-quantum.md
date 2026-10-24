---
title: "Jayanthi et al. 2026 — Quantum-inspired bi-level scheduling for serverless edge function deployment"
type: source
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
bibkey: jayanthi-2026-quantum
depth: standard
tags: [serverless, edge, placement, reinforcement-learning, g0-novelty-gate]
relations:
  - target: bi-level-scheduling
    type: builds-on
    confidence: extracted
    because: "Instantiates a global (QNGO, environment choice) plus local (PPO, container choice) scheduler: «the local scheduler fine-tunes the assignment at the node level ... while the global scheduler swiftly chooses the optimal environment» (p. 7)."
  - target: faas-sim
    type: cites
    confidence: extracted
    because: "Simulations run on FaaS-Sim: «We implemented the simulations using the FaaS-Sim tool» (p. 15)."
  - target: azure-functions-trace-2021
    type: cites
    confidence: extracted
    because: "One of two evaluation workloads, «14 days of Azure function invocations» (p. 16)."
  - target: globus-compute-dataset
    type: cites
    confidence: extracted
    because: "Second evaluation workload, 2,121,472 jobs on 580 endpoints (p. 16)."
---

# Quantum-inspired bi-level scheduling for resource-aware serverless function deployment in edge computing

## Bibliographic Details
Jayanthi, M., Shirisha, A. Sharada, and Kovvur, Ram Mohan Rao. 2026. *Quantum-inspired bi-level scheduling for resource-aware serverless function deployment in edge computing*. Discover Computing 29(1): 582 (36 pp., open access). https://doi.org/10.1007/s10791-026-10504-3. Received 10 April 2026, accepted 20 August 2026. Page numbers below are the printed "Page N of 36" numbers (identical to physical PDF pages).

## Section map

| Covered | Section | pp. |
|---|---|---|
| ✓ F1 | Abstract; 1 Introduction (contributions) | 1–3 |
| ✓ F1 | 2 Literature review; 2.1 Research gap (MAPE-K, BOECM, FBSW/DDRA/MRB, DQN, Q-learning) | 3–5 |
| ✓ F1 | 3 System model: architecture, time slots, container fault rate, cold start, cost, energy (Eqs. 1–4) | 5–8 |
| ✓ F1 | 4.1 Preprocessing (5-min bins, label encoding, z-score) | 8 |
| ✓ F1 | 4.2 IQRNN resource prediction (monotone quantiles, Eqs. 5–10) | 8–10 |
| ✓ F1 | 4.3 QNGO global scheduler (fitness Eq. 12, quantum amplitudes/tunnelling, Eqs. 11–22) | 10–12 |
| ✓ F1 | 4.4 PPO-RL local scheduler (state, six actions, reward Eq. 25, PPO updates) | 13–15 |
| — | 4.5 Computational complexity | 15 |
| ✓ F1 | 5 Setup, datasets (Globus, Azure), hyperparameters (Tables 1–2), metrics, baselines | 15–18 |
| ✓ F1 | 5.5 Results vs episodes (Tables 3–6) | 18–21 |
| ✓ F1 | 5.6 Results vs workload intensity 0.6–1.2 (Tables 7–10) | 21–24 |
| — | 5.7 Results vs number of edge nodes 3–30 (Tables 11–14) | 24–27 |
| — | 5.8 Resource prediction evaluation (Table 15) | 27–28 |
| — | 5.9 Convergence and stability (Figs. 3–5) | 28–31 |
| — | 5.10 Ablation (Table 16); 5.11 Sensitivity of fitness weights (Fig. 6) | 31–33 |
| ✓ F1 | 5.12 Discussion; 5.13 Limitations and future directions | 33–34 |
| ✓ F1 | 6 Conclusion; declarations; references (Zolfaghari 2025 is ref. 8) | 34–36 |

## Kernthesen

### 1. ⭐ A three-stage pipeline (predict, pick environment, pick container) is the paper's contribution (pp. 2–3, 7)
The authors combine an Improved Quantile Regression Neural Network (IQRNN) that predicts per-function execution time, CPU, memory, bandwidth and storage, a quantum-inspired Northern Goshawk Optimizer (QNGO) as global scheduler choosing cloud versus a specific edge server, and a PPO deep-RL local scheduler choosing the container. They argue prior hierarchical schedulers treat prediction, environment selection and scheduling as separate components, whereas theirs is "an integrated prediction-based scheduling approach" (p. 3). The justification for two levels is scalability: one flat scheduler "would require knowledge of every container across all servers" (p. 7).

### 2. IQRNN enforces non-crossing quantiles through a softplus re-parameterisation (pp. 9–10)
Each quantile is the previous one plus a softplus increment (Eq. 6), plus a monotonicity penalty (Eq. 9), and the net is trained with pinball loss. The claim is that this removes quantile crossing and stabilises prediction under noisy data (p. 9). It is presented as "uncertainty-aware" prediction, but nothing in the paper turns the quantile spread into a decision rule or a bound (see focus block).

### 3. QNGO replaces random coefficients with quantum-style amplitudes and a tunnelling term (pp. 10–12)
Agents are initialised with amplitudes alpha = cos(theta), beta = sin(theta) (Eq. 11); exploration uses amplitude-weighted random numbers (Eqs. 16–17) and a distance-decaying "tunnelling" perturbation T_q (Eq. 19). "Quantum" here is a metaphor for diversity-preserving stochastic search on a classical machine. The decision it makes is a single-function argmin over candidate environments (cloud or one of the edge servers).

### 4. The environment-selection fitness is a fixed equal-weight sum over predicted-versus-available resources (p. 11)
Eq. 12 sums five normalised ratios (time, CPU, memory, bandwidth, storage) with w1 = ... = w5 = 0.2; the environment with lowest fitness wins (p. 11). It contains no queueing, network-distance, state-transfer, or cold-start term. A sensitivity study varies the weights (p. 32).

### 5. ⭐ The PPO local agent has a six-action space mixing placement, scaling, queue priority, consolidation and pre-warm (pp. 13–14)
Actions: a1 reuse a warm container, a2 launch a cold one, a3 resize CPU/memory, a4 prioritise "latency-sensitive or deadline-critical functions" in the container queue, a5 consolidate functions at low load for energy, a6 pre-warm containers (pp. 13–14). The state holds current requests, container capacity, warm/cold flags, resource requirements and hosted functions (Eq. 23, p. 13).

### 6. The reward is a single scalarised cost with an SLO-violation penalty (p. 14)
r(t) = -(cold-start latency + fault rate + operating cost + energy + lambda * P_t) with lambda = 10 and P_t a binary SLO-violation flag at a 0.5 s threshold (Eq. 25, p. 14). SLO misses are only penalised in training; there is no run-time test that refuses work.

### 7. Cost, energy, cold-start and fault-rate models are per-function and per-time-slot (pp. 5–8)
Time is divided into slots; cold start is triggered when a container goes from not hosting f at t-1 to hosting it at t (Eq. 2); fault rate is a decreasing function of allocated computation capacity (Eq. 1); cost and energy are linear in duration (Eqs. 3–4). The objects scheduled are independent functions F = {f1..fn}; no inter-function dependency appears anywhere in the model (p. 5).

### 8. Evaluation: FaaS-Sim, Azure 2021 and Globus Compute traces, seven RL/heuristic baselines (pp. 15–18)
80/20 train/test split, PPO trained for 300 episodes (p. 16). Baselines: A3C, Double Dueling DQN, MADQL, DDRA, Greedy, ADRL+WSRIT and DRRL (p. 18). Prediction baselines: LSTM, GRU, Informer, QRNN (p. 18). Metrics: container fault rate, cold-start latency, function operating cost, energy, plus RMSE/MAE/MAPE/R2 for prediction (pp. 17–18). Setup is tiny: 1 cloud node, 3 edge nodes in the default (Table 1, p. 16), scaled to 30 in Tables 11–14 (pp. 24–27).

### 9. Headline gains are 13.7–29.2% over the best baselines, and the ablation attributes most to IQRNN (pp. 1, 31, 34–35)
Abstract and conclusion: 20.17–29.16% cold-start, 19.45–20.12% energy, 13.68–16.39% cost, 24.31–27.07% fault-rate reduction. Removing IQRNN raises Azure fault rate by 39.4% and cold-start latency by 40.7% (p. 31), larger than dropping QNGO (about 23%) or PPO (p. 31). So the forecasting component, not the scheduler structure, carries most of the claimed effect.

### 10. Workload-intensity sweep scales load from 0.6 to 1.2 and shows graceful, monotone degradation (pp. 21–24)
Tables 7–10 show all metrics worsening smoothly with intensity, with the proposed method lowest throughout (p. 21). The "intensity ratio" is never defined operationally, and 1.2 is only a 20% increase; no saturation, queue growth or rejection regime is explored.

### 11. Stated limitations concede the gaps this project cares about (p. 34)
The method assumes edge resource availability is known at scheduling time; PPO may react poorly to sudden spikes ("fast policy adjustment"); IQRNN accuracy needs relevant history and online sliding-window retraining is future work; "dependencies among functions" and security/isolation are "not covered in this study" (p. 34). Conclusion proposes decentralising the scheduler (p. 35).

### 12. Related work is a single paragraph per approach, mostly energy-aware and RL schedulers (pp. 3–5)
Covers MAPE-K energy schedulers, BOECM reuse-time optimisation, FBSW/DDRA/MRB placement, DQN/Q-learning placement and autoscaling. Zolfaghari et al. 2025 (dynamic function placement and request scheduling of serverless workflows) appears only as ref. 8 within a bracketed cluster [7-9] in the opening paragraph (p. 2, p. 35), not discussed in Section 2 and not a baseline.

## What this source does not address
No workflows or DAGs, no data/state transfer between functions (that is the territory of workflow papers such as Zolfaghari 2025 (DFPS), which is not yet a wiki page); no re-placement or migration policy (decisions are per arriving function, once); no admission control or load shedding; no worst-case or competitive-ratio guarantees; no real-trace non-stationarity analysis; no comparison to any workflow-aware placement method; security, isolation and privacy are deferred (p. 34). Real-hardware validation is asserted (OpenFaaS on Kubernetes, p. 15) but no OpenFaaS result table is shown.

## Focus: G0 novelty gate for D1/D2/D3 (when to reconfigure, forecasts with guarantees, overload admission, placement-dispatch coupling) — 2026-10-13

**Carries Kernthesen 1, 2, 4, 5, 6, 7, 8, 10, 11, 12.**

### Evidence per question

**(a) Does it decide WHEN to reconfigure or replace placement (event/cost-triggered versus clock-driven)? No.**
- The scheduler is invoked per arriving function: the global scheduler "chooses an appropriate environment for the incoming function" and the local one assigns it to a container (p. 5). Placement is a decision about each new invocation within a slot loop (p. 5), not a re-optimisation of an existing deployment.
- The only reconfiguration-like actions are a3 (resize a container), a5 (consolidate at low load) and a6 (pre-warm), all selected by the PPO policy as ordinary actions (pp. 13–14). There is no change-point detector, no threshold test, no switching-cost term, and no analysis of when to act. State carries no cost of changing placement (Eq. 23, p. 13).
- Predictor retraining is offline (80/20 split, p. 16); online sliding-window refinement is explicitly future work (p. 34).
- Verdict: D1 "when to reconfigure" is not touched. Timing is implicit in the RL policy and in the per-request loop.

**(b) Forecasts with robustness or worst-case guarantees? No guarantee; uncertainty-aware only in name.**
- IQRNN outputs non-crossing quantiles (pp. 9–10), motivated as "uncertainty-aware resource prediction" (p. 3). But the fitness function consumes "expected" resource values T_p, CPU_p, ... (Eq. 12, p. 11), and the paper never states that an upper quantile is used, nor does it define a hedging rule, regret bound or competitive ratio.
- Forecast target is the resource demand and execution time of a function, not the future arrival rate of a function. Preprocessing bins requests into 5-minute counts (p. 8) but the predicted outputs listed are execution time, CPU, memory, bandwidth, storage (p. 8).
- No experiment injects forecast error or tests degradation under a mis-specified forecast; the closest are the workload-intensity sweep (pp. 21–24) and the ablation that removes IQRNN (p. 31). The paper itself notes accuracy "might be compromised" for unseen behaviours (p. 34).
- Verdict: no learning-augmented / robust-consistency layer; D1's forecast add-on (H1b) is untouched.

**(c) Admission control or overload handling? None.**
- Every function is scheduled (placed on cloud, edge, or a new cold container, p. 13). There is no accept/reject, deferral or shedding action in the six-action space (pp. 13–14). Overload is handled implicitly by "reducing overload situations" through forecast-driven placement (p. 19) and by a fault-rate metric (Eq. 1, p. 6).
- The nearest mechanisms: the SLO penalty (lambda = 10 at a 0.5 s threshold, p. 14), which shapes training only, and action a4, which moves deadline-critical functions ahead in a container's queue (pp. 13–14). Neither refuses work or protects goodput.
- The heaviest load tested is intensity 1.2 (Tables 7–10, pp. 21–24); metrics degrade smoothly, so true overload (rho near or above 1) is not exercised. Sudden spikes are listed as a limitation (p. 34).
- Verdict: D2 admission is not touched. a4 is a queue-priority hint on independent functions, not critical-path dispatch.

**(d) Couples placement and dispatch/request scheduling; handles workflows or DAGs? Partial coupling at single-function level; no workflows.**
- Single PPO policy acts over placement (a1/a2), scaling (a3), queue priority (a4), consolidation (a5), pre-warm (a6), with one reward (pp. 13–14). That is a flat joint action space, but it is single-function.
- The model schedules independent functions F = {f1..fn} (p. 5). The word "dependencies" appears only in the limitations: "dependencies among functions ... are not covered in this study" (p. 34), and "workflow" appears only in the title of the cited [8] and [19] and for the paper's own pipeline figure (Fig. 2, p. 8). No DAG, critical path, makespan, or inter-function state transfer metric.
- Verdict: D3 (coupled placement-dispatch for workflows) is not touched; the only overlap is that one RL policy mixes placement and queue-priority actions.

### Workload and trace
- Globus Compute: 2,121,472 jobs, 252 users, 580 endpoints, 277,386 functions in 29 clusters, 28 Nov 2022 to 3 Jul 2023 (p. 16). Azure Functions invocation trace: 14 days (p. 16; data statement cites the 2021 trace, p. 35). Neither trace contains DAG structure; Azure has no per-workflow information.
- Simulator FaaS-Sim (Python 3.12.3), 1 cloud node and 3 edge nodes by default (Table 1, p. 16), edge node count varied to 30 (Tables 11–14); 300 PPO training episodes, 80/20 split (p. 16). OpenFaaS on Kubernetes cited for real-world implementation (p. 15), without separate results.
- Source code and config on Figshare (p. 35).

### Baselines
A3C, Double Dueling DQN, MADQL, DDRA, Greedy, ADRL+WSRIT (Li et al. 2025, ref. 4, task dispatching in serverless edge), DRRL (p. 18); predictor baselines LSTM, GRU, Informer, QRNN (p. 18). Hyperparameters of baselines set "in accordance with their pertinent references" (p. 18).

### Metrics
Container fault rate (%), cold-start latency (s), function operating cost ($), energy (Wh) (pp. 17–18); prediction RMSE, MAE, MAPE, R2 (p. 18). No makespan, tail latency (P95/P99), SLO-goodput, throughput or admission rate; no confidence intervals or repeated-seed statistics reported in the tables.

### Comparison to DFPS (Zolfaghari 2025)
No. Zolfaghari et al. appear only as ref. 8, in the introductory cluster "[7-9]" about the many-to-many function-to-node mapping (p. 2; reference list p. 35). It is not in the baseline list (p. 18) and not analysed in Section 2 (pp. 3–5).

### What this focus needs beyond the Kernthesen
1. The paper's own remark that QNGO prunes non-compliant environments so PPO acts in a smaller action space (p. 33) confirms the design is a pruning hierarchy, not a re-planning loop.
2. Reported scale advantages with edge node count (3 to 30) are mostly resource-availability effects (pp. 24–25), not scheduling-timing effects.
3. Table 3 to 14 results are very smooth across episodes and sweeps and several extracted tables are garbled; treat precise numbers cautiously when used as an evidence base (pp. 18–27).

### Direct quotes (for the draft)
> "Serverless concerns such as security-aware scheduling, tenant isolation, privacy, and dependencies among functions are not covered in this study." (p. 34)

> "the local scheduler fine-tunes the assignment at the node level, increasing scalability, efficiency, and adaptability, while the global scheduler swiftly chooses the optimal environment (cloud or which edge server) based on summarized metrics." (p. 7)

> "a4 indicates that latency-sensitive or deadline-critical functions should be prioritized in the container's queue" (pp. 13–14)

> "The existing system relies on the assumption that the availability of resources for edge nodes can be known during the scheduling process." (p. 34)

### Examples & illustrations (for later drafting)
- Ablation: dropping IQRNN raises Azure container failure by 39.4% and cold start by 40.7% (p. 31), showing the claimed benefit is predominantly forecast-driven.
- Cold-start latency at 300 episodes on Azure: proposed 0.086 s versus Greedy 0.14 s, DRRL about 0.09 s (Table 4, p. 19; the table is partly garbled).

### Boundary of this focus
This block judges only novelty overlap for D1/D2/D3. It does not assess the technical soundness of QNGO or IQRNN, nor the reported magnitude of gains.

## Mentioned entities
- Software and data: [[faas-sim]], [[azure-functions-trace-2021]], [[globus-compute-dataset]]
- Concepts: [[bi-level-scheduling]]

## Connections
- Builds on the global/local hierarchical scheduling pattern: [[bi-level-scheduling]] (typed in `relations:`).
- Evaluated on [[azure-functions-trace-2021]] and [[globus-compute-dataset]] in [[faas-sim]] (typed as `cites`).
- Cites Zolfaghari 2025 (DFPS) once as a generic placement reference (p. 2); no stance, no wiki page yet, so no typed relation.

## G0 verdict

Basis: Jayanthi 2026 only (not the other G0 sources).

- **D1 (when to reconfigure): clear.** Placement is a per-arriving-function decision inside a time-slot loop with no change-point, threshold or switching-cost logic (p. 5, pp. 13–14); retraining is offline with online updating deferred to future work (pp. 16, 34); its forecasts are per-function resource demands without robustness or worst-case guarantees (pp. 8–11).
- **D2 (overload admission + critical-path dispatch): clear.** The six PPO actions contain no accept/reject or shedding (pp. 13–14); the SLO appears only as a training penalty at 0.5 s (p. 14), a4 is a queue-priority nudge on independent functions, and load is only swept up to 1.2x with smooth degradation (pp. 21–24); no DAG or critical path exists.
- **D3 (coupled placement-dispatch for workflows): clear, minor partial overlap only at the single-function level.** One PPO policy jointly chooses placement, scaling, queue priority and pre-warm (pp. 13–14), but all functions are independent and workflow dependencies are explicitly out of scope (pp. 5, 34); Zolfaghari 2025 is cited once in passing and not compared (pp. 2, 18, 35).
