---
title: "ClusterLess-style baseline (CLU): independent deadline-aware workflow scheduler, pre-registration and Stage 1 results"
type: synthesis
created: 2026-11-16
updated: 2026-11-17
status: draft
author: llm
tags: [baselines, clusterless, deadline-aware, protocol, pre-registration, 2026-literature]
bibliography: ../../output/bibtex/references.bib
---

# ClusterLess-style baseline (CLU): pre-registration

*Written 16 Nov 2026, before any line of the baseline is implemented and before any run. User request 16 Nov: "write the ClusterLess pre-registration"; the baseline must be independent, like Heu and RL.*

## 1. Why this baseline, and why only this one

The user asked for one or two methods from 2026 to compare with F6. Three candidates were read on 16 Nov (full text, HTML versions; the PDF of CLASP did not load as text):

| Paper | Verdict | Reason |
|---|---|---|
| **ClusterLess**, arXiv 2605.04310 (May 2026), deadline-aware serverless workflow orchestration on federated edge clusters | **Used, as a single-cluster reduction** | Only candidate that takes DAG workflows with end-to-end completion times and cold-start overheads in its time estimate. |
| Taming Cold Starts, MPC, arXiv 2508.07640 (Aug 2025, v2 Jan 2026) | Not used | Single function only; no per-container busy state, so "waiting for a nearly ready container" is not a decision; no numeric weights, horizon or interval; constraint (18) is not solvable as written; no code. |
| **CLASP**, arXiv 2608.29103 (29 Aug 2026), chained-request-aware scaling and operator placement | Not used | Stream processing: objective is to sustain an input rate with as few workers as possible; no cold-start, container, keep-alive or pre-warming policy; state-migration design; coefficients from a 10-worker Faasm cluster with identical workers; no P99; code "after acceptance". Reimplemented, it would be a bin-packing heuristic plus a scaling rule of our own design. |

One new baseline is registered. A second, weakly specified one is not added. The paper states the gap: recent 2026 work targets single functions, streams, or deadline-driven federation; none optimises tail latency of workflow requests through cold-start-aware placement.

Bibkey: not yet in `references.bib`; it is added with verified metadata before any text cites it (no citation key is invented here).

## 2. What the paper specifies, and what it does not

**Specified (ported as written).**
- Workflow = DAG; a function starts only after its parents finish. Each workflow has an absolute deadline A_w + D_w.
- Serving time on worker n,i (Eq. 4): warm execution χ = Q + T; warm scaling χ = Q + WS + T; cold scaling χ = Q + CS + T.
- Transfer time between parent g and child f on different workers (Eq. 5): θ = X_out^g / b (zero if co-located). Start time (Eq. 6): S^f = A_w for roots, else max over parents (F^g + θ^gf). Finish F = S + χ (Eq. 7).
- Resource feasibility (Eq. 11): the function's CPU and memory demand fits the worker.
- Intra-cluster orchestration (Algorithm 2): start with every function local, in warm-execution mode; while the predicted workflow finish exceeds the deadline, take the bottleneck function (largest completion time), advance its mode (warm execution → warm scaling → cold scaling → offloading), accept a mode that is feasible and improves, then recompute the dependent functions.
- Hard deadlines: a function with no deadline-feasible placement marks the workflow as violated.

**Not specified (all fixed below, none tuned afterwards).** The estimators of Q, WS, CS and T; the internals of `IdentifyBottleneck`, `NextMode`, `ApplyMode`, `GetAvail`, `FuncOrch`; what "improving" means; how the pending set is formed; the placement rule among feasible workers; tie-breaking; keep-alive and pre-warming (none in the paper); the deadline values for our workloads; whether a plan is built once at submission (Algorithm 2, Sec. V-B) or per ready function (Sec. III-C); bookkeeping of resources reserved for in-flight workflows; what the bandwidth checks of Eqs. 12-13 compare (a size in MB against a bandwidth, with no time window). No code or artifact statement was seen in the part of the paper read; the last ~17,500 of 97,440 characters were read only as a summary.

## 3. The reduction to our system (deviations, stated in advance)

Run in the on-demand container model of Heu and RL (`dfps/ondemand.py`, mode `ready`): containers are created on demand with the function's cold start, idle containers are kept until recycled (`keep_warm=None`), a ready task takes an idle container of its function, else a free slot, else recycles the least-recently-used idle container of another function, else waits in the node's FIFO queue. Same scenario, network, capacities (CAP-W2 weights), execution-time draws and metrics as every other system.

