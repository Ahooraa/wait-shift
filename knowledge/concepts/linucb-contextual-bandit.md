---
title: "LinUCB contextual bandit (in scheduling)"
type: concept
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
sources:
  - "[[tian-2024-sfsm]]"
tags: [online-learning, bandit, regret]
---

# LinUCB contextual bandit (in scheduling)

## Definition
A linear-reward contextual bandit: each arm keeps a ridge-regression estimate theta = A^-1 b and is chosen by its estimate plus (here minus, for minimisation) an upper-confidence exploration term. Tian et al. use it per edge node, with Eq. 17-18 and Alg. 3 (pp. 1020-1021 of [[tian-2024-sfsm]]).

## How it is applied
Arms are edge nodes, context is a 7-feature DAG descriptor, reward is the per-slot Lyapunov objective P3 (p. 1021).

## Criticism
The regret bound (Theorem 1, Eq. 21, p. 1021) is relative to the best linear arm and needs bounded parameter and context norms and a Lipschitz link (pp. 1021-1022); it is silent on forecast error, distribution shift and constraint satisfaction. Its source lemmas are cited from Qin et al. and not reproved.

## Not to be confused with
Learning-augmented algorithms with consistency-robustness guarantees: bandit regret measures learning speed, not worst-case damage from a wrong forecast.

## Relevance to this project
Marks what "online learning with a guarantee" means in the FaaS-edge literature, to be distinguished from D1's forecast-with-guarantee layer.

## Sources
- [[tian-2024-sfsm]]
