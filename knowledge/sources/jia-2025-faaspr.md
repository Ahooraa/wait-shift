---
title: "Jia et al. 2025 — FaaSPR: Latency-Oriented Placement and Routing Optimization for Serverless Workflow Processing"
type: source
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
bibkey: jia-2025-faaspr
depth: standard
tags: [serverless, workflow, placement, routing, cold-start, g0, novelty-gate]
relations:
  - target: faaspr
    type: mentions
    confidence: extracted
    because: "Proposes FaaSPR (abstract, p. 2063)."
  - target: faasflow
    type: contradicts
    confidence: extracted
    because: "Argues FaaSFlow's centralised grouping exceeds server limits and overlooks instance migration, 'leading to frequent cold start' (p. 2063)."
  - target: horizontal-vertical-grouping
    type: builds-on
    confidence: extracted
    because: "Placement technique (Sect. IV-A, pp. 2066-2068)."
  - target: migration-minimizing-placement
    type: builds-on
    confidence: extracted
    because: "Alg. 2 priority = saved cold start + saved transmission (p. 2068)."
  - target: multi-stage-lp-routing
    type: builds-on
    confidence: extracted
    because: "Routing LP with latency cap and binary search (Sect. V, pp. 2068-2070)."
  - target: azure-functions-trace-2019
    type: cites
    confidence: extracted
    because: "Workload generated from the Azure Function Dataset, top 2% functions (p. 2072)."
  - target: shahrad-2020-serverless-wild
    type: cites
    confidence: extracted
    because: "Ref. [18]; heuristic instance reservation by invocation frequency cited as early cold-start work (p. 2076)."
  - target: cold-start
    type: mentions
    confidence: extracted
    because: "Cold start is one of three overhead sources (p. 2063)."
  - target: dfps
    type: mentions
    confidence: inferred
    because: "Not cited by the paper (no occurrence of DFPS or Zolfaghari in the text); related problem family, but cloud datacentre rather than edge."
  - target: periodic-replacement-and-rescheduling
    type: contradicts
    confidence: inferred
    because: "Both re-place on a clock (here per 1-min scaling request, p. 2068); FaaSPR adds a cold-start reuse bias that periodic replacement lacks."
---

# FaaSPR: Latency-Oriented Placement and Routing Optimization for Serverless Workflow Processing

## Bibliographic Details
Jia, Yunshan; Jin, Chao; Li, Qing; Liu, Xuanzhe; Jin, Xin. 2025. *FaaSPR: Latency-Oriented Placement and Routing Optimization for Serverless Workflow Processing*. IEEE Transactions on Networking 33(4): 2063-2078. https://doi.org/10.1109/TON.2025.3552407. Page numbers are printed pages (PDF page 1 = p. 2063). Text extracted from the library PDF (UTF-8, non-layout); the reference list was not read beyond [21].

## Section map

| Covered | Section | pp. |
|---|---|---|
| ✓ F1 | I. Introduction | 2063-2064 |
| ✓ F1 | II. Background and motivation (workflow architecture, scaling, overhead breakdown) | 2064-2065 |
| ✓ F1 | III. FaaSPR overview | 2065-2066 |
| ✓ F1 | IV. Placement (grouping, Alg. 1; migration-minimizing priority, Alg. 2) | 2066-2068 |
| ✓ F1 | V. Multi-stage LP routing (model, constraints, overhead) | 2068-2070 |
| ✓ F1 | VI. Implementation | 2070-2071 |
| ✓ F1 | VII-A. Evaluation setup (benchmarks, workload, cluster, baseline) | 2071-2072 |
| ✓ F1 | VII-B. Benefits (workflows, bandwidth, resource distribution, multi-workflow) | 2072-2074 |
| ✓ F1 | VII-C/D. Micro-scale benchmark, ablation | 2074-2075 |
| ✓ F1 | VII-E. Scalability (16 and up to 1024 workers) | 2075 |
| ✓ F1 | VIII. Related work; IX. Conclusion | 2075-2076 |
| — | References | 2076-2078 |

