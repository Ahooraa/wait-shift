---
title: "Multi-stage LP routing"
type: concept
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
tags: [routing, dispatch, linear-programming, serverless, workflow]
sources:
  - "[[jia-2025-faaspr]]"
---

# Multi-stage LP routing

## Definition
[[faaspr]]'s routing algorithm (Sect. V, pp. 2068-2070): given the placement matrix P and predicted per-branch invocation frequency O for the next scaling interval, choose frequencies o_k over feasible routing paths (function-to-server assignments) minimising average latency subject to coverage (Constraint 1), instance capacity alpha*P_ij/t_i with alpha = 0.9 (Constraint 2) and a latency cap L = l_x that zeroes slower paths (Constraint 3). The smallest feasible x is found by binary search over repeated LP solves; invocations then pick a path by weighted random draw.

## How it is applied
Per workflow, recomputed per scaling request, milliseconds with server groups of 8 (p. 2070); scheduling overhead is microseconds (p. 2075). Routing is open-loop: it uses no live queue state per request.

## Not to be confused with
Per-request dispatch on queue state (the D2/D3 notion); here it is a static probability table refreshed once per interval.

## Relevance to this project
This is the "routing" half of the placement-routing coupling relevant to D3; the alpha headroom is its only overload provision.

## Sources
- [[jia-2025-faaspr]]
