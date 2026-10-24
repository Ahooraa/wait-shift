---
title: "Shahrad et al. 2020 — Serverless in the Wild"
type: source
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
bibkey: shahrad-2020-serverless-wild
depth: standard
tags: [serverless, workload-characterization, cold-start, keep-alive, azure-functions-trace]
relations:
  - target: azure-functions-trace-2019
    type: builds-on
    confidence: extracted
    because: "Characterizes the 14-day Azure Functions workload (15-28 July 2019) and releases a sanitized subset (p. 207)."
  - target: hybrid-histogram-keep-alive-policy
    type: supports
    confidence: extracted
    because: "Proposes and evaluates this policy (Sec. 4-5, pp. 210-215)."
  - target: cold-start
    type: builds-on
    confidence: extracted
    because: "Goal is reducing the number of cold starts, orthogonal to making each cheaper (p. 206)."
  - target: apache-openwhisk
    type: builds-on
    confidence: extracted
    because: "Implements the policy in OpenWhisk's Controller/Invoker (Sec. 4.3, pp. 212-213)."
  - target: azure-functions-trace-2021
    type: mentions
    confidence: inferred
    because: "A different, later Azure trace; not mentioned in this paper (it predates it)."
---

# Serverless in the Wild: Characterizing and Optimizing the Serverless Workload at a Large Cloud Provider

## Bibliographic Details
Shahrad, M., Fonseca, R., Goiri, I., Chaudhry, G., Batum, P., Cooke, J., Laureano, E., Tresness, C., Russinovich, M., Bianchini, R. 2020. *Serverless in the Wild: Characterizing and Optimizing the Serverless Workload at a Large Cloud Provider*. USENIX ATC 2020, pp. 205-218. https://www.usenix.org/conference/atc20/presentation/shahrad. Page numbers below are the printed USENIX pages (PDF page n = printed 203+n). Identity of the PDF confirmed from its first page (title, authors, ATC 2020 proceedings).

## Section map

| Covered | Section | pp. |
|---|---|---|
| — | 1 Introduction | 205-206 |
| ✓ F1 | 2 Background (triggers, applications as scheduling unit, cold starts, fixed keep-alive) | 206-207 |
| ✓ F1 | 3.1 Data collection (four datasets, limitations) | 207 |
| ✓ F1 | 3.2 Functions, applications, triggers | 207-208 |
| ✓ F1 | 3.3 Invocation patterns (diurnal, skew, IAT CV) | 208-209 |
| ✓ F1 | 3.4 Function execution times (log-normal fit) | 209 |
| ✓ F1 | 3.5 Memory usage (Burr fit) | 209-210 |
| ✓ F1 | 3.6 Main takeaways | 210 |
| ✓ F1 | 4.1 Design challenges | 210-211 |
| ✓ F1 | 4.2 Hybrid histogram policy | 211-212 |
| — | 4.3 Implementation in Apache OpenWhisk | 212-213 |
| ✓ F1 | 5.1 Methodology (simulator, workloads) | 213 |
| ✓ F1 | 5.2 Simulation results | 213-215 |
| — | 5.3 Experimental results, policy overhead | 215 |
| ✓ F1 | 6 Production implementation in Azure Functions | 215-216 |
| — | 7 Related work, 8 Conclusion | 216 |

## Kernthesen

### 1. ⭐ Invocation frequency spans eight orders of magnitude and is extremely skewed (p. 208)
Daily invocations per function/application vary by over 8 orders of magnitude (Fig. 5a). 45% of applications are invoked at most once per hour and 81% at most once per minute on average; the 18.6% most popular applications (at least once per minute) produce 99.6% of invocations (Fig. 5b). Keeping the rarely invoked majority warm is therefore costly relative to their billable time.

### 2. ⭐ Triggers are heterogeneous and determine predictability (pp. 207-208)
HTTP is the largest class (55.0% of functions, 35.9% of invocations); queue 15.2%/33.5%; event 2.2%/24.7%; timer 15.6%/2.0%; orchestration 6.9%/2.3%; storage 2.8%/0.7%; others 2.2%/1.0% (Fig. 2). 64.07% of apps have at least one HTTP trigger, 29.15% at least one timer; 43.27% are HTTP-only, 13.36% timer-only (Fig. 3). 95% of timer functions fire at most once per minute on average. 86% of apps have no timers or timers combined with other triggers, so timer predictability does not carry over to most apps.

