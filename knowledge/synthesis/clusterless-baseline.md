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

**Stage 2 (registered 17 Nov 2026 on the user's go-ahead, before any Stage 2 run; commit 9f97288 is the code that will run).** CLU at kappa 1.5 (refined, as in Stage 1), development seeds 1-3, in the sensitivity studies that exist for F6, Heu, B* and RL, with the same settings as their stored cells (their cells are reused, none is re-run):
- D. Node count: 20 and 40 nodes, four Q1 applications, nominal load 0.5 per node, no peak cap (`--ne N --peak-cap 0`): 2 x 4 x 3 = 24 runs. Output `~/testbed-results/sim-clu-s2/{ne20, ne40}`.
- E. Cold-start duration: 2, 5, 10 s for every function, live cell (peak cap 300), four applications (`--cold-s S`): 3 x 4 x 3 = 36 runs. Output `sim-clu-s2/{cold2, cold5, cold10}`.
- F. 1000Genome: loads 0.5, 0.7, 0.9, no peak cap (`--apps 6100.1000-genome --rho R --peak-cap 0`): 3 x 3 = 9 runs. Output `sim-clu-s2/{x0.5, x0.7, x0.9}`.
- Total 69 runs. Same dispatcher as Stage 1 (hub and the three laptops, heaviest first; same code on every machine, checked by md5 before the start). Per-cell stop rule as in Stage 1: a cell running longer than 2 h of wall time is stopped and reported, never silently dropped; it is re-run only with the user's go-ahead. Expected cost: from Stage 1, CLU's wall time is 0.2 to 6 times Heu's; the 40-node ML and MapReduce cells (Heu 1,250-1,450 s) are the ones that could reach the stop.
- **Frozen:** the CLU code, kappa = 1.5, the refine rule and the estimators stay as in Stage 1; no change between Stage 1 and the end of Stage 2. A change is a new variant (CLU-2) with its own registration.
- **Not in Stage 2:** Trip Booking (not run for F6, B* and RL); the kappa and CLU-S arms outside the live cell; the held-out seeds 7-10 and seeds 4-6. The held-out seeds are consumed once, need all five systems and a controller that is frozen, so they get their own registration when the F6 confirmation is decided. This narrows the earlier sketch of Stage 2, which listed seeds 7-10.

## 9. Readings (fixed now; a baseline has no hypothesis to confirm, so these are descriptions)

Unit: a cell; ratios are P99(CLU) / P99(F6) with F6 = `frozen6` in the same cell; geometric mean with a bootstrap 95% CI over the 12 cells of a condition (10,000 resamples); average makespan the same way.
- **R1.** CLU against F6, Heu, B*, RL per condition: geometric-mean P99 and average makespan, per application and per seed, lowest-P99 count out of 12. This feeds the existing sensitivity figures (CLU added as a fifth series, palette slot and marker chosen then).
- **R2.** κ sensitivity: P99 and `pred_violated` rate at κ = 1.0, 1.5, 3.0.
- **R3.** CLU against CLU-S (does refinement at ready time matter).
- **R4.** Cold starts (total, including the warm-up), moved nothing (CLU has no mover), decision time per plan and re-plan, share of requests whose predicted finish missed the deadline, and share whose real finish missed it.
- **R5 (Stage 2, node count).** CLU against F6, Heu, B*, RL at 20 and 40 nodes: geometric-mean ratio of P99 and of average makespan, bootstrap 95% CI over the 12 cells of a node count, lowest-P99 count out of 12; the 10-node point is the load-0.5 cell without a peak cap of Stage 1 (ML and MapReduce uncapped; Video and ExCamera the live twin). Also CLU's plan time (median, p99, max) against the node count, with the 10-node values of Stage 1.
- **R6 (Stage 2, cold-start duration).** The same ratios at 2, 5, 10 s over the 12 cells of a duration, plus CLU's cold starts and escalations per request against the duration (descriptive: whether cold scaling is chosen less often when it costs more).
- **R7 (Stage 2, 1000Genome).** Per-cell P99 and average makespan of the five systems at loads 0.5, 0.7, 0.9 and the geometric-mean ratio over the 9 cells with a bootstrap CI. These runs hold 54-88 requests, so the P99 is set by one or two requests; the CI is reported with that warning and no ranking is claimed.
- **Figures.** After R5-R7, CLU is added as a fifth series to `sim2_node_count`, `sim3_cold_start_duration` and `sim4_1000genome` (the load and cost figures already carry it), and the overview rows now marked 'not run' are filled.
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

**Status.** Implementation checks passed. Stage 1 (84 simulator runs) ran 16-17 Nov 2026 and is analysed below (section "Stage 1 results"). Stage 2 (69 runs: node count, cold-start duration, 1000Genome) ran 17 Nov 2026 and is analysed at the end of this page (section "Stage 2 results").

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

**Figures (17 Nov 2026).** CLU is a fifth series (violet, down triangle) in `sim1_load_sweep`, `sim5_costs_vs_load` and the `sim6` overview of `output/data-analysis/sim-figures/` (script `make_sim_figures.py`); the node-count, cold-start and 1000Genome figures got CLU after Stage 2 (see "Stage 2 results").

**Stage 2 started 17 Nov 2026 00:58 (user go-ahead).** 69 cells, one dispatcher unit `sim-clu2-dispatch` (hub 10 slots, edge-2: 3, edge-3: 3, edge-4: 5; heaviest first by Heu's stored wall time); output `~/testbed-results/sim-clu-s2/{ne20, ne40, cold2, cold5, cold10, x0.5, x0.7, x0.9}`, log `dispatch.log`. Code on the laptops equals the hub's (md5, 17 Nov 00:57). Results: not yet.

**Stage 2 stopped by the user, 17 Nov 2026 01:25, after 27 minutes.** 61 of 69 cells finished, 0 failures; 8 cells were stopped while running (not by the 2 h rule) and have no result: ne20 660.map-reduce s2; ne20 660.map-reduce s3; ne40 690.ml s1; ne40 690.ml s2; ne40 690.ml s3; ne40 660.map-reduce s1; ne40 660.map-reduce s2; ne40 660.map-reduce s3. Dispatcher unit and all sim_sweep processes stopped on the hub and the laptops. No reading R5-R7 has been applied; the 61 finished cells are in `~/testbed-results/sim-clu-s2/`. The missing cells are the 40-node and the heaviest 20-node ML and MapReduce cells, so R5 cannot be completed as registered until they are run or the registration is amended.

**Stage 2, remaining 8 cells restarted 17 Nov 2026 01:31 (user go-ahead).** One process per cell, no two heavy cells on one core: hub 4 (40-node ML seeds 1-3, 40-node MapReduce seed 3), edge-4 2 (40-node MapReduce seeds 1-2), edge-2 1 and edge-3 1 (20-node MapReduce seeds 2 and 3). Same code (commit 9f97288), same 2 h per-cell stop rule, unit `sim-clu2b-dispatch`. Results: not yet.

**Stage 2 finished 17 Nov 2026 02:13.** All 69 cells done, 0 failures, no cell reached the 2 h stop rule (the 8 restarted cells took 28-42 min on the hub and edge-4); every run has `n_unfinished = 0`. Same code as Stage 1 (commit 9f97288). Results below.

## Stage 2 results (17 Nov 2026; readings R5-R7 as registered in section 9)

Computed by `output/data-analysis/clu_readings_s2.py` (tables also in `output/data-analysis/clu-readings/readings_s2.md`, ratios in `R5_ratios.csv`, `R6_ratios.csv`, `R7_ratios.csv`). Same method as R1: geometric-mean ratio CLU / system over the cells of a condition, bootstrap 95% CI (10,000 resamples) over cells, development seeds 1-3, F6 = `frozen6`. Cells of one application share seeds across conditions and the three seeds are few, so the intervals describe these 12 (R7: 9) cells, not a population.

**What the readings say, in short.**
- **R5 (node count).** F6 stays ahead of CLU at every size: P99 ratio CLU / F6 2.36 [1.34, 4.23] at 10 nodes, 2.45 [1.54, 4.12] at 20, 2.67 [1.62, 4.45] at 40; F6 has the lowest P99 in 10, 9 and 10 of 12 cells. Against Heu, CLU's ratio is 0.82, 0.92, 0.85 (every interval contains 1, no difference shown). Against B* the ratio falls with size, 0.66, 0.59, 0.43, with CLU lower in 12 of 12 cells at 40 nodes (B*'s P99 grows with the node count while CLU's is flat except Video). Against RL 0.90, 0.44, 0.44, intervals wide (RL's ML P99 is 159, 537, 633 s). CLU's plan time does not grow with the cluster: median per-plan time 1.00, 0.81, 0.89 ms, median p99 5.4, 4.7, 5.3 ms, largest plan 135, 47, 58 ms (10, 20, 40 nodes); the wall time of a run grows with the request count (ML 511, 967, 1,545 s). The one application where CLU's P99 degrades with size is Video: 41 s, 46 s, 91 s, real miss share 8.2%, 15.9%, 32.8% (more requests per run, escalation 0.35, 0.57, 0.92 per request).
- **R6 (cold-start duration).** CLU / F6 P99 is 3.40 [1.27, 10.61] at 2 s, 8.32 [2.45, 33.29] at 5 s, 20.31 [5.82, 84.69] at 10 s; F6 has the lowest P99 in 9, 11, 12 of 12 cells. CLU is lower than F6 in 3 cells at 2 s, the three ML cells (P99 0.99, 0.88, 1.01 s against F6's 1.19, 1.17, 2.81). Against Heu, B* and RL every interval contains 1 (CLU / Heu 0.63, 0.77, 0.97; CLU / B* 0.88, 1.70, 2.73; CLU / RL 1.00, 0.57, 0.87): no ranking among the baselines is shown. The registered descriptive question, whether CLU chooses cold scaling less often when it costs more: **not in these cells.** Cold-mode decisions per request rise with the duration for ML (0.002, 0.005, 0.007 for 2, 5, 10 s) and Video (0.26, 0.50, 0.55), stay flat for ExCamera (1.11, 1.07, 1.03) and for MapReduce rise from 0.12 (measured) to 4.1 and 8.3 and fall to 6.6 at 10 s; escalations per request rise the same way. Absolute cold starts fall only at the longest durations (MapReduce 20,468 at 5 s to 10,671 at 10 s; ExCamera 616, 321, 338), where the run is already backlogged. MapReduce is the failure: P99 120, 578, 1,634 s against F6's 1.5 s, real deadline-miss share 56.5%, 100%, 100% (every request misses its deadline at 5 and 10 s), the same mechanism as in Stage 1 (D5: escalation under an unreachable deadline).
- **R7 (1000Genome).** 54-88 requests per run (45 in one cell), so each P99 is set by one or two requests and no ranking is claimed (as registered). Geometric-mean P99 ratio over the 9 cells: CLU / F6 1.36 [1.10, 1.67] (CLU lower in 2 of 9), CLU / Heu 0.60 [0.44, 0.82] (8 of 9), CLU / B* 1.36 [1.26, 1.47] (0 of 9), CLU / RL 1.09 [0.95, 1.31] (6 of 9); average makespan 1.15, 0.88, 1.06, 1.14 against F6, Heu, B*, RL. Lowest P99 per cell: B* 6, F6 3, CLU 0, Heu 0, RL 0. Heu is the weak system here (P99 up to 3,220 s); CLU's P99 at load 0.7 and 0.9, seed 1, is 1,239 s and 1,439 s against F6's 564 s and 645 s.

**Lowest P99 of the five systems (cells out of 12 per condition; 9 for 1000Genome).** Node count, CLU / F6 / Heu / B* / RL: 10 nodes 1 / 10 / 1 / 0 / 0, 20 nodes 1 / 9 / 2 / 0 / 0, 40 nodes 1 / 10 / 1 / 0 / 0. Cold start: 2 s 3 / 9 / 0 / 0 / 0, 5 s 1 / 11 / 0 / 0 / 0, 10 s 0 / 12 / 0 / 0 / 0. 1000Genome 0 / 3 / 0 / 6 / 0. CLU's P99 ratio interval excludes 1 against F6 in every Stage 2 condition (above 1); against Heu only on 1000Genome (below 1); against B* at 20 and 40 nodes (below 1) and on 1000Genome (above 1); against RL never. These describe these cells; no claim is made about why (CLU-2 is not registered).

### Stage 2: R5. Node count (nominal load 0.5 per node, no peak cap)

Geometric-mean ratio CLU / system over the 12 cells (4 applications x seeds 1-3) of a node count, bootstrap 95% CI (10,000 resamples). Below 1: CLU is lower. 'n/12' counts cells where CLU is lower. The 10-node row is the load-0.5 cell without a peak cap of Stage 1 (ML and MapReduce own runs; Video and ExCamera the live twin).




**P99 makespan**

| Condition | vs F6 | vs Heu | vs B* | vs RL |
|---|---|---|---|---|
| 10 nodes (load 0.5, no cap) | 2.36 [1.34, 4.23]; 1/12 | 0.82 [0.48, 1.29]; 4/12 | 0.66 [0.40, 1.08]; 8/12 | 0.90 [0.37, 1.97]; 5/12 |
| 20 nodes | 2.45 [1.54, 4.12]; 1/12 | 0.92 [0.61, 1.33]; 5/12 | 0.59 [0.40, 0.86]; 9/12 | 0.44 [0.11, 1.49]; 8/12 |
| 40 nodes | 2.67 [1.62, 4.45]; 1/12 | 0.85 [0.45, 1.52]; 5/12 | 0.43 [0.24, 0.68]; 12/12 | 0.44 [0.09, 1.84]; 7/12 |

**average makespan**

| Condition | vs F6 | vs Heu | vs B* | vs RL |
|---|---|---|---|---|
| 10 nodes (load 0.5, no cap) | 1.76 [1.20, 2.76]; 1/12 | 1.02 [0.73, 1.42]; 3/12 | 0.70 [0.47, 1.03]; 9/12 | 0.77 [0.33, 1.50]; 7/12 |
| 20 nodes | 1.70 [1.21, 2.59]; 1/12 | 1.03 [0.76, 1.39]; 3/12 | 0.60 [0.42, 0.85]; 10/12 | 0.56 [0.18, 1.35]; 8/12 |
| 40 nodes | 1.68 [1.22, 2.48]; 2/12 | 0.99 [0.69, 1.40]; 4/12 | 0.44 [0.29, 0.63]; 12/12 | 0.47 [0.16, 1.20]; 7/12 |

**P99 makespan per application (mean of seeds 1-3, s)**


10 nodes (load 0.5, no cap)

| App | CLU | F6 | Heu | B* | RL | lowest |
|---|---|---|---|---|---|---|
| ML | 5.29 | 2.85 | 21.93 | 20.35 | 158.69 | F6 |
| MapReduce | 37.21 | 3.35 | 23.36 | 19.13 | 10.33 | F6 |
| Video | 41.14 | 29.77 | 33.23 | 90.29 | 69.78 | F6 |
| ExCamera | 170.66 | 102.75 | 158.16 | 175.25 | 148.14 | F6 |

20 nodes

| App | CLU | F6 | Heu | B* | RL | lowest |
|---|---|---|---|---|---|---|
| ML | 5.56 | 3.10 | 18.27 | 20.99 | 537.37 | F6 |
| MapReduce | 38.72 | 3.60 | 21.36 | 27.00 | 11.26 | F6 |
| Video | 45.56 | 30.68 | 34.71 | 91.25 | 88.65 | F6 |
| ExCamera | 175.74 | 110.13 | 201.60 | 244.91 | 157.05 | F6 |

40 nodes

| App | CLU | F6 | Heu | B* | RL | lowest |
|---|---|---|---|---|---|---|
| ML | 4.48 | 2.94 | 20.45 | 36.28 | 633.47 | F6 |
| MapReduce | 38.56 | 3.90 | 25.01 | 49.74 | 5.03 | F6 |
| Video | 91.21 | 29.78 | 35.89 | 119.37 | 108.46 | F6 |
| ExCamera | 174.80 | 105.94 | 429.30 | 288.94 | 148.72 | F6 |

**Average makespan per application (mean of seeds 1-3, s)**


10 nodes (load 0.5, no cap)

| App | CLU | F6 | Heu | B* | RL | lowest |
|---|---|---|---|---|---|---|
| ML | 1.25 | 0.88 | 2.88 | 5.42 | 39.46 | F6 |
| MapReduce | 8.71 | 1.31 | 3.68 | 5.48 | 2.70 | F6 |
| Video | 25.27 | 23.98 | 23.53 | 37.10 | 27.89 | Heu |
| ExCamera | 117.65 | 85.62 | 100.28 | 108.93 | 102.67 | F6 |

20 nodes

| App | CLU | F6 | Heu | B* | RL | lowest |
|---|---|---|---|---|---|---|
| ML | 1.27 | 0.96 | 2.73 | 5.19 | 43.80 | F6 |
| MapReduce | 8.07 | 1.39 | 3.64 | 7.18 | 2.66 | F6 |
| Video | 26.60 | 23.98 | 23.60 | 40.03 | 33.13 | Heu |
| ExCamera | 111.80 | 86.69 | 104.59 | 127.37 | 106.41 | F6 |

40 nodes

| App | CLU | F6 | Heu | B* | RL | lowest |
|---|---|---|---|---|---|---|
| ML | 1.06 | 0.94 | 2.82 | 7.66 | 44.27 | F6 |
| MapReduce | 7.58 | 1.46 | 3.85 | 12.17 | 2.68 | F6 |
| Video | 31.80 | 23.87 | 23.60 | 47.87 | 44.01 | Heu |
| ExCamera | 112.82 | 85.23 | 106.78 | 156.21 | 96.00 | F6 |

**Lowest P99 of the five systems, count over the cells of a condition**

| Condition | CLU | F6 | Heu | B* | RL | cells |
|---|---|---|---|---|---|---|
| 10 nodes (load 0.5, no cap) | 1 | 10 | 1 | 0 | 0 | 12 |
| 20 nodes | 1 | 9 | 2 | 0 | 0 | 12 |
| 40 nodes | 1 | 10 | 1 | 0 | 0 | 12 |

**CLU's plan time against the node count (all cells of the application, 3 seeds)**

| Nodes | App | requests (mean) | plan ms p50 | p99 | max | escalations per request | real miss share | wall s (mean) |
|---|---|---|---|---|---|---|---|---|
| 10 nodes | ML | 85,043 | 0.90 | 4.4 | 58 | 0.32 | 18.9% | 511 |
| 10 nodes | MapReduce | 31,591 | 1.13 | 14.2 | 135 | 20.18 | 43.8% | 921 |
| 10 nodes | Video | 1,692 | 1.00 | 3.7 | 26 | 0.35 | 8.2% | 13 |
| 10 nodes | ExCamera | 383 | 3.05 | 32.0 | 111 | 25.23 | 36.0% | 39 |
| 20 nodes | ML | 183,203 | 0.88 | 2.3 | 39 | 0.41 | 22.1% | 967 |
| 20 nodes | MapReduce | 68,219 | 0.83 | 9.0 | 42 | 19.00 | 40.0% | 1,381 |
| 20 nodes | Video | 3,631 | 0.40 | 1.4 | 6 | 0.57 | 15.9% | 12 |
| 20 nodes | ExCamera | 805 | 1.76 | 18.2 | 47 | 25.95 | 35.6% | 49 |
| 40 nodes | ML | 328,744 | 0.77 | 1.7 | 50 | 0.22 | 16.3% | 1,545 |
| 40 nodes | MapReduce | 122,440 | 0.87 | 7.1 | 58 | 18.43 | 38.5% | 2,403 |
| 40 nodes | Video | 6,605 | 1.08 | 3.1 | 19 | 0.92 | 32.8% | 58 |
| 40 nodes | ExCamera | 1,438 | 1.86 | 16.2 | 34 | 29.31 | 36.3% | 89 |

10 nodes: median over the 12 cells of the per-cell p50 = 1.00 ms, of the per-cell p99 = 5.4 ms, largest single plan 135 ms.

20 nodes: median over the 12 cells of the per-cell p50 = 0.81 ms, of the per-cell p99 = 4.7 ms, largest single plan 47 ms.

40 nodes: median over the 12 cells of the per-cell p50 = 0.89 ms, of the per-cell p99 = 5.3 ms, largest single plan 58 ms.

**Cold starts (total of the run incl. warm-up, mean of seeds)**

| Nodes | App | CLU | Heu | B* | RL |
|---|---|---|---|---|---|
| 10 nodes | ML | 6,779 | 66,551 | 2,820 | 14,084 |
| 10 nodes | MapReduce | 38,749 | 113,064 | 2,650 | 122,510 |
| 10 nodes | Video | 224 | 1,499 | 5,150 | 1,987 |
| 10 nodes | ExCamera | 509 | 1,867 | 3,682 | 3,077 |
| 20 nodes | ML | 10,308 | 140,558 | 3,794 | 16,415 |
| 20 nodes | MapReduce | 71,504 | 243,055 | 5,185 | 245,296 |
| 20 nodes | Video | 823 | 2,914 | 7,498 | 4,274 |
| 20 nodes | ExCamera | 1,022 | 3,635 | 5,921 | 6,376 |
| 40 nodes | ML | 18,820 | 265,128 | 3,972 | 16,702 |
| 40 nodes | MapReduce | 116,779 | 440,772 | 8,525 | 332,753 |
| 40 nodes | Video | 1,438 | 6,135 | 9,219 | 7,426 |
| 40 nodes | ExCamera | 2,134 | 7,142 | 8,166 | 11,238 |

### Stage 2: R6. Cold-start duration (live cell: nominal load 0.5, peak cap 300 tasks/s; one duration for every function)

Geometric-mean ratio CLU / system over the 12 cells of a duration, bootstrap 95% CI. Below 1: CLU is lower.




**P99 makespan**

| Condition | vs F6 | vs Heu | vs B* | vs RL |
|---|---|---|---|---|
| cold start 2 s | 3.40 [1.27, 10.61]; 3/12 | 0.63 [0.24, 1.47]; 4/12 | 0.88 [0.34, 2.44]; 7/12 | 1.00 [0.45, 2.23]; 6/12 |
| cold start 5 s | 8.32 [2.45, 33.29]; 1/12 | 0.77 [0.26, 1.95]; 6/12 | 1.70 [0.57, 5.67]; 8/12 | 0.57 [0.21, 1.24]; 4/12 |
| cold start 10 s | 20.31 [5.82, 84.69]; 0/12 | 0.97 [0.39, 2.41]; 5/12 | 2.73 [0.93, 8.80]; 6/12 | 0.87 [0.31, 2.09]; 3/12 |

**average makespan**

| Condition | vs F6 | vs Heu | vs B* | vs RL |
|---|---|---|---|---|
| cold start 2 s | 2.63 [1.24, 6.28]; 1/12 | 0.72 [0.36, 1.35]; 5/12 | 1.31 [0.67, 2.76]; 8/12 | 0.93 [0.52, 1.61]; 8/12 |
| cold start 5 s | 5.29 [1.44, 21.99]; 1/12 | 0.78 [0.25, 2.33]; 6/12 | 2.17 [0.72, 7.65]; 8/12 | 0.72 [0.32, 1.47]; 4/12 |
| cold start 10 s | 8.45 [1.92, 41.27]; 0/12 | 0.72 [0.21, 2.40]; 9/12 | 2.44 [0.67, 10.11]; 8/12 | 0.61 [0.20, 1.65]; 3/12 |

**P99 makespan per application (mean of seeds 1-3, s)**


cold start 2 s

| App | CLU | F6 | Heu | B* | RL | lowest |
|---|---|---|---|---|---|---|
| ML | 0.96 | 1.72 | 21.01 | 8.64 | 6.65 | CLU |
| MapReduce | 119.99 | 1.49 | 34.52 | 8.73 | 16.34 | F6 |
| Video | 46.99 | 29.65 | 42.77 | 111.20 | 57.00 | F6 |
| ExCamera | 203.59 | 101.83 | 256.91 | 206.09 | 169.11 | F6 |

cold start 5 s

| App | CLU | F6 | Heu | B* | RL | lowest |
|---|---|---|---|---|---|---|
| ML | 4.86 | 1.72 | 62.58 | 11.51 | 74.40 | F6 |
| MapReduce | 577.91 | 1.49 | 88.16 | 12.07 | 677.35 | F6 |
| Video | 86.83 | 29.66 | 75.67 | 138.46 | 59.00 | F6 |
| ExCamera | 232.47 | 103.73 | 271.90 | 238.80 | 183.97 | F6 |

cold start 10 s

| App | CLU | F6 | Heu | B* | RL | lowest |
|---|---|---|---|---|---|---|
| ML | 14.44 | 1.72 | 147.17 | 20.45 | 314.19 | F6 |
| MapReduce | 1634.12 | 1.50 | 180.05 | 18.99 | 492.75 | F6 |
| Video | 201.37 | 29.86 | 146.45 | 224.61 | 95.22 | F6 |
| ExCamera | 292.91 | 102.56 | 431.53 | 303.15 | 215.48 | F6 |

**Average makespan per application (mean of seeds 1-3, s)**


cold start 2 s

| App | CLU | F6 | Heu | B* | RL | lowest |
|---|---|---|---|---|---|---|
| ML | 0.68 | 0.69 | 6.72 | 1.72 | 3.21 | CLU |
| MapReduce | 32.53 | 1.01 | 13.32 | 2.90 | 9.06 | F6 |
| Video | 26.75 | 23.98 | 25.65 | 41.28 | 27.28 | F6 |
| ExCamera | 136.27 | 85.66 | 119.15 | 122.01 | 121.38 | F6 |

cold start 5 s

| App | CLU | F6 | Heu | B* | RL | lowest |
|---|---|---|---|---|---|---|
| ML | 0.82 | 0.69 | 19.58 | 2.05 | 10.29 | F6 |
| MapReduce | 334.66 | 1.01 | 36.44 | 4.08 | 147.21 | F6 |
| Video | 33.08 | 23.98 | 32.39 | 50.21 | 28.61 | F6 |
| ExCamera | 150.16 | 85.75 | 141.95 | 128.52 | 129.72 | F6 |

cold start 10 s

| App | CLU | F6 | Heu | B* | RL | lowest |
|---|---|---|---|---|---|---|
| ML | 1.36 | 0.69 | 41.36 | 3.31 | 58.54 | F6 |
| MapReduce | 904.58 | 1.01 | 71.85 | 5.97 | 248.78 | F6 |
| Video | 44.67 | 24.00 | 50.36 | 79.16 | 37.86 | F6 |
| ExCamera | 160.47 | 85.95 | 206.55 | 153.77 | 146.03 | F6 |

**Lowest P99 of the five systems, count over the cells of a condition**

| Condition | CLU | F6 | Heu | B* | RL | cells |
|---|---|---|---|---|---|---|
| cold start 2 s | 3 | 9 | 0 | 0 | 0 | 12 |
| cold start 5 s | 1 | 11 | 0 | 0 | 0 | 12 |
| cold start 10 s | 0 | 12 | 0 | 0 | 0 | 12 |

**CLU's cold starts and escalations against the duration (descriptive)**

Cold starts: total of the run incl. the warm-up, mean of seeds; 'cold-mode decisions' = decisions where CLU chose cold scaling (all seeds); per request = divided by the requests of the run. Measured-duration values (0.22-0.34 s) are the live cell of Stage 1 (R4).

| App | duration | cold starts (CLU) | cold-mode decisions per request | escalations per request | predicted miss share | real miss share |
|---|---|---|---|---|---|---|
| ML | measured | 3 | 0.001 | 0.004 | 0.0% | 0.2% |
| ML | 2 s | 0 | 0.002 | 0.010 | 0.0% | 0.6% |
| ML | 5 s | 0 | 0.005 | 0.030 | 0.0% | 1.2% |
| ML | 10 s | 2 | 0.007 | 0.036 | 0.0% | 2.8% |
| MapReduce | measured | 2,118 | 0.122 | 0.712 | 0.0% | 4.1% |
| MapReduce | 2 s | 20,750 | 4.149 | 21.756 | 23.7% | 56.5% |
| MapReduce | 5 s | 20,468 | 8.323 | 43.111 | 60.1% | 100.0% |
| MapReduce | 10 s | 10,671 | 6.639 | 34.865 | 44.4% | 100.0% |
| Video | measured | 224 | 0.132 | 0.352 | 0.9% | 8.2% |
| Video | 2 s | 516 | 0.255 | 0.687 | 4.5% | 9.4% |
| Video | 5 s | 956 | 0.500 | 1.219 | 8.5% | 19.0% |
| Video | 10 s | 672 | 0.551 | 1.390 | 1.5% | 24.8% |
| ExCamera | measured | 509 | 0.961 | 25.235 | 22.5% | 36.0% |
| ExCamera | 2 s | 616 | 1.110 | 26.683 | 19.6% | 40.6% |
| ExCamera | 5 s | 321 | 1.069 | 24.312 | 13.6% | 36.4% |
| ExCamera | 10 s | 338 | 1.034 | 20.326 | 7.0% | 34.5% |

### Stage 2: R7. 1000Genome (10 nodes, no peak cap; ML cell's window)

These runs hold 54-88 requests, so the P99 is set by one or two requests: read the intervals as wide, no ranking is claimed.

**Per cell: P99 / average makespan (s)**

| Load | seed | requests | CLU | F6 | Heu | B* | RL | lowest P99 |
|---|---|---|---|---|---|---|---|---|
| load 0.5 | 1 | 54 | 511.2 / 326.1 | 470.5 / 323.4 | 666.2 / 339.7 | 435.3 / 322.0 | 505.7 / 297.7 | B* |
| load 0.5 | 2 | 56 | 433.2 / 317.1 | 533.2 / 302.4 | 875.2 / 370.0 | 368.3 / 288.9 | 462.3 / 290.7 | B* |
| load 0.5 | 3 | 45 | 455.0 / 364.9 | 312.6 / 263.9 | 397.7 / 280.6 | 284.5 / 262.1 | 518.7 / 294.2 | B* |
| load 0.7 | 1 | 80 | 1239.0 / 502.7 | 564.3 / 432.6 | 3220.2 / 831.0 | 814.8 / 547.5 | 790.8 / 400.4 | F6 |
| load 0.7 | 2 | 62 | 464.1 / 346.9 | 332.3 / 268.9 | 613.1 / 307.5 | 314.5 / 277.4 | 486.2 / 296.7 | B* |
| load 0.7 | 3 | 60 | 434.6 / 312.8 | 312.1 / 266.3 | 435.3 / 296.5 | 292.8 / 269.3 | 447.5 / 291.5 | B* |
| load 0.9 | 1 | 88 | 1438.8 / 522.4 | 645.3 / 499.0 | 1591.3 / 653.5 | 1062.9 / 702.2 | 747.9 / 441.6 | F6 |
| load 0.9 | 2 | 71 | 480.0 / 335.1 | 515.8 / 337.6 | 1644.2 / 485.3 | 345.4 / 295.0 | 491.9 / 313.4 | B* |
| load 0.9 | 3 | 83 | 556.3 / 359.3 | 404.2 / 283.2 | 1740.2 / 490.5 | 483.2 / 356.7 | 564.3 / 335.0 | F6 |

Lowest P99 of the five systems over the 9 cells: CLU 0, F6 3, Heu 0, B* 6, RL 0.

**Geometric-mean ratio CLU / system over the 9 cells (3 loads x seeds 1-3), bootstrap 95% CI**

| Measure | vs F6 | vs Heu | vs B* | vs RL |
|---|---|---|---|---|
| P99 makespan | 1.36 [1.10, 1.67]; 2/9 | 0.60 [0.44, 0.82]; 8/9 | 1.36 [1.26, 1.47]; 0/9 | 1.09 [0.95, 1.31]; 6/9 |
| average makespan | 1.15 [1.07, 1.24]; 1/9 | 0.88 [0.75, 1.02]; 6/9 | 1.06 [0.95, 1.19]; 2/9 | 1.14 [1.09, 1.18]; 0/9 |

**Mean over seeds 1-3 (s)**

| Load | measure | CLU | F6 | Heu | B* | RL |
|---|---|---|---|---|---|---|
| load 0.5 | P99 | 466.44 | 438.77 | 646.37 | 362.68 | 495.57 |
| load 0.5 | average | 336.07 | 296.58 | 330.07 | 291.02 | 294.20 |
| load 0.7 | P99 | 712.60 | 402.92 | 1422.87 | 474.04 | 574.84 |
| load 0.7 | average | 387.44 | 322.59 | 478.35 | 364.73 | 329.57 |
| load 0.9 | P99 | 825.00 | 521.76 | 1658.59 | 630.49 | 601.37 |
| load 0.9 | average | 405.59 | 373.28 | 543.12 | 451.30 | 363.34 |
