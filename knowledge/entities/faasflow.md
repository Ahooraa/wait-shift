---
title: "FaaSFlow"
type: entity
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
tags: [software, serverless, workflow, baseline]
sources:
  - "[[jia-2025-faaspr]]"
---

# FaaSFlow

## What it is
State-of-the-art serverless workflow system (Li et al., ASPLOS 2022; ref. [17] of [[jia-2025-faaspr]]) that groups function instances with data dependencies, places each group centrally on one server and passes data through shared memory (pp. 2063, 2066).

## Contested
[[jia-2025-faaspr]] argue its groups exceed one server's capacity under high concurrency and that it ignores instance migration, causing frequent cold starts (p. 2063, p. 2074). This is the authors' characterisation, not independently checked here.

## Relevance to this project
The only baseline in [[faaspr]]'s evaluation (p. 2072); not a DFPS-family scheduler.

## Sources
- [[jia-2025-faaspr]]
