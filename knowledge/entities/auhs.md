---
title: "AUHS (adaptive user-satisfaction-driven heuristic scheduler)"
type: entity
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
tags: [algorithm, serverless-workflows, cloud-edge]
sources:
  - "[[lei-2026-adaptive]]"
---

# AUHS

## What it is
Online heuristic for serverless workflow scheduling in cloud-edge setups, proposed by Lei et al. (2026) in [[lei-2026-adaptive]]. Two stages: batch-level task ordering (weighted sub-deadline decomposition plus earliest-sub-deadline-first, p. 11) and function-level plan selection among seven node x container candidates by minimum non-execution latency (pp. 5-7).

## The evidence
Evaluated in EdgeCloudSim on 1280 random instances against SAUHS, RANDOM, HEFT, SKIPPY, IGA, PPO; MUS 0.91 vs 0.74-0.87 (Table 4, p. 11).

## Contested
No independent replication; simulation only (p. 13). SKIPPY is ahead on MUS at lambda = 20/s (p. 12).

## Relevance to this project
Nearest 2026 competitor for D2/D3 of the faas-edge-adaptation plan; it has no forecasting, admission control or reconfiguration trigger (see the G0 verdict in the source page).

## Sources
- [[lei-2026-adaptive]]