## Kernthesen

### 1. ⭐ Cold start, transfer and queuing dominate workflow latency (pp. 2063, 2065)
Under FaaSFlow, transmission, cold start and queuing are 22.92-37.67%, 1.30-8.18% and 34.94-49.90% of average time, 73.91-80.84% together; 84.49-88.42% of tail-request time (p. 2065). This motivates placement plus routing.

### 2. ⭐ Centralised group placement does not scale under concurrency (pp. 2064-2066)
Instances of one workflow far exceed one server, and centralised groups cause migrations as traffic scales (p. 2065). Fig. 5 example: a 2 GB function cannot join its neighbours on an 8 GB server.

### 3. ⭐ Horizontal and vertical grouping (pp. 2066-2068)
See [[horizontal-vertical-grouping]]. Vertical merge on the critical path, then even horizontal split with HG_limit = 4; foreach nodes constrained by the previous interval's maximum concurrency.

### 4. ⭐⭐ Migration-minimizing placement (p. 2068)
See [[migration-minimizing-placement]]. Priority sums reuse_ratio x cold-start time and expected saved transmission under an assumed random routing, plus a tiny AggreFactor that keeps instances of the same function together to shrink the LP.

### 5. ⭐⭐ Placement is regenerated on every scaling request (pp. 2065, 2068)
Placement is re-run each time the platform issues a scaling request (p. 2068). Scaling concurrency = rate x duration, detected at one-minute granularity (p. 2065).

### 6. ⭐⭐ Routing is an LP over path frequencies with a latency cap (pp. 2068-2070)
See [[multi-stage-lp-routing]]. Constraint 1 demands path frequencies cover the predicted branch frequency (an admit-all form); Constraint 2 caps load at alpha = 0.9 of capacity against bursts and failures (pp. 2069-2070).

### 7. ⭐ Invocation frequency is an input, predicted naively (p. 2069)
Future frequency is predicted from the historical trace and instance number; better predictors are declared out of scope. No error analysis, no guarantee.

### 8. Scalability by server groups of 8 and binary search (pp. 2070, 2075)
Scaling-request handling stays under 900 ms at 1024 nodes and 11,000 req/min; per-request scheduling is microseconds (p. 2075).

### 9. Evaluation: six workflows, Azure trace, CloudLab, one baseline (pp. 2071-2072)
Video processing, driver searching, ResNet50 training (second-level), checklist review, calculator, travel guide (millisecond-level). Workload: top-2% Azure Function Dataset trace (average 203.8, peak 264 req/min) with Poisson arrivals inside each minute; 8 workers of 64 cores/128 GB with a sampled available fraction (about 402 GB total), 50 MB/s per instance, scaling interval 1 min; hour-long runs, first 5 min dropped. Baseline: FaaSFlow only. Metrics: average latency, P99, resource consumption.

### 10. ⭐ Headline results (pp. 2072-2074)
Versus FaaSFlow: average latency -48.62 to -62.97% and P99 -41.64 to -51.99% (second-level workflows); P99 -86.60 to -93.46% (millisecond-level); resource use -23.77 to -46.18%. Overhead from cold start, transfer and queuing falls 90.59%, 55.41%, 84.05% (p. 2073). Local transfer share 76.20% vs 42.72% (p. 2074).

### 11. Stable latency across scaling events (p. 2074)
Over 20 minutes and 19 scaling events FaaSPR stays stable while FaaSFlow peaks at 99.4 s because of cascading cold starts.

### 12. Ablation: every part contributes, routing most (pp. 2074-2075)
Average latency vs FaaSFlow: DataTrans* -18.15%, ColdStart* -51.42%, Routing* -55.00%; DataTrans* alone resembles FaaSFlow because without routing a workflow's functions land in different horizontal groups (p. 2075).

