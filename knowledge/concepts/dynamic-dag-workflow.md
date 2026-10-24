---
title: "Dynamic DAG workflow"
type: concept
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
tags: [workflow, serverless, dynamic-dag]
sources:
  - "[[liu-2025-sdser]]"
---

# Dynamic DAG workflow

## Definition
A serverless application whose invoked execution path varies per request: the successor is unknown until the current function finishes, and function invocation frequency can differ by up to 70% (pp. 890-891 of [[liu-2025-sdser]]).

## How it is applied
[[liu-2025-sdser]] treats each hop as an independent request triple and ignores parallel fan-out; this makes per-hop prediction possible but hides workflow-level makespan.

## Not to be confused with
Static DAGs with a fixed path, as in [[sfsm]] and [[platform-agnostic-workflow-model]].

## Relevance to this project
Defines the workload class where predictive pre-deployment matters: the successor is uncertain, so containers for all branches would over-provision ([[cold-start]]). Parameter source: [[deathstar-benchmark]].

## Sources
- [[liu-2025-sdser]]
