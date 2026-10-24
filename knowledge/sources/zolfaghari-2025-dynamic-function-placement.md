---
title: "Zolfaghari et al. 2025 — Dynamic Function Placement and Request Scheduling of Serverless Workflows in Edge Environment (DFPS)"
type: source
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
bibkey: zolfaghari-2025-dynamic-function-placement
depth: standard
based_on: preprint
tags: [serverless, edge, workflow, placement, scheduling, dfps, reproduction, baseline]
relations:
  - target: dfps
    type: mentions
    confidence: extracted
    because: "The system this paper proposes (Sec. 3-4, pp. 3-9)."
  - target: dfps-printed-errata
    type: contradicts
    confidence: extracted
    because: "Eq. 3 (p. 6), Eq. 6 (p. 7), Alg. 1 (p. 8) and Alg. 2 (p. 9) contradict the paper's own prose or mathematics; checked on rendered pages."
  - target: periodic-replacement-and-rescheduling
    type: mentions
    confidence: extracted
    because: "Sec. 4.3 (pp. 7-9) defines it; interval 4 s (pp. 9-10)."
  - target: edgecloudsim
    type: cites
    confidence: extracted
    because: "Evaluated in EdgeCloudSim extended for serverless (p. 9)."
  - target: alibaba-cluster-trace
    type: cites
    confidence: extracted
    because: "Workflows taken from the Alibaba Cluster Trace, applications under one minute (p. 9)."
  - target: shahrad-2020-serverless-wild
    type: cites
    confidence: extracted
    because: "Table 2 ranges for function run-time and cold-start delay are attributed to it (p. 10, ref. [45])."
  - target: cold-start
    type: mentions
    confidence: extracted
    because: "Cold-start reduction is the stated motivation for an initial placement plus periodic adjustment (pp. 2, 7)."
---

# Dynamic Function Placement and Request Scheduling of Serverless Workflows in Edge Environment

## Bibliographic Details
Zolfaghari, Behrooz; Abrishami, Saeid; Rasoolzadegan, Abbas; Javadi, Bahman. 2025. *Dynamic Function Placement and Request Scheduling of Serverless Workflows in Edge Environment*. IEEE Transactions on Services Computing 18(5): 2781-2793. DOI 10.1109/TSC.2025.3592226.

> Page note: the library PDF is the accepted, "not fully edited" author version (13 pages, IEEE Xplore copy with a third-party watermark). Printed page numbers equal PDF pages and are used throughout; they differ from the journal pagination 2781-2793. Figure values (Figs. 5-7) are plots only; no numbers appear in the text.

## Section map

| Covered | Section | pp. |
|---|---|---|
| ✓ F1 | Abstract; 1 Introduction (contribution list) | 1-2 |
| ✓ F1 | 2 Related Work: 2.1 Edge FaaS, 2.2 placement and scheduling at the edge | 2-3 |
| ✓ F1 | 3.1 System architecture model, Table 1 notation | 3-4 |
| ✓ F1 | 3.2 Problem formulation, Eq. 1-2 | 4-5 |
| ✓ F1 | 4.1 Initial placement (NSGA-II), Eq. 3-4 | 5-6 |
| ✓ F1 | 4.2 Request scheduling (graph pattern matching, M/M/c), Eq. 5-6 | 6-7 |
| ✓ F1 | 4.3 Dynamic replacement and rescheduling (SA), Alg. 1-2, Eq. 7-8 | 7-9 |
| ✓ F1 | 4.4 Computation complexity | 9 |
| ✓ F1 | 5.1 Simulation setup, baselines, Table 2 | 9-10 |
| ✓ F1 | 5.2.1 Varying arrival rates (Fig. 5) | 10 |
| ✓ F1 | 5.2.2 Varying network size (Fig. 6) | 11 |
| ✓ F1 | 5.2.3 Application variety (Fig. 7) | 11 |
| ✓ F1 | 6 Conclusion and future work | 11-12 |
| — | References [1]-[45] | 12-13 |

## Kernthesen

