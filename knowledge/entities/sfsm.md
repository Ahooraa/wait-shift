---
title: "SFSM (Serverless Function Scheduling Method)"
type: entity
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
sources:
  - "[[tian-2024-sfsm]]"
tags: [method, serverless, edge, lyapunov, bandit]
---

# SFSM

## What one sees
Scheduler of Tian et al. 2024 for DAG-structured FaaS requests on edge nodes. Per request: merge the DAG ([[two-level-data-merging]]), place each function by a LinUCB-style bandit ([[linucb-contextual-bandit]]), then update a virtual cost queue ([[lyapunov-drift-plus-penalty]]) (Alg. 1, p. 1019 of [[tian-2024-sfsm]]).

## The evidence
Simulation on Alibaba v2018 DAGs: 37.2% lower average makespan and 91.7% lower cost than OnDoc, PASS, LSS and an ablation in the combined regime (p. 1023); loses to static LSS on makespan in the computation-intensive regime (p. 1022).

## Contested
The regret bound is imported from a contextual-bandit paper and its assumptions are not checked against the system (pp. 1021-1022). No theorem covers the cost constraint.

## Relevance to this project
Closest "no forecasts, with a guarantee" neighbour for D1 besides [[sun-2026-hybrid]]; has no reconfiguration trigger, admission control or instance coupling (G0 verdict in [[tian-2024-sfsm]]).

## Sources
- [[tian-2024-sfsm]]
