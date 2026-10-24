---
title: "Guo et al. 2026 — Popularity-aware layer-wise caching and function scheduling for dynamic workflow at the edge (OLCFS)"
type: source
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
bibkey: guo-2026-popularity-aware-caching
depth: standard
tags: [serverless-edge, dag-workflow, layer-wise-caching, online-learning, regret-bound, novelty-gate-g0]
relations:
  - target: olcfs
    type: mentions
    confidence: extracted
    because: "Proposes OLCFS (Algorithm 2) on top of the single-slot AAST (Algorithm 1), pp. 6283-6286."
  - target: layer-wise-container-caching
    type: builds-on
    confidence: extracted
    because: "Extends RainbowCake-style three-layer (bare/lang/user) caching to popularity-skewed dynamic DAGs (Sect. III-A, p. 6280)."
  - target: combinatorial-multi-armed-bandit
    type: builds-on
    confidence: extracted
    because: "«OLCFS is structured upon combinatorial multi-armed bandits» with each invocation probability as a base arm (p. 6285); regret via the CUCB analysis [50] (p. 6286)."
  - target: cold-start
    type: mentions
    confidence: extracted
    because: "Cold start decomposed into incremental (newly cached) and uncached-layer parts, Eq. 5-7 (pp. 6280-6281)."
  - target: alibaba-cluster-trace
    type: cites
    confidence: extracted
    because: "EB1 workflow topology taken from the top multi-call-graph application of the Alibaba microservice trace (pp. 6286-6287)."
  - target: azure-functions-trace-2019
    type: cites
    confidence: inferred
    because: "Cites Azure measurements [23] for invocation skew (8 orders of magnitude) and for the 10 s slot choice (pp. 6278, 6287); the trace itself is not replayed."
---

# Popularity-aware layer-wise caching and function scheduling for dynamic workflow at the edge

## Bibliographic Details
Guo, Xiaolin; Dong, Fang; Shen, Dian; Huang, Zhaowu. 2026. *Popularity-aware layer-wise caching and function scheduling for dynamic workflow at the edge*. *IEEE Transactions on Mobile Computing* 25(5): 6277-6290 (received 3 Mar 2025, accepted 17 Nov 2025). https://doi.org/10.1109/TMC.2025.3635845. Page numbers below are the printed IEEE pages (6277-6290).

## Section map

| Covered | Section | pp. |
|---|---|---|
| ✓ F1 | I. Introduction (three challenges, three designs, contributions) | 6277-6279 |
| — | II. Background (SEC, layer-wise caching, dynamic workflow) | 6279 |
| ✓ F1 | III. System model and problem statement (slots, Eq. 1-10, LCFS, NP-hardness) | 6279-6281 |
| ✓ F1 | IV-A. Problem transformation to ILP (Eq. 11-22, path set) | 6282 |
| ✓ F1 | IV-B1. AAST single-slot rounding algorithm, Lemmas 1-5, Theorems 1-2 | 6282-6285 |
| ✓ F1 | IV-B2. OLCFS online algorithm, Theorem 3 | 6285-6286 |
| ✓ F1 | V. Evaluation (setup, baselines, results, ablation, convergence) | 6286-6289 |
| ✓ F1 | VI. Related work | 6289 |
| ✓ F1 | VII. Discussion (single-instance, concurrency, limitations) | 6289-6290 |

## Kernthesen

### 1. ⭐⭐ Cold start in DAG workflows is a popularity problem, so caching must be weighted by function invocation probability (pp. 6278, 6280)
Call graphs differ in frequency (Alibaba trace: up to 53761 call graphs per application; shares vary 15-70%), so uniform layer caching wastes memory on rarely invoked functions. The paper uses the invocation probability rho_i as popularity and weights completion times by it in the objective (p. 6281).

### 2. ⭐ Caching and scheduling are coupled and must be optimised jointly (p. 6278)
Caching alone may warm a function on a memory-rich but slow node; the paper cites a 24 ms / 25% ACT penalty from decoupling [21]. Joint variables x (placement) and y (layer cached) appear in one TINLP.

### 3. ⭐ Time-coupled cache cost mitigates thrashing (Eq. 5-7, pp. 6280-6281)
Cold start per slot is T_inc (layers newly cached versus slot t-1, via [y_t - y_{t-1}]+) plus T_unc (uncached layers). Loading a layer is charged in the slot it is loaded, so reusing last slot's cache is cheaper; this is the only mechanism against thrashing (no explicit switching budget).

