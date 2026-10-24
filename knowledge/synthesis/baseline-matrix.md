---
title: "Baseline matrix: what is run, what is an ablation, what is cited only (controller evaluation)"
type: synthesis
created: 2026-10-24
updated: 2026-10-24
tags: [baselines, related-work, evaluation, controller]
sources:
  - "[[zolfaghari-2025-dynamic-function-placement]]"
  - "[[gunasekaran-2020-fifer]]"
  - "[[bhasi-2021-kraken]]"
  - "[[daw-2020-xanadu]]"
  - "[[lei-2026-adaptive]]"
  - "[[liao-2025-adaptive]]"
  - "[[liu-2025-sdser]]"
  - "[[ma-2025-online-deployment]]"
  - "[[tian-2024-sfsm]]"
  - "[[jia-2025-faaspr]]"
status: draft
author: llm
bibliography: ../../output/bibtex/references.bib
---

# Baseline matrix

Our controller = a re-layout every 60 s (sizing + incremental soft-routing placement) + finish-time request moves every 4 s, fixed slot budget, no B* annealing (FROZEN-2). Metric for every row: **P99 completion latency** (arrival of a request to the end of its last task; the DFPS paper's "makespan" is the same quantity, reported as a mean), requests arriving in a 900 s window after a 60 s warm-up, same scenarios, seeds and simulator. Reference for gains: the best of B*, RL, RL_CAL per case ("best existing").

## 1. Systems we run (comparison, not ablation)

| Method | Reference | What it is here | Status / caveat |
|---|---|---|---|
| **B\*** | Zolfaghari et al. 2025, [[zolfaghari-2025-dynamic-function-placement]] | DFPS rebuilt from the paper with errata E1-E4 fixed; keeps its own tuned move period (T* = 4 s Azure, 8 s Huawei) | Our own reimplementation, no authors' code. 3 of 3 paper claims reproduced |
| **RL** | Yang et al. (MOSEC), IEEE TSC 2025 | DDQN dispatcher, one step at a time, no fixed layout; follows the paper DFPS names as its RL baseline | Trained on the first calibrated-from-paper scenario; result depends on the training run (up to 2x) |
| **RL_CAL** | same | the same RL retrained on the calibrated reproduction scenario (24 episodes x 90 s, 80 nodes) | Weaker than RL in a first test; both kept, best taken per case |
| **Heu** | Xu et al. | per-request joint placement and scheduling | Run only on a subset: 2.5-5.3 h per run at load 0.7; dropped for the later runs (user decision 2026-10-18) |

## 2. Mechanism 1 (sizing): rules swapped into our controller

| Method | Reference | Role | Status |
|---|---|---|---|
| HPA-style: containers = ceil(load / 0.8), no backlog term | Kubernetes HPA, Knative | run (ablation) | On the final controller: re-running (`final_ablation.py`, results/fx.txt). Earlier result on the older controller: 3.6% worse |
| Fifer-style: backlog containers only if drain time exceeds a cold start | [[gunasekaran-2020-fifer]] | run (ablation) | as above; earlier 70.9% worse; LSTM part not used |
| Kraken-style: DAG weights (connectivity + commonality, cap 0.25) | [[bhasi-2021-kraken]] | run (ablation) | as above; earlier 5.4% worse; cap value is ours (not given in the paper) |
| Rate oracle / simulation-scored layouts (foresight) | own | run (ablation) | plain rule reached 97-121% of their result |
| FRAP-DWS (Wang et al., IEEE Trans. Computers 2026) | own notes | cite only | per function, no workflows, no placement; no fair comparison possible |
| Xanadu (cascading cold starts, speculative deployment) | [[daw-2020-xanadu]] | cite only | targets cold-start cascades, not a capacity re-layout |

## 3. Mechanism 2 (placement): variants of our own rule

| Variant | Role | Status |
|---|---|---|
| Rebuild whole layout every minute (affinity rule) | ablation | with unlimited moves P99 141.0 vs 140.3 s, but 4,386 vs 1,396 cold starts |
| Random placement | ablation | 12.8% worse (earlier controller) |
| k-median from scratch / incremental k-median / nearest-container cost | ablation | from scratch 11.5% worse; soft routing +2.7%, waiting term +0.9% |
| Facility location / k-median, mobile facility location, cDSMA (incremental service migration), Modena 2025 and STEP 2026 (reconfiguration-limited microservice placement) | cite only | no one combines a fixed slot budget, incremental placement and queued-request redistribution (abstract-level search) |
| **FaaSPR placement** (Jia et al., IEEE/ACM ToN 2025, [[jia-2025-faaspr]]): migration-minimizing placement. Priority of a server for a group = expected cold starts saved by reusing live instances + expected transfer saved (random routing assumed) | **candidate to run** (placement rule swapped into our controller, same sizing counts) | closest published match to our incremental placement: both start from the live layout and prefer reuse. Differs: groups functions by workflow critical path (horizontal and vertical grouping), regenerated at each scaling request, counts come from the platform. Needs a faithful port of the grouping and priority rules |
| **FaaSFlow-style grouping** (co-locate functions along the critical path; the baseline both FaaSPR and BeeFlow beat) | candidate to run (placement ablation) | our co-location measurement says transfer is only 7-11% of the critical path, so this should help little; running it would test that claim directly |
| **BeeFlow** (Luo et al., J. Systems Architecture 2023): behavior-tree workflows, contention-aware partitioning and placement for resource-constrained edge clusters | cite only | static placement per workflow, no re-layout, no request moves; its observation that eager co-location overloads a few nodes supports our finding that spreading matters more than closeness. Baseline there is FaaSFlow on an SBC cluster |
| **ClusterFlow** (Ahmadpanah and Sobhanloo, Computer Networks 287 (2026) 112562, doi 10.1016/j.comnet.2026.112562; read 24 Oct from the PDF, metadata not yet checked on the publisher site) | cite and contrast | names the problem "workflow fracturing": migrating one function away from its producers and consumers turns local state access into network transfer. Groups strongly coupled functions into "Workflow Pods" with a greedy agglomerative partitioner (DDAP: merge along the heaviest edges while the pod fits a node) and migrates a pod atomically with group checkpointing (CRIU, eBPF routing). 12-node Kubernetes testbed, baselines Vanilla K8s + HPA, FAASM, DesFaaS: P99 -35.7% vs DesFaaS, cross-node traffic -77.2% vs K8s and -61.7% vs DesFaaS, migrations -76.9%. Closest to our mechanism 2 (co-locating containers by data affinity); it moves live containers and their memory, which our simulator does not model, so it cannot be run faithfully here. DDAP is the same greedy idea as FaaSPR's vertical grouping |
| **Archipelago** (Singhvi et al., arXiv 1911.09849) | cite and contrast | slack-based scheduling: shortest remaining slack first, extended to DAGs by recomputing the slack of each function after its predecessors finish. The closest published form of slack-aware queue ordering |
| **GrandSLAm** (Kannan et al., EuroSys 2019), **Fifer** ([[gunasekaran-2020-fifer]]), **Llama** (arXiv 2102.01887) | cite and contrast | per-stage slack: GrandSLAm reorders requests with low computational slack first; Fifer spreads the total slack over the stages (static, linear chains); Llama computes slack dynamically over DAG paths |
| EDF versus shortest-remaining-slack-first for serverless DAGs (Sledge, EdgeSys 2022) and **METIS** (SoCC 2025, critical-path prioritisation at the OS level), AARC (arXiv 2502.20846, critical-path resource configuration) | cite and contrast | all abstract-level; the two ordering policies perform about equally in the Sledge study |
| DesFaaS (cited by ClusterFlow as ref. [11]) | cite only, not read | function-granular joint migration of a function and its persistent state; the "fracturing" predecessor in ClusterFlow's account |
| Edge DAG deployment papers: [[ma-2025-online-deployment]], [[liu-2025-sdser]], [[tian-2024-sfsm]] | cite only (candidates to run) | prediction or learning based; need code or a faithful reimplementation to be run |

## 4. Mechanism 3 (request moves): rules swapped in, and the cap

| Method | Reference | Role | Status |
|---|---|---|---|
| Finish-time move rule (ours; B*'s own AET estimate) | B*, Eq. 8 | the method | no cap, every 4 s and right after a re-layout |
| No request moves | own | ablation | 2x2: 1,022 s vs 130 s (geometric-mean P99) |
| Join-shortest-queue moves | textbook rule | run (ablation) | final-controller re-run in progress; earlier 9.0% worse |
| Work stealing | textbook rule (Blumofe-Leiserson style) | run (ablation) | as above; earlier 28.6% worse |
| Move caps 100 / 300 / 1000 / none | own | ablation | +55.9 / +70.5 / +77.5 / +77.9% over B* at 85% load |
| **Hermod** | Kaffes, Yadwadkar, Kozyrakis, SoCC 2022 | **candidate to run**, otherwise cite and contrast | early binding plus processor sharing per worker; consolidates at low load. Not a queue-migration scheme, so it contrasts with ours; a faithful port to our model is a real piece of work |
| **FaaSPR routing** (multi-stage LP over routing paths, load capped at 0.9 of instance capacity, paths chosen by weighted random per invocation) | [[jia-2025-faaspr]] | **candidate to run** as a dispatcher replacement (dispatcher test) | the real alternative to mechanism 3: it prevents imbalance by routing arrivals in proportion to capacity, we repair it by moving what is already waiting. Needs a port (scipy LP per re-layout). Reported ablation: routing contributes most (avg latency -55.00% vs FaaSFlow) |
| **Llumnix** | Sun et al., OSDI 2024 (Alibaba) | cite and contrast (adjacent, closest in spirit) | reschedules requests across LLM-serving instances at runtime by live migration, for load balancing, de-fragmentation, priorities and faster scaling. Different domain (LLM serving, GPU-memory state, no workflow DAGs, no container layout), but it is the strongest evidence that runtime request migration is a known idea; our novelty statement must be limited to serverless workflow control on a fixed container budget |
| **Ermes** | stateful serverless platform for the edge-cloud continuum (arXiv 2609.18924; Politecnico di Milano theses) | cite and contrast | ILP placement plus a decentralised policy that migrates state and function logic toward demand (user locality). Migrates state and functions, not queued requests between live containers. Abstract level only |
| Sparrow | Ouyang et al., SOSP 2013 | cite only | late-binding, pull-based probing; no migration of queued tasks |

## 5. Dispatcher independence (does the controller need DFPS's graph matching?)

greedy_eft, locality, jsq, random dispatchers, each under B* and under ours (96 runs, `dispatcher_sweep.py`): queued after admission round 2. Cheap additions suggested by HyperDrive's baselines: first-fit and round-robin. Larger addition: FaaSPR-style LP routing (see section 4).

| Paper | Mechanism | Role |
|---|---|---|
| **HyperDrive** (Pusztai, Marcelino, Nastic, IEEE/ACM SEC 2024) | filter-then-score multi-criteria node choice per function (SLO, latency, satellite temperature, energy); multi-commit on conflicts; one-shot placement | cite only. Built for LEO satellites; its baselines are first-fit, round-robin and random on network latency, no queues, no re-layout. Only the three simple rules are reusable |
| **SCALE** (Xu et al., arXiv 2606.06820, 2026) | DRL cross-attention pointer network assigns ready DAG primitives to servers, with a regulariser so it generalises to unseen cluster sizes | cite only. Agentic LLM workflows, one primitive per server at a time, no containers, no cold starts, no layout. Same class as the RL baseline (a learned dispatcher) and it supports our no-learning argument; not a comparable controller |

## 6. Mechanism ablations (what each part contributes)

Re-layout x request moves 2x2 (done); taking B* apart (done); layout-age test (done); move period 2/4/8 s (done); re-layout every 30 s (done); elastic capacity (done). Not yet isolated: "new counts with old placement" (sizing without the incremental placement).

## 7. Literature search record (2026-10-24, abstract level, web search only)

Queries (8): Hermod; queued-request migration / work stealing in serverless; serverless DAG edge placement with periodic re-placement; Dirigent; DRL container scheduling at the serverless edge; request migration / work stealing at the edge for DAGs; platform re-dispatch of queued invocations; Kraken, Fifer, Xanadu baselines.

Findings:
- **No paper found that migrates already-queued requests between live containers or nodes for serverless workflows** (adjacent: Llumnix migrates in-flight LLM requests between serving instances; Ermes migrates state and functions at the edge). Platform queues are pull-based (OpenFaaS queue-based scaling, AWS SQS + Lambda, Temporal workers): work is pulled by whichever worker has capacity; nothing is reassigned. OpenWhisk controllers move to the next host above a load threshold at dispatch time. A 2018 Google Summer of Code proposal for OpenWhisk work stealing exists, with no evaluated result found.
- **The closest prior art is DFPS itself.** Its part 3 (Alg. 1, relocation gain Eq. 8) already pulls waiting requests to a new container's server, one trial at a time inside the annealing. Our claim is therefore not "moving queued requests" but: moving them systematically (longest queues first, finish-time estimate, no cap, right after a layout change) is what carries the gain, and it multiplies with the re-layout (2x2, interaction -1.30).
- **Hermod (SoCC 2022):** taxonomy of serverless schedulers; early binding plus per-worker processor sharing beats late binding and random balancing under common execution-time distributions; reported up to 85% lower slowdown and 60% higher throughput on OpenWhisk. Single functions, no workflow DAGs, no queue migration.
- **Papers supplied by you (read, 24 Oct):** FaaSPR (already in the wiki), HyperDrive, BeeFlow, SCALE. None moves already-queued requests. FaaSPR is the nearest on mechanisms 2 and 3 (reuse-aware placement; capacity-proportional routing), so it is the one to port. Note: the "Scale" I listed earlier (arXiv 2605.15704, DRL container scheduling at the serverless edge) is a different paper from your SCALE (arXiv 2606.06820, agentic workflows); the former has not been read.
- **Other edge serverless schedulers seen:** Lou et al. (shortest-function-first with cold-start-aware instance initialisation, arXiv 2310.16475), HyperDrive (edge-cloud-space DAG scheduling, arXiv 2410.16026), Li et al. (dependent task placement with on-demand function configuration, ACM DOI 10.1145/3616374), "Scale" (DRL container scheduling at the serverless edge, arXiv 2605.15704, only its reference list was seen), BeeFlow (workflows as behaviour trees on resource-constrained edge clusters), Dirigent (SOSP 2024, cluster-manager design, not a policy comparison).
- **Not done:** a systematic search with documented queries in IEEE Xplore, ACM DL, Scopus and Semantic Scholar, with inclusion and exclusion criteria. Nothing above was read beyond abstracts and search snippets. Until that is done, the novelty statement is "we found no prior work", not "there is none".

## What stays open
- FaaSPR code is written (placement, LP routing; variants fp_place, fp_route, fp_both, fp_pub in `faaspr_sweep.py`). fp_pub changes three things at once and is only a published-configuration reference, never a controlled baseline. Report FaaSPR placement together with its churn (cold starts) and P99, since higher churn is only a cost if it does not buy lower P99. Check LP feasibility and fallback counts in the smoke test before any full run. The sampled-path and shared-LP adaptations may handicap the routing; if fp_route underperforms, say so.
- Workflow-aware extensions under consideration (24 Oct), with their lineage: (1) re-binding the not-yet-started descendants of a request when one of its tasks is moved: same principle as ClusterFlow's subgraph migration (do not sever heavy edges when moving), and a form of late binding (Hermod's early/late binding taxonomy; our RL baseline already binds each step when it becomes ready); it moves no live state, because the inputs of unstarted tasks do not exist yet. (2) critical-path-weighted placement: refines our pairwise affinity; direct precedents in FaaSPR's vertical grouping and ClusterFlow's DDAP. Neither is a new concept; both would be presented as measured refinements, built only if workflow_stress.py shows the gap to the textbook stacks growing with data intensity. A reviewer's claim of 2008-era grid-workflow rescheduling after migration is not yet verified.
- (superseded) Decide whether FaaSPR is ported: placement rule (reuse priority) and LP routing are the two parts that map onto ours; the LP routing is the more interesting contrast.
- Decide whether Hermod is run (port to our model) or cited and contrasted.
- Decide which of the edge DAG schedulers (Lei AUHS, Liao EGAT, Liu Sdser, Ma OPTS, Tian SFSM) can be run fairly; none has been run so far.
- Add the "sizing without incremental placement" ablation.
- Re-run the sizing, shortest-queue, stealing and textbook-stack ablations on the final controller (in progress) and update the deck.
- Run the systematic search before any novelty claim goes into a paper.
