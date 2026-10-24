---
title: "Function calling probability and probability-threshold pre-warming"
type: concept
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
tags: [dynamic-dag, prewarming, ewma, cold-start]
---

# Function calling probability and probability-threshold pre-warming

## Definition
In a dynamic DAG each request runs one path, so each function f_v has a calling probability rho_v (1 for ordinary functions, in (0,1) for dynamic ones; path probability p_k is the product of rho along the path), Ma et al. 2025, Sec. III-A (pp. 3-4). Pre-warming rule: estimate rho_v by min-max-normalised invocation counts per observation period, smooth with EWMA, and pre-warm f_v iff the estimate is at least a threshold P_pre (Eq. 1-2, p. 4).

## Where it comes from
Motivated by over-provisioning when every function is pre-warmed for a DAG where requests touch only a subset (abstract, p. 1). Kraken (Bhasi et al.) is cited as the prior system-level treatment of dynamic DAGs (p. 3).

## How it is applied
In [[ma-2025-online-deployment]] the flag is server-independent and fixed before the optimisation ([[ebro]]); P_pre was tuned to about 0.3 on SocialNetwork (p. 8).

## Criticism
Min-max normalisation makes the estimate relative to the most and least called function rather than an absolute rate; the independence of path probabilities as a product is assumed, not tested; the EWMA smoothing factor is not reported in the evaluation. No error bound links forecast quality to the guarantees (inferred from Theorems 1-2, pp. 6-7).

## Not to be confused with
Keep-alive time policies ([[keep-alive-time]], [[hybrid-histogram-keep-alive-policy]]), which decide how long a used container stays warm; this rule decides which containers to warm before any request.

## Relevance to this project
The only prediction input in the paper; a baseline for forecast-driven pre-deployment. See [[cold-start]].

## Sources
- [[ma-2025-online-deployment]]
