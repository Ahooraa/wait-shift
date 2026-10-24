---
title: "Deadline-feasible offloading with EDF super-master"
type: concept
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
tags: [serverless, deadline, offloading, edf, federated-edge, novelty-gate-g0]
sources:
  - "[[farahani-2026-clusterless]]"
---

# Deadline-feasible offloading

## Definition
When no local mode meets the deadline, [[clusterless]] sends the function to an elected super-master. It sorts pending requests by earliest workflow deadline (Alg. 3, p. 6), computes the completion time on each remote cluster (Eq. 8, p. 3), keeps only clusters with completion time within A_w + D_w and strictly better than the local time, and picks the minimum (Eqs. 9-10, p. 3). If no cluster qualifies, the function stays at its origin and the workflow is marked deadline-violated (p. 3; Alg. 3 lines 11-12, p. 6).

## Criticism
This is a feasibility filter and an ordering, not admission control: nothing is rejected or shed, so an infeasible workflow still consumes capacity. The objective is the deadline satisfaction rate, not goodput.

## Relevance to this project
The closest ClusterLess comes to D2. Compare [[bi-level-scheduling]] and [[event-driven-two-stage-scheduling]].

## Sources
[[farahani-2026-clusterless]]
