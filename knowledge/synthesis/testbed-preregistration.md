---
title: "Testbed experiment: pre-registration (draft, not yet frozen)"
type: synthesis
created: 2026-11-12
updated: 2026-11-12
status: draft
author: llm
tags: [testbed, pre-registration, g6, sim-to-real, sebs-flow, cold-starts]
bibliography: ../../output/bibtex/references.bib
---

# Testbed experiment: pre-registration

**Status: DRAFT.** Decisions taken by the user on 2026-11-12 are marked (decided); it becomes the pre-registration when the user freezes it (section 11 lists what is still open). Nothing below may be changed after the
freeze except through a `DEVIATIONS.md` entry. It closes DEV-T3 and DEV-T7 and is the plan for Gate G6 (`input/ideas/faas-edge-adaptation-plan.md`, Task 19), whose
wording (4-6 nodes, K3s, 2 workflows, 30 min, 3 seeds) it replaces: the testbed is four laptops with real agents, the workload is SeBS-Flow, see `testbed/DESIGN.md`.

## 1. What has been looked at (declared before the freeze)
- **Testbed calibration** (static placement, Trip Booking, 5/20/50 requests/s, 18 live runs in two series, 20 nodes): overhead, hub health, Wi-Fi impairment. It fixed the planning limit of 300 tasks/s.
- **Phase 4 pilot** (FROZEN-4 only, MapReduce, 10 nodes, loads 0.3 and 0.5, **development seeds 1 and 2**, 3 live runs). One live P99 ratio to the simulator was 1.12, inside the simulator's own spread.
- **Simulator:** the paper's held-out cases (seeds 7-10, CAP-W1, the earlier workload) have been run. SeBS-Flow scenarios have been run in the simulator only as the references of the calibration and the pilot, not for any comparison between systems.
- **No held-out seed (7-10) has been run live, and no baseline has been run live.** The confirmatory runs below start only after the freeze.

## 2. Questions and claims
- **Q1 (G6, sim-to-real).** Does the improvement of the paper's controller (FROZEN-5, adopted 12 Nov 2026) over each comparison system, measured in P99 makespan on the testbed, have the same sign as in the simulator and at least half its size?
  The size is the geometric mean over seeds of (system P99 / FROZEN-5 P99). This is the G6 rule of the frozen plan, applied per system and pooled over applications as in section 7.
- **Q2 (cold starts).** How many cold starts does each system incur on real timing, per application? Counts, not only latency: the measured cold starts are short (0.22-0.35 s), so a latency-only view
  understates them (DEV-T6). Reported per window, per request and per 100 tasks.
- **Q3 (the testbed itself).** Does the testbed stay within its calibrated limits while the controllers run (hub health, section 6)? A controller that does not keep up on the hub is a finding about its
  decision time, reported as such.
- Not claimed: absolute latencies of a real cloud (functions are emulated: sleeping tasks with measured durations; transfers are real bytes at 1/100 payload, paced to the nominal Eq. 1-2 time); anything about
  capacity models other than CAP-U (single slot per container, tagged `capacity_model` on every result).

