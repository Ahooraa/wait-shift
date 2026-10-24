---
title: "SeBS-Flow"
type: entity
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
tags: [benchmark, software, serverless, workflows]
sources:
  - "[[schmid-2025-sebs-flow]]"
---

# SeBS-Flow

## What it is
Open-source benchmark suite for serverless workflows, built on the SeBS FaaS benchmark suite. It ships six application workflows (Video Analysis, Trip Booking, MapReduce, ExCamera, Machine Learning, 1000Genomes) and four microbenchmarks, a platform-agnostic JSON workflow definition ([[platform-agnostic-workflow-model]]), and generators for AWS Step Functions, Google Cloud Workflows and Azure Durable Functions ([[schmid-2025-sebs-flow]], pp. 1, 5-7).

## Location and authority data
Code: https://github.com/spcl/serverless-benchmarks (SeBS repository); experiment artifact: https://github.com/spcl/sebs-flow-artifact (p. 1). Languages: Python, Node.js, C++, Java (p. 6). License and exact directory layout for workflows not verified (not stated in the paper).

## The evidence
Workflow shapes, sizes and measured runtimes are tabulated in the focus block of [[schmid-2025-sebs-flow]] (Table 4, p. 7; Fig. 7, p. 9).

## Contested
Representativeness is argued by comparison with published workflow characterisations (p. 7); all applications are fixed-size, bursty (30 invocations), cloud-hosted, without deadlines.

## Relevance to this project
Candidate source of realistic workflow DAGs (2 to 19 functions, fan-out up to 12, depth up to 6) for the simulator and Kubernetes testbed. Reuse requires a new transcription backend and replacement of cloud storage and NoSQL services; per-function durations must come from the artifact's raw data. See [[apache-openwhisk]] as a possible testbed platform.

## Open / to verify
Check the repo for per-function timing data and whether workflow JSON files are standalone; check whether a Kubernetes/OpenWhisk backend exists in newer commits.

## Sources
- [[schmid-2025-sebs-flow]]
