---
title: "EGAT two-stage scheduler (Liao et al. 2025)"
type: entity
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
tags: [algorithm, serverless-workflows, edge, gnn, reinforcement-learning]
sources:
  - "[[liao-2025-adaptive]]"
---

# EGAT two-stage scheduler

## What it is
Scheduler proposed in [[liao-2025-adaptive]] for serverless workflows on dynamic edge servers. An Edge-enhanced Graph Attention Network encodes the workflow DAGs and the resource graph; stage 1 picks a ready function, stage 2 picks a server for it; both are trained end-to-end with PPO (pp. 119-121). See [[event-driven-two-stage-scheduling]].

## The evidence
Simulation with 4-8 nodes against RAND, HEFT, DRL-Flat and DRL-WGNN: about 14% lower mean makespan on average and up to 20% against DRL-WGNN (p. 122), plus lower load imbalance and smaller degradation under node churn (Figs. 5-6, p. 122).

## Contested
Small simulated testbed, arrival process unspecified, no confidence intervals, no real platform, no comparison with schedulers beyond HEFT and the authors' own DRL variants (pp. 121-122).

## Relevance to this project
Flagged at gate G0 as event-driven, two-stage and workflow-aware at the dynamic edge. It decides what to schedule next, not when to reconfigure, and has no forecasts, admission control or switching cost (see the G0 verdict in the source page).

## Sources
- [[liao-2025-adaptive]]