### 13. Stated gaps in prior work (pp. 2075-2076)
Palette needs user annotations; FaaSFlow ignores server limits. Xu et al. [21] (placement and routing for workflows in edge networks) is dismissed as relying on an edge setting with no remote storage and no bandwidth constraints, hence unsuitable for data-centre platforms (p. 2076). Prediction (ORION, Kraken, Xanadu, AQUATOPE) is called complementary, not part of FaaSPR (p. 2076).

## Figures and tables
Fig. 2 (random vs local-first routing, p. 2065), Fig. 3 (overhead breakdown, p. 2065), Fig. 4 (architecture, p. 2066), Fig. 8-10 (results), Fig. 13 (micro-scale, p. 2074), Fig. 14 (ablation, p. 2075), Table III (multi-workflow, p. 2073). Not extracted to assets.

### 14. Latency metric, precisely (re-read 26 Oct, pp. 2068-2069, 2072, from an unprotected copy via pikepdf/PyMuPDF; the library PDF has an owner-password restriction, openable with an empty user password)
Two distinct "latency" quantities appear, worth not conflating: (1) the routing LP's internal latency variable (Sect. V, Constraint 3, the latency threshold L) explicitly "does not involve cold starts" (p. 2069) -- execution + transfer only, used solely to decide which routing paths are feasible; (2) the REPORTED evaluation metric ("99th tail latency," Fig. 8b caption, p. 2072) is the full measured per-workflow completion latency including cold starts, queueing and transfer -- "workflow processing latency is determined by the critical path" (p. 2068), one data point per invocation (Fig. 13, "latency per workflow"), hour-long runs with the first 5 min dropped. (2) is the one the paper's headline numbers (-41.64 to -93.46% P99 vs FaaSFlow) refer to, and it is the same statistical object as our p99_makespan (P99 over per-request arrival-to-completion time, warmup excluded) -- comparable in KIND, never in absolute magnitude (different hardware/workload/scenario entirely, see baseline-matrix.md). Resource consumption is also defined precisely: "the sum of the product of resource occupation and execution time for all instances processing the workflow" (p. 2072), normalized to FaaSFlow -- closer to our provisioned_slot_s than mean_containers, though neither is an exact unit match (their resource occupation is continuous memory/CPU, ours is discrete container-slots).

## What this source does not address
No edge setting (remote Redis storage, 8-server cloud cluster); no decision of *when* to re-place beyond the scaling-request clock; no cost-benefit or hysteresis trigger; no forecasting method or robustness guarantee (deferred to prediction work such as AQUATOPE, p. 2076); no admission control or overload shedding; no SLO or goodput metric; no comparison with DFPS-family or NSGA-II/RL schedulers; no state-aware per-request dispatch. Edge placement is the subject of [[jayanthi-2026-quantum]] and of Xu et al. [21] (not in the wiki).

## Focus: novelty gate G0: re-placement timing, forecasts with guarantees, admission control, placement-dispatch coupling (plan input/ideas/faas-edge-adaptation-plan.md) — 2026-10-13

**Carries Kernthesen 4, 5, 6, 7, 9, 10, 13.**

