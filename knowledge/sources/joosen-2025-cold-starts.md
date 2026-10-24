---
title: "Joosen et al. 2025 — Serverless Cold Starts and Where to Find Them"
type: source
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
bibkey: joosen-2025-cold-starts
depth: standard
based_on: preprint
tags: [serverless, cold-start, trace, huawei, simulator-inputs]
relations:
  - target: cold-start
    type: builds-on
    confidence: extracted
    because: "Component-level production analysis of cold starts: pod allocation, code deploy, dependency deploy, scheduling (p. 8, Sec. 4.2)."
  - target: huawei-public-trace-2025
    type: mentions
    confidence: extracted
    because: "Documents and releases the dataset (p. 1 fn. 1, Table 1 p. 2)."
  - target: keep-alive-time
    type: builds-on
    confidence: extracted
    because: "Default keep-alive of one minute on the platform; timer functions with period above 1 min cold-start on every call (pp. 3, 10)."
  - target: pod-utility-ratio
    type: builds-on
    confidence: extracted
    because: "Introduces the metric (Sec. 4.5, p. 11)."
  - target: cold-start-time-model
    type: supports
    confidence: extracted
    because: "Supplies the LogNormal/Weibull fits offered for simulation (p. 8, Sec. 4.1)."
---

# Serverless Cold Starts and Where to Find Them

## Bibliographic Details
Joosen, A., Hassan, A., Asenov, M., Singh, R., Darlow, L., Wang, J., Deng, Q., Barker, A. 2025. *Serverless Cold Starts and Where to Find Them*. EuroSys '25, Rotterdam, 30 Mar - 3 Apr 2025. arXiv:2410.06145. The library PDF is the arXiv v1 preprint (8 Oct 2024, marked "preprint" in the page headers); page numbers below are its printed pages (1-16). Data: https://github.com/sir-lab/data-release (p. 1, fn. 1).

## Section map

| Covered | Section | pp. |
|---|---|---|
| ✓ F1 | 1 Introduction (31 days, five regions, 85 billion requests, 11.9 million cold starts) | 1-2 |
| ✓ F1 | 2.1 Platform and dataset (YuanRong, Table 1 fields) | 2-3 |
| ✓ F1 | 2.2 Cold starts in the system (pod life cycle, pools, keep-alive) | 3 |
| ✓ F1 | 3.1 Region statistics (requests per function, execution time, CPU, users) | 3-4 |
| ✓ F1 | 3.2 Peak time analysis (peak lags, peak-to-trough, holidays) | 4-6 |
| ✓ F1 | 3.3 Runtimes and trigger types (periodicity of pods) | 6-8 |
| ✓ F1 | 4.1 Cold start distributions (LogNormal, Weibull fits) | 8 |
| ✓ F1 | 4.2 Components of cold start times (hourly series, Spearman, small vs large pools) | 8-10 |
| ✓ F1 | 4.3 Which functions cause the most cold starts (Region 2) | 10-11 |
| ✓ F1 | 4.4 Runtime language and trigger type vs cold start time | 11 |
| ✓ F1 | 4.5 Real cost of cold starts (pod utility ratio) | 11-13 |
| - | 5 Discussion and open problems | 13-14 |
| - | 6 Related work, 7 Conclusion | 14 |

## Kernthesen

### 1. Cold start data from production were previously aggregate only; this is a per-event multi-region release (pp. 1-2)
The authors argue that earlier production data (Shahrad 2020, Joosen 2023) offered only aggregate cold-start statistics, mostly from a single region. They release event-level request, pod and function tables from five Huawei Cloud regions (20 clusters), 31 days, 85 billion requests, over 12 million pods and over 11 million cold starts (11.9 million in the abstract) (pp. 1, 2).

### 2. ⭐ Cold start has four logged components (pp. 3, 8)
Pod allocation (take a pod from the resource pool, or start one if none is free), deploy code (download, extract, deploy), deploy dependencies (zero for functions without layers) and scheduling (networking, routing, scheduling overhead). They add up to total cold start time (p. 8).

### 3. ⭐ Pod life cycle and keep-alive are fixed at one minute (pp. 3, 10)
Pods come from pre-created pools per CPU-memory configuration (smallest 300 millicores / 128 MB, largest 26 cores / 32 GB, p. 10), receive code and dependencies, serve, then wait for a keep-alive of one minute by default, reset on each request; otherwise the pod is deleted (p. 3).

