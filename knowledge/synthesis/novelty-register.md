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
| P1 | **Workflow fracturing after a request move**: a moved task's children stay bound to the nodes chosen at arrival | local edges 38.6% planned -> 17.7% executed, 66% of edges fractured (one short run); real cost unknown at full length | ClusterFlow (read; migrates running subgraphs atomically); DesFaaS (known only through ClusterFlow); Pheromone (downstream functions run where the data is); Janus (late binding of downstream sizes); grid rescheduling lineage (Zhao and Sakellariou, Bittencourt and Madeira, Chen et al.) | re-binding the NOT-YET-STARTED descendants at move time, no live state moved, fixed slot budget; a measured application of a long-known principle, not a new one | diagnosing: pilot running, rule R1 |
| P2 | **Slack-blind FIFO queues**: wait on tasks off the critical path; join stragglers | 41% of all wait is off the critical path (one short run); join gap 10 s mean, 26 s in the tail | Archipelago, GrandSLAm, Fifer, Llama, EDF vs SRSF study, METIS | only an application inside a move-based controller; weak novelty | diagnosing: rule R2 |
| P3 | **Move rule ignores data transfer** in generic balancers | shortest-queue moves 11.3% worse than ours; textbook stack 14.2% worse; gap to the stack 8% -> 43% when state sizes grow x10 (one scenario) | ClusterFlow, FaaSPR (placement and routing), work stealing; no published queue-migration rule found | our finish-time move rule and its scaling with data size; no 2025-2026 paper found that measures how a controller's tail scales with state size against off-the-shelf rules (search of 25 Oct, snippet level); the measured decomposition | evidence in hand; pilot confirms; systematic search still to do |
| P4 | **Placement churn**: regrouping and rebuilding layouts cost cold starts | FaaSPR placement 4.9x our cold starts at equal P99; old rebuild rule 3x | FaaSPR (read), ClusterFlow DDAP, mobile facility location, reconfiguration-limited placement (Modena, STEP) | incremental soft-routing placement under a fixed slot budget | built, measured |
| P5 | **Tail made of waiting that routing cannot repair** | no-moves: P99 981 s vs 124 s; LP routing no moves 976 s but mean 23% lower | FaaSPR routing (read), Llumnix (adjacent LLM request migration), Hermod, TensorCast (LLM routers, periodic rebalancing of waiting requests), CLASP (serverless stream processing, queued requests migrate with state), Bittencourt and Madeira 2007 (reschedule queued grid tasks) | the 4-way division of labour: sizing ~ neutral, placement -> cold starts, routing -> mean, moves -> P99 | measured |
| P6 | **Low-load floor and bursty Huawei traffic**: gains compress at 50% load | irreducible P99 about 88 s; RL ahead in 4 of 20 cases | RL baselines, FRAP-DWS, Fifer | not pursued; known limit | limit stated |
| P7 | **Overload without admission** | goodput x2.4 with admission, 27% rejected | Archipelago-style admission, queue thresholds | not our contribution unless the professor decides | decision pending |

## Open literature questions (first answers in [[literature-search-2026-10-25]], snippet level; a systematic search is still open)
1. Recent (2025-2026) work on request or task re-planning after migration in serverless workflows (P1).
2. Recent work on tail latency in serverless DAGs under data-intensive states (P3).
3. Whether any serverless work moves queued requests as a periodic control step (Llumnix and Ermes are adjacent only).
4. Grid-workflow rescheduling after task migration (a reviewer-supplied claim, 2008-era, unverified).

## How an entry moves
diagnosed (trace or ablation) -> nearest work read -> gap stated in one sentence -> decision rule written before the result -> built only if the rule fires -> success criterion on development seeds -> confirmation on fresh seeds.

## Candidate checks (25 Oct), against an externally proposed list
- **Fracture-aware move gating**: already inside our move rule. `Sol.aet` (dfps/solution.py:109-117) = input transfer + queue wait + `sum(stt(state, candidate node, planned node of each child))`, and a request moves only if that total improves, so the downstream transfer penalty of a move is priced today. What remains is an optional margin or hysteresis (move only if the gain exceeds m seconds), which is a churn control, and ClusterFlow's threshold delta is its precedent. ClusterFlow also prices severed heavy edges in its objective J and defers single-function migration (Sec. 3.2 and 5.5), so "ClusterFlow only changes the unit" is too strong.
- **Locality-aware queue pop**: no effect in this model. A request is enqueued at a node only after all its input states are stored there (`Sim._ev_state`), and a relocation moves the states with it, so every queued request is already local to the node whose slot frees.
- **Join-anchored (minimax) placement**: partly explored: the DFPS dispatcher has the critical-path matching objective (erratum E5 variant, `match_objective="critical"`), used in the D2 oracle; not evaluated inside our controller.
- **Successor-aware placement, state propagation, delayed moves, slack weighting**: precedents or unverified; "AnchorDL" and "AeroFlow" could not be found by search and must not be cited.

