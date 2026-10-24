---
title: "Literature search 2026-10-25: re-binding after migration, data-intensive tails, queued-request migration"
type: synthesis
created: 2026-10-25
updated: 2026-10-25
tags: [literature-search, related-work, novelty, workflow-awareness]
sources:
  - "[[zolfaghari-2025-dynamic-function-placement]]"
  - "[[jia-2025-faaspr]]"
  - "[[gunasekaran-2020-fifer]]"
  - "[[bhasi-2021-kraken]]"
status: draft
author: llm
bibliography: ../../output/bibtex/references.bib
---

# Literature search, 25 Oct 2026

**Method and limits.** Web search only (no IEEE Xplore, ACM DL, Scopus or Semantic Scholar queries), 26 queries in total over this and the earlier 24 Oct session, results read at snippet and abstract level; the full texts of FaaSPR, HyperDrive, BeeFlow, SCALE and ClusterFlow were read from the supplied PDFs earlier. Nothing here is a systematic review, so every "none found" means "not surfaced by these queries". Inclusion: serverless, FaaS or edge/cloud workflow (DAG) control; older grid-workflow work kept where it matches a mechanism. The search answers the four open questions of [[novelty-register]].

## Queries (25 Oct) and what each returned

| # | Query (shortened) | Most relevant results |
|---|---|---|
| 1 | serverless workflow rescheduling of downstream tasks after migration, re-binding dependents | Pheromone / "Following the Data, Not the Function" (local triggering of downstream functions next to their data), Metronome (ICSE 2026, delay scheduling for locality), serverless survey, Nardelli and Russo (ICPE 2024, state migration with offloading). No paper re-binding dependents after a migration |
| 2 | late versus early binding in serverless workflow scheduling | Hermod (binding of invocations to workers), Janus (arXiv 2502.14320, IPDPS 2025: late binding of function SIZES, downstream sizes adapted as upstream functions finish) |
| 3 | tail latency, data-intensive serverless DAGs, state transfer, locality (2025-2026) | Archipelago, Wukong, Metis (SoCC 2025, slides only), Pheromone. No 2025-2026 paper combining the three |
| 4 | migration of queued requests between edge nodes, periodic rebalancing | TensorCast (periodic rebalancing of waiting requests in LLM inference routers), a patent on stealing queued workloads between edge nodes, KubeDSM. Nothing for serverless workflows |
| 5 | grid-workflow rescheduling after task migration | Zhao and Sakellariou (low-cost rescheduling of dependent tasks at a few chosen points), Chtepen et al. (ModSim 2009, run-time rescheduling, postpone migration when the gain is low), Bittencourt and Madeira (SITIS 2007, reschedule QUEUED tasks away from poorly performing resources), Chen et al. (J. Supercomputing 2015, rearrange and reschedule using precedence slack so that a delay does not propagate to successors), a UConn dissertation on migrating dependent task sets |
| 6 | incremental redeployment with migration cost at the edge | multi-cloud microservice re-orchestration (arXiv 2401.01408), migration planning in SDN edge (arXiv 2111.08936), live migration versus re-instantiation. No serverless paper pricing reconfiguration |
| 7 | joint autoscaling and placement, DAG-aware, fixed capacity | ContinuumBench (arXiv 2609.08946, benchmark of joint autoscaling and placement, 2026), Kraken, the DFPS paper. No Kraken successor found |
| 8 | workflow-aware dispatch by finish time with queue wait, transfer time and joins | HEFTLess (HEFT-style, batch completion), ADRL and WSRIT (Li et al.: dispatch plus queue ordering by remaining idle time), SoDa/EWSF (deadline-aware). None models transfer, queue wait and join together |
| 9 | Pheromone (follow-up on query 1) | NSDI 2023, IEEE/ACM ToN 2025: data buckets with triggers, two-level local-first scheduling of downstream functions |
| 10 | ClusterFlow citation check | no abstract found by search; one ACM reference list cites "Ahmadpanah S, Sobhanloo S (2026) ClusterFlow ... Computer Networks, 10.1016/j.comnet.2026.112562, vol. 287"; the DOI redirects to Elsevier but the publisher page could not be fetched. Existence corroborated by one independent citation; metadata not checked on the publisher page |
| 11 | DesFaaS | no source mentions DesFaaS by name; Ermes and Nardelli and Russo turned up instead. DesFaaS is known to us only through ClusterFlow's account of it |
| 12 | stragglers and tail latency at fan-out and fan-in | WiseFuse, Orion, Archipelago, Wukong |
| 13 | Janus (follow-up on query 2) | adapts downstream function sizes at run time as the remaining budget changes; developer hints plus provider rules; up to 34.7% better resource efficiency (authors' figure) |
| 14 | ClusterFlow extended search | only the citation above; adjacent: CLASP (arXiv 2608.29103, serverless stream processing: after a scaling decision, workers exchange state AND queued requests according to a migration plan), Databelt (arXiv 2508.15351, state path for serverless workflows in the 3D continuum), ClusterLess (arXiv 2605.04310), live migration of multi-container pods in multi-cluster serverless edge (ACM 2024) |

## Answers to the open questions

1. **Re-planning after migration in serverless workflows (P1).** Not found for serverless. The idea is old in grid workflows (Zhao and Sakellariou; Chtepen; Bittencourt and Madeira; Chen et al.: reschedule at selected points, weigh migration cost against gain, keep a delay from propagating to successors). In serverless the principle appears as ClusterFlow (migrate the dependent subgraph with it), Pheromone (run downstream functions where the data is) and Janus (bind later, as the upstream finishes, but for function sizes). A re-binding rule for unstarted descendants would be a re-use of a long-known principle in a new setting, and should be presented as that.
2. **Tail latency of data-intensive serverless DAGs (P3).** No 2025-2026 paper found that measures how a controller's tail scales with state size against off-the-shelf rules. Our x1 to x10 scaling result (P99 grows by 1.9 against 3.1 for the HPA + shortest-queue stack, one scenario, pending the pilot) has no direct counterpart in what surfaced; that is a candidate contribution, to be verified with a systematic search.
3. **Queued requests moved as a periodic control step (P5).** The adjacent set is larger than we had: TensorCast (LLM request routers, threshold-triggered rebalancing of waiting requests), CLASP (serverless stream processing, queued requests migrate with state at scaling), Llumnix (LLM instances), a patent on stealing queued workloads between edge nodes, and the old grid result of rescheduling queued tasks (Bittencourt and Madeira 2007). None is serverless workflow control on a fixed container budget. The narrow claim stands; "no prior work" must not be written.
4. **Reviewer-supplied claim on grid-workflow rescheduling after migration.** Substantiated in spirit (see 1), not verified for the exact statement "migration used to trigger rescheduling of dependents".

## Consequences for the register
- P1 (fracturing): nearest work now includes the grid lineage and Pheromone; the claim is a measured application, not a new principle.
- P2 (slack-blind queues): already weak; nothing new here.
- P3 (transfer-blind moves, scaling with data size): the most promising empirical gap; needs the pilot and a systematic search.
- P5 (queued requests): add CLASP and TensorCast to the adjacent set.
- New items to read in full before any novelty sentence: CLASP, TensorCast, Zhao and Sakellariou, Bittencourt and Madeira, Chen et al. 2015, Janus, Pheromone, Metronome, ContinuumBench, Databelt.
