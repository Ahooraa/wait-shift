---
title: "ClusterLess (deadline-aware workflow orchestrator for federated edge K8s clusters)"
type: entity
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
tags: [software, orchestrator, serverless, edge, workflow, kubernetes, novelty-gate-g0]
sources:
  - "[[farahani-2026-clusterless]]"
---

# ClusterLess

## What it is
A two-tier orchestrator for serverless DAG workflows with end-to-end deadlines on federated Kubernetes edge clusters, built on OpenFaaS and Argo and evaluated on six clusters with 64 nodes (pp. 1, 6). Each cluster master orchestrates locally and picks one of four execution modes per ready function ([[execution-mode-selection]]). A load-elected super-master places offloaded functions on remote clusters ([[deadline-feasible-offloading]]). Authors: Farahani, Colosi, Murturi, Nastic, Villari, Dustdar, Prodan; arXiv preprint 2026.

## Contested
No peer-reviewed venue is known; the 40% and 90% figures are single-testbed averages against four self-built baselines, none of them a published scheduler (p. 7).

## Relevance to this project
Candidate competitor for D2 and D3 at gate G0 of the headroom plan. It is reactive, per-invocation and forecast-free, and has no admission control. See the G0 verdict in [[farahani-2026-clusterless]]. Contrast with [[dfps]].

## Sources
[[farahani-2026-clusterless]]
