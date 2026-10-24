---
title: "Lei, Zhou, Daniëlse & Zhao 2026 — Multi-Agent Based Time Critical FaaS Scheduling in Edge-Cloud Continuum"
type: source
created: 2026-10-20
updated: 2026-10-20
status: review
author: llm
bibkey: lei-2026-multi-agent
depth: standard
tags: [serverless, edge-cloud, architecture-switching, tail-latency, openfaas, regime-switching, g0-novelty, related-work]
relations:
  - target: dfps
    type: mentions
    confidence: extracted
    because: "Cites Zolfaghari et al. 2025 (DFPS) as ref. [11] among systems that optimise function placement inside a fixed control architecture (Sec. I, p. 499; refs p. 505)."
  - target: speculative-execution
    type: mentions
    confidence: extracted
    because: "Related work on tail-latency mitigation via speculative execution or redundancy (Sec. II, p. 499)."
  - target: cold-start
    type: mentions
    confidence: extracted
    because: "Concedes tail-ratio signals are noisy under cold starts or low traffic (Sec. VI, p. 505)."
---

# Multi-Agent Based Time Critical FaaS Scheduling in Edge-Cloud Continuum

## Bibliographic Details
Lei, Yitao; Zhou, Mengbing; Daniëlse, Paul; Zhao, Zhiming. 2026. *Multi-Agent Based Time Critical FaaS Scheduling in Edge-Cloud Continuum*. 2026 IEEE International Parallel and Distributed Processing Symposium Workshops (IPDPSW), pp. 498-505. DOI 10.1109/IPDPSW71298.2026.00085.

> Page note: the page refs are the printed IEEE page numbers 498-505.

## Section map

| Covered | Section | pp. |
|---|---|---|
| ✓ F1 | I Introduction (three architectures, gap, contributions) | 498-499 |
| ✓ F1 | II Related work | 499 |
| ✓ F1 | III-A/B Multi-agent architecture, modes and request flow | 499-501 |
| ✓ F1 | III-C Tail-aware architecture evolution (Eq. 1-5, Alg. 1) | 501-502 |
| ✓ F1 | IV Implementation on OpenFaaS | 502-503 |
| ✓ F1 | V Evaluation (testbed, overhead, completion time, tail ratio) | 503-505 |
| ✓ F1 | VI Conclusion | 505 |

## Kernthesen

### 1. ⭐ No scheduling architecture (centralized, federated, decentralized) is universally best, and static choices cannot follow changing load and network conditions (p. 498)

### 2. ⭐ The scheduling architecture itself is treated as a runtime control variable: all three modes live in one agent codebase and are switched on the fly (Sec. III-A/B, pp. 499-501)
New requests are bound to the new mode; in-flight requests finish under the old one. Configuration is reloaded without redeployment.

### 3. ⭐ The switching signal is the tail ratio r = P95/P50 of execution times over a sliding window, per function and per architecture (Eq. 1, p. 501)
P95 is chosen over P99 for stability under finite windows; the median normalises.

### 4. ⭐ Soft and hard thresholds map the ratio piecewise-linearly to a preference weight for the next more coordinated architecture (Eq. 2, p. 501)
Only the upward transitions decentralized to federated and federated to centralized are defined; the weights give traffic fractions, so several architectures can run at once.

### 5. Traffic fractions are exponentially smoothed with a factor that depends on the change in query rate through a scaled sigmoid (Eq. 3-4, pp. 501-502)
alpha = 0.1 + 0.8 sigma(gamma (dQPS - delta)), gamma = 0.5, delta = 5.

### 6. Upgrades also require the query rate to exceed a threshold (QPS_fed, QPS_cen) (Alg. 1, p. 502)

### 7. The thresholds are fitted by grid search on testbed data to minimise the gap to the best static architecture (Eq. 5, p. 502)
Fitted on the same kind of data later evaluated; no held-out workload is reported.

### 8. ⭐ The authors state explicitly that the mechanism works above placement: it "does not merely adjust placements or replica counts within a fixed control structure" (p. 502)

### 9. Test bed: six VMs (two cloud, four edge), OpenFaaS with faas-netes and faasd, emulated RTTs; a matrix-multiplication function, 1000 requests per run, concurrency varied with Locust (Sec. V-A, p. 503)
An image-resize function was run and omitted as "qualitatively similar".

### 10. ⭐ The dynamic architecture is close to the best static one in total completion time, often second best at high load; centralized is worst (Fig. 5, p. 504)
Average response stays below 1 s at the highest concurrency, centralized exceeds 1.1 s at 30 users (Fig. 6).

### 11. The dynamic mode keeps tail ratios low and stable, decentralized shows the strongest tail amplification (Fig. 7-8, pp. 504-505)
Centralized has low ratio only because its base latency is already high.

### 12. ⭐ Stated limits: tail-ratio signals can be noisy under cold starts or low traffic; evaluation is VM-based only (Sec. VI, p. 505)
Future work: cost, energy and SLOs as extra objectives.

## Figures and tables
Fig. 1 modular agent architecture; Fig. 2 request routing; Alg. 1 tail-aware update (p. 502); Fig. 3 topology; Fig. 4 CPU and memory; Fig. 5-8 completion time, response time, boxplots, tail ratio (pp. 503-505).

## What this source does not address
No workflows or DAGs (one function); no container counts, placement or data-locality decisions; no prediction or look-ahead of load (the trigger reads past latency only); no simulation, oracle or upper bound on what switching could gain; no admission control; no comparison to a placement-based baseline such as DFPS or RL, and no statistical test across seeds (repeat counts are omitted, p. 503).

## Focus: prior art for look-ahead, simulation-judged and regime-aware container re-planning of serverless workflows at the edge (D1-D3) — 2026-10-20

**Carries Kernthesen 1, 2, 3, 4, 7, 8, 12.**

### What this focus needs beyond the Kernthesen
1. It is the only source read that switches between regimes at run time, but the regime is the control architecture, not the container layout.
2. The trigger is purely reactive and reads the past window; our result that reactive layout switching loses to a look-ahead judged by a simulator clone is the contrast.
3. Thresholds are fitted to the evaluation testbed; there is no sign of robustness checks under changed workloads.

### Direct quotes
> "it does not merely adjust placements or replica counts within a fixed control structure, but actively shifts the system between decentralized, federated, and centralized modes in response to long-tail behavior" (p. 502, Sec. III-C)

> "no prior work integrates multi-agent control with QoS feedback to enable architecture-level adaptation" (p. 499, Sec. II, the authors' novelty claim)

### Boundary of this focus
Not pre-empting: it shows regime switching on a tail signal is publishable at edge-cloud scale, but with single functions and no capacity re-planning.

## Mentioned entities
- Systems: [[dfps]] (cited only), OpenFaaS
- Concepts: [[speculative-execution]], [[cold-start]]

## Connections
- Reactive regime switch; contrast with the hybrid reactive/forecast replica rule in [[gupta-2025-hybrid-reactive-proactive]] and the forecast controller in [[nguyen-2025-taming]].
