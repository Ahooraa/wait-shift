---
title: "Problem scope: runtime placement and re-placement under externally-sized containers"
type: synthesis
created: 2026-10-27
updated: 2026-11-02
status: review
author: llm
tags: [scope, placement, re-placement, autoscaling, bin-packing, resource-contention, network-contention, g0-novelty]
sources:
  - "[[zolfaghari-2025-dynamic-function-placement]]"
  - "[[jia-2025-faaspr]]"
  - "[[gunasekaran-2020-fifer]]"
  - "[[bhasi-2021-kraken]]"
bibliography: ../../output/bibtex/references.bib
---

# Problem scope: runtime placement and re-placement under externally-sized containers

Fixed after a working session (27 Oct) narrowing the project from "DFPS-style dynamic placement" toward a
scope with a clearer boundary against autoscaling and a clearer baseline set. Supersedes the informal framing in
[[baseline-matrix]] sections 2-4 where it conflicts; does not invalidate the ablation results there (sizing vs.
placement vs. moves), which motivated this narrowing in the first place.

## 1. Problem in one sentence
On an edge cluster with fixed, heterogeneous per-node resource capacity, decide online where function containers
are placed, when they are relocated, and what happens to already-queued requests, while an external autoscaler
keeps changing how many containers each function gets under a changing workload.

## 2. System model

**Cluster.**
- A set of edge nodes, each with a fixed resource capacity `cap_k` (memory, GB) and a fixed storage capacity for
  intermediate state.
- Heterogeneous network distances between nodes, in a multi-tier edge topology.

**Containers.** *(Revised 2 Nov 2026: the uniform one-slot-per-container model is retired; see
[[heterogeneous-container-sizes]] for the audit and the change list.)*
- Each function `f` has a container weight `w_f` (its memory footprint), and a node holds any set of containers
  whose weights sum to at most `ecc_k`. The weights come from the workflow and task **profiles**, not from a
  distribution picked by hand: Alibaba cluster-trace-v2018 `plan_mem` per task ([[alibaba-cluster-trace]]) and the
  per-workflow `memory` setting of each SeBS-Flow benchmark ([[schmid-2025-sebs-flow]]). Each source is divided by its
  own median (the two are in different units), a function takes the mean over the tasks mapped to it, and the weights
  are normalised to mean 1 so that `ecc_k` still reads "containers of average size". Code: `dfps/profiles.py`.
- Memory is the capacity dimension because a warm container holds its memory whether it runs or not; CPU
  (`plan_cpu`, carried in the profile file) matters while a task runs and enters through the contention model below.
- A node's containers must satisfy `Σ (containers on k) × w_f ≤ ecc_k` -- a knapsack constraint, not a slot count.
  The earlier simulator treated every container as one slot. That was our reading of
  [[zolfaghari-2025-dynamic-function-placement]] (DFPS), Sec. 3.1, p. 4: "Each container requires a fixed, specific
  amount of CPU and memory resources. Therefore, each edge e_k can accommodate a limited number of containers ... ecc_k
  (container capacity)". The sentence gives a count bound; it does not say all functions are the same size, and the
  paper publishes no per-function sizes. Reading it as one slot per container was ours, not the paper's.
- Consequence for fill: with real-valued weights a node cannot in general be filled exactly, so the DFPS invariant D-7
  ("every slot always holds an instance") becomes "no container of the lightest function still fits".

**Global budget.**
- `N_total = Σ_k ecc_k` is fixed, in units of the average container. Capacity is only ever redistributed among
  functions -- never added or removed system-wide.

**Compute resource contention (new, 27 Oct).**
- Each function also has a CPU weight `c_f` (containers are 2D resource vectors `(cpu_f, mem_f)`, standard
  cluster-scheduling practice). The memory constraint above gates *admission* only; it says nothing about
  *execution speed* once containers are running concurrently.