### 3. ⭐ Arrivals are neither periodic nor Poisson (p. 209)
The CV of inter-arrival times is 0 for only about 50% of timer-only apps, under 30% of apps with at least one timer and about 20% of all apps; about 10% of non-timer apps have CV near 0 (periodic external callers); only a small fraction has CV near 1. 40% of apps have IAT CV above 1 (p. 210).

### 4. Platform load shows diurnal and weekly patterns over a flat baseline (p. 208)
Hourly invocations (Fig. 4) show clear day/night and weekday/weekend cycles and a constant baseline of roughly 50% of the peak.

### 5. ⭐ Execution times are short and log-normal (p. 209)
50% of functions average under 1 s; 50% have maximum under about 3 s; 90% have maximum at most 60 s; 96% average under 60 s; 75% have maximum at most 10 s (p. 210). The average-time distribution fits a log-normal (MLE) with log mean -0.38 and sigma 2.36 (Fig. 7). Median averages differ by about 10x across triggers (200 ms to 2 s); orchestration functions are an outlier at about 30 ms.

### 6. ⭐ Memory is per application, with a 4x spread across 90% of apps (pp. 209-210)
The application is the unit of allocation. Maximum allocated memory: 50% of apps at most 170 MB, 90% at most 400 MB. The average allocated memory fits a Burr distribution with c = 11.652, k = 0.221, lambda = 107.083 (Fig. 8). No strong correlation between invocation frequency and memory, or memory and execution time (p. 210).

### 7. Execution time is far below inter-arrival time, so idle time approximates IAT (p. 209)
For most apps the average execution time is at least two orders of magnitude below the average IAT; for the 81% invoked at most once per minute, idle-time and IAT distributions are nearly identical.

### 8. Fixed keep-alive is a poor one-size-fits-all policy (pp. 206, 213-214)
AWS and Azure retain for 10 and 20 minutes; OpenWhisk 10 minutes. In simulation the 75th-percentile app has cold starts 50.3% of the time at 10 minutes and 25% at 1 hour; about 3.5% of apps are 100% cold even with no unloading (single invocation in the week).

### 9. ⭐ The hybrid histogram policy sets per-app pre-warm and keep-alive windows (pp. 210-212)
Per app, a range-limited histogram of idle times (1-minute bins, e.g. 4-hour range, out-of-bound ITs counted separately) gives the pre-warming window (5th percentile, reduced by a 10% margin) and keep-alive window (99th percentile, increased by 10%). See [[hybrid-histogram-keep-alive-policy]].

### 10. ⭐ A representativeness check and an ARIMA fallback handle what the histogram cannot (p. 212)
If the CV of the bin counts is below a threshold (default 2) the policy reverts to standard keep-alive; if too many ITs are out of bounds it forecasts the next IT with ARIMA (15% margin).

### 11. Gains over fixed keep-alive (pp. 213-215)
The 10-min fixed policy has about 2.5x more cold starts at the 75th percentile than the 4-hour histogram at equal memory; fixed 2-hour matches the 4-hour histogram's cold starts at about 50% more memory. Cutoffs [5,99] cut wasted memory 15% versus [0,100]. ARIMA handled 0.64% of invocations, used by 9.3% of apps, halving always-cold apps (10.5% to 5.2%). OpenWhisk (19 VMs, 68 apps, 8 h, 12,383 invocations): container memory down 15.6% (p. 215).

### 12. ⭐ Production implementation is cheap and asynchronous (pp. 215-216)
960 bytes per app (240 integers), hourly backup, a new histogram per day, histograms older than 2 weeks removed; pre-warm event scheduled 90 seconds early; all decisions off the critical path.

