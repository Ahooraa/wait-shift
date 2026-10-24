---
title: "Huawei Public Cloud serverless trace (2025 release)"
type: entity
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
tags: [dataset, trace, serverless, huawei]
sources:
  - "[[joosen-2025-cold-starts]]"
---

# Huawei Public Cloud serverless trace (2025 release)

## What it is
Event-level serverless trace from Huawei Cloud's YuanRong platform: five regions (R1-R5), 20 clusters, 31 days including a week-long holiday, 85 billion requests, over 12 million pods, 11.9 million cold starts. Released at https://github.com/sir-lab/data-release ([[joosen-2025-cold-starts]], pp. 1-3).

## The evidence
Three tables (Table 1, p. 2): request level (timestamp ms, hashed pod/cluster/function/user/request IDs, execution time in microseconds, CPU millicores, memory bytes); pod level (timestamp, IDs, total cold start time and four components in microseconds); function level (runtime, trigger type, CPU-MEM config). Pods per region from 3.2e5 (R1) to 7.0e6 (R5) (Fig. 1, p. 3). Not all functions of the regions are included (p. 2). All IDs hashed. Pool sizes from 300 millicores / 128 MB up to 26 cores / 32 GB (p. 10).

## Contested
Table 1 gives the function table for one region only while the trigger and runtime analyses use Region 2; check the paper's data statement against the repository.

## Relevance to this project
Candidate source of duration, arrival and cold-start distributions for the simulator; carries no workflow DAGs. Contrast with [[azure-functions-trace-2021]].

## Open / to verify
Which tables and columns the repository actually holds, whether per-minute series exist for all regions, and the time unit of the fits in [[cold-start-time-model]].

## Sources
- [[joosen-2025-cold-starts]]
