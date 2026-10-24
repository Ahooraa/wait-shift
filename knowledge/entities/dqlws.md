---
title: "DQLWS (Deep Q-Learning based Workflow Scheduling)"
type: entity
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
sources:
  - "[[sun-2026-hybrid]]"
tags: [method, drl, lyapunov, edge, serverless-workflows]
---

# DQLWS

## What one sees
A scheduler from Sun et al. 2026 that assigns ready workflow functions to edge nodes each time slot. Lyapunov drift-plus-penalty supplies the per-slot objective (delay, energy, queue backlog); a double DQN approximates the minimiser over a masked discrete action space. Trained offline in a simulator, inference online (p. 11 of [[sun-2026-hybrid]]).

## The evidence
- State: function queue, node resource occupation, bandwidth matrix; action: node per ready function; reward: deadline-violation penalty (pp. 9-10).
- Reported: 74.34 ms delay, 404.54 nJ, 4.8% violations versus five baselines in CloudSim (pp. 15-17).
- See [[lyapunov-drift-plus-penalty]] and [[delay-sensitive-tolerant-workflow-classes]].

## Contested
Evaluation is purely simulated with synthetic video workflows and 50 runs; no real traces, cold starts or non-stationary load. Claims of "near-optimal" rest on the V-bounded Lyapunov gap (p. 8), not on an oracle comparison.

## Relevance to this project
Closest published neighbour to D2 (priority under deadlines) and D3 (joint node choice and dispatch) found at the G0 gate, but it does not do admission control, forecasting or timing of reconfiguration. See the G0 verdict in [[sun-2026-hybrid]].

## Sources
- [[sun-2026-hybrid]]
