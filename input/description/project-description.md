---
title: "Project description"
updated: 2026-10-27
---

# Runtime placement and re-placement of serverless workflow containers on resource-constrained edge clusters

## Research question

Given an external autoscaler that sets per-function container counts reactively under a changing workload, how
should those containers be placed, relocated, and how should already-queued requests be handled at runtime, on an
edge cluster with fixed, heterogeneous per-node resource capacity and non-trivial network/compute contention --
and does this placement/re-placement layer improve tail (P99) workflow completion latency over existing
placement, migration and request-scheduling approaches, beyond what the autoscaler's sizing decisions alone
achieve?

The full system model, decision variables, costs, metrics and modelling assumptions are fixed in
[[problem-scope]] (`knowledge/synthesis/problem-scope.md`) and are the authoritative, current scope -- this file
is a summary entry point into it, not a duplicate; read that page for anything more detailed than below.

## Context and motivation

Edge-deployed serverless workflows (DAGs of functions with data dependencies) run under tight, fixed per-node
capacity, heterogeneous network distances, and autoscalers that only decide *how many* containers a function
gets, not *where* they go or what happens to work already waiting when the layout changes. DFPS (Zolfaghari et
al. 2025) is the closest prior system, but conflates sizing and placement into one mechanism and assumes
uniform-size containers on a mostly-idealised network. Our own ablations (see [[baseline-matrix]]) show sizing is
not where the gain comes from (an HPA-style sizing swap keeps ~98% of the controller's gain) while disabling
request moves is catastrophic (geometric-mean P99 rises 8x) -- this motivated narrowing the contribution to
placement, relocation and request-move decisions specifically, with sizing treated as an external input.

## Methodology

Discrete-event simulation (own simulator, `dfps/`), built from a corrected re-implementation of DFPS (errata
E1-E4 fixed) and extended with: heterogeneous container resource weights (continuous GB, replacing DFPS's
uniform-slot assumption), compute resource contention (linear processor-sharing slowdown under node CPU
overload), and network link contention (max-min fair sharing per hop under concurrent transfers). Controllers and
baselines are compared under identical scenarios, seeds and metrics; published mechanisms (FaaSPR placement/
routing, Fifer/Kraken/HPA sizing rules, join-shortest-queue, work stealing) are ported as faithfully as possible,
with every adaptation from the source paper's own formulas disclosed and fidelity-audited in the relevant source
page. Phase 1 is simulation-only, with parameters from the literature (DFPS Table 2, FaaSPR's stated ranges).
Phase 2 (planned, for a Q1-journal submission) is testbed validation on real edge hardware, to measure actual
container resource weights, cold-start costs and network contention, and to validate the simulation's headline
results against them -- not yet designed.

## Expected outcomes

A journal article (target: Q1), reporting: (1) the problem scope and its departure from DFPS's model (heterogeneous
containers, contention), (2) simulation results comparing the proposed placement/re-placement mechanism against
the baseline set in [[baseline-matrix]], under the contention-aware model, (3) testbed validation of the
simulation's central claims (phase 2). The simulator and its scenario-generation code are a secondary deliverable
(reproducibility).

## Scope boundaries

Out of scope, per [[problem-scope]] section 7: designing the autoscaler itself or deciding total system capacity
(sizing is always an external input); live migration of a container's in-memory state (containers are stateless;
relocation is a restart elsewhere); elastic/unbounded cloud capacity; single-function applications with no
inter-function data dependency. See [[problem-scope]] section 10 for the currently open decisions (count-fitting
rule, DFPS baseline fairness under heterogeneous weights, spatial workload realism, contention-model parameter
choices) -- these are tracked there, not duplicated here, and this file should be treated as stale on any of them
without checking that page first.

## People

[Add: roles, responsibilities.]

## Timeframe

Phase 1 (simulation): in progress. Phase 2 (testbed validation): not yet scheduled.
