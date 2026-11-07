---
title: "Independent baseline systems under CAP-W1: audit of the Graph-Aware, FaaSPR and HEFT ports, and the protocol"
type: synthesis
created: 2026-11-05
updated: 2026-11-05
status: draft
author: llm
tags: [baselines, capacity-model, faaspr, graph-aware, heft, audit, protocol]
sources:
  - "[[jia-2025-faaspr]]"
bibliography: ../../output/bibtex/references.bib
---

# Independent baseline systems under CAP-W1: audit and protocol

Capacity model: **CAP-W1** throughout. Controller of ours in the comparison: FROZEN-3 (see CLAUDE.md, "Controller versions").
Request (5 Nov 2026): run FaaSPR, Graph-Aware and HEFT as **independent systems** in CAP-W1, "no more fitting to CAP-U",
ports implemented "correct and fair". This page records what the two papers actually specify (read from the full texts on
5 Nov), where the existing ports depart from them, and the protocol. Draft: nothing below has been run.

## 1. What the papers specify

**Graph-Aware** (Liang et al., Future Internet 18:265, 2026; read from the supplied text). An online constructive scheduler: tasks
in topological order, each to `argmax_j s_ij` over the feasible nodes, `s_ij = -a*l_exec - b*l_comm - g*l_cost + h*delta`
(Eq. 21), state updated after every assignment (Algorithm 1). `l_exec = c_i / u_j`, "may be augmented with queueing delay";
`l_comm` sums, over predecessors, data volume over bandwidth plus link latency, along the shortest path; `l_cost = rho_j * c_i`.
`delta` is a bounded residual from encoders `f_w`, `f_r` and "fixed residual-scoring parameters" `w_g`, `b_g` that the paper does
not give. Coefficients: "fixed default values chosen a priori", never stated; Sec. 5.6 sweeps `b` over 0.2-1.1 and `g` over
0.1-0.9, finds `b` the most sensitive (larger is better up to 1.1) and `h` of limited effect. The data-availability statement
names a repository (github.com/CBY-alt/graph-scheduling-edge-cloud); **it returns 404 on 5 Nov 2026** (the owner's only public
repository is a different one), so there is no reference implementation to check against. Its own HEFT-like baseline is "a
dependency-aware heuristic that prioritizes workflow tasks and assigns them according to estimated completion time", after
Topcuoglu et al. The paper has no containers, no cold starts and no placement: it assigns tasks to nodes that exist.

**FaaSPR** (Jia et al., IEEE/ACM ToN 33(4), 2025; read from the PDF, which needs `pdftotext`: the file is password-protected for
other readers). A platform that, at every scaling request (1 min), (a) takes instance counts from the platform's autoscaler
(concurrency = request rate x mean duration), (b) places them with horizontal and vertical grouping plus migration-minimising
priority (Algorithms 1 and 2; `HG_limit = 4`; `AggreFactor` small), workflows one after another in random order, and (c) solves a
**multi-stage LP** over routing paths per workflow: minimise `sum l_i o_i` s.t. coverage `sum_j B_ij o_j >= O_i` (Constraint 1),
capacity `sum_k R_ijk o_k <= alpha * P_ij / t_i` with `alpha = 0.9` (Constraint 2), and a latency threshold `L = l_x` over the
paths sorted by latency (Constraint 3*), `x` the **smallest** index for which the LP is feasible (binary search). Requests
draw a path with probability `o_i / sum o`. Cluster: 8 servers; for larger clusters servers are split in **groups of 8**, each group
placing and routing on its own. Resources are memory-based (0.5-2 GB per instance), which is what CAP-W1 models.

## 2. Audit of the existing ports

Severity: **C** = changes the algorithm, **A** = adaptation forced by our model (documented in the port), **F** = fitted to CAP-U.

