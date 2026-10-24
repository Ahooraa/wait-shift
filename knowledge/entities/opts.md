---
title: "OPTS (Online Prewarming and Tasks Scheduling)"
type: entity
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
sources:
  - "[[ma-2025-online-deployment]]"
tags: [method, online, scheduling, prewarming, dynamic-dag]
---

# OPTS

## What one sees
Online algorithm of Ma et al. 2025 for several concurrent requests. Per fixed time slice it first pre-warms containers from the EBRO result ([[ebro]]); inside the slice it keeps one topologically ordered list per request, ranks the heads of all lists by function weight (probability-weighted execution time, p. 6), and assigns the top function to the server with the earliest start time (Alg. 2, Eq. 10-14; pp. 6-7). If the earliest start needs a new pre-warmed container, the flag y_{v,i} is set and the server's remaining memory is reduced (Eq. 9, p. 6); the counter q_{v,i} resets at slice end.

## The evidence
- Guarantee: Theorem 2, ratio l/l' + 8/5 to the optimal schedule, only for equal server memory and equal link rates (p. 7).
- Reported: 25.2% lower makespan than FCFS, 21.6% than Fixed; 80.1% and 76.9% lower total cold-start time (pp. 8-9).

## Contested
Slice length and how l' is measured are not given; the ratio does not contain a forecast-error term. No admission or rejection step exists.

## Relevance to this project
Closest in this paper to a "when to (re)deploy" rule: slice-start re-warming plus on-demand warming at dispatch. See [[ma-2025-online-deployment]].

## Sources
- [[ma-2025-online-deployment]]
