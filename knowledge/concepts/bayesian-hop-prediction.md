---
title: "Bayesian hop prediction (Dirichlet-multinomial)"
type: concept
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
tags: [prediction, dynamic-dag, bayesian]
sources:
  - "[[liu-2025-sdser]]"
---

# Bayesian hop prediction

## Definition
For each function f_k the next function is a categorical draw with probabilities Theta_k. A Dirichlet prior (all parameters 1 at the start) is updated after each slot by adding the observed hop counts, and the predicted successor is sampled from Multi(Theta) (Eq. 19-23, p. 894 of [[liu-2025-sdser]]). The entry function f0 is treated as a Poisson stream.

## How it is applied
Used by [[sdser]] to generate "expected requests" every slot as input to [[predictive-pre-deployment]].

## Criticism
Counts only accumulate, so there is no forgetting and no change detection; stationary hop probabilities are implicit. Sampling instead of taking the mode is argued to damp anomalies (p. 894) but adds variance to the predicted request set. No calibration or error metric for the prediction is reported.

## Not to be confused with
Path-level prediction (Xanadu most-likely path, Kraken arrival estimation), which the paper criticises (p. 898).

## Relevance to this project
The simplest forecast layer for a dynamic-DAG baseline; a forecast with an error guarantee would have to add what this lacks. Related: [[learning-augmented-online-algorithms]].

## Sources
- [[liu-2025-sdser]]
