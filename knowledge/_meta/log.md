---
title: "Wiki Log"
type: synthesis
created: 2026-04-15
updated: 2026-04-15
status: review
author: llm
---

# Wiki-Log

## [2026-04-15] meta | Projekt initialisiert
- Ordnerstruktur angelegt
- Schema-Dokument (CLAUDE.md) erstellt
- Index und Log initialisiert
- 2026-10-13 · task · plan=faas-edge-adaptation · Task 0 done: project scaffolded in place at D:\DFPS implementation (template merged without overwriting; methodology=quantitative); gap evaluation moved to input/description/dfps-gap-evaluation.md; ledger created; library at ./library
- 2026-10-13 · note · plan=faas-edge-adaptation · Existing DFPS re-implementation found in the project (dfps/, tests/, PLAN.md, STATUS.md; phases 0-7 done: simulator, NSGA-II, matching, SA, Heu, RL). Relevant to Tasks 6, 7, 9; reuse decision pending user approval
- 2026-10-13 · deviation · plan=faas-edge-adaptation · Tasks 6/7/9: user approved extending the existing dfps/ package in place instead of adopting faas-sim or building a new simulator (Task 6 decision = reuse dfps/sim.py; Tasks 7/9 scope reduced to audit vs E1-E6 corrections, non-stationary workloads, oracles, extra metrics). Tasks 8/10 validation criteria unchanged.

## [2026-10-13] acquire | plan faas-edge-adaptation, Task 1
- Added 13 corpus PDFs (copied) and downloaded 8 open-access PDFs (incl. jayanthi2026quantum, Springer gold OA); 6 manual: input/bibliography/acquisition-todo.md
- Library keys differ from plan keys; mapping in input/bibliography/acquisition-log-2026-10-13.json
- Corrections: wei2020optimal arXiv id is 2010.11443 (plan had 2010.11251); joosen2024serverless published EuroSys 2025 (key joosen-2025-cold-starts); guo2026popularity issue year 2026
- Unverified (no DOI) entries: exton-2024-raptor, shahrad-2020-serverless-wild, wei-2020-robustness-consistency, purohit-2018-online-algorithms-predictions
- PDF size scan (optimize-pdf.py) skipped: ghostscript not installed; sizes unchecked

## [2026-10-13] acquire | reconcile, Task 1 closed
- User supplied the 6 manual PDFs; registered via add-to-library (sun-2026-hybrid, lei-2026-adaptive, farhadi-2021-service, rausch-2021-optimized, xu-2023-stateful, yang-2025-multi-objective). Library: 27 PDFs, all 27 plan sources on disk; acquisition-todo.md empty
- Version caveats: Sun = journal pre-proof; Xu = accepted author version
- 2026-10-13 · ingest · [[nguyen-2025-taming]] · focus: «G0 novelty gate for D1/D2/D3: MPC horizon, trigger policy, forecast-error robustness, workflows/DAGs, edge placement, admission, coupled placement-dispatch; traces, baselines, metrics» · verdict D1 partial, D2 clear, D3 clear

- 2026-10-13 · ingest · [[jayanthi-2026-quantum]] · focus: «G0 novelty gate for D1/D2/D3 (when to reconfigure, forecasts with guarantees, overload admission, placement-dispatch coupling)» · verdict: D1 clear, D2 clear, D3 clear (minor single-function overlap); new pages [[bi-level-scheduling]], [[faas-sim]], [[azure-functions-trace-2021]], [[globus-compute-dataset]]

- 2026-10-13 · ingest · [[lei-2026-adaptive]] · focus: «Novelty gate G0 (plan faas-edge-adaptation): when-to-reconfigure, forecasts with guarantees, overload admission, placement-dispatch coupling»

- 2026-10-13 · ingest · [[sun-2026-hybrid]] · based_on: original (journal pre-proof, not Version of Record) · focus: «G0 novelty gate: when-to-reconfigure, forecast robustness, admission control, placement-dispatch coupling; trace, baselines, metrics, DFPS comparison» · verdict D1 clear, D2 partial, D3 partial · entities: [[dqlws]], [[lyapunov-drift-plus-penalty]], [[delay-sensitive-tolerant-workflow-classes]]
- 2026-10-13 · ingest · [[exton-2024-raptor]] · focus: «duration, arrival and cold-start distributions, workflow shapes, evaluation method for simulator parameterisation (plan Task 3)» · new pages [[raptor]], [[speculative-execution]], [[heavy-tailed-function-durations]]
- 2026-10-13 · ingest · [[liao-2025-adaptive]] · focus: «G0 novelty gate: when-to-reconfigure, forecast robustness, admission control, placement-dispatch coupling; traces, baselines, metrics, DFPS comparison» · verdict D1 clear, D2 clear, D3 partial · new pages [[egat-scheduler]], [[event-driven-two-stage-scheduling]]

- 2026-10-13 · ingest · [[ma-2025-online-deployment]] · focus: «prediction and pre-deployment as baseline design: triggers, guarantees (Thm 1, Thm 2), assumptions, workloads/baselines/metrics, overload handling, relation to DFPS (plan Task 3)» · new pages [[ebro]], [[opts]], [[function-calling-probability-prewarming]], [[randomized-rounding]]
- 2026-10-13 · ingest · [[liu-2025-sdser]] · focus: «prediction and pre-deployment as baseline design: Bayesian hop prediction, pre-deploy trigger, Mosa scheduling, workloads/baselines/metrics, forecast-error handling, controller requirements (plan Task 3/17)» · new pages [[sdser]], [[deathstar-benchmark]], [[bayesian-hop-prediction]], [[dynamic-dag-workflow]], [[predictive-pre-deployment]]
- 2026-10-13 · ingest · [[guo-2026-popularity-aware-caching]] · focus: «online guarantees and assumptions, popularity shifts, update trigger, workloads/baselines/metrics, relation to DFPS, D1, D3 (plan Task 3)» · new pages [[olcfs]], [[layer-wise-container-caching]], [[combinatorial-multi-armed-bandit]]
- 2026-10-13 · ingest · [[wei-2020-robustness-consistency]] · focus: «H1b forecasts with worst-case guarantee for keep-alive: ski-rental/online theorems, consistency-robustness trade-off, randomized vs deterministic hypotheses, reuse of a trust parameter (plan Task 3)» · arXiv v1 file of the NeurIPS 2020 paper
- 2026-10-13 · ingest · [[zolfaghari-2025-dynamic-function-placement]] · focus: «reproduction parameters (Table 2), errata E1-E6, evaluation protocol, evidence for D1-D3 (plan Task 3)» · new pages [[dfps]], [[dfps-printed-errata]], [[periodic-replacement-and-rescheduling]]
- 2026-10-13 · repair · [[purohit-2018-online-algorithms-predictions]] · theorems verified against PDF (numbers unchanged); new concept pages [[consistency-robustness-tradeoff]], [[non-clairvoyant-scheduling]], [[container-keep-alive]]; back-links added to [[ski-rental]], [[learning-augmented-online-algorithms]]
- 2026-10-13 · ingest · [[farahani-2026-clusterless]] · focus: «novelty gate G0: does ClusterLess pre-empt D1 (when to reconfigure), D2 (overload admission, critical-path dispatch), D3 (coupled placement-dispatch)?» · new pages [[clusterless]], [[execution-mode-selection]], [[deadline-feasible-offloading]]
- 2026-10-13 · ingest · [[jia-2025-faaspr]] · focus: «novelty gate G0: re-placement timing, forecasts with guarantees, admission control, placement-dispatch coupling (D1-D3 verdict)» · new pages [[faaspr]], [[faasflow]], [[horizontal-vertical-grouping]], [[migration-minimizing-placement]], [[multi-stage-lp-routing]]

## [2026-10-13] gate | G0 novelty, plan faas-edge-adaptation
- Full-text reads: Sun, Lei, Jayanthi, Nguyen, Liao, FaaSPR, ClusterLess (+ Guo for guarantees). No direction pre-empted: D1 clear, D2 partially overlapping (admission/goodput open), D3 partially overlapping (differentiator: placement scored by dispatch response on upcoming requests; position vs FaaSPR). Ledger updated; G0 PASS
- Deviation: Task 2 additionally ingested Liao, FaaSPR, ClusterLess (flagged A-grade by the literature scan); plan listed 4 sources
- Deviation: Huawei F2 source: plan said "Public 2023 per-second"; the release has per-minute only for Public 2023 (26 days, 5093 functions); per-second exists only for Private 2023. F2 = Public 2023 per-minute; Private per-second (file not yet downloaded: Drive quota) for sub-minute checks only

## [2026-10-13] data | Task 4 datasets
- Azure 2019 + 2021, Huawei Public/Private 2023 per-minute, Huawei 2025 Region 1 cold starts, SeBS-Flow workflows (branch feature/workflows) acquired and extracted; sha256 in input/data/checksums.sha256; provenance in input/data/README.md
- Not obtained: Huawei Private 2023 per-second (Drive quota exceeded; user may fetch manually)

## [2026-10-13] task | Task 6 harness decision
- Decision: extend dfps/ in place (output/data-analysis/sim/DECISION.md). faas-sim steps not run. Open finding: current simulator misses the plan's runtime budget (about 15-30 min wall per simulated 30 min at 80 nodes); to be profiled in Task 7/8

## [2026-10-13] gate | G1 trace practicality (Task 5), results in output/data-analysis/results/g1_trace_screen.json
- D1: PASS by the literal rule (F2 deviation share 49.0% vs Poisson null 40.8%); change points/h F1 0.184, F2 0.008 (< 1): demand at minute scale is mostly smooth in both traces. D2: PASS via F2 (13.3% overloaded windows), F1 0.02% (KILL). Azure 2021 duration SCV 27.8 overall, per-function median 1.93
- Operationalisations fixed before running: z-scored series for PELT (own prefix-sum PELT, matches ruptures on a test series); aggregate top-200 load for D2; pass = threshold in >= 1 real family. ruptures too slow for 800 series

## [2026-10-13] task | Task 7 simulator extensions (in place in dfps/)
- Added: extended metrics (percentiles, SLO-goodput, rejection, warm-idle, decision timing), admission/exec-sampler/controller hooks, event-log hash, dfps/traces.py (thinning, rho calibration, regime shifts, empirical sampler). 51 fast tests pass
- Optimised matching.py (faster gather, de-duplicated spanning trees): 1.4x, outputs verified identical on 45 schedules. Profile: scheduling (kbest_tree) is about 95% of wall time at about 15 ms per arrival, so one simulated hour at rho = 0.85 costs about 36 min wall; the plan's 10 min budget is not met
- Deviation (runtime rule of Task 8): headroom runs use shortened windows (15-30 simulated minutes) and process-level parallelism; to be fixed with the Task 8 measurement
- Deferred: link contention, Huawei cold-start sampler, scale-to-zero

## [2026-10-13] task | Task 8 simulator validation: PASS (output/data-analysis/results/g2_validation.json)
- M/M/c: all 9 cells within 5% of Erlang-C (max 3.2%, c=16 rho=0.5, where the mean wait is only 0.001); Little's law, conservation, determinism pass
- Runtime budget NOT met for one simulated hour (20 min wall at 80 nodes, 19 ms/arrival): per plan, headroom runs use 30-min windows (about 10 min wall)
- Finding: at nominal rho = 0.85 on aggregate capacity, random placement leaves the 80-node system saturated (123 of 5230 requests unfinished, mean makespan 276 s) because of per-function load imbalance (A-16); load calibration must account for it (Task 9/10)
- Corrections: wrong hand-typed Erlang-C reference (1.714 -> 9/7) fixed; waits are autocorrelated so batch-means SE is used (iid SE understated noise about 7x)

## [2026-10-13] task | Task 9 controllers and variants
- Added: SA best-so-far (E3), critical-path matching objective (E5 variant), Sol.snapshot/restore, dfps/controllers.py (RateChangeTrigger, QueueThresholdAdmission, affinity_greedy_placement), dfps/variants.py (B_STAR, AS_PRINTED), 8 new tests; 65 fast tests pass
- B* departs from PLAN.md L-1 ("return last solution") by adding best-so-far; erratum numbering of the gap evaluation (E1-E6) differs from PLAN.md/DEVIATIONS.md (E-1, E-2, E-5, E-6)

