---
title: "Predictive container pre-deployment"
type: concept
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
tags: [cold-start, prediction, pre-warming]
sources:
  - "[[liu-2025-sdser]]"
---

# Predictive container pre-deployment

## Definition
Deploying containers ahead of requests based on a forecast of which function runs next. In [[sdser]] this is a once-per-slot decision: predict hops ([[bayesian-hop-prediction]]), solve a relaxed LP, round randomly, deploy (Alg. 1, p. 894 of [[liu-2025-sdser]]).

## How it is applied
A pre-deployed container removes the cold-start term (1-y)*tau_cold from execution time (Eq. 2, p. 892). Deployment costs g_k per newly created container; containers carried over from the previous slot are free (Eq. 8-9, p. 893). Misses are repaired by reusing residual containers or paying a cold start (Mosa, pp. 895-896).

## Criticism
Slot-triggered only; no uncertainty bound; no eviction or keep-alive model beyond slot-to-slot carry-over (compare [[keep-alive-time]]).

## Not to be confused with
Keep-alive policies ([[hybrid-histogram-keep-alive-policy]]) that retain containers after use rather than forecast future ones, and ski-rental style caching ([[ski-rental]]).

## Relevance to this project
Template for an "Sdser-style predictive controller" baseline; implementation needs are listed in the focus block of [[liu-2025-sdser]].

## Sources
- [[liu-2025-sdser]]
