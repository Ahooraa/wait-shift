---
title: "Novelty register: diagnosed problems, nearest published work, remaining gap"
type: synthesis
created: 2026-10-25
updated: 2026-10-25
tags: [novelty, related-work, diagnosis, workflow-awareness]
sources:
  - "[[zolfaghari-2025-dynamic-function-placement]]"
  - "[[jia-2025-faaspr]]"
  - "[[gunasekaran-2020-fifer]]"
  - "[[bhasi-2021-kraken]]"
status: draft
author: llm
bibliography: ../../output/bibtex/references.bib
---

# Novelty register

Working rule (user, 2026-10-25): diagnose first, map the latest related work on that exact problem, then look for a novel solution. One row per diagnosed problem. "Evidence" is what we measured; "nearest work" is what a reviewer will cite; "gap" is the narrow claim that survives; "status" says whether anything is built. All literature entries are abstract-level unless marked read. See [[baseline-matrix]] for the papers and [[workflow-aware-decision-rules]] for the build thresholds.

| # | Diagnosed problem | Evidence (ours) | Nearest published work | Remaining gap | Status |
|---|---|---|---|---|---|
| P1 | **Workflow fracturing after a request move**: a moved task's children stay bound to the nodes chosen at arrival | local edges 38.6% planned -> 17.7% executed, 66% of edges fractured (one short run); real cost unknown at full length | ClusterFlow (read; migrates running subgraphs atomically); DesFaaS (function-granular predecessor) | re-binding the NOT-YET-STARTED descendants at move time, no live state moved, fixed slot budget; a late-binding form | diagnosing: pilot running, rule R1 |
| P2 | **Slack-blind FIFO queues**: wait on tasks off the critical path; join stragglers | 41% of all wait is off the critical path (one short run); join gap 10 s mean, 26 s in the tail | Archipelago, GrandSLAm, Fifer, Llama, EDF vs SRSF study, METIS | only an application inside a move-based controller; weak novelty | diagnosing: rule R2 |
| P3 | **Move rule ignores data transfer** in generic balancers | shortest-queue moves 11.3% worse than ours; textbook stack 14.2% worse; gap to the stack 8% -> 43% when state sizes grow x10 (one scenario) | ClusterFlow, FaaSPR (placement and routing), work stealing; no published queue-migration rule found | our finish-time move rule and its scaling with data size; the measured decomposition | evidence in hand; pilot confirms |
| P4 | **Placement churn**: regrouping and rebuilding layouts cost cold starts | FaaSPR placement 4.9x our cold starts at equal P99; old rebuild rule 3x | FaaSPR (read), ClusterFlow DDAP, mobile facility location, reconfiguration-limited placement (Modena, STEP) | incremental soft-routing placement under a fixed slot budget | built, measured |
| P5 | **Tail made of waiting that routing cannot repair** | no-moves: P99 981 s vs 124 s; LP routing no moves 976 s but mean 23% lower | FaaSPR routing (read), Llumnix (adjacent LLM request migration), Hermod | the 4-way division of labour: sizing ~ neutral, placement -> cold starts, routing -> mean, moves -> P99 | measured |
| P6 | **Low-load floor and bursty Huawei traffic**: gains compress at 50% load | irreducible P99 about 88 s; RL ahead in 4 of 20 cases | RL baselines, FRAP-DWS, Fifer | not pursued; known limit | limit stated |
| P7 | **Overload without admission** | goodput x2.4 with admission, 27% rejected | Archipelago-style admission, queue thresholds | not our contribution unless the professor decides | decision pending |

## Open literature questions (to be answered with a documented search, not snippets)
1. Recent (2025-2026) work on request or task re-planning after migration in serverless workflows (P1).
2. Recent work on tail latency in serverless DAGs under data-intensive states (P3).
3. Whether any serverless work moves queued requests as a periodic control step (Llumnix and Ermes are adjacent only).
4. Grid-workflow rescheduling after task migration (a reviewer-supplied claim, 2008-era, unverified).

## How an entry moves
diagnosed (trace or ablation) -> nearest work read -> gap stated in one sentence -> decision rule written before the result -> built only if the rule fires -> success criterion on development seeds -> confirmation on fresh seeds.