## [2026-10-14] deviation | G2 reproduction, waiting-list retries in overloaded cells (plan Task 10)
- Cause: once node storage is exhausted (deep overload, Uniform x2.0 and heavier Pareto cells), arrivals fail placement and wait; the original rule retried the whole waiting list after every task completion (A-24), costing ~36 ms per request: a x2.0 job did not finish in 13 h. A 1 s retry throttle alone did not bound the cost (each round re-tried the whole growing list; 7 x2.0 jobs ran >3.8 h)
- Fix (Sim options, default = original behaviour, event hashes unchanged): retry_min_interval = 1 s and retry_max_attempts = 10 per round (round-robin) in the overloaded cells only (Uniform x2.0; Pareto x0.5, x1.0, x2.0). Cells Uniform x0.25-1.0 and Pareto x0.25 never used the waiting list (n_retry_rounds = 0) and keep the original behaviour; verified identical event hashes for a x1.0 job with the throttle on
- Pareto x0.5 (3 of 10 jobs had used the waiting list) and Uniform x2.0 were re-run under the new rule; earlier results moved to results/g2_reproduction_superseded/
- Caveat: overloaded cells measure backlog more than scheduling quality; their makespans include extra planner queue delay. Reported with this caveat

## [2026-10-14] bug | G2 batch stall: livelock in the retry throttle (found with py-spy), fixed
- Root cause (verified): the throttled retry event re-tested `now - last_retry >= 1.0`; for ~0.04% of times (t + 1.0) - t rounds to 0.9999999999998, the test failed and the event re-scheduled itself at the same timestamp forever (simulated clock frozen, CPU at 100%). py-spy stack samples of a hung job all sat in _ev_retry -> _maybe_retry -> _at; reproduced deterministically at t = 7.1997616808981535
- Fix: the retry event retries unconditionally (it is scheduled at the earliest allowed time); plus a guard that raises if > 5e6 events occur at one timestamp. Regression tests added (69 pass). Runs that did not livelock are unchanged: re-running a finished capped job (pareto_x1.0_s10, SR, 96 retry rounds) gives the identical event hash
- Correction of earlier diagnoses: the 13 h stall of the FIRST batch (no throttle) was the genuine retry storm (measured); the stalls of the second (throttle) and third (throttle + cap) batches were this livelock, not the cost of retries or of annealing as I had suspected. The throttle + cap stay (they bound the retry cost); job errors are now written to <tag>.err instead of stopping the batch

## [2026-10-14] bug | G2 batch: crash "cannot reroute" under storage exhaustion, fixed (A-25b)
- After the livelock fix, 3 Uniform x2.0 jobs (seeds 4, 6, 10) raised: a request's planned node lost its instance to a DFPS re-plan and no node holding the function had free storage for its states (A-25 reroute had no fallback)
- Fix (A-25b, a modelling choice the paper does not cover): the request stays on its node with its storage and retries the reroute every 1 s of simulated time; counted as n_parked. Regression test added. Runs that never reached this branch (all finished results) are unchanged; batch restarted so all 22 remaining jobs use the fixed code