## 3. Systems
All run through the same `Sim`/`LiveSim` code, same scenario, same initial layout `X0`, same common-random-number execution times (`CrnSampler`), same metrics.
| id | system | live class | note |
|---|---|---|---|
| F5 | FROZEN-5 (the paper's controller from 12 Nov 2026: FROZEN-4 = PL-5 re-layout fill, MV-4 mover, `transfer_only` dispatcher, plus queue-aware binding of single-parent tasks at ready time, `late_bind`) | `LiveSim` | arm `frozen5` in `testbed/frozen_live.py`; with the switch off it equals the paper's stored FROZEN-4 run (event hash); live-checked on MapReduce and ML (development seed 1) |
| B* | DFPS with E1-E4 corrected, replacement period T* = 4 s | `LiveSim` | annealer path, to build |
| RL | on-demand learned policy (calibrated checkpoint) | `LiveOnDemandSim` | to build |
| GA | Graph-Aware, independent system (decided): headline substrate S-P (stock HPA sizing every 60 s + affinity placement, no mover, FIFO), beta = 1.1, tie-break v2 | `LiveSim` | port as audited in [[independent-baselines-capw1]]; no tuning carried over from CAP-U; to build live |
| FP | FaaSPR, independent system (decided): weighted placement, per-workflow LP router with the exact threshold, sufficiency check on sampled paths, stock autoscaler | `LiveSim` | same audit and rule; to build live |
Decided 2026-11-12: SR, SG and Heu are **not** in the live set (and HEFT is not added); five systems.
The textbook stack is not a baseline (user decision 6 Nov). HEFT, the third independent baseline of the simulator study, is not in the live set.
Initial layout: every system that uses an initial layout (F5, B*, GA, FP) starts from the same `X0` (the NSGA-II plan of the case) wherever its own protocol uses one; RL starts empty, as on demand. **Build item:** the pilot used a random `X0`; the confirmatory runs use the plan's `X0`.

## 4. Applications, cluster and loads
Each SeBS-Flow application is its own experiment (DEV-T6). Cluster: **10 logical nodes** over the four laptops (about 150 container slots, 5-25 per node, CAP-U), links 50 MB/s with Eq. 1-2 pacing.
The hub drives at most **300 tasks/s** (calibrated R_max 350 with margin; FROZEN-4 used 18-25% hub CPU at 336 tasks/s). `rho_cap` is the load at which an application needs 300 tasks/s; the load actually offered is recorded as `rho_effective`. **Load rule (decided: one load per application):** the load offered is the highest the hub allows, `min(0.7, rho_cap)`, recorded as `rho_effective`; the frozen plan's levels 0.5 and 0.7 are reached where the hub allows (the low load is dropped). With 10 nodes (seed 1):
| application | tasks/request | tasks/s at rho 0.5 | `rho_cap` | offered | in the confirmatory set |
|---|---|---|---|---|---|
| Video (650.vid) | 4 | 7 | >0.95 | 0.7 | yes, medium run (10 min window) |
| ML (690.ml) | 3 | 266 | 0.56 | 0.56 | yes, short run (5 min window) |
| MapReduce (660.map-reduce) | 10 | 330 | 0.45 | 0.45 | yes, short run; below the plan's levels |
| ExCamera (680.excamera) | 16 | 6 | >0.95 | 0.7 | yes, long run (30 min window) |
| Trip Booking (6200) | 7 | 2,860 | 0.05 | 0.05 (cap) | **orchestration / cold-start regime only**: capped, in Q2 and Q3, **not** in the Q1 P99 claim (not load-comparable: rho_eff 0.05) |
| 1000Genome (6100) | 19 | 1 | >0.95 | - | **not in the confirmatory set**: 190 requests take an hour (critical path 4 min); one demonstration run, simulator for the rest |
Run shape: warm-up (controller's first decision at the end of it) 60 s (180 s for ExCamera), measured window as above, drain up to 60 s (240 s for ExCamera). Re-layouts every 60 s, move pass every 4 s (the paper's cadence).

## 5. Seeds and design
Held-out seeds **7, 8, 9, 10** (the held-out seeds of the simulator study, so each live case has a simulator twin). Development seeds 1-3 are for debugging only and are never reported as a result.
A **block** = one (application, seed) at its one load. In every block all five systems run, in an order drawn at random once (seed fixed in the repository before the freeze); blocks are interleaved across sessions, never one
system after another. Planned runs: 4 seeds x 5 systems x 5 applications (ML, MapReduce, Video, ExCamera, Trip Booking) = **100 runs**, about **27 hours** of unattended running (9 min per short run including guard, cooldown and drain:
ML, MapReduce, Trip Booking 9 h; Video 15 min per run, 5 h; ExCamera 40 min per run, 13 h). Each run is paired with its simulator twin (same scenario and common random numbers, configured as the testbed: CAP-U, payload pacing, same cadence).
Seeds: 4 (decided).

## 6. Run protocol, validity and exclusions
Per run, automatically: `fleet.py quiet on`, the guard with its 90 s cooldown (up to 2 retries 60 s apart; every refusal is stored in the result), the monitors running, one run, the run-end stamp. Every result records the
controller arm, `capacity_model`, `mover_impl`, `place_impl`, commit, `rho_effective`, impaired seconds per laptop and shared (3+ laptops), guard refusals, hub health, and the netmon log.
- **Invalid run** (repeated once with the same system, seed and cell, and still reported in the run table): a fatal agent or transfer error, fewer than 99% of the window's requests completed, or the guard bypassed.
- **Hub-health failure** (late-event fraction above 1% or hub CPU above 90%, the calibration criteria): repeated once; if the repeat fails the same way it **stays in the analysis** with a flag, because the cause is
  then that system's own decision time, which is a result (Q3).
- **Network impairment is never a reason to drop a run.** The primary analysis includes every valid run. A pre-registered sensitivity analysis excludes runs in which any laptop was impaired for more than 25% of the run's
  seconds (observed so far: 3-18% per run) and reports whether any conclusion changes. Stall episodes are reported, not removed.
- A session is stopped, not patched, if the guard refuses three times in a row; the cause is written to `DESIGN.md` before the session resumes.

## 7. Metrics and analysis
- **Primary:** P99 end-to-end makespan of the requests in the window (arrival at the controller to the last task, as in the frozen plan), per (application, load, system).
- **Secondary:** median and mean makespan; cold-start count (per window / request / 100 tasks); requests moved and re-layouts; controller decision time (adjust and plan, p95); hub health; impaired seconds per run.
- **Pairing and effect size:** per block, ratio P99(system) / P99(F5); the effect of a system is the geometric mean over the 4 seeds, with a 95% bootstrap interval over seeds (10,000 resamples). Per-seed ratios are shown.
  A bootstrap over requests is not used: it understates run-to-run noise (single-run noise about 1.5% in the simulator, more in chaotic cases; see the placebo runs with a 1 ms shift of the move clock).
- **Pooled test:** 4 seeds cannot give a per-application Wilcoxon p-value below 0.125. The inferential test therefore pools the Q1 applications (ML, MapReduce, Video, ExCamera: 4 applications x 4 seeds = 16 pairs per
  comparison): Wilcoxon signed-rank on the log ratios, Holm correction over the four comparisons (B*, RL, GA, FP against F5), rank-biserial effect size. Per-application results are descriptive with their intervals.
- **G6 reading (Q1):** for each comparison, sim-to-real holds when the testbed's pooled log-ratio has the same sign as the simulator twin's and at least half its size. The simulator twin's own run-to-run spread (move-clock placebo,
  six runs per case) is reported next to every live ratio; a live value inside that spread is "consistent", outside it "differs", with both numbers shown. Failing G6 is reported as a limitation with the discrepancy analysis, as the plan says.
