---
title: "Periodic replacement and rescheduling (DFPS auto-scaling)"
type: concept
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
tags: [auto-scaling, reconfiguration, simulated-annealing, dfps]
sources:
  - "[[zolfaghari-2025-dynamic-function-placement]]"
---

# Periodic replacement and rescheduling (DFPS auto-scaling)

## Definition
The third DFPS component: at fixed intervals a simulated-annealing search swaps function instances between types on edge nodes and relocates the scheduled requests accordingly, to lower the makespan of the requests already scheduled ([[zolfaghari-2025-dynamic-function-placement]], Sec. 4.3, pp. 7-9). Interval: 4 s, chosen by a sweep of 1-9 s on the same workloads (pp. 9-10).

## How it is applied
Neighbour move: pick a random node, remove an instance of the function with the fewest requests in the past interval, add one of a random function, then reschedule requests (Alg. 1, p. 8). The score is the sum of relocation gains, i.e. differences in estimated execution time of requests (Eq. 8, p. 8). Arrival rates feeding the queue model are updated "every few seconds" (p. 7).

## Criticism
Reading for weakness D1 (clock-driven, cost-blind, forecast-free): the trigger is the clock; the search runs every interval with no test of whether demand changed; the score has no cold-start or migration term in the printed AET (transfer plus service time, p. 8); inputs are past-interval counts, not forecasts. The stated reason for periodicity is to limit cold starts (p. 7), which is an argument, not a measured result. See the focus block of the source page for page cites.

## Not to be confused with
Initial placement (NSGA-II, once offline) and per-request scheduling (graph matching); and with per-request replacement in Heu or RL, which the paper criticises (p. 10).

## Relevance to this project
The D1 mechanism that an event-triggered, cost-aware controller would replace. The adaptation plan tunes the period from {1,...,64} s as an oracle baseline.

## Sources
- [[zolfaghari-2025-dynamic-function-placement]]
- [[dfps]]
