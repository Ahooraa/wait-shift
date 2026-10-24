---
title: "Alibaba Cluster Trace v2018"
type: entity
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
tags: [dataset, trace, workflows]
sources:
  - "[[lei-2026-adaptive]]"
  - "[[liao-2025-adaptive]]"
---

# Alibaba Cluster Trace v2018

## What it is
Open production trace of 4034 machines over eight days (Lei et al., p. 9, refs. [35,36]).

## The evidence
Used only to reconstruct six workflow DAG topologies; arrivals are synthetic Poisson, and image sizes and cold starts come from a separate Alibaba Function Compute trace (p. 9) in [[lei-2026-adaptive]].

## Contested
Batch-job DAGs are not serverless workflow traces; arrival burstiness is not taken from it.

## Relevance to this project
Shows the field commonly evaluates workflows with synthetic arrivals, which supports the plan's non-stationary-workload motivation.

## Sources
- [[lei-2026-adaptive]]

- Also cited by [[liao-2025-adaptive]] (ref. [7], Lu et al. 2017 trace analysis; version v2017 vs v2018 unclear, p. 121).
