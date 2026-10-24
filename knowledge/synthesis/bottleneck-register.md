---
title: "Bottleneck register: recorded and possible bottlenecks (DFPS re-implementation and headroom study)"
type: synthesis
created: 2026-10-15
updated: 2026-10-16
tags: [bottleneck, overload, simulator, dfps, research-material]
sources:
  - "[[zolfaghari-2025-dynamic-function-placement]]"
  - "[[shahrad-2020-serverless-wild]]"
  - "[[joosen-2025-cold-starts]]"
status: draft
author: llm
bibliography: ../../output/bibtex/references.bib
---

# Bottleneck register

Living list of bottlenecks met while re-implementing DFPS and screening the three directions (plan `faas-edge-adaptation`).
Two kinds are kept apart:

- **Recorded**: measured in this project; the evidence file is named. These can be cited as our own findings (with their caveats).
- **Possible**: plausible from the method or the data, **not yet measured**. Each says what measurement would confirm or refute it.

A third column says why the entry matters for the research: **system** (a property of DFPS or edge FaaS, potential paper material), **study** (threatens the validity of our measurements), or **tool** (a property of our simulator only, to be reported as a limitation, not as a finding).

## Recorded bottlenecks

| ID | Bottleneck | Evidence | Kind | Research relevance |
|---|---|---|---|---|
| R1 | **Per-function overload hides behind a moderate aggregate load.** At aggregate offered utilisation rho = 0.85 a random placement left the 80-node system saturated (123 of 5,230 requests unfinished, mean makespan 276 s). At rho = 0.7 the NSGA-II placement puts the busiest functions at 1.6x (F3) and 2.7x (F2) their instance capacity while the median Huawei function sits at 0.017 | `output/data-analysis/results/g2_validation.json` (runtime_budget.note_load); T* smoke test, log 2026-10-15 | system + study | Aggregate rho is a poor load measure for function-level placement; headroom can partly measure placement imbalance (A-16 mapping). Supports D1/D3 motivation (re-balancing matters) and is a threat to validity if not reported |
| R2 | **Storage exhaustion under deep overload.** In Uniform x2.0 the free storage of the most loaded node reached 0 MB at about 100 s; from about 210-250 s every new request failed placement and joined a waiting list | diagnostics `g2_diag_x2*.txt` (2026-10-14) | system | In-flight requests reserve state storage at planning (A-23), so storage, not CPU slots, becomes the binding resource. DFPS never discusses storage-driven overload; relevant to D2 (admission) |
| R3 | **Retry storm.** With per-completion retries of the waiting list (A-24), 94,000 retries occurred in 30 simulated seconds once storage ran out; one x2.0 job did not finish in 13 h | `g2_diag_x2.txt`, log 2026-10-14 | tool (+ system) | Any re-plan-on-every-event controller has this failure mode under overload: a design lesson for D2, and a reason to bound control work per unit time |
| R4 | **Request scheduling (graph matching) dominates compute.** About 95% of wall time; about 10-19 ms per arrival (36 ms with the profiler); one simulated hour at 80 nodes, rho = 0.85 costs about 20 min wall | `results/` profiles, `g2_validation.json` | tool + system | Decision overhead of DFPS's matching is significant at 60 req/s; relevant to the plan's 50 ms p95 decision-time limit and to scalability claims |
| R5 | **Annealing cost grows with the backlog.** B* re-plan time rose from 0.1 s (1,440 queued runs) to 1.7-2.6 s (11,900 queued runs) at x2.0, i.e. up to 65% of the 4 s interval | `g2_diag_x2_bstar_capped.txt` | system | A clock-driven re-planner gets slower exactly when it is most needed; supports D1 (decide when to re-plan) |
| R6 | **Reroute dead end.** A request whose node lost its instance in a re-plan could find no node holding the function with free storage; the original code crashed (3 x2.0 jobs). Now the request waits (A-25b) | `results/g2_reproduction/*.err` (superseded), log 2026-10-14 | system | DFPS relocations can strand in-flight work under storage pressure; a correctness gap of periodic re-placement (D1/D3) |
| R7 | **Static baselines degrade much faster with load than DFPS.** SR/SG mean makespan grows from about 52-64 s (Uniform x0.25) to about 300-340 s (x1.0); B* from 30 s to 81 s. Under Pareto, SR/SG are 250-280 s already at x0.25 | `g2_reproduction.json` (80 jobs, 2026-10-15) | system | Popularity skew (Pareto) is where static placement breaks; mismatch with the paper (paper: DFPS approx. SG under Uniform) to be explained |
| R8 | **Printed errata cost grows with load.** DFPS as printed minus B* (80 jobs): +0.7 s (Uniform x0.25), +15.6 s (x1.0), +47.7 s (x2.0); Pareto +1.9 s (x0.25) to +70.1 s (x2.0); P99 up to 25% higher | same | system | Motivation material: the E1-E3 corrections matter most under load |
| R9 | **Minute-scale demand is mostly smooth in the top functions.** Change points per hour: Azure 0.18, Huawei 0.008 (median top-200); Azure aggregate CV 0.10 | `g1_trace_screen.json` | system + study | Weakens D1's premise at minute scale; non-stationarity may live at sub-minute scale (not measured: Huawei per-second file not obtained) |
| R10 | **Overload is bursty in Huawei, absent in Azure.** 13.3% of 1-min windows overloaded at rho = 0.7 (Huawei aggregate CV 0.62) vs 0.02% (Azure) | `g1_trace_screen.json` | system | D2 headroom can only come from bursty families (F2, F3) |
| R12 | **Printed placement objective is degenerate.** With Eq. 3 as printed (E1), the NSGA-II placement (SG_signed) is no better than random: Pareto x0.5 600.1 vs SR 599.3 s, x1.0 1240 vs 1193 s, x2.0 2166 vs 2142 s; with the corrected objective SG beats SR at every scale | `g2_reproduction.json` (80 jobs, 2026-10-15) | system | Direct evidence that erratum E1 disables DFPS's initial-placement optimisation; motivation material |
| R13 | **Static placements cannot drain deep overload.** Pareto x2.0: SR left up to 2,956, SG (printed) 5,921, SG (corrected) 918 requests unfinished after the drain limit; both DFPS variants finished all | same | system | Dynamic re-placement is what keeps the system stable under skewed overload; also a censoring caveat for static means |
| R14 | **Re-plan period is a U-shaped trade-off (P1, P2 confirmed).** B* P99 vs period (rho 0.7, 3 instances): T = 1 s causes ~52,000-58,000 cold starts per 15 min and P99 757/960/457 s (F1/F2/F3); best at 2-8 s (602/585/382); at 64 s imbalance accumulates (1404/1817/1052). The best period differs by family (4/8/2 s) | `g2_tstar.json` (2026-10-15) | system | Direct support for D1's premise: a fixed period is either too eager (cold-start cost) or too lazy (imbalance); the optimum is workload-dependent |
| R11 | **Heavy-tailed durations.** Azure 2021 duration SCV 27.8 overall; per-function median 1.93; 62% of functions with SCV > 1 | `g1_trace_screen.json` | system | The paper's exponential service assumption (A-13) understates tails; sensitivity material |

