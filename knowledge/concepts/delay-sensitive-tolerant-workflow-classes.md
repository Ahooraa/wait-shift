---
title: "Delay-sensitive vs delay-tolerant workflow classes"
type: concept
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
sources:
  - "[[sun-2026-hybrid]]"
tags: [priority, deadlines, workflows]
---

# Delay-sensitive vs delay-tolerant workflow classes

## Definition
In [[sun-2026-hybrid]] a workflow is classified by its temporal emergency factor lambda = P / D (sum of unqueued execution times over deadline, Eq. 1, p. 4); lambda above a threshold (0.5) means delay-sensitive and all its functions are high priority.

## How it is applied
Feeds two separate Lyapunov virtual queues ([[lyapunov-drift-plus-penalty]]) and the [[dqlws]] reward penalty. Ablation: removing the classification raises violations from 4.8% to 8.9% (p. 15).

## Criticism
P is a sum over all functions, not the critical path, so parallel DAG branches overstate urgency; queueing delay is excluded by design (p. 4). The class is static per workflow, with no admission decision.

## Not to be confused with
SLO-based admission or goodput maximisation: here every workflow is still admitted and scheduled.

## Relevance to this project
Partial overlap with D2's critical-path dispatch; the admission half and the critical-path priority remain distinct.

## Sources
- [[sun-2026-hybrid]]
