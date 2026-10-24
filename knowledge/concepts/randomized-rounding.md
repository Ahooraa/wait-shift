---
title: "Randomized rounding (LP relaxation) with Chernoff analysis"
type: concept
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
tags: [approximation, integer-programming, offline]
---

# Randomized rounding

## Definition
Relax a 0/1 program to [0,1], solve it, then set each variable to 1 with probability equal to its fractional value; analyse deviation of the rounded objective and constraints with Chernoff bounds. As used in [[ma-2025-online-deployment]] (Sec. IV, pp. 5-6, appendix pp. 9-10).

## How it is applied
In [[ebro]]: repeat rounding until the integer vector is feasible (Alg. 1, p. 5). Results are "with a high likelihood" bounds (Lemmas 1, 4, 5; Theorem 1).

## Criticism
Constraints hold only in expectation (Lemma 3, p. 5), so feasibility rests on re-sampling; the bound contains the problem size n and number of servers l (Theorem 1, p. 6) and can be loose.

## Not to be confused with
Online competitive analysis ([[learning-augmented-online-algorithms]]); Theorem 1 is an offline approximation against the model's own optimum.

## Relevance to this project
Shows what "theoretical performance guarantee" means in this baseline: relative to the offline optimum of the model, with known probabilities.

## Sources
- [[ma-2025-online-deployment]]
