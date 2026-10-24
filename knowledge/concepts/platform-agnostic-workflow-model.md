---
title: "Platform-agnostic serverless workflow model (SeBS-Flow)"
type: concept
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
tags: [serverless, workflows, dag, petri-net]
sources:
  - "[[schmid-2025-sebs-flow]]"
---

# Platform-agnostic serverless workflow model (SeBS-Flow)

## Definition
A workflow model based on workflow nets with data (WFD-nets, Petri-net extension), where transitions are either serverless functions or coordinators (the orchestrator awaiting a phase and scheduling the next), extended with resource annotations for data passing (object storage, NoSQL, invocation payload, transparent, reference) ([[schmid-2025-sebs-flow]], pp. 3-4). Specified in JSON with six phase types: task, map, loop, repeat, switch, parallel (p. 5).

## Where it comes from
Introduced by Schmid et al. to abstract away incompatible state-machine (AWS, GCP) and orchestrator-function (Azure) programming models (pp. 2-3).

## How it is applied
Transcribed to AWS/GCP/Azure by platform generators; checked against 58 judgeable literature workflows, 53 fully expressible (p. 8). Used by [[sebs-flow]].

## Criticism
It is level-synchronous: each phase receives the previous phase's output and the coordinator joins all functions before the next phase (pp. 4-5), so finer dependency structures are not expressible; map fan-out is fixed only at run time by array size (p. 5). Not a criticism voiced in the paper; my reading.

## Not to be confused with
Provider-specific workflow definitions (Amazon States Language, Google Workflows YAML) and with general DAG schedulers that carry per-edge dependencies.

## Relevance to this project
The JSON definition gives a parseable, platform-neutral DAG source for a simulator and a testbed; the AND-join per phase must be mapped to DFPS-style dependency handling.

## Sources
- [[schmid-2025-sebs-flow]]
