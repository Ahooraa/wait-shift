---
title: "Speculative execution (straggler mitigation)"
type: concept
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
tags: [scheduling, stragglers, replication]
---

# Speculative execution (straggler mitigation)

## Definition
Launching redundant copies of a task so that the first to finish determines completion, to cut the tail of the response-time distribution ([[exton-2024-raptor]], p. 4).

## Where it comes from
Data-processing frameworks (MapReduce, Spark, Dryad), where straggling is well known (pp. 2, 4).

## How it is applied
Cost-limiting strategies: delayed speculation, straggler prediction, budgeting, and preemption of losing copies (p. 4). Under Poisson arrivals and i.i.d. exponential service, preemption removes the capacity loss (p. 4, citing Gardner et al.). For two i.i.d. Exp(1) tasks, replication gives E[min] = 0.5 against E[max] = 1.5 for fork-join (p. 15).

## Criticism
Little benefit when execution times are near deterministic or correlated (pp. 14-15, Table 7).

## Not to be confused with
Predictive prewarming for cold starts ([[cold-start]]), which acts before dispatch rather than by duplicating work.

## Relevance to this project
Candidate baseline policy, and an analytic sanity check for a simulator with exponential service times.

## Sources
- [[exton-2024-raptor]]
