---
title: "IceBreaker (Roy, Patel, Tiwari 2022)"
type: entity
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
tags: [serverless, prewarming, software]
---

# IceBreaker

## What it is
Serverless scheduling framework (ASPLOS 2022, Roy, Patel, Tiwari) that prewarms functions on heterogeneous servers using a Fourier-based invocation predictor and a utility-based placement strategy ([[nguyen-2025-taming]], Sec. II, IV).

## Contested
[[nguyen-2025-taming]] argues IceBreaker does not coordinate prewarm completion with dispatch and does not shape requests; in their homogeneous testbed its placement advantage is disabled, which may understate it (Sec. V-C, p. 6).

## Relevance to this project
Source of the Fourier forecaster reused by the MPC scheduler; its heterogeneity-aware placement is a candidate prior art for D3 (to be checked in its own source page).

## Sources
- [[nguyen-2025-taming]]