### 4. LCFS is NP-hard by reduction from bin packing (p. 6281)
The single-slot memory-limited special case LCFS-P with independent functions equals bin packing; the proof is a sketch.

### 5. ILP via chain-path enumeration (Eq. 11-22, p. 6282)
DFS enumerates all source-to-sink paths P; the recursive max in Eq. 10 becomes a max over paths of a popularity-weighted sum (Eq. 22). Products x*x are linearised with auxiliary variables. The path sum is a surrogate: Eq. 22 sums rho-weighted terms rather than the Eq. 10 critical path.

### 6. ⭐⭐ AAST = LP relaxation plus randomised rounding with retry until feasible (Algorithm 1, pp. 6282-6283)
The fractional LP solution is read as probabilities; rounding is repeated "until feasible". Theorem 1 (p. 6283): complexity O(H|N|^2|I|^2) "with high probability", H an empirical constant of simplex.

### 7. ⭐⭐ Single-slot guarantee is probabilistic and loose in form (Lemmas 1-5, Theorem 2, pp. 6283-6285)
Lemma 3 gives capacity constraints only in expectation. Lemmas 4 and 5 use Chernoff bounds plus a union bound over paths, giving failure probability at most 1/e^|N| (Eq. 30, 35). Theorem 2: the slot objective is at most sum_i p_i tau_i delta_1 + (2 - delta_1 + delta_2) OP with high probability, where delta_1, delta_2 depend on |N|, ln|P| and expected values Gamma_1, Gamma_2. This is roughly a factor-2 bound with additive terms, not a tight ratio.

### 8. ⭐⭐ OLCFS is CUCB over invocation probabilities (Algorithm 2, pp. 6285-6286)
Arms are functions; the first |I| slots initialise each arm; later slots use the UCB index mu_a = mu_hat_a + sqrt(3 ln t / (2 N_a)), feed it into AAST together with the previous cache state y_{t-1}, then update empirical means from the observed reward (reward = maxACT - ACT).

### 9. ⭐⭐ Theorem 3: regret O(|I| ln T) against a (1+eps)(1-1/e^|N|) fraction of OPT (p. 6286)
Reg(T) <= (6 ln T / (f^-1(Delta_min))^2 + pi^2/3 + 1) |I| Delta_max. It is an approximation-regret in the style of Chen et al. [50]; it needs f monotone with bounded smoothness and stationary arms, and compares to an approximate benchmark because AAST is only an approximation.

### 10. Evaluation: OLCFS beats FaasCache, RainbowCake and GSP by up to 2.92x ACT (pp. 6287-6288)
Ablation: removing RO (online learning/reuse) hurts most (2.1x), FS 1.81x/1.94x, LC 1.47x/1.45x (p. 6288). Convergence within a few slots (Fig. 8, p. 6289).

### 11. Admitted scope limits (pp. 6289-6290)
Single workflow, single instance per function, no queuing, no concurrency, no horizontal scaling; fixed-length slots (could become decision intervals or event-triggered, not tested).

## Figures and tables
Fig. 1 dynamic DAG and call graphs (p. 6277); Fig. 3 relation between Algorithms 1 and 2 (p. 6285); Fig. 4 Video and EB1 topologies (p. 6286); Figs. 5-8 results (pp. 6288-6289).

## What this source does not address
No queueing, concurrency or multi-instance scaling (own admission, pp. 6285, 6289); no multi-workflow contention; no non-stationary or adversarial popularity (arms are stationary, so shifts are not analysed); no admission control or SLO/tail metrics; no real-system deployment (simulation with profiled DNN workloads); no keep-alive/idle-cost trade-off. Other workflow-scheduling neighbours with different objectives: [[lei-2026-adaptive]], [[sun-2026-hybrid]].

## Focus: Online guarantees and assumptions, popularity shifts, update trigger, workloads/baselines/metrics, relation to DFPS, D1 and D3 (plan Task 3) — 2026-10-13

**Carries Kernthesen 3, 6, 7, 8, 9, 10, 11.**

