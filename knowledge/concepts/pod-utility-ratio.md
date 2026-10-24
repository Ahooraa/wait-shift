---
title: "Pod utility ratio"
type: concept
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
tags: [serverless, cold-start, metric]
sources:
  - "[[joosen-2025-cold-starts]]"
---

# Pod utility ratio

## Definition
Ratio of a pod's useful lifetime (total lifetime minus the 1-minute keep-alive) to its cold start time; at 1 or below the pod lived no longer than it took to start ([[joosen-2025-cold-starts]], Sec. 4.5, p. 11).

## How it is applied
Region 2: 20% of pods below 1, median about 4; Go pods best (35% above 100), Node.js worst (about 40% below 1); timers lowest (p. 11). Pods with long cold starts tend to live longer (p. 13).

## Not to be confused with
Cold start time itself, or [[keep-alive-time]] (which is subtracted).

## Relevance to this project
A candidate amortised cold-start cost metric for the simulator ([[cold-start]]).

## Sources
- [[joosen-2025-cold-starts]]