## [2026-10-15] fix | trace loader: top-function selection used the whole trace (test leak), fixed before any tuning
- dfps/traces.load_counts chose the top-200 functions by volume over the full trace, so the test span influenced selection. Now chosen by DEV-span volume only (same functions for the test span); F1 selection is two-pass and memory-safe. Old caches deleted; nothing had used them yet
- Note: G1 (Task 5, decided 2026-10-13) used the first 15 days of Huawei Public 2023 as dev (57.7%); the loader uses exactly 60% of minutes (15.6 days). Small difference, G1 not re-run
- Added: dfps/sebsflow.py (6 SeBS-Flow apps unrolled with the paper's Table-4 parameters; DFPS Fig. 1 read from the rendered figure), traces.build_trace_scenario (plan workflow mix: 6 SeBS-Flow + Fig. 1 + 8 Alibaba; F1/F2/F3 arrivals calibrated to rho), bottleneck_utilisation
- Finding (smoke test): at aggregate rho = 0.7 the initial NSGA-II placement leaves a few functions at 1.6-2.7x their instance capacity (F2 median function load 0.017); recorded per run in the T* tuning
- 2026-10-15 · synthesis · [[bottleneck-register]] · created: recorded (11) and possible (8) bottlenecks with evidence files

## [2026-10-15] gate | G2 harness validity: PASS (Task 8 validation + Task 10 reproduction)
- 80 jobs (Uniform/Pareto x scales 0.25-2 x 10 workloads), output/data-analysis/results/g2_reproduction.json. B*: claims (i), (ii), (iii) all reproduce (3/3); DFPS as printed: 2/3 ((ii) fails at Pareto x0.5-2.0 because SG with the printed Eq. 3 placement is no better than SR: E1 makes the placement objective degenerate)
- Not reproduced: the paper's Uniform result (DFPS about equal to SG); here B* is about 3x better than SG at every Uniform scale
- As printed minus B* mean makespan: +0.7 s (U x0.25), +15.6 s (U x1.0), +47.7 s (U x2.0), +70.1 s (P x2.0); P99 up to 25% higher
- Caveat: Pareto x2.0 static methods left up to 5,921 requests unfinished (SR 2,956, SG_abs 918); their means are over completed requests and biased low; DFPS variants finished all
- Remaining Task 10 step: T* tuning (running next)

## [2026-10-15] task | Task 11 (D1 headroom) implementation, operationalisations (before any result)
- Controllers in dfps/oracles.py, runner output/data-analysis/d1_headroom.py, 5 new tests (tests/test_oracles.py)
- P_true: B* driven by the true mean per-function rates of the next T*; per-node split by the measured share of the last window
- P_fc: truth x mean-one lognormal error (sigma 0.25/0.5/1.0) per (window, function). Deviation: not a seasonal-naive forecaster (F3 has no season; 15-min windows hold no season)
- O1 as in the plan (DP over 10-s slots; keep vs switch to the placement computed from the slot's true rates via affinity-greedy; Erlang-C slot cost + cold-start switching cost; evaluated in full simulation). Simplifications: queues pooled per function, transfers ignored in the DP
- Smoke test (tiny F3 scenario) showed O1 can LOSE to B* (P99 141 vs 120): O1 changes placement only and never re-plans requests, so it is not a guaranteed upper bound. Kept O1 as pre-registered; added two diagnostics outside the decision rule: S_MEAN (static greedy from window-mean true rates) and O1_BSTAR (O1 switches + B* annealing every T*). If O1 < B* at scale, D1 must not be read as KILL without these
- Windows: 15 simulated min + 60 s warm-up (same as T* tuning) so the 540 base runs fit the 12 h timebox (+50% overrun rule); P_fc runs only if H1b condition (a) can pass (h_forecast CI-low >= 0.10 in some family)
- Decision unit: family-level CI pools the 3 load levels (30 paired instances); per-cell CIs reported
- 2026-10-15 · bug · O1 DP queue cost overflowed (Erlang-C factorial with pooled instance counts in the hundreds); replaced in oracles.py by the stable Erlang-B recursion (equal to queueing.fst within 1e-9 where both work; test added); prep restarted. B* itself is unaffected (per-node counts <= 25)

## [2026-10-15] task | Task 10 closed: T* = 4 s (F1), 8 s (F2), 2 s (F3); output/data-analysis/results/g2_tstar.json
- U-shaped P99 vs period in all families (1 s: ~55k cold starts per 15 min; 64 s: imbalance accumulates); F2 4 s vs 8 s within 2% -> 8 s by the pre-set tie rule
- All runs at aggregate rho 0.7 had bottleneck utilisation 1.6-2.9 under the initial placement (see bottleneck register R1)

## [2026-10-15] interim | Task 11 (exploratory peek, 9 of 90 instances: F1, rho 0.5) — no decision taken
- P99 (s): B* 147-439; O1 (pre-registered) 399-3046, worse than B* in 9/9; S_MEAN (static affinity-greedy from true mean rates) 689-1505, worse in 9/9; P_TRUE worse than B* in 8/9; O1_BSTAR (O1 switches + B* annealing) better than B* in 8/9 (e.g. 349->221, 439->326)
- Reading: the pre-registered O1 is not an upper bound in this simulator: its switch targets (affinity-greedy placements, balanced in the pooled queueing model) perform badly once node-level matching and storage matter. If this holds, the pre-registered rule will yield KILL for D1 as an artifact of the oracle. Feeding true rates into DFPS's annealing (P_TRUE) distorts its estimates rather than helping. Exploratory signal: clairvoyant placement changes on top of B* help
- Action: grid continues unchanged; D1 decision deferred to G3 with the user (no rule changed)

## [2026-10-15] task | Task 12 (D2 headroom) implementation, operationalisations (before any result)
- Runner output/data-analysis/d2_headroom.py; scenarios traces.build_overload_scenario; Sim.record_requests; controllers.RejectSet
- F1/F2 windows by G1's rule on the top-200 aggregate (median minute provisioned at rho 0.7, window centred on a minute above capacity; F1 dev span has only 3 such minutes, so F1 windows peak at about 1.0-1.04, F2 at about 1.06-1.16); 15 trace functions from the window give the workflow mix. F3: rho 0.7 base + one 2-10 min burst at 1.2 or 1.5 (pooled as family F3, 20 instances)
- O2 = iterative hindsight shedding (reject in-window requests that missed SLO or did not finish in the previous pass; <= 4 passes; best pass counts) + critical-path dispatch (E5 variant). Approximate oracle: durations are re-drawn when the service order changes
- HEUR = queue-threshold admission theta = 1.0 x total slots (fixed, not tuned)
- Smoke test (tiny F3 x1.5 scenario): later shedding passes LOWERED goodput (2.88 -> 2.52); best was pass 0 (admit-all + critical-path). Same weak-oracle risk as O1; to be checked at scale
- Runs queued after the D1 grid (CPU)
- 2026-10-15 · decision-needed · Task 13 (D3): pre-registered O3 (K=32 simulation-scored candidates per period) measured at about 2-19 h per run vs about 10 min for a normal run; infeasible in the 14 h timebox. Options and recommendation in output/data-analysis/sim/D3_O3_feasibility.md; not implemented pending the user's decision
- 2026-10-15 · ops · D1 grid died at ~06:52 (BrokenProcessPool: workers were children of the ended Claude session); 120/540 runs saved. Resumed 12:10 as a detached process (survives session end), D1->D2 pipeline also detached. Task 11 timebox (started 04:27): 12 h = 16:27, +50% = 22:27; about 5 h were lost to the crash

## [2026-10-15] decision (user) | Task 11 overrun accepted; Task 13 design
- D1 grid: finish the full pre-registered grid (10 instances x 3 loads x 3 families, all controllers) although it overruns the 12 h + 50% limit by about 3-4 h; deviation logged here
- D3 (Task 13): option 2 of output/data-analysis/sim/D3_O3_feasibility.md. O3 scores K = 32 local-search candidates per period with the corrected queueing surrogate (true upcoming rates) on the full grid; the simulation-scored ranking is measured on a subset (1 instance per family x load, 8 candidates at sampled periods) and Kendall tau between the two rankings is reported (plan threshold 0.7). B* and the affinity-greedy heuristic are shared with the D1 grid (same scenarios, seeds, initial placement)

## [2026-10-15] deviation (user-approved) | headroom read as a lower bound from the best clairvoyant controller (D1-D3), decided BEFORE any headroom result was analysed
- Reason: early checks showed the pre-registered oracles are weak (O1 lost to B* in 9/9 instances seen; O2's later shedding passes lowered goodput in a smoke test). A clairvoyant controller that loses to B* gives no upper bound, so a KILL from it would be an artifact
- Rule change in the ANALYSIS only (no runs changed, D1 not restarted): headroom per instance = (B* - best clairvoyant) / B*, best over the controllers that use future information (D1: O1, O1_BSTAR, P_TRUE; D2: best O2 pass, already so; D3: O3). This is a LOWER bound on the true headroom
- Asymmetric reading: CI lower bound >= 0.25 in >= 2 families = GO (valid from a lower bound); if no family reaches 0.10 the outcome is reported as "no headroom found with these oracles", NOT as a pre-registered KILL. The pre-registered per-oracle numbers (h_total from O1 alone etc.) are still reported alongside
- Caveat: taking the best of several controllers per instance favours the envelope slightly (selection over 3 noisy runs); reported as such
- 2026-10-15 · ops · laptop hibernated; D1 stopped at 287/540 (last run 19:25), no errors. Resumed 20:58 (detached, PID 12084) with the D1->D2 pipeline re-armed

## [2026-10-16] deviation | D2 oracle O2 replaced by O2H (user chose option 3)
- Interim D2 (38/40): pre-registered O2 ~= B* (h about -1%, CI spans 0) -> KILL by rule, but the queue-threshold heuristic gives +183-317% SLO-goodput, so O2 is not an upper bound.
- Diagnosis (240 s debug, F1 s8): hindsight shedding only adds rejections; pass 1 kept 562/3873 requests, utilisation fell 0.56 -> 0.25, goodput 3.12 -> 2.84. Best pass was always pass 0 (admit all).
- O2H: hindsight-tuned threshold theta in {0.5,1,2} with critical-path dispatch, then <=3 repair passes (reject admitted misses, re-admit rejected arrivals at load < 0.8 x slots), best pass kept. Code: d2_headroom.py run_o2h; RecordingAdmission in dfps/controllers.py.
- B*, HEUR and old O2 results reused; O2H written to <tag>.o2h.json. Analysis reports pre-registered decision_D2 plus decision_D2_envelope_o2h (envelope = max(HEUR, O2, O2H)) and headroom beyond the heuristic.
- Queued detached (pipeline PID 1492) after the D2 pipeline PID 14680.

## [2026-10-16] decision | post-G3 oracle ablations parked
- D2 capacity bound computed (output/data-analysis/results/d2_capacity_bound.json): loose; O2H at 15-31% of pooled bound -> loss is placement timing on bottleneck functions during bursts.
- User: keep ablations A (bottleneck-first targets), B (O1+B* + admission on D2 scenarios), C (stage-1 burst predictor) in mind; run them in the design step after G3, after D2 and D3. Stored in input/ideas/post-g3-oracle-ablations.md; register entry P9.

## [2026-10-16] result | D1 and D2 decisions recorded
- D1 (540/540): envelope MAYBE (F1 23.1%, F2 42.2%, F3 4.2%); pre-registered O1 rule KILL.
- D2 (40/40 + O2H 40/40): envelope MAYBE (downgraded, heuristic captures 71-80%); pre-registered O2 rule KILL. O2H best pass always a static theta (0.5/1.0); no repair pass won. F2 beyond-HEUR mean inflated by F2_s9 (HEUR 0.61/s).
- Ledger G3 rows filled. Next: D3 (surrogate O3 + Kendall tau), then G3 stop for the user.

## [2026-10-17] reproduction | DFPS Figs. 5-7 (user request; not part of the pre-registered plan)
- Script output/data-analysis/fig567_reproduction.py: Fig. 5 scale 0.25-2.0 (8 pts), Fig. 6 nodes 20-160, Fig. 7 apps 5-40; Uniform + Pareto; SR, SG(|.|), DFPS=B*, Heu, RL; metrics makespan / utilisation / cold starts.
- First pass seeds 1-5 (paper: 10); G2 cells reused. Overload throttle as G2 when offered util >= 0.8 or G2-overloaded cell (flag stored).
- Smoke test passed for all 5 methods. Queued detached after D3 (PID 21052).

## [2026-10-17] deviation | D3 simulation-scored oracle O3S (user-approved design)
- Reason: surrogate O3 (pre-registered option 2) is 3.7-7.2x worse than B* on P99 and its scorer ranks no better than chance (tau about 0, about 570 checks); it replaced SA and used weak random-swap candidates.
- O3S (dfps/o3s.py, design output/data-analysis/sim/D3_O3S_design.md): B* SA unchanged every T*; every 30 s, 8 candidates (keep, affinity target, backlog-aware bottleneck-first target, two half-way moves, 3 local variants) scored by cloning the live simulator and running 30 s ahead on the true arrivals with the real scheduler (request-seconds); switch if > 2% better than keep.
- User choices: 27 runs (seeds 1-3 x family x load; reduced grid caps D3 at MAYBE), epoch/horizon 30/30 s, run right after D3 and before the Figs. 5-7 reproduction.
- Key comparison: O3S vs O1+B* on the same instances. Scorer noise floor: tau between two clone seeds (5 checks per run).
- Refactor: controllers.affinity_greedy_placement accepts counts; proportional_counts extracted (tests pass).

## [2026-10-17] bug | O3S half-way candidate could remove a function's last instance
- 4 of the first 21 O3S runs (F2_r0.5_s1, F2_r0.7_s3, F2_r0.85_s1, F2_r0.85_s3) failed on apply_placement's invariant (every function >= 1 instance). half_way now skips a replacement that would remove a function's last instance (fuzz test: 0 violations in 2,000 cases). The 4 runs were restarted with the fix at 09:02; completed runs are unaffected (the failing candidate was never applied).

## [2026-10-17] experiment | O3S long look-ahead (user request)
- Interim O3S (25/27): +2-6% vs B*, 8-58% worse than O1+B*; switches in only 6-12% of decisions (14/25 runs: none); scorer tau about 0.52. Reading: a 30 s look-ahead sees the switch cost (cold starts) but not its later gain.
- Variant O3S_h120: horizon 120 s, epoch 60 s, K = 5 (keep, affinity, bottleneck, two half-way moves; no local variants), seed 1 of every family x load (9 runs), 6 workers, started 10:03. Output <tag>.O3S_h120.json, analysis d3s_headroom.py analyze --long.
- Queue: main O3S analysis after its last runs; then O3S_h120 analysis; then Figs. 5-7.

## [2026-10-17] result + queue | O3S_h120 (9 runs, seed 1)
- O3S with a 120 s look-ahead beats B* and O1+B* in all 9 instances: vs B* F1 +42% (CI 24-52), F2 +62% (51-74), F3 +15% (9-20); vs O1+B* +36% / +36% / +11%. Switches in 93-98% of decisions; scorer tau 0.71-0.80. n = 3 per family -> decision capped at MAYBE.
- User: finish the Figs. 5-7 reproduction first, then extend O3S_h120 to seeds 2-3 (18 more runs, 27 total). Queued after the figure pipeline (d3s_headroom.py run --long --seeds 1-3; seed-1 runs are skipped as done).

## [2026-10-17] calibration | reproduction setting vs paper Fig. 5 (user: "valid and trustworthy, as close as possible to the paper")
- Stopped the uncalibrated Figs. 5-7 run (18/980 jobs; kept in results/fig567_uncalibrated_partial) and the queued O3S_h120 seeds 2-3 (re-queue after the figures).
- Gap: G2 setting at x1.0 gives mean makespan SR/SG/DFPS 337/296/81 s (Uniform) and 1193/1130/244 s (Pareto) vs about 15/15/15 and 270/230/90 s in Fig. 5; rankings match. At x0.25 Uniform our servers are 18% busy yet SR takes 63 s (paper 12 s at 28%): our unloaded critical path is about 19 s of execution (depth about 3 x 5.7 s), the paper's low-load makespan is about 11 s.
- Fig. 5 digitized by eye into output/data-analysis/results/paper_fig5_digitized.json. Calibration uses Fig. 5 only; Figs. 6-7 are the held-out check. Only open settings vary; Table 2 and the B* algorithm are fixed.
- Screen (calibrate_fig5.py, 8 settings x 12 scenarios x SR/SG/B*): base, load 0.5, load 0.25, pool 15, pool 60, distinct function per task, deterministic execution times, single-task Alibaba jobs included (new extraction data/alibaba_dags_lt60s_min1.json: 2,528,027 jobs, 42% single-task, mean 2.9 tasks; the old set required >= 2 tasks).
- Code: build_scenario(function_mapping="pool"|"distinct"); default unchanged.

## [2026-10-17] calibration | screen result and combination round
- Screen: 94/96 jobs (two pool-15 jobs stopped after about 6.5 h each; pool 15 ranks poorly anyway). Ranking by mean |log| makespan error vs Fig. 5: load x0.25 (x1.86), load x0.5 (x2.50), pool 15 (x3.76), single-task jobs (x3.95), fixed exec (x4.20), base (x4.42), distinct (x4.43), pool 60 (x5.19).
- Load x0.25 matches the Pareto ranking and the high-load end; Uniform low-load floor stays about 24 s (paper 12 s) even at 4% utilisation, so the floor is the workflow length (critical path about 19 s + transfers), not load. No setting reproduces Uniform SR ~ SG ~ DFPS yet.
- Combination round started (stage combo, 6 settings x 12 scenarios): load 0.25/0.125/0.35 with single-task jobs; load 0.25 + single-task + fixed exec; load 0.25 + fixed exec; load 0.25 + single-task + distinct functions.

## [2026-10-17] calibration | combination round, makespan breakdown, depth x mapping test
- Combination round (72 jobs): best load x0.25 + fixed exec (x1.80), barely better than load x0.25 alone (x1.86); Uniform low-load floor still 20-30 s vs paper 12 s.
- Makespan breakdown (makespan_breakdown.py, instrumented without changing the simulator; segments sum to the makespan exactly): at low load about 85% of makespan is execution along a critical path about 3 tasks deep (about 21 s); transfers about 1 s, planning wait 0, rerouting and queueing small. At Table-2 load SR spends 33 of 54 s queueing at 16% utilisation (per-function imbalance). The single-task test was confounded (its 15 draws happened to be deeper, 3.6 tasks).
- Utilisation check: paper Uniform x0.25 SR is 28% busy at 12 s; ours 16% (Table-2 load) and 4% (load x0.25). A lower load factor fits makespan only by idling the servers, so the paper's load is not lower than ours; the gap is workflow depth and balance across functions.
- Depth x mapping test started 22:32 at the paper's own load (no load factor): max critical-path depth 2 (with / without single-task jobs) and 3, each with shared pool vs one function per task.

## [2026-10-18] calibration result + Figs. 5-7 run (calibrated scenario)
- Depth x mapping test (72 jobs, Table-2 load, no load factor): best d2_any_distinct (Alibaba jobs < 60 s with longest chain <= 2 tasks, single-task jobs included; every task its own function): makespan off by x1.86 (same as load x0.25 but without changing the load), Pareto ranking holds, Uniform x0.25 SR/SG/DFPS 11/10/11 s vs paper 12/12/11. Mapping 'one function per task' beat the shared pool in every pair. Remaining gaps: Pareto low-load SR (22 vs 226 s), DFPS Pareto better than paper (26 vs 85 s at x1), utilisation about 1/3 of the paper's (definition unclear), Uniform x1 SR 26 vs DFPS 14.
- User approved adopting it for the reproduction. B* and baselines unchanged; only the scenario differs. fig567_reproduction.py now builds the calibrated scenario (results/fig567_cal, no G2 reuse); seeds 1-5, SR/SG/B*/Heu/RL, Figs. 6-7 are the held-out check. Smoke test passed for all 5 methods.
- Queued after it: O3S_h120 seeds 2-3 (d3s_headroom.py run --long --seeds 1-3).

## [2026-10-18] baseline diagnostic | why our Heu and RL beat the paper's by 4-20x
- Rankings (Fig. 5, calibrated): the order of SR, SG and B* matches the paper at every point (B* < SG < SR, as DFPS < SG < SR); every ranking difference comes from Heu and RL, which in ours are as fast as or faster than B*, in the paper 1.5-20x slower than DFPS.
- Keep-warm test (baseline_keepwarm.py; ondemand.py keep_warm option, default unchanged): releasing every container after its task (AB-H5's proposed default) or a 10/60 s idle timeout (AB-R4) raises Heu/RL makespan only from about 11-14 s to about 17 s at low load and from 35-53 s to 48-88 s at x2. Paper: 46-405 s. Keep-warm is a minor factor, not the cause.
- Volume check: the paper's Heu/RL show 35-58 thousand cold starts already at the lowest rate; our runs contain only 4.5-4.9 thousand tasks at x0.25 (36-39 thousand at x2), so even "every task cold" cannot reach the paper's counts. The paper's runs must contain about 10x more task executions (longer runs, bigger workflows or several instances per request), and its Heu/RL must have a large per-request delay that our adaptations do not have (paper Heu 199 s at 20% utilisation).
- Candidate causes not in the DFPS paper's text: MOSEC offloads to a cloud server (our RL is edge-only, AB-R1); Heu optimises cost, not delay (our AB-H3 makes node costs equal, so Heu becomes locality-greedy, which is good for delay); run length (A-21 300 s) unknown in the paper.

## [2026-10-18] result | O3S_h120 on 27 instances (seeds 1-3 x family x load)
- Headroom vs B* (P99, bootstrap CI): F1 +48.1% (36.2-59.6), F2 +40.7% (29.7-52.7), F3 +15.0% (9.5-20.5). vs O1+B*: +22.3% (8.1-34.9), +15.0% (2.8-26.8), +6.2% (0.0-12.0). Scorer tau 0.76-0.82 (>= 0.7). Switches in 76-85% of decisions.
- By the rule: lower bound >= 25% in F1 and F2 (GO pattern), recorded as MAYBE because of the reduced grid (27 of 90). Clairvoyant on arrivals 120 s ahead: an upper bound.

## [2026-10-18] baselines | B* vs Heu vs RL (mean and P99) and RL retraining
- 48 points of Figs. 5-7 (calibrated): best by mean RL 34, B* 9, Heu 5; by P99 RL 32, B* 10, Heu 6. B* wins when capacity is tight (Uniform x2, 20 servers, 35-40 apps; up to 4x better P99); RL/Heu win with spare capacity, B* 2-3x slower P99 under Pareto.
- Variant test (baseline_variants.py): Heu with Xu et al.'s 1-5 invocations per function reproduces the paper's high-load Heu (390 vs 405 s Uniform x2; 377 vs 295 Pareto x2) but not low load (36 vs 199 s); an untrained (random) RL reaches only 154 s vs the paper's 285 s (Pareto x2).
- RL retraining on the calibrated scenario started (experiments/train_rl.py --calibrated, 24 episodes x 90 s, 80 nodes, 10-35 apps; NER compares whole states so the node count is fixed at 80), then evaluated as RL_CAL on all 220 Fig. 5-7 cells.

## [2026-10-18] cheater | RL + look-ahead (RLLA), built and probed
- dfps/rlla.py + output/data-analysis/d1_rlla.py: RL places tasks unchanged; every 30 s a look-ahead (clone, replay true arrivals 120 s) chooses among: none, future-aware eviction (Belady-style: evict the function with least upcoming demand per container), eviction + pre-warming (margin 0.5 over a 60 s lead), optional recycle limits. ondemand.py gained prewarm(), evict_score, recycle_budget (all off by default; tests pass; earlier results unaffected).
- Probe on F2 rho 0.7 seed 1 (RL P99 483 s vs O3S_120 174 s): RL saturates all 1,235 slots, backlog grows, and it recycles about 80 containers per second. Pre-warming is impossible (no free slots); future-aware eviction changes the score by < 1%; limiting recycling makes it 16-19% worse. Interim reading: in saturated cases the room above RL comes from planned capacity + look-ahead (O3S), not from tuning RL's container lifecycle. Recycle limits dropped from the default candidate set.
- Queued: RLLA on the 27 O3S instances after d1_vs_baselines finishes.

## [2026-10-18] decision | Heu dropped from the remaining D1-vs-baselines runs (user)
- Heu runs at rho 0.7 took 2.5-5.3 h each (per-request planning under load); remaining runs projected at 1-2 days. Done Heu runs (F1 rho 0.5 all 10, F1 rho 0.7 most) are kept; RL and RL_CAL run on all 90 instances. Best existing method = best of B*, RL, RL_CAL (and Heu where run). RL was the best existing method in 9 of 10 F1 rho 0.5 instances; Heu in none.
- Restarted 21:50 (RL / RL_CAL only), followed by the RLLA cheater (27 instances).

## [2026-10-19] result | RL + look-ahead cheater (RLLA), 27 instances; envelope vs best existing method
- RLLA vs RL (P99): F1 +1.2% (0.0-3.0), F2 0.0%, F3 0.0%; the look-ahead kept plain RL in 753 of 756 decisions (future-aware eviction 3 times, pre-warming never). Pre-warming / eviction levers add nothing measurable above RL.
- Envelope (best cheater incl. O3S_120, O1+B*, O1, P_TRUE, RLLA) vs best existing (B*, RL, RL_CAL, Heu where run), 9 instances per family: F1 +34.9% (19.5-49.6), F2 +25.5% (11.9-39.8), F3 +10.2% (4.1-16.9). This supersedes the d1_vs_baselines "incl. O3S" figures (+30.4 / +16.6 / +8.7), which let the headroom go negative where all cheaters were worse than RL; with RLLA (which falls back to RL) the envelope is floored at RL, as it should be.
- Deck slide "Is the gap still open against the best existing method" updated with these numbers.

## [2026-10-19] run | O3S_h120 extended to all 90 instances (user)
- d3s_headroom.py run --long --seeds 1-10 (63 new runs; seeds 1-3 kept), then analyze; d1_rlla.py analyze is rerun afterwards so the envelope vs best existing method uses all instances where O3S exists (RLLA itself only on seeds 1-3, where it equalled RL).

## [2026-10-19] deck | D3 slides restructured (user)
- Removed the slide on the first (formula) D3 oracle; its outcome (3.6-6.5x worse than B*, tau about 0) is kept as one sentence on the D3 mechanism slide and in the summary row. New slide "The five options built every 60 seconds" (how each option is built, worked example, which option wins in the real runs: busiest-first 53%, data-affinity 46%, half-way about 1%). Mechanism slide now states how D3 addresses "DFPS never tests a layout with its scheduler": layouts are judged by replaying the real scheduler on the real next 120 s; the scheduler itself is unchanged.

## [2026-10-20] literature-review | positioning of the look-ahead / hybrid direction
- Extended input/bibliography/literaturguide.md (update section, 12 new rows with verification status), added 2 verified BibTeX entries (fuerst-2021-faascache, gupta-2025-hybrid-reactive-proactive), audit log input/bibliography/audit-log-2026-10-20.json. Library-first pass (29 docs): no local gaps.
- Findings: pre-warming, MPC, hybrid reactive/proactive, break-even keep-alive and workflow-aware pre-warming (ORION, Xanadu) all exist; O3S is a rollout policy; stage-1-burst idea (ablation C) is close to Xanadu / ORION. Not found: simulation-judged layout re-planning with the real scheduler for edge serverless workflows; explicit switching cost for serverless DAG re-placement; regime dependence vs RL. Tool limits: OpenAlex rate-limited, web index weak for 2025-26; no full texts read.

## [2026-10-20] literature-review | four papers supplied by the user, read
- Registered in the library as lei-2026-multi-agent, daw-2020-xanadu, deng-2022-dependent-function-embedding, ray-2020-proactive-placement (renamed from the 2026/2020/2022 user file names after title and author check). BibTeX added (DOIs from the PDFs; Deng without DOI).
- Findings (literaturguide.md section 6): Lei 2026 switches the control architecture on a reactive p95/p50 trigger, single functions, no capacity re-planning: not pre-emptive. Xanadu = just-in-time pre-warming along the most likely workflow path with an aggressiveness (look-ahead depth) parameter: closest prior art for the stage-based prediction idea (ablation C); cloud, no edge layout. Deng 2022 = offline DAG placement, online left to future work. Ray 2020 = proactive prefetching/migration for a mobile user, linear workflows.
- Reading depth: Lei in full; Xanadu, Deng, Ray key sections, not every proof; no wiki source pages yet.

## [2026-10-20] ingest | six sources, focus: prior art for look-ahead, simulation-judged, regime-aware container re-planning (D1-D3)
- Source pages created (depth standard, 10-12 Kernthesen each): [[gupta-2025-hybrid-reactive-proactive]], [[mahgoub-2022-orion]], [[lei-2026-multi-agent]], [[daw-2020-xanadu]], [[deng-2022-dependent-function-embedding]], [[ray-2020-proactive-placement]]
- BibTeX appended: mahgoub-2022-orion (the other five entries were added earlier today); keywords present on all six.
- Reading depth: ORION, Gupta, Lei, Xanadu, Deng and Ray read through the evaluation and conclusion; Deng's proofs (Lemma 1-2, Theorem 3) and Ray's Fig. 5-8 curves were not checked line by line.
- Result: none of the six pre-empts the combination (workflow-level edge layouts + simulator-clone look-ahead + regime trigger). Closest: Xanadu/ORION (stage-based just-in-time pre-warming, no edge, no queueing), Lei 2026 (regime switch on a reactive tail signal, control architecture only), Gupta 2025 (max of forecast and reactive replica count, no workflows).
- ORION page refs use printed USENIX pages (PDF page + 301); lint `PAGE-OUT-OF-RANGE` fixed accordingly.
- lint-wiki.py: 0 issues. Pending: master merge of the six new bibkeys (merge-bibs.py --report-only, plugin script, not run).

## [2026-10-20] result | D3 O3S_120 on all 90 instances (final)
- Run finished 07:03. Gain vs B* (mean, 95% CI, 30 cases each): F1/Azure +33.9% (25.7-42.2, median 32.5), F2/Huawei +46.3% (37.6-54.7, median 48.9), F3/synthetic +12.2% (9.3-15.2, median 13.1). Pre-registered GO rule (lower bound >= 25% in 2 of 3 families) is met against B*; the "MAYBE (capped, 27 of 90)" label in d3s_headroom_O3S_h120.json is a hard-coded cap from the reduced-grid era and is stale.
- vs O1+B*: +15.1% (8.6-22.1), +3.1% (-8.7 to 14.2), +8.5% (5.5-11.6). The first 27 cases had given 48/41/15% vs B*: extra seeds lowered Azure.
- vs best existing method (best of B*, RL, RL_CAL, Heu where run; baselines exist for all 90): Azure +19.9% (8.6-30.5), Huawei +10.3% (-5.7 to 24.7), synthetic +8.0% (3.9-11.9). Loses at 50% load (-3 to -31%, better in 8 of 30), wins at 70/85% (+13 to +43%, better in 54 of 60).
- Envelope (best of O3S, O1, O1+B*, P_TRUE, floored at best existing; RLLA excluded, only 9 cases/family and ~0 gain): Azure +26.0% (18.3-34.1), Huawei +27.4% (19.1-35.9), synthetic +10.3% (7.4-13.3).
- Script: output/data-analysis/d3s_vs_existing.py -> results/d3s_vs_existing.log and .json. Deck updated and republished (Artifact version 36). G3 decision is the user's.

## [2026-10-20] analysis | blind O3S: forecaster attempts and spike predictability
- First blind attempt (copy last 2 min) stopped at the user's request (not a forecaster). Trained per-family gradient-boosting rate forecaster (dfps/forecast.py): held-out error vs copy-last-2-min: Azure 0.165 vs 0.179, synthetic 0.127 vs 0.152, Huawei 0.500 vs 0.177 (median loss under-predicts spiky series: 58% of volume); squared and Poisson losses worse. Not used.
- Bug: forecast.test_offsets assumed 30-min windows (scenarios use 15 min), so training excluded the wrong minutes and test windows may have leaked. Fixed in code; models not retrained.
- spike_predictability.py (trace level, windows reproduced exactly): rises >= 1.5x the 5-min level carry only 3.0% (Azure) and 0.3% (Huawei) of next-2-min volume; copy-last-2-min error at trace level is 0.155 / 0.049, against 0.179 / 0.177 on the simulated arrivals, so most forecast error is Poisson sampling noise of the thinned arrivals, not trace spikes. Same-minute-yesterday anticipates 29-34% of rise volume vs 12-22% for copying but is worse overall.
- Implication: oracle O3S replays the exact sampled arrivals, so part of its headroom may be knowledge of random arrival clumps that no forecaster can have. Proposed next: rate-oracle O3S (clone replays a fresh Poisson sample of the true rates) to split rate foresight from noise foresight; then scenario-robust scoring and event-triggered re-planning. Awaiting user decision.

## [2026-10-20] run | rate-oracle O3S started (user decision)
- dfps/o3s.py: `future="rate"`: at each decision the clone replays a fresh Poisson draw of the TRUE rate series over the 120 s horizon (one draw per decision, shared by all 5 candidates; capped at the end of the series); candidate layouts still use the true rates. Unit check: draw counts match the real arrivals (3344 vs 3322, 3889 vs 3729, 1739 vs 1763), per-workflow composition r >= 0.997, no shared arrivals.
- Run: d3s_headroom.py run --long --future rate --seeds 1-3 (27 cases, 10 workers), started 15:29, expected about 6 h (oracle wall times). Output *.O3S_h120_rateoracle.json; comparison d3s_rateoracle_compare.py queued to run when it ends (results/d3s_rateoracle_compare.log).
- 15:37 restart (user decision): F3 synthetic dropped from the rate-oracle run as not predictable; run now F1 + F2 only (18 cases), new `--families` flag in d3s_headroom.py. Old run (7 min, no case finished) stopped. Expected finish still about 21:40 (the slowest case, F2 85% seed 2, took 6.0 h as oracle); CPU time 31 h instead of 47 h.

## [2026-10-21] run | mechanism pipeline queued (user decision: no-foresight 18 cases -> two ablations -> speed study)
- Rate-oracle run of 20 Oct 15:37 died silently (no output, no reboot); relaunched 23:34 detached (results/pipeline_rateoracle.ps1, PID 27896).
- Disclosure: the "stopped" persistence-blind run of 20 Oct kept 3 workers alive; they finished F1_r0.7_s1, F1_r0.85_s3, F2_r0.85_s3. No-foresight O3S vs B* (= best existing in all three): +53%, +29%, +22% against oracle +52%, +30%, +16%.
- New O3S modes (dfps/o3s.py cand_mode): nosim (busiest-first every epoch, no clone check), local_sim (clone-judge only small DFPS-style swaps), keep_bottleneck (2 clones per decision); d3s_headroom.py --cand/--horizon/--K. Smoke tests pass (130 s runs).
- results/pipeline_mechanism.ps1 (PID 17896) waits for the rate oracle, then runs on F1+F2 seeds 1-3, all no-foresight: blind full; nosim; local_sim; keep_bottleneck H120; full H60; keep_bottleneck H30. Comparison after each stage: results/d3s_variants_compare.log (gain vs B*, vs best existing by load, share of oracle gain kept, decision compute time).

## [2026-10-21] bug | O3S mode flags never reached the worker processes — blind and rate-oracle results invalid
- d3s_headroom.py set --blind / --future / --cand as module globals in configure(); on Windows the ProcessPool workers re-import the module, so they ran with the defaults = the EXACT oracle. Found because "rate oracle" and "no foresight" runs had identical clone scores at every decision.
- Invalid and moved to results/invalid_mode_bug/: 3 *_blind.json (20 Oct) and 4 *_rateoracle.json (21 Oct). The earlier claim "no-foresight O3S matches the oracle (+53/+29/+22%)" is WITHDRAWN; those were oracle reruns. Unaffected: all exact-oracle results (default mode) and the long-variant parameters (epoch/horizon/K always travelled in the job tuple).
- Fix: blind/future/cand now travel in the job tuple and are written to each result file (`mode`). Being checked with a 4-mode ProcessPool test; pipeline (rate oracle -> no foresight -> ablations -> speed study) relaunches after it passes.

## [2026-10-21] bug check (user request) | findings
- Mode bug fix verified with a 4-job ProcessPool test (exact / persist / rate / nosim recorded per file, distinct scores). Same bug class absent from all other run scripts (all pass settings in the job tuple).
- Censoring check: all 90 oracle runs and 198 baseline runs finish every request, same arrivals per case -> P99 comparisons not flattered by unfinished requests.
- Interpreter: all valid results were produced by C:\Users\ahoor\anaconda3\python.exe (numpy 1.26.4). Runs started with `py -3` (Python 3.12.1, numpy 2.2.4) draw different random streams: B* F1_r0.7_s1 gave P99 573 s instead of 450 s; with Anaconda it reproduces bit-for-bit (same event hash). Affected only invalid/test runs (blind, rate oracle, smoke/pool tests) and analysis bootstraps; d3s_vs_existing re-run under Anaconda gives identical numbers. d3s_headroom._job now asserts numpy 1.x and records python/numpy in each result.
- Note for interpretation: one case's P99 moved 27% with a different random stream (same arrivals) -> single runs per case are noisy; conclusions must rest on many cases, as they do.
- Decision timing: wall_s now excludes the tau diagnostic re-scoring (wall_total_s keeps both); earlier p90s were inflated, medians barely.
- Speed-study confound fixed: busiest-first backlog clearing time fixed at 120 s (clear_s) for all look-ahead lengths.
- Stale "MAYBE (capped, 27 of 90)" label now caps only below 90 instances.
- Detached (WMI) launch lacked the conda PATH, workers crashed loading numpy (BrokenProcessPool); pipeline_mechanism.ps1 now sets PATH. Relaunched 02:42.

## [2026-10-21] run | churn trade-off sweep for the busiest-first rule (user concern: migration / cold-start cost of re-layout every minute)
- Data first: busiest-first re-layouts at 14 of 14 decisions; in-window cold starts +52% (50% load) / +57% (70-85%) vs B*, about 440-470 extra container changes per re-layout; vs RL 17k vs 73k at 70-85%. Smoke test: each re-layout wants to change 500-1000 of 1235 slots (40-80%), partly because B*'s annealing (100 trials per round, about 75 container changes per applied round, rounds every 2/4/8 s for F3/F1/F2) keeps moving the layout away between re-layouts.
- Corrections made today: (1) n_moved counts re-routed queued requests, not containers (earlier statement wrong); (2) deck said B* "swaps one container every 4 s": it runs 100 trial swaps per round (assumption A11, paper leaves it open), about 75 container changes per applied round; slide rows on the D1-detail and D3-mechanism slides fixed (artifact v52).
- Pipeline of 21 Oct (rate oracle / no foresight / ablations / speed study): stopped after ablation 2b (17 of 18 cases; last case finishing in its own process); speed variants 3a and 3b cancelled as no longer informative. Ablation 2b result: clone-judging small swaps only keeps -2% (Azure) and 0% (Huawei) of B*'s gain, switching in 6% / 0% of decisions: the gain is the large layout move, not the check.
- New: dfps/o3s.py churn controls (min_frac, cap via limit_changes, min_backlog, no_inner = B* swaps off) in 'nosim' mode; d3s_headroom.py flags; output/data-analysis/churn_sweep.py runs 11 variants x 18 cases in one pool (11 workers) started 22:37: noinner, frac0.4/0.6, cap50/100/200, E120/180/300, bl1.0/2.0. Compare with output/data-analysis/churn_compare.py. Smoke test (400 s runs) passed for base/frac/cap/E/bl; the first thresholds (frac0.1, bl0.2) never bind because wanted changes are 40-80% of slots and backlog is 1.1-2.2x slots at 70% load, so thresholds were raised.

## [2026-10-22] literature-review | novelty and baselines for the busiest-first rule (user request)
- Web search plus abstract pages and two full-PDF design reads (Fifer, Kraken); written to input/bibliography/literaturguide.md section 8; BibTeX added for gunasekaran-2020-fifer, bhasi-2021-kraken, chen-2026-scale, farahani-2026-clusterless (metadata from PDFs/arXiv pages; no PDFs in the library yet, so no wiki source pages and no ingest).
- Finding: backlog-driven per-stage container sizing is prior art (Fifer 2020: Nc = queue length / batch size with a cold-start check; Kraken 2021: per-function sizing for DAGs; HPA/KPA target utilisation). The rule's sizing cannot be the contribution. No paper found combining workflow DAGs, a fixed slot budget across edge nodes, whole-layout re-plan over DFPS, and a churn cap; coverage partial (Springer papers and citing-paper lists not accessible).
- No later paper found that uses DFPS as a baseline or reports dynamic re-layout above it. Baselines still missing for a state-of-the-art claim: HPA/KPA-style, Fifer-style, Kraken-style.

## [2026-10-22] ingest | Fifer 2020, Kraken 2021 (user decision, after the literature search)
- Focus: prior art for backlog-driven per-function container sizing at the edge (busiest-first rule, fixed capacity, churn).
- Source pages created (depth standard, 12 Kernthesen each, based_on: preprint; Fifer = arXiv v1, Kraken = NSF public-access manuscript, page numbers follow those files): [[gunasekaran-2020-fifer]], [[bhasi-2021-kraken]]. PDFs copied to library/pdf/. Concept page created: [[backlog-driven-container-sizing]]. BibTeX entries added earlier today (keywords present).
- Result: Fifer's reactive rule Nc = PQlen / batch size with the cold-start check Df > Cd, and Kraken's ceil(delayed / batch size) with the same check, are the published counterparts of our sizing rule; the cost check is what our rule lacks.

## [2026-10-22] experiment | baselines, independent variant, full churn sweep
- Baselines (HPA-, Fifer-, Kraken-style sizing rules inside the busiest-first set-up; F1/F2, seeds 1-3, 18 cases each): +44.7% / +44.4% / +44.7% P99 gain over B*, against +49.5% for busiest-first. Paired: busiest-first better by +10.7% / +10.1% / +10.6% (95% intervals 3-21, 4-16, 5-18), wins 14, 14, 15 of 18. Each rule keeps about 90% of busiest-first's gain. Concept: [[backlog-driven-container-sizing]]; sources [[gunasekaran-2020-fifer]], [[bhasi-2021-kraken]].
- Independent variant (no B*, own small-move layer, up to 75 moves per B* period): -3.5% vs B* (all loads), +0.4% at 70-85%; with cap 200: -34%. The gain needs B*'s swaps.
- Churn sweep complete (18 cases per variant): cap 200 +42.9% gain, cold starts -25%; cap 100 +37.1%, -33%; B* alone 11,337 cold starts in window vs 17,628 for every-minute busiest-first.
- Scripts: output/data-analysis/baselines_paired.py, independent_sweep.py, churn_compare.py; code: dfps/o3s.py baseline_layout, fine_step. Ablation 2b last case (F2 85% seed 2) stopped on request, 17 of 18 cases.

## [2026-10-22] experiment | step 1 diagnostic: which part of B* carries busiest-first's gain
- 12 cases (F1/F2, 70-85% load, seeds 1-3), busiest-first every 60 s, no foresight. P99 gain over B*: reference (busiest-first + B*) +55.0% (46 to 63); re-run with swap log identical (+55.0%, same P99 in all 12 cases); B* container swaps only, its request moves dropped +9.9% (-4 to 24); request moves only, no B* +71.7% (64 to 79), better than the reference in 12 of 12 cases; re-layout only -11.2%; count-balancing independent variant +0.4%.
- Cold starts in the window (mean per case): request moves only 4,401; reference 16,939; B* alone 10,771.
- Swap log of the reference: B* changes ~75 containers and moves ~210-240 waiting requests per round, evenly over the minute (not concentrated after re-layouts); about half of its container-change ends reverse the last re-layout; 68% of its added containers go to functions with a backlog.
- Reading: the gain comes from moving waiting requests to where they finish earliest, not from B*'s container swaps. Open: request moves without any re-layout (B* or initial placement + moves), 50% load, tuning of the 300-moves cap, baselines and churn with this layer.
- Code: dfps/o3s.py rebalance_step, _log_round, swaps_only; output/data-analysis/bstar_role_diag.py.

## [2026-10-22] experiment | control 1 and 50% load: request moves vs re-layout
- 18 cases (F1/F2, 50/70/85% load, seeds 1-3), no foresight. P99 gain over B* / over best existing: busiest-first re-layout + request moves, no B* +67.1% / +53.1% (18/18 wins); old reference (re-layout + B*) +49.5% / +27.7% (13/18); B* + request moves, no re-layout +50.6% / +27.9% (14/18); fixed initial placement + request moves -268% / -459% (0/18). Paired: re-layout + moves beats B* + moves by +72% (36 to 118), 17 of 18; beats fixed placement + moves 18 of 18. At 50% load the new version beats the best existing method (+20.4%, 6/6), unlike the old reference (-18%).
- Fixed-placement control checked: all requests complete, none parked, cold_starts 0, so the layout never changed; large loss is capacity not following the traffic.
- Code: dfps/o3s.py rebalance_step, random_placement, util_cap / clear_s switches; scripts control_rebal.py, new_layer_sweep.py, new_layer_compare.py.

## [2026-10-23] experiment | placement investigation: the affinity rule is a weak k-median heuristic
- Diagnostic (output/data-analysis/placement_diag.py, live re-layouts of the no-B* controller): the published affinity rule leaves 98% of its placement decisions tied between several nodes (mean 30 of 80 available; 17% of decisions have a completely flat cost vector), converts 226-1013 containers where the target counts need only 72-588 (60-75% avoidable), and never sees origin->root transfers, which carry 24-32% of the expected transfer cost.
- Diagnosis: placement minimises hops to the NEAREST instance of a function, i.e. a weighted k-median / coverage objective, not a per-container assignment cost. Two negative results confirm this: a min-cost transportation formulation is 176% worse on transfer cost, and adding origin cost per container (affinity_placement_v2, origin_weight=1) is 107% worse, because every container then chases the same central nodes.
- New rule (dfps/controllers.py kmedian_placement + _two_opt): each function's containers are facilities; demand points are the nodes holding its workflow partners (weighted by state volume per second) plus the request origins (weighted by input volume, from the observed window only). Containers are placed by marginal coverage gain; the layout is computed INCREMENTALLY (shrinking functions give up duplicates and then their least useful instances, growing functions take the freed slots), then improved by 2-opt swaps accepted only while the transfer seconds saved exceed the cold-start seconds they cost, amortised over the epoch -- no tuning knob.
- Offline on real re-layout inputs (F1_r0.7_s1): published rule 556 conversions / 152.2 s/s transfer; incremental k-median 227 (the theoretical minimum, -59%) / 101.0 (-34%); + improvement pass -58% / -38%; from scratch +56% / -68%. Origin-awareness is nearly neutral (101.0 vs 100.8), so the gain comes from the coverage objective and from being incremental.
- Simulator smoke test (240 s, F1 70% s1): incremental 126.6 s P99 / 779 cold starts; from scratch 130.9 / 1570. Full comparison on the 18 development cases running (output/data-analysis/placement_sweep.py).

## [2026-10-23] experiment | k-median placement in the simulator: negative result with a diagnosis
- 18 development cases, no-B* controller, only the placement rule changed. Incremental k-median (+ improvement pass): P99 208.6 s vs 166.2 s for the published affinity rule, i.e. 22.5% WORSE (better in only 4 of 18); median 77.7 vs 60.7 s; gain over best existing +45.2% vs +53.1%. Load-dependent: -4.8% at 50% load (3/6 wins), -24.3% at 70%, -38.3% at 85%. The improvement pass changes nothing in the simulator (208.6 vs 208.8), so it is dropped.
- But churn collapses: cold starts 1,403 vs 4,417 (-68%), forced reroutes 1,324 vs 11,770 (-89%). New failure mode at 85% load: 15 requests parked per run and 61 retry rounds (reference: 0 of both), i.e. no node holding the function had storage for the request's input states.
- First hypothesis (coverage concentrates each function on few nodes) DISPROVED by measurement: k-median spreads MORE than the published rule (28.9 vs 16.1 distinct nodes per function on F1; 25.2 vs 21.4 on F2), though its worst-case per-node count is higher (15 vs 10). A spread cap therefore addresses nothing and is left off by default.
- Remaining hypothesis, consistent with the project's central finding: the published rule's churn incidentally REDISTRIBUTES queued state (11,770 forced reroutes per run against 1,324), and that redistribution, not the layout's locality, is what keeps P99 low. Decisive test queued: the same k-median layout with unlimited request moves, against the reference at an unlimited cap (nl_rmall, +57.0% over best existing).
- Offline transfer-distance proxy (-38%) therefore does NOT predict P99: in this system the binding constraint is queued state and dispatch flexibility, not transfer distance.

## [2026-10-23] experiment | queued: move-cost sensitivity and overload admission
- Decisive placement test finished: k-median + unlimited request moves P99 140.3 s vs affinity + unlimited 141.0 s (paired +0.2%, -1 to +1, 8/18 wins) with cold starts 1,396 vs 4,386 (-68%) and forced reroutes 707 vs 10,768 (-93%); parked requests 5.1 -> 0.5. Confirms the hypothesis: the published placement's advantage was the request redistribution its churn forced, not its locality. k-median from scratch is 11.5% worse (0/18) with 57 parked per run, so being incremental is essential; the origin term (212.5 vs 208.6) and the improvement pass (208.6 vs 208.8) are both neutral and dropped.
- Frozen controller: busiest-first sizing + incremental k-median placement + finish-time request moves (no cap), no B*. +57.1% over best existing on the 18 development cases, a third of every other variant's cold starts. Needs its own held-out run.
- Weakness found by measurement: in that configuration the request moves are 62,903 per 900 s run (70/s, 3.0 per completed request) and add 41% to the total state volume, while the simulator charges a relocation only its own transfer time (no link contention) -- and P99 falls monotonically as the cap is lifted (233.5 s at 100, 166.2 at 300, 141.7 at 1000, 141.0 unlimited). The gain therefore rests on an unpriced action.
- Queued: Sim(move_cost=m) charges every relocation m times its nominal transfer time for EVERY controller alike; ours (unlimited and cap 300) and B* at m = 2 and 5, 18 development cases (output/data-analysis/move_cost_sweep.py). Smoke test at m = 5 on F1 70% s1: B* 1053 s P99 against 450 s at m = 1, and it relocates more than we do (115,243 vs 84,773), so the test is two-sided.
- Queued: overload admission (output/data-analysis/overload_admission.py) -- the three mechanisms have no way to turn work away, so there is no story at or above capacity. Reuses D2's overload scenarios, baselines (B*, HEUR = B* + queue threshold theta 1.0) and hindsight oracle (O2H) on F1/F2 seeds 1-10; metric SLO-goodput, since P99 is computed only over admitted requests.

## [2026-10-23] experiment | queued: capacity- and queue-aware placement; pattern grid cut to 85% load
- Move-cost study finished (18 dev cases): our gain over B* measured under the same relocation cost is +70.9% (cost 1), +70.1% (2), +66.5% (5), 18/18 wins each; B* is hit harder (579 -> 729 s) than ours in relative terms it is 140 -> 222 s, but B* relocates MORE (78,987 vs 72,061 moves at cost 5). At 50% load against RL the gain flips from +21.6% (cost 1) to +12.9% (2) to -19.6% (5, 0/6): RL pays nothing for relocation. At cost 5 capping moves at 300 is 19% worse than unlimited (7/18 wins), still +60.4% over B*.
- Pattern-controlled scenarios (pattern_scenarios.py): 9 single-pattern workflow sets (chain3/12, diamond4/8, wide16, out-tree, in-tree, layered, real SeBS-Flow apps) at matched offered load; cut to 85% load, 36 jobs. Smoke test wide16 F1 85%: B* P99 223.2 s / 1,738 cold starts vs ours 122.2 s / 386.
- Overload admission smoke test (F1 s1, 180 s window): ours admit-all goodput 16.48 (0 rejected), ours + queue threshold 32.30 (35% rejected, P99 91.4 s); B* 5.94, B* + threshold 16.03 at full length. Full runs queued behind the move-cost study.
- Correction: the standard scenario mix already contains the 6 SeBS-Flow apps + DFPS Fig. 1 + 8 Alibaba DAGs, so SeBS-Flow is not a third workload family.
- Placement prior art (web search, abstracts only): k-median / facility location for replica and service placement (CDN replica survey arXiv 1611.01729), mobile facility location with movement cost (Swamy), incremental service migration at the edge (cDSMA, arXiv 1007.5341), reconfiguration-limited microservice placement (Modena SoftCom 2025, STEP Chalmers 2026). None found combining a fixed container-slot budget, incremental coverage-gain placement and queued-request redistribution. The novelty claim must not rest on k-median itself.
- Queued: queue_aware_placement (dfps/controllers.py): the incremental k-median with a cost that prices capacity -- soft routing p_dn proportional to c_n exp(-hops/tau), state-transfer seconds plus M/M/1 waiting seconds per container -- because the distance objective did not predict P99. Variants qa (tau 1), qa_tau2, qa_noqueue (ablation), 18 dev cases each, unlimited request moves; reference nl_km_rmall (P99 140.3 s, 1,396 cold starts). Offline: valid layouts, same conversions as k-median, fewer containers piled on one node (max 8 vs 16 on F1 85%).

## [2026-10-23] analysis | what holds the controller back at 50% load
- Overload admission final (20 cases, SLO-goodput): B* 2.32; B* + threshold 7.67; ours admit-all 10.30; ours + threshold 23.29 (20/20 wins over both ours alone and B* + threshold); oracle O2H 8.70 (not an upper bound for our controller, which is a different system). Admission cuts our request moves by half (112,680 -> 58,374 per case) and parked requests from 9,193 to 0; cold starts unchanged (1,324 vs 1,300). On Huawei admission matters most (4.08 -> 24.68).
- Co-location headroom (placement_locality.py, 8 runs): transfer is 7.4% (50% load) and 10.9% (85%) of the planned critical path for our controller, 9.7% / 12.7% for B*; 46% / 32% of edges already local (B*: 31% / 25%). Workflow-aware co-location dropped.
- Queue-aware placement vs incremental k-median (both unlimited moves, 18 dev cases): P99 134.6 vs 140.3 s (+3.6%, +2 to +5, 15/18 wins), parked 0.0 vs 0.5; gain grows with load (+1.8% / +3.4% / +5.5%). tau 2: +3.8%. The ablation without the waiting term (qa_noqueue) is running; until it is in, the gain cannot be attributed to the queue model rather than the soft routing.
- 50% load: the P99 of a request is mostly irreducible. Task durations are exponential, so with no queueing and no cold starts the P99 floor of the workflow mix is 88 s on average over the 20 cases (Monte Carlo critical path + 0.72 s per edge). Ours is 33 s above it, RL 57 s; ours removes 41% of RL's excess. Cases where RL is ahead: 4 of 20, all Huawei (seeds 5, 6, 7, 10); in 3 the gap is 4-14 s. Huawei seed 5 is the real failure (floor 56 s, ours 152 s, RL 130 s) and has the burstiest arrival series (CV 0.27, peak 1.7x). Old oracle (exact future, simulation-scored, cap 300) also lost to RL at 50% (-17.9%, 1/6), so the earlier 50% weakness was the request-move cap, not foresight.
- Running: hard50.py -- re-layout every 15/30/60 s on the six hardest 50% cases, and a per-request timeline of Huawei seed 5.

## [2026-10-23] experiment | queue-aware ablation, elastic capacity built, cadence at 50% load
- Queue-aware ablation (18 dev cases, final controller): k-median 140.3 s P99; queue-aware WITHOUT waiting term 136.1 (+2.7%, +2 to +4, 15/18); with waiting term tau 1 134.6 (+3.6%, 15/18); tau 2 135.0 (+3.8%, 17/18). The waiting term alone adds +0.9% (0 to +2, 12/18): +0.1% at 50% load, +0.3% at 70%, +2.3% at 85% (6/6). Most of the gain is the soft routing (a placement cost that does not assume every request finds its nearest container), not queue pricing. Soft routing lives in the placement cost only; the dispatcher (graph pattern matching) and the finish-time request moves are unchanged. Final placement: soft-routing cost with the waiting term, tau 1, described as a design choice, not a contribution.
- Elastic capacity (output/data-analysis/elastic_*.py; Sim(elastic=True), add_instance / remove_instance / _destroy, provisioned_slot_s accounting; the sizing rule's own count replaces the leftover-slot spreading; HPA/Fifer/Kraken rules can run at their own container counts). Tests: invariants after 400 random operations, fixed-budget accounting (209,950 = 209,950), controller run at 50% load (701 of 1,235 slots at the end, mean 794 = 64%, P99 122.7 s, 432 cold starts) passed; the identity test (non-elastic B* must reproduce a stored event hash) was still running. Sweep (6 variants x 18 cases) is gated on all tests passing.
- Cadence at 50% load (hard50.py, six hardest cases, selected): re-layout every 30 s vs 60 s: P99 +9.2% (+1 to +19), 5/6 better, cold starts 1,526 vs 1,409; every 15 s: +9.4% (-2 to +21), cold starts 1,647. Flips Huawei seeds 5 and 7 to wins over RL; seeds 6 and 10 remain losses. Timeline of Huawei seed 5: median 12-15 s, slow requests only in minutes 2, 4, 9, 13, 14; only minute 4 is a total-rate peak; one workflow carries 80-94% of requests in every minute; queue at the 60 s decisions is small after the first, so the tail comes from spikes between re-layouts. The gain is probably overstated because the cases were selected; queued: cadence_sweep.py runs 30 s vs 60 s on all 20 cases at 50% load (22 new runs), reporting the six selected and the fourteen others separately.

## [2026-10-23] decision | FROZEN-1 and its held-out test (user decision)
- The user froze the controller as: busiest-first sizing (utilisation 0.8, backlog cleared in 120 s) + incremental soft-routing placement (tau 1, origin weight 1, NO waiting term) + finish-time request moves with no cap, B* annealing off, fixed slot budget, no foresight. Record with a hash of the code files: results/frozen_config.json (frozen at 23:22).
- Evidence for the choice, development seeds 1-3, 18 cases (gain over the best existing method): soft routing without the waiting term +58.2% (+75.8% at 70-85% load); with the waiting term +58.4% (+76.1%); plain k-median +57.1% (+74.9%). The differences between the top variants are about one point and within the selection noise of choosing among variants on the same cases; the no-waiting-term version is the simpler of the two.
- Test queued (frozen_sweep.py): FROZEN-1 at 60 s and at 30 s re-layout cadence on held-out seeds 4-10 (42 cases each, never used for any development), then the 30 s variant on development seeds. These are the only two configurations run on the held-out seeds. The earlier cadence_sweep.py (30 s vs 60 s with the k-median, all 50%-load cases) was stopped as superseded; partial files nl_hardE30/hardE60 for the six hard cases remain from hard50.py.
- The pattern study (running) and its smoke test use the k-median placement, a point or so away from the frozen placement; the elastic sweep (gated) was switched to the frozen placement, checked offline: 724 of 1,235 slots requested at 50% load, valid layout, 511 slots empty.

## [2026-10-24] queue | elastic sweep paused, frozen sweep given 11 workers
- Pattern study (22 of 36 at 02:06): chain3 +85.4%, diamond4 +81.5%, diamond8 +78.2%, outtree7 +75.9%, wide16 +77.0% (2 cases), chain12 +68.1% over B* at 85% load, every case a win; cold starts fall 7-12-fold; the deepest chain has the smallest gain and the most moves per request (6.6). Uses the k-median placement, not the frozen soft-routing one.
- Elastic capacity (el80 18/18, el65 14/18 at the time): at target 0.8 the controller needs 67% of the slots at 50% load (P99 +28% against the full-slot version), 92% at 70%, 100% at 85%; at target 0.65 it needs 80% at 50% load (P99 +10.7%) and 100% above; overall 88% / 94% of the slots for +10.8% / +3.0% P99; still +66% / +71% over B* at full provisioning. The analysis script originally assumed 1,235 slots everywhere; the slot total differs per scenario (about 1,246 on average) and is now read per case.
- Decision (user): the elastic sweep is paused (its finished runs are kept and it resumes by re-running results/pipeline_elastic.ps1 or elastic_sweep.py run 11, which skips existing files; the 0.5 target and the HPA/Fifer/Kraken variants have not started). The frozen held-out sweep now has 11 workers: the original 8 plus a second pool of 3 working through the same list in reverse order, so no in-progress run was lost.

## [2026-10-24] review response work: tables, two-timescale smoke tests, queued sweeps
- paper_tables.py (no new runs) -> output/data-analysis/results/paper_tables.md: T1 the 2x2 with raw P99 seconds (B* 579 s mean; A fixed layout 3,948; B fixed + moves 1,957; C re-layout only 639; D both 166), conditional effects x2.1 / x3.7 / x6.6 / x11.6, A to D x24.8, interaction -0.56 (-0.81 to -0.31) -- grid run with the earlier configuration (affinity, cap 300); T2 absolute P99 on held-out seeds per family and load with requests per P99 (FROZEN-1 Huawei 50%: 119 s vs RL 133 s; Azure 85%: 182 vs B* 632, RL 1,018); T3 admission 2x2: B* 2.32 -> 7.67, ours (k-median version) 10.30 -> 23.29. Correction for the second review: admission does NOT hurt B* (10.30 is ours without admission).
- Emergency (fast) capacity loop: first bug (adjuster never stored warmup) fixed. Smoke tests on burst-injected scenarios: Huawei 70% s1 baseline 92.8 s vs plain fast loop 94.3 s, cold starts +10%, 12 actions starting at 72 s (before the first burst, i.e. false alarms); Huawei 50% s1 baseline 73.7 s vs fast+hold 75.9 / fast+hold+severity+gate 75.5, cold starts +8-9%. At 50-70% load the fixed budget leaves 580-820 spare containers, so spare capacity plus request moves already absorb the bursts (baseline in-burst P99 barely above outside). Benchmark narrowed accordingly: one option (regime gate), 85% load added (tight capacity), configs fz60 / fz30 / fast_gate on 12 burst scenarios (36 runs).
- Queued (review_sweeps.py, development seeds, after the frozen held-out sweep): layout-age test (re-layouts decided on time, applied 60/120/300 s late; 70-85% load; 36 runs) and the 2x2 re-run with FROZEN-1 settings (fixed layout + unlimited moves; soft-routing re-layout without moves; 36 runs). New switch: churn 'relayout_delay' in dfps/o3s.py.

## [2026-10-24] results | 30 s cadence held-out, burst benchmark, layout age, FROZEN-1 2x2, pattern study complete
- Held-out (seeds 4-10, 42 cases each; the two pre-declared configurations): FROZEN-1 at 30 s vs 60 s: P99 +4.9% (+2 to +8), better in 26/42, cold starts 1,258 vs 1,174 (+7%). Gain over the best existing method: 30 s +52.0% (41/42 wins) vs 60 s +49.0% (39/42); at 70-85% load +67.6% vs +65.3% (28/28 both); at 50% load +20.6% (13/14) vs +16.4% (11/14). Azure +3.8%, Huawei +5.9%. Development seeds showed less (+2.0%, Huawei -1.7%).
- Burst benchmark (12 burst-injected scenarios incl. 85% load; vs FROZEN-1 at 60 s): 30 s cadence +1.9% (-0 to +4), 7/12, cold +9%; emergency loop with regime gate +3.6% (+1 to +6), 9/12, cold +18%, 39 actions and 447 conversions per run; its gain is the same inside and outside the bursts (+2.9% vs +3.6%), i.e. it acts as a general extra corrector, not a burst catcher.
- Layout age (re-layouts decided on time, applied late; 70-85% load, 12 dev cases): 60 s late +44% P99 (+32 to +55), 120 s +113%, 300 s +370% with 29,907 parked requests. The fast request moves do NOT compensate a stale layout: the controller needs timely re-layouts (a real robustness requirement).
- 2x2 with FROZEN-1 settings (18 dev cases, geometric-mean P99): A fixed/no moves 3,725 s; B fixed + unlimited moves 1,727; C soft-routing re-layout, no moves 1,022; D FROZEN-1 129.5. Moves x2.2 on a fixed layout, x7.9 with re-layout; re-layout x3.6 without moves, x13.3 with; interaction -1.30 (-1.52 to -1.07), stronger than the earlier grid (-0.56): the incremental placement leans on the moves even more than the old rebuild rule did.
- Pattern study complete (36 jobs, 85% load, k-median version): every pattern positive over B*, 36/36 wins: chain3 +85%, diamond4 +82%, layered12 +79%, diamond8 +78%, wide16 +78%, outtree7 +76%, intree7 +73%, chain12 +68%, real SeBS-Flow apps +66%. Moves per request grow with workflow size (1.7 for chain3 to 10.4 for wide16).

## [2026-10-24] decision | FROZEN-2 adopted (user): moves right after a re-layout, 4 s move period on both families
- Timing test (development seeds; 39 of 54 runs when read): moves on the tick that applies a re-layout +1.7% P99 (+1 to +3), 12/16 better, cold starts unchanged; a re-layout applied 5 s late (effectively 8 s, the next controller tick) -3.7% (-5 to -2), worse in 11/12, worst -10% at 85% load; a 60 s rate window +1.3% P99 but +35% cold starts (not adopted).
- FROZEN-2 = FROZEN-1 + (1) request moves also run on a re-layout tick (churn moves_after_relayout) and (2) request-move period 4 s on Huawei (was 8 s, B*'s tuned T*; B* keeps its own period in every comparison). Defined in output/data-analysis/frozen2.py; recorded in results/frozen_config.json (successors) with code hashes. Cadence stays 60 s.
- Held-out status: seeds 4-10 were used for FROZEN-1 at 60 s and 30 s and their results are known; FROZEN-2 was chosen from development seeds only, so a rerun on seeds 4-10 is not strictly clean; fresh seeds (11 and above) would be.
- Running: FROZEN-2 on the 18 development cases (frozen2.py), compared with FROZEN-1.

## [2026-10-24] decision | FROZEN-2 keeps the 4 s request-move period; 2 s reported as a sensitivity result
- Timing test final (18 dev cases): moves right after a re-layout +1.6% P99 (+1 to +3), 14/18; re-layout applied 5 s late (about 8 s in practice) -2.7% (-4 to -2), -3.7% at 70-85% load; 60 s rate window +1.1% but cold starts 1,936 vs 1,396.
- FROZEN-2 vs FROZEN-1 (dev, 60 s cadence): P99 +4.5% (+3 to +6), 14/18; Azure +0.9% (immediate moves only), Huawei +8.2% (+7 to +9), 9/9 (period 8 s -> 4 s). Gain over best existing +60.0% vs +58.2% (+77.0% vs +75.8% at 70-85% load).
- Move period 2 s vs 4 s (FROZEN-2, 18 dev cases): P99 +2.2% (+1 to +3), 15/18, moves per request 4.11 vs 3.19 (+29%), cold starts unchanged, gain over best existing +60.9% vs +60.0%. Diminishing returns (8 s -> 4 s gave +8.2% on Huawei) and 29% more state transfers, which the relocation-cost study showed matter; decision (user): keep 4 s. A 2 s adoption would need the relocation cost priced at 2x and 5x.
- Queued, running next: admission second round (admission_sweep.py, 120 runs on the D2 overload set: FROZEN-2 with/without admission, move-cap curve with/without admission, thresholds 0.5/1.0/2.0, B* with/without admission, SLO factor swept offline at 2/3/5/10 from per-request logs). Smoke test passed: goodput recomputed from the log at 3x matches the simulator (33.62 vs 33.62).

## [2026-10-24] draft | deck update
- output/presentation/dfps-headroom-briefing.html: 13 new slides (B* not needed, FROZEN-2 controller, 2x2 re-layout x moves, held-out validation, ablations, placement, timing, robustness, 50% load, dropped ideas, overload/admission, elastic, prior art); summary, proposal, next steps and title status rewritten; older slides marked superseded. Published as version 55.

## [2026-10-24] query | baseline matrix and literature search
- Synthesis created: [[baseline-matrix]] (run / ablation / cite-only per mechanism, with status and caveats).
- Web search (8 queries, abstract level): no work found that migrates already-queued requests between live containers or nodes for serverless workflows; closest prior art is DFPS's own relocation step. New candidates noted, none read: Hermod (SoCC 2022), Sparrow, Dirigent, Lou et al. arXiv 2310.16475, HyperDrive, Li et al. 10.1145/3616374, Scale (arXiv 2605.15704), BeeFlow. A systematic documented search is still open.
- Started: final_ablation.py (108 runs: hpa/fifer/kraken sizing, jsq, steal, textbook stack on the FINAL controller; results/fx.txt). dispatcher_sweep.py queued behind admission round 2 (an earlier attempt to queue it had silently not started).
- Code: baseline_layout(..., place=) so sizing-rule baselines can use the incremental placement; default behaviour unchanged.

## [2026-10-24] query | four supplied papers added to the baseline matrix
- Read FaaSPR (already ingested), HyperDrive (SEC 2024), BeeFlow (JSA 2023), SCALE (arXiv 2606.06820). Added to [[baseline-matrix]]: FaaSPR placement and LP routing as candidates to run; FaaSFlow-style grouping as a placement ablation; BeeFlow, HyperDrive and SCALE cite-only; first-fit and round-robin proposed as extra dispatchers.
- None of the four moves already-queued requests. SCALE (agentic LLM DAGs, no containers) is a different paper from the "Scale" (arXiv 2605.15704) found by web search earlier.

## [2026-10-24] code | FaaSPR ported (placement and LP routing), as separate variants
- dfps/controllers.py: faaspr_placement (grouping, hg_limit 4, reuse-priority placing; counts from our sizing; random workflow order). dfps/dispatchers.py: FaaSPRRouter (sampled routing paths, one LP over all workflows, alpha 0.9, multi-stage latency threshold, recomputed at every layout change). dfps/o3s.py: placement "faaspr" option, also for the sizing-rule baselines. Adaptations are listed in the docstrings.
- output/data-analysis/faaspr_sweep.py: fp_place (placement only), fp_route (routing only), fp_both, fp_pub (HPA sizing + both, no request moves). Only a smoke test (140 s, one case) was started; NO full runs are queued. Order agreed with the user's review: finish the final-controller ablation re-run (fx), add the missing "new counts, old placement" ablation, dispatcher sweep, then fp_route and fp_place separately, fp_both and fp_pub last.
- Existing runs are unaffected: defaults unchanged, running workers loaded the old modules.

## [2026-10-24] experiment | admission round 2 finished (final controller, 120 runs, 20 overload windows)
- theta 1.0: goodput 11.08 -> 26.08 (x2.4), rejected 27%, P99 of admitted 738 -> 127 s, parked 25,683 -> 0. Threshold sweep (10 windows): none 14.92, 0.5 20.66 (51% rejected), 1.0 29.10 (25%), 2.0 24.37 (12%). Move cap with admission (20): 100 20.69, 300 25.99, none 26.08; without admission (10): 4.89 / 12.39 / 14.92. SLO factor 2/3/5/10: x3.6 / x2.4 / x1.5 / x1.1 (B* x3.6 / x3.2 / x2.4 / x1.3; ours+adm over B*+adm x4.3 / x3.3 / x2.3 / x1.9).
- Talk deck: slides 26-29 (admission effect, tuning, question for the professor, elastic capacity). Decision on whether admission belongs in the contribution is left to the professor.

## [2026-10-24] query | ClusterFlow read; workflow-awareness study started
- ClusterFlow (Computer Networks 287, 2026, 112562) read from the supplied PDF and added to [[baseline-matrix]] as cite-and-contrast (workflow fracturing, DDAP greedy grouping, atomic subgraph migration; closest to our mechanism 2; not runnable in our simulator, which has no live container migration).
- output/data-analysis/workflow_stress.py: ours vs stack (HPA + JSQ, our placement) vs kstack (HPA + JSQ + random placement) vs B*, at data scale k = 1/4/10 on the standard mix (F1/F2, 70/85%, seeds 1-2) and on chain12/layered12/wide16 (k = 1/10). dfps/o3s.py: baseline_layout accepts rng for data-oblivious placement. Smoke test running.

## [2026-10-24] experiment | ablations re-run on the final controller (final_ablation.py, 108 runs, 18 dev cases each)
- FROZEN-2 better than: textbook stack (HPA + JSQ) +14.2% (12 to 17), 18/18 (50/70/85%: +15.7/+14.1/+12.7%); JSQ moves +11.3% (9 to 13), 18/18; work stealing +35.2% (27 to 44), 18/18; HPA sizing +2.3% (1 to 4), 12/18; Kraken sizing +6.2% (2 to 11), 13/18; Fifer sizing +32.1% (18 to 47), 16/18, 5,648 cold starts vs about 1,280.
- Gain over best existing: ours +60.0%; stack +52.9% (88% of ours); JSQ +54.2%; HPA +59.0%. Talk deck slides 16 and 21 updated (version 4); the "earlier controller" caveat removed for these rows.

## [2026-10-24] experiment | FaaSPR mechanisms in our controller, 18 dev cases (faaspr_sweep.py)
- Bug fixed in faaspr_placement: functions used by no workflow (one in each seed-3 scenario) were never placed, leaving slots empty; they now go where a live instance can be reused, else to the server with the most free slots. The 6 crashed runs were re-run.
- fp_place: ours better by +1.6% (-0 to +3), 14/18; cold starts 6,927 per run vs ours (see below); parked 14.8. fp_route (300 paths, repair on storage): ours better by +2.2% (+1 to +3), 16/18; cold starts 1,410. No-moves pair (ours_nm, fp_route_nm) running.

## [2026-10-24] experiment | no-moves pair finished (ours_nm vs fp_route_nm, 18 dev cases) and the stress-pilot design fix
- P99 geometric mean: ours with moves 124 s, ours no moves 981 s (x7.9), FaaSPR routing no moves 976 s. Median per-case ratio fp_route_nm / ours_nm 1.031 (3% slower), geometric-mean ratio 0.996; fp_route_nm lower in 6/18. The earlier table row ("-7.0% (-29 to +11), 12/18") used the asymmetric per-case formula (x - ref) / x, driven by three F2 seed-3 cases where routing is 0.42-0.66 of ours_nm; use log ratios or medians for noisy comparisons. Mean latency 162.6 vs 210.5 s (23% lower with routing); storage-wait retries 86 vs 307; cold starts 1,300 vs 1,271 (ours with moves: 1,402, +10% for x7.9 on P99).
- Interaction in the 2x2 is -1.30 on the log scale of P99: the combined reduction is e^1.30 = 3.7 times the product of the separate effects. Deck slide 20 caption states the sign.
- workflow_stress.py: first design (storage unchanged) cannot finish at k = 10 (Little's law: requests in flight need 2-7 times the cluster storage); storage now scales with k.
- Moves per request in short smoke runs (30-37) vs full runs (2.4-3.5): short windows are dominated by the start-up transient (moves in the first minutes divided by few completed requests); not comparable across run lengths.

## [2026-10-25] experiment | workflow-structure diagnostic built; stress pilot started
- dfps/sim.py: optional per-task trace (Sim(trace=True)); dfps/diagnostics.py: realised critical path decomposition (execution / wait of unmoved and moved tasks / transfer, exact sums), fracturing (edges whose parent ran away from its plan or whose child was relocated; local edges planned vs final), wait on and off the critical path, join gap.
- Smoke test, state sizes x1 -> x10 with storage scaled (F1 85%, seed 1, short window): ours 150.7 -> 286.4 s P99, stack (HPA + JSQ) 162.7 -> 503.7 s; ours' P99 advantage over the stack 8% -> 43%.
- First breakdown (ours, F1 70% seed 1, 130 s window): sojourn 53.5 s = exec 21.9 + wait 10.8 (unmoved) + 17.2 (moved) + transfer 3.6; local edges 38.6% planned -> 17.7% final; 66% of edges fractured; 41% of the wait is on tasks off the critical path. Tail (19 requests): 139.4 s.
- workflow_stress.py run 10 started (144 runs, trace recorded in every run); results/wfstress.txt on completion.

## [2026-10-25] query | decision rules for workflow-aware improvements, written before the pilot results; novelty of slack-aware ordering
- [[workflow-aware-decision-rules]] fixes thresholds for R1 (re-binding), R2 (slack-aware ordering), R3 (critical-path-weighted placement) and the success criterion for anything built, with 0 of 144 pilot runs finished.
- Web search: slack-aware / critical-path ordering is published (Archipelago, GrandSLAm, Fifer, Llama, Sledge EDF vs SRSF, METIS); added to [[baseline-matrix]]. R2 is not a new idea.
- Median re-check of the FaaSPR rows (18 dev cases, log ratio variant / ours): fp_route median 1.022 (95% bootstrap 1.008 to 1.036), slower in 16/18; fp_place median 1.021 (1.006 to 1.040), slower in 14/18. Both are about 2% slower than ours, small but detectable; the earlier "+1.6% (-0 to +3), no detectable difference" wording for fp_place came from the mean of (x - ref)/x and is replaced.

## [2026-10-25] meta | working principle: diagnose, map related work, then look for novelty
- User instruction recorded in memory. New page [[novelty-register]]: seven diagnosed problems (fracturing, slack-blind queues, transfer-blind moves, placement churn, tail that routing cannot repair, low-load floor, overload) with evidence, nearest work, remaining gap, status.

## [2026-10-25] query | documented literature search on the open questions of the novelty register
- [[literature-search-2026-10-25]]: 14 new queries (26 in all over two sessions), web search only, snippet level; answers to the four open questions; reading list (CLASP, TensorCast, Zhao and Sakellariou, Bittencourt and Madeira, Chen et al. 2015, Janus, Pheromone, Metronome, ContinuumBench, Databelt). Findings: no serverless paper re-binds dependents after a move (grid-workflow lineage and ClusterFlow, Pheromone, Janus are the precedents); no 2025-2026 paper found measuring tail scaling with state size against off-the-shelf rules; adjacent queued-request migration work is larger than listed before (CLASP, TensorCast). ClusterFlow citation corroborated by one independent reference list; publisher page not retrievable; DesFaaS found by no source except ClusterFlow itself.

## [2026-10-25] query | synonym sweep and cross-check against an independent search report
- Eight more queries (epoch-based, receding horizon, queue draining, pending invocations, backlog, re-binding unstarted, Tremulant, Styx/iRoute): nothing new academically except CLASP again. Independent report agrees on the headline but misses the adjacent precedents (CLASP, TensorCast, Llumnix, grid lineage) and names two papers (Tremulant, iRoute) that could not be found. Addendum in [[literature-search-2026-10-25]].

## [2026-10-25] query | external method suggestions checked against the code and the literature
- FAMG already in Sol.aet; LAQP vacuous by construction (inputs stored at the node before enqueue); AnchorDL and AeroFlow not found; ClusterFlow does price severed edges. Recorded in [[novelty-register]].

## [2026-10-25] experiment | stress pilot 87/144: first results; rules R1-R3 evaluated; trace overhead check
- Trace on or off gives identical results (F1 85%, seed 1, 140 s: P99 150.6956 vs 150.7, mean 67.18 vs 67.2, 639 cold starts, 2,405 completed): instrumentation does not change the simulation.
- Ours' P99 advantage over the stack (HPA + JSQ, our placement) at k = 1 -> 10: mix 85% +16.5% -> +48.1%; chain12 +11.5% -> +41.2%; mix 70% (k = 10) +52.2%; wide16 (k = 10) +64.9%; layered12 (k = 10, one scenario) +29.5%. Against B*: +57.8% to +81.6% at k = 10.
- Rule evaluation in [[workflow-aware-decision-rules]]: R1 (re-binding) does not fire (1 of 5 groups); R2 (slack ordering) fires; R3 confounded by churn.
