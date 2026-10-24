---
title: "Schmid et al. 2025 — SeBS-Flow: Benchmarking Serverless Cloud Function Workflows"
type: source
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
bibkey: schmid-2025-sebs-flow
depth: standard
based_on: preprint
tags: [serverless, workflows, benchmark, dag, eurosys, testbed-reuse]
relations:
  - target: sebs-flow
    type: mentions
    confidence: extracted
    because: "The benchmark suite this paper introduces (Abstract, p. 1; Sec. 4, p. 5)."
  - target: platform-agnostic-workflow-model
    type: mentions
    confidence: extracted
    because: "Defines the WFD-net based model and JSON phase language (Secs. 3-4, pp. 4-5)."
  - target: azure-functions-trace-2021
    type: cites
    confidence: inferred
    because: "Uses an analysis of Azure Durable Functions production traces [49] (median 3 functions, 5.6 s) for representativeness (p. 7); that this is the same trace family as the 2021 Azure Functions trace page is an inference, not stated."
  - target: cold-start
    type: mentions
    confidence: extracted
    because: "Cold starts are a measured factor of critical-path slowdown on AWS and GCP (Table 5 and Sec. 7.3.2, p. 11)."
---

# SeBS-Flow: Benchmarking Serverless Cloud Function Workflows

