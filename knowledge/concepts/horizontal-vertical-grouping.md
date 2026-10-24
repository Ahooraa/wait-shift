---
title: "Horizontal and vertical instance grouping"
type: concept
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
tags: [placement, serverless, workflow]
sources:
  - "[[jia-2025-faaspr]]"
---

# Horizontal and vertical instance grouping

## Definition
Placement technique of [[faaspr]] (Sect. IV-A, pp. 2066-2068): vertically merge functions that share data edges on the critical path into groups (greedy, largest edge weight first, Alg. 1), then split each vertical group into several near-even horizontal groups (at least HG_limit = 4 instances per function) that are spread over servers, so each horizontal group is small enough to fit one server.

## Where it comes from
Replaces [[faasflow]]-style whole-group centralised placement, which fails when a group exceeds one server (p. 2066).

## How it is applied
Edge weights from average data size of the last 1000 invocations (p. 2067). Foreach nodes need at least the previous interval's maximum concurrency per horizontal group (p. 2067). Ablation DataTrans*: -18.15% average latency vs FaaSFlow (p. 2074).

## Not to be confused with
Horizontal/vertical scaling of instances.

## Relevance to this project
Not a D1-D3 mechanism; it shows what a placement scored by data locality (not by dispatch response) looks like.

## Sources
- [[jia-2025-faaspr]]
