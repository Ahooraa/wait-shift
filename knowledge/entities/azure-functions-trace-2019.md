---
title: "Azure Functions trace (2019)"
type: entity
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
tags: [dataset, trace, serverless]
sources:
  - "[[shahrad-2020-serverless-wild]]"
---

# Azure Functions trace (2019)

## What it is
The production Azure Functions workload of 15-28 July 2019 (14 days, all invocations across Azure's infrastructure), documented in [[shahrad-2020-serverless-wild]] (p. 207) and released as a sanitized subset in the AzurePublicDataset repository. Four collected datasets: invocation counts per function in 1-minute bins; trigger per function; execution time per function (average, min, max, count per 30-second interval, per worker); memory per application (sampled every 5 s, per-minute averages of allocated and resident memory).

## The evidence
Distribution parameters and shares are summarised in [[azure-functions-workload-distributions]]. The paper's simulation uses the first week (p. 213).

## Contested
Limitations stated by the authors (p. 207): 1-minute resolution, no exact inter-arrival times below a minute; execution-time distribution only approximated by weighted percentiles; absolute totals withheld. It is a different collection from [[azure-functions-trace-2021]]; do not mix their statistics.

## Relevance to this project
Candidate arrival, duration and memory source for the simulator. No workflow/DAG structure.

## Open / to verify
Dataset README and column semantics (time unit of the log-normal fit); how the released subset relates to the full population described in the paper.

## Sources
- [[shahrad-2020-serverless-wild]]
