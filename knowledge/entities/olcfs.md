---
title: "OLCFS (Online Layer-wise Caching and Function Scheduling)"
type: entity
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
sources:
  - "[[guo-2026-popularity-aware-caching]]"
tags: [method, serverless-edge, caching, bandit]
---

# OLCFS

## What one sees
Online algorithm of Guo et al. 2026 that, each 10 s slot, learns function invocation probabilities with a UCB index and passes them to the single-slot approximation AAST (LP relaxation, randomised rounding) to choose which container layers to cache and where to place each function (Algorithms 1-2, pp. 6283, 6286 of [[guo-2026-popularity-aware-caching]]).

## The evidence
- Theorem 3 (p. 6286): regret O(|I| ln T) against a (1+eps)(1-1/e^|N|) fraction of the optimum, assuming stationary arms.
- Up to 2.92x lower ACT than FaasCache, RainbowCake, GSP in simulation (p. 6287).

## Contested
Guarantees assume i.i.d. stationary popularity and no queueing; shifts are not analysed or tested; the Theorem 2 factor is roughly 2 OP.

## Relevance to this project
Nearest published "online guarantee plus learned popularity" neighbour for the DFPS dynamic-replacement gap (D1, D3), but with a fixed slot trigger and no queues.

## Sources
- [[guo-2026-popularity-aware-caching]]
