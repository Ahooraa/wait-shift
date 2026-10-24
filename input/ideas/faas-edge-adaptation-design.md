---
title: "Which DFPS weakness leaves the most exploitable headroom for serverless workflows at the edge, and can a practical method capture it?"
type: design
created: 2026-10-13
updated: 2026-10-13
tags: [serverless, faas, edge-computing, workflow-scheduling, function-placement, simulation, online-algorithms]
status: approved
author: mixed
---

# Headroom-gated screening of DFPS weaknesses (serverless workflows at the edge)

## Research Question
DFPS (Zolfaghari et al., IEEE TSC 2025) controls serverless workflows at the edge in a particular way. It reconfigures on a fixed clock, ignores reconfiguration cost, uses no forecasts, admits every request, and decouples placement from dispatch. We consider three candidate weaknesses:

- **D1:** clock-driven, cost-blind, forecast-free reconfiguration
- **D2:** admitting everything and optimising the mean during overload
- **D3:** placement decoupled from dispatch

Which of these leaves enough exploitable performance headroom under realistic, non-stationary workloads to justify a Q1 contribution? And does a practical method for the best-ranked weakness capture at least half of that headroom on held-out traces?

The question can come out negative. All three directions may show little headroom, or the method may capture too little of it.

## Relevance / State of the field (brief)
The gap evaluation (`input/description/dfps-gap-evaluation.md`; 73-paper corpus plus web search) ranked these as the strongest candidates:

- **T1 (when to reconfigure):** score 21/25
- **T2 (forecasts with a worst-case guarantee):** score 21/25
- **T4/T6 (tail-aware dispatch and admission control):** scores 20/25 and 17/25
- **T5 (two-timescale co-design):** score 20/25

The predictive, caching, fusion and GNN/DRL lines of work are crowded. Two 2026 papers that cite DFPS or work on the same problem (Sun et al., FGCS; Lei et al., JPDC) have not yet been read. Checking them is the first gate.

## Method
This is a staged, headroom-gated screening study using trace-driven discrete-event simulation. A corrected reimplementation of DFPS is the reference controller.

- **Practicality screen.** Each direction first gets a cheap check on the raw traces: how non-stationary demand is, and how often overload occurs.
- **Headroom experiment.** Each surviving direction then gets an oracle (clairvoyant) experiment that bounds the achievable gain. It is also compared against a simple heuristic, to rule out directions a heuristic already solves.
- **Method development.** Only directions that pass the pre-registered thresholds receive method development. Development has its own mid-point viability gate.
- **Confirmation.** It ends with a confirmatory test on held-out traces and a small Kubernetes testbed check.

**Why this design over the alternatives:** committing to one direction up front risks hundreds of hours on a gap with no exploitable headroom. Running all three directions in full would be infeasible.

## Data Sources / Material Basis
- **Workload traces:**
  - Azure Functions 2019 (per-minute invocation counts) and 2021 (per-invocation durations)
  - Huawei public traces 2023 (request series) and 2025 (cold starts)
- **Workflow DAGs:** SeBS-Flow workflows and Alibaba cluster-trace-v2018 batch DAGs.
- **Literature:** the user's 73-paper corpus, plus the acquire-pending sources listed in the plan.

## Output Target
☐ Book chapter   ☑ Journal article (Q1: IEEE TSC, TPDS, TCC or FGCS)   ☐ Grant proposal   ☐ Talk   ☐ Other

## Expected Results
- **Positive:** at least one direction shows oracle headroom of 25% or more (lower bound of the 95% CI) over the best-tuned corrected DFPS. The method captures at least 50% of that headroom on held-out traces, and the testbed check confirms the sign of the improvement.
- **Null:** no direction reaches the threshold. In that case the harness, the corrected DFPS and the realism results support a fallback paper re-evaluating edge serverless workflow schedulers.

## Ethical / Methodological Risks
- **Bias in reading the results:** oracle and threshold choices could be tuned after the fact. Mitigation: thresholds are pre-registered and the test traces stay untouched until confirmation.
- **Unfair baseline:** comparing against an incorrect DFPS. Mitigation: implement both the printed and the corrected variants.
- **Simulator fidelity:** mitigated by validation tests and the testbed check.
- **Licences:** only public traces under their published licences. No personal data is involved.

## Feasibility
- **Effort:** about 113 hours to the direction decision (gate G3), and about 400 hours to submission.
- **Tools:** Python (SimPy, pymoo, ruptures, numpy/scipy) and a commodity workstation. The testbed needs 4–6 VMs or Raspberry Pis running K3s and OpenFaaS or Knative.
- **People:** no collaborators are required. Emailing the DFPS authors for their code is optional.

## Scope Boundaries (what is NOT investigated)
- decentralised or multi-owner control (the DFPS authors' declared future work)
- user mobility
- energy and carbon
- GPU and LLM workflows
- function fusion
- layer caching

## Next Step
Hand off to writing-research-plan → `input/ideas/faas-edge-adaptation-plan.md`.
