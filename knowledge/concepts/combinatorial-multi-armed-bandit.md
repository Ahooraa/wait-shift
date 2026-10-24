---
title: "Combinatorial multi-armed bandit (CUCB)"
type: concept
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
sources:
  - "[[guo-2026-popularity-aware-caching]]"
tags: [online-learning, regret, bandit]
---

# Combinatorial multi-armed bandit (CUCB)

## Definition
Each round a super-arm (strategy) built from base arms is played; base-arm outcomes are observed; the learner keeps a UCB index per base arm and calls an offline (approximation) oracle to select the strategy. Guo et al. cite Chen et al. [50], [51] (p. 6285 of [[guo-2026-popularity-aware-caching]]).

## How it is applied
Arms are functions' invocation probabilities; index mu_hat + sqrt(3 ln t / (2 N_a)); the oracle is AAST (Algorithm 2, p. 6286). Regret is measured against a fraction of the optimum because the oracle is an approximation (Theorem 3, p. 6286).

## Criticism
Standard guarantees need stationary (i.i.d.) arm distributions; the paper has no change-point handling.

## Not to be confused with
[[linucb-contextual-bandit]] (contextual, linear payoffs) and [[learning-augmented-online-algorithms]] (worst-case robustness against bad predictions).

## Relevance to this project
Shows what stationary-regret "online guarantees" look like for placement, in contrast with competitive-ratio guarantees under shifts.

## Sources
- [[guo-2026-popularity-aware-caching]]
