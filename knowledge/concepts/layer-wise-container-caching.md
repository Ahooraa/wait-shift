---
title: "Layer-wise container caching"
type: concept
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
sources:
  - "[[guo-2026-popularity-aware-caching]]"
tags: [cold-start, caching, serverless-edge]
---

# Layer-wise container caching

## Definition
Containers are viewed as three stacked layers (bare, language/runtime, user code) cached bottom-up, so a start loads only the uncached layers (Sect. II-B and III-A, pp. 6279-6280 of [[guo-2026-popularity-aware-caching]]; constraint y_u <= y_l <= y_b, Eq. 1). The idea is attributed there to RainbowCake [26].

## Where it comes from
Replaces full-container pre-warming (large memory) and zygote sharing (only the language layer), p. 6278.

## How it is applied
In the paper, layers are chosen per edge server under a memory budget M_n, weighted by function popularity ([[olcfs]]).

## Criticism
Existing layer-wise schemes are reactive and popularity-blind, causing thrashing (p. 6278).

## Not to be confused with
Keep-alive ([[keep-alive-time]]), which keeps a whole instance warm for a time window rather than choosing layers under a memory budget.

## Relevance to this project
Alternative to the pure keep-alive view of [[cold-start]] mitigation; DFPS assumes all slots stay warm.

## Sources
- [[guo-2026-popularity-aware-caching]]
