---
title: "FROZEN-3 against FaaSPR under FaaSPR's own evaluation setting: protocol"
type: synthesis
created: 2026-11-06
updated: 2026-11-06
status: review
author: llm
tags: [baselines, faaspr, protocol, fairness, capacity-model]
sources:
  - "[[jia-2025-faaspr]]"
bibliography: ../../output/bibtex/references.bib
---

# FROZEN-3 against FaaSPR under FaaSPR's own setting (protocol, written before any run)

Capacity model: **CAP-W1** (container weight = memory in GB). Ours: FROZEN-3. Request (6 Nov 2026): "an experiment of ours vs FaaSPR under its paper's setting, so it is a fair comparison".
Motivation: in the 80-server, 15-workflow held-out comparison ([[independent-baselines-capw1]]) FaaSPR ran outside the regime its paper evaluates (LP infeasible in 73-96% of solves at rho >= 0.7, per-workflow
rates about 3.75x peak-to-mean, functions shared between workflows, no server groups of 8). This experiment moves **our controller into FaaSPR's regime** instead of moving FaaSPR into ours.

## 1. What the paper's setting is (Jia et al., IEEE/ACM ToN 2025, Sec. VII-A) and what is reproduced

| paper | this experiment | status |
|---|---|---|
| 8 worker servers, one application at a time | 8 servers, one workflow per scenario, functions owned by that workflow | reproduced |
| memory is the instance resource, 0.5-2 GB per function type | container weight w_f ~ U(0.5, 2.0) GB | reproduced |
| 402 GB of memory available in total (a portion of 8 x 128 GB), distribution "normalised" | 402 GB, split equally (51, 51, 50 x 6 GB) | reproduced; the equal split is a reading of "normalised" |
| 50 MB/s per instance, Redis on each worker and a remote store; a read from another server goes through the remote store | bandwidth 50 MB/s; every transfer between two different servers costs two transfers (h = 2), none within a server; request input is negligible (0.01 MB, the "upload" function is task 0) | reproduced as a model of that data path |
| Azure trace, top 2% of functions: mean 203.8 req/min, peak 264 req/min, Poisson within each minute | one-minute rates with mean 203.8 and maximum 264, Poisson arrivals within each minute | reproduced (rate series is generated, not the Azure trace itself) |
| platform scales every 60 s to demand; the cluster is not filled | stock autoscaler every 60 s (HPA sizing, ceil(load / 0.8)), **elastic**: slots beyond the count stay empty | reproduced |
| 1 h runs, first 5 min discarded | 3,600 s, warm-up 300 s | reproduced |
| six benchmarks (Fig. 7) incl. switch and foreach | three static DAG shapes after Fig. 7: `chain5` (c, ResNet50 training), `fan6` (a, video processing, parallel branch, 3 segments), `tree6` (e, calculator); switch / foreach logic not modelled; Fig. 7 b, d, f omitted (b is a chain, d and f are millisecond-scale) | **not reproduced**: shapes only, no timings from the paper (none are given) |
| function durations, cold starts | exec time U(2, 10) s x a per-case factor, cold start U(2, 10) s (the DFPS paper's ranges); the factor sets the load | **free parameter** |
| server groups of 8 | one group of 8 = the whole cluster | reproduced (and no longer an adaptation) |
| all routing paths enumerated | 1,500 sampled paths per solve (the sufficiency check of [[independent-baselines-capw1]], section 5); where the whole path set is smaller than the sample the sampler is expected to cover it, and the number of distinct paths in the last solve is reported | adaptation, reported |

**Load.** The paper does not state how heavily its cluster is used. rho = busy-memory-seconds of the measured window over (402 GB x window), as everywhere in this project. The platform scaler needs rho / 0.8 of the memory,
so rho <= 0.8; the three levels are **0.4, 0.55 and 0.7**, with the per-case exec-time factor chosen to hit them (arrival process fixed by the paper's numbers).

## 2. Arms (same scenario, start layout, arrivals and seeds per case)

- `faaspr`: FaaSPR placement (`faaspr_placement_w`) + `FaaSPRRouterPaper`, platform scaler as above (elastic), rate window 60 s (the paper's scaling interval), alpha 0.9, HG_limit 4, FIFO queues, no request mover.
  Fixed in advance because the earlier 30 s window was a choice made in a different regime; no value is tuned on any case.
- `f3_fixed`: FROZEN-3 as defined (transfer_only router, gain-ordered mover, criticality queue order), **fixed memory budget filled to 402 GB** (its design).
- `f3_elastic`: FROZEN-3 with the same elastic scaler as FaaSPR (counts not filled), so that the two systems may use the same amount of memory; this is the resource-parity arm.
  *Implementation note.* For weighted containers `queue_aware_placement` always filled the leftover memory ("the counts are a floor"), so the existing `elastic` flag did nothing for FROZEN-3 under CAP-W1 (found in the smoke test: 400 GB provisioned
  against 266 GB needed). A parameter `fill_leftover` (default True, i.e. every earlier run unchanged; a re-run of a stored FROZEN-3 case reproduced it exactly) is switched off when `elastic` is set. No other change to FROZEN-3.
Both of ours differ from `faaspr` in one respect that is not a setting: our controller has the request mover and the criticality queue order; FaaSPR does not have them in its paper.

## 3. Cases, reading, reporting

Cases: 3 shapes x 3 loads x seeds 7-10 = 36 scenarios; seeds 1-2 were used to debug the scripts only. 108 runs. Every result is tagged CAP-W1, `setting: faaspr-paper`, `mover_pass` as in FROZEN-3.
**Reading (no pass/fail bar).** Per case, P99 makespan and mean makespan of `faaspr` over each of ours; geometric mean with a 95% bootstrap interval over case log-ratios (10,000 resamples, seed 0), wins of ours out of 36,
split by shape and by load. Also mean provisioned memory (GB, time-averaged over the measured window) of every arm, because the paper's own second metric is resource use.
**Setting-fidelity check (reported, not tuned).** Share of FaaSPR's LP solves that needed the slack fallback; the paper's algorithm assumes the LP is feasible. If it is above 0.3 in the median case, the setting is not FaaSPR's regime and
that is said next to the table.

## 4. Known limits (printed under the table)
Shapes follow Fig. 7 but the timings, data volumes, switch and foreach behaviour do not come from the paper; the arrival series is generated with the paper's mean and peak, not the Azure trace; the load level is ours; the server
resource distribution is the equal split; FROZEN-3's constants were tuned on CAP-U (earlier comparisons); FaaSPR's paths are sampled where the path count is large; the remote-store data path is modelled as a doubled hop count.

## 5. Result (6 Nov 2026; 108 runs, 36 scenarios, no errors; report in `results/faaspr_setting_report.txt`)

Ratio FaaSPR / FROZEN-3 (geometric mean, 95% bootstrap interval); FROZEN-3 lower in 36 of 36 scenarios in every row.

| FaaSPR over | P99 | mean makespan |
|---|---|---|
| `f3_fixed` (budget filled, 400 GB) | 2.32 [2.10, 2.58] | 1.80 [1.72, 1.90] |
| `f3_elastic` (same memory as FaaSPR, 277 GB) | **2.19 [1.98, 2.44]** | 1.58 [1.50, 1.67] |

By shape (P99 vs `f3_elastic`): chain5 2.13, fan6 2.46, tree6 2.02. By load: 2.00 (rho 0.4), 2.20 (0.55), 2.40 (0.7); the gap widens with load. Means over the 36 scenarios: P99 304 s (FaaSPR), 126 s (`f3_fixed`),
132 s (`f3_elastic`); mean makespan 96, 53, 60 s; provisioned memory 277.0, 399.9, 277.0 GB; cold starts 1,727, 27, 1,007.
**Setting-fidelity check (as pre-registered):** the median share of FaaSPR's LP solves needing the slack fallback is 0.07 (mean 0.08), against 0.73-0.96 in the 80-server comparison, and there were no repaired, unplannable or parked requests.
The setting is FaaSPR's regime. Distinct paths in the last solve: 1,298 on average (the sampled set is smaller than 1,500 where the full set is smaller).
**Reading.** With resource parity and in a regime where FaaSPR's LP works as designed, FROZEN-3 has about half FaaSPR's P99 and about 0.63 of its mean. The earlier statement that the gap was an artefact of the bursty regime is therefore
not supported: the gap is about 2x here and 3.9x there. What this does not separate: FaaSPR has no request mover and no criticality queue order, which are our controller's mechanisms, so the gap is not evidence about FaaSPR's
placement and routing alone; the shapes are Fig. 7's but the timings, data volumes and load level are ours; FROZEN-3's constants were tuned on CAP-U; the arrival series is generated, not the Azure trace.

## Evidence base
The FaaSPR paper (Secs. IV-VII, Fig. 7, read from the PDF); the audit and port of [[independent-baselines-capw1]]; the FROZEN-3 definition (`output/data-analysis/frozen2.py`).

## What stays open
Whether the ranking depends on the unstated load; whether millisecond-scale workflows (Fig. 7 d-f) change it; the effect of the switch and foreach structures; the Azure trace itself.

## Sources
[[jia-2025-faaspr]]; [[independent-baselines-capw1]]; [[heterogeneous-container-sizes]].
