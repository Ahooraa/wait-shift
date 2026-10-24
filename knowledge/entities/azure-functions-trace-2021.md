---
title: "Azure Functions invocation trace (2021)"
type: entity
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
tags: [dataset, trace, serverless]
sources:
  - "[[jayanthi-2026-quantum]]"
---

# Azure Functions invocation trace (2021)

## What it is
Public Microsoft Azure Functions invocation trace (AzureFunctionsInvocationTrace2021 in the AzurePublicDataset repository, per the data statement of [[jayanthi-2026-quantum]], p. 35). Jayanthi describe it as 14 days of function invocations (p. 16). It carries per-function arrivals and durations but no workflow/DAG structure.

## Relevance to this project
A candidate arrival source for simulator workloads. Jayanthi 2026 use it with an 80/20 train/test split (p. 16).

## Open / to verify
The paper's description ("virtual machines, task arrivals, CPU and memory usage") mixes in features of other Azure traces (p. 16); verify against the dataset README. The 2019 trace of Shahrad et al. is a different dataset.

## Sources
- [[jayanthi-2026-quantum]]

## Added by exton-2024-raptor ingest (2026-10-13)
[[exton-2024-raptor]] (p. 4) quotes the 2021 trace as mean response about 3 s with SCV about 30.6, versus mean about 0.7 s and SCV about 11.7 for the 2019 trace. See [[heavy-tailed-function-durations]].