## Bibliographic Details
Schmid, Larissa; Copik, Marcin; Calotoiu, Alexandru; Brandner, Laurin; Koziolek, Anne; Hoefler, Torsten. 2025. *SeBS-Flow: Benchmarking Serverless Cloud Function Workflows*. Proc. Twentieth European Conference on Computer Systems (EuroSys '25), Rotterdam, pp. 902-920. DOI 10.1145/3689031.3717465. Code: https://github.com/spcl/serverless-benchmarks ; artifact: https://github.com/spcl/sebs-flow-artifact.

> Page note: the PDF read is the author's accepted version (arXiv:2410.03480v3, 19 pp.). Page refs below are the printed page numbers of that file, not of the ACM Version of Record (pp. 902-920).

<!-- ERSCHLIESSUNG -->

## Section map

| Covered | Section | pp. |
|---|---|---|
| — | 1 Introduction; Table 1 (analysis of 72 workflow papers) | 1-2 |
| — | 2 Background: platforms (Table 2), pricing (Table 3), workflow nets | 2-3 |
| — | 3 Serverless Workflows Model (transitions, resource annotations) | 4 |
| ✓ F1 | 4 Workflows Benchmark Suite: JSON definition (4.1), transcription (4.2), suite (4.3) | 5-6 |
| ✓ F1 | 5 Benchmark Applications; Table 4 | 6-7 |
| — | 6 Evaluation of Workflow Model (expressiveness, overhead) | 8 |
| ✓ F1 | 7.1 Methodology | 9 |
| ✓ F1 | 7.2 RQ1 runtime (Fig. 7) | 9 |
| ✓ F1 | 7.3 RQ2 overhead sources, cold starts, Table 5, Figs. 8-13 | 9-12 |
| — | 7.4 RQ3 scientific workflows (1000Genome vs HPC) | 12 |
| — | 7.5 RQ4 pricing; 7.6 RQ5 evolution | 12-13 |
| — | 8 Related work; 9 Conclusions | 13-14 |

## Kernthesen

### 1. ⭐ There is no benchmark suite for serverless workflows, and the 72 surveyed papers evaluate on inconsistent workloads (pp. 1-2)
The authors examined 72 research papers on serverless workflows and found they use different applications, cover different workload classes and compare against different platforms (Table 1), so results cannot be compared. SeBS-Flow is offered as the first workflow benchmark suite to fix this.

### 2. Workflow platforms differ fundamentally in programming model, limiting portability (pp. 2-3)
AWS Step Functions is a static JSON state machine (max parallelism 40), Google Cloud Workflows a semi-dynamic JSON/YAML state machine (max parallelism 20), Azure Durable Functions a dynamic orchestrator-function model with unlimited parallelism (Table 2, p. 2). Billing also differs: per state transition on AWS/GCP, per orchestrator duration on Azure (Table 3, p. 3).

### 3. ⭐ The model is a workflow net with data (WFD-net), extended with coordinator transitions and resource annotations (pp. 3-4)
Function transitions are executed by the platform; coordinator transitions between phases model the orchestrator awaiting all functions of a phase (an AND-join) and scheduling the next. Data passing is annotated as object storage, NoSQL, invocation payload, transparent, or reference.

### 4. ⭐ Workflows are specified in a portable JSON language of six phase types (p. 5)
Phase types: task, map, loop, repeat, switch, parallel. `root` names the first phase, `states` holds the phases, `next` names the successor; each phase receives the previous function's output payload. Map parallelism is decided at runtime from the input array size (p. 5), i.e. fan-out is an input parameter, not part of the definition.

### 5. Platform-specific generators transcribe the JSON; new platforms need one interface (pp. 5-6, 14)
AWS loops use a map state configured for sequential traversal; GCP needs HTTP-POST states and a sub-workflow per map; Azure ships the JSON with the code and a generic orchestrator interprets it (Sec. 4.2). Conclusions (p. 14) state that benchmarks can be ported to other services by implementing a single transcription interface.

### 6. ⭐ Six application benchmarks plus four microbenchmarks cover the representative shapes (pp. 6-7)
Video Analysis, Trip Booking, MapReduce, ExCamera, Machine Learning, 1000Genomes; microbenchmarks: function chain, object-storage I/O, parallel sleep, selfish detour. Shapes and data volumes are in Table 4 (see focus block).

### 7. The suite is argued representative of real workflows (p. 7)
Citing Eismann et al. [27]: 72% of workflows are "small" (2-10 functions), 23% "medium" (11-1000), 4% "large"; four of the six benchmarks are small, two medium. Per the Azure Durable trace analysis [49]: 40% of workflows sequential, median 3 distinct functions, median execution 5.6 s.

### 8. The model expresses 53 of 58 judgeable workflows from the literature with no measurable overhead (p. 8)
14 of 72 papers gave too little detail. Orchestrator parsing overhead on Azure averaged 13.6 ms on 1000Genome (median runtime 3757.55 s).

### 9. ⭐ No platform is fastest overall; Azure is slowest for data-heavy/highly parallel workflows because of orchestration overhead (p. 9)
AWS fastest on three of six; GCP 1.55-1.97x slower than AWS on three; Azure slowest on Video, ExCamera and 1000Genome, with the largest variance (p. 9). Azure ExCamera overhead averaged 495.5 s vs a 13.5 s critical path (p. 9).

### 10. Overhead sources: storage I/O, parallel scheduling, return payload (pp. 10-11)
Azure overhead grows to about 149 s for a 128 MB download and 4.9 s for 1 MB (20 parallel functions, Fig. 9a); return-payload latency rises on Azure from 16 kB (Fig. 9b), but benchmarks return less than 1 MB (p. 11).

### 11. Critical-path differences come from CPU allocation and cold starts (p. 11)
Cold-start share is 38-100% on AWS/GCP vs 0.6-7.7% on Azure (Table 5); warm runs are up to 2.0x (GCP) and 4.5x (AWS) faster.

### 12. Serverless workflow services scale scientific workflows near-optimally but run far slower than HPC (p. 12)
1000Genome averages 457.7 s (GCP), 259.8 s (AWS) vs 7.7 s on the HPC node Ault; strong-scaling speedups 1.96/1.95 (AWS) for 10/20 jobs vs 5/10 jobs.

### 13. Orchestration cost can dominate for simple pipelines; price rankings differ per benchmark (p. 12)
Even the sequential Trip Booking pays notable state-transition cost; AWS function compute is 6.7x GCP's price; AWS state transitions cost 2.5x GCP's but need fewer states (Table 5: e.g. 1000Genome 26 vs 96).

## Figures and tables
Table 1 (p. 2) survey of 72 papers; Table 2 (p. 2) platform features; Table 3 (p. 3) pricing; Fig. 3 (p. 4) and Fig. 6 (p. 7) workflow nets (figures for the other benchmarks are in supplementary material, not in this PDF); Fig. 4 (p. 5) JSON definitions; Table 4 (p. 7) benchmark features; Fig. 7 (p. 9) runtimes; Fig. 8 (p. 10) critical path vs overhead; Table 5 (p. 11) cold starts and transitions; Fig. 11 (p. 12) scaling profiles; Fig. 15 (p. 14) prices.

## What this source does not address
No Kubernetes, OpenWhisk or edge platform is evaluated (only AWS, GCP, Azure cloud services); no per-function execution-time table (only workflow-level runtime and critical path); no workload arrival traces (bursts of 30 invocations only); no deadlines or placement. Figures for the other five benchmarks are in the supplementary material and the master thesis [5] (footnote, p. 5). Request-arrival and invocation-pattern characterisation belongs to trace papers such as [[azure-functions-trace-2021]], not here.

<!-- FOKUS -->

## Focus: Workflow DAG shapes of the benchmark applications (names, #functions, fan-out, depth), payload/state sizes, function durations, and reuse in a simulator and Kubernetes testbed — 2026-10-13

**Carries Kernthesen 4, 5, 6, 7, 9.**

### What this focus needs beyond the Kernthesen

#### Workflow shapes and sizes (Table 4, p. 7; parameters from Sec. 5, p. 7; memory from Sec. 7, Fig. 7 captions, p. 9)

| Benchmark | #functions | Parallelism (max fan-out) | Critical path | Download MB | Upload MB | Configured parameters | Memory |
|---|---|---|---|---|---|---|---|
| Video Analysis | 4 | 2 | 3 | 238.83 | 7.48 | F=10 frames, B=5 -> N=2 detect | 2048 MB |
| Trip Booking | 7 | 1 | 4/7 | 0.0 | 0.0 | failure injected in last confirm, then 3 reverse functions | 128 MB |
| MapReduce | 9 | 5 | 4 | 0.02 | 0.04 | N=3 mappers, W=5000 words, M=5 reducers | 256 MB |
| ExCamera | 16 | 5 | 6 | 302.07 | 17.49 | M=30 frames, chunk N=6 -> 5 parallel | 256 MB |
| Machine Learning | 3 | 2 | 2 | 7.82 | 3.91 | N=500 samples, M=1024 features, K=2 classifiers | 1024 MB |
| 1000Genome | 19 | 12 | 4 | 273.54 | 3.47 | M=1250 lines, N=5 individuals, P=6 populations | 2048 MB |

Structures (p. 7): Video = decode -> N x detect (map) -> acc (Fig. 6). Trip Booking = sequential pipeline with SAGA compensation (critical path "4/7", read here as 4 on the success path and 7 when failure triggers the three reversals; the paper does not spell out the slash). MapReduce = split -> N map -> shuffle -> M reduce. ExCamera = chunked encode/decode/re-encode with interdependent tasks. ML = gen -> K parallel train. 1000Genome = individuals (N) -> individuals_merge + sifting -> mutation_overlap and frequency (each per population P), three phases. Maximum depth is 6 (ExCamera); every graph is composed of task/map/parallel/switch phases, i.e. series-parallel; maximum fan-out 12. Per-function DAG edge lists are not tabulated in this PDF.

Note: "Download/Upload" are per workflow execution, I read them as total object-storage volume (inferred; the table does not define the columns).

#### Runtime and durations (Fig. 7, p. 9; Fig. 8, p. 10)
Workflow runtime in seconds as annotated in Fig. 7 (GCP / AWS / Azure; the statistic is not named in the caption; burst of 30): Video 55.69 / 26.74 / 642.12; ExCamera 132.63 / 87.11 / 550.38; MapReduce 19.44 / 11.19 / 8.64; Trip Booking 9.19 / 16.14 / 8.51; ML 15.32 / 10.05 / 6.67; 1000Genome 453.63 / 257.14 / 3757.55 (the text calls the last value the median, p. 8; p. 12 gives means of 457.7 s GCP, 259.8 s AWS). The paper reports no per-function durations. Critical path T_C is the sum over phases of the maximum function runtime in the phase (p. 9); overhead T_O = runtime minus T_C. Azure ExCamera: T_C 13.5 s, overhead 495.5 s (p. 9). Warm-only critical paths are up to 2.0x (GCP) and 4.5x (AWS) shorter than cold-inclusive ones (p. 11). Workflows are short (about 7 s to 4.5 min on AWS) except 1000Genome on Azure (about 1 h).

#### Payload and state sizes
Inter-function data is split by channel: large objects via object storage (Download/Upload columns), small state via NoSQL (Trip Booking: 3 inserts + 3 deletes, items "at most a few hundred bytes", p. 12), and returned payloads below 1 MB for all benchmarks (p. 11). The payload microbenchmark covers 2^5 to 2^18 bytes (Fig. 9b, p. 10); the storage microbenchmark 2^10 to 2^28 bytes (Fig. 9a).

#### What is needed to reuse the workflows in a simulator and a Kubernetes testbed
1. **Repo and definition format.** Code in the SeBS repository (https://github.com/spcl/serverless-benchmarks); experiment artifact https://github.com/spcl/sebs-flow-artifact (p. 1). Workflows are platform-agnostic JSON (phases task/map/loop/repeat/switch/parallel with `root`, `states`, `next`, `func_name`, `array`; Sec. 4.1, p. 5); function code in Python, Node.js, C++ or Java (p. 6). The JSON is directly parseable into a DAG for a simulator.
2. **The DAG needs a parameter instantiation.** Map fan-out derives from the runtime input array size (p. 5), so a simulator must fix N per benchmark (values in the table).
3. **Durations and payloads must be measured or taken from the artifact.** No per-function runtimes or per-edge payload bytes are tabulated; only workflow-level runtime/critical path (Figs. 7-8) and total download/upload (Table 4). Each function logs start/end timestamps, requestID and containerID to Redis (p. 6), so raw per-function data should exist in the artifact (not verified here).
4. **Kubernetes/OpenWhisk is not supported out of the box.** Backends are AWS, Google Cloud, Azure (pp. 2, 9); porting needs one new transcription interface (pp. 6, 14). The suite depends on cloud object storage and NoSQL (DynamoDB, CosmosDB, Firestore; p. 6), which a K8s testbed would have to replace (for example an S3-compatible store and a key-value store; my suggestion, not the paper's). Orchestration (the coordinator) would be supplied by the testbed's own scheduler.
5. **Model fit.** Functions of a phase run in parallel and the coordinator is an AND-join between phases (p. 4), i.e. level-synchronous execution; finer cross-phase dependencies are not expressible, so a per-edge DAG model is a superset.

### Direct quotes (for the draft)
> "The level of parallelism is then decided dynamically at runtime depending on the size of the given array." (p. 5)

> "four of six applications can be classified as “small” and two more as “medium.”" (p. 7)

> "We used 𝐹= 10 frames and batch size 𝐵= 5, yielding two parallel functions in the map phase." (p. 7)

### Examples & illustrations (for later drafting)
- Video Analysis as the worked example of a map-based fan-out DAG (decode -> N detect -> acc), Fig. 6 (p. 7).
- Trip Booking SAGA with injected failure followed by three reversal functions: a conditional path with critical path 4 vs 7 (p. 7).
- 1000Genome as the widest graph (12-way parallelism, 19 functions) and the longest-running (median 3757.55 s on Azure, p. 8).

### Boundary of this focus
Per-function service times, per-edge payload bytes and request arrival patterns are not given; the suite targets commercial cloud workflow services, not edge or Kubernetes. Applications carry no deadlines.

## Mentioned entities
- Software: [[sebs-flow]], [[apache-openwhisk]]
- Datasets: [[azure-functions-trace-2021]]
- Concepts: [[platform-agnostic-workflow-model]], [[cold-start]]

## Connections
- Cites an Azure Durable production-trace analysis for representativeness; related to [[azure-functions-trace-2021]] (typed in `relations:`, inferred).
- Provides the candidate workflow set (shapes above) for the simulator and testbed experiments of this project.
