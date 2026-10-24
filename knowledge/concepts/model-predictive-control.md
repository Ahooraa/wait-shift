---
title: "Model predictive control (MPC)"
type: concept
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
tags: [control, receding-horizon]
---

# Model predictive control (MPC)

## Definition
Control scheme that, at each control step, solves a constrained optimisation over a finite horizon of H steps using a system model and a forecast, executes only the first step's action, and repeats (receding horizon). Cited by [[nguyen-2025-taming]] to Garcia, Prett and Morari (1989) and Kwon and Han (2005).

## How it is applied
In [[nguyen-2025-taming]]: forecast request rate over H steps, minimise a six-term cost (latency, queue wait, over-provisioning, cold starts, reclaim, smoothness) under queue/warm-pool dynamics, execute prewarm/reclaim/dispatch for the current step (Sec. III, pp. 2-3). Trigger: every fixed control interval. Horizon and weights are empirically tuned (p. 6).

## Criticism
No robustness guarantee to forecast error in that application beyond clipping; parameter tuning is workload-specific (Nguyen et al., p. 6).

## Not to be confused with
Reactive threshold autoscaling (no forecast, no horizon) and learning-augmented algorithms with consistency/robustness bounds.

## Relevance to this project
Closest prior art for forecast-driven proactive reconfiguration (D1) in G0; periodic-trigger and no-worst-case-guarantee gaps are the angles left open.

## Sources
- [[nguyen-2025-taming]]