## Candidate check (25 Oct): lambda x T cross as an explanation of the super-multiplicative interaction
- The T axis is a within-controller parameter (re-layout epoch of FROZEN-1/2: 60 s, 30 s variant held out; 15/30/60 s on the six hardest 50% cases). The lambda axis (weight on the downstream term of `Sol.aet`) does not exist yet and needs one new churn parameter.
- The substitution-through-staleness hypothesis (aggressive moves allow a longer period) is contradicted by the layout-age test: with moves on, a layout applied 60/120/300 s late costs +44/+113/+370% P99, i.e. moves do not repair a stale layout.
- Free check on the existing 2x2 (old settings: affinity placement, cap 300; 18 cases): the interaction (log scale, negative = more reduction than the product) is -0.21 at 50% load, -0.66 at 70%, -0.80 at 85%, and -0.87 on Azure against -0.24 on Huawei. It grows with load, the signature of a queueing nonlinearity (each fix lowers effective utilisation and P99 diverges near saturation) plus the capacity-versus-queue complementarity. To be recomputed on the FROZEN-1 grid whose interaction is -1.30.
- Decision: do not run a 60-90 run lambda x T grid. Run the planned lambda sweep as a sensitivity row; extend the load axis (60/78/92%) as part of the operating envelope. Pre-set null: optimal T unchanged between lambda 0.5, 1 and 2 within +-2%.

## Placement x moves substitution (25 Oct) -- the one durable result from the interaction-hunt thread
"With moves uncapped, placement quality has no detectable P99 effect: 140.3 vs 141.0 s (paired +0.2%, 95% interval -1% to
+1%, 8/18 wins) despite 3.1x fewer cold starts (1,396 vs 4,386)." This is the SAFE form: we do not have a moves-off x
placement cell (fp_route_nm/ours_nm vary the dispatcher with the SAME placement, not placement with moves off), so
"substitutes" (a cross-derivative claim) is not established, only "no detectable P99 effect with moves on" is. Ties three
findings together: why FaaSPR's placement ties us on P99 despite 4.9x the cold starts (moves absorb the churn); why the
random-placement stack's comparison was uninterpretable (not moves-matched against a controlled baseline); the general
division of labour (placement -> cold starts, moves -> P99, see [[baseline-matrix]]). In the deck, slide 18.

## Interaction-hunt thread closed (25 Oct)
Checked a proposed "sizing enables moves via a free slot" mechanism against the code: WRONG for the fixed-budget controller
(proportional_counts always fills every slot; a move needs storage space at the destination, not an empty container --
dfps/sim.py relocate()/`_reroute`). The elastic-mode version (a real free-slot concept) was checked for a free analysis path:
el50/65/80 (output/data-analysis/elastic_sweep.py) all use rebal_max=10**9 (unlimited moves), so there is no moves-off arm
and no free analysis. Given the review's own prior (saturation-family, a third saturation result adds nothing) and the cost
(20 new runs), this is not built. No further interaction hunting; the existing re-layout x moves interaction (-0.21 to -0.80
by load) stands as the project's one interaction finding.

## First envelope data point and a real ping-pong number (25 Oct, smoke)
rho=0.92, k=1, ours, F1 (140 s window): completed = arrived = 2,865 (no censoring), unfinished 0, parked 0, P99 159.95 s --
barely above the 85%-load k=1 number (157.8 s, affinity_probe.py), i.e. the controller ramps from 85% to 92% gracefully at
normal data intensity with no admission. Ping-pong (share of moved tasks moved >=2 times): 17.7%, inside the 15-25% range an
earlier review flagged as worth a cooldown/pruning rule -- first real number on this question, from one cell; needs the full
grid before acting. k=20 dropped from the envelope grid: the stack-controller, k=20, rho=0.92 cell ran 26+ minutes with no
result (1.1 GB memory) before being stopped; plausibly pathological (no locality awareness + very large transfers + near
overload), not worth the risk when k=1/10 already show the scaling trend clearly.
