---
title: "Raptor (speculative serverless scheduler)"
type: entity
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
tags: [software, scheduler, serverless, openwhisk]
sources:
  - "[[exton-2024-raptor]]"
---

# Raptor (speculative serverless scheduler)

## What it is
A distributed scheduler prototype for parallelizable serverless workflows. It extends OpenWhisk 2.0 with per-container function executors that replicate a workflow across a "flight" of peers, share state over SCTP, and preempt the replicas with POSIX job-control signals when one finishes ([[exton-2024-raptor]], pp. 4-7, 10). Code: github.com/kcexn/stochastic-scheduler-controller (p. 20, ref. 19).

## The evidence
About 35% lower mean response than stock OpenWhisk for SSH key generation on a 15-worker, 3-AZ cluster, about 1% on 5 workers/1 AZ (p. 15); word count over 50% faster (p. 15); thumbnails about 11% (Table 7, p. 13).

## Contested
Gains depend on near-independent execution times; the authors state that at small scale Raptor provides no performance benefits (p. 17). Linux, OpenWhisk and SCTP only (p. 18).

## Relevance to this project
A workflow-level speculative-execution baseline and a source of workflow shapes (fork-join width 2 and 4, map-reduce). Not an edge scheduler.

## Sources
- [[exton-2024-raptor]]