## Figures and tables
Fig. 1 functions per app (p. 207); Fig. 2 trigger table (p. 207); Fig. 3 trigger combinations (p. 208); Fig. 4 hourly load (p. 208); Fig. 5 daily invocations and popularity skew (p. 208); Fig. 6 IAT CV (p. 209); Fig. 7 execution time CDF with log-normal fit (p. 209); Fig. 8 memory CDF with Burr fit (p. 210); Figs. 9-12 policy timelines and histograms (pp. 211-212); Figs. 14-20 evaluation (pp. 213-215).

## What this source does not address
No workflow/DAG structure or inter-function dependencies (functions are independent; only Durable Functions orchestration is labelled as a trigger class); no edge or cloud-edge setting; no deadlines or latency classes; no cold-start duration model (deferred to Wang et al. 2018, p. 209); no absolute totals (confidential, p. 207); sub-minute inter-arrival times are not reconstructible (1-minute bins, p. 207); the execution-time distribution is approximated from weighted percentiles of per-interval averages. Burst-driven cold starts from concurrency spikes are excluded (<1% of apps, p. 206). The later 2021 trace is covered by [[azure-functions-trace-2021]].

## Focus: Simulator workload distributions (duration, arrival, memory) and hybrid-histogram keep-alive trigger logic for D1 — 2026-10-13

**Carries Kernthesen 1, 2, 3, 5, 6, 7, 9, 10, 12.**

### What this focus needs beyond the Kernthesen
1. Sampling recipe for a synthetic app population: daily rate from the skewed distribution (Kernthese 1), trigger class from Figs. 2-3, IAT CV from Fig. 6 (timer-only about 50% at CV 0; 40% of apps above 1), execution time log-normal(mu = -0.38, sigma = 2.36) in log-seconds (p. 209), memory Burr(c = 11.652, k = 0.221, lambda = 107.083) in MB (p. 209). Time unit of the log-normal fit is inferred as seconds from the Fig. 7 axis; verify against the released dataset.
2. Re-decision logic (D1): the policy re-decides per application on every invocation, when an execution ends (state executing to idle). In OpenWhisk the Load Balancer updates keep-alive and pre-warm parameters after each invocation (p. 213); in Azure the aggregated histogram is read when the app goes idle and a pre-warm event is scheduled (pp. 215-216). The decision is invocation-driven, not periodic.
3. Regime switching: histogram representativeness (CV of bin counts, Welford online, default threshold 2) decides histogram versus standard keep-alive (pre-warm 0, keep-alive = histogram range); the share of out-of-bound ITs decides ARIMA (p. 212). Staleness is handled by a daily histogram and 2-week retention in production (p. 215); weighted use of daily histograms is proposed, not implemented.
4. The policy reacts to observed idle-time distributions only; it has no cost, deadline or load signal and no explicit drift trigger beyond the CV check.

### Direct quotes (for the draft)
> "Researchers can use the distributions of the workload characteristics we study to create realistic traces for their work." (p. 205)
> "The application, not the function, is the unit of scheduling and resource allocation." (p. 206)
> "our dataset does not allow the precise reconstruction of inter-arrival times that are smaller than one minute." (p. 207)
> "We decide whether a histogram is representative by computing the CV of its bin counts." (p. 212)

### Examples & illustrations (for later drafting)
- Four applications with over 1k functions each, auto-generated names, timer or HTTP triggered, apparently large automated tests (p. 207).
- Fig. 12: nine real IT histograms; left column sharp head and tail, centre column head rounds to 0, right column widely spread (pp. 211-212).
- ARIMA worked example: predicted IT 5 h gives pre-warm 4.25 h and keep-alive 1.5 h (p. 212).

### Boundary of this focus
Simulator inputs and keep-alive trigger logic only. Cold-start percentages are recorded as context, not as a baseline to reproduce.

## Mentioned entities
- Datasets: [[azure-functions-trace-2019]], [[azure-functions-trace-2021]]
- Platforms: [[apache-openwhisk]]
- Concepts: [[hybrid-histogram-keep-alive-policy]], [[cold-start]], [[azure-functions-workload-distributions]]

## Connections
- Implements its policy in: [[apache-openwhisk]] (Controller and Invoker).
- Documents the dataset: [[azure-functions-trace-2019]].
- Proposes: [[hybrid-histogram-keep-alive-policy]].
- Reduces the number of events defined in [[cold-start]].
