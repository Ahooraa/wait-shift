---
title: "DeathStarBench"
type: entity
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
sources:
  - "[[liu-2025-sdser]]"
tags: [benchmark, microservices, dynamic-dag]
---

# DeathStarBench

## What one sees
Open microservice benchmark suite (social network and others) whose requests take varying call paths. [[liu-2025-sdser]] cites it as its reference for dynamic-DAG behaviour (p. 890).

## The evidence
Sdser's authors drove it with wrk and traced it with Jaeger to record per-service execution time, cold-start time and container memory (Sect. IV-A, p. 896). The measured values are not tabulated in the text.

## Relevance to this project
A source of dynamic-DAG path structure and per-service parameters for [[dynamic-dag-workflow]] experiments; durations are service-level, so heavy-tail parameterisation still needs [[heavy-tailed-function-durations]].

## Open / to verify
Which DeathStar applications and how many functions were used is not stated in the text read.

## Sources
- [[liu-2025-sdser]]
