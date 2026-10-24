---
title: "Hybrid histogram keep-alive policy"
type: concept
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
tags: [serverless, cold-start, keep-alive, policy]
---

# Hybrid histogram keep-alive policy

## Definition
Per-application policy of [[shahrad-2020-serverless-wild]] (Sec. 4.2, pp. 211-212) that sets two parameters: the *pre-warming window* (time after the last execution before the app image is reloaded; 0 means never unload) and the *keep-alive window* (how long the image stays loaded after being loaded or after an execution).

## How it is applied
- **Histogram:** idle times (end of execution to next invocation) in 1-minute bins, range e.g. 4 h; longer ITs are out-of-bounds (OOB). Pre-warm = 5th percentile (rounded down), keep-alive = 99th percentile (rounded up) of in-bound ITs, with a 10% margin each (p. 211).
- **When it re-decides:** after every invocation/execution end the windows are recomputed from the updated histogram (OpenWhisk Load Balancer, p. 213; Azure: when an app goes executing to idle, pre-warm event scheduled 90 s early, pp. 215-216). Event-driven, not periodic.
- **Regime switch (the trigger logic):** (1) too few ITs or a changing pattern, i.e. CV of histogram bin counts below a threshold (default 2, Welford online), gives standard keep-alive (pre-warm 0, keep-alive = histogram range) until the histogram is representative again; (2) too many OOB ITs gives an ARIMA forecast of the next IT with 15% margin (pre-warm = prediction minus 15%, keep-alive 15% each side); (3) otherwise the histogram is used (p. 212, Fig. 10).
- **Forgetting:** production keeps one histogram per day and drops those older than 2 weeks (p. 215).
- **Results:** about 2.5x fewer 75th-percentile cold starts than 10-min fixed at equal memory in simulation; 15.6% less container memory in OpenWhisk (pp. 214-215).

## Criticism
Learns only from the app's own idle-time history; no explicit change-point test beyond the CV check; slow for rarely invoked apps; no deadline, cost or system-load input.

## Not to be confused with
Fixed keep-alive (10 min AWS/OpenWhisk, 20 min Azure) and lazy cache eviction (pp. 206, 212, 216).

## Relevance to this project
Reference point for D1 (when to re-decide): the trigger is a per-invocation event plus a statistical representativeness gate, against which a model-predictive or drift-based reconfiguration trigger can be compared. See also [[cold-start]].

## Sources
- [[shahrad-2020-serverless-wild]]