### 1. ⭐ Per-request placement and scheduling is the weakness the paper targets (pp. 2-3)
The authors argue that existing edge serverless-workflow methods decide placement and scheduling individually for each request, which "leads to a higher number of cold starts and lowers function re-usability" under high request volume (p. 2). They also state that none of these methods has a runtime auto-scaling mechanism (p. 3). The remedy is a good initial placement plus periodic runtime adjustment.

### 2. The problem is split into three sub-problems (pp. 2-3)
Initial placement (once, before requests), request scheduling (per request), and dynamic replacement and rescheduling (periodic). Each gets its own algorithm: NSGA-II, graph pattern matching, simulated annealing.

### 3. System model: central controller, container slots, states stored at nodes (pp. 3-5)
A central controller (possibly in the cloud, p. 4) manages Ne edge nodes, each with a container capacity ecc_k, a storage capacity esc_k, a list of warm instances and a list of stored states. Workflows are DAGs; each task output is a "state" sent to the node chosen for the next task. The architecture "follows a static planning and dynamic scheduling approach" (p. 4). A standby controller is the proposed answer to the single point of failure (p. 4). Propagation delay is set to zero; transfer time is hops times size over bandwidth (Eq. 1-2, p. 5).

### 4. ⭐ The objective is mean workflow makespan under capacity limits only (p. 5)
Makespan is the time from request receipt to the last task's completion. Constraints are function (container) and storage capacity. No deadline, SLO, drop or admission notion appears.

### 5. Initial placement balances proximity and proportionality (pp. 5-6)
NSGA-II with two criteria: the BFS "proximity level" (hops until every function type is visible) summed over nodes, and Eq. 3, the gap between available and expected instances per function, where expected instances are proportional to mean execution time (Eq. 4). Population 100; the final plan is the front member with the lowest sum of min-normalised criteria. It runs "only once offline" (p. 9). Printed Eq. 3 is identically zero (see [[dfps-printed-errata]]).

### 6. Request scheduling is pattern-graph matching on warm instances (pp. 6-7)
The workflow becomes a labelled pattern graph and the warm instances of the needed functions become a weighted reference graph, rebuilt per request. G-edge weights are queueing service time (M/M/c, Eq. 5-6) plus state transfer time. The match with the least total weight is chosen (p. 7). The whole DAG is bound at arrival.

### 7. ⭐ Dynamic adjustment is a periodic simulated-annealing search (pp. 7-9)
Every interval, one instance of the least-requested function on a random node is replaced by a random function and requests are relocated when their relocation gain is positive (Alg. 1, Eq. 8). The evaluation function sums relocation gains. Alg. 2 anneals from T_max to T_min and returns the last solution. The interval is "set to the average critical path length" (p. 7) in the text, but 4 s in the experiments.

### 8. Complexity is dominated by SA; NSGA-II is offline (p. 9)
O(Ni x No x Np^2) for NSGA-II (offline), roughly linear in g-edges per request for matching, O(Ni x Ne x Nr) for SA. No wall-clock decision latency is reported.

### 9. ⭐ Evaluation protocol: simulator, workloads, baselines (pp. 9-10)
EdgeCloudSim extended for serverless, Alibaba trace workflows under 1 minute, GT-ITM topologies. Two workload shapes, Uniform and Pareto, from per-application Poisson arrivals. Baselines: SR (static, random initial placement), SG (static, NSGA-II), Heu (Xu et al. [18], per-request joint placement and scheduling), RL (Yang et al. [28], MOSEC). Metrics: average makespan, utilisation, cold starts. Ten workloads per point, repeated-measures ANOVA p < 0.05 (p. 10).

### 10. ⭐ Makespan rises with arrival rate for every method; ranking depends on workload shape (pp. 10-11)
Congestion raises makespan for all methods under both Uniform and Pareto (p. 10). Under Uniform, DFPS, SR and SG are well below Heu and RL. Under Pareto the static plans fail because the uniform initial placement does not fit the skew, SG is slightly better than SR, and DFPS is best (p. 10). SR and SG cold starts are zero by construction (p. 10).

