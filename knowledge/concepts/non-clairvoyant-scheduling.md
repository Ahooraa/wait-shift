---
title: "Non-clairvoyant scheduling with predictions"
type: concept
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
tags: [online-algorithms, scheduling, predictions]
sources:
  - "[[purohit-2018-online-algorithms-predictions]]"
  - "[[wei-2020-robustness-consistency]]"
---

# Non-clairvoyant scheduling with predictions

## Definition
n jobs are present at time 0 on one machine; preemption is free; true sizes x_j are unknown until a job completes; the objective is the sum of completion times (Purohit, Svitkina and Kumar 2018, Sect. 3, pp. 6-7). With predictions y_j the error is eta = sum_j |x_j - y_j|, no job has zero length and the shortest job is normalised to at least 1 (p. 6). Round-Robin (RR) is 2-competitive and optimal without predictions (Motwani et al., cited p. 2); Wei and Zhang give the exact 2 - 2/(n+1) (p. 5).

## Where it comes from
Classical non-clairvoyant scheduling, extended with predictions as a [[consistency-robustness-tradeoff]] problem. Shortest Predicted Job First (SPJF) is optimal for perfect predictions but unbounded for bad ones; its ratio is at most 1 + 2 eta/n (Lemma 3.2, p. 7).

## How it is applied
Preferential Round-Robin (PRR) runs SPJF at rate lambda and RR at rate 1-lambda (Lemma 3.1, p. 7, for monotonic algorithms). Theorem 3.3: ratio at most min{(1/lambda)(1 + 2 eta/n), 2/(1-lambda)}, hence 2/(1-lambda)-robust and 1/lambda-consistent; lambda > 0.5 beats RR when predictions are good (pp. 7-8). Theorem 3.4: ratio at most (1+lambda)/(2 lambda) when eta = 0 (p. 8). Wei and Zhang show the general bound is tight only at the endpoints (Thm 1.3, p. 4) and give a tight two-job trade-off with robustness at most 2 (Thm 1.4, p. 4).

## Criticism
Single machine, no release dates, free preemption, no precedence constraints (pp. 6, 9). The introduction calls the scheduling algorithm randomised (p. 2) although PRR as described in Sect. 3 is a rate-sharing combination of two deterministic rules; flagged.

## Not to be confused with
[[ski-rental]], the single-decision rent-or-buy problem from the same paper; and DAG or workflow scheduling, whose precedence constraints are not covered here.

## Relevance to this project
Lemma 3.1 is a reusable device for blending a forecast-driven and a forecast-free controller, but no bound transfers to workflow dispatch or non-preemptive containers.

## Sources
- [[purohit-2018-online-algorithms-predictions]]
- [[wei-2020-robustness-consistency]]