- Default model: linear slowdown under overload --
  `actual_exec_time = exec_time × max(1, Σ running_cpu_demand_on_k / cpu_cap_k)`,
  a processor-sharing approximation. Simpler and more defensible than an M/M/c queueing model given the
  workload's non-stationarity (no steady-state assumption needed); revisit only if this proves too crude against
  testbed data.

**Network contention and transfer cost (revised, 27 Oct).**
- Previous model: `stt(size, k, k2) = h[k,k2] × (epd + size/bw)` -- correct on distance, but assumes every
  transfer gets the full per-hop bandwidth regardless of concurrent traffic.
- Addition: each hop has finite bandwidth; concurrent transfers sharing a hop split it by max-min fair sharing
  (recomputed as flows start/finish) -- the standard network-flow default, and a reasonable approximation of real
  TCP congestion behaviour over short flows.
- Same-node transfers (`h=0`) keep a small fixed overhead rather than being exactly free, since real container
  runtimes still cross a network/IPC boundary on the same host -- literature value for now, testbed-measured
  later.
- Transfer cost is resolved to the *specific* container instance chosen (nearest-instance lookup), not just the
  node -- already true in the current simulator, carried forward unchanged.

**Applications.**
- Serverless workflows, as DAGs of functions. Dependent tasks exchange intermediate state; transferring state
  between nodes takes time that grows with size, hop distance, and (new) current link contention.

**Workload.**
- Non-stationary request arrivals at edge origins, varying in rate, composition (which workflows are active), and
  spatial origin.

## 3. Inputs (given, not decided)
- Per-function container counts, produced by a standard external autoscaler (Kubernetes-HPA-style, or a simple
  queue-length rule), as desired instance counts per function at each epoch.
- **Contribution boundary:** the autoscaler is an input, not a contribution. This work is not about how many
  containers a function gets.
- The decision-maker observes cluster state only (current layout, queues, recent load, current contention) -- no
  knowledge of future arrivals.

## 4. Decisions (the scope)
1. **Fitting desired counts to the budget** -- when `Σ n_f × w_f` does not exactly fit `N_total`, reconcile to a
   feasible allocation (exact rule still open, see section 10).
2. **Placement of containers** -- which node hosts each container, respecting `cap_k`, `cpu_cap_k`, and storage
   limits.
3. **Removal of containers** -- which specific instance is removed when a function's count drops, and what
   happens to its queued/running requests.
4. **Relocation** -- whether to move existing containers between nodes with counts unchanged.
5. **Request handling on reconfiguration** -- where already-queued requests go when their container disappears or
   a better one appears, including moving queued requests between live containers.

## 5. Challenges / costs

| Decision | Cost |
|---|---|
| Add container | cold start |
| Remove container | its queued/running requests must be drained or reassigned |
| Relocate container | cold start at destination + temporary capacity gap at source |
| Move queued request | its input state is transferred again, under current link contention |
| Run container under load | execution slowdown under compute contention |
| Any change | churn: frequent reconfiguration can cost more than it gains |

## 6. Objective and metrics
- **Primary:** P99 end-to-end workflow completion latency.
- **Reported alongside, not optimised directly:** reconfiguration cost (cold starts, bytes re-transferred).

## 7. Out of scope
- Designing the autoscaler, or deciding total system capacity.
- Live migration (moving a container with its in-memory state) -- functions are stateless; relocation is a
  restart elsewhere.
- Elastic/unbounded cloud capacity.
- Single-function applications with no inter-function data dependency.

## 8. Assumptions
- Container resource weight `w_f` and CPU weight `c_f` are continuous, not discretised into size classes, and are derived
  from workflow and task profiles (Alibaba `plan_mem`/`plan_cpu`, SeBS-Flow `memory`), not assumed equal (2 Nov).
  The two profile sources are put on one scale by dividing each by its own median; that is an assumption.
- Network links have finite, shared bandwidth per hop (max-min fair sharing under contention).
- Compute contention follows a linear processor-sharing slowdown, not a full queueing-theoretic model.
- One central decision-maker.
- Placement is vector bin-packing under heterogeneous 2D weights plus relocation and request-moves on top --
  closer to VM-placement-with-bin-packing literature than to plain assignment; name this explicitly in related
  work so the baseline choice reads as deliberate.