### 4. ⭐ Cold start durations are long-tailed, regional medians 0.1-2 s; a LogNormal fit is offered for simulation (p. 8)
Pooled over all regions the cold start time is fitted by a LogNormal with mean 3.24 and standard deviation 7.10, and inter-arrival times between cold starts by a Weibull with mean 1.25 and standard deviation 3.66 (Fig. 10 caption, p. 8). The authors recommend the fits for simulation experiments. The text does not say whether the numbers are moments of the distribution or parameters of the underlying normal (see focus block).

### 5. ⭐ Regions differ by orders of magnitude and by profile (pp. 3-4)
Median requests per function, execution time and CPU usage differ between regions by factors of up to 50, 25 and 3 (p. 4). About 20% of functions in Region 1 get at least one request per minute on average versus about 1% in Region 4. Median execution time ranges from 4 ms (R5) to 100 ms (R1); executions can last tens or hundreds of seconds (p. 3).

### 6. ⭐ Arrivals are periodic and bursty (pp. 4-6)
All regions show clear daily periodicity, with the daily peak at a different time of day per region (Fig. 5, p. 4-5). Per-function peak-to-trough ratios range from below 2 to over 1000, the largest workloads stay below 60, and functions with fewer than 1440 requests/day have ratio close to 1 (p. 5).

### 7. ⭐ Two distinct sources of cold starts (pp. 5, 10)
High cold start counts come either from high-fluctuation workloads (frequent autoscaling) or from many functions invoked with a period just above the 1-minute keep-alive (p. 5). Most functions are invoked rarely and cold-start on nearly every request, mostly timer functions (p. 10).

### 8. Trigger and runtime mix shape pods and cold starts (pp. 6-7, 10)
Timers are 42% of triggers, APIG-S 23%, APIG-S+TIMER-A 13% (p. 6). In Region 2 timers are almost 60% of functions, 30% of cold starts and 5% of running pods; Python3 is almost 50% of cold starts; small CPU-memory configurations over 60% of cold starts (p. 10). Weekdays carry about 30% more pods than weekends (p. 7).

### 9. ⭐ Pool size and runtime change the cold start time (pp. 10-11)
Larger pools have longer median cold starts, ratio from about 1:1 (R5) to 5:1 (R3) (p. 10); the summary box says 2-5x (p. 11). Pod allocation time is multimodal because the pool search expands in stages (p. 10). Custom runtimes have no pool and HTTP needs a server start; both have median above 10 s, while most other runtimes are below 1 s with a long tail (p. 11). OBS-triggered functions have median about 10 s because they are mostly Custom runtimes (p. 11).

### 10. Dominant components vary by region and time (pp. 8-9, 13)
Mean cold start time ranges from 3 s in R1 (dominated by dependency deployment and scheduling, abstract) to under 0.3 s in R3 (p. 9); Region 2 is dominated by pod allocation, which oscillates in phase with the number of cold starts (p. 9). Scheduling delay is the first or second component everywhere except briefly in R1 (p. 13).

### 11. ⭐ Pod utility ratio (p. 11)
Utility ratio = (pod lifetime minus 1 min keep-alive) / cold start time. In Region 2, 20% of pods have ratio below 1, the median is about 4, 35% of Go pods exceed 100, about 40% of Node.js pods are below 1, and timers have the lowest ratios (p. 11).

### 12. Holiday effect (pp. 5-6, 9)
During a week-long holiday pods and CPU fall; Regions 1, 2, 4, 5 show a pre-holiday rush and a post-holiday catch-up with more and slower cold starts; Region 3 behaves differently (p. 6, p. 9).

### 13. Open problems the authors name (pp. 13-14)
Cross-region scheduling, scheduling delay, peak shaving for asynchronous calls (roughly 60% of functions are asynchronous, p. 13), dynamic keep-alive for timers, prediction of workflow calls (workflows 20% of cold starts, p. 13), concurrency adjustment and resource pool prediction (p. 13-14).

## Figures and tables
- Table 1 (p. 2): fields of request, pod and function tables.
- Fig. 3 (p. 4): CDFs of requests per day, execution time, CPU per region. Fig. 5 (p. 5): normalised peaks. Fig. 6 (p. 5): peak-to-trough scatter.
- Fig. 10 (p. 8): cold start and inter-arrival CDFs with fits. Fig. 11 (p. 9): hourly component series. Fig. 13 (p. 10): small vs large pool violins. Figs. 15-16 (p. 12): by runtime and trigger. Fig. 17 (p. 12): utility ratio.