| # | Port | Departure | Severity | Action |
|---|------|-----------|----------|--------|
| G1 | `GraphAware` | `beta = 4`, chosen on development cases (`graphaware_sweep.py`, CAP-U) | **F** | remove; `alpha = 1`, `beta = 1.1` (top of the paper's own sweep), no per-scenario tuning |
| G2 | `GraphAware` | `eta = 0`, residual term dropped | A | keep: encoders and weights unspecified; the paper finds `eta` of limited effect. Stated in every table note |
| G3 | `GraphAware` | `gamma = 0` (no node prices) | A | keep: `l_cost` is constant across candidates and drops out |
| G4 | `GraphAware` | the layout is not the paper's concern; the earlier "standalone" arm ran on a static NSGA-II layout | A | see protocol, substrate S-P and S-S |
| H1 | `heft_like` | no insertion-based slot search; availability from the live start-time estimate plus this plan's own work | A | keep, document; HEFT is a reference, not the contribution |
| P1 | `faaspr_placement` | **equal-size slots only**: a group "fits" if it fits the free slot count | **C** | weighted port: `f.resource = fw[f]`, `R_j = ecc_j`, capacity in `sc.fw` units (the paper's own memory model) |
| P2 | `faaspr_placement` | counts come from our sizing and always fill the slot budget | **C** | FaaSPR's own scaler (`ceil(rate x duration)`), elastic: slots may stay empty |
| P3 | `faaspr_placement` | replication floor (>= 2 hosts) added after a CAP-U storage deadlock | A / F | keep as a documented adaptation only if the storage deadlock recurs under CAP-W1; report the count of repairs either way |
| P4 | `faaspr_placement` | edge weight uses the network-average hop count | A | keep (the paper gives no formula beyond "average data size of the last 1000 invocations") |
| R1 | `FaaSPRRouter` | threshold is `theta x best latency` from an 8-value grid, chosen by smallest slack | **C** | exact Constraint 3*: sort paths by latency, binary search the smallest feasible `x` |
| R2 | `FaaSPRRouter` | one LP shared by all workflows | A | the paper solves one LP per workflow with its own instances; here functions are shared, so split each function's capacity over the workflows that use it (as the placement split does), then one LP per workflow, as in the paper |
| R3 | `FaaSPRRouter` | sampled paths (60-300 per workflow) instead of all paths | A | exhaustive enumeration is impossible here (about 36 hosts per function in the start layout, 2-19 tasks per workflow). Keep sampling, add the paper's own reduction (instances placed together), and **measure sufficiency**: results at 60, 300 and 1,500 paths per workflow |
| R4 | `FaaSPRRouter` | no server groups of 8 | A | the paper's scalability device; with 80 edge nodes arbitrary groups would split the topology. Open (see section 4) |
| R5 | `FaaSPRRouter` | per-task repair when the drawn node lacks input storage (our A-23 budget; the paper has none) | A | keep, and report `n_pure` and repaired-task share per case; a high repaired share means the port is not running FaaSPR's routing |
| S1 | both | all earlier FaaSPR runs were swap-ins into our controller (our sizing, our re-layout, our moves) | **C** | the independent system has none of ours: its own scaler, placement and routing, no request moves, FIFO queues |
| S2 | all | tuning and constants fitted on CAP-U development cases | **F** | none carried over; see protocol |

No departure of type **C** is accepted silently: each is fixed before any run, and each **A** is printed under every result table.

## 3. Protocol (draft; to be frozen before the first run)

**Systems** (all CAP-W1, same scenarios, arrivals, seeds and initial layout where one is needed):
1. **FROZEN-3** (ours, the paper's controller).
2. **FaaSPR**: stock autoscaler (section 4), weighted placement, per-workflow multi-stage LP routing, no request moves.
3. **Graph-Aware** on substrate S-P (below), constants from the paper (G1-G3).
4. **HEFT** on the same substrate.
5. Already available in CAP-W1 and re-used: B*, RL, textbook stack.

**Substrate for scheduler-only systems.** Graph-Aware and HEFT assign tasks to nodes and say nothing about containers. Two arms:
S-P (platform): a stock autoscaler every 60 s (HPA sizing, `ceil(load / 0.8)`) and our data-affinity placement, the same as the
textbook stack, but with **no** request mover and FIFO queues; S-S (static): the NSGA-II start layout only, no re-layout (the
as-published reading). S-P is the primary reading; S-S is reported beside it.

**Fitting.** None on CAP-U. Constants are the papers' own (G1, `alpha = 0.9`, `HG_limit = 4`, scaling interval 60 s). Where a paper is
silent, the value is written here before the run and is not tuned. FROZEN-3 itself was tuned on CAP-U development cases; this is stated
in the table note and is a known advantage of the proposed system, not of the baselines.

**Cases.** Development seeds 1-3 (18 cases) are used to **debug** the ports (health checks, sufficiency, no result reading against
FROZEN-3); results are reported on **held-out seeds 7-10** (scenarios in `results/d1_headroom`, weighted and normalised exactly as
`capw1_light.py prep`), F1/F2 x rho 0.5/0.7/0.85, 24 cases.

**Health checks before any full run** (each reported, none tuned): FaaSPR LP slack share, repaired-task share, unplanned requests, solve time;
Graph-Aware and HEFT parked requests; every run passes `check_invariants()`.

**Reading** (pre-registered): per case P99 makespan ratio system / FROZEN-3; geometric mean with a bootstrap interval over case
log-ratios (10,000 resamples, seed 0); wins out of 24. No pass/fail bar is attached: the table is the result. A system that runs
into its health check (e.g. more than 5% of tasks repaired, FaaSPR) is reported as such, with its P99, and is not silently dropped.

## 4. Decisions (5 Nov 2026, user) and implementation status

User decisions: (1) Graph-Aware and HEFT on **both** substrates, S-P primary; (2) FaaSPR keeps sampled paths with a **sufficiency check** (60, 300, 1,500 paths per workflow); (3) results reported on **held-out seeds 7-10**, development seeds 1-3 for debugging only.

Implemented (all new code; the CAP-U versions are untouched, results under `results/faaspr_grid`, `results/graphaware_grid` remain reproducible):
- `dfps/controllers.py::faaspr_placement_w`: weighted FaaSPR placement (P1). Diagnostics in `FAASPR_W_DIAG` (instances that fitted nowhere, rescues).
- `dfps/dispatchers.py::FaaSPRRouterPaper`: per-workflow LPs, exact Constraint 3* with binary search on `x`, capacity split over workflows, multiplicity-aware load (R1, R2). In-run counters for the health checks.
- `GraphAware` default `beta = 1.1` (G1).
- `output/data-analysis/capw1_independent.py`: arms `faaspr`, `ga_p`, `heft_p`, `ga_s`, `heft_s`; no request mover, FIFO queues; each result is tagged `system`, `mover: none`, `queue: FIFO`, CAP-W1.

Two decisions taken while implementing, both from the papers, neither from CAP-U results:
- **Common stock autoscaler.** FaaSPR's own scaler is "concurrency = rate x duration", but the paper adds that platforms "deploy more instances than concurrency". A literal `ceil(concurrency)` left no headroom under the paper's own alpha = 0.9 capacity cap and the LP was infeasible. All independent systems that need counts (FaaSPR, S-P) therefore use the **same stock autoscaler as the textbook stack**: HPA sizing `ceil(load / 0.8)`, 30 s past window, slot budget filled by demand, re-evaluated every 60 s. FaaSPR's router uses the same 30 s rate estimate (the paper feeds one prediction to both placement and routing).
- **Instance that fits nowhere.** Weighted packing can leave a function without an instance (fragmentation). The simulator requires one per function; the port then takes the room of one instance of a function that has several and counts it (`rescued`). Skipped instances are counted (`shortfall`).

Smoke-test health (F1 rho 0.7 seed 1, development case, 400 s; read as health, not as a result): all five arms run to completion and pass `check_invariants()`. FaaSPR: workflow LPs infeasible at the paper's alpha = 0.9 in 1-5 of 15 workflows in most windows and in all 15 during the one overload burst (t = 180 s, uncovered share 0.56), handled by the slack in adaptation (b); 20% of requests had at least one task repaired for node storage, 5% of requests had an unplannable task. FaaSPR concentrates instances, and our per-node input-state storage budget (no counterpart in the paper) is what the repair and the parked requests respond to. These counts are printed in every result table.

## 5. Path-sufficiency check (pre-registered 5 Nov 2026, before any run; user go-ahead 5 Nov)

**Question.** Is FaaSPR's routing handicapped by sampling its paths (R3)? **Design.** FaaSPR (`faaspr` arm, FP-2), full length (900 s), three development
cases chosen to span load and family before running: F1 rho 0.7 seed 1, F2 rho 0.7 seed 2, F1 rho 0.85 seed 3; 60, 300 and 1,500 sampled paths per
workflow, same scenario, layout, arrivals and seeds (path sampling uses its own seeded generator). Nine runs, CAP-W1, results in
`results/capW1_suff/p{n}/`. Development cases: nothing is compared with FROZEN-3.
**Reading (descriptive, three cases cannot carry an interval).** Per case P99 at 60 and 300 relative to 1,500; the mean log-ratio per path count; the
workflow-LP slack share, repaired-request share, unplanned share and solve time per path count. **Decision rule, fixed now:** 300 paths are kept for the
held-out run if the geometric mean of P99(300) / P99(1,500) is within 3% of 1 (the run-to-run noise floor is about 1.5% per run, see memory) and no case
differs by more than 10%; otherwise 1,500 paths are used for the held-out run, at the cost of longer solves. 60 paths are reported, not used. The check bounds
the sampling error of the routing; it does not show equivalence to exhaustive enumeration (stays open, section 6).

### Result of the sufficiency check (5 Nov 2026; nine runs, no errors)

| Case | Paths | P99 (s) | Avg (s) | LPs needing slack | Requests with a repaired task | Requests with an unplannable task | Solve (ms) |
|---|---|---|---|---|---|---|---|
| F1 rho 0.7 s1 | 60 / 300 / 1,500 | 443 / 304 / 440 | 106 / 86 / 95 | 0.49 / 0.19 / 0.26 | 0.14 / 0.11 / 0.14 | 0.03 / 0.03 / 0.03 | 548 / 3,217 / 15,541 |
| F2 rho 0.7 s2 | 60 / 300 / 1,500 | 745 / 850 / 849 | 231 / 211 / 215 | 0.78 / 0.67 / 0.70 | 0.57 / 0.57 / 0.58 | 0.32 / 0.30 / 0.33 | 580 / 3,271 / 16,030 |
| F1 rho 0.85 s3 | 60 / 300 / 1,500 | 498 / 788 / 613 | 135 / 136 / 134 | 0.80 / 0.75 / 0.74 | 0.21 / 0.15 / 0.18 | 0.16 / 0.14 / 0.16 | 377 / 2,335 / 13,020 |

P99(300) / P99(1,500): 0.692, 1.002, 1.285, geometric mean 0.962; P99(60) / P99(1,500): 1.009, 0.878, 0.812, geometric mean 0.896.
**Decision by the rule fixed in advance: 1,500 paths for the held-out run** (the geometric mean is within 3%, but two cases differ by more than 10%).

What the table says beyond the rule: (1) the LP slack, repaired and unplannable shares do **not** fall as paths are added, so sampling is not what makes the routing
infeasible; (2) P99 is not monotone in the path count (case 1: 443, 304, 440), so a single FaaSPR run carries noise of tens of percent, far above the 1.5%
floor of our own controller, and only the 24-case aggregate can be read; (3) the unplannable requests are a storage effect: in the F2 diagnostic 4,312 of 4,595
unplannable tasks were for a function whose hosts all had no free input-state storage. FaaSPR's layout is concentrated (8.4 hosts per function and 3.2 distinct functions per node,
against 26.2 and 9.8 under S-P, with up to 8 instances of one function on a node), so a backlog of one function fills the few nodes that hold it. Our per-node input-state budget has no
counterpart in the paper (it uses a remote store). On this F2 case FaaSPR (P99 850) was still ahead of Graph-Aware on S-P (1,480); both have no request mover.

## 6. Frozen protocol for the held-out run (5 Nov 2026, written before the run; user go-ahead 5 Nov)

**Cases.** F1/F2 x rho 0.5/0.7/0.85 x seeds 7, 8, 9, 10 = 24 held-out cases; scenarios from `results/d1_headroom`, weighted and normalised as `capw1_light.py prep` (the
24 start layouts were rebuilt on 5 Nov with the memory-safe prep in `capw1_independent.py`; same arithmetic). 900 s, warm-up 60 s, CAP-W1.
**Ten arms, same scenario, start layout, arrivals and seeds per case.** `frozen3` (ours; transfer_only router, gain-ordered mover, criticality queue order), `stack`
(textbook stack), `B_STAR`, `RL` (CAP-W1 policy), and the independent systems `faaspr` (**1,500 paths**, section 5), `faaspr_rs` (identical, per-node input-state storage relaxed x1000:
a sensitivity arm, since the paper has a remote store and no per-node budget), `ga_p`, `heft_p` (stock autoscaler + our affinity placement, no mover, FIFO), `ga_s`, `heft_s` (static start
layout). Graph-Aware alpha 1, beta 1.1; FaaSPR alpha 0.9, `HG_limit` 4, 60 s scaling interval, 30 s rate window; no value tuned on any scenario.
**Reading (as in section 3, unchanged).** Per case P99 makespan of each system over FROZEN-3; geometric mean with a bootstrap interval over case log-ratios (10,000
resamples, seed 0), wins out of 24, split by load; mean P99. No pass/fail bar. FaaSPR is reported with its in-run health counters (LP slack share, repaired and unplannable
requests, parked share) beside the table, for `faaspr` and `faaspr_rs` both; `faaspr_rs` is labelled a sensitivity arm and is not the FaaSPR headline row. `faaspr` is.
**Known advantages and limits, printed under the table.** FROZEN-3's own constants were tuned on CAP-U development cases; the baselines use the papers' values. The independent
systems have no request mover, which our controller's two loops make the dominant mechanism (slide: x13.7 and x8.1); a P99 gap to them is therefore not evidence about their
placement or routing alone. FaaSPR's paths are sampled. Graph-Aware has no reference code (the repository named in the paper returns 404). `RL` was trained on CAP-W1 development scenarios.
**Run order and resumption.** `python output/data-analysis/capw1_heldout.py run 4` (resumable; unreadable result files are removed first), 4 workers at below-normal priority; report with `report`.

### Run log of the held-out run (5 Nov 2026)
- **First pass: 224 of 240 runs finished; 16 FaaSPR runs crashed** (8 cases in each of `faaspr` and `faaspr_rs`: F1 rho 0.85 seed 7; F2 rho 0.5 seeds 7, 8; F2 rho 0.7 seeds 7, 8; F2 rho 0.85 seeds 7, 8, 9).
  Both arms crashed on the same cases because the first re-layout (60 s) is identical in the two. Cause, found by reproducing F2 rho 0.5 seed 7: `faaspr_placement_w` returned a
  layout with **no instance of the heaviest function** (weight 3.27 after load normalisation, median 1.41), and `Sim.apply_placement` requires one instance of every function. The
  weighted packing leaves free room in small pieces; the rescue step (evict one instance of a multi-instance function on a node) found no node where one eviction freed enough room.
- **Fix, a change to the port, not to the protocol.** The rescue now falls back to evicting several instances on one node (fewest evictions, then least weight; most-replicated
  functions first; never a function's last instance) when the single-eviction rule finds nothing. The single-eviction rule runs first and is unchanged, so every run that did not
  crash is bit-identical: none of the 32 finished FaaSPR runs ever had a lost function (a lost function crashes the run), so the new branch was never reached in them.
  Counters `rescued_multi` and `evicted` record how often the new branch fires. On the reproduction case it fired 3 times in 6 re-layouts (6 instances evicted), and the run completed.
- **Per-run counters.** `placement_diag` in the result files was a per-process counter and accumulated over the jobs a pool worker ran; the 32 runs of the first pass carry such
  cumulative values and must not be read as per-run. The report does not use it. From the rerun on the counters are reset at the start of each run.
- The 16 crashed runs were re-run with the fixed code; the other 224 results were left as they were. All 240 runs then finished with no error file.

### Result (5 Nov 2026; 240 runs, 24 cases per system; report in `results/capw1_heldout_report.txt`)
P99 makespan ratio system / FROZEN-3, geometric mean [95% bootstrap interval over case log-ratios], wins of FROZEN-3 out of 24, by load, and mean P99:

| system | all cases | FROZEN-3 wins | rho 0.5 | rho 0.7 | rho 0.85 | mean P99 (s) |
|---|---|---|---|---|---|---|
| stack (textbook stack) | 1.24 [1.20, 1.29] | 24/24 | 1.20 | 1.24 | 1.28 | 282 |
| RL | 2.96 [2.36, 3.63] | 23/24 | 2.70 | 3.12 | 3.09 | 570 |
| B* | 3.15 [2.40, 4.02] | 21/24 | 2.43 | 3.61 | 3.57 | 637 |
| FaaSPR (`faaspr`, headline) | 3.93 [3.22, 4.77] | 24/24 | 3.14 | 4.64 | 4.16 | 787 |
| FaaSPR, storage relaxed (`faaspr_rs`, sensitivity) | 4.77 [3.83, 5.93] | 24/24 | 3.65 | 5.96 | 5.01 | 1,002 |
| Graph-Aware on S-P, v2 tie-break (`ga_p2`) | 5.87 [4.96, 6.90] | 24/24 | 5.34 | 6.64 | 5.70 | 1,121 |
| HEFT-like on S-P, v2 (`heft_p2`) | 6.87 [5.50, 8.45] | 24/24 | 6.29 | 8.17 | 6.31 | 1,307 |
| Graph-Aware on S-S, v2 (`ga_s2`) | 28.55 [21.03, 38.09] | 24/24 | 28.28 | 30.66 | 26.84 | 5,682 |
| HEFT-like on S-S, v2 (`heft_s2`) | 27.11 [19.77, 36.32] | 24/24 | 25.57 | 30.40 | 25.64 | 5,393 |
| *v1, superseded:* Graph-Aware on S-P (`ga_p`) | 6.07 [5.11, 7.19] | 24/24 | 5.59 | 6.70 | 5.99 | 1,162 |
| *v1, superseded:* HEFT-like on S-P (`heft_p`) | 14.93 [11.68, 19.18] | 24/24 | 18.33 | 15.65 | 11.60 | 2,807 |
| *v1, superseded:* Graph-Aware on S-S (`ga_s`) | 29.95 [22.14, 40.06] | 24/24 | 30.38 | 31.34 | 28.21 | 5,975 |
| *v1, superseded:* HEFT-like on S-S (`heft_s`) | 49.18 [38.65, 62.72] | 24/24 | 56.38 | 53.12 | 39.70 | 9,889 |
| FROZEN-3 | 1 | | | | | 216.5 |

> **After the audit of section 7 the four Graph-Aware / HEFT-like arms were re-run with a neutral tie-break (v2); the v2 rows are the ones to quote, the v1 rows are kept for the record.** The v1 HEFT-like rows (14.9, 49.2) were inflated by exact ties resolved to the lowest node index.
> Paired v2 / v1 P99 ratio over the 24 cases: HEFT-like on S-P 0.46 [0.39, 0.53] (lower in 24/24), HEFT-like on S-S 0.55 [0.45, 0.66] (24/24); Graph-Aware on S-P 0.97 [0.94, 1.00] (17/24), Graph-Aware on S-S 0.95 [0.93, 0.98] (18/24), i.e. a 3-5% effect for Graph-Aware.

FaaSPR health (in-run counters, mean over the 24 cases): `faaspr` slack-LP share 0.45, repaired requests 0.22, unplannable 0.10, parked/arrived 0.50; `faaspr_rs` slack-LP share 0.34,
repaired 0.00, unplannable 0.00, parked 0.00.

**Reading (frozen; no pass/fail bar).** FROZEN-3 has the lower P99 in every case against all independent systems and the textbook stack, in 21 of 24 against B* and 23 of 24 against RL.
Every interval excludes 1. Three things the table does not say: (1) the independent systems have no request mover and FROZEN-3's constants were tuned on CAP-U cases, so the gaps are not
evidence about their placement or routing alone; (2) relaxing the storage budget did not help FaaSPR (4.77 against 3.93; the intervals overlap), so the per-node storage rule is not what holds the headline
row back, even though it explains its parked and unplannable requests; (3) the LP is infeasible at alpha = 0.9 in 34-45% of solves, so the port runs well outside the regime the paper evaluates, and the slack adaptation (b) decides much of its routing.
With v2, the order among the independent systems is FaaSPR (3.9), then Graph-Aware and HEFT-like on S-P (5.9 and 6.9), then both on S-S (28.6 and 27.1). Exploratory paired contrasts, not part of the frozen reading: HEFT-like / Graph-Aware on S-P 1.17 [1.08, 1.28] (HEFT-like lower in 5/24), on S-S 0.95 [0.89, 1.01] (10/24), so Graph-Aware is ahead of HEFT-like on the better substrate and the two cannot be told apart on the static one; FaaSPR / Graph-Aware(S-P) 0.67 [0.59, 0.77] (20/24), FaaSPR / HEFT-like(S-P) 0.57 [0.51, 0.65] (23/24). The paper's claim that Graph-Aware beats a HEFT-like scheduler is reproduced on S-P (modestly) and not on S-S. Substrate matters more than the dispatcher: S-S is about 4-5 times worse than S-P for both, because the static layout never adapts.

## 7. Audit of the Graph-Aware and FaaSPR ports against the papers (5 Nov 2026, after the held-out run; user request: "make sure their implementation is fair")
The two papers were re-read (Graph-Aware: Secs. 3-5, with Eqs. 11 and 14-21 read from the PDF because the markdown copy lost its equations; Eqs. 22-24, the argmax, commit and state update, from the prose; FaaSPR: Secs. IV-VII) and
each element compared with the code. Held-out cases were not used for any check below; development cases (seeds 1-3) and the one tie test case are named where used. Nothing was re-run for the table.

**Graph-Aware (`dfps/dispatchers.py::GraphAware`).**

| paper element | port | status |
|---|---|---|
| online, tasks in topological order, argmax of s_ij, state updated after each assignment (Alg. 1, Sec. 4.4) | `_plan_tasks` + per-plan work counter `extra` | match |
| s = -alpha l_exec - beta l_comm - gamma l_cost + eta delta | alpha 1, beta 1.1, gamma 0, eta 0 | adaptation: no node prices in our model (gamma); delta's encoders and fixed weights are not given, and the paper's Sec. 5.6 finds eta has "only a limited effect" |
| l_exec = c_i / u_j, "augmented with queueing delay" | DFPS start-time estimate (`fst_vec`, queue-aware) plus work already planned there | adaptation; the same queue information DFPS itself uses |
| l_comm over predecessors, shortest path by latency | hops x (epd + d/bw), epd = 0 | adaptation. A root task also pays transfer from the request origin; the paper's Eq. 16 sums over predecessors only, so this gives the port slightly more information |
| normalisation "within the current scheduling instance" | min-max over the candidate set of each decision | one of several readings; not tested |
| candidate set R(v): nodes with enough CPU and memory | nodes holding a container of the function with free input storage | forced by the problem: the container layout is not the scheduler's decision (S-P / S-S supply it) |
| coefficients "fixed default values chosen a priori" | no tuning on any scenario; beta 1.1 is the top of the paper's own sweep | match with the text |
| tie-breaking | not specified; port resolves exact ties to the **lowest node index** | **defect of the port**, see below |

*Tie test (F2 rho 0.7 seed 7, 450 s, Graph-Aware on S-P).* 10.6% of decisions end in an exact tie (2.3 candidates on average); the 8 busiest nodes receive 15.9% of the tasks. With ties broken by
lowest queue estimate, then at random: 9.7% ties, 15.8%, P99 1,026 s to 1,125 s. One run, inside the run-to-run noise: **no measurable effect for Graph-Aware.**

**HEFT-like (`heft_like`): material.** Its estimate is max(node-ready, data-ready) + run time. Whenever data-ready is the larger, the queue term drops out and every node at the same hop distance ties.
On the same case 85-88% of decisions are exact ties among 19-26 candidates, all resolved to the lowest index; the 8 busiest nodes receive 33% of the tasks. With the same tie-break as above: share 17.5%,
**P99 5,763 s to 1,783 s (a factor 3.2)**. The v1 HEFT rows (14.9, 49.2) were therefore not valid as HEFT's performance. Re-run with v2 on all 24 held-out cases (below): 6.9 and 27.1, a factor 2.2 and 1.8 below v1 on the geometric mean (the one-case factor of 3.2 was larger).

**FaaSPR (`faaspr_placement_w`, `FaaSPRRouterPaper`).**

| paper element | port | status |
|---|---|---|
| Alg. 1: vertical groups merged along the critical path in descending edge weight while the placement stays feasible; horizontal groups, at least HG_limit = 4 instances per function, at most one per server | `faaspr_placement_w` | match |
| Alg. 2: priority = reused instances x cold-start time + neighbour-edge weight x share of the neighbour on the server + Aggre_factor x instances there; infeasible = -1 | `priority` | match. `aggre` = 1e-3 against edge weights of 1-5 s and cold starts of 2-10 s, i.e. a pure tie-break as intended (measured) |
| several workflows: placed in random order, capacity updated in between | `rng.permutation` | match |
| Constraints 1-3*, objective min sum l_k o_k, smallest feasible x by binary search, weighted random path, alpha = 0.9, one LP per workflow | `FaaSPRRouterPaper._solve` | match |
| platform scaler decides the instance counts | stock HPA sizing, as for every independent system | adaptation |
| functions belong to one workflow | counts and capacity split over workflows in proportion to rate x occurrences | adaptation (our functions are shared by up to 15 workflows) |
| all routing paths enumerated; servers grouped by 8 | 1,500 sampled paths per workflow; one group of 80 servers | adaptation (sufficiency check, section 5) |
| LP always feasible at x = r | penalised slack when it is not; per-task storage repair; rescue evictions when weighted packing loses a function | adaptation, health counters reported |
| rate: "predict ... based on the historical trace" | last 30 s of arrivals | free parameter, tested below |

Three decisions of the port that could have disadvantaged FaaSPR were tested on the development cases F1 rho 0.7 s1, F2 rho 0.7 s2, F1 rho 0.85 s3 (900 s, 1,500 paths; single runs, FaaSPR's run-to-run noise is tens of percent):
- **Cluster fill.** The independent arms size with `_fit_counts`: the autoscaler's counts are a floor and the remaining capacity is filled in proportion to demand, so FaaSPR's bundle packing runs on a cluster packed to 100%
  (it then drops 600-700 instances per run). Its paper has a platform that scales to demand. Arm `faaspr_el` (counts not filled): P99 437 / 544 / 1,594 s against 440 / 849 / 613 s, dropped instances 114-486 per run,
  LP infeasibility unchanged. Mixed sign: **no evidence that the fill holds FaaSPR back.** (The `faaspr_placement_w` docstring says FaaSPR does not fill the cluster; that is true of the function, not of the arm.)
- **Rate window** 60 s (the paper's scaling interval) and 120 s (the autoscaler's own window) against 30 s: P99 394 / 1,046 / 605 s and 477 / 1,097 / 985 s against 440 / 849 / 613 s; the share of solves needing slack did not fall.
  **The 30 s window is not a handicap.**
- **`aggre`** (above): fine.

*Why the LP is infeasible so often (73-96% of solves at rho >= 0.7).* Not a port error that I could find: the overall arrival rate is smooth (peak/mean 1.27 per 30 s window, the paper's trace 1.3), but **per workflow** the
30 s rate has a median peak/mean of 3.75 (90th percentile 7.0) with about 3 arrivals per window, and with alpha = 0.9 a window more than about 1.1x above the sizing rate cannot be covered. The paper evaluates one application on 8 servers
at about 3.4 req/s. FaaSPR is therefore run outside the regime it was built for; that is a property of the workload, reported beside the table, not something the port can fix without inventing a rate predictor.

**Tie-break v2 (decision of the user, 5 Nov 2026: implement and re-run the four Graph-Aware / HEFT-like arms).** A *tie-break* is the rule that chooses between candidates whose score is exactly equal. v1 took the first
(lowest node index); v2 (`dfps/dispatchers.py::break_ties`) takes, among the tied candidates, the one with the lowest queue estimate (the start-time estimate the scores themselves use), and a random one if several still tie.
New arms `ga_p2`, `heft_p2`, `ga_s2`, `heft_s2` (`capw1_independent.py`); the v1 arms are unchanged (a re-run of `heft_p` and `ga_p` on F1 rho 0.5 seed 7 reproduced the stored results exactly) and stay in the
results beside v2, so both are reported. Nothing else changed: same scenarios, seeds, substrates, coefficients. The rule was fixed after seeing the effect on one case (HEFT-like, F2 rho 0.7 seed 7), so it is a
bug fix of the port, not a tuned setting; it is not tuned further.

**Verdict.** Graph-Aware: structure and score as in the paper, with the adaptations listed; the tie-break moves it by 3-5% over the 24 cases (paired v2/v1 0.97 and 0.95), small but not zero. FaaSPR: placement and routing follow the paper's algorithms; the adaptations are listed and the three that could
have mattered were tested without finding a handicap. HEFT-like: a real tie-break defect (3.2x on the test case); re-run on all 24 held-out cases with v2, which halves its P99 (ratios 0.46 and 0.55); the v2 rows replace the v1 rows. All systems still lack a request mover and FROZEN-3's constants were tuned on CAP-U (section 6).
Audit files: `results/capW1_audit_ties*`, `capW1_audit_el`, `capW1_audit_win60`, `capW1_audit_win120`; the `faaspr_el` arm and the optional window argument were added to `capw1_independent.py`.

## 8. On-demand (elastic) re-comparison on the held-out set (protocol, written before the run; user request 6 Nov 2026)

*Why.* Every system in section 6 ran on a cluster that its sizing rule fills to about 100% (the scaler's counts are a floor, the leftover is spread over the functions), which is FROZEN-3's design ("fixed slot budget") but not how a
platform that scales to demand behaves, and not FaaSPR's setting ([[faaspr-paper-setting]]: with equal memory FROZEN-3 still had 0.46x FaaSPR's P99). The user asked whether FROZEN-3 is still better than the baselines when it runs
**on-demand** ("we overlooked this behavior"). *On-demand* here means: each system runs the containers its scaler asks for and memory beyond that stays empty (the `elastic` option; not RL's separate on-demand container model).
*What can scale.* On-demand arms (new): `frozen3_od`, `stack_od`, `ga_p2_od`, `heft_p2_od` (S-P), `faaspr_od`; same scenarios, start layouts, seeds, 900 s / 60 s warm-up, same configurations as in section 6 plus `elastic`;
`stack_od` and the S-P arms keep their data-affinity placement (a flag-gated path in `baseline_layout`, since its elastic branch would otherwise substitute k-median). **Not scaled, by design:** RL (already creates and recycles containers per request),
B* (fixed-budget replacement), the static S-S arms. They are reported as they are and labelled.
*Reading (no pass/fail bar).* (A) every system against `frozen3_od`: P99 ratio per case, geometric mean with a 95% bootstrap interval (10,000 resamples, seed 0), wins, split by load, mean-makespan ratio. (B) `frozen3_od` against the baselines
as already run (filled): the conservative reading, FROZEN-3 with less memory than they have. Also: provisioned memory (time average, share of the cluster) and cold starts per arm.
*Expectation stated in advance, so it can fail.* At rho 0.85 the scaler's need exceeds the cluster (need = rho / 0.8 > 1), the counts are shrunk to the cluster, and on-demand coincides with filled there; any difference should appear at rho 0.5 and 0.7.
*Limits printed under the table.* The independent systems have no request mover; FROZEN-3's constants were tuned on CAP-U with the filled budget, so on-demand is a configuration it was not tuned for; B*, RL and S-S are not on-demand-comparable.

### Result of the on-demand re-comparison (6 Nov 2026; 120 runs, 24 held-out cases, no errors; report in `results/capw1_ondemand_report.txt`)

**A. every scalable system on-demand; ratio = system / FROZEN-3 on-demand** (P99, geometric mean [95% bootstrap CI], FROZEN-3 lower in x/24):

| system | P99 ratio | FROZEN-3 lower | rho 0.5 | rho 0.7 | rho 0.85 | mean-makespan ratio |
|---|---|---|---|---|---|---|
| textbook stack, on-demand | 1.26 [1.19, 1.34] | 23/24 | 1.32 | 1.26 | 1.19 | 1.26 |
| FaaSPR, on-demand | 3.57 [2.81, 4.46] | 24/24 | 3.17 | 3.40 | 4.23 | 2.58 |
| Graph-Aware, S-P, on-demand (v2) | 5.92 [4.90, 7.11] | 24/24 | 5.58 | 6.02 | 6.18 | 4.17 |
| HEFT-like, S-P, on-demand (v2) | 6.46 [5.08, 8.09] | 24/24 | 6.36 | 6.40 | 6.62 | 4.91 |
| RL (on-demand by design) | 2.59 [2.00, 3.29] | 21/24 | 2.08 | 2.75 | 3.04 | 2.20 |
| B* (fixed budget by design) | 2.76 [2.00, 3.72] | 21/24 | 1.87 | 3.19 | 3.52 | 3.43 |
| Graph-Aware / HEFT-like, S-S (static, v2) | 25.0 / 23.7 | 24/24 | | | | |

**B. FROZEN-3 on-demand against the baselines as already run (filled; FROZEN-3 has less memory):** stack 1.09 [1.00, 1.19] (FROZEN-3 lower in 15/24; at rho 0.5 the filled stack is ahead, 0.92), FaaSPR 3.44, Graph-Aware 5.14, HEFT-like 6.02 (24/24 each);
FROZEN-3 filled / FROZEN-3 on-demand 0.88 [0.79, 0.98] (on-demand lower in 4/24).
**FROZEN-3 itself, on-demand over filled:** P99 1.14 [1.03, 1.26], mean makespan 1.17; by load 1.30 (rho 0.5), 1.13 (0.7), 1.01 (0.85); the whole effect is in family F1 (1.30; F2 1.00). Memory used: 65%, 88%, 98% of the cluster (the scaler's
need, as predicted; at rho 0.85 on-demand and filled coincide). Cold starts per run: FROZEN-3, stack, Graph-Aware and HEFT-like all 1,522 filled and 1,255 on-demand (their layouts are set by the same sizing and placement, which depend only on the trace);
FaaSPR 5,271 filled and 4,247 on-demand; B* 10,384; RL 41,377; static layouts 0. The earlier reading that the filled cluster has fewer cold starts because of spare warm containers holds in the paper-setting run but not here.
**Reading.** With every scalable system on-demand FROZEN-3 is still lower than all of them, in 21-24 of 24 cases; the margin over the textbook stack is the same as when both are filled (1.26 against 1.24). The margin FROZEN-3 loses by
running on-demand is about 14% on P99 (30% at rho 0.5), enough that the *filled* textbook stack is roughly level with *on-demand* FROZEN-3 (1.09, interval touching 1). Limits: no request mover in the independent systems; FROZEN-3's constants were
tuned on CAP-U with the filled budget; B*, RL and S-S are not on-demand-comparable and are shown for reference.

### Plan: faster capacity for on-demand FROZEN-3 (6 Nov 2026, written before the runs; user concern)
On-demand removes the spare containers that absorbed demand between two re-layouts, so a rise waits up to 60 s for capacity. Step 1, development cases only (18 cases, seeds 1-3; held-out seeds untouched): `frozen3_od` with a re-layout every 30 s and every 15 s against every 60 s and against filled.
Read: P99 and mean makespan ratios, cold starts, memory share. Step 2, only after step 1: a trigger-based add and shrink between re-layouts (`fast_step` cannot do this: it only converts containers in a full cluster). A faster loop is a change to our controller, and the stock scaler of the baselines stays at 60 s, so any comparison must also run the textbook stack at the same cadence.

**Step 1 result (6 Nov 2026; 36 runs, 18 development cases, no errors; seeds 1-3 only, so nothing here is held-out evidence).** On-demand FROZEN-3 over filled FROZEN-3:

| re-layout every | P99 ratio | rho 0.5 | rho 0.7 | rho 0.85 | mean-makespan ratio | cold starts per run | memory share |
|---|---|---|---|---|---|---|---|
| 60 s | 1.22 [1.16, 1.29] | 1.36 | 1.16 | 1.16 | 1.22 | 1,567 | 0.82 |
| 30 s | 1.15 [1.08, 1.23] | 1.35 | 1.08 | 1.06 | 1.15 | 2,127 | 0.83 |
| 15 s | 1.13 [1.06, 1.21] | 1.31 | 1.06 | 1.04 | 1.12 | 2,470 | 0.83 |

Filled reference: mean P99 121 s, 2,091 cold starts. Paired against 60 s on-demand: 30 s 0.94 [0.92, 0.97] (lower in 14/18), 15 s 0.92 [0.90, 0.95] (16/18). **Reading.** The faster loop recovers most of the loss at rho 0.7 and 0.85 and almost none at rho 0.5; halving the period again adds little and costs 16% more cold starts.
At rho 0.5 the wait for capacity is therefore not the main cause. Untested hypothesis: on-demand runs at about 0.8 utilisation by construction, where filled runs at about 0.5, so the loss there is queueing at the higher utilisation; a trigger would not fix that, a lower utilisation target might. Also: on these development cases rho 0.85 differs from filled at 60 s (1.16, memory 0.96), so the expectation in the protocol that the two coincide there held on the held-out set (1.01) but not here.

**Step 1b, plan (written before the runs; user go-ahead 6 Nov).** On-demand FROZEN-3 at a 30 s period with utilisation targets 0.65 and 0.5 (the sizing rule's ceil(load / target)), 18 development cases, 36 runs. Tests the hypothesis above: if the rho 0.5 loss is queueing at 0.8 utilisation, these targets should remove most of it, at the price of more memory. If they do not, the hypothesis is wrong. Where the target's need exceeds the cluster (target 0.65 at rho 0.7 and above; target 0.5 at every load) the counts are shrunk to the cluster, so those cells approach the filled version.

**Step 1b result (6 Nov 2026; 36 runs, 18 development cases, no errors; not held-out).** On-demand FROZEN-3, re-layout every 30 s, over filled FROZEN-3:

| utilisation target | P99 ratio | rho 0.5 (memory share) | rho 0.7 | rho 0.85 | mean-makespan ratio | cold starts | memory share overall |
|---|---|---|---|---|---|---|---|
| 0.8 (the rule as defined) | 1.15 [1.08, 1.23] | 1.35 (0.64) | 1.08 (0.88) | 1.06 (0.96) | 1.15 | 2,127 | 0.83 |
| 0.65 | 1.03 [0.99, 1.07] | 1.10 (0.78) | 0.96 (0.97) | 1.04 (0.98) | 1.02 | 2,254 | 0.91 |
| 0.5 | 1.00 [0.96, 1.03] | 1.00 (0.95) | 0.96 (0.98) | 1.04 (0.98) | 0.98 | 2,331 | 0.97 |

**Reading.** The hypothesis (the rho 0.5 loss is queueing at 0.8 utilisation) is supported: a lower target removes it, 1.35 to 1.10 at 0.65 and 1.00 at 0.5. But it is bought with memory: at target 0.5 the cluster is 95-98% used at every load, i.e. the filled
version again, and the saving is gone. Target 0.65 is the middle: P99 within 3% of filled overall (interval touching 1) with 91% of the memory, and at rho 0.5 +10% for 78% of the memory (against +35% for 64%). The utilisation target is therefore the knob that trades memory for tail latency; it is
not a free improvement. At rho 0.7 and above the 0.65 and 0.5 needs exceed the cluster and the counts are shrunk to it, so those cells are close to filled by construction. Limits: one period (30 s), development cases, a target chosen after seeing the 0.8 result, so this is a design curve, not evidence for a setting; cold starts rise with a lower target (2,127 to 2,331).
This did not test a trigger between re-layouts; the faster period and the lower target together reach about filled quality, which suggests a trigger would mainly cut cold starts, not latency, at a given memory.

**Step 2, plan: trigger-based add and shrink between re-layouts (written before the runs; user request 6 Nov 2026: "also test trigger based").** New method `O3SimAdjuster.fast_scale`, on-demand only, off unless `fast_scale` is set; the existing `fast_step` cannot do this (it converts containers in a full cluster).
Checked on every request-move tick (4 s), at most one action per 10 s, from a 20 s arrival window, a 120 s window and the live queues; parameters are the existing `fast_step` defaults, none tuned: window 20 s, backlog cleared in 30 s, trigger 1.0 cold start, budget 40 containers per action.
*Add:* a function is in emergency when its queue would take longer than one of its cold starts to drain with today's containers and the short-window sizing, ceil((short-window load + queued work / 30 s) / target), needs more containers than it has; it gets up to the deficit, worst drain first, within the memory that is free (plus what the shrink below releases).
*Shrink:* a function with nothing queued whose count is above 1.25 x the larger of its short-window and long-window need releases the excess (idle containers first). The 1.25 margin is new and was fixed here, before any run.
*Placement:* the data-affinity placement with the new counts, leftover not filled. The slow re-layout continues unchanged and starts from the live layout.
*Arms (18 development cases, 54 runs):* `frozen3_od_fs` (60 s re-layout + trigger), `frozen3_od_e30_fs` (30 s + trigger), `frozen3_od_e30_u65_fs` (30 s, target 0.65, + trigger). Compared with filled, 60 s, 30 s and 30 s / 0.65 without trigger from step 1 and 1b: P99 ratio to filled, mean makespan, cold starts, memory share, and the number of trigger actions.
*Stated in advance:* a trigger helps if it lowers P99 at 0.8 and 0.65 without a large rise in cold starts; it does not help if its gain equals what the 30 s period already gave (1.15) at higher cold starts. In a full cluster (rho 0.85) there is little free memory to add into, so little change is expected there.

**Step 2 result (6 Nov 2026; 54 runs, 18 development cases, no errors; not held-out).** On-demand FROZEN-3 over filled FROZEN-3 (P99 ratio; filled has 2,091 cold starts, mean P99 121 s):

| configuration | P99 ratio | rho 0.5 | rho 0.7 | rho 0.85 | mean-makespan ratio | cold starts | memory share | trigger actions per run |
|---|---|---|---|---|---|---|---|---|
| 60 s, target 0.8 | 1.22 [1.16, 1.29] | 1.36 | 1.16 | 1.16 | 1.22 | 1,567 | 0.82 | 0 |
| 60 s + trigger | **1.07 [1.02, 1.12]** | 1.17 | 0.99 | 1.05 | 1.10 | 2,124 | 0.86 | 57 |
| 30 s, target 0.8 | 1.15 [1.08, 1.23] | 1.35 | 1.08 | 1.06 | 1.15 | 2,127 | 0.83 | 0 |
| 30 s + trigger | 1.05 [0.99, 1.10] | 1.19 | 0.99 | 0.98 | 1.07 | 2,761 | 0.84 | 60 |
| 30 s, target 0.65 | 1.03 [0.99, 1.07] | 1.10 | 0.96 | 1.04 | 1.02 | 2,254 | 0.91 | 0 |
| 30 s, target 0.65 + trigger | **1.00 [0.95, 1.03]** | 1.07 | 0.93 | 0.99 | 1.00 | 2,442 | 0.92 | 47 |

Paired, trigger over the same configuration without it: 60 s 0.87 [0.84, 0.90] (lower in 18/18, cold starts x1.36); 30 s 0.91 [0.88, 0.93] (18/18, x1.30); 30 s at target 0.65 0.96 [0.95, 0.98] (15/18, x1.08).
**Reading against the criteria fixed in advance.** The trigger lowers P99 at both targets, in every case at 0.8, and it beats the faster period at equal cold starts: 60 s + trigger reaches 1.07 with 2,124 cold starts, the 30 s period alone 1.15 with 2,127. So the wait for capacity was part of the loss, and a trigger addresses it better than
a shorter period. It costs cold starts: every trigger configuration is at or above the filled version's 2,091 (the on-demand saving in cold starts is gone), and 30 s + trigger is 32% above it. At 0.8 it recovers about two thirds of the loss for 4 points of extra memory (0.86). At rho 0.5 a loss remains at target 0.8 (1.17); target 0.65 + trigger removes most of it (1.07) at 92% memory.
Limits: development cases and one parameter set (not tuned, but the trigger and the target came after seeing results); cold starts and memory are costs the P99 numbers hide; the baselines' stock scaler has no trigger, so any comparison with them is between our controller with a trigger and theirs without one, which is a property of our design and is to be stated as such.

**Diagnosis of the extra cold starts (6 Nov 2026; 12 runs: 6 development cases, seed 1, with and without the trigger at a 60 s re-layout; script `output/data-analysis/ondemand_steps/diag_cold_sources.py`, which logs every container change with its source).**
Every cold start is a container added, so cold starts = adds exactly (no trigger: 8,986 cold starts = 8,986 slow-loop adds; with trigger: 12,399 against 6,852 + 5,549 = 12,401). Totals over the six cases:

| | cold starts | slow-loop adds | slow-loop removals | trigger adds | trigger removals |
|---|---|---|---|---|---|
| 60 s, no trigger | 8,986 | 8,986 | 12,871 | 0 | 0 |
| 60 s + trigger | 12,399 | 6,852 | 15,625 | 5,549 | 137 |

*Churn between the two loops.* Of the 5,549 containers the trigger added, **3,122 (56%) were removed again by the next re-layouts within 120 s**, and **2,900 (52%) of its adds re-created containers the slow loop had removed within the previous 120 s**.
The trigger's own shrink removed only 137 containers, so the shrink half of the mechanism is almost never used here. The trigger lowered the slow loop's adds by 2,134, so the net extra is 3,413 cold starts, of which the reversed adds (3,122) are nearly all. The cause: the slow loop sizes from the last 30 s of arrivals with no queue term (by design, so that
sizing does not depend on the layout's own quality), so it takes back what the queues needed; the trigger adds it again at the next burst. Consequence: a hold on trigger-added containers (the existing `hold_floor` mechanism, about 120 s) targets the cause directly; this is a hypothesis for the next step, not a result.

**Step 3, plan: hold the trigger's containers (written before the runs; user go-ahead 6 Nov 2026).** The diagnosis shows the slow re-layout taking back 56% of what the trigger added. After a trigger add, the function's new count is a floor for the slow loop for `fast_hold` seconds
(the existing `hold_floor` mechanism, "scale up fast, scale down slowly"). *Implementation note.* In a full cluster `apply_hold_floor` pays for held containers with other functions' slack; in on-demand mode nothing has slack, so it would silently not honour the hold. In on-demand mode the held containers
are now extra (as long as the total fits the cluster; otherwise the old rule applies); the fixed-budget path is unchanged. The trigger's own shrink also respects active holds.
*Arms (18 development cases, 36 runs):* `frozen3_od_fs_h120` and `frozen3_od_fs_h60` (60 s re-layout + trigger + hold of 120 s and of 60 s), against trigger-only (P99 1.07, 2,124 cold starts, memory 0.86), no trigger (1.22, 1,567, 0.82) and filled (1.00, 2,091, ~1.0). The churn diagnosis is repeated on 6 cases for the 120 s arm.
*Stated in advance.* The hold works if cold starts fall clearly below trigger-only (towards the no-trigger level) and P99 stays at about 1.07 or better. It fails if cold starts stay above 2,400, or P99 loses most of the trigger's gain. Memory is expected to rise somewhat (held containers cannot be released); more than about 0.92 would mean the saving over filled is mostly gone.

**Step 3 result (6 Nov 2026; 36 runs, 18 development cases, not held-out).** *Incident:* the first pass crashed in 19 of 36 runs, all where the cluster was nearly full: the on-demand hold fell back to `apply_hold_floor`, which counts containers and ignores their weights, so held counts could exceed the memory and the placement
asserted. The on-demand fallback now trims the held increments, heaviest first, until they fit; the 17 runs that had finished were unaffected (the held counts fitted, where old and new code agree) and the 19 were re-run.

| configuration (60 s re-layout) | P99 over filled | rho 0.5 | rho 0.7 | rho 0.85 | mean-makespan ratio | cold starts | memory share |
|---|---|---|---|---|---|---|---|
| no trigger | 1.22 [1.16, 1.29] | 1.36 | 1.16 | 1.16 | 1.22 | 1,567 | 0.82 |
| trigger | 1.07 [1.02, 1.12] | 1.17 | 0.99 | 1.05 | 1.10 | 2,124 | 0.86 |
| trigger + hold 60 s | 1.06 [1.01, 1.11] | 1.15 | 0.99 | 1.04 | 1.09 | 1,952 | 0.87 |
| trigger + hold 120 s | **1.05 [1.00, 1.10]** | 1.14 | 0.98 | 1.03 | 1.08 | **1,825** | 0.88 |

Paired over trigger-only: hold 120 s P99 0.98 [0.97, 0.99] (lower in 14/18), cold starts x0.85; hold 60 s 0.99 [0.98, 1.01], x0.92. Filled has 2,091 cold starts, so with a 120 s hold the on-demand controller is below filled in cold starts (1,825), at P99 1.05 and 88% of the memory.
**Against the criteria fixed in advance:** cold starts fell clearly below trigger-only (2,124 to 1,825) without losing P99 (1.07 to 1.05), memory stayed below 0.92: the hold works. It recovers only part of the way to the no-trigger level (1,567).
*Churn diagnosis repeated for the 120 s hold (6 cases, seed 1):* cold starts 10,283 (trigger-only 12,399; no trigger 8,986); trigger adds 3,465 (5,549); **adds removed again within 120 s: 793 (3,122), i.e. 23% of the trigger's adds against 56%**; trigger adds that re-created what the slow loop had just removed: 1,744 (2,900), 50% against 52%.
The extra cold starts over no-trigger fell from 3,413 to 1,297. **The hold removed the first half of the fighting (the slow loop taking back the trigger's work) and not the second (the slow loop shrinking a function that the next burst needs again).** The second half is the slow loop's own aggressive shrink, sized from 30 s of arrivals with no queue term; a gentler shrink is the next candidate.

**Step 4, plan: a gentler shrink for the slow re-layout (written before the runs; user go-ahead 6 Nov 2026).** The second half of the churn is the slow loop shrinking a function that the next burst needs again (50% of the trigger's adds re-create containers removed within the previous 120 s).
Rule (`shrink_delay` = 2, fixed here, not tuned): at each re-layout a function whose sizing need is below its current count keeps the current count unless that has been true at 2 consecutive re-layouts; growth is never delayed. Implemented as a floor on the slow loop's counts (`_floors`), combined with the trigger's hold. In a full cluster the floors are trimmed to fit, as for the hold.
*Arms (18 development cases, 36 runs):* `frozen3_od_fs_h120_sd2` (60 s re-layout + trigger + hold 120 s + gentler shrink) and `frozen3_od_sd2` (gentler shrink alone, no trigger), against hold-only (P99 1.05, 1,825 cold starts, memory 0.88), no trigger (1.22, 1,567, 0.82), filled (1.00, 2,091, ~1.0). The churn diagnosis is repeated on 6 cases for the main arm.
*Stated in advance.* It works if cold starts fall below 1,825 (towards 1,567) with P99 within 0.02 of hold-only (at most 1.07) and memory at most 0.92. It fails if memory exceeds 0.92 (the saving over filled is then mostly gone), or P99 exceeds 1.08, or cold starts do not fall.
Memory is expected to rise: a delayed shrink holds containers longer by construction.

**Step 4 result (6 Nov 2026; 36 runs, 18 development cases, no errors; not held-out).** On-demand FROZEN-3 over filled FROZEN-3, 60 s re-layout:

| configuration | P99 | rho 0.5 | rho 0.7 | rho 0.85 | mean-makespan ratio | cold starts | memory share (0.5 / 0.7 / 0.85) |
|---|---|---|---|---|---|---|---|
| no trigger | 1.22 [1.16, 1.29] | 1.36 | 1.16 | 1.16 | 1.22 | 1,567 | 0.82 (0.64 / 0.87 / 0.96) |
| gentler shrink only | 1.14 [1.09, 1.20] | 1.24 | 1.07 | 1.12 | 1.17 | **1,371** | 0.87 (0.71 / 0.92 / 0.98) |
| trigger + hold 120 s | 1.05 [1.00, 1.10] | 1.14 | 0.98 | 1.03 | 1.08 | 1,825 | 0.88 (0.73 / 0.94 / 0.98) |
| **trigger + hold 120 s + gentler shrink** | **1.05 [1.00, 1.10]** | 1.13 | 0.99 | 1.04 | 1.08 | **1,607** | 0.90 (0.77 / 0.96 / 0.98) |

Paired: gentler shrink over hold-only P99 1.00 [0.99, 1.01], cold starts x0.88; gentler shrink alone over no trigger P99 0.93 [0.91, 0.95] (lower in 17/18), cold starts x0.86. Filled: 2,091 cold starts.
**Against the criteria fixed in advance, it works:** cold starts 1,825 to 1,607 (the no-trigger level is 1,567), P99 unchanged at 1.05, memory 0.90 (limit 0.92). The shrink delay alone also helps: P99 1.22 to 1.14 and cold starts 1,567 to 1,371, i.e. fewer than filled, for 5 points more memory.
*Churn diagnosis for the main arm (6 cases):* cold starts 9,178 (no trigger 8,986, hold-only 10,283, trigger-only 12,399): the extra over no trigger fell from 3,413 to 1,297 to **192**. Trigger adds undone within 120 s: 338 of 2,798 (12%). Trigger adds that re-created just-removed containers: 1,604 (57%), not lower than before, yet the total fell, because the slow loop now adds fewer
(6,380 against 8,986): the trigger's adds substitute for the slow loop's, so that measure is not the cost. The trigger's own shrink removed more here (1,061 against 198), since the slow loop no longer shrinks as fast.
**What it costs.** Memory by load is 0.77 at rho 0.5 but 0.96 at 0.7 and 0.98 at 0.85: the on-demand controller with all three additions is close to the filled version in memory at rho 0.7 and above, and the saving (and the remaining 13% P99 loss) is at rho 0.5. Overall: 5% P99 for 10% of the memory and 23% fewer cold starts than filled; at rho 0.5, 13% P99 for 23% of the memory.
Limits: development cases; the three additions and their parameters (hold 120 s, delay 2) were fixed one at a time after seeing the previous result, so the combination is not a pre-registered configuration until a held-out run confirms it.

**Step 5, plan: 30 s re-layout at target 0.7, and feasibility and scalability (written before the runs; user request 7 Nov 2026).** Arm `frozen3_od_e30_u70` (on-demand FROZEN-3, no trigger, no hold, no shrink delay), 18 development cases. Read against filled: P99, mean makespan, cold starts, memory share by load; beside the existing 30 s arms at targets 0.8 and 0.65.
*Time and compute.* Compute time of each controller decision (re-layout computation, one request-move pass, routing one request), measured by timers around those calls in one process with nothing else running, on scenarios of 80, 160, 320 and 640 servers (and 1,280 if the run time allows) at constant load per server, with functions and workflows fixed at 30 and 15, and in a second sweep scaled with the servers. The growth exponent with server count is fitted on a log-log scale.
*Feasibility rule, fixed here.* Python, one core. Feasible at a size if the 99th percentile of each decision takes at most 10% of the time available to it: re-layout 3 s (period 30 s), move pass 0.4 s (period 4 s), routing 10 ms per request. These are compute times only; the messages a controller needs to collect queue state are not in the simulator and are not measured.

**Step 5a result: 30 s re-layout at target 0.7 (7 Nov 2026; 18 runs, development cases, no errors; not held-out).** On-demand FROZEN-3 over filled (filled: 2,091 cold starts):

| configuration (no trigger, hold or delay unless stated) | P99 | rho 0.5 | rho 0.7 | rho 0.85 | mean-makespan ratio | cold starts | memory share (0.5 / 0.7 / 0.85) |
|---|---|---|---|---|---|---|---|
| 30 s, target 0.8 | 1.15 [1.08, 1.23] | 1.35 | 1.08 | 1.06 | 1.15 | 2,127 | 0.83 (0.64 / 0.88 / 0.96) |
| **30 s, target 0.7** | **1.06 [1.01, 1.11]** | 1.17 | 0.98 | 1.05 | 1.05 | 2,216 | 0.89 (0.73 / 0.95 / 0.98) |
| 30 s, target 0.65 | 1.03 [0.99, 1.07] | 1.10 | 0.96 | 1.04 | 1.02 | 2,254 | 0.91 (0.78 / 0.97 / 0.98) |
| 60 s, trigger + hold 120 s + shrink delay 2 (for reference) | 1.05 [1.00, 1.10] | 1.13 | 0.99 | 1.04 | 1.08 | 1,607 | 0.90 (0.77 / 0.96 / 0.98) |

Paired: target 0.7 over target 0.8 at 30 s, P99 0.92 [0.89, 0.95] (lower in 16/18), cold starts x1.05; target 0.7 over target 0.65, P99 1.03 [1.02, 1.04] (lower in 2/18), cold starts x0.98.
**Reading.** Two settings, no new mechanism, reach the P99 and memory of the three-mechanism design (1.06 and 0.89 against 1.05 and 0.90; intervals overlap, no paired test run between them). What the mechanisms still buy is cold starts: 2,216 against 1,607, 38% more, and 6% above filled. At rho 0.7 and above the cluster is nearly full (0.95, 0.98), so any saving is at rho 0.5 (0.73 of the memory for 17% P99).

**Step 5b: controller cost (7 Nov 2026; plan written before the lazy runs).** First measurement, on-demand FROZEN-3, 30 s, target 0.7, one core: re-layout grows as about N^2.9 and the move pass as N^1.8, routing is flat; the limits fail by 320-640 servers. Profile at 320 servers: 105 of 155 s in the mover, 32.8 million candidate look-ups of which 98.6% hit a cached value.
*Exact speed-ups.* MV-3 (`fast_order`): per-function estimate arrays updated only where a move changes a queue; event hashes equal in 6 of 6 cases. `fast_place`: each candidate priced from a shared base, O(K D) instead of O(K N D), same formula (largest relative difference 4e-16); event hash equal in 2 of 6 cases, in the other 4 P99 differs by +0.1 to +0.5%, consistent with rounding tipping exact ties, so it is not called bit-identical.
*Lazy re-layout scoring (`lazy_place`), test fixed here.* Re-price only the candidate about to be accepted. Not guaranteed to reproduce the exact greedy choice. Arm `frozen3_od_e30_u70_fo_lz` on the 18 development cases against the stored `frozen3_od_e30_u70`. It is acceptable if the P99 ratio has a geometric mean within 2% of 1 (the run-to-run noise floor is about 1.5%), and cold starts and memory are within 2%. Then the scaling sweep is repeated with it.

**Step 5b result (7 Nov 2026).** *Lazy test on 18 development cases (80 servers):* P99 lazy / exact 0.988 [0.973, 1.001], lazy lower in 10/18, per case 0.913 to 1.032; mean makespan 0.995; cold starts 1.001; memory 1.000; moves 1.007; event hashes differ in 18/18. Passes the rule fixed in advance.
*Decision times, one core, one seed, synthetic DAGs, random start, 30 functions and 15 workflows, other runs in the background (so indicative):*

| servers | re-layout typical, exact | lazy | re-layout largest (first), exact | lazy | move pass p99, MV-2 | MV-3 | routing p99 |
|---|---|---|---|---|---|---|---|
| 80 | 15 ms | 21 ms | 0.10 s | 0.13 s | 77 ms | 87 ms | 1.6 ms |
| 160 | 101 ms | 39 ms | 0.28 s | 0.19 s | 158 ms | 109 ms | 2.2 ms |
| 320 | 610 ms | 130 ms | 5.0 s | **0.62 s** | 431 ms | **289 ms** | 3.5 ms |
| 640 | 6.6 s | 0.63 s | 107 s | **2.2 s** | 3.3 s | 1.16 s | 6.0 ms |
| 1,280 | timed out | running | 1,380 s (23 min) | running | 4.6 s | running | 4 ms |

Growth with servers (median): re-layout N^2.9 to N^1.6; move pass N^1.8 to N^1.3; routing flat. **Against the limits fixed in advance, the controller now passes at 320 servers, and at 640 only the move pass fails (1.16 s against 0.4 s).** P99 at these sizes (one run each): 80: 87 s exact, 88 s lazy; 160: 83 s exact, 85 s lazy; 320: 92 s exact, 94 s lazy; 640: 139 s exact, 105 s lazy; so no sign of lost quality from lazy scoring at scale, on one seed.
Not done: scaled functions and workflows (sweep B), 1,280 servers, clean timing with nothing else running. Control-plane messages are not measured.

**Step 5c, plan: lower the cost further (written before the runs; user request 7 Nov 2026).** Profile at 640 servers and 240 functions, nothing else running: 136 s, of which move passes 48 s and re-layouts 21 s.
*Exact, event hashes must equal the stored `frozen3_od_e30_u70_fo_lz` runs:* the availability of all containers in one scan per pass (13 s was `live_availability`, 550,000 calls); mover arithmetic on the hosts only (16 s); the re-layout's selection tracks each function's best candidate instead of rescanning all functions and nodes after every add (6.6 s).
*Second approximation on lazy scoring (`place_thin` = M, off by default):* per function the re-layout keeps only the M heaviest demand points, reweighted so the function's total pull is unchanged. Arms M = 32 and M = 16, on the 18 development cases, against lazy without thinning. It is acceptable if the P99 ratio has a geometric mean within 2% of 1, and cold starts and memory within 2%. At 80 servers a function has at most 80 demand points, so M = 32 may barely bite there; quality is therefore also read at 320 and 640 servers (synthetic, 3 seeds, short runs, so noisy) before any claim.

**Step 5c result (7 Nov 2026).** *Exact speed-ups:* event hashes equal the stored lazy runs in 6 of 6 cases. *Second approximation, 18 development cases, over lazy:* M = 32 P99 1.007 [0.992, 1.021], per case 0.939 to 1.061, mean makespan 1.017, moves 1.016, cold starts 0.999, memory 1.000: passes. M = 16 P99 1.029 [1.014, 1.045], mean makespan 1.050, moves 1.055: fails. At 80 servers the median function has 73 demand points; M = 32 keeps 67% of its pull, M = 16 39% (one scenario).
*Complexity of the re-layout* (A containers changed, K candidates, D demand points, both up to N; F functions; r re-pricings per accepted container): original O(A K N D); shared base O(A K D); lazy O(F K D + A r D); lazy + thinning O(F K M + A r M), so with M fixed the demand points no longer grow with N.
*Clean timing, one process, one core, one seed, synthetic DAGs, typical re-layout, lazy to lazy + M = 32:* fixed 30 functions: 320 servers 65 to 22 ms, 640 servers 318 to 36 ms, 1,280 servers 1,206 to 73 ms; largest call 0.19 to 0.12 s, 0.78 to 0.37 s, 2.5 to 0.81 s; growth N^1.77 to N^0.70. Functions scaled with servers: 320/120 167 to 57 ms, 640/240 1,746 to 158 ms; largest call at 640/240 2.5 to 0.47 s; growth N^2.67 to N^1.32. The move pass is unchanged by thinning: p99 about 0.18 s at 320 servers, 0.9-1.1 s at 640 (limit 0.4 s), so it is now the only decision over its limit.
Seed-1 P99 ratio M = 32 over lazy by servers/functions: 80/30: 0.98; 160/30: 0.95; 320/30: 1.01; 640/30: 1.33; 1280/30: 1.01; 160/60: 1.12; 320/120: 1.01; 640/240: 0.96. One run per size, so noise; 3 seeds at 320 and 640 are still running.

## 9. The two-loop 2x2 under CAP-W1 with the current controller (plan, written before the runs; user go-ahead 7 Nov 2026)

*Why.* The paper's central claim is that replacement and request moves depend on each other. The existing table (3,725 / 1,724 / 1,017 / 126 s, x30, interaction -1.32) carries no capacity tag and used the earlier controller (matcher router, count-ordered moves). The user may also drop the criticality queue order.
*Design.* 18 development cases, 900 s, warm-up 60 s, CAP-W1, filled budget, transfer_only router, gain-ordered moves, FIFO queues in all four cells: A fixed layout, no moves; B fixed layout, moves; C re-layout every 60 s, no moves; D both. `output/data-analysis/capw1_grid.py`, 72 runs.
*Reading (no pass/fail bar).* P99 geometric means; effect of each loop with and without the other, with 95% bootstrap intervals over cases; log interaction (A - B - C + D).
*Queue order, stated in advance.* D is FROZEN-3 without the criticality order. The earlier table gave x1.03 for the order, but on 3 Nov making the mover's wait estimate match the service order made P99 7.5% worse, so removing the order may cost more than 3%. Reference: the stored FROZEN-3 runs. Reported as P99 FIFO over criticality with interval; removing it is the user's decision, and it would be a new controller version.

*Result (7 Nov 2026; 72 runs, no errors; development cases, not held-out; `results/capw1_grid_report.txt`).*

| P99 geometric mean | no moves | moves | effect of moves |
|---|---|---|---|
| fixed layout | 3,899 s | 1,527 s | x2.55 [2.18, 3.02] |
| re-layout every 60 s | 1,431 s | 118 s | x12.10 [10.56, 13.96] |
| effect of re-layout | x2.73 [2.36, 3.09] | x12.92 [10.25, 16.07] | both together x32.99 [28.54, 37.79] |

Each effect is better in 18/18 cases. Log interaction -1.56 [-1.79, -1.32]: together the loops give 4.74 times the product of their separate effects. **The central claim holds under CAP-W1 with the current controller and FIFO queues, and is somewhat stronger than in the earlier table (x30, 3.7 times).**
*Queue order.* FIFO over FROZEN-3 (criticality): P99 1.017 [0.995, 1.040], FIFO lower in 8/18; mean makespan 1.003; moves 0.999; cold starts 1.000; by load 1.003, 1.001, 1.047. The cost is about 2%, not shown to differ from zero, mostly at rho 0.85; the feared larger loss through the mover's estimate did not appear. Removal is the user's decision and would be a new controller version.

*Thinning, quality at scale (step 5c; synthetic, 240 s runs, M = 32 over lazy).* 320 servers, 3 seeds: P99 1.008, 1.021, 1.020, mean makespan +3.9%. 640 servers, 3 seeds: P99 1.333, 1.022, 0.999, mean makespan +6.6%. The mean-makespan cost grows with size, as the kept share of each function's pull falls. At 1,280 servers and 480 functions M = 32 takes the re-layout from 15.6 s to 520 ms typical and from 29.7 s to 1.2 s at most, the one size where lazy alone fails the limit; the move pass p99 there is 1.6 s. Reading: lazy scoring as standard; M = 32 only where lazy alone misses the limit.

### Robustness checks of the 2x2 (plan, written before the runs; user go-ahead 7 Nov 2026)
Three objections to the result above: three of the four cells have P99 above the 840 s measured window, so their queues do not clear and the ratio may depend on run length; the no-move cells use a router that ignores queues by design; development cases only.
- **Queue-aware router.** Cells `Aq`, `Cq`: the no-move cells with greedy_eft (input transfer + queue estimate), 18 development cases, 36 runs. *Stated in advance:* if `Cq` stays far above D (at least x3, interval excluding it) the claim stands as "neither loop works alone". If `Cq` comes within x1.5 of D, the honest claim narrows to "moves substitute for queue-aware routing".
- **Run length.** Each cell with the 900 s trace repeated 4 times (3,600 s, same load; repeated, not a longer trace), 6 development cases, 24 runs. *Stated in advance:* a P99 that grows about in proportion to run length means the queue diverges and the ratio x33 is not a stable quantity; then the paper leads with the absolute outcome and D's stability, not with the ratio.
- **Held-out.** All four cells on seeds 7-10, 24 cases, 96 runs; same reading; D against stored FROZEN-3 for the queue order.
- **Mechanism.** At every 4 s tick queued work is split into *stranded* (an idle container of the same function exists elsewhere: what moves fix), *wrong function* (none of that function idle, but others are: what re-layout fixes; container sizes ignored) and *shortage*; per request, critical-path time into wait, execution and the rest. *Expectation:* stranded dominates in C, wrong-function dominates in B, little of either in D. If not, the explanation of the interaction is wrong.

*Results of the robustness checks (7 Nov 2026; 156 runs, no errors; `results/capw1_grid_report.txt`).*
- **Held-out, seeds 7-10, 24 cases:** P99 6,452 / 2,225 / 1,776 / 186 s. Moves x2.90 [2.55, 3.30] on a fixed layout, x9.55 [7.40, 12.18] with re-layout; re-layout x3.63 [3.09, 4.33] without moves, x11.96 [8.48, 16.71] with them; both x34.7 [26.35, 45.15], each 24/24; log interaction -1.19 [-1.52, -0.88], 3.29 times the product of the separate effects. The interaction replicates on unseen seeds, smaller than on the development cases (-1.56).
- **Queue-aware router, 18 development cases:** `Cq` 1,055 s, better than transfer_only by x1.36 [1.18, 1.58], still x8.92 [8.00, 9.97] above D, D lower in 18/18; `Aq` x28.28 above D; interaction -1.40 [-1.62, -1.18]. Above the x3 line fixed in advance: **the claim stands as "neither loop works alone"; it is not an artefact of the queue-blind router.** greedy_eft is one queue-aware router; the Graph-Aware and HEFT-like rows on S-P point the same way.
- **Run length, 6 development cases, trace repeated to 3,600 s:** P99 A 3,461 to 11,863 s (x3.43), B 1,423 to 7,075 s (x4.97), C 1,388 to 3,365 s (x2.43), **D 97 to 94 s (x0.97)**. A and B grow about in proportion to run length, C less, D not at all. Both together x35.7 at 900 s, x125.7 at 3,600 s; interaction -1.77 to -3.06. **So x33 is not a stable quantity, as feared, but it understates the gap rather than overstating it.** Per the rule fixed in advance, the paper leads with the absolute outcome and D's stability. Limit: a repeated trace, not a longer one.
- **Queue order on the held-out set:** FIFO over FROZEN-3 P99 **1.053 [1.024, 1.084]**, FIFO lower in only 4/24; by load 1.024, 1.065, 1.070; mean makespan 1.007. The development reading (1.017, interval including 1) understated it: removing the order costs about 5% on the tail, clearly above zero.
- **Mechanism: the expectation fixed in advance failed as written.** Shares of queued work, held-out: A stranded 0.05, wrong function 0.10, shortage 0.85; B 0.02, 0.16, 0.82; C 0.13, 0.02, 0.85; D 0.39, 0.15, 0.46. Shortage dominates all single-loop cells, not stranded in C or wrong function in B. The direction agrees (stranded C > B, wrong function B > C), but the share is a poor measure: with thousands queued and about 1,100-1,200 containers, queued work exceeds all idle containers by arithmetic.
  *Post hoc, not pre-registered:* set against the idle containers instead. Mean absolute stranded / wrong function: A 254 / 519, B 67 / 611, C 512 / 63, D 161 / 75. Utilisation in the window A 0.23, B 0.31, C 0.52, D 0.69, so idle containers are about 815, 730, 580 and 375 (rough: slot and capacity units are mixed). Then in C about 88% of idle containers are the right function in the wrong place, and in B about 84% are the wrong function. That fits "re-layout supplies the right capacity, moves bring the queued work to it", and needs direct logging of idle containers to confirm before any claim.
  *Time along the critical path:* in the slowest 1%, C is nearly all queue wait (2,173 of 2,291 s); A and B have 2,617 and 1,705 s that are neither queue wait nor execution, far too much for state transfer. Retry rounds (3,368, 1,888 against 473 in C and 29 in D) suggest requests waiting to be planned at all, for lack of state storage; not confirmed.

## Evidence base
The papers read on 5 Nov 2026 (Graph-Aware text; FaaSPR PDF through `pdftotext`), the existing code (`dfps/dispatchers.py`,
`dfps/controllers.py::faaspr_placement`, `output/data-analysis/graphaware_sweep.py`), and the CAP-W1 scenario files (80 nodes, 30
functions, 15 workflows of 2-19 tasks, weights 0.26-1.75).

## What stays open
- FaaSPR's LP is infeasible at its own alpha = 0.9 during overload bursts; the paper has no overload rule, and the slack adaptation (b) is ours.
- Server groups of 8 (R4): not implemented; the single-group reading is used and its effect is not measured.
- Whether S-P is the right substrate for Graph-Aware and HEFT; S-S is run beside it for that reason.
- Storage: FaaSPR's concentrated layout meets our per-node storage budget (above). The storage-relaxed arm `faaspr_rs` (section 6) separates the port from that model rule; it is a sensitivity arm, `faaspr` is the headline row.
- The rescue step is our adaptation: the paper's platform would fail a placement that leaves a function without an instance and retry. How often it fires (and how often several evictions are needed) is recorded per run from the rerun on, not measured on the first pass.
- Whether the held-out ranking changes with 10 or 30 seeds: 24 cases give intervals that are wide for noisy systems such as FaaSPR.
- The path-sufficiency check (section 5, R3) bounds the sampling error of FaaSPR's routing; it cannot show equivalence to exhaustive enumeration.
- No reference implementation of Graph-Aware exists to compare against (404), so its port rests on the paper's text alone.

## Sources
[[jia-2025-faaspr]]; Liang et al. 2026 (Future Internet 18:265), supplied as a text file; [[baseline-matrix]]; [[heterogeneous-container-sizes]].