## 9. Validation plan (phased)
- **Phase 1 (now):** simulation, with `w_f`, `c_f`, cold-start, and network-timing parameters from the literature
  (DFPS Table 2, FaaSPR's stated ranges) -- realistic but not measured.
- **Phase 2 (for a Q1 submission):** testbed validation -- real edge nodes, real container runtime, measured
  network timing, memory and CPU footprints, and link contention -- to ground the simulation parameters and
  validate headline results on real hardware. Not yet designed; when scoped, needs: testbed size, platform
  (e.g. K3s/OpenFaaS on real or virtualised edge nodes), and which specific claims the testbed must confirm (a
  literature-sourced simulation cannot be the final evidence for a Q1 claim on its own).

## Evidence base
- [[baseline-matrix]] sections 2 and 4: sizing swap (HPA-style) kept ~98% of the controller's gain (+2.3%,
  12/18 wins) while disabling request moves raised geometric-mean P99 from 130s to 1,022s -- the empirical basis
  for narrowing the contribution to placement/re-placement/moves and treating sizing purely as an input.
- [[jia-2025-faaspr]]: source of the 0.5-2GB container-memory range (section 9, p. 10) and the only baseline in
  this project that already models heterogeneous container sizes natively.
- [[zolfaghari-2025-dynamic-function-placement]] (DFPS): says "each container requires a fixed, specific amount of
  CPU and memory resources" (Sec. 3.1, p. 4) and bounds a node by `ecc_k` containers; it does not state that all
  functions are one size. The uniform-slot model was our reading of it, retired on 2 Nov; its own
  `FEN()` placement formula (Eq. 3-4) has no notion of a function costing more capacity than another, which is
  why it is not fairly comparable under this scope's weights without a disclosed, audited port (section 10).
- `knowledge/_meta/log.md` (2026-10-26, "state-transfer modeling check"): the topology-hop-variance finding that
  motivated taking the network model seriously here rather than leaving it a flat/contention-free formula.

## What stays open
- **D2 fitting rule:** exactly how desired autoscaler counts reconcile to the continuous GB budget when they do
  not fit exactly (proportional scale-down weighted by `w_f`, greedy drop-smallest-marginal-value, or another
  rule) -- not yet fixed.
- **DFPS baseline fairness:** recommended default is to run DFPS only in a homogeneous-weight regime (its native
  assumption) as one baseline, and treat a weighted, fidelity-audited DFPS port as a stretch goal rather than a
  blocking requirement for phase 1.
- **Spatial workload realism:** current traces (`thin_arrivals`) have uniform, static request origins; the
  motivating case for placement (vs. sizing alone) is strongest when origins shift, so a new trace-generation
  step may be needed before this scope's central claim can be demonstrated convincingly.
- **Container-weight distribution shape:** uniform 0.5-2GB (FaaSPR's range) vs. something closer to a real
  function-memory histogram (e.g. derived from the Azure public trace's own reported size fields, if any exist)
  -- worth checking what data is actually available before committing to a shape.
- **D8 compute contention model:** linear slowdown under overload (recommended, adopted as default above) vs.
  M/M/c queueing -- revisit only if testbed data shows the linear model is too crude.
- **D9 network contention model:** max-min fair sharing per hop (recommended, adopted as default above) vs. a
  simpler per-hop concurrent-transfer cap.
- **D10 same-node transfer overhead:** small fixed constant (recommended, adopted as default above) vs. exactly
  zero -- exact value needs a literature source or an early testbed measurement.
- **Engineering cost, stated plainly:** contention (compute and network) is a real simulator extension, not a
  scope-doc change -- `dfps/sim.py` needs running-container tracking per node and concurrent-flow tracking per
  link, neither of which exists today. Every existing result in [[baseline-matrix]] was produced without
  contention; that layer is not invalidated, but any claim carried forward into a paper needs the sizing/
  placement/moves ablations re-run once contention is built, since contention could change which mechanism wins.