## Possible bottlenecks (not yet measured)

| ID | Hypothesis | How to test | Kind |
|---|---|---|---|
| P2 | Within a run, the best period changes over time (bursts vs calm); a fixed T* cannot follow it | O1 / O1+B* vs B* in Task 11 (running) | system (D1) |
| P3 | Link bandwidth (50 MB/s, store-and-forward per hop, no contention) is not a bottleneck in the paper's model but would be with fair-share contention and 10-50 MB states | Task 17 sensitivity: contention on/off | study |
| P4 | Storage, not slots, is the binding resource at high load for every method (R2 generalised) | log min free storage and slot occupancy per run in Task 11-13 | system |
| P5 | The function-to-type mapping (A-16, uniform global pool) creates artificial hot spots that drive R1; with SeBS-Flow workflows (fixed function identities) the imbalance may differ | compare bottleneck_utilisation for Alibaba-only vs mixed workflows | study |
| P6 | Matching's K-best/spanning-tree search makes decision time exceed 50 ms p95 at high arrival rates (R4) | plan_ms_p95 metric, recorded in every run since Task 7 | system |
| P7 | Overloaded cells (Uniform x2.0, Pareto x1.0/x2.0) measure backlog, not scheduling quality; method rankings there may be driven by who stalls least | compare rankings with and without censoring at fixed drain | study |
| P8 | Sub-minute bursts (not visible in per-minute traces) carry the non-stationarity D1 needs | requires the Huawei Private per-second file (Drive quota blocked the download) | study (D1) |

- **P9 (2026-10-16, D2 capacity bound): capacity on the wrong functions during bursts.** Offered work is 0.8-1.3x total capacity over the window, yet the best oracle (O2H) serves only 15-31% of the pooled bound on time: the loss is bottleneck functions x burst timing x deadlines, not aggregate overload. Follow-up ablations parked in `input/ideas/post-g3-oracle-ablations.md` (after G3).

## Tool-only issues (fixed, not findings)

- Floating-point livelock in the retry throttle (fixed 2026-10-14; regression test). Not a system property.
- Memory blow-up building the full Azure matrix (66k x 20k); now two-pass.

## How to use this page

When a later task measures a "possible" entry, move it to "Recorded" with the evidence file and date. Before drafting, every "system" entry cited in the paper needs its evidence re-checked against the final runs.
