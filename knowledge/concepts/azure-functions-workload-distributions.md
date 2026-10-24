---
title: "Azure Functions workload distributions (2019)"
type: concept
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
tags: [serverless, workload, simulator-input]
---

# Azure Functions workload distributions (2019)

## Definition
Empirical and fitted distributions of invocation frequency, inter-arrival variability, execution time and memory for the Azure Functions 2019 workload ([[shahrad-2020-serverless-wild]], Sec. 3, pp. 207-210). Data: [[azure-functions-trace-2019]].

## How it is applied
Simulator inputs (printed USENIX page numbers):
- **Arrival frequency (p. 208):** daily invocations span over 8 orders of magnitude; 45% of apps at most hourly, 81% at most once per minute; the 18.6% of apps invoked at least once per minute carry 99.6% of invocations.
- **Inter-arrival CV (p. 209):** timer-only apps about 50% at CV 0; at-least-one-timer under 30%; all apps about 20%; about 10% of non-timer apps near 0; 40% of apps have CV above 1 (p. 210); few near 1, so not Poisson.
- **Triggers (p. 207):** functions/invocations in %: HTTP 55.0/35.9, Queue 15.2/33.5, Event 2.2/24.7, Orchestration 6.9/2.3, Timer 15.6/2.0, Storage 2.8/0.7, Others 2.2/1.0. Apps: HTTP-only 43.27%, timer-only 13.36%, queue-only 9.47%, HT 4.59%, HQ 4.22% (p. 208). 95% of timer functions fire at most once per minute.
- **Diurnal pattern (p. 208):** day/night and weekday/weekend cycle over a constant baseline of about 50% of the peak hour.
- **Execution time (p. 209):** log-normal MLE fit to the per-function average, log mean -0.38, sigma 2.36; 50% average under 1 s, 90% maximum at most 60 s, 75% maximum at most 10 s (p. 210); trigger medians 200 ms to 2 s; orchestration about 30 ms.
- **Memory (pp. 209-210):** per application; Burr fit to average allocated memory c = 11.652, k = 0.221, lambda = 107.083 (MB); maximum: 50% at most 170 MB, 90% at most 400 MB; no strong correlation with frequency or execution time.
- **Functions per app (p. 207):** 54% of apps have one function, 95% at most 10, about 0.04% above 100.

## Criticism
Fits are to marginal distributions of per-function averages, not per-invocation values; data binned at 1 minute (p. 207). Independence of rate, duration and memory is only loosely checked ("no strong correlation").

## Not to be confused with
The 2021 Azure trace ([[azure-functions-trace-2021]]), a different collection.

## Relevance to this project
Parameter table for synthetic arrival, duration and memory generation in the simulator; the heavy rate tail and CV above 1 argue against a Poisson-only arrival model.

## Sources
- [[shahrad-2020-serverless-wild]]