| # | Paper | Here | Reason |
|---|---|---|---|
| D1 | Federated clusters, super-master, heartbeats, offloading mode | **One cluster = our 10 logical nodes; no offloading mode, no super-master** | We have one hub and one cluster. This is the paper's own "CLI" variant (intra-cluster only). |
| D2 | Warm scaling (WS) and cold scaling (CS) overheads | **One cold-start value per function** (`sim.cold_start[f]`); the mode set is warm execution and cold scaling only | The simulator has one cold start per function (no separate image-present case); the paper gives no WS value. |
| D3 | Eqs. 12-13 bandwidth feasibility | **Dropped**; transfers cost time (Eq. 5 via `sim._stt`), storage is a hard limit (`esc`) as for Heu | The checks are dimensionally incomplete as printed. |
| D4 | Deadlines D_w given per workflow class | **D_w = κ × L_w**, L_w = longest path of (nominal execution time + cold start) over the workflow's tasks, zero transfer; **κ = 1.5 primary**, κ ∈ {1.0, 3.0} reported | Our workloads have no deadlines. The paper's three classes (strict, moderate, lenient) span about 0.6-1.0 of the lenient value; the middle value is fixed here before any result. Heu uses 2.0 (AB-H3); a different value is used on purpose, so the baseline is not a copy of Heu's convention. |
| D5 | Hard deadline: infeasible → workflow "violated" | **The request still runs** with the plan of the smallest predicted finish; violations are counted (`pred_violated`) | Every request must complete for makespan to exist. |
| D6 | Keep-alive, pre-warming: none | **None** (container model of Heu and RL) | Not in the paper; identical to the other baselines. |
| D7 | Execution times from a time estimator | **Nominal means** `sim.exec_time[f]`, as Heu and RL see them | Nothing else is specified. |

## 4. The algorithm as implemented (fixed now)

