---
title: "Event-driven two-stage scheduling (task selection then placement)"
type: concept
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
tags: [scheduling, workflows, terminology]
sources:
  - "[[liao-2025-adaptive]]"
---

# Event-driven two-stage scheduling

## Definition
In [[liao-2025-adaptive]]: a decision is taken whenever functions become ready (the "event"), in two stages: first select a ready function from all active workflows, then select a server for it (Sect. III, pp. 119-120). Joint action (f*, v*) with factorised policy (Eq. 21, p. 120).

## Where it comes from
Positioned against myopic local-priority task selection and static resource features in earlier learning-based work (pp. 117-118).

## How it is applied
EGAT encoders plus PPO over simulated workflows with node churn (pp. 120-122); see [[egat-scheduler]].

## Criticism
"Event-driven" here means a per-task decision on arrival or readiness, not a trigger policy that decides when to reconfigure; the stages decide what next, not when to re-plan.

## Not to be confused with
Event- or cost-triggered reconfiguration (deciding when to switch placement or capacity under a switching cost): a different decision, which this paper does not make.

## Relevance to this project
Terminology trap at gate G0: the label "event-driven, two-stage" sounds like D1/D3 but is neither (see the G0 verdict in [[liao-2025-adaptive]]).

## Sources
- [[liao-2025-adaptive]]
