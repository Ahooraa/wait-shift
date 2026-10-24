---
title: "Keep-alive time"
type: concept
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
tags: [serverless, cold-start, policy]
sources:
  - "[[joosen-2025-cold-starts]]"
---

# Keep-alive time

## Definition
Idle period after which a warm pod is deleted; on the Huawei platform one minute by default, reset on every request ([[joosen-2025-cold-starts]], p. 3).

## How it is applied
Functions invoked less often than once per minute, notably timers, cold-start on nearly every call; the authors suggest dynamic keep-alive and pre-warming for them (pp. 10, 13). Keep-alive policy is also studied by FaasCache (their ref. [10], no page here).

## Relevance to this project
Fixed simulator parameter (60 s) for the warm/cold decision behind [[cold-start]].

## Sources
- [[joosen-2025-cold-starts]]
