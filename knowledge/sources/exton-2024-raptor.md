---
title: "Exton & Rodriguez 2024 — Raptor: Distributed Scheduling for Serverless Functions"
type: source
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
bibkey: exton-2024-raptor
depth: standard
tags: [serverless, scheduling, speculative-execution, openwhisk, workload-parameters, simulator-parameterisation]
relations:
  - target: raptor
    type: mentions
    confidence: extracted
    because: "The scheduler this paper proposes and prototypes (Sec. 3, pp. 5-10)."
  - target: speculative-execution
    type: builds-on
    confidence: extracted
    because: "Adapts straggler mitigation by speculative execution from data-processing frameworks: «Speculative execution has a strong track record as an effective straggler mitigation technique» (p. 2)."
  - target: heavy-tailed-function-durations
    type: supports
    confidence: extracted
    because: "Reports SCV about 11.7 (2019) and 30.6 (2021) for Azure traces (p. 4)."
  - target: azure-functions-trace-2021
    type: cites
    confidence: extracted
    because: "Quotes mean response about 3 s, SCV about 30.6 for the 2021 Azure trace (p. 4)."
  - target: apache-openwhisk
    type: mentions
    confidence: extracted
    because: "Prototype integrated with OpenWhisk 2.0 and evaluated on it (pp. 5-6, 10-12)."
  - target: cold-start
    type: mentions
    confidence: extracted
    because: "Attributes part of the duration variance to cold starts (p. 2); bundle delivered once at cold start (p. 8)."
---

# Raptor: Distributed Scheduling for Serverless Functions

## Bibliographic Details
Exton, Kevin; Rodriguez, Maria A. 2024. *Raptor: Distributed Scheduling for Serverless Functions*. arXiv:2403.16457v2 [cs.DC], 13 Dec 2024 (PDF dated 16 Dec 2024). https://arxiv.org/abs/2403.16457. No DOI; arXiv-only preprint, publication status unverified.

> Page note: printed page numbers equal PDF pages (arXiv layout, 23 pp.; references from p. 18).
> Author note: the PDF title page names "Maria A. Rodriguez"; the library bib entry reads "Read, Maria". Flagged for the human; the bibkey is unaffected.

## Section map

| Covered | Section | pp. |
|---|---|---|
| ✓ F1 | Abstract; 1 Introduction (Azure trace statistics, speculative execution, contributions) | 1-3 |
| ✓ F1 | 2 Background and Related Work (straggling, 2019/2021 Azure SCV, preemption) | 3-5 |
| — | 3.1 Function invocation, routing, scheduling in OpenWhisk (controller/scheduler/invoker, v1 vs 2.0) | 5-6 |
| — | 3.2 Raptor architecture (flights, action fork, SCTP state-sharing) | 6-7 |
| ✓ F1 | 3.3 Scheduling procedure: action manifest, fork, execute (cyclic-shift DAG order), preempt | 7-10 |
| ✓ F1 | 4.1 OpenWhisk performance overhead (GCP cluster, tuning, control-plane latency, Tables 4-6) | 10-13 |
| ✓ F1 | 4.2.1 SSH key generation workflow (Poisson arrivals, exponential min/max argument) | 13-15 |
| ✓ F1 | 4.2.2 Word count and thumbnail workflows; Table 7 | 13, 15-16 |
| ✓ F1 | 4.2.3 Reliability and fault tolerance (task-failure simulation) | 16 |
| — | 5 Conclusions; 5.1 Future work | 17-18 |

## Kernthesen

### 1. Straggling makes serverless duration distributions heavy-tailed (pp. 2, 4)
Job scheduling at warehouse scale skews response-time distributions to heavy tails. The authors support this with Azure statistics: mean about 0.7 s and squared coefficient of variation (SCV) about 11.4 on p. 2, and about 0.7 s and SCV about 11.7 on p. 4 for the 2019 trace (an internal inconsistency).