## What this source does not address
No DAG or workflow structure beyond a "workflow" trigger, no per-region fitted parameters (only one pooled LogNormal and one pooled Weibull), no prediction or scheduling algorithm (directions only, pp. 13-14), no edge or heterogeneous-node setting, no monetary cost. Earlier aggregate statistics are in Shahrad 2020 (Azure; no page yet); long-term trends in Joosen 2023 (their ref. [18], no page).

## Focus: Duration, arrival and cold-start distributions for the simulator — 2026-10-13

**Carries Kernthesen 2, 3, 4, 5, 6, 7, 9, 11.**

### What this focus needs beyond the Kernthesen
1. Stated fit parameters: cold start time LogNormal mean 3.24, sd 7.10; inter-arrival of cold starts Weibull mean 1.25, sd 3.66; both pooled over all regions, seconds (Fig. 10 caption, p. 8).
2. Interpretation (reviewer calculation, not in the paper): if 3.24 and 7.10 are moments, the LogNormal has mu = 0.296, sigma = 1.326 (median 1.35 s). If they were the underlying normal's parameters, the median would be about 25 s, contradicting the 0.1-2 s regional medians (p. 8), so moments is the consistent reading. The Weibull moments imply shape about 0.42 and scale about 0.42 s (CV 2.9, heavy-tailed, bursty cold start arrivals). Verify against the released data before relying on them.
3. Cold start median by region 0.1-2 s (p. 8); mean from about 3 s (R1) to below 0.3 s (R3) (p. 9). Cold start inter-arrival median from 0.1 s (R1) to several seconds (R3) (p. 8).
4. Execution time (request level): median 4 ms (R5) to 100 ms (R1), tails of tens to hundreds of seconds; CPU median about 0.1-0.3 cores (p. 3; the text says "Region 3" twice, a typo).
5. Cold start fraction: functions below 1 request/min cold-start on about every call; above 1/min far fewer (p. 10, Fig. 14). No global cold-start-per-request fraction is given; workflow (synchronous) triggers cause 20% of cold starts (p. 13).
6. Trace tables (Table 1, p. 2). Request level (5 regions, 31 days): timestamp (ms), pod ID, cluster name, function name, user ID, request ID (all hashed), execution time (microseconds), CPU usage (millicores), memory usage (bytes). Pod level (5 regions, 31 days): timestamp (ms), pod ID, cluster, function, user, total cold start time and pod allocation, deploy code, deploy dependency, scheduling times (microseconds). Function level (listed as 1 region in Table 1, while the text analyses Region 2 triggers and runtimes, p. 6): hashed function name, runtime, trigger type, CPU-MEM config. Check this inconsistency against the data release.

### Direct quotes (for the draft)
> "Cold start times can be approximated with a LogNormal distribution, while inter-arrival times can be approximated with a Weibull distribution" (p. 8)

> "researchers working on problems related to cold start time optimizations can use these fits to run simulation experiments for cold start optimizations." (p. 8)

> "Large peak-to-trough ratios indicate a function with large bursts of invocations." (p. 5)

> "A 1:1 ratio or less means that the pod is used for a time less than or equal to its cold start time." (p. 11)

### Examples & illustrations (for later drafting)
- Custom runtime: no reserved pool, pods created from scratch each time; median cold start above 10 s, nearly all pod allocation (pp. 11, 14).
- Timer functions with period above 1 min and a 1-min keep-alive cold-start on every invocation (pp. 10-11).

### Boundary of this focus
Gives pooled and qualitative per-region distributions and one pooled pair of fits; there are no fitted execution time distributions and no per-runtime parameter tables, so those must be fitted from the released data.

## Mentioned entities
- Datasets: [[huawei-public-trace-2025]]
- Concepts: [[cold-start]], [[cold-start-time-model]], [[keep-alive-time]], [[pod-utility-ratio]]

## Connections
- Builds on: [[cold-start]] (adds component breakdown and production distributions).
- Supplies simulator inputs: [[cold-start-time-model]].
- Complements: [[azure-functions-trace-2021]] (another public trace, aggregate only).
