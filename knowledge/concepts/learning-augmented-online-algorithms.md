---
title: "Learning-augmented online algorithms (consistency and robustness)"
type: concept
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
tags: [online-algorithms, predictions, worst-case-guarantee]
---

# Learning-augmented online algorithms (consistency and robustness)

## Definition
Online algorithms that receive a machine-learned prediction and are judged by two competitive-ratio measures: **consistency** (ratio when the prediction is perfectly accurate) and **robustness** (worst-case ratio over all inputs and predictions). An algorithm is beta-consistent if ALG/OPT <= beta whenever input equals prediction, and gamma-robust if ALG/OPT <= gamma for every input/prediction pair (Wei and Zhang 2020, Sec. 1.3, p. 5; also p. 3). The line of work was initiated by Lykouris and Vassilvitskii (ICML 2018) and Kumar, Purohit and Svitkina (NeurIPS 2018) (p. 1-2).

## Where it comes from
Replaces pure worst-case analysis (too pessimistic) and pure ML prediction (no worst-case bound) (p. 2). [[wei-2020-robustness-consistency]] gives the first non-trivial lower bounds, showing the consistency-robustness trade-off is intrinsic (pp. 3, 10-11).

## How it is applied
Ski rental (deterministic and randomised, tight) and non-clairvoyant scheduling (tight at endpoints; tight everywhere for two jobs); see [[ski-rental]] and the Kernthesen of [[wei-2020-robustness-consistency]]. A trust parameter lambda in (0,1) selects the point on the trade-off curve.

## Criticism
Wei and Zhang note only two problems are settled; other problems (matching, generalised ski rental) are left open (p. 11). Their bounds are worst-case over predictions and use absolute error eta; they say nothing about learning or estimating the prediction, or about its error distribution.

## Not to be confused with
Online learning with regret bounds, and stochastic online models: Wei and Zhang make no distributional assumption on inputs (p. 5). Also distinct from drift-plus-penalty control without forecasts ([[lyapunov-drift-plus-penalty]]) and from forecast-driven control without a guarantee ([[model-predictive-control]]).

## Relevance to this project
The theoretical home of the H1b layer (forecast + worst-case guarantee for D1). No FaaS-scheduling paper reviewed so far carries such a guarantee ([[model-predictive-control]], [[lyapunov-drift-plus-penalty]] pages).

## Sources
- [[wei-2020-robustness-consistency]]
- [[purohit-2018-online-algorithms-predictions]]
