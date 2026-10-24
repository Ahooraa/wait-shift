---
title: "Apache OpenWhisk"
type: entity
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
tags: [serverless, platform, software]
---

# Apache OpenWhisk

## What it is
Open-source FaaS platform (openwhisk.apache.org) that runs on Kubernetes. Default policy: cold start whenever no warm container is free; containers kept warm for up to 10 minutes after last use ([[nguyen-2025-taming]], Sec. IV, p. 4).

## The evidence
[[nguyen-2025-taming]] implements its MPC scheduler as middleware (Redis queue, wsk CLI prewarm, Loki-checked reclaim) without modifying OpenWhisk core, on single-node k3s.

## Relevance to this project
Baseline platform/default policy in the nearest MPC prior art for G0.

## Sources
- [[nguyen-2025-taming]]

## Added by exton-2024-raptor ingest (2026-10-13)
[[exton-2024-raptor]] (pp. 5, 12) tuned OpenWhisk 2.0 on a 3-AZ GCP cluster: control-plane overhead median about 9 ms (about 6-7 ms single AZ), p90 14-16 ms (Table 6); the scheduler uses queues to manage cold-start frequency (p. 5). See [[raptor]].
