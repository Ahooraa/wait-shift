---
title: "Mean user satisfaction (MUS)"
type: concept
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
tags: [metric, deadline, qos]
sources:
  - "[[lei-2026-adaptive]]"
---

# Mean user satisfaction (MUS)

## Definition
Per-workflow satisfaction is 1 up to the soft deadline and decays linearly to 0 at a maximum permissible completion time set by a tolerance factor; MUS is the mean over all workflows (Eq. 1 and 4, p. 4 of [[lei-2026-adaptive]]).

## Criticism
It is a mean utility: it hides how many workflows miss deadlines and how badly, which the authors patch with deadline satisfaction ratio and mean tardiness (p. 10). It is not a tail or goodput metric.

## Not to be confused with
SLO-goodput or P99 makespan, the metrics of the faas-edge-adaptation plan.

## Relevance to this project
Contrast metric for D2: MUS rewards graceful degradation, whereas SLO-goodput under overload rewards shedding.

## Sources
- [[lei-2026-adaptive]]
