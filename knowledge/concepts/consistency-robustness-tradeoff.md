---
title: "Consistency-robustness trade-off"
type: concept
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
tags: [online-algorithms, predictions, worst-case-guarantee]
sources:
  - "[[purohit-2018-online-algorithms-predictions]]"
  - "[[wei-2020-robustness-consistency]]"
---

# Consistency-robustness trade-off

## Definition
The competitive ratio of a prediction-using online algorithm is a function c(eta) of the prediction error eta. The algorithm is gamma-robust if c(eta) <= gamma for all eta, and beta-consistent if c(0) = beta (Purohit, Svitkina and Kumar 2018, Sect. 1, p. 2, where they write rho-robust and delta-consistent). The algorithm must not know the predictor quality and must assume nothing about error types (p. 2). Wei and Zhang 2020 define the same notions on ALG/OPT (Sect. 1.3, p. 5). The trade-off: a smaller consistency forces a larger robustness, and a trust parameter lambda moves the algorithm along one curve. General background: [[learning-augmented-online-algorithms]].

## Where it comes from
Introduced for caching by Lykouris and Vassilvitskii (2018); Purohit et al. apply it to [[ski-rental]] and [[non-clairvoyant-scheduling]] (p. 2). Purohit et al. show that trusting the prediction naively is 1-consistent but not robust (Lemma 2.1, p. 3).

## How it is applied
- Deterministic ski rental: (1+lambda)-consistent and (1+1/lambda)-robust (Purohit et al., Thm 2.2, pp. 3-4).
- Randomised ski rental: lambda/(1-e^{-lambda})-consistent and 1/(1-e^{-(lambda-1/b)})-robust (Thm 2.3, p. 4).
- Preferential Round-Robin for scheduling: (1/lambda)-consistent and 2/(1-lambda)-robust (Thm 3.3, p. 7).
- Wei and Zhang prove matching lower bounds for ski rental (Thms 1.1, 1.2, p. 3), so the trade-off is intrinsic and not an artefact of these algorithms (abstract, p. 1); the bounds are asymptotic in the purchase price B (pp. 7, 18). For scheduling they are tight only at the endpoints and for two jobs (Thms 1.3, 1.4, p. 4).

## Criticism
Bounds are worst case over predictions and use an absolute (L1) error eta, so they say nothing about error distributions, learning lambda from data, or changing lambda over time (see "What this source does not address" in both source pages).

## Not to be confused with
Bias-variance or accuracy-versus-cost trade-offs of a learned model: here both quantities are worst-case competitive ratios of the decision rule, not properties of the predictor.

## Relevance to this project
H1b asks for forecast-driven decisions with a worst-case guarantee; lambda is the trust dial, and the Wei lower bounds cap what any single-gap scheme can achieve (see [[container-keep-alive]]).

## Sources
- [[purohit-2018-online-algorithms-predictions]]
- [[wei-2020-robustness-consistency]]
