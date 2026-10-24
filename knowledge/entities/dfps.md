---
title: "DFPS (Dynamic Function Placement and Scheduling)"
type: entity
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
tags: [software, scheduler, serverless, edge, workflow, baseline]
sources:
  - "[[zolfaghari-2025-dynamic-function-placement]]"
---

# DFPS (Dynamic Function Placement and Scheduling)

## What it is
A centralised controller architecture for serverless workflows (DAGs) in a multi-access edge network. It has three parts: an initial placement of function instances found once offline with NSGA-II, a per-request scheduler that matches the workflow DAG against the warm instances by graph pattern matching, and a periodic replacement and rescheduling step based on simulated annealing ([[zolfaghari-2025-dynamic-function-placement]], pp. 2-9). Objective: minimise average workflow makespan under container-capacity and storage constraints (p. 5). No code is released.

## The evidence
Evaluated in a modified [[edgecloudsim]] with workflows from the [[alibaba-cluster-trace]], against four baselines (SR, SG, Heu, RL), on average makespan, utilisation and cold starts; the abstract claims up to 86% lower makespan (pp. 1, 9-11). Reproduction parameters are in the focus block of the source page.

## Contested
The printed equations and algorithms contain several errors; see [[dfps-printed-errata]]. The evaluation uses stationary Poisson arrivals, so "dynamic" is never tested against change over time (reading of p. 9; gap list V1 in `input/description/dfps-gap-evaluation.md`).

## Relevance to this project
The reference system that the plan's adaptation work (D1 clock-driven reconfiguration, D2 admit-everything dispatch, D3 placement decoupled from dispatch) tries to improve on. See [[periodic-replacement-and-rescheduling]] for the D1 mechanism.

## Sources
- [[zolfaghari-2025-dynamic-function-placement]]
