---
title: "EBRO (Expectation-based Rounding Optimization)"
type: entity
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
sources:
  - "[[ma-2025-online-deployment]]"
tags: [method, offline, randomized-rounding, prewarming, dynamic-dag]
---

# EBRO

## What one sees
Offline algorithm of Ma et al. 2025 that decides which function containers to pre-warm and on which edge server, for one request at a time. It relaxes the 0/1 placement variables of problem (6) to [0,1], solves the relaxed program with Gurobi, then rounds each variable to 1 with its fractional value as probability, repeating until the result is feasible (Alg. 1, p. 5). Pre-warming is then set wherever a function is placed.

## The evidence
- Objective: expected path-weighted execution time, with pre-warm flags fixed beforehand from a probability threshold (Eq. 2, 7; pp. 4-5). See [[function-calling-probability-prewarming]].
- Guarantee: Theorem 1 upper bound "with a high likelihood" (p. 6), via Lemmas 1-5 and a Chernoff bound (pp. 5, 9). See [[randomized-rounding]].
- Reported: up to 78.4% lower request time and 88.5% lower cold-start time than HEFT, DPE, Gendoc (p. 8).

## Contested
The bound is a ratio to the optimum of the same model, not a bound under forecast error. Lemma 3 gives resource feasibility only "in expectation" (p. 5), yet Alg. 1 loops until feasible; the paper does not say how many rounds are typical.

## Relevance to this project
A prediction-driven offline pre-deployment baseline for conditional (dynamic) DAGs. See [[ma-2025-online-deployment]] and [[opts]].

## Sources
- [[ma-2025-online-deployment]]