### What this focus needs beyond the Kernthesen
1. (a) WHEN to re-place: only on the scaling-request clock; there is no trigger, hysteresis or reconfiguration budget. Migration avoidance is a reuse bonus in the server priority (Alg. 2, p. 2068), and the abstract's claim to address "frequent instance migrations" (p. 2063) rests on that alone. Cold-start time is the only switching cost; state-transfer cost of moving an instance is not modelled.
2. (b) Forecasts: one-step history-based prediction of branch frequency feeds the LP (p. 2069); no error model, no robustness or consistency bound, and no sensitivity to forecast error in Sect. VII.
3. (c) Admission/overload: none. Constraint 1 requires covering all predicted demand; the only overload provision is the fixed alpha = 0.9 headroom (pp. 2069-2070). Infeasibility arises only from the latency cap (p. 2070) and no shedding is defined. The multi-workflow experiment scales invocation frequency down so total demand does not exceed cluster capacity (p. 2073).
4. (d) Coupling: yes, but one-directional. Placement is computed first assuming random routing (Alg. 2, pp. 2068) plus a bonus that shrinks the routing LP; routing is then optimised for the fixed placement (p. 2069). The paper names the need: "the lack of coordination with routing" (p. 2065). Placement is NOT scored by the dispatch response on upcoming requests: no simulation, queueing model or LP response is inside the placement loop. Routing is an interval-wise probability table (open-loop), not per-request queue-state-aware dispatch.
5. DFPS comparison: DFPS is neither cited nor compared. Setting: cloud datacentre cluster with shared remote storage (CloudLab), not edge; single baseline FaaSFlow; metrics average/P99 latency and resource consumption, not SLO-goodput.

### Direct quotes (for the draft)
> "FaaSPR updates the horizontal and vertical grouping strategy each time the serverless platform sends a scaling request." (p. 2068)

> "In the current version, we predict the future invocation frequency based on the historical trace and instance number." (p. 2069)

> "Another issue with placement strategies is the lack of coordination with routing." (p. 2065)

> "For simplicity, we assume a random routing strategy in the algorithm" (p. 2068)

> "we multiply the load capacity of each instance by a constant factor α, to cope with traffic bursts and instance failures" (p. 2069)

### Examples & illustrations (for later drafting)
- Fig. 2: random routing causes inter-server transfer, local-first routing overloads one instance and queues (p. 2065).
- Fig. 5: 1 GB/1 GB/2 GB sequential workflow on 8 GB servers shows why centralised grouping breaks (p. 2066).
- Fig. 13: 19 scaling events, FaaSFlow peaks at 99.4 s (p. 2074).

### Boundary of this focus
Only the four D1-D3 mechanisms were assessed; data-transfer grouping and LP internals are covered in the Kernthesen only. The reference list was not read, so related prior art cited there (for example [21]) is unverified here.

### G0 verdict
- **D1 (when to reconfigure, switching cost, forecasts with guarantees): partially overlapping.** Only a cold-start-reuse bias inside a clock-triggered placement (Alg. 2, p. 2068) and a naive frequency forecast left out of scope (p. 2069); no trigger, hysteresis, migration bound or robustness guarantee, so the "when" and "guarantee" core of D1 is clear.
- **D2 (admission control and overload-aware dispatch): clear.** No admission or shedding, only alpha = 0.9 headroom (pp. 2069-2070), evaluation kept within capacity (p. 2073), metrics are latency and cost rather than SLO-goodput (p. 2072).
- **D3 (coupled placement and dispatch): partially overlapping.** Placement and routing are explicitly coupled (pp. 2065-2066, 2069) and the ablation shows routing matters most (p. 2075), but placement assumes random routing (p. 2068) and is never scored by the dispatch response on upcoming requests, and routing is an open-loop interval LP; the planned differentiator survives, yet D3 must be positioned against FaaSPR as prior placement-plus-routing work (cloud, not edge).

## Mentioned entities
- Systems: [[faaspr]], [[faasflow]], [[dfps]]
- Concepts: [[horizontal-vertical-grouping]], [[migration-minimizing-placement]], [[multi-stage-lp-routing]], [[cold-start]], [[periodic-replacement-and-rescheduling]]
- Data: [[azure-functions-trace-2019]]

## Connections
- Contradicts: [[faasflow]] (authors' claim); cites [[shahrad-2020-serverless-wild]] and [[azure-functions-trace-2019]].
- Related, not cited by the paper: [[zolfaghari-2025-dynamic-function-placement]] (DFPS), [[periodic-replacement-and-rescheduling]].
