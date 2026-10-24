---
title: "Execution-mode selection (warm / warm-scale / cold-scale / offload)"
type: concept
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
tags: [serverless, deadline, scheduling, cold-start, novelty-gate-g0]
sources:
  - "[[farahani-2026-clusterless]]"
---

# Execution-mode selection

## Definition
In [[clusterless]] each ready function is assigned one of four modes with serving times Q+T (warm execution), Q+WS+T (warm scaling), Q+CS+T (cold scaling), or offloading to the super-master (Eq. 4, p. 3). Algorithm 2 repeatedly takes the function with the largest completion time in the workflow (the bottleneck) and advances its mode in the fixed order warm, warm scaling, cold scaling, offload until the workflow meets its deadline (pp. 5-6).

## Not to be confused with
Pre-warming or keep-alive policies ([[cold-start]], [[function-calling-probability-prewarming]]). The mode is chosen at invocation time, reactively, with no forecast of future calls and no standing decision about how many warm instances to keep.

## Relevance to this project
The "how to execute" half of D2/D3 execution-mode selection. It is a greedy, deadline-driven, per-workflow loop with no cost model for reconfiguration.

## Sources
[[farahani-2026-clusterless]]
