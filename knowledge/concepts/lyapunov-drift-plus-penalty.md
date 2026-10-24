---
title: "Lyapunov drift-plus-penalty"
type: concept
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
sources:
  - "[[sun-2026-hybrid]]"
tags: [control, queue-stability, online-optimization]
---

# Lyapunov drift-plus-penalty

## Definition
An online control technique: define virtual queues and a quadratic Lyapunov function L(Theta); each slot minimise drift plus V times the penalty, which converts a long-term constrained problem into per-slot problems without knowing future arrivals. Sun et al. use it with parameter V and obtain an average cost within B/V of the optimum (Theorem 2, p. 8 of [[sun-2026-hybrid]]).

## How it is applied
Here: two virtual queues (delay-sensitive, delay-tolerant functions), penalty = weighted delay and energy (Eq. 16, 32), combined with a DDQN ([[dqlws]]).

## Criticism
The bound holds for the time-average cost under i.i.d.-style arrival assumptions (Theorem 1, p. 7) and says nothing about worst-case deviation from forecasts or about per-workflow deadlines.

## Not to be confused with
Learning-augmented algorithms with robustness-consistency guarantees (forecast-trusting with worst-case fallback); Lyapunov control avoids prediction instead of hedging it.

## Relevance to this project
Shows that "online, no forecasts, with a guarantee" is already occupied by Lyapunov methods, so the project's H1b forecast-with-guarantee layer must be distinguished from it.

## Sources
- [[sun-2026-hybrid]]
