---
title: "Cold start time and inter-arrival model (simulator inputs)"
type: concept
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
tags: [serverless, cold-start, simulation, distribution]
sources:
  - "[[joosen-2025-cold-starts]]"
---

# Cold start time and inter-arrival model

## Definition
Pooled fits from the Huawei trace ([[joosen-2025-cold-starts]], Fig. 10, p. 8): cold start time LogNormal (mean 3.24, sd 7.10), cold start inter-arrival Weibull (mean 1.25, sd 3.66), both over all five regions.

## How it is applied
Implied parameters (our calculation, assuming mean and sd are moments): LogNormal mu 0.296, sigma 1.326, median 1.35 s; Weibull shape about 0.42, scale about 0.42 s. Regional medians 0.1-2 s; Custom and HTTP runtimes median above 10 s; large pools 1:1 to 5:1 longer median than small pools (pp. 8, 10-11). Components: pod allocation, deploy code, deploy dependencies, scheduling (p. 8).

## Criticism
A pooled fit hides the regional, runtime and pool-size heterogeneity that the paper itself shows dominates the distribution.

## Relevance to this project
Default draws for cold start delay in the simulator, with per-runtime or per-pool overrides ([[cold-start]], [[huawei-public-trace-2025]]).

## Sources
- [[joosen-2025-cold-starts]]
