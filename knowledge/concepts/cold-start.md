---
title: "Cold start (serverless)"
type: concept
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
tags: [serverless, latency]
---

# Cold start (serverless)

## Definition
The delay incurred when no warm function replica is available and the platform must create a container, allocate resources and load dependencies (Nguyen et al. 2025, Sec. I, p. 1).

## How it is applied
Measured example: EfficientDet function, 280 ms warm vs about 10.5 s cold, a 38x increase; literature cited reports 16x-166x of execution time on AWS Lambda/Azure ([[nguyen-2025-taming]], p. 2). Mitigations: shorter initialisation, container reuse/sharing, keep-alive, proactive prewarming, request shaping.

## Not to be confused with
Warm-start queueing delay (waiting for a busy warm container), which [[nguyen-2025-taming]] trades off against cold-start delay.

## Relevance to this project
Background cost model for reconfiguration (D1) and placement (D3) at the edge.

## Sources
- [[nguyen-2025-taming]]

## Added by exton-2024-raptor ingest (2026-10-13)
[[exton-2024-raptor]] reports no cold-start time distribution; it only attributes part of the Azure duration variance to cold starts (p. 2). Gap marker: cold-start parameters must come from other sources.
