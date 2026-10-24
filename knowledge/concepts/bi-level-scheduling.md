---
title: "Bi-level (global/local) scheduling"
type: concept
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
tags: [scheduling, hierarchical, serverless, edge]
sources:
  - "[[jayanthi-2026-quantum]]"
---

# Bi-level (global/local) scheduling

## Definition
A two-tier scheduling pattern: a global scheduler picks a coarse target (here cloud or one edge server) from summarised metrics, and a local scheduler refines the choice at node level (here a container). Jayanthi et al. 2026 justify it by scalability: a flat scheduler "would require knowledge of every container across all servers" (p. 7) [@jayanthi-2026-quantum].

## How it is applied
In [[jayanthi-2026-quantum]]: QNGO (global, population-based search over environments, p. 10–12) then PPO-RL (local, container choice, pp. 13–15). The global stage also prunes the PPO action space (p. 33).

## Not to be confused with
Bi-level optimisation in the mathematical-programming sense (leader/follower); this paper's "bi-level" is purely hierarchical decision-making. It is also not a placement-vs-dispatch split: both levels are placement decisions.

## Relevance to this project
Shows that "hierarchical" in recent edge-FaaS literature does not imply coupling placement with dispatch (relevant to D3 of the FaaS-edge adaptation plan).

## Sources
- [[jayanthi-2026-quantum]]