### 2. The 2021 Azure trace is more variable than 2019 (p. 4)
2019: mean about 0.7 s, SCV about 11.7. 2021: mean about 3 s, SCV about 30.6. The authors read the rise as a lengthening tail and a worsening straggler problem.

### 3. Speculative execution mitigates stragglers, and its cost is wasted capacity (p. 4)
Excess copies reduce capacity and raise energy use; mitigations include delayed speculation, straggler prediction and budgeting. Raptor chooses preemption of the losing copies.

### 4. Under Poisson arrivals and i.i.d. exponential service, preemption removes the capacity loss of replication (p. 4)
Cited from Gardner et al. (reference 23), not shown here.

### 5. Raptor runs workflow replicas in "flights" with peer-to-peer state sharing (pp. 4-7)
All tasks are executed speculatively by all flight members, and the flight is preempted as soon as one member completes the last task. State is shared over SCTP; events are delivered in half an RTT (p. 6).

### 6. Workflows are described by an action manifest (name, location, dependencies, concurrency) (pp. 7-9)
Table 1 is a four-function diamond (fn1 to fn2 and fn3, then fn4) with concurrency 2. Each executor derives a DAG, and followers apply a cyclic shift to the search order to decorrelate execution sequences (Table 3, p. 9).

### 7. Preemption uses POSIX job-control signals on per-invocation process groups (pp. 4, 10)
Functions not yet started are never started; running ones are signalled to release resources.

### 8. Benefit depends on scale and independence (pp. 3, 14-15)
At 5 workers in one availability zone (AZ), Raptor gains about 1% on mean response time; at 15 workers over 3 AZs it gains about 35%, matching the i.i.d. exponential prediction E[T_Raptor]/E[T_OpenWhisk] = 2 E[min(Z1,Z2)] / E[max(Z1,Z2)] = 1/1.5, about 0.67 (p. 15).

### 9. Load matters: best at moderate load (pp. 14-15)
At low load too few containers exist for independence; at high load Kafka queueing dominates.

### 10. Replication also lowers job failure probability (p. 16)
Stock fork-join failure compounds with the number of parallel tasks (all must succeed); Raptor needs at least one success, so job failure probability falls toward 0 (Fig. 8).

### 11. Even near-deterministic data-parallel workflows benefit (pp. 15-16, Table 7)
Word count improves by over 50% (mean 4296 to 1954 ms), mainly because the state-sharing stream bypasses the control data path; thumbnails improve about 11% (mean 1653 to 1474 ms).

### 12. A tuned OpenWhisk control plane adds small, stable overhead (pp. 11-13)
Median about 9 ms (3 AZ) and about 6-7 ms (1 AZ), with 90th percentile 14-16 ms (Table 6, p. 12); the workflows were chosen with mean execution at least 10x this overhead (p. 10).

## Figures and tables
Table 1 manifest (p. 8); Table 3 execution sequences (p. 9); Table 4 GCP cluster (p. 11); Table 5 OpenWhisk tuning (p. 11); Fig. 5 and Table 6 control-plane overhead (p. 12); Table 7 response times (p. 13); Fig. 6 SSH key response by load (p. 14); Fig. 7 (p. 16); Fig. 8 failure probabilities (p. 16).

## What this source does not address
No edge setting, no heterogeneous edge/cloud placement, no deadline or QoS objective, no energy or cost model, and no workload-trace replay: Azure traces are cited only for summary statistics (mean, SCV). No cold-start duration distribution is reported, and no distribution family is fitted to the Azure traces. Arrival rates for "low/medium/high" load are not given. Workflow shapes are small (2-4 parallel tasks, one 4-function diamond), not general DAGs from production traces. Only OpenWhisk on Linux is tested (p. 18). For trace data see [[azure-functions-trace-2021]]; for cold-start modelling see [[cold-start]] and [[nguyen-2025-taming]].

## Focus: Duration, arrival and cold-start distributions and workflow shapes usable to parameterise a serverless simulator; evaluation method (plan Task 3) — 2026-10-13

**Carries Kernthesen 1, 2, 6, 8, 9, 12.**

