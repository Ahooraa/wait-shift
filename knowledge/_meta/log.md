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

## [2026-10-25] query | lambda x T proposal checked; interaction by load computed from the existing 2x2
- Old 2x2 (18 cases): interaction -0.21 / -0.66 / -0.80 at 50 / 70 / 85% load; -0.87 Azure, -0.24 Huawei. Hypothesis of substitution through staleness contradicted by the layout-age data. Recorded in [[novelty-register]].

## [2026-10-25] code | staleness and data-aware-planning diagnostics built, thresholds pre-registered
- dfps/controllers.py: demand_points/queue_aware_placement take affinity=True/False (drop the workflow-partner term, keep origin + capacity + queueing). dfps/o3s.py: O3SimAdjuster._staleness (count-mismatch vs ideal sizing, no solve) and _placement_mismatch (no-solve locality lower bound: share of live containers outside their function's own attraction-ranked top nodes); logged every move tick as (t, count_mismatch, placement_mismatch, backlog) when churn["log_staleness"]. place_kwargs passes churn["affinity"] through for placement="qaware".
- output/data-analysis/staleness_probe.py (6 dev cases, 50/70/85% load) and affinity_probe.py (mix + chain12, k in {1,10}) written; smoke tests (short windows) confirm both run; full runs not yet queued.
- Pre-registered thresholds for both in [[workflow-aware-decision-rules]], written before any full-length result: D1 needs bursty drift (CV>1) AND mismatch predicting backlog (corr>0.3) AND a real cold-start saving over 30s cadence; D2's interesting outcome is a SMALL loss at k=10 despite the 9-14% ceiling (current term capturing little headroom), not a large loss (term already load-bearing) or a flat result (direction dead).

## [2026-10-25] experiment | D1 (staleness) and D2 (affinity) full runs finished, applied against pre-registered rules
- D1: burstiness-by-family passes (Huawei CV > Azure CV at all 3 loads); mismatch predicts BACKLOG (4/6 cases, corr>0.3) but not the TAIL proxy (2/6, near-zero/negative at 85% load in both families); cold-start-saving criterion untested. Trigger not built. Placement-mismatch calibration: corr(proxy,true)=0.22 (weak instrument), true mismatch negative in 13/15 samples.
- D2: mixed across scenarios -- mix 70% k=10 +10.0% (load-bearing), mix 85% k=10 -3.4% (noaff better), chain12 k=10 +1.4% (small loss despite the 10.6% ceiling -- the pre-registered "interesting" outcome). Cold starts flat (not churn); moves/request higher without affinity in every row (move-mediated confound confirmed, as pre-registered). Single seed, not closed; chain12 flagged for a second seed.
- Full results and the applied criteria in [[workflow-aware-decision-rules]].

## [2026-10-25] experiment | bounds table complete (all 6 scenarios); operating envelope launched
- layered12 k=10 bound finished (~4.7h wall time, replay error 0.0): the SMALLEST ceilings of any shape (re-binding 0.4%, co-location 0.9%, slack 0.7-2.7%), smaller than wide16 despite denser structure -- a dense DAG has many comparable-length paths, so fixing one does not move P99. Full 6-row table in [[workflow-aware-decision-rules]].
- output/data-analysis/operating_envelope.py: 48 runs, load {50,70,85,92%} x data scale {1,10,20} x {F1,F2} x {ours,stack}, no admission at 92% (raw overload behaviour). Fresh scenarios via traces.build_trace_scenario (arbitrary rho; needs data/alibaba_dags_lt60s.json passed explicitly) + dfps.nsga2 directly for the initial layout (experiments.run pulls in torch, OMP error #15, same issue admission_sweep.py hit). New diagnostics.py stat: pingpong = share of tasks moved >=2 times (free on any new trace run).

## [2026-10-25] meta | interaction-hunt closed; substitution sentence corrected with interval; envelope hardened
- "Sizing enables moves via a free slot" checked against the code: wrong for the fixed budget (every slot always holds a container; moves need storage, not an empty slot). Elastic-mode version has no moves-off arm among el50/65/80 (all rebal_max=10**9) -- not a free analysis, not built. No further interaction hunting.
- Placement x moves substitution restated with its real interval (paired +0.2%, -1 to +1, 8/18 wins, log 23 Oct) rather than the unqualified "equal"; talk deck slide 18 updated (version 6). "Substitutes" (cross-derivative) is NOT established -- we lack a moves-off x placement cell; the safe claim is "no detectable P99 effect with moves on," stated as such in [[novelty-register]].
- operating_envelope.py: added completed/arrived reporting and a censoring warning per cell (92% load with no admission can leave requests unfinished); jobs interleaved by load instead of heaviest-first, since a smoke test of one 92% cell reached 1.1 GB working set in 140 s -- running every high-memory cell concurrently at grid start would risk an OOM. The 92% smoke run was left running (could not be killed: Bash process-termination is blocked by this session's auto-mode); full grid not yet launched, pending it settling.

## [2026-10-25] experiment | operating envelope launched (32 runs, k=20 dropped)
- First data point (smoke, rho=0.92 k=1 ours): clean, no censoring, P99 159.95 s (vs 157.8 s at 85% load). Ping-pong 17.7% of moved tasks moved >=2 times -- inside the range worth a cooldown rule per the earlier pruning-idea review, one cell only so far.
- k=20 dropped from the grid after the stack/92%-load/k=20 smoke cell ran 26+ min / 1.1 GB with no result (user stopped it). Grid now 32 runs: load {50,70,85,92%} x k {1,10} x {F1,F2} x {ours,stack}, launched with 8 workers.

## [2026-10-25] experiment | move-gain probe (Phase 0, check 3): dispersion-scaled margin killed
- dfps/o3s.py: gain_log added to rebalance_step (one line, gated by churn["log_gain"]), no cost when off.
- 8 runs (F1/F2 x 50/70/85/92% load, k=1, ours only): mean gain 7-11s (50%) to 11-15s (92%), rising not collapsing; median stable 5.4-6.7s; near-zero-gain share flat 4-6% at every load. Candidate killed per its own pre-registered criterion. Full table and reasoning in [[novelty-register]].

## [2026-10-25] experiment | P3 scaling probe: family-dependent curve, not a universal law
- 28 runs (output/data-analysis/p3_scaling_probe.py), rho=0.85, k in {0.5,2,3,5,7,10}, seed-2 noise check at k=3,5.
- Delta-gap(k) monotone in k for both families (pass); cross-family validation fails (F1 climbs earlier/faster than F2, family gap 15-22 pts, above the 2-10 pt noise floor). tau tracks Delta-gap within family (r=0.98/0.84) but not between. Full table and verdict in [[workflow-aware-decision-rules]] and [[novelty-register]].

## [2026-10-26] experiment | lambda sweep Gate 0: axis binds, proceeding to Gate 1
- 6 runs (output/data-analysis/lambda_probe.py), k in {1,5,10} x {F1,F2}, seed 1, free re-scoring of 165k-205k logged decisions per cell. Flip rate 16-34% at lam=0, well above the 15% threshold at k=10 for both families (26.1%/30.4%). Gate 0 passes decisively; launching the 48-cell Gate 1 matrix. Full table in [[workflow-aware-decision-rules]].

## [2026-10-26] experiment | lambda sweep Gate 1: default weight wrong, no adaptive mechanism
- 48-cell matrix (output/data-analysis/lambda_gate1_probe.py). lam=0.5 beats lam=1 in 9/12 cells, effect grows sharply with k (+-3pts at k=1, -7 to -47pts at k=10 vs lam=1; lam=2 is much worse, +18 to +38pts at k=10). Gate 1 fails: both families want the same lam=0.5 at k=10, no family-dependent split. Verdict: engineering tuning fix (lam~0.5 is a better default), not a novel adaptive mechanism. Refinement sweep (lam in {0.25,0.75}, k=10) running to locate the minimum more precisely. Full tables in [[workflow-aware-decision-rules]] and [[novelty-register]].

## [2026-10-26] data | lambda sweep refinement, k=10 (8 runs)
- lam in {0.25, 0.75} added either side of 0.5 (output/data-analysis/lambda_refine_probe.py). Revised minimum: 3 of 4 cells minimize at lam~0.25, not 0.5; lam=0.75 flips to a small penalty in 2/4 cells (F1 s2 +0.2, F2 s1 +5.8) -- a sign flip the coarser Gate-1 grid could not see. lam=0.25 never crosses zero across all four cells (sum -77.4 vs -73.6 at lam=0.5), the more robust single constant.
- Does not reopen Gate 1's cross-family verdict (lam=0.25 still wins for both families) -- only moves the recommended retuned constant from ~0.5 to ~0.25. Full table in [[workflow-aware-decision-rules]]; novelty-register updated.

## [2026-10-26] decision | lambda sweep: stop refining, record pipeline-fix provenance
- Decision (user): no further lam-seed/lam-value runs for this thread. 2 seeds x 6 lam values establishes an interior plateau below lam=1 but can't resolve a ~5-point difference against a ~45-point seed-to-seed noise floor without ~10 seeds/cell for a payoff capped at ~1 point of P99; the plateau itself (lam in [0.25,0.5] all comparably better than 1) is the finding, not a pinned optimum.
- Provenance recorded: the refined table's lam=1 baseline lookup was edited mid-run (commit cfd36e3) to fall back to the Gate-1-run fresh (k=10,seed=2) cells in results/lambda_gate1/ when the fixed existing_lam1() map has no entry for them (it only covers k=1/k=5 reuse). No new simulation; same Gate-1 P99 numbers, just widened what analyze() reads. Pre-fix script reproduces only the seed=1 rows. Noted in [[workflow-aware-decision-rules]] and [[novelty-register]].

## [2026-10-26] decision (user) | lambda sweep stop-decision reversed; seed-expansion launched
- User reversed the "stop refining" call (same day, see entry above) and asked to run the more-seeds-at-k=10 experiment instead of more lam values. output/data-analysis/lambda_seeds_probe.py added: seeds 3-10 x lam in {0,0.25,0.5,0.75,1,2} x {F1,F2}, k=10 (reuses lambda_gate1_probe.one(), same RUNS dir/schema). 95 runs launched detached (PID 1157, 6 workers, log /tmp/lambda_seeds_batch.out), ~305s/run observed on smoke test.
- Goal: resolve whether lam=0.25 genuinely beats lam=0.5 (pooled ~5-point difference seen at n=2) once n~10 seeds/cell are available, against the previously-estimated sigma ~45 noise floor.

## [2026-10-26] data | baseline-matrix updated with the final_ablation.py result (was stale)
- results/fx.txt (completed 24 Oct, 18 dev cases) had landed but baseline-matrix.md still said "re-running" / "earlier result on older controller". Updated with final numbers: HPA +2.3% (12/18 wins, HPA keeps ~98% of our gain), Fifer +32.1% (16/18, 4.4x our cold starts), Kraken +6.2% (13/18), jsq +11.3% (18/18), steal +35.2% (18/18, widest margin), textbook stack (hpa+jsq) +14.2% (18/18). All still gain 32-60% over best-existing (B*/RL/RL_CAL) despite losing to FROZEN-2.

## [2026-10-26] task | FaaSPR: smoke-tested, metrics aligned to the paper's own, load x state-size grid launched
- Smoke test (F1 r0.7 s1, 140s): fp_place and fp_route healthy (fp_route: 12.6% task-level storage-repair fallback, unplanned 0.3%). fp_both NOT sane yet: 47.5% of requests unplanned (storage-feasibility interaction between FaaSPR's own placement and routing, not seen in either alone) -- held back, not run at scale.
- User asked to check FaaSPR's own reported metrics (read from knowledge/sources/jia-2025-faaspr.md, already ingested): average latency, P99, resource consumption -- not just our P99 headline. faaspr_sweep.py grid_analyze() now reports all three (avg_makespan, p99_makespan, mean_containers as the resource-consumption proxy).
- output/data-analysis/faaspr_sweep.py extended with a load x state-size grid (grid_run/grid_analyze): ours/fp_place/fp_route x F1/F2 x rho in {0.5,0.7,0.85} x k in {1,5,10} x seed=1 (54 runs), rebuilding scenarios via p3_scaling_probe.build generalised over rho, rather than reusing fixed-k D1 pickles. Launched detached (PID 1345, 3 workers), followed automatically by the original fixed-k dev grid (fp_place/fp_route, 36 runs).

## [2026-10-26] fix | FaaSPR comparison caveat: not the same P99 as the paper (user caught this)
- User correctly flagged that fp_place/fp_route P99s are not comparable to FaaSPR's own published numbers (different hardware/workload/scenario entirely: CloudLab 8x64-core + remote Redis + 6 named workflows + Azure top-2% trace vs our edge-node simulator + SeBS-Flow/Alibaba DAGs + calibrated F1/F2 traffic). Clarified in baseline-matrix.md: the comparison is "FaaSPR's algorithm ported as a swap-in inside our own controller/scenario" (same as every other row in sections 2/4), valid only within our own simulator (fp_place/fp_route vs ours, same seed) -- never against the paper's absolute figures. "Beat FaaSPR on its own metrics" (prior entry) means same metric TYPES, not same numbers.

## [2026-10-26] ingest (re-read) | jia-2025-faaspr: precise latency-metric definition (user question)
- User asked whether our P99 and FaaSPR's P99 are the same metric. Re-read pp. 2068-2069, 2072 from an unprotected copy (pikepdf strips the owner-password restriction; library PDF opens with empty user password, no re-acquisition needed). Found: FaaSPR's LP internal latency variable excludes cold starts (p. 2069), but the REPORTED evaluation metric ("99th tail latency", Fig. 8b) is the full per-workflow completion latency including cold starts/queueing/transfer -- same statistical object as our p99_makespan, comparable in kind (never in absolute magnitude, different hardware/workload). Resource consumption formally defined (p. 2072): sum of resource-occupation x execution-time product, normalized to FaaSFlow -- closer to our provisioned_slot_s than mean_containers, though neither is an exact unit match. Added as source-page addendum (jia-2025-faaspr.md, section 14).

## [2026-10-26] task | FaaSPR port: fp_both storage deadlock fixed; algorithm/formula fidelity audit
- Diagnosed fp_both's 47.5% unplanned rate (faaspr_both_diag.py): FaaSPR's grouping placement consolidated 6 of 30 functions onto a single host; one such host sat at -10 to -19 units of free storage continuously, leaving FaaSPRRouter's per-task repair step zero fallback candidates (the paper's routing LP constrains only execution-rate capacity, never our model's explicit per-node storage budget). Fixed with a minimum-replication floor in dfps/controllers.py::faaspr_placement (adaptation 5, swap-based, conserves both functions' totals): any function with >= 2 instances is kept on >= 2 hosts. n_unplanned dropped 2410 -> 0 on the same case; residual exception is the one function with exactly 1 total instance (cannot be split regardless). fp_both added to faaspr_fig11.py and faaspr_sweep.py's GRID_VARIANTS/grid_analyze as a genuine "whole ported design" comparison point; 18-cell grid launched.
- User asked for a careful fidelity audit of the ported algorithms/formulas before trusting a "whose design is better" comparison. Re-read Sec. IV (Algorithms 1/2, horizontal/vertical grouping + migration-minimizing priority) and Sec. V (Constraints 1-3, the LP objective, multi-stage threshold search) directly from the paper text and checked line-by-line against dfps/controllers.py::faaspr_placement and dfps/dispatchers.py::FaaSPRRouter. Verdict: faithful, no correctness bugs. Found and disclosed three previously-undocumented approximations (now in the functions' own docstrings as adaptations 6/7): (1) the cold-start reuse ratio uses the horizontal group's actual (possibly uneven) instance share rather than the paper's idealised even-split denominator; (2) the transmission-saving term's edge weight uses a flat network-average hop count rather than a pair-specific cost, since the paper gives no explicit edge-weight formula; (3) the routing fallback for a workflow whose LP-solved frequencies are all ~zero (uniform distribution over near-best-latency paths) has no paper counterpart -- needed only because our sampled path set is non-exhaustive, unlike the paper's.

## [2026-10-26] task | state-transfer modeling check: topology-mismatch finding, confirmed empirically
- User asked whether state-transfer/data-transfer cost is modeled suitably, worried our superiority over FaaSPR might come from under-modeling it. Checked dfps/network.py::Network.stt -- a real store-and-forward multi-hop formula (hop_count x (epd + size/bw)), identical code path for every controller (no per-controller discount), magnitudes realistic (0.2-4s/hop on 10-200+MB states at bw=50MB/s, vs 2-10s exec times), epd=0/bw=50 inherited from the original DFPS paper project-wide, not introduced for this comparison. In faaspr_fig11.py's breakdown, transfer is the single largest driver of the ours-vs-FaaSPR-ported makespan gap (15% of makespan for ours vs 35-36% for fp_route/fp_both).
- Root cause found by reading the placement code, not assumed: dfps/controllers.py::affinity_placement_v2 and ::transport_placement (our own default placement paths) both cost against EXACT pairwise hop distances to a partner function's real current location (`h[k, nodes_g]`). FaaSPR's own published Algorithm 2 priority formula (faithfully ported, see 2026-10-26 fidelity-audit entry above) has no distance term at all in its transmission-savings calculation -- only co-location probability x a flat per-edge weight, correct for FaaSPR's own flat single-switch 8-server CloudLab cluster but structurally blind to the distance variance of our 80-node multi-tier edge topology (confirmed: mean hop 4.87, range 1-8, diameter 8).
- Hypothesis tested directly, not just argued: ran all four variants (ours/fp_place/fp_route/fp_both) on a new matched-setup scenario (output/data-analysis/faaspr_match_setup.py, built this session) -- FaaSPR's own cluster shape (8 servers, flat all-to-all hop=1 topology, 50MB/s, ~322 slots from the paper's ~402GB/~1.25GB-per-instance) and trace shape (individual Azure top-2% traces rate-matched to the paper's own 203.8 req/min average, aggregate-scaled by 1/15 for the 15-concurrent-workflow residual mismatch -- our workflow corpus is kept, see faaspr_match_setup.py's docstring for the full chain of fixes). Result: on the flat topology all four variants converge (p99 75.4-77.0, transfer 0.41-0.68s -- noise-level spread), versus the 80-node edge topology's 2-4x gap (p99 157-261, transfer 9.9-39.0). Confirms the topology-mismatch explanation empirically: FaaSPR's algorithm is only at a disadvantage on topologies with real hop-distance variance, not against a simulator bias.
- Conclusion communicated to user: state-transfer modeling is realistic and applied identically to every controller; a meaningful share of "our" advantage in the FaaSPR comparison is attributable to a genuine domain mismatch (FaaSPR's design fits a flat cloud rack, not a multi-tier edge topology), which should be stated explicitly in any writeup rather than left as an unqualified "ours wins."

## [2026-10-26] task | Graph-Aware dispatcher + its paper's baselines; FaaSPR lam confound fixed; moves-off arm
- Ported Liang et al. 2026 (Future Internet 18:265) Graph Scheduling and its baselines as dispatcher swap-ins in dfps/dispatchers.py: GraphAware (Eq. 21 with eta=gamma=0, min-max normalised per decision, per-plan Psi update; 6 fidelity caveats in its docstring), RoundRobin, resource_fit, heft_like (upward rank, EFT with max(data ready, node ready)); Comm.-Cost-Aware Greedy == existing greedy_eft; MLP-Based Scheduler not ported (learned, unpublished weights). Runner output/data-analysis/graphaware_sweep.py; beta selection rule fixed before tuning (5 values on 4 dev cases, mean P99/best-per-case). Smoke test (F1 r0.85 k5, 60 s window) clean for all five.
- Methodology (user question): a dispatcher is a single decision layer, so these rows are layer swap-ins (baseline-matrix section 5), never a whole-system comparison. Moves-off arm added (FROZEN2 + rebal=False; no_inner stays True) to separate dispatcher quality from what our request moves repair.
- Fixed a confound introduced earlier today: fp_place/fp_route/fp_both keep our request moves, so lam is our parameter there too; they now use lam=0.5 like "ours" (faaspr_sweep GRID_VARIANTS, faaspr_fig11, faaspr_match_setup). Dev-grid VARIANTS stay at lam=1.0 (their reference is lam=1.0). Stale lam=1.0 results moved (not deleted) to results/faaspr_grid/stale_lam1/, results/fig11_rich/stale_lam1/, results/stale_lam1/; the grid fp_place cells also predated the minimum-replication floor fix.
- Runs chained behind existing jobs (free RAM ~0.7 of 16.5 GB): GA tune -> pick -> moves-on grid (72) -> moves-off arm (108); after the lambda sweep: FaaSPR grid reruns (54) -> Fig. 11 fp_* (6) -> matched-setup fp_* (3).
- Beta tuning, first case (F1 r0.85 k10): P99 355.1 / 358.8 / 342.7 / 331.8 / 317.0 for beta 0.25 / 0.5 / 1 / 2 / 4 (DFPS matcher, same case: 321.3) -- falling up to the top of the grid. Declared extension (user decision, made on this one case only): if the rule picks beta=4, add beta in {8, 16} on the same 4 tune cases and re-apply the rule; no further extension, a 16 win is frozen and reported as a boundary optimum. Implemented as `graphaware_sweep.py select` (tested on synthetic curves for all three outcomes); the GA chain now runs select -> run -> run_nm.

## [2026-10-27] decision (user) | research scope fixed: placement/re-placement under externally-sized containers
- User's motivating concern: inconclusive baseline search traced partly to an unclear scope (mixing sizing and placement). Decided, across a working session, to narrow the contribution to runtime placement, relocation and request-move decisions, with per-function container counts taken as an external autoscaler input (not a contribution) -- grounded in [[baseline-matrix]]'s own ablations (HPA-style sizing swap kept ~98% of the controller's gain; disabling request moves raised geometric-mean P99 8x).
- Extended twice at the user's request, each time toward more realism for an eventual Q1-journal submission with testbed validation: (1) heterogeneous container resource weights (continuous GB, matching [[jia-2025-faaspr]]'s 0.5-2GB range) replacing DFPS's uniform-slot assumption -- turns placement into vector bin-packing, and flags that DFPS's own placement formula is not well-defined under continuous weights (recommended: homogeneous-regime-only DFPS baseline for phase 1, a weighted port deferred); (2) compute resource contention (linear processor-sharing slowdown under node CPU overload) and network link contention (max-min fair sharing per hop under concurrent transfers, small fixed same-node overhead) -- both new simulator mechanisms, not yet built; every existing baseline-matrix result predates them and will need re-running once they exist.
- Recorded in full as [[problem-scope]] (10 sections + open-decisions list: D2 count-fitting rule, DFPS fairness, spatial workload realism, container-weight distribution shape, D8-D10 contention model choices). `input/description/project-description.md` still the empty template -- not yet filled in from this.

## [2026-10-28] task | move-rule penalties, Step A: dimensions and causes of the P99 problems (no new mechanism built)
- Context: slack_frac_aware (dfps/o3s.py rebalance_step, 2026-10-27; urgency_gain / pingpong_penalty / frac_penalty, default off) tuned on the full 900 s F3 window: urgency 0.02/0.05/0.15 -> P99 215.7/207.5/217.8, frac 0.5/1.0 -> 207.1/208.6 (baseline 211.37). User: flat constants are scenario-blind; find the right dimension and cause for each term first, and separate adaptive re-moves from thrashing before penalising ping-pong.
- Scripts: output/data-analysis/penalty_stepA_collect.py (one baseline run, logging only: every relocation with source, queue position, AET parts; every start), penalty_stepA_analyze.py, penalty_stepA_extra.py; reports in results/penalty_stepA/. Move counterfactual = the (pos+1)-th start at the old pool after the move (FIFO slot); a first version using the queue neighbours was biased (the run behind a moved run has almost always moved too -- the rule stops a queue at the first non-mover) and was replaced.
- Findings: (0) the whole tail is the top critical-path quartile (CP >= 26 s); their stretch is not higher, so P99 is an absolute-seconds problem. (1) fracture cost is exactly dhops x (epd + size/bw), 98% caused by our own rebalance moves; relevance (on the realised critical path) is predicted by the child's structural float (AUC 0.75), not by state size (0.42): 64% for zero-float children vs 19-29% otherwise -- AET's uniform lam=0.5 misweights both. (2) join gap is ~95% desync, not structure (tail 50.4 of 53.3 s); a task that is the last missing input of its join is on the critical path with P = 0.99-1.00 (vs 0.08-0.19), but only ~6 s/request of tail wait accrues after that point -- most desync builds upstream. (3) urgency: the SLO-budget slack used by _slack ranks tail-critical tasks worst (AUC 0.65; budget 3xCP gives the tail's own large workflows MORE slack); absolute projected sojourn (elapsed + remaining critical path) 0.91. (4) re-moves are not thrashing on average: returns are the best moves (net +7 s, 28% harmful; they undo fracture), onward re-moves ~ first moves; what hurts is low predicted gain relative to the function's service time (gain < 0.25 mu: realised ~0, 52-58% harmful), whatever the move count. Outcome-conditioned "tail critical path" move rows look negative but are selection-biased; the ex-ante large-workflow class is positive (+3.6 s net).
- Open: margin normalisation (absolute vs mu vs mu/sqrt(c)) is not separable here (mu spans only 3.6-9.3 s; AUC 0.653-0.664) -- needs Step D on other scenarios. Proposed formulas await user approval before Step B/C.

## [2026-10-28] task | move-rule penalties, Step A by workflow family (user: length bias + selection bias)
- User concern: the pooled P99 tail is 98% fork-join (mostly the 16-task, CP 53.7 s type), so pooled diagnostics optimise for long DAGs; and outcome-conditioned tail rows are selection-biased. Re-ran on the same baseline dump: output/data-analysis/penalty_stepA_family.py, report results/penalty_stepA/report_family.txt. Families derived from DAG structure, not assumed: chain (5 types, 7847 req), fan-in (4, 5171), fan-out (1, 1020), fork-join (5, 6263); worst 10% taken within each family and each type.
- Bottlenecks of each family's worst 10% (share of its extra sojourn over the other 90%): moved-task wait is the largest everywhere (35/51/43/46% chain/fan-in/fan-out/fork-join -- congestion the moves were trying to fix, not harm from moves: ex-ante moves are net positive in every family); service-time noise 14-30% (not addressable by placement); join desync 32% fan-in, 24% fork-join, 0 elsewhere; fracture extra-hop 5-13% (largest fork-join). So the join term is family-specific, the fracture term is a minor contributor everywhere.
- Selection bias, measured: conditioning on the family's P90 still flips the sign of move value (fan-in critical-path moves: -2.81 s net in the worst 10% vs +4.63 s in the other 90%; ex-ante +3.7 s). P90 does not remove the bias -- only ex-ante cuts do; P90 kept for robustness reporting, not for validating move value.
- Robust across all four families (ex-ante): moves with predicted gain < 0.25 mu are net ~0 or negative (46-60% harmful), >= 0.5 mu clearly positive; returns are the best-value re-moves in chain/fan-in/fork-join.
- Urgency: within one workflow type every slack variant is the same quantity shifted by a constant; they differ only across types. Against each request's own family's worst 10%, absolute projected sojourn wins (AUC 0.775); against its own TYPE's worst 10% (the fair target) it drops to 0.628 and projected sojourn / type median sojourn wins (0.749). The urgency dimension therefore encodes the objective (pooled P99 vs per-type tails) -- a user decision.

## [2026-10-28] task | move-rule penalties, Steps B/C stage 1 (full 900 s F3, 3 seeds, burn-in 120 s): no term beats the baseline reliably
- Implemented dfps/o3s.py::_rebalance_terms (churn move_terms: margin_theta, urgency_priority [projected sojourn / type's online median], join_gate, relevance_out [edge classes 1.0 cut edge / 0.39 / 0.21, derived in Step B]); sim.py keeps soj_log. Driver output/data-analysis/penalty_stepBC.py, reports results/penalty_stepBC/report_stage1.txt. Flag on with every term off reproduces the baseline exactly (211.37 / 70430 moves).
- Burn-in: moving the cut from 60 s (simulator warm-up) to 120 s changes pooled P99 by +0.3% (243.2 -> 244.0) and no family by more than 0.9%: no startup transient to remove; the regime shift is visible (stretch peaks 3.6 at 600-660 s, 2.4 after 720 s).
- Each seed draws a DIFFERENT workflow set (fan-in types 4 / 1 / 0 in seeds 1 / 2 / 3, chains 5 / 6 / 9): seeds are not replicates; fan-in evidence is seeds 1-2 only; baseline pooled P99 per seed 210 / 220 / 302, so a percentile pooled over seeds is dominated by seed 3 (it made fork-join look worse while 3/3 seeds were individually better) -- use per-seed changes with paired request-level bootstrap.
- Result (mean over seeds of per-seed P99 change, paired bootstrap 95% CI): margin 0.25 +2.0% [+0.7,+3.6] pooled, fork-join +3.5% [+1.5,+4.9] (significantly WORSE); 0.375 +1.7%, 0.5 +2.5% worse; 0.125 +0.2% [-1.3,+1.5] pooled but chain +4.7% [+2.2,+7.6] worse. Margins cut moves 6-21% at no P99 gain. Urgency +0.2% [-1.3,+1.7], join gating +0.5% [-0.8,+2.0]: null. Relevance -1.4% [-2.6,-0.1] pooled (fork-join -1.3% [-2.9,+0.5]; per seed -1.1/-3.3/+0.3): the only nominally positive cell, one of ~56 tested, so not established. P99 noise per run is ~2-3%.
- Consequences: (1) the 2026-10-27/28 single-run readings of slack_frac_aware (urgency 0.05 -1.8%, frac 0.5 -2.0%) are within this noise and must not be cited as wins; (2) Stage 2 as specified (margin 0.25 + terms) is not run: 0.25 is significantly worse and the margin rule's Step A premise (low-gain moves are coin flips) does not translate into a P99 gain; (3) stage 3 (margin 0.125 + urgency/join combinations, and urgency x join with no margin) still running, 7 runs; its numbers decide whether the interaction hypothesis (urgency and join gating complement each other) has any support.

## [2026-10-28] task | move-rule penalties, stage 3 (margin 0.125 combinations, urgency x join): null; DAG Topology Suite launched
- Stage 3 (full 900 s F3, 3 seeds, burn-in 120 s, paired-bootstrap CI over per-seed changes): m125+U +0.0% [-1.4,+1.1], m125+J -0.1%, m125+UJ +0.5%, UJ (no margin) +0.4% [-0.9,+2.0], m125+UJR +1.8% [+0.4,+3.2] (significantly worse; fork-join +2.7%). No synergy between urgency and join gating; urgency does not rescue the margin; relevance is not additive (alone -1.4% in stage 1, +1.8% inside the four-term set) -- consistent with its stage-1 signal being noise.
- Suite (user request): output/data-analysis/dag_suite.py (five archetypes x 15 variants, structure fixed across seeds so seeds are true replicates; F3 arrivals, rho 0.7, data x1, heavy x10) and dag_suite_run.py (baseline vs U / J / R isolated, composite also UJR and the pair runs UJ, UR, JR; join-gating firing counters in O3SimAdjuster.term_stats). Note: relevance on a chain is a downstream-weight change 0.5 -> 1.0 (all edges are cut edges), reported separately. Results in results/dag_suite/.

## [2026-10-28] task | DAG Topology Suite + physical check: relevance dropped, join gating inert on its targets; placebo noise floor running
- Suite (results/dag_suite/report.txt; 5 archetypes x 15 variants, 3 seeds, paired request bootstrap). Pre-registered rules: join gating diamond -0.2% [-1.4,+1.3] (1/3 seeds), grid -0.2% [-1.7,+1.5] (2/3) -> not a win; relevance on data-heavy +0.1% [-1.6,+2.3] -> dropped; relevance on chain (weight change 0.5 -> 1.0) -0.7% n.s.; UR vs U directly +0.5% [-0.9,+2.0] n.s. Join gating fires only where joins exist (chain 0 of 272k candidates; diamond 2.0%, grid 3.3%, composite 1.5%, heavy 1.7%); ~99% of gating candidates move.
- Not pre-registered: composite U/J/R/all six pairs and triple -1.3 to -4.0%, all 3/3, interactions all ~+3 -- the signature of a high-luck shared baseline (request bootstrap does not see run-to-run trajectory noise). Heavy J -3.9% [-5.5,-2.0] 3/3. Placebo controls launched (baseline policy, move clock 2.001 / 1.999 s; dag_suite_run.py P1/P2): seed 1 placebos already move P99 by about +-1.5%.
- Physical check (physical_check.py, deterministic re-runs with trace + decision instrumentation; instrumented baseline reproduces 211.4): relevance on heavy -- critical-path extra hop -9.8%, but all-edge extra hop +8.8%, MB x hops +1.5%, relocated MB +1.7%, join desync +3.3% (all 3/3): it shifts transfer onto non-critical edges whose float is consumed under load, so it moves more bytes and buys nothing; on F3 the same pattern (all-edge extra hop +17%, MB x hops +5.5%). No gridlock: relevance vetoes 17.9% (heavy) / 11.7% (F3) of plain-rule moves but adds as many, total acceptance and backlog unchanged; with urgency it vetoes 1%. Join gating on diamond/grid: desync +0.2% / -0.7%; it changes the accept decision in only 412 / 603 of 300k / 256k evaluations -- an ordering-only lever on tasks that would have moved anyway, consistent with Step A (most desync builds upstream, ~6 s/request reachable at the gate).

## [2026-10-28] task | placebo noise floor: run-to-run P99 noise ~1.5% per run; only two marginal cells survive, both need confirmation
- Placebo (dag_suite_run.py P1/P2: baseline policy, move clock 2.001 / 1.999 s; 30 runs): per-seed P99 change vs baseline SD 1.9% (max |5.1%|), per-run sigma 1.46% (P99) / 1.49% (P90) from the 3 null runs per seed. The paired request bootstrap used so far does not see this trajectory noise and was too narrow. The composite baseline ran high-luck: its placebos sit 1.5% below it -- explains the uniform ~2% composite "gains" and the +3 interactions.
- Re-referenced to the mean of the 3 null runs per seed, Bonferroni over 19 cells (|z| > 3.0): all single terms and pairs on all five archetypes within noise. Two cells just past the threshold: composite U+J+R -3.0% (z -3.09; seeds -4.6/-1.6/-2.8; P90 -1.8%, z -1.8) -- odd structure, since no pair shows it; heavy J -3.3% (z -3.39; seeds -2.1/+0.1/-8.0) -- rests on one seed beyond the largest placebo shift, and the physical check shows desync only -1.0%, P90 -0.5%, 357 changed decisions of 150k. Neither is claimable without a confirmatory run on fresh seeds.
- Standing verdicts: margin dropped; relevance dropped (data-heavy P99 n.s., more bytes moved); join gating fails its pre-registered targets (diamond/grid, desync unchanged, ~0.1% of decisions changed); urgency null on every archetype. Detectable effect with 3 seeds at this noise: about 3% P99.

## [2026-10-28] task | criticality-aware dispatch, gate 1 (honest ceiling): data-heavy -7.6% P99 (z -7.3), F3 x5 -1.6%
- Built: Sim(queue_priority=...) hook (dfps/sim.py; None == FIFO, tests 78/78) and dfps/dispatch_priority.py (gate: join-gating run first, else FIFO; full: gating first, then (elapsed + remaining critical path) / type's online median sojourn). Uncapped (no starvation control). Runner output/data-analysis/dispatch_ceiling.py, report results/dispatch_ceiling/report.txt; 3 seeds, referenced to the mean of base + 2 placebos per seed.
- Pre-registered gate metric (pooled P99): heavy full -7.6% (z -7.26; seeds -3.5/-5.2/-14.2; P90 -4.1%) -> >= 6%, build; F3 full -1.6% (z -2.57; seeds -4.0/0.0/-0.7) -> < 3%, would not build; gate-only -0.4% (F3) / -0.9% (heavy) -> the structural override alone is not enough. Replay ceiling A_all -8 to -25% but A_unmoved only -0.7 to -4.7%: the replay mostly credited moved tasks whose wait includes relocation, as its docstring warns.
- Post hoc (not pre-registered): per (seed, type) P99, full improves 78% (F3) / 82% (heavy) of cells, median -6.5% / -5.2%, vs placebo median -0.6% / +0.4%; cells worse than +5%: 11% / 4% vs placebo 22% / 27%. Normalised urgency spreads the gain across workflow types -- pooled P99, dominated by the longest types, understates it on F3. Mean sojourn ~unchanged (-0.1% / -1.3%): priority redistributes wait toward urgent requests.
- Mechanism: gate cuts join desync 5.1% (F3) / 4.4% (heavy), 3/3 seeds both, but desync is not what sets P99; full's gain is in moved-task wait on the critical path (-2.0% / -5.3%). Uncapped full raises per-task wait P99 by 8% (F3) / 14% (heavy) -> starvation control is warranted, although no workflow type is harmed beyond placebo spread.

## [2026-10-28] decision (user) + pre-registration | criticality-aware dispatch evaluation (written BEFORE any evaluation run)
- User decisions: load diamond/grid to baseline stretch >= 3; starvation controls approved with aging 2x the function's online median wait as primary (3x, 5x sensitivity); Bonferroni with two metrics (pooled |z| > 2.95, separate threshold for the per-type sign test); priority-aware AET only as a diagnostic on data-heavy; PRIMARY metric = per-type P99 (mechanism claim), pooled P99 = SLA table. Gate-only kept to report join gating on loaded scenarios.
- Built (all default-off, tests 78/78): dfps/dispatch_priority.py QueuePriority("full", aging=2.0): tiers overdue (elapsed + remaining critical path >= type's online P95 sojourn) > join-gating > aged (wait > aging x function's online median wait; oldest first) > rest; within tiers normalised urgency. Sim callbacks on_start / won; O3SimAdjuster churn prio_aet. Calibration (dispatch_calib.py, seed 1 baseline): grid stretch 3.01 / 3.20 / 3.67 at rho 0.80 / 0.85 / 0.90 -> rho 0.85; diamond 2.41 / 2.70 / 2.89 at 0.80 / 0.85 / 0.90 -> next step 0.93 / 0.95, rule: smallest tested rho with stretch >= 3; if none, the diamond is reported as not loadable to 3 and excluded (Bonferroni stays at 8). Smoke (heavy s1): full2 P99 312.9 (FIFO base 324.0); aged tier decided 33% of dispatches.
- Registered analysis = output/data-analysis/dispatch_eval.py docstring and report(): scenarios f3 (x5), heavy, diamond, grid; seeds 1-6; nulls base + P1/P2 (move clock 2.001 / 1.999 s); variants gate, full2. PRIMARY: per-type P99 sign test over (seed, type) cells with >= 100 requests vs 1/2, p < 0.05/8, calibrated by P1 vs (base, P2) which must not reject. SECONDARY: pooled P99 vs mean of nulls, z < -2.95 and >= 4/6 seeds. PHYSICAL: full2 -> critical-path wait of moved tasks falls (mean < 0, >= 4/6 seeds); gate -> join desync falls on diamond and grid. STARVATION reported: task wait P99/P99.9/max, types worse than +5% on average, tier counts. Established = PRIMARY rejects in favour AND PHYSICAL holds. Sensitivity (descriptive only): full3/full5 seeds 1-3 all scenarios, full2_aet heavy seeds 1-6.
- [2026-10-28, same entry, before the diamond runs] Diamond calibration step 2: stretch 3.15 at rho 0.93, 3.40 at 0.95 -> rho 0.93 by the registered rule (smallest tested rho with stretch >= 3).

## [2026-10-29] result | criticality-aware dispatch evaluation -- final verdict (registered analysis, all 150 runs complete)
- All 120 primary runs (f3/heavy/diamond/grid x seeds 1-6 x base/P1/P2/gate/full2) and 30 sensitivity runs (full3/full5 seeds 1-3 all scenarios, full2_aet heavy seeds 1-6) complete. Calibration check passed on every scenario (P1 vs mean(base,P2) per-type sign test did not reject: p 0.461/0.916/0.343/0.916 for f3/heavy/diamond/grid, all > 0.05).
- **full2 (criticality-aware dispatch, aging 2x) is ESTABLISHED on all four scenarios** by the registered rule (PRIMARY rejects in favour AND PHYSICAL holds): per-type P99 sign test p = 2.97e-05 (f3, 65/90 cells improved) / 9.18e-11 (heavy, 75/90) / 1.78e-11 (diamond, 76/90) / 1.14e-07 (grid, 70/90), all well under the Bonferroni threshold 0.05/8 = 0.00625. PHYSICAL (critical-path wait of moved tasks falls, >=4/6 seeds) holds on all four. Median per-type P99 change: f3 -3.1%, heavy -4.5%, diamond -6.1%, grid -3.7%, overall median across all 360 (seed, type) cells -4.3%.
- **gate (join-gating only) is NOT established anywhere**: p = 1.0 (f3) / 0.0725 (heavy) / 0.461 (diamond) / 0.461 (grid) -- never crosses the Bonferroni threshold; f3 and diamond/grid aren't even directionally favourable at the pooled-seed level. Confirms the diagnosis that join-gating alone was never where the headroom was.
- This confirms the session's central diagnosis: the headroom Step A located was in dispatch order (who starts next at a FIFO pool), not in the move-rule layer -- none of the four earlier move-rule terms (margin, urgency, join-gate, relevance) ever touched dispatch order, and once dispatch order itself is made criticality-aware, a real, noise-robust, physically-grounded P99 improvement appears on every tested topology.
- Sensitivity (descriptive only, not part of the established claim, workload/topology-dependent):
  - full2_aet (heavy, priority-aware AET diagnostic) vs full2: median per-type P99 change +2.7% (6/6 seeds) -- making the move-rule's own wait estimate priority-aware did not help on top of full2 here; if anything slightly worse on this scenario. Diagnostic-only, no action taken.
  - full3 (aging 3x median wait, seeds 1-3) median per-type P99 change vs nulls: f3 -4.8%, heavy -6.9%, diamond -6.1%, grid -3.2%.
  - full5 (aging 5x median wait, seeds 1-3): f3 -5.7%, heavy -6.4%, diamond -6.1%, grid -3.7%.
  - Aging 3x/5x look comparable to or slightly better than the registered 2x on these 3 seeds, but this is 3-seed, non-Bonferroni-corrected, descriptive data only, per the pre-registration -- it must not be used to retroactively re-pick the aging threshold. If a follow-up wants to test a higher aging threshold as the primary variant, that requires its own fresh pre-registration, not a swap based on this sensitivity read.
- **Evaluation phase declared complete.** No code, mechanism, or threshold changes should follow from this entry without a new pre-registration.

## [2026-10-29] decision (user) + pre-registration | aging-multiplier selection (written BEFORE any of these runs exist)
- User decision: do not add new mechanism (no per-workflow-type adaptive setting, no formula) -- the full2 mechanism's per-type harm/spread data showed no workflow type harmed and a modest 5-9pp spread across types on every scenario, which does not support per-type tuning. The only open free parameter is the one already in the mechanism: the aging multiplier (QueuePriority("full", aging=X)). User asked to find the best single global value, testing X=1.0 in addition to the already-built 2.0/3.0/5.0, and explicitly asked that the comparison not mistake noise for improvement -- i.e. the same sign-test + Bonferroni + placebo-calibration discipline as the full2 registration, not a raw-median read like the earlier 3-seed sensitivity table.
- Scope: scenarios f3/heavy/diamond/grid (same RHO as before), seeds 1-6, aging in {1.0, 2.0, 3.0, 5.0} (new config full1 = dict(prio="full", aging=1.0); full3/full5 extended from seeds 1-3 to 1-6 to match full2's seed count -- unequal seed counts would make this comparison itself unreliable). Reference = mean of the same three null runs (base/P1/P2) per seed, already run; no new null runs needed.
- Registered analysis, applied identically to all four aging values (this is a head-to-head comparison among aging values, a separate registered question from the full2-vs-gate build decision above, with its own correction):
  PRIMARY: per-type P99 sign test over (seed, type) cells with >= 100 requests, two-sided vs 1/2, Bonferroni over 16 tests (4 aging values x 4 scenarios): p < 0.05/16 = 0.003125. Calibration (P1 vs mean(base,P2)) reused from the existing registration -- already checked, did not reject on any scenario (p 0.343-0.916).
  PHYSICAL: critical-path wait of moved tasks falls (mean of per-seed changes < 0, >= 4/6 seeds) -- same criterion as full2's PHYSICAL check.
  STARVATION (reported, not a gate unless it fails): per-type cells harmed > +5% on average (>= 3 seeds); task wait P99/P99.9/max vs base.
- Selection rule (fixed in advance, to prevent picking the best-looking value after the fact): on each scenario, among the aging values whose PRIMARY rejects in favour AND PHYSICAL holds AND no workflow type is harmed > +5% on average, the winner is the one with the most negative median per-type P99 change. If no aging value clears all three gates on a scenario, that scenario keeps full2 (already established) by default. A single value is adopted as the new global default only if it wins on all four scenarios; otherwise report per-scenario winners and keep full2 (aging=2.0) as the global default, noting the scenarios where a different value would do better.
- Runs needed: full1 all 6 seeds (24 runs), full3/full5 seeds 4-6 (24 runs) = 48 new runs; full2 and the null runs are already complete and reused as-is.

## [2026-10-29] result | aging-multiplier selection -- final verdict
- All 48 runs complete (full1/full3/full5 now all at 6 seeds, matching full2). output/data-analysis/dispatch_eval.py report_aging implements the registered comparison.
- **Every aging value (1.0/2.0/3.0/5.0) clears PRIMARY (p << 0.05/16 on all 16 scenario x value cells, range 1.8e-11 to 3.2e-12) and PHYSICAL (wait_moved falls, >=4/6 seeds) on every scenario, with no workflow type harmed > +5% anywhere.** The mechanism's benefit is robust to this parameter across two orders of magnitude of aging threshold -- a useful finding in itself: the win is not a fragile artifact of the 2x choice.
- Per-scenario winners (lowest median per-type P99 change among eligible values): f3 -> full5 (-5.4%), heavy -> full3 (-6.9%), diamond -> full5 (-6.1%, tied with full2/full3 at -6.1%), grid -> full2 (-3.7%). No value wins on all four scenarios; margins between the per-scenario winner and the other eligible values are small (<=1.3pp in every case), consistent with ordinary seed-to-seed variation rather than a real per-topology optimum.
- By the rule fixed in advance (adopt a new global value only if it wins on all four scenarios, else keep full2): **no single global winner -> full2 (aging=2.0) remains the global default.** No per-scenario adaptive setting is adopted -- the disagreement is not large enough to outweigh the added complexity, matching the user's decision earlier in this entry not to add per-workflow or per-scenario tuning without a clear diagnostic signal, which this comparison did not produce.
- **Aging-multiplier selection phase complete.** The dispatch-order mechanism (QueuePriority("full", aging=2.0)) is the final, established setting from this evaluation. No further threshold changes without a new pre-registration.

## [2026-10-29] result | 2x2 grid re-run on the extended simulator (re-layout x moves+criticality dispatch), vs B*/RL/RL_CAL
- User decision: re-run the original 2026-10-22 grid2x2.py's A/B/C/D design (fixed-layout-nothing-adapts / fixed-layout+moves /
  re-layout-only / both) under the current code, since dfps/controllers.py, dispatchers.py and model.py changed since -- and
  fold the newly-established criticality-aware dispatch (QueuePriority("full", aging=2.0)) into cells B and D on top of the
  finish-time move rule, so the grid now tests {re-layout} x {moves + criticality dispatch}. Scope: same F1/F2 x rho
  0.5/0.7/0.85 x seeds 1-3 (18 cases) as the original, for direct comparability with baseline-matrix.md. Compared against the
  existing B*/RL/RL_CAL comparison baselines only (not the full ablation table).
- **Found and fixed a real compatibility bug before running anything**: dfps/model.py's Scenario.fw field (added 2026-10-27)
  defaults to an all-ones array in __post_init__, but __post_init__ never re-runs on unpickling, so every pre-existing
  Scenario pickle (e.g. results/d1_headroom/*.pkl, from 2026-10-15) loaded with fw=None and crashed downstream (need @ sc.fw
  etc, ValueError). Fixed with a __setstate__ that re-derives fw when absent/None. Verified: the repaired pickle now gives
  fw=ones as expected; tests 78/78 unaffected. Because fw=None/ones is bit-identical to the pre-fw code path (verified
  separately in controllers.py's own docstring, 0 mismatches / 30k trials), this means the cached B*/RL/RL_CAL/HEU result
  JSONs (results/d1_headroom, results/d1_baselines) remain valid reference numbers -- they did NOT need regenerating, only
  the Scenario pickle loading needed the fix to even run under current code at all.
- New runner: output/data-analysis/grid2x2_v2.py (A/B/C/D, 72 fresh runs, no errors). Supermultiplicative interaction
  confirmed on the extended simulator (log-P99 scale, effect = ln(P99_without/P99_with), all-loads/18 cases): moves+dispatch
  alone (A->B) x2.4, moves+dispatch with re-layout (C->D) x8.3; re-layout alone (A->C) x3.7, re-layout with moves+dispatch
  (B->D) x12.8. Interaction (A-B)-(C-D) = -1.25 (CI -1.45 to -1.05, i.e. x0.3) -- reliably negative at both 50% and 70-85%
  load, confirming the combination is substantially more than additive, not an artifact of one load level.
- D (ours, re-layout + moves + criticality dispatch) vs B*: +73.2% pooled P99 (CI +67 to +79, all loads); +61.2% at 50% load,
  +79.2% at 70-85% load. D vs best-existing (min of B*/RL/RL_CAL per case): +60.4% all loads (CI +48 to +71); +26.6% at 50%
  load, +77.3% at 70-85% load. The all-loads figure (+60.4%) lands almost exactly on baseline-matrix.md's pre-existing +60.0%
  (24 Oct, move-rule-only controller, before criticality dispatch) -- a consistency check that the code refresh and the added
  mechanism did not regress the headline comparison.


## [2026-11-01] experiment | placement-objective additions (pre-registered, running)
- User request: our placement sees only request origins and direct edges; test what a more workflow-aware placement buys, one addition at a time and all together.
- Rules written BEFORE any run: knowledge/synthesis/workflow-aware-decision-rules.md ("Placement-objective additions"); novelty-register row P8. Variants V1 own state size, V2 two-hop chains, V3 join cohesion, V4 fork cohesion, V5 critical-path weighting, V6 waiting term (anchor), V7 all of V1-V5. Constants fixed in advance (gamma 0.5, floor 0.25). Noise floor from placebo runs (move period +-1 ms).
- Code (default off, V0 bit-identical): dfps/controllers.py (demand_points struct, _edge_phi, _add_structure, function_state_size, queue_aware_placement struct/size_aware), dfps/o3s.py place_kwargs (churn keys pstruct, size_aware). Runner: output/data-analysis/placement_extensions.py.
- Checks passed before launching: default-off demand and layout identical to the HEAD code on two real scenarios; on the chain archetype V3, V4, V5 give exactly the V0 layout; V0 re-run reproduces the stored results exactly (event hash and P99): grid2x2_v2 D F2 50% s3, dag_suite base chain s1 and diamond s1.
- Also this session: Heu/RL warm-start check (OnDemandSim X0 option, output/data-analysis/baselines_warmstart.py, results/d1_baselines_warmstart/): giving RL the NSGA-II start changes P99 by -1.3% on average (range -8.5% to +10.4%) and cold starts by -1.6% (range -11% to +13%), 18 dev cases; Heu not rerun (about 68 CPU-hours). Slide 2 keeps the cold-start numbers and carries a note.
- Launched 258 runs (T1 162 on the 18 dev cases incl. 36 placebos, T2 96 on the DAG suite), 10 workers; about 30 CPU-hours.

## [2026-11-02] experiment | placement-objective additions stopped at 162 of 258 runs
- Stopped by the user to focus on the request-move mechanism. No variant paid on T1 (8 of 18 cases with placebos) or structurally on T2 (grid, diamond, composite, heavy complete). Results and caveats: knowledge/synthesis/workflow-aware-decision-rules.md ("result, stopped early"); partial report results/placement_ext_report_partial.txt; novelty-register P8 updated.
- Not covered: Huawei cases, most of 85% load, chain V1/V2/V6/V7. Code stays in place, default off, V0 bit-identical (dfps/controllers.py, dfps/o3s.py).

## [2026-11-02] plan | request-move mechanism: variants of a different kind (pre-registered, awaiting user go-ahead)
- User asked to stop the placement experiment and focus on the request-move mechanism. Plan, history of every earlier move-score change (all null or worse), nearest work (web search 2 Nov, snippet level) and gates: knowledge/synthesis/workflow-aware-decision-rules.md ("Request-move mechanism"). Variants M1 tail-aware estimate, M2 transit-aware destination, M3 idle-initiated pull, M4 gain-ordered pass; Gate 0 cheap diagnostics before any variant run. No code written, no run started.
- [2026-11-02] gap diagnosis step 1 (move estimate error, existing Step A log): held-out R2 0.437 -> 0.535 with two coefficients (transfer x1.26, wait x0.55); more features add nothing; lateness grows with transfer time for idle destinations. Written in workflow-aware-decision-rules.md. New candidate M5 (re-weighted estimate). No simulation run.

## [2026-11-02] result | request-move gap diagnosis step 2 (timing rung, estimate-error replication)
- 18 development cases, 73 runs, 0 errors; logging runs identical to stored D runs 18 of 18. Timing rung: period 1 s P99 +0.8% (-0.4 to +2.0), 0.5 s +4.3% worse (+1.9 to +6.7), moves per request +70% / +131% -> M3 (idle-initiated pull) dead by the pre-registered rule. Estimate error: rmse -8.9% with two coefficients, but weights transfer 1.06-1.13 / wait 0.44-0.64 per cell; pre-registered condition (both, 4 of 6 cells) met in 1 -> M5 dropped; transit lateness criterion met in 3 of 6 -> M2 dropped. Post hoc: the wait weight is about 0.5 in all 6 cells. Full text and caveats in workflow-aware-decision-rules.md; report results/move_gap_report.txt.

## [2026-11-02] query | wait-weight test of the request-move rule
- Pre-registered then run: wait_w = 0.5 on the 18 development cases; P99 +2.0% worse (CI +1.0 to +3.0), 2/18 better; closed as null. Default wait_w = 1.0 bit-identical (checked).
- Code: Sol.aet(wait_w=), churn["wait_w"]; script output/data-analysis/wait_weight.py

## [2026-11-02] query | move-rule gap diagnosis step 3 (M1, M4 logging)
- 18 logging runs identical to stored D runs; M1 Gate 0 flip rate 10.8% (z 0.5) / 15.5% (z 1.0) -> proceeds to runs per pre-registration; M4 structure alive but current order already roughly gain-descending (corr -0.41).
- Code: churn["log_move_ctx"] (o3s.py), output/data-analysis/move_ctx_probe.py

## [2026-11-02] query | M1 tail-aware comparison run
- Pre-registered then run: z = 0.5 and 1.0 on 18 development cases: P99 +0.2% (CI -0.5 to +0.9) and +0.5% (-0.1 to +1.2); closed as null. Default tail_z = 0 bit-identical (checked).
- Code: churn["tail_z"] in dfps/o3s.py; variants T05, T10 in placement_extensions.EXTRA. Move-rule gap diagnosis: nothing reducible found on timing, estimate weights, destinations or tail-awareness; M4 untested.

## [2026-11-02] meta | AET terminology corrected
- AET is the paper's "actual execution time" (p. 8), not "estimated finish time"; labels fixed in the English talk deck and synthesis pages; differences between the paper's AET and ours listed in workflow-aware-decision-rules.md.

## [2026-11-02] meta | uniform-slot capacity assumption retired; container sizes from workflow and task profiles
- User challenge: DFPS Sec. 3.1 (p. 4) says each container needs "a fixed, specific amount of CPU and memory resources" and bounds a node by ecc_k containers; it never says all functions are one size. One slot per container was our reading, and real functions differ. Decision: capacity is a weighted knapsack with per-function weights taken from profiles.
- Wiki: new [[heterogeneous-container-sizes]] (audit table, derivation, open points); [[problem-scope]] section 2, assumptions and evidence base revised.
- Data: Alibaba plan_cpu/plan_mem re-extracted for the same 1,459,783 jobs in the same order (data/alibaba_dags_lt60s_profiles.json; experiments/extract_alibaba_profiles.py checks the match). SeBS-Flow memory per benchmark from config.json.
- Code (uniform path unchanged when all weights are 1): dfps/profiles.py (new); sim.py (hetero flag, apply_placement, invariants); sa.py; nsga2.py; controllers.py queue_aware_placement + guards on equal-size-only rules; o3s.py (_fit_counts, baseline_layout, random_placement guard); ondemand.py (weighted room-making for Heu/RL); workload.py (profile loader, meta workflow_jobs); experiments/run.py. Tests: tests/test_hetero.py (8).
- Derived weights on the 18 development scenarios: 0.27 to 2.33, CV 0.47-0.54; exact job recovery by replay, 0 ambiguous.
- Not done: no weighted scenario set, initial layouts or runs yet; all earlier results (deck slides 2, 34, decomposition) are under uniform capacity. Heu and RL stay size-blind by design.
- Regression check (2 Nov): grid2x2_v2 cell D, F1 rho 0.5 seed 1, re-run under the changed code: event hash identical to the stored run, P99 99.127 s in both. The equal-size path is unchanged.

## [2026-11-02] data | capacity model versions + CAP-W1 light test (pre-registered)
- Versions named: CAP-U (one slot per container; all results to date) and CAP-W1 (profile weights, load-preserving normalisation).
- Consistency fixes for weighted runs (sim pending additions, deferred conversions, live-capacity invariant, B* misfit redraw, lazy affinity layout); equal-size runs bit-identical (event hash).
- Light test pre-registered in heterogeneous-container-sizes.md; script output/data-analysis/capw1_light.py, results results/capW1_light/.

## [2026-11-02] data | CAP-W1 light test: ours vs B* after the sizing fix
- 18 of 18 cases: ours below B* in 18; geometric-mean P99 ratio 0.24 (CAP-U) -> 0.15 (CAP-W1); pre-registered verdict SURVIVES; gap grows (d = -0.48, CI [-0.64, -0.33]); the 85% narrowing was the proportional_counts sizing bug and is gone after the fix.
- Ours' P99 almost unchanged (x0.97); B* x1.57. Recorded in [[heterogeneous-container-sizes]]. Heu/RL CAP-W1 runs still in progress.

## [2026-11-03] diagnosis | why our Figs. 5-7 differ from the paper (B*, Heu, RL order; curve shapes) -- user request
- New page [[fig5-7-reproduction-gap]]: the paper's count curves are flat (Heu/RL cold starts ~50k at every rate, DFPS cold starts fall x0.18 over an 8x rate rise), ours scale with the rate because our runs have a fixed 300 s length. That fits a fixed request count per workload in the paper (inference; run length is not stated). The paper's utilisation text ("aggressive removal of idle instances", p. 11) fits busy / alive-container time, not busy / slot capacity. The calibrated pool averages 1.54 tasks per request, the full < 60 s pool 2.91.
- Probe pre-registered and started: output/data-analysis/fig5_pattern_probe.py (cal300 / calN / wide300 / wideN x Uniform, Pareto x scale 0.25, 1, 2 x SR, SG, B*, Heu, RL; seed 1; CAP-U). Smoke test: cal300 reproduces the stored fig567_cal runs (identical event hashes for RL, Heu, SR).
- dfps/heu.py: per-workflow quantities cached (weights, node delays, slot and storage demand). Results identical (event hash on 3 stored cells), Heu 2-3.5x faster.
- Probe result (60/60, seed 1), details on [[fig5-7-reproduction-gap]]: a fixed request count reproduces DFPS's falling cold starts (x2/x0.25 0.11-0.12 vs paper 0.18/0.34; ours with 300 s runs 0.93-0.95). Larger workflows plus fixed count reproduce the steady Pareto SR/SG curves (slope 1.9-2.1 vs 1.5) but break the Uniform low-rate fit (SR 69 vs 12 s). No variant fixes the order (Kendall tau 0.25-0.38): Heu and RL stay at or below B* everywhere. Remaining suspect: the paper's RL (and possibly Heu) release containers after use, about one cold start per task; not tested.

## [2026-11-03] data | dispatcher replacement line: mover diagnosis + traced join binding (CAP-W1)
- Why does the mover move tasks: WAIT holds (99-100% of moves wait-driven, 6/6), PULL not shown (0-1%); the mover is a queue balancer, 86-94% of moves leave the planned node, destination hosts a planned child in 5-7%.
- Traced join binding: early join move cost not reduced (0/6 cases down >= 25%; up in 4, down in 2); moves/req -1 to -6%; with the 18-case result (gm 1.002, no gain) the join-binding mechanism claim is not supported.
- Details in [[workflow-aware-decision-rules]] (sections "Why does the mover move tasks: result", "Traced join binding: result"). Scripts move_why_diag.py, joinbind_traced.py; results results/move_why/, results/joinbind_traced/.

## [2026-11-03] data | Fig. 5 probe 2: release after use for Heu and RL (CAP-U)
- keep_warm=0 for Heu and RL on the cal300 / calN / wideN scenarios, 36 of 36 runs, seed 1; pre-registered in [[fig5-7-reproduction-gap]] before the runs.
- RL utilisation (busy over alive containers) is explained: about 50%, flat, against the paper's 56-41%. Heu is flat too, but its level misses (52% against 20-35%).
- The order is not explained in substance: Heu and RL move just above DFPS at x0.25 (+4-10 s), against the paper's 5-20x; tau +0.07-0.10 at most; at high rates they stay faster than DFPS on Pareto.
- Remaining suspects: MOSEC cloud offloading and Heu's cost objective (AB-H3). Script fig5_pattern_probe.py (REL variants); results results/fig5_probe/*r_*.json.

## [2026-11-03] query | What the DFPS, Xu 2023 and MOSEC papers say about Heu and RL slowness
- DFPS pp. 10-11: per-request placement, idle or replaced instances, low reuse and more cold starts; RL spreads tasks over nodes; RL removes idle instances aggressively. Table 2: 80 edge nodes, no cloud; no Heu cost weights given.
- Xu 2023 Alg. 1 l. 9: a new instance per request. MOSEC p. 4: idle containers recycled after a no-load period; it has a cloud server, but the DFPS setup does not.
- Neither remaining suspect (cloud offload, Heu cost weights) is backed by the DFPS text. The mechanism the text names was tested in probe 2 and cannot reach 46-199 s at the lowest rate (cold start 2-10 s, 1.4-2.8 tasks per request).
- Reading: the paper's Heu and RL makespan magnitude is not reproducible from the published descriptions. Section "What the papers say about Heu and RL" in [[fig5-7-reproduction-gap]].

## [2026-11-03] data | Figs. 5-7 rerun with protocol v2 (user approved, CAP-U)
- fig567_reproduction.py --protocol v2: fixed request count (300 s / scale, warm-up 10%), Heu and RL release every container after its task, util_alive reported. Results in results/fig567_v2/, summary in output/data-analysis/results/fig567_reproduction_v2.json. The v1 results (results/fig567_cal) are untouched.
- Smoke test: seed 1, Uniform x0.25: Heu, RL and DFPS reproduce the probe's identical runs (same event hash).

## [2026-11-04] data | FIFO vs criticality-order mismatch in the move estimate; live-state replay (CAP-W1)
- Mismatch diagnostic: not material (moves with gain <= 0 in service order 1-16%, 0/6 cases >= 20%); the FIFO estimate only overstates the wait (service-order count never larger). Intervention (mover counts ahead in service order, 18 cases): gm P99 ratio 1.075 [1.055, 1.096], better in 1/18, moves/req +20-50%: worse.
- Live-state replay: exec=plan beats exec=live in 6/6 (gap -18.7 to -38.6 pts); off-plan agreement 14-37% vs 2-5% for the formula estimate; not supported as a basis for a live-state binder.
- In-transit variant pre-registered and running (live_replay2.py). Details in [[workflow-aware-decision-rules]]. Scripts prio_mismatch.py, live_replay.py; results results/prio_mismatch_diag/, prio_mismatch_arm/, live_replay/.

## [2026-11-04] data | live-state replay, in-transit variant (CAP-W1)
- Counting tasks bound or relocated but not yet queued does not raise agreement of the live choice with the executing node (-0.4 to -4.0 points, 0/6 cases >= +10); in-transit mass is 44-128% of the queued count. Not the reason the live estimate fails; see [[workflow-aware-decision-rules]]. Script live_replay2.py, results results/live_replay2/.
- Graph-Aware port audited against the paper for size handling (no size feature dropped except the residual margins inside delta, eta = 0); Graph-Aware on the 18 CAP-W1 cases (beta 4, then beta 1) and the calibration test (matcher and greedy EFT arms) started.

## [2026-11-04] data | Graph-Aware on CAP-W1 (beta 4); dispatcher calibration (matcher, greedy EFT)
- Graph-Aware beta 4, 18 CAP-W1 cases: gm P99 ratio vs matcher 0.985 [0.960, 1.015], better 15/18, NOT WORSE; moves/req lower in 18/18 (-2 to -21%); plan time 2-7 ms vs 10-90 ms. Beta 1 arm running.
- Calibration: matcher and greedy EFT equally calibrated (CAL 0/3); FST at planning has ~zero rank correlation with realised wait (Spearman -0.20 to +0.03), roots included. Graph-Aware calibration arm running.
- Pre-registered the last two spatial tests (snapshot stability, randomised move veto) with the user's stopping rule; move_cost sweep skipped (no contention model). Details in [[workflow-aware-decision-rules]].

## [2026-11-04] result | Figs. 5-7 rerun with protocol v2 (CAP-U, 5 seeds)
- 1320 of 1320 runs, 0 failed. Compared descriptively on [[fig5-7-reproduction-gap]]: Fig. 5 against the digitised values, Figs. 6-7 against the paper's text claims.
- Reproduced: DFPS cold starts fall with rate (x2/x0.25 0.12 vs 0.18; 5.6k vs 5.1k at x1 Uniform); Heu and RL cold-start curves are flat (level 0.3-0.5 of the paper's); RL utilisation over alive containers is about 50%, flat.
- Not reproduced: the order (tau 0.15 -> 0.24 U, 0.49 -> 0.52 P; Heu, RL at most 1.7x DFPS vs 4-22x); Heu's low utilisation (50% vs 20-35%); Heu vs RL distinction (identical within 0.1% in cold starts under release-after-use, paper 199 vs 46 s).
- Figs. 6-7: the claims about the static methods and DFPS utilisation hold; the claims that need Heu or RL to be slow do not (Pareto DFPS best only up to 60 nodes; Heu utilisation highest from 60 nodes).

## [2026-11-04] data | spatial line closed: snapshot stability, randomised move veto; Graph-Aware beta 1
- Graph-Aware beta 1 (18 CAP-W1 cases): gm 0.983 [0.965, 1.000], better 13/18, NOT WORSE.
- Snapshot stability: best node moves after binding (A 6/6: bind choice >= 1 s worse at +2 s for 34-65%), but exec does not follow the later snapshot (B 0/6, +2 to +3 pts) -> mixed. Event hashes matched (veto code inert).
- Move veto (10% of first moves, never moved afterwards): vetoed requests slower in 6/6 (+1.9 to +3.2 s remaining sojourn); effect rises with estimated gain (high third +3.7 to +6.9 s, low third ~0); no group where vetoing helps -> inconclusive by the pre-committed rule (low third not better in only 3/6). No mechanism built; spatial line closed per the stopping rule. Details in [[workflow-aware-decision-rules]].

## [2026-11-04] data | objective-aligned routers (CAP-W1, 18 cases per arm)
- transfer_only: P99 vs matcher 0.973 [0.957, 0.988], 15/18 better, NOT WORSE (not BETTER: CI upper > 0.97); moves/req +4% vs Graph-Aware -> cost not lower. Plan time 0.5-1.4 ms.
- mover_aet: P99 0.994 [0.978, 1.011], NOT WORSE; moves/req vs Graph-Aware 0.932 [0.868, 1.002] -> not lower by the rule; fewer moves at rho 0.5 (-5 to -31%), more at rho 0.85.
- Neither arm meets the pre-registered success rule; Graph-Aware stays the lowest-cost baseline. Router line closed again. Details in [[workflow-aware-decision-rules]].

## [2026-11-04] plan | transfer_only confirmation on fresh seeds 4-6 (CAP-W1)
- Pre-registered before any run in [[workflow-aware-decision-rules]]: matcher, greedy EFT, transfer_only on 18 fresh cases; CONFIRMED if P99 NOT WORSE vs matcher AND P99 CI upper <= 1.00 vs greedy EFT.

## [2026-11-04] result | transfer_only confirmation, fresh seeds 4-6 (CAP-W1, 18 cases x 3 arms)
- NOT CONFIRMED. P99 vs matcher 0.998 [0.974, 1.029] (C1 not met: upper > 1.02); vs greedy EFT 0.985 [0.969, 1.0000126] (C2 not met, by 1.3e-5). The seed 1-3 advantage (0.973, growing with load) did not replicate.
- Cost/plan time: moves/req -4% vs matcher, no difference vs greedy EFT; plan time 0.03x matcher. Matcher stays in FROZEN-2; routers reported as a sensitivity table. Router line closed. Details in [[workflow-aware-decision-rules]].

## [2026-11-04] decision | router = transfer_only (user decision, despite NOT CONFIRMED)
- Recorded as a design decision on planning cost and simplicity; P99 level with the matcher (not claimed better). Controller = FROZEN-2 + transfer_only dispatcher. See [[workflow-aware-decision-rules]].

## [2026-11-04] meta | mover speed-up (fast_rebal, opt-in), bit-identical on two cases
- Profile: mover = 89% of wall. Vectorised transfer terms, cached service estimate, tail position. 250 s runs identical field by field; 4.9x (heavy) and 1.8x (light) faster. Default off pending full-length checks. See [[workflow-aware-decision-rules]].

## [2026-11-04] result | fast_rebal full-length equivalence: 6 of 6 identical (900 s)
- Fast mover vs stored original runs on 6 cases (all loads, both families): every non-wall-clock field identical; wall time 1.5-5.8x lower. See [[workflow-aware-decision-rules]].

## [2026-11-04] meta | fast mover is the default; results tagged mover_impl (MV-2 / MV-1)
- `fast_rebal` default on; `mover_impl` written into every result (MV-2 vectorised, MV-1 original/untagged). Convention in CLAUDE.md; default and explicit-off paths both reproduce the original reference. See [[workflow-aware-decision-rules]].

## [2026-11-04] plan | mover pass order / early stop, counterfactual Gate 0 (user go-ahead, reopens mover line)
- V1 no early stop, V2 wait order, V3 gain order vs V0 current; logging only, 18 CAP-W1 cases; pass to online run if >= 5% moves differ AND >= 5% more estimated gain in >= 4/6 cells. See [[workflow-aware-decision-rules]].

## [2026-11-04] result | mover pass order / early stop Gate 0 (CAP-W1, 18 cases, logging only)
- Probe inert (18/18 identical), V0 = real pass 954/954. All variants dead by the rule: V1 no early stop 0/6 (gain +0.0-0.1%), V2 wait order 0/6 (5-44% moves differ, gain +0-0.9%), V3 gain order 3/6 (gain +4.7-6.8% with 5-11% fewer moves at rho >= 0.7). Storage changes <= 0.47% of decisions. See [[workflow-aware-decision-rules]].

## [2026-11-04] plan | V3 follow-up online (gain-ordered mover), last mover experiment
- Pre-registered (user's wording): 12 CAP-W1 cases at rho >= 0.7, seeds 1-3; success = P99 gm CI upper <= 1.02 AND moves/req gm CI upper <= 0.95 vs the current mover (transfer_only). Fail -> mover line closed permanently; pass -> cost improvement, move to writing. See [[workflow-aware-decision-rules]].

## [2026-11-04] result | V3 follow-up online: FAIL; mover line closed permanently
- 12 CAP-W1 cases at rho >= 0.7: P99 1.008 [0.985, 1.037] (not shown non-inferior: upper > 1.02); moves/req 0.922 [0.907, 0.938] (met, 12/12 lower). Directional cost signal, does not clear the online test. Current mover stays. See [[workflow-aware-decision-rules]].

## [2026-11-04] plan | V3 confirmation on fresh seeds 4-6 (12 runs)
- CONFIRMED if moves/req CI upper <= 0.95 AND median makespan CI upper < 1.00 (fresh 12) AND P99 CI upper <= 1.02 pooled over 24 cases. See [[workflow-aware-decision-rules]].

## [2026-11-04] result | V3 confirmation, seeds 4-6: NOT CONFIRMED; mover line closed
- Moves/req 0.922 [0.903, 0.940] (12/12), median 0.985 [0.979, 0.991] (12/12): both replicate. P99 pooled 24: 1.003 [0.984, 1.026] -> not within 2%. Current mover stays; gain order = discussion point. See [[workflow-aware-decision-rules]].

## [2026-11-04] decision | FROZEN-3 = FROZEN-2 + gain-ordered pass + transfer_only (user decision, despite NOT CONFIRMED)
- Adopted for consistent cost reduction (moves -8%, median -1.5-2%, 24/24); P99 not claimed. Results tagged `mover_pass`. See [[workflow-aware-decision-rules]].

## [2026-11-04] decision | baselines for the final table: Heu cite-and-contrast; RL / RL_CAL kept
- Heu: "no queue model and no dynamic adjustment; porting would require inventing components it does not specify" -> cited, not run ([[baseline-matrix]]).
- RL, RL_CAL kept with B* and the textbook stack. CAP-W1 coverage: B* and RL 18/18; RL_CAL and textbook stack CAP-U only; FROZEN-3 rho 0.7/0.85 only.

## [2026-11-05] synthesis | user | independent baselines CAP-W1
- Page created: [[independent-baselines-capw1]] (draft): audit of the Graph-Aware, FaaSPR and HEFT ports against the full texts, and the protocol. Nothing run.
- Finding: the repository named in the Graph-Aware paper's data-availability statement returns 404 on 5 Nov 2026.

## [2026-11-05] synthesis | user | FaaSPR path-sufficiency check
- Nine runs (3 development cases x 60/300/1500 paths), results in `results/capW1_suff/`. Rule fixed in advance: use 1,500 paths for the held-out run. See [[independent-baselines-capw1]], section 5.
- Memory cause of the laptop slowdowns found and fixed: capw1_light.prep_job held 3.4 GB of parsed Alibaba JSON per worker; the new prep parses once in the parent.

## [2026-11-05] result | user | held-out run, first pass: 224 of 240 finished; 16 FaaSPR runs crashed, port fixed, rerun
- Crash in `faaspr_placement_w`'s rescue step (heaviest function fitted on no node after one eviction); both FaaSPR arms, same 8 cases. Rescue extended to several evictions on one node; runs that finished are bit-identical. See [[independent-baselines-capw1]], section 6 (run log).

## [2026-11-05] result | user | held-out run, independent baselines under CAP-W1 (240 runs, seeds 7-10)
- P99 ratio to FROZEN-3 (geometric mean): textbook stack 1.24, RL 2.96, B* 3.15, FaaSPR 3.93 (storage-relaxed 4.77), Graph-Aware on S-P 6.07, HEFT-like on S-P 14.9, Graph-Aware on S-S 30.0, HEFT-like on S-S 49.2. FROZEN-3 lower in 24/24 cases against every independent system and the stack, 21/24 against B*, 23/24 against RL. Caveats and FaaSPR health counters: [[independent-baselines-capw1]], section 6.

## [2026-11-05] audit | user | Graph-Aware and FaaSPR ports re-checked against the papers
- Both papers re-read, each element compared with the code ([[independent-baselines-capw1]], section 7). FaaSPR follows its algorithms; three possible handicaps tested on development cases (cluster fill, rate window, `aggre` scale): none found. Graph-Aware: structure as in the paper; the lowest-index tie-break has no measurable effect on it.
- **Defect found in the HEFT-like port:** 85-88% of its decisions are exact ties resolved to the lowest node index; on one case P99 5,763 s -> 1,783 s with a neutral tie-break. The held-out HEFT rows (14.9, 49.2) are not valid as reported; re-run pending the user's decision.

## [2026-11-05] decision | user | tie-break v2 for Graph-Aware and HEFT-like; four arms re-run
- `break_ties`: exact ties go to the lowest queue estimate, then random (v1: lowest node index). New arms ga_p2, heft_p2, ga_s2, heft_s2 on the 24 held-out cases (96 runs); v1 results kept and reported beside them. v1 arms verified unchanged. See [[independent-baselines-capw1]], section 7.

## [2026-11-05] result | user | held-out run, tie-break v2 for Graph-Aware and HEFT-like (96 runs, no errors)
- P99 ratio to FROZEN-3 (geometric mean): Graph-Aware S-P 5.87 (v1 6.07), HEFT-like S-P 6.87 (v1 14.9), Graph-Aware S-S 28.6 (v1 30.0), HEFT-like S-S 27.1 (v1 49.2). Paired v2/v1: Graph-Aware 0.97 and 0.95, HEFT-like 0.46 and 0.55. FROZEN-3 lower in 24/24 against all four. v2 rows replace v1 rows in any quoted table; FaaSPR rows unchanged. See [[independent-baselines-capw1]], sections 6-7.

## [2026-11-06] plan | user | FROZEN-3 against FaaSPR under FaaSPR's own setting
- Protocol written before any run: [[faaspr-paper-setting]] (8 servers, 402 GB, 203.8 req/min, elastic 60 s scaler, three Fig. 7 shapes x rho 0.4/0.55/0.7 x seeds 7-10; arms faaspr, f3_fixed, f3_elastic; 108 runs).
- Code: `queue_aware_placement(fill_leftover=...)`, off only with `elastic` (the elastic flag did nothing for FROZEN-3 under weighted containers); default unchanged, stored FROZEN-3 case reproduced exactly. Script `output/data-analysis/faaspr_paper_setting.py`.

## [2026-11-06] result | user | FROZEN-3 against FaaSPR under FaaSPR's own setting (108 runs, no errors)
- P99 ratio FaaSPR / FROZEN-3: 2.32 (budget filled), 2.19 [1.98, 2.44] at equal memory (277 GB); mean makespan 1.80 and 1.58; FROZEN-3 lower in 36/36. FaaSPR's LP slack share 0.07 (its regime reproduced). See [[faaspr-paper-setting]], section 5.

## [2026-11-06] plan | user | on-demand re-comparison of FROZEN-3 against the baselines (held-out set)
- Protocol written before the run ([[independent-baselines-capw1]], section 8): arms frozen3_od, stack_od, ga_p2_od, heft_p2_od, faaspr_od (120 runs); RL, B* and S-S kept as they are and labelled. New code: `output/data-analysis/capw1_ondemand.py`, a flag-gated elastic qaware path in `baseline_layout` (`elastic_qaware`), nothing existing changed.

## [2026-11-06] result | user | on-demand re-comparison on the held-out set (120 runs, no errors)
- All scalable systems on-demand, P99 ratio to FROZEN-3 on-demand: stack 1.26, FaaSPR 3.57, Graph-Aware 5.92, HEFT-like 6.46; RL 2.59, B* 2.76 (not on-demand-comparable). FROZEN-3 lower in 21-24/24. FROZEN-3 on-demand costs 14% P99 against filled (30% at rho 0.5, 1% at rho 0.85) and saves 2-35% of the memory; the filled stack is roughly level with on-demand FROZEN-3 (1.09). See [[independent-baselines-capw1]], section 8.

## [2026-11-06] plan | user | faster capacity loop for on-demand FROZEN-3
- Step 1: re-layout every 30 s and 15 s on the 18 development cases (results/capW1_ondemand, arms frozen3_od_e30, frozen3_od_e15). See [[independent-baselines-capw1]], section 8.

## [2026-11-06] result | user | on-demand FROZEN-3 re-layout period, step 1 (36 runs, development cases)
- P99 over filled: 1.22 at 60 s, 1.15 at 30 s, 1.13 at 15 s; cold starts 1,567, 2,127, 2,470. Most of the loss recovered at rho 0.7 and 0.85, almost none at rho 0.5 (1.36, 1.35, 1.31). See [[independent-baselines-capw1]], section 8.

## [2026-11-06] decision | user | textbook stack removed from slide 2's charts
- User: it is a mix of our own parts and not a good baseline to show. Slide 2's bars, title, card, metric note and speaker note updated; other slides that mention the stack not yet changed. The stack stays in the wiki as an ablation-style comparison.

## [2026-11-06] result | user | on-demand FROZEN-3, utilisation target at a 30 s period (36 runs, development cases)
- P99 over filled: 1.15 (target 0.8), 1.03 (0.65), 1.00 (0.5); memory share 0.83, 0.91, 0.97. At rho 0.5: 1.35 / 1.10 / 1.00 for 64 / 78 / 95% of the memory. Lower target buys tail latency with memory. See [[independent-baselines-capw1]], section 8.

## [2026-11-06] plan | user | trigger-based add and shrink for on-demand FROZEN-3
- Design and arms written before the runs ([[independent-baselines-capw1]], section 8, step 2): `fast_scale`, parameters from `fast_step`, shrink margin 1.25 fixed in advance; 54 development runs.

## [2026-11-06] result | user | trigger-based add and shrink for on-demand FROZEN-3 (54 runs, development cases)
- P99 over filled: 1.22 (60 s) -> 1.07 with trigger; 1.15 (30 s) -> 1.05; target 0.65 at 30 s 1.03 -> 1.00. Cold starts 1,567 -> 2,124, 2,127 -> 2,761, 2,254 -> 2,442 (filled 2,091). Trigger beats the faster period at equal cold starts. See [[independent-baselines-capw1]], section 8.

## [2026-11-06] diagnosis | user | where the trigger's extra cold starts come from (12 runs)
- Cold starts = container adds. 56% of the trigger's adds were removed again by the slow re-layout within 120 s and 52% re-created what it had just removed: the two loops fight. The trigger's shrink almost never fires (137 removals). See [[independent-baselines-capw1]], section 8.

## [2026-11-06] plan | user | hold for the trigger's containers (fast_hold) in on-demand mode
- Written before the runs ([[independent-baselines-capw1]], section 8, step 3): arms frozen3_od_fs_h120 and _h60, 36 development runs; success and failure criteria stated in advance. Code: on-demand branch of the hold in `bottleneck_first_placement` (held containers are extra), hold recorded by `fast_scale`; fixed-budget path unchanged.

## [2026-11-06] result | user | hold for the trigger's containers (36 runs, development cases; 19 re-run after a fix)
- Hold 120 s: P99 1.05 (trigger-only 1.07), cold starts 1,825 (2,124; filled 2,091), memory 0.88. Undone trigger adds fell from 56% to 23%; re-creations of just-removed containers stayed at 50%: the slow loop's shrink is the remaining cause. See [[independent-baselines-capw1]], section 8.

## [2026-11-06] plan | user | gentler shrink (shrink_delay = 2) for the slow re-layout
- Written before the runs ([[independent-baselines-capw1]], section 8, step 4): arms frozen3_od_fs_h120_sd2 and frozen3_od_sd2, 36 development runs, success and failure criteria stated in advance. Code: `O3SimAdjuster._floors`, gated by churn `shrink_delay`.

## [2026-11-06] result | user | gentler shrink (shrink_delay = 2), 36 runs on development cases
- Trigger + hold 120 s + gentler shrink: P99 1.05 over filled, cold starts 1,607 (hold-only 1,825; no trigger 1,567; filled 2,091), memory 0.90 (0.77 / 0.96 / 0.98 by load). Extra cold starts over no trigger fell from 3,413 to 192. The memory saving is mostly at rho 0.5. See [[independent-baselines-capw1]], section 8.

## [2026-11-07] plan | user | 30 s re-layout at target 0.7; time and compute scalability
- Written before the runs ([[independent-baselines-capw1]], section 8, step 5): arm frozen3_od_e30_u70 on 18 development cases; decision times at 80-640+ servers; feasibility rule fixed in advance (p99 of each decision at most 10% of its period; routing 10 ms).

## [2026-11-07] result | user | on-demand FROZEN-3, 30 s re-layout at target 0.7 (18 runs, development cases)
- P99 over filled 1.06 [1.01, 1.11], cold starts 2,216, memory 0.89 (0.73 / 0.95 / 0.98 by load). Same P99 and memory as trigger + hold + shrink delay (1.05, 0.90), with 38% more cold starts. See [[independent-baselines-capw1]], section 8.

## [2026-11-07] result | user | controller cost: lazy re-layout scoring and MV-3
- Measured: re-layout about N^2.9, move pass N^1.8, limits failed by 320-640 servers. MV-3 (exact, event hashes equal 6/6) and lazy scoring (P99 0.988 [0.973, 1.001] on 18 development cases): re-layout N^1.6, largest call at 640 servers 107 s to 2.2 s, move pass p99 3.3 s to 1.16 s. Passes at 320 servers; at 640 only the move pass fails. See [[independent-baselines-capw1]], section 8.

## [2026-11-07] result | user | controller cost: exact speed-ups and second approximation on lazy scoring
- Exact speed-ups hash-equal 6/6. Demand-point thinning M = 32: P99 1.007 [0.992, 1.021] on 18 development cases (M = 16 fails, 1.029). Typical re-layout at 1,280 servers 1,206 to 73 ms; growth N^1.77 to N^0.70 (fixed functions), N^2.67 to N^1.32 (scaled). The move pass is the only decision still over its limit at 640 servers. See [[independent-baselines-capw1]], section 8.

## [2026-11-07] plan | user | the two-loop 2x2 under CAP-W1 with the current controller, FIFO queues
- Written before the runs ([[independent-baselines-capw1]], section 9): 72 runs on 18 development cases; cell D against stored FROZEN-3 gives the cost of removing the queue order.

## [2026-11-07] result | user | the two-loop 2x2 under CAP-W1, FIFO queues (72 runs, development cases)
- P99 3,899 / 1,527 / 1,431 / 118 s; moves x2.55 alone, x12.10 with re-layout; both x33, 4.74 times the product; interaction -1.56 [-1.79, -1.32]. Removing the queue order: P99 1.017 [0.995, 1.040]. Thinning M = 32 at scale: mean makespan +3.9% (320 servers), +6.6% (640). See [[independent-baselines-capw1]], section 9.

## [2026-11-07] plan | user | robustness checks of the two-loop 2x2
- Written before the runs ([[independent-baselines-capw1]], section 9): queue-aware router in the no-move cells, 3,600 s runs, held-out seeds, mechanism split; 156 runs, outcomes stated in advance.

## [2026-11-07] result | user | robustness checks of the two-loop 2x2 (156 runs)
- Held-out: 6,452 / 2,225 / 1,776 / 186 s, interaction -1.19 [-1.52, -0.88]. Queue-aware no-move cell still x8.92 above D: claim stands. 3,600 s: D stable (x0.97), A and B grow with run length, so x33 understates and is not stable. Queue order on held-out costs 5% (1.053 [1.024, 1.084]), more than the development reading. The pre-registered mechanism expectation failed as written; a post hoc reading against idle containers supports it, unconfirmed. See [[independent-baselines-capw1]], section 9.

## [2026-11-08] result | user | default controller = MV-3 mover with exact re-layout scoring (84 runs)
- MV-3 + exact scoring identical to the exact controller in 42/42 runs (event hash). Lazy scoring costs P99 x1.093 [1.034, 1.166] on the 24 held-out cases (x1.004 on development): scale-only switch, not default. New tag `place_impl` (PL-1/1f/2/3). Speed-up slides rewritten, original-vs-lazy table added. See [[independent-baselines-capw1]], section 9.

## [2026-11-08] result | user | re-layout timing separated by switch; makespan effect of lazy scoring at scale
- Exact scoring re-timed on current code (results/capW1_scale_cur/). Median re-layout, 80 / 160 / 320 / 640 servers: exact 17 / 96 / 762 / 11,230 ms, lazy 10 / 21 / 65 / 318 ms, lazy + M=32 10 / 15 / 22 / 36 ms. The exact speed-ups' own share is not separable. Lazy vs exact mean makespan at scale: x1.02 at 320 servers, x0.93 at 640 (seeds 0.80, 1.00, 1.00; seed 1 exact run is an outlier). Driver of the cost, from the code and a profile of one call: containers placed x free hosts x hosts x demand points per placement. See [[independent-baselines-capw1]].

## [2026-11-08] result | user | incremental re-layout scoring PL-4: same greedy and objective, N^3.1 to N^1.8
- New switch `incr_place` (tag PL-4), arm `frozen3i`, not default. 12-15x at 320 and 7-21x at 640 servers against exact scoring (seeds 1-3); first differing choices on recorded inputs were floating-point ties (8 of 8). The acceptance rule fixed in advance was not met as written (one tied choice moved one case's P99 by 52%); placebo reading: P99 PL-4 / exact 0.992 development, 0.984 held-out. Lazy evaluation is unsound for this objective: gains rise in 69-88% of grow steps. See [[independent-baselines-capw1]].

## [2026-11-08] meta | user | default re-layout scoring is now PL-4
- `frozen2.FROZEN3` = MV-3 + PL-4; `FROZEN3_PL1` is the former default. Earlier results not re-run. Speed-up slides updated. See [[independent-baselines-capw1]].

## [2026-11-09] result | user | FROZEN-4 adopted: shortfall-first re-layout fill (PL-5)
- `frozen2.FROZEN4` = FROZEN-3 + PL-5; `FROZEN4_P8` is the 8-pass option; `FROZEN3` unchanged. 246 re-runs, no errors (`results/frozen4_rerun_report.txt`). Held-out, filled: mean about -4%, cold starts -9%, P99 -4 to -11% by clock (median case 0.967-0.996). On-demand: mean about -3%. FaaSPR's setting: no change. Fragmentation oracle: under 2% left, re-layout tuning closed. Slides and figures not updated. See [[independent-baselines-capw1]], section 10.

## [2026-11-09] result | user | MV-4 compiled request-move pass, same decisions as MV-3
- Switch `fast_mv4`, tag MV-4, not default. Event hashes equal MV-3 in 126 of 126 full-length runs and 15 of 15 scale runs. Move-pass median 7-18x lower (1,280 servers: 601-1,007 ms to 57-81 ms); p99 inside the 0.4 s limit through 1,280 servers, 505-528 ms at 2,560. Early stopping prices about a third of the hosts at every size, so the order did not fall. See [[independent-baselines-capw1]], section 11.

## [2026-11-09] meta | user | MV-4 is the default mover of FROZEN-4, with a stop at the staying cost
- `frozen2.FROZEN4` now sets `fast_mv4`; `FROZEN4_MV3` keeps the MV-3 mover. Event hashes equal MV-3 in 126 of 126 full-length runs with the stop, so earlier FROZEN-4 results stand. Two-sided threshold search and delta re-evaluation tested, exact, not adopted: the order did not fall and the time gain is absent or small. See [[independent-baselines-capw1]], section 11.