### What this focus needs beyond the Kernthesen
1. **What is proved, exactly.** Theorem 1 (p. 6283) is a run-time bound w.h.p.; Lemmas 1-2 are feasibility w.h.p.; Lemma 3 (pp. 6283-6284) is capacity feasibility in expectation only; Theorem 2 (p. 6285) is a per-slot approximation bound w.h.p. (failure at most 1/e^|N|, Eq. 30/35); Theorem 3 (p. 6286) is a regret bound against a (1+eps)(1-1/e^|N|) fraction of OPT (Eq. 39). There is no competitive ratio and no worst-case bound over adversarial sequences.
2. **Assumptions the guarantees need.** (a) Each function's invocation follows an unknown fixed distribution with "short-term stationarity" so UCB can learn it (p. 6285), i.e. i.i.d. across slots. (b) Rewards bounded or normalisable (Chernoff, "properly normalized to [0,1]", p. 6284). (c) f monotone with bounded smoothness; Delta_min/Delta_max defined over bad strategies (p. 6286). (d) Every request finishes within one slot; one instance per function; no queueing (pp. 6280, 6285, 6289). (e) delta_1, delta_2 in [0,1], argued to hold "in practice" (pp. 6284-6285). (f) Rounding variables treated as independent events although coupled by constraints (p. 6282).
3. **Popularity shifts.** Handled only by continual re-estimation of the UCB mean (cumulative counts, no forgetting, no change detection, no window). The guarantee is for stationary arms, so a shift lies outside Theorem 3. Experiments vary call-graph shares across scenarios (Fig. 6, p. 6288) with fixed shares inside a run, so tracking after a shift is never tested.
4. **Update trigger.** Caching and placement are re-solved every fixed slot (10 s, p. 6287); each slot solves an LP and rounds (Algorithm 2, line 7). An event-triggered interval is only suggested (p. 6290). Reconfiguration cost enters as the incremental cold-start term, not as a switching cost or threshold rule.

### Direct quotes (for the draft)
> "We assume that each function invocation follows an unknown distribution with unknown expectations." (p. 6285)

> "The short-term stationarity of these invocation probabilities ensures that OLCFS can effectively learn and adapt within each time slot t." (p. 6285)

> "OLCFS assumes that each request can be scheduled immediately on the assigned edge servers, without explicitly tracking the availability of function instances or managing queuing delays." (p. 6285)

> "the decision interval can also be event-triggered instead of fixed-length." (p. 6290)

### Examples & illustrations (for later drafting)
- Workloads: Video (10 tasks) and EB1 (13 tasks, top multi-call-graph application of the Alibaba microservice trace), 5 call graphs each; tasks are 13 DNN models (pp. 6286-6287).
- Setup: 5 edge servers, 300-600 MB cache memory, 10-70 GFLOPS, 200-300 Mbps, 10 s slots, 250 slots per data point (pp. 6286-6287).
- Baselines: FaasCache (full container, priority), RainbowCake (layer-wise), GSP (DAG step placement), each given greedy scheduling or greedy full caching to be comparable (p. 6287). Metrics: average ACT split into cold start and execution time; ablation (w/o FS, LC, RO); convergence of reward = maxACT - ACT (pp. 6287-6289). No tail latency, SLO, cost or overhead measurement.

### Relation to DFPS, D1 and D3
- **DFPS.** Zolfaghari et al. (DFPS) are not cited or compared. Guo et al. cover caching plus single-instance placement without queueing; DFPS places multi-instance functions with M/M/c queueing. Guo's per-slot joint model resembles the DFPS replacement loop but replaces timing by a fixed slot.
- **D1 (when to reconfigure).** Not answered: reconfiguration happens every slot, with only a soft cost via T_inc. The limitations paragraph (p. 6290) names event-triggered intervals as an extension. D1 stays open against this source.
- **D3 (coupled placement-dispatch).** Partly preempted: the joint x/y optimisation per slot couples caching state and scheduling (Kernthese 2), but "dispatch" is a one-shot assignment of functions to servers without queues, so queue-aware coupling is not covered.

### Boundary of this focus
Not a source on queueing-aware dispatch or worst-case robust guarantees; its guarantees hold under stationary, i.i.d.-learnable popularity.

## Mentioned entities
- Methods: [[olcfs]]
- Concepts: [[layer-wise-container-caching]], [[combinatorial-multi-armed-bandit]], [[cold-start]]
- Datasets: [[alibaba-cluster-trace]], [[azure-functions-trace-2019]]

## Connections
- Builds on RainbowCake-style layer caching and the CUCB analysis: [[layer-wise-container-caching]], [[combinatorial-multi-armed-bandit]].
- Uses Alibaba trace topology: [[alibaba-cluster-trace]].
- Related G0 neighbours: [[lei-2026-adaptive]], [[sun-2026-hybrid]]; contrast with worst-case guarantees in [[learning-augmented-online-algorithms]].
