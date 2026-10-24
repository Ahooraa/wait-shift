---
title: "FaaSPR"
type: entity
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
tags: [software, scheduler, serverless, workflow, placement, routing, g0]
sources:
  - "[[jia-2025-faaspr]]"
---

# FaaSPR

## What it is
Serverless workflow scheduler (about 2800 LOC Python prototype on Kubernetes, Redis, SciPy; p. 2070) that couples an instance **placement generator** with a **routing scheduler**. Placement runs on every platform scaling request; routing is a multi-stage LP that outputs path-selection frequencies (pp. 2065-2066). Introduced in [[jia-2025-faaspr]].

## History of research
Positioned against [[faasflow]] (centralised grouping, ignores migration/cold start) and Palette (annotation-driven locality hints) (pp. 2063, 2075-2076).

## Contested
Whether its "placement and routing" is the same thing as the D3 coupling of DFPS-style placement with request dispatch: it is a one-way sequential coupling (placement assumes random routing, routing then adapts), see the G0 verdict in [[jia-2025-faaspr]].

## Relevance to this project
Flagged in the plan as the strongest threat to D3. Evidence: no re-placement trigger or forecast guarantee, no admission control, cloud-datacentre evaluation only. Components: [[horizontal-vertical-grouping]], [[migration-minimizing-placement]], [[multi-stage-lp-routing]].

## Sources
- [[jia-2025-faaspr]]
