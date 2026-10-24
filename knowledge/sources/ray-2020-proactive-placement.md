---
title: "Ray, Banerjee & Narendra 2020 — Proactive Microservice Placement and Migration for Mobile Edge Computing"
type: source
created: 2026-10-20
updated: 2026-10-20
status: review
author: llm
bibkey: ray-2020-proactive-placement
depth: standard
tags: [edge, microservices, prefetching, migration, reinforcement-learning, dyna-q, linear-workflow, g0-novelty, related-work]
relations:
  - target: predictive-pre-deployment
    type: supplements
    confidence: extracted
    because: "Prefetches successor microservices along a workflow before they are invoked; the first work claimed to exploit the dependency graph for prefetching in MEC (Sec. I, p. 29)."
  - target: deathstar-benchmark
    type: mentions
    confidence: extracted
    because: "Container sizes and start times come from DeathStarBench Media Microservices (Sec. V-A, p. 36)."
  - target: cold-start
    type: mentions
    confidence: extracted
    because: "Container initialisation latency is the cost that prefetching hides (Sec. II, p. 29)."
  - target: migration-minimizing-placement
    type: mentions
    confidence: inferred
    because: "Counts the cost of migrating or re-initialising deployed-but-unused services in the reward (Eq. 2, p. 34)."
---

# Proactive Microservice Placement and Migration for Mobile Edge Computing

## Bibliographic Details
Ray, Kaustabha; Banerjee, Ansuman; Narendra, Nanjangud C. 2020. *Proactive Microservice Placement and Migration for Mobile Edge Computing*. 2020 IEEE/ACM Symposium on Edge Computing (SEC), pp. 28-41. DOI 10.1109/SEC50012.2020.00010.

> Page note: printed pages 28-41; the page number printed at the bottom closes the page it follows.

## Section map

| Covered | Section | pp. |
|---|---|---|
| ✓ F1 | I Introduction (reactive versus proactive; linear workflows; contributions) | 28-29 |
| ✓ F1 | II Motivating example (on-demand, prefetching, prefetching plus migration, Tables I-III) | 29-31 |
| ✓ F1 | III Formal model: MDP states [service, distance], blocks, transitions, migration | 31-34 |
| ✓ F1 | IV RL solution: Dyna-Q, reward, load-dependent MDPs, capacity heuristic, Alg. 2 | 34-36 |
| ✓ F1 | V Evaluation: San Francisco taxi traces, DeathStarBench timings, MCAPP-IM and on-demand baselines | 36-39 |
| ✓ F1 | VI-VII Related work and conclusion | 39-41 |

## Kernthesen

### 1. ⭐ Traditional placement and migration policies are reactive (deploy after an invocation); the paper proposes a proactive one that prefetches successor microservices using the application's dependency structure (p. 29)
Claimed first work to exploit the microservice task-graph structure to prefetch and pre-provision in MEC.

### 2. Microservices are containers with non-trivial initialisation; creating a task in an existing container is cheaper; prefetched but unused services have no state to migrate (Sec. II, pp. 29-30)
Example numbers: 25 ms initialise, 10 ms new task, 30 ms migrate.

### 3. ⭐ The example shows a 66% speed-up of proactive prefetching plus migration over on-demand placement, and the key trade-off: prefetching all successors wastes resources, never prefetching adds latency to every invocation (pp. 30-31)

### 4. ⭐ The decision is how many successor services (j, 0 < j < n-i) to deploy with the current one and on which server; migration moves the service in use with state, re-initialises the unused ones (Sec. III-A, p. 31)
Linear workflows only; one single edge server per user's active set h(t).

### 5. ⭐ The MDP has states [service set, discretised distance 0..k] arranged in blocks i = 0 (reactive) to n-1 (prefetch everything); inter-block transitions encode the prefetch count (Sec. III-B/C/D, pp. 32-33)
Minimised applications need no encoding: prefetched services stay until exit.

### 6. ⭐ Rewards are unknown, so learning uses Dyna-Q (Q-learning plus simulated updates from a stored model); the reward weighs the resource cost of prefetched services that were used against those not used (Eq. 1-2, pp. 34)
Epsilon-greedy with epsilon 0.2.

