---
title: "Heavy-tailed function durations"
type: concept
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
tags: [workload, distributions, simulator-parameterisation]
---

# Heavy-tailed function durations

## Definition
Serverless execution/response times with squared coefficient of variation (SCV) far above 1 (exponential = 1), i.e. a long right tail ([[exton-2024-raptor]], pp. 2, 4).

## How it is applied
Reported moments: 2019 Azure mean about 0.7 s, SCV about 11.7 (p. 4; 11.4 on p. 2); 2021 Azure mean about 3 s, SCV about 30.6 (p. 4). The paper fits no family. As a derived option (not stated in the source), a moment-matched lognormal has sigma^2 = ln(1+SCV) and mu = ln(mean) - sigma^2/2: 2019 gives sigma about 1.59, mu about -1.63 (seconds); 2021 gives sigma about 1.86, mu about -0.63. A two-phase hyperexponential would also match SCV above 1. Check against the raw trace before use.

## Criticism
The paper mixes "response time" and "execution time" wording and the 2019 SCV differs between pages 2 and 4; moments alone do not fix tail shape.

## Not to be confused with
Heavy tail in the strict (power-law) sense: only SCV is reported, so no tail index is known.

## Relevance to this project
Duration model for simulator tasks; pair with raw data from [[azure-functions-trace-2021]] to fit.

## Sources
- [[exton-2024-raptor]]