### What this focus needs beyond the Kernthesen
1. Duration parameters (the only concrete distributional numbers): 2019 Azure mean about 0.7 s, SCV about 11.7 (p. 4; p. 2 says 11.4); 2021 Azure mean about 3 s, SCV about 30.6 (p. 4). The paper calls these "response times" on p. 4 but "average execution time" on p. 2, so treat them as per-invocation durations with unclear scope, not end-to-end latency.
2. Synthetic duration model: i.i.d. exponential task times with mean 1 (SCV 1) is the analytic reference (p. 15); empirical SSH-keygen durations come out close to it only at 15 workers over 3 AZs. Measured SSH job response (two parallel keygens, stock): median 939 ms, mean 1335 ms, p90 2887 ms (Table 7, p. 13), i.e. mean/median 1.42 and p90/mean 2.2.
3. Arrival process: Poisson sequence injected over 30 minutes (p. 14). Rates for low/medium/high load are NOT stated (Figs. 5-6 label only the three levels).
4. Cold start: no distribution or cold-start time is reported. The usable facts are qualitative: an action bundle (manifest plus code) is delivered once per cold start and the SCTP association is set up once at cold start (pp. 6, 8); part of the Azure duration variance is attributed to cold starts (p. 2). Control-plane overhead (not cold start): median 8-9 ms (3 AZ) vs 6 ms (1 AZ); p90 14-16 ms vs 9-15 ms (Table 6, p. 12; Iluvatar 2-2.5 ms median, 3-10 ms p90).
5. Workflow shapes: fork-join of width 2 (SSH keygen, Table 8, p. 14); width 4 (thumbnail: download, 4 sizes, upload, p. 15); serverless map-reduce word count (p. 15); 4-node diamond (Table 1, p. 8); N parallel 100 ms busy-wait tasks with per-task failure probability for reliability tests (p. 16).
6. Data anomaly: Table 7 word-count p90 (3039 ms stock, 1416 ms Raptor) is below the median (4126, 1920 ms), which is impossible for a true percentile (p. 13); do not use the word-count percentiles.

### Direct quotes (for the draft)
> "the 2019 Azure trace exhibits serverless function response times with a mean of approximately 0.7 seconds and a squared coefficient of variation of around 11.7, while the 2021 Azure trace exhibits mean response times of around 3 seconds and with a squared coefficient of variation of around 30.6." (p. 4)

> "generating a Poisson arrival sequence of job invocation requests that are injected into OpenWhisk over a period of 30 minutes." (p. 14)

> "under a high-availability deployment, Raptor reduces mean response times by approximately 35% relative to stock OpenWhisk." (p. 15)

### Examples & illustrations (for later drafting)
- Evaluation testbed: 21 GCP VMs in 3 AZs, 15 e2-small worker nodes (5 per AZ), 3 control nodes and 3 Kubernetes controllers; CouchDB with 5 shards replicated 3 times (p. 11, Table 4).
- Single-AZ (5 workers) vs 3-AZ (15 workers) comparison as a test of when independence assumptions hold (pp. 14-15).

### Boundary of this focus
Only mean/SCV for Azure durations and Poisson arrivals are usable as simulator inputs; cold-start times, arrival rates and DAG shapes beyond fork-join must come from other sources ([[azure-functions-trace-2021]], [[nguyen-2025-taming]]). Evaluation is a small real OpenWhisk testbed, not a simulator.

## Mentioned entities
- Software: [[raptor]], [[apache-openwhisk]]
- Datasets: [[azure-functions-trace-2021]]
- Concepts: [[speculative-execution]], [[heavy-tailed-function-durations]], [[cold-start]]

## Connections
- Builds on straggler mitigation by speculative execution: [[speculative-execution]].
- Supports the heavy-tail premise: [[heavy-tailed-function-durations]].
- Cites Azure trace statistics: [[azure-functions-trace-2021]].
- Cold-start mitigation on the same platform: [[nguyen-2025-taming]] (no stance asserted).
