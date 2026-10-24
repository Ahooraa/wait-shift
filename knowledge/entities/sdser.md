---
title: "Sdser (Synchronized Deployment and Scheduling for Expected Requests)"
type: entity
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
sources:
  - "[[liu-2025-sdser]]"
tags: [method, serverless, edge, dynamic-dag, bayesian, pre-deployment]
---

# Sdser

## What one sees
Framework of Liu, Zhou and Ma (ICDCS 2025): [[bayesian-hop-prediction]] of next functions, the PPS algorithm (LP relaxation plus randomized rounding, pre-deploys containers each slot; Alg. 1-2, pp. 894-895) and the three-priority Mosa online adjuster (Alg. 3, pp. 895-896), all in [[liu-2025-sdser]]. See [[predictive-pre-deployment]] and [[dynamic-dag-workflow]].

## The evidence
Experiments parameterised from DeathStar measurements, 15 servers, baselines OLC, GSP, Gendoc: up to 27.05% lower total overhead and 31.36% lower cold-start rate (p. 890); the ablation shows both prediction and Mosa contribute (pp. 897-898).

## Contested
The 7/2 guarantee covers rounding against the LP optimum of the predicted requests, not forecast error (p. 895). Slot length, retry limit and code are not given; no tail metrics, no overload rule.

## Relevance to this project
Candidate predictive baseline ("Sdser-type") against DFPS-style methods; the DFPS audit names the lack of a recent predictive baseline as weakness V3. The implementation checklist is in the focus block of [[liu-2025-sdser]]. It scores per-request overhead rather than workflow makespan, so a fair comparison needs an objective mapping.

## Sources
- [[liu-2025-sdser]]