### 11. Larger networks lower makespan; SG can match DFPS under Uniform load (p. 11)
For 20-160 nodes, makespan falls for all methods. Under Uniform, SG is comparable to or slightly better than DFPS; under Pareto DFPS is best and SG always beats SR. DFPS utilisation falls with network size.

### 12. More applications raise makespan (p. 11)
For 5-40 applications, fewer instances per function can be placed, so makespan rises for all methods.

### 13. The RL baseline lacks workflow awareness (pp. 10-11)
The authors attribute RL's weaker results to scheduling tasks independently, which spreads a workflow across nodes, adding cold starts and transfer delay. Its high utilisation comes from aggressively removing idle instances (p. 11).

### 14. Stated future work is decentralised control (p. 12)
Extension to settings where resources belong to different owners and central management is infeasible.

## Figures and tables
Fig. 1 sample image-processing workflow (p. 1); Fig. 2 DFPS architecture (p. 5); Fig. 3 chromosome and crossover (p. 6); Fig. 4 pattern and reference graphs (p. 7); Fig. 5 arrival-rate results (p. 10); Fig. 6 network size (p. 11); Fig. 7 application variety (p. 12). Table 1 notation (p. 3); Table 2 simulation parameters (p. 10).

## What this source does not address
No code, no values for T_max, T_min, cooling schedule, NSGA-II generations, GT-ITM parameters, run length or warm-up. No non-stationary arrival process, no request origin or mobility, no admission or rejection, no tail-latency or SLO metric, no decision-latency measurement, no cold-start cost inside the relocation gain. Forecast-based adaptation is [[sun-2026-hybrid]] and [[lei-2026-adaptive]] territory; heavy-tailed duration distributions are in [[heavy-tailed-function-durations]].

## Focus: Reproduction parameters (Table 2), errata E1-E6, evaluation protocol, and evidence for D1-D3 — 2026-10-13

> [!warning] Provenance: based on the accepted **author manuscript** (not fully edited), not the Version of Record.
> Page numbers are those of the 13-page manuscript. Equations and algorithms may have been corrected in the final version; re-check E1-E6 against the VoR if it becomes available.

**Carries Kernthesen 4, 5, 6, 7, 9, 10, 11.**

### What this focus needs beyond the Kernthesen

**Table 2 and Sec. 5.1 parameters (all pp. 9-10, as printed):**

| Parameter | Value |
|---|---|
| Function run-time | 2-10 s (range attributed to Shahrad et al. [45]) |
| Cold-start delay | 2-10 s (same attribution) |
| Intermediate state size | 10-50 MB |
| Number of workflows | 15 (5-40 in Sec. 5.2.3) |
| Edge nodes | 80 (20-160 in Sec. 5.2.2) |
| Average bandwidth | 50 MB/s (propagation delay 0, p. 5) |
| Edge node function capacity ecc | 5-25 |
| Edge node storage capacity esc | 10-30 GB |
| Incoming request rate | 0.5-100 per second |
| Replacement interval | 4 s (sweep 1-9 s, lowest delay) |
| NSGA-II population | 100, 2 objectives (p. 9) |
| Uniform arrivals | per-app Poisson mean 200-700 ms |
| Pareto arrivals | about 20% of apps 50-100 ms, the rest 2-4 s |
| Arrival scale factors | 0.25, 0.5, ..., 2 |
| Repetitions / test | 10 workloads, repeated-measures ANOVA p < 0.05 |
| Workflow source | Alibaba trace, apps under 1 min; topologies GT-ITM |

Not stated: T_max, T_min, cooling schedule, generation count, distribution inside ranges, number of function types, task-to-function mapping, run length, warm-up, utilisation definition, request origin.

**Cross-check against existing notes.** `DFPS_PAPER_DATA.md` (section 3) and `PLAN.md` section 4 reproduce Table 2 and Sec. 5.1 as above; no value differs. `DEVIATIONS.md` OPEN-2 is consistent with the "not stated" list. `input/description/dfps-gap-evaluation.md` M7 and V5 are consistent (ranges and unreported SA settings). The errata comparison (E1-E6, including the numbering clash with PLAN/DEVIATIONS) is on [[dfps-printed-errata]]. One point not in the notes: Eq. 6 returns the number in the system, not the number in the queue (p. 7).