- **Cold-start claim (Q2):** counts with their seed-to-seed range per application; time cost shown under the measured model and, labelled hypothetical, under the DFPS 2-10 s range (a sensitivity run).

## 8. Stopping rule
No further calibration campaign. No tuning of any system, threshold or cadence on the held-out seeds. If a held-out result prompts a change, the change is a deviation entry and the affected cells are re-run on fresh seeds
(11, 12), never on 7-10. The confirmatory set runs once to completion under the rules of section 6.

## 9. Threats to validity (stated in the paper) and sensitivity runs (after the confirmatory set)
Emulated functions (sleeping tasks) and 1/100 payloads: the testbed is a hybrid of real control plane, network, clocks and controller time with modelled function execution; shared 2.4 GHz medium (the testbed's own load
raises impaired seconds from about 3% to 12%, not shown to be self-induced); one router, one room; CAP-U only; NSGA-II initial layouts only; one cluster size, 10 nodes (below the paper's smallest tested size of 20: a deviation); millisecond tasks (Trip Booking, ML, MapReduce)
measure orchestration as much as work (DEV-T5). Sensitivity runs, in this order and only after the confirmatory set: 5 GHz network; DFPS 2-10 s cold-start range; guard window and limits varied; payload scale.

## 10. Evidence base
`testbed/DESIGN.md` (calibration, guard, phase 4 pilot), `testbed/frozen_live.py` and its tests (paper-hash equivalence), `DEVIATIONS.md` DEV-T1 to DEV-T7, the frozen plan (`input/ideas/faas-edge-adaptation-plan.md`: metric,
bootstrap, Wilcoxon-Holm, G6 rule), [[independent-baselines-capw1]] (held-out seeds 7-10), the run-noise note (placebo runs).

## 11. Decisions
**FROZEN-5 adopted (user, 12 Nov 2026).** Pre-registered in [[workflow-aware-decision-rules]] ("FROZEN-5: queue-aware binding at ready time") and confirmed in the simulator on SeBS seeds 4-6 (P99 ratio to FROZEN-4 0.664 [0.541, 0.806], 12 of 12, no application worse); live checks on MapReduce and ML complete, with one criterion not met as worded (hub CPU 3-4 points above FROZEN-4's). FROZEN-5 replaces FROZEN-4 as system F5 in the tables above; FROZEN-4 is **not** run as a reference arm (the planned runs stay at 100). FROZEN-4 stays the controller of every result before this date, and its stored results stay valid. Known: RL is still ahead of FROZEN-5 on ExCamera in the simulator (P99 ratio F5/RL 1.03-1.38 on seeds 4-6); the Q1 claim and its application list must be worded with that in view (open item, below).

Decided by the user on 2026-11-12: (1) systems = F4 (replaced by F5, see above), B*, RL, Graph-Aware and FaaSPR as independent systems; SR, SG, Heu removed; (2) 10 logical nodes; (3) one load per application, the highest the hub allows; (5) 4 seeds (7-10).
**Not yet answered, kept as proposed until the user says otherwise:** (4) applications: ML, MapReduce, Video and ExCamera in the Q1 claim, Trip Booking capped and outside it, 1000Genome simulator-only with one demonstration run;
(6) thresholds: 99% completion, late-event fraction 1% and hub CPU 90%, repeat once, the 25% impairment cut of the sensitivity analysis.
**Build items before the first confirmatory run:** live B*, RL, Graph-Aware and FaaSPR; the plan's `X0` for SeBS scenarios; the experiment driver (randomised blocks, resume, merge); the simulator twins for all cells.