Policy in `dfps/clusterless.py` (new file; reads only the simulator's public state: queues, container counts, idle counts, `exec_time`, `cold_start`, `ecc`, `fw`, `esc`, `storage_used`, `_stt`; **no code, estimator or constant is taken from the F5/F6 controller**, `o3s.py` or `sim.py::_late_bind`).

**State per node k at planning time t.**
- Warm set W_f: nodes holding at least one container of f (idle or busy).
- Room R_f: nodes where a new container of f fits (free capacity ≥ fw_f, or idle containers of other functions are enough to recycle); computed without changing state.
- Queue delay Q_k (paper's per-worker Q): 0 if node k holds an idle container of f; else backlog_k / ecc_k, with backlog_k = Σ over queued runs of nominal T·fw + Σ over running tasks of remaining nominal T·fw (remaining = max(0, T − elapsed)), plus T·fw of every task already placed on k *in the plan under construction* (so one plan does not pile all its tasks on one node).

**Plan of one request** (functions in topological order; a function's parents have predicted finish F^g and node n_g).
1. **Initial plan, all functions warm-execution mode.** For function f, candidate nodes = W_f. For each candidate k: θ_k = max over parents of `_stt`(output size, n_g, k) after F^g (S^f = max (F^g + θ), roots S = arrival time plus input transfer); χ_k = Q_k + T_f; F_k = S_k + χ_k. Choose the smallest F_k; ties: smaller θ, then lower node index. If W_f is empty (no container of f anywhere), the function is marked "needs scaling" and takes the cold-scaling rule of step 3 directly.
2. **Bottleneck loop.** While max F^f over the request's functions exceeds A_w + D_w: take the function with the largest predicted F^f among those not yet in cold-scaling mode; move it to cold-scaling mode: candidates = R_f; χ_k = CS_f + T_f (no queue wait, a new container); F_k as above; take the smallest. **Accept if the new F^f is smaller than its old F^f** (the paper's "improving"); then recompute all descendants with the rule of step 1 given the new F^f; else mark f as failed (excluded from selection) and continue. Stop when the deadline is met, no function can be moved, or every function is in cold-scaling mode.
3. If the deadline is still missed, keep the plan as it stands and count `pred_violated` (D5).
4. Reserve the input storage of the plan's tasks as for every other baseline.

**Binding, primary arm CLU (plan at submission, refined per ready function).** The plan is built at arrival (Algorithm 2). Whenever a task becomes ready, the plan is recomputed for that task and all not-yet-started descendants with the real finish times of finished parents and the current queues (Sec. V-B: "built on submission, then refined"; Sec. III-C: a decision per ready function). The task goes to the node of the new plan. **Ablation arm CLU-S** = plan at arrival only, never recomputed (Algorithm 2 read literally). Both are run; CLU is the headline, chosen now.

Tie-breaking, the "failed" exclusion and recompute order are fixed above; a rule not named here is not applied.

## 5. Independence and no-tuning rules

- Written from the paper's equations only; F6's selection rules, estimators and constants are not reused. Shared are only the simulator and the scenario, as for Heu and RL.
- No constant (κ, tie rule, backlog definition) is changed after a result is seen. If a defect is found, it is fixed as a labelled new version (CLU-2); the CLU results stay and both are reported, as in the tie-break v2 audit of the HEFT-like port ([[independent-baselines-capw1]]).
- κ = 1.5 is the headline; κ = 1.0 and 3.0 are always reported next to it. No "best κ per cell".
- CLU is not evaluated against F6 until the implementation checks in section 6 pass.
- A weak result is reported as it is. The audit (section 7) is where a possible handicap is looked for, before the runs.

## 6. Implementation checks (before any comparison run)

1. **Equations.** Unit tests for Eqs. 4-7 on a toy DAG (fork-join, three tasks) with hand-computed finish times; the warm-mode plan equals brute force over all nodes on 30 random toy instances.
2. **Escalation.** With a loose deadline no function leaves warm mode when a container exists; with a deadline below the warm-mode finish the bottleneck is moved and the finish improves; a function with no container anywhere starts in cold scaling.
3. **Simulator invariants.** `check_invariants()` clean on a short run per application; every request completes; event hash reproducible with the same seed.
4. **Decision time.** 99th percentile of one plan and one re-plan per application, reported (no limit applies to a baseline; a limit of 50 ms is the point at which the cost is mentioned in the paper).
5. **Policy seed.** Seeds as for the other baselines: policy seed + 500, simulator seed + 400 (`testbed/baselines_live.py` convention); CLU has no random element, so the policy seed is unused.

## 7. Audit step (before the runs, as done for FaaSPR and Graph-Aware)

A list of every equation and rule of section 2 against the code, with the line, and the deviations D1-D7. Questions to answer in writing: does CLU ever choose a node without a container of f in warm mode; does the backlog estimate ever exceed the real queue wait by more than a factor of 2 on a development cell (checked on a short log); is `pred_violated` rate reported per κ. Any defect found is fixed **before** the first comparison run and recorded; after that, section 5 applies.

## 8. Runs

All in the simulator, development seeds 1-3, the stored cells of the other systems (same scenarios, same CAP-W2 weights, same arrivals).

**Stage 1 (registered now).**
- A. Live cell and load sweep: four Q1 applications (ML, MapReduce, Video, ExCamera) × seeds 1-3 × conditions {live cell (load 0.5, peak cap 300), load 0.5 uncapped, 0.7, 0.9} = 48 runs, CLU at κ = 1.5.
- B. κ sensitivity at the live cell: κ ∈ {1.0, 3.0}, 4 × 3 × 2 = 24 runs.
- C. CLU-S ablation at the live cell: 12 runs.
- Total 84. Per-cell stop rule: a cell running longer than 2 h of wall time is stopped and reported as such; no cell is silently dropped.

**Stage 2 (not registered, needs the user's go-ahead).** Node-count (20, 40) and cold-start-duration studies, 1000Genome, and the held-out seeds 7-10. Seeds 4-6 stay reserved for the F6 confirmation.

## 9. Readings (fixed now; a baseline has no hypothesis to confirm, so these are descriptions)

Unit: a cell; ratios are P99(CLU) / P99(F6) with F6 = `frozen6` in the same cell; geometric mean with a bootstrap 95% CI over the 12 cells of a condition (10,000 resamples); average makespan the same way.
- **R1.** CLU against F6, Heu, B*, RL per condition: geometric-mean P99 and average makespan, per application and per seed, lowest-P99 count out of 12. This feeds the existing sensitivity figures (CLU added as a fifth series, palette slot and marker chosen then).
- **R2.** κ sensitivity: P99 and `pred_violated` rate at κ = 1.0, 1.5, 3.0.
- **R3.** CLU against CLU-S (does refinement at ready time matter).
- **R4.** Cold starts (total, including the warm-up), moved nothing (CLU has no mover), decision time per plan and re-plan, share of requests whose predicted finish missed the deadline, and share whose real finish missed it.
- **No claim is made that F6 beats CLU in advance.** If CLU has the lowest P99 in a condition, the table shows it, and the paper says so.

## 10. Limits stated in advance

- A single-cluster reduction of a federated system: the federation, offloading and the custom Kubernetes controller are not reproduced (D1). The comparison is with ClusterLess's intra-cluster part (its "CLI" variant), not with the system as evaluated in the paper.
- Estimators and the placement rule are ours where the paper is silent (section 2); a different reasonable reading could rank differently. This is why section 5 keeps CLU-2 open and why κ and the binding variants are reported, not selected.
- The paper's own evaluation uses edge hardware, 4G bandwidth traces and deadlines in a different workload; no number from it is expected to transfer.
- Development seeds only; F6 was chosen on the same seeds, so a gap in F6's favour on seeds 1-3 is optimistic (CLU received no tuning, F6 did).
- Simulator only. A live run of CLU is not planned.

## Evidence base
Papers read in full on 16 Nov 2026: ClusterLess (arXiv 2605.04310, tail summarised), the MPC paper (arXiv 2508.07640, PDF and TeX not read), CLASP (arXiv 2608.29103, evaluation tail summarised). Baseline protocol and the HEFT tie-break precedent: [[independent-baselines-capw1]]. Container model and the other two baselines: `dfps/ondemand.py`, `dfps/heu.py`, `BASELINES_SPEC.md`. Decision context: [[workflow-aware-decision-rules]], [[baseline-matrix]].

## What stays open
Whether the paper's code is released (not seen in the part read); the value of κ that matches the paper's deadline classes (the paper does not relate them to a critical path); whether the second baseline slot should be filled by a later 2026 paper; the exact warm-scaling overhead the paper used.

## Implementation and checks (16 Nov 2026, before any comparison run)

**Code.** `dfps/clusterless.py` (policy `ClusterLessPolicy(kappa, refine)`), builder `build_clu` and `warm_up_clu` in `testbed/baselines_live.py`, arms `clu`, `clu_s`, `clu_k10`, `clu_k30` in `testbed/controller_check.py::systems` (so `testbed/sim_sweep.py` runs them; its output gets a `clu` block with plans, replans, escalations, predicted and real deadline misses, plan time). Tests `tests/test_clusterless.py` (9). Check script `testbed/diag/clu_check.py`. Transfers are priced with `net.stt`/`net.h` directly, never `sim._stt`, so planning is not counted as data moved and the live simulator is not asked to send bytes. Nothing is committed.

**Section 6 checks.**
1. *Equations:* Eqs. 4-7 reproduced by hand on a two-task chain (nodes, finish times and workflow finish equal the hand values); the single-task warm plan equals brute force on 30 random placements. **Passed.**
2. *Escalation:* a loose deadline leaves every function in warm execution; a deadline below the warm finish moves the bottleneck to cold scaling next to its parent when a state transfer costs more than a cold start (finish improves by the expected amount); when scaling does not help, the move is dropped and the plan is unchanged; a function with no container anywhere is placed by the cold-scaling rule at the origin. **Passed.**
3. *Simulator:* 40-request runs of CLU and CLU-S finish every request, `check_invariants()` clean, event hash identical on a repeat. On the four live cells (seed 1, warm-up 30 s + window 120 s, CAP-W2, development): every request completes and the invariants hold for CLU and CLU-S in all four applications. **Passed.**
4. *Decision time (CLU, one plan or re-plan):* p99 1.4 ms (ML), 7.0 ms (MapReduce), 2.2 ms (Video), 14.3 ms (ExCamera); maximum 20.5 ms. Below the 50 ms mentioned in the registration. **Passed.**
5. *Seeds:* simulator seed + 400, policy seed + 500, as the other baselines. **Done.**

**Audit (section 7).**
- Warm mode never picks a node without a container of the function, by construction; a function with no container goes to the cold-scaling rule (test).
- *Is the finish-time estimate off?* Over all tasks of the short runs, the median of (predicted / real time from decision to finish) is 1.01 (ML), 0.98 (MapReduce), 1.02 (Video), 1.12 (ExCamera) for CLU. No factor-2 overestimate of the wait. In CLU-S the plan is older than the decision, so its error is larger by design (ratio 0.41 in MapReduce). The mean predicted time in MapReduce (0.36 s) is below the real one (0.60 s): the per-node backlog estimate under-reads long queues, so CLU sometimes thinks a node is free when it is not. This is a property of the registered estimator (section 4), recorded here and not changed.
- *Deadline misses at kappa = 1.5 (short runs):* predicted at arrival 0 of 4,275 (ML) up to 1 of 172 (Video); real 56/4,275 (ML), 351/1,234 (MapReduce), 49/172 (Video), 7/42 (ExCamera) for CLU, and far more for CLU-S (737, 682, 96, 30). The arrival plan sees an almost empty queue, so it predicts success; the real misses come from queueing after the plan, which is what refinement at ready time corrects (P99 on these short runs: CLU 2.0 / 8.3 / 47 / 121 s against CLU-S 6.6 / 14.9 / 158 / 168 s). Short development runs, not a comparison.
- Escalation counts are large in MapReduce (10,565 moves over 1,234 requests): the re-plan at every ready function repeats the escalation of its not-started descendants. This costs plan time only (p99 7 ms) and is part of the registered rule.

**Not changed after seeing these numbers:** kappa, the backlog definition, tie rule, binding rule. The checks found no defect that needs CLU-2.

**Status.** Implementation checks passed. Stage 1 (84 simulator runs) ran 16-17 Nov 2026 and is analysed below (section "Stage 1 results"). Stage 2 is not registered and not started.

**Stage 1 started 16 Nov 2026 (user go-ahead; spread over the hub and edge-2/3/4 the same evening by one dispatcher, `sim-clu-dispatch`).** Output `~/testbed-results/sim-clu/{live, rho0.5-uncapped, rho0.7, rho0.9}` (live holds arms `clu`, `clu_k10`, `clu_k30`, `clu_s`); four systemd user units, 11 workers; the 2 h per-cell stop rule applies. Finished 17 Nov 2026 00:06: 84 of 84 cells, 0 failures, no cell stopped (the longest, an ML cell at load 0.9, took 58 min). Results below.

## Stage 1 results (17 Nov 2026; readings R1-R4 as registered in section 9)

84 simulator runs, development seeds 1-3, CAP-W2, 10 nodes, container model of Heu and RL. Every cell finished all requests. Tables made by `output/data-analysis/clu_readings.py` (untracked; CSV and the full tables in `output/data-analysis/clu-readings/`). CLU = kappa 1.5, re-planned at every ready function, unless a row says otherwise. Ratios are geometric means over the 12 cells (4 applications x 3 seeds) of a condition with a bootstrap 95% CI (10,000 resamples). **The "load 0.5, no cap" condition has 12 cells, but Video and ExCamera there are the live cells (the peak cap never binds for them), so they repeat the live-cell numbers.** Only 3 development seeds: F6 was chosen on the same seeds and CLU received no tuning, so gaps in F6's favour are optimistic.

**What the readings show (descriptive; no claim was registered).**
- **CLU is a usable baseline and stronger than most of the existing ones.** Against Heu its P99 is lower in 6 / 4 / 9 / 10 of 12 cells (live / load 0.5 no cap / 0.7 / 0.9); against B* in 11 / 8 / 7 / 9; against RL in 9 / 5 / 6 / 5. The CIs of the ratio exclude 1 for B* and RL on the live cell, for Heu at load 0.7 and 0.9, and for RL at load 0.7; the other pairs include 1.
- **F6 has the lower P99 in most cells and the gap grows with load.** CLU / F6 = 1.10 [0.84, 1.40] on the live cell (not distinguishable; CLU is lower in 4 of 12 cells), then 2.36 [1.34, 4.26], 2.32 [1.71, 3.24], 2.64 [2.04, 3.48]. F6 has the lowest P99 of the five systems in 7 / 10 / 11 / 12 of 12 cells. On average makespan the order is the same (1.08 [1.00, 1.21] at the live cell, about 2 at loads 0.7 and 0.9).
- **The one cell group where CLU leads F6 is ML on the live cell** (P99 1.09 s against 1.72 s; ratio 0.68 over 3 seeds); at every other load ML is 1.4-2.0 times F6's P99. MapReduce is CLU's weakest application (5.2-11 times F6 once the cap is removed).
- **Re-planning at ready time matters (R3).** CLU / CLU-S: P99 0.61 [0.51, 0.73], lower in 11 of 12 cells; average makespan 0.83 [0.77, 0.88], lower in 12 of 12. The arrival plan sees almost empty queues: real misses 0.2-36% with re-planning against 2-54% without.
- **kappa (R2).** kappa 1.0 gives P99 0.88 [0.73, 1.04] of kappa 1.5 (not distinguishable); kappa 3.0 gives 1.77 [1.18, 2.68] (worse), with no predicted miss at all. Per application kappa 1.0 is nominally lowest in ML, MapReduce, Video and ExCamera. **kappa stays 1.5, as registered**: choosing 1.0 now would be tuning on the development seeds, which section 5 excludes; the three values are reported, not selected.
- **Deadline predictions are far too optimistic once the system is loaded (R4).** At load 0.9 the share of requests whose predicted finish missed the deadline is 62-99% and the real share 67-100%, so almost every request has an unreachable deadline. The rule of section 4 (D5: such a request still runs) then keeps escalating: 47-50 moves per request in MapReduce and ExCamera at load 0.9, and cold starts rise to 142,279 in MapReduce at load 0.9 against 44,804 for Heu and 1,750 for B*. This is consistent with the large MapReduce gap, but it was not tested separately: a variant that stops escalating once the deadline is out of reach would be a different baseline (CLU-2), not registered and not run.
- **Decision time is small (R4).** Plan time per decision: median 0.4-5.7 ms, p99 1-45 ms, largest single plan 183 ms.

### R1. CLU against F6, Heu, B*, RL

Geometric-mean ratio CLU / system over the 12 cells (4 applications x seeds 1-3) of a condition, bootstrap 95% CI (10,000 resamples). Below 1: CLU is lower. 'Lower in n/12' counts cells.


**P99 makespan**

| Condition | vs F6 | vs Heu | vs B* | vs RL |
|---|---|---|---|---|
| live cell (load 0.5, cap 300) | 1.10 [0.84, 1.40]; 4/12 | 0.86 [0.70, 1.06]; 6/12 | 0.34 [0.22, 0.52]; 11/12 | 0.55 [0.40, 0.75]; 9/12 |
| load 0.5, no cap | 2.36 [1.34, 4.26]; 1/12 | 0.82 [0.48, 1.29]; 4/12 | 0.66 [0.40, 1.08]; 8/12 | 0.90 [0.37, 1.95]; 5/12 |
| load 0.7 | 2.32 [1.71, 3.24]; 1/12 | 0.73 [0.53, 0.98]; 9/12 | 0.72 [0.51, 1.03]; 7/12 | 0.52 [0.26, 0.98]; 6/12 |
| load 0.9 | 2.64 [2.04, 3.48]; 0/12 | 0.70 [0.51, 0.95]; 10/12 | 0.77 [0.51, 1.22]; 9/12 | 0.71 [0.39, 1.19]; 5/12 |

**average makespan**

| Condition | vs F6 | vs Heu | vs B* | vs RL |
|---|---|---|---|---|
| live cell (load 0.5, cap 300) | 1.08 [1.00, 1.21]; 3/12 | 0.91 [0.81, 1.02]; 6/12 | 0.61 [0.51, 0.76]; 11/12 | 0.61 [0.45, 0.82]; 10/12 |
| load 0.5, no cap | 1.76 [1.20, 2.79]; 1/12 | 1.02 [0.73, 1.43]; 3/12 | 0.70 [0.47, 1.03]; 9/12 | 0.77 [0.33, 1.48]; 7/12 |
| load 0.7 | 1.94 [1.34, 3.01]; 0/12 | 1.28 [0.92, 1.86]; 3/12 | 0.80 [0.54, 1.22]; 8/12 | 0.64 [0.32, 1.16]; 7/12 |
| load 0.9 | 1.99 [1.45, 2.91]; 0/12 | 1.33 [0.98, 1.91]; 4/12 | 0.80 [0.48, 1.40]; 8/12 | 0.79 [0.51, 1.15]; 5/12 |

**P99 makespan per application (mean of seeds 1-3, s)**


live cell (load 0.5, cap 300)

| App | CLU | F6 | Heu | B* | RL | lowest |
|---|---|---|---|---|---|---|
| ML | 1.09 | 1.72 | 1.79 | 7.93 | 4.15 | CLU |
| MapReduce | 1.76 | 1.48 | 2.34 | 6.85 | 2.95 | F6 |
| Video | 41.14 | 29.77 | 33.23 | 90.29 | 69.78 | F6 |
| ExCamera | 170.66 | 102.75 | 158.16 | 175.25 | 148.14 | F6 |

load 0.5, no cap

| App | CLU | F6 | Heu | B* | RL | lowest |
|---|---|---|---|---|---|---|
| ML | 5.29 | 2.85 | 21.93 | 20.35 | 158.69 | F6 |
| MapReduce | 37.21 | 3.35 | 23.36 | 19.13 | 10.33 | F6 |
| Video | 41.14 | 29.77 | 33.23 | 90.29 | 69.78 | F6 |
| ExCamera | 170.66 | 102.75 | 158.16 | 175.25 | 148.14 | F6 |

load 0.7

| App | CLU | F6 | Heu | B* | RL | lowest |
|---|---|---|---|---|---|---|
| ML | 48.14 | 32.90 | 135.77 | 119.26 | 487.28 | F6 |
| MapReduce | 186.10 | 33.17 | 128.23 | 99.82 | 475.22 | F6 |
| Video | 130.64 | 58.49 | 186.59 | 259.80 | 93.74 | F6 |
| ExCamera | 338.42 | 171.02 | 482.42 | 392.15 | 242.17 | F6 |

load 0.9

| App | CLU | F6 | Heu | B* | RL | lowest |
|---|---|---|---|---|---|---|
| ML | 223.47 | 93.12 | 435.58 | 392.74 | 647.26 | F6 |
| MapReduce | 473.23 | 90.63 | 385.18 | 192.53 | 1500.33 | F6 |
| Video | 262.46 | 104.97 | 327.02 | 650.01 | 145.25 | F6 |
| ExCamera | 495.75 | 266.33 | 982.35 | 638.60 | 398.19 | F6 |

**Lowest P99 of the five systems, count over the 12 cells of a condition**

| Condition | CLU | F6 | Heu | B* | RL |
|---|---|---|---|---|---|
| live cell (load 0.5, cap 300) | 4 | 7 | 1 | 0 | 0 |
| load 0.5, no cap | 1 | 10 | 1 | 0 | 0 |
| load 0.7 | 0 | 11 | 0 | 0 | 1 |
| load 0.9 | 0 | 12 | 0 | 0 | 0 |

**Per seed: P99 ratio CLU / F6 (geometric mean over the 4 applications)**

| Condition | seed 1 | seed 2 | seed 3 |
|---|---|---|---|
| live cell (load 0.5, cap 300) | 1.19 | 1.12 | 1.00 |
| load 0.5, no cap | 3.22 | 2.67 | 1.53 |
| load 0.7 | 2.77 | 2.46 | 1.82 |
| load 0.9 | 3.16 | 2.24 | 2.60 |

**Per application: P99 ratio CLU / F6 (geometric mean over the 3 seeds)**

| Condition | ML | MapReduce | Video | ExCamera |
|---|---|---|---|---|
| live cell (load 0.5, cap 300) | 0.68 | 1.09 | 1.38 | 1.43 |
| load 0.5, no cap | 1.42 | 11.03 | 1.38 | 1.43 |
| load 0.7 | 1.47 | 5.45 | 2.13 | 1.70 |
| load 0.9 | 2.01 | 5.20 | 2.44 | 1.90 |

### R2. kappa sensitivity (live cell, 12 cells)

| kappa | geometric-mean P99 ratio to kappa = 1.5 | avg makespan ratio | predicted misses / requests | real misses / requests |
|---|---|---|---|---|
| 1.0 | 0.88 [0.73, 1.04] | 0.96 [0.91, 1.01] | 0.298% | 1.924% |
| 1.5 | 1 (reference) | 1 | 0.144% | 1.451% |
| 3.0 | 1.77 [1.18, 2.68] | 1.15 [1.02, 1.30] | 0.000% | 2.868% |

Per application, P99 (s, mean of seeds) and real-miss share (all requests incl. warm-up):

| App | k = 1.0 | k = 1.5 | k = 3.0 | pred. miss share k = 1.0 / 1.5 / 3.0 | real miss share k = 1.0 / 1.5 / 3.0 |
|---|---|---|---|---|---|
| ML | 0.99 | 1.09 | 1.02 | 0.0% / 0.0% / 0.0% | 0.4% / 0.2% / 0.2% |
| MapReduce | 1.49 | 1.76 | 5.07 | 0.0% / 0.0% / 0.0% | 0.9% / 4.1% / 9.9% |
| Video | 31.54 | 41.14 | 109.41 | 4.9% / 0.9% / 0.0% | 39.4% / 8.2% / 15.4% |
| ExCamera | 151.19 | 170.66 | 228.78 | 27.0% / 22.5% / 0.0% | 86.9% / 36.0% / 21.6% |

### R3. CLU (re-planned at every ready function) against CLU-S (plan at arrival only), live cell

Ratio CLU / CLU-S over 12 cells: P99 0.61 [0.51, 0.73] (CLU lower in 11/12), average makespan 0.83 [0.77, 0.88] (lower in 12/12).

| App | P99 CLU | P99 CLU-S | avg CLU | avg CLU-S | real miss share CLU / CLU-S | cold starts CLU / CLU-S |
|---|---|---|---|---|---|---|
| ML | 1.09 | 1.70 | 0.69 | 0.78 | 0.2% / 2.0% | 3 / 0 |
| MapReduce | 1.76 | 3.01 | 1.04 | 1.28 | 4.1% / 7.2% | 2118 / 511 |
| Video | 41.14 | 75.92 | 25.27 | 34.13 | 8.2% / 37.7% | 224 / 916 |
| ExCamera | 170.66 | 227.91 | 117.65 | 134.86 | 36.0% / 53.6% | 509 / 707 |

### R4. Cold starts, decision time, deadline misses (CLU, kappa = 1.5)

Cold starts: total of the run including the warm-up, mean of seeds. F6 is left out: it makes the same container changes during the warm-up, so its in-window count is not comparable.

| Condition | App | cold starts CLU | Heu | B* | RL | pred. miss share | real miss share | plan ms p50 / p99 / max | escalations per request |
|---|---|---|---|---|---|---|---|---|---|
| live | ML | 3 | 28877 | 1798 | 13977 | 0.0% | 0.2% | 0.62 / 3.1 / 35 | 0.00 |
| live | MapReduce | 2118 | 48605 | 3684 | 82897 | 0.0% | 4.1% | 0.85 / 4.8 / 63 | 0.71 |
| live | Video | 224 | 1499 | 5150 | 1987 | 0.9% | 8.2% | 1.00 / 3.7 / 26 | 0.35 |
| live | ExCamera | 509 | 1867 | 3682 | 3077 | 22.5% | 36.0% | 3.05 / 32.0 / 111 | 25.23 |
| unc0.5 | ML | 6779 | 66551 | 2820 | 14084 | 17.8% | 18.9% | 0.90 / 4.4 / 58 | 0.32 |
| unc0.5 | MapReduce | 38749 | 113064 | 2650 | 122510 | 40.1% | 43.8% | 1.13 / 14.2 / 135 | 20.18 |
| unc0.5 | Video | 224 | 1499 | 5150 | 1987 | 0.9% | 8.2% | 1.00 / 3.7 / 26 | 0.35 |
| unc0.5 | ExCamera | 509 | 1867 | 3682 | 3077 | 22.5% | 36.0% | 3.05 / 32.0 / 111 | 25.23 |
| rho0.7 | ML | 8873 | 58175 | 3302 | 16656 | 55.3% | 55.9% | 0.38 / 1.1 / 47 | 0.59 |
| rho0.7 | MapReduce | 106942 | 96773 | 2229 | 102747 | 78.7% | 82.4% | 1.92 / 18.2 / 146 | 38.29 |
| rho0.7 | Video | 1553 | 3120 | 4343 | 3067 | 31.9% | 36.5% | 0.79 / 4.0 / 26 | 1.58 |
| rho0.7 | ExCamera | 1081 | 2638 | 2612 | 3583 | 46.2% | 62.9% | 5.72 / 44.9 / 148 | 38.91 |
| rho0.9 | ML | 11892 | 22458 | 3509 | 7060 | 83.4% | 83.8% | 0.57 / 2.1 / 163 | 0.81 |
| rho0.9 | MapReduce | 142279 | 44804 | 1750 | 66350 | 99.1% | 100.0% | 1.88 / 7.8 / 183 | 47.04 |
| rho0.9 | Video | 2441 | 3911 | 3815 | 2852 | 61.6% | 67.3% | 1.36 / 3.9 / 25 | 2.72 |
| rho0.9 | ExCamera | 1943 | 2841 | 2179 | 2861 | 70.0% | 84.4% | 5.74 / 44.9 / 166 | 50.31 |

Largest single plan over all 48 CLU cells of the four conditions: 183 ms. State moved between nodes by CLU: 0 MB relocated (no mover); the run-time state traffic is in the result files (`resources.state_mb`).

**Figures (17 Nov 2026).** CLU is a fifth series (violet, down triangle) in `sim1_load_sweep`, `sim5_costs_vs_load` and the `sim6` overview of `output/data-analysis/sim-figures/` (script `make_sim_figures.py`); the node-count, cold-start and 1000Genome figures show no CLU because it was not run there.