**Claims as stated (the protocol's falsifiable ones):**
1. Average makespan rises with arrival scale for all methods, under both Uniform and Pareto (p. 10).
2. Under Pareto, makespan ordering is DFPS lowest, SG next, SR highest (p. 10; SG better than SR at all network sizes, p. 11). Under Uniform the picture differs: SG is comparable to or slightly better than DFPS (p. 11), and DFPS, SR, SG all beat Heu and RL (p. 10).
3. SR and SG have zero cold starts by construction (p. 10). A reproduction therefore cannot rank them against DFPS on cold starts.
4. Headline: up to 86% lower makespan; which scenario and baseline is not stated in the text (abstract).

**Evidence for the weaknesses (reading of this source, not the project's verdicts):**
- D1, clock-driven, cost-blind, forecast-free reconfiguration. The interval is fixed by the clock: "set to the average critical path length" in the text (p. 7), 4 s in the experiments, chosen on the evaluated workloads (pp. 9-10). SA runs every interval with no change test (Alg. 2, p. 9). The evaluation function is the sum of relocation gains (p. 8), and AET is transfer plus service time (p. 8), with no cold-start or migration cost term. Inputs are the past interval's request counts and a rate "updated every few seconds" (pp. 7-8), not a forecast. Arrivals are stationary Poisson (p. 9). Periodicity is justified as cold-start limitation (p. 7) without a comparison against an event-triggered alternative. No decision-overhead numbers are given.
- D2, admit-everything dispatch. Requests are "forwarded to the central controller for scheduling" (p. 4). A node without storage space only loses its g-node (p. 7); there is no rule for an empty match, and no rejection, deadline or SLO. The objective is mean makespan (p. 5), and the metrics contain no drop or goodput measure (p. 10). Makespan grows with load "due to congestion" (p. 10), the symptom admission control would address.
- D3, placement decoupled from dispatch. Three components with separate objectives (p. 2): placement by proximity and proportionality criteria that ignore requests (pp. 5-6), dispatch bound to currently warm instances (p. 7). Partial coupling exists: SA moves relocate already scheduled requests (pp. 7-8). The coupling is one way: placement reacts to current queues, but dispatch does not anticipate planned placement changes and NSGA-II never sees dispatch. The authors contrast DFPS with Heu, which places and schedules jointly per request (p. 9).

### Direct quotes (for the draft)
> "the average application makespan increases with rising request arrival rates across all methods" (p. 10)

> "The length of these intervals is set to the average critical path length of the workflows." (p. 7)

> "the cold start count for these methods remains zero" (p. 10)

> "scheduling and placement decisions are made once for each request, without any modifications during runtime" (p. 3)

### Examples & illustrations (for later drafting)
- Pareto workload: a few applications (about 20%) receive 50-100 ms Poisson means, the rest 2-4 s; the initial uniform placement then mismatches demand, which is why SR and SG degrade while DFPS adjusts (pp. 9-10).
- RL baseline: tasks of one workflow are scattered across nodes, which raises cold starts and transfer delay (p. 11).

### Boundary of this focus
Numbers behind Figs. 5-7 were not read; only the textual claims. The related-work survey (pp. 2-3) was read for the positioning claim only. The cited baselines Heu [18] and RL [28] are not read here.

## Mentioned entities
- Systems and tools: [[dfps]], [[edgecloudsim]]
- Datasets: [[alibaba-cluster-trace]]
- Concepts: [[dfps-printed-errata]], [[periodic-replacement-and-rescheduling]], [[cold-start]]

## Connections
- Contradicts itself in the printed equations and algorithms: [[dfps-printed-errata]].
- Cites for run-time and cold-start ranges: [[shahrad-2020-serverless-wild]].
- Later work that cites DFPS and addresses adaptation: [[sun-2026-hybrid]], [[lei-2026-adaptive]], [[jayanthi-2026-quantum]] (named in `input/description/dfps-gap-evaluation.md` section 6; not stated in this source).
