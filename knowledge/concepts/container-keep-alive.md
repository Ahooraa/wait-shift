---
title: "Container keep-alive as a rent-or-buy decision"
type: concept
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
tags: [serverless, keep-alive, online-algorithms, h1b]
sources:
  - "[[purohit-2018-online-algorithms-predictions]]"
  - "[[wei-2020-robustness-consistency]]"
---

# Container keep-alive as a rent-or-buy decision

## Definition
Project-level modelling concept, not a result of the cited papers. For one idle container let x be the idle gap until the next request and b the cold-start cost in units of idle cost. Keeping it warm for tau and then evicting costs x if x <= tau and tau + b if x > tau, so OPT = min{b, x}. This is the cost structure of [[ski-rental]], with "buy on day i" read as "evict after idle time i" (buy-on-day-i cost b + i - 1 is in Purohit et al. 2018, p. 4; the reading is the project's). The idle policy it models is [[keep-alive-time]]; the penalty is [[cold-start]].

## Where it comes from
Fixed keep-alive timeouts have no worst-case link to forecasts. The rent-or-buy view lets the learning-augmented results apply: forecast gap y >= b gives early eviction at about lambda*b, y < b keeps warm until about b/lambda (Alg. 2, p. 4), with the deterministic (1+lambda, 1+1/lambda) [[consistency-robustness-tradeoff]] and the tight randomised variant (Wei and Zhang Thms 1.1, 1.2, p. 3).

## How it is applied
Candidate H1b layer for single-gap decisions, with eta = |y - x| per gap. See [[learning-augmented-online-algorithms]].

## Criticism
Does not carry over without new work: cold-start cost is not constant (depends on function and node); idle-cost rate varies with memory; gaps interact through shared pools, so they are not independent instances (Sect. 2.4 extends only with omitted proofs, p. 6); reconfiguration with switching costs is not one-shot rent-or-buy; relative forecast error needs conversion to L1 eta; no rule for choosing lambda from data.

## Not to be confused with
Container caching with state ([[layer-wise-container-caching]]) and the hybrid-histogram heuristic ([[hybrid-histogram-keep-alive-policy]]), which carry no worst-case guarantee of this kind.

## Relevance to this project
Basis of H1b (forecasts with a worst-case guarantee for keep-alive); whether trace gaps fit the model is empirical and open.

## Sources
- [[purohit-2018-online-algorithms-predictions]]
- [[wei-2020-robustness-consistency]]