### 7. Load dependence is handled by three MDPs per application (low, medium, high traffic in the k-hop neighbourhood) instead of one, because the same action earns different rewards under different load (Sec. IV-A, Alg. 2, pp. 35)

### 8. Capacity is handled by a greedy heuristic outside the MDP: deploy prefetched services in workflow order until the server is full (Sec. IV-B, pp. 35-36)

### 9. ⭐ Evaluation is a simulation: San Francisco taxi trajectories as users, real tower locations as servers, random coverage, service invocations assigned randomly to slots; container times from DeathStarBench Media Microservices and Docker Hub images (Sec. V-A, p. 36)
The authors say no public MEC workload traces suitable for the problem exist.

### 10. ⭐ With ample server resources the RL policy lowers latency by about 44% against MCAPP-IM; with scarce resources the gain falls to about 11% on average (Fig. 7, pp. 38-39)
Abstract and introduction state about 28% average latency improvement over the reactive approach (p. 29).

### 11. Under high load the agent learns to prefetch less, because prefetched containers block resources: "lean towards more reactive deployments" (Fig. 5, p. 38)

### 12. Stated limits: linear workflows only, tabular Dyna-Q whose memory grows with the distance resolution k, some actions unexplored when the data does not cover the action space (Sec. V-B, VII; pp. 39, 41)

## Figures and tables
Fig. 1-2 example and workflow; Table I-III timelines (pp. 30-31); Fig. 3 MDP (p. 33); Alg. 1 Dyna-Q, Alg. 2 prefetching and migration (pp. 34-35); Fig. 5-8 results (pp. 37-39).

## What this source does not address
One user's mobility drives everything; aggregate request load and bursts are not forecast. No DAG branching (linear only), no queueing at servers, no admission control, no SLO or percentile metrics (average user latency), no oracle bound, no look-ahead simulator, and no comparison against DFPS-type schedulers. The baselines are on-demand placement and MCAPP-IM, neither of which prefetches.

## Focus: prior art for look-ahead, simulation-judged and regime-aware container re-planning of serverless workflows at the edge (D1-D3) — 2026-10-20

**Carries Kernthesen 1, 3, 4, 6, 7, 10, 11, 12.**

### What this focus needs beyond the Kernthesen
1. Prefetching along a workflow is established for linear microservice chains; the new part for us is acting on aggregate downstream load and judging the change by a simulator clone.
2. Its finding that proactive gain shrinks from 44% to 11% under load (Kernthese 10) is consistent with our result that look-ahead pays at low and moderate load but a capacity-limited system leaves little room; it also treats load as a regime (three MDPs), the nearest thing to regime awareness in these six sources besides [[lei-2026-multi-agent]].
3. Reward is a hand-weighted resource cost of used versus unused prefetched services; tabular Dyna-Q with 28% reported against a purely reactive scheme is the learned-policy end of the comparison set.

### Direct quotes
> "To the best of our knowledge, this is the first work that exploits the microservice dependency task graph structure to prefetch and pre-provision microservices to better meet QoS requirements in MEC." (p. 29, Sec. I)

> "in a high traffic environment, the MEC servers are resource constrained and hence lean towards more reactive deployments" (p. 38, Sec. V-B)

### Examples & illustrations
- Tables I-III: the same two-user timeline under on-demand (75 ms total initialisation), prefetching, and prefetching plus migration (25 ms, 66% less) (pp. 30-31).

### Boundary of this focus
Pre-empts nothing about aggregate-load forecasting or simulation-judged layout changes. It is prior art for "prefetch along the workflow" and for the observation that proactive gain depends on load.

## Mentioned entities
- Systems: [[deathstar-benchmark]]
- Concepts: [[predictive-pre-deployment]], [[cold-start]], [[migration-minimizing-placement]]

## Connections
- Same stage-wise idea as [[daw-2020-xanadu]] and [[mahgoub-2022-orion]]; reactive counterpart in [[lei-2026-multi-agent]]; aggregate forecasting in [[nguyen-2025-taming]].
