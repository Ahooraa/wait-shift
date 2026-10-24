---
title: "Two-level data merging (DAG vertical/horizontal merging)"
type: concept
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
sources:
  - "[[tian-2024-sfsm]]"
tags: [dag, graph-optimisation, data-locality]
---

# Two-level data merging

## Definition
A DAG pre-processing step in [[tian-2024-sfsm]] (Alg. 2, pp. 1019-1020): vertical merging fuses single-successor/single-predecessor chains; horizontal merging groups same-level functions up to a node parallel degree, ordered by resource demand, to reduce cross-node transfers and balance load.

## How it is applied
Run on every arriving request before placement ([[sfsm]], Alg. 1, p. 1019). The ablation without it is worse (p. 1022).

## Criticism
Merged functions lose independent scheduling and scaling; the paper does not discuss cold starts or per-function concurrency for merged nodes (inferred).

## Not to be confused with
Function fusion for cold-start avoidance in serverless platforms; here the motivation is data transfer only.

## Relevance to this project
Peripheral: orthogonal to the D1/D2/D3 contributions.

## Sources
- [[tian-2024-sfsm]]
