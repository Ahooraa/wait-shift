---
title: "Migration-minimizing placement"
type: concept
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
tags: [placement, cold-start, switching-cost, serverless]
sources:
  - "[[jia-2025-faaspr]]"
---

# Migration-minimizing placement

## Definition
[[faaspr]]'s way to avoid "frequent instance migrations" (abstract, p. 2063): when a horizontal group is placed, each server gets a priority = expected saved cold-start time (reuse ratio of instances already there in the previous interval times the function's cold-start time) + expected saved transmission (edge weights to neighbours on that server, assuming random routing) + a small aggregation bonus (Alg. 2, p. 2068).

## How it is applied
It is a myopic bias inside a placement run that executes at every scaling request (p. 2068), not a decision about whether to re-place. There is no switching-cost threshold, hysteresis or bound on the number of migrations. Ablation ColdStart*: -51.42% average latency vs FaaSFlow (p. 2074).

## Not to be confused with
A reconfiguration trigger such as D1's cost-benefit rule: here the cost only reorders candidate servers.

## Relevance to this project
Closest thing to a switching-cost model in the source; relevant to the D1 verdict (partial overlap on cost-awareness only). Compare [[periodic-replacement-and-rescheduling]].

## Sources
- [[jia-2025-faaspr]]
