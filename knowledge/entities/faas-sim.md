---
title: "FaaS-Sim"
type: entity
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
tags: [simulator, software, serverless]
sources:
  - "[[jayanthi-2026-quantum]]"
---

# FaaS-Sim

## What it is
Python simulator for serverless edge/cloud platforms with Edge and Cloud node types of distinct processing and storage capability (as described in [[jayanthi-2026-quantum]], p. 15). Version and citation are not given in that paper.

## Relevance to this project
Jayanthi 2026 evaluate on it (Python 3.12.3, 1 cloud + 3 edge nodes by default, Table 1, p. 16). The project's own decision is to extend the in-repo `dfps/sim.py` instead (see log, 2026-10-13).

## Open / to verify
Which FaaS-Sim (faas-sim by Rausch et al.?) is meant is not stated; verify before relying on it.

## Sources
- [[jayanthi-2026-quantum]]
