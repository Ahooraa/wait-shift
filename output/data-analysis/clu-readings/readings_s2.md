### R5. Node count (nominal load 0.5 per node, no peak cap)

Geometric-mean ratio CLU / system over the 12 cells (4 applications x seeds 1-3) of a node count, bootstrap 95% CI (10,000 resamples). Below 1: CLU is lower. 'n/12' counts cells where CLU is lower. The 10-node row is the load-0.5 cell without a peak cap of Stage 1 (ML and MapReduce own runs; Video and ExCamera the live twin).




**P99 makespan**

| Condition | vs F6 | vs Heu | vs B* | vs RL |
|---|---|---|---|---|
| 10 nodes (load 0.5, no cap) | 2.36 [1.34, 4.23]; 1/12 | 0.82 [0.48, 1.29]; 4/12 | 0.66 [0.40, 1.08]; 8/12 | 0.90 [0.37, 1.97]; 5/12 |
| 20 nodes | 2.45 [1.54, 4.12]; 1/12 | 0.92 [0.61, 1.33]; 5/12 | 0.59 [0.40, 0.86]; 9/12 | 0.44 [0.11, 1.49]; 8/12 |
| 40 nodes | 2.67 [1.62, 4.45]; 1/12 | 0.85 [0.45, 1.52]; 5/12 | 0.43 [0.24, 0.68]; 12/12 | 0.44 [0.09, 1.84]; 7/12 |

**average makespan**

| Condition | vs F6 | vs Heu | vs B* | vs RL |
|---|---|---|---|---|
| 10 nodes (load 0.5, no cap) | 1.76 [1.20, 2.76]; 1/12 | 1.02 [0.73, 1.42]; 3/12 | 0.70 [0.47, 1.03]; 9/12 | 0.77 [0.33, 1.50]; 7/12 |
| 20 nodes | 1.70 [1.21, 2.59]; 1/12 | 1.03 [0.76, 1.39]; 3/12 | 0.60 [0.42, 0.85]; 10/12 | 0.56 [0.18, 1.35]; 8/12 |
| 40 nodes | 1.68 [1.22, 2.48]; 2/12 | 0.99 [0.69, 1.40]; 4/12 | 0.44 [0.29, 0.63]; 12/12 | 0.47 [0.16, 1.20]; 7/12 |

**P99 makespan per application (mean of seeds 1-3, s)**


10 nodes (load 0.5, no cap)

| App | CLU | F6 | Heu | B* | RL | lowest |
|---|---|---|---|---|---|---|
| ML | 5.29 | 2.85 | 21.93 | 20.35 | 158.69 | F6 |
| MapReduce | 37.21 | 3.35 | 23.36 | 19.13 | 10.33 | F6 |
| Video | 41.14 | 29.77 | 33.23 | 90.29 | 69.78 | F6 |
| ExCamera | 170.66 | 102.75 | 158.16 | 175.25 | 148.14 | F6 |

20 nodes

| App | CLU | F6 | Heu | B* | RL | lowest |
|---|---|---|---|---|---|---|
| ML | 5.56 | 3.10 | 18.27 | 20.99 | 537.37 | F6 |
| MapReduce | 38.72 | 3.60 | 21.36 | 27.00 | 11.26 | F6 |
| Video | 45.56 | 30.68 | 34.71 | 91.25 | 88.65 | F6 |
| ExCamera | 175.74 | 110.13 | 201.60 | 244.91 | 157.05 | F6 |

40 nodes

| App | CLU | F6 | Heu | B* | RL | lowest |
|---|---|---|---|---|---|---|
| ML | 4.48 | 2.94 | 20.45 | 36.28 | 633.47 | F6 |
| MapReduce | 38.56 | 3.90 | 25.01 | 49.74 | 5.03 | F6 |
| Video | 91.21 | 29.78 | 35.89 | 119.37 | 108.46 | F6 |
| ExCamera | 174.80 | 105.94 | 429.30 | 288.94 | 148.72 | F6 |

**Average makespan per application (mean of seeds 1-3, s)**


10 nodes (load 0.5, no cap)

| App | CLU | F6 | Heu | B* | RL | lowest |
|---|---|---|---|---|---|---|
| ML | 1.25 | 0.88 | 2.88 | 5.42 | 39.46 | F6 |
| MapReduce | 8.71 | 1.31 | 3.68 | 5.48 | 2.70 | F6 |
| Video | 25.27 | 23.98 | 23.53 | 37.10 | 27.89 | Heu |
| ExCamera | 117.65 | 85.62 | 100.28 | 108.93 | 102.67 | F6 |

20 nodes

| App | CLU | F6 | Heu | B* | RL | lowest |
|---|---|---|---|---|---|---|
| ML | 1.27 | 0.96 | 2.73 | 5.19 | 43.80 | F6 |
| MapReduce | 8.07 | 1.39 | 3.64 | 7.18 | 2.66 | F6 |
| Video | 26.60 | 23.98 | 23.60 | 40.03 | 33.13 | Heu |
| ExCamera | 111.80 | 86.69 | 104.59 | 127.37 | 106.41 | F6 |

40 nodes

| App | CLU | F6 | Heu | B* | RL | lowest |
|---|---|---|---|---|---|---|
| ML | 1.06 | 0.94 | 2.82 | 7.66 | 44.27 | F6 |
| MapReduce | 7.58 | 1.46 | 3.85 | 12.17 | 2.68 | F6 |
| Video | 31.80 | 23.87 | 23.60 | 47.87 | 44.01 | Heu |
| ExCamera | 112.82 | 85.23 | 106.78 | 156.21 | 96.00 | F6 |

**Lowest P99 of the five systems, count over the cells of a condition**

| Condition | CLU | F6 | Heu | B* | RL | cells |
|---|---|---|---|---|---|---|
| 10 nodes (load 0.5, no cap) | 1 | 10 | 1 | 0 | 0 | 12 |
| 20 nodes | 1 | 9 | 2 | 0 | 0 | 12 |
| 40 nodes | 1 | 10 | 1 | 0 | 0 | 12 |

**CLU's plan time against the node count (all cells of the application, 3 seeds)**

| Nodes | App | requests (mean) | plan ms p50 | p99 | max | escalations per request | real miss share | wall s (mean) |
|---|---|---|---|---|---|---|---|---|
| 10 nodes | ML | 85,043 | 0.90 | 4.4 | 58 | 0.32 | 18.9% | 511 |
| 10 nodes | MapReduce | 31,591 | 1.13 | 14.2 | 135 | 20.18 | 43.8% | 921 |
| 10 nodes | Video | 1,692 | 1.00 | 3.7 | 26 | 0.35 | 8.2% | 13 |
| 10 nodes | ExCamera | 383 | 3.05 | 32.0 | 111 | 25.23 | 36.0% | 39 |
| 20 nodes | ML | 183,203 | 0.88 | 2.3 | 39 | 0.41 | 22.1% | 967 |
| 20 nodes | MapReduce | 68,219 | 0.83 | 9.0 | 42 | 19.00 | 40.0% | 1,381 |
| 20 nodes | Video | 3,631 | 0.40 | 1.4 | 6 | 0.57 | 15.9% | 12 |
| 20 nodes | ExCamera | 805 | 1.76 | 18.2 | 47 | 25.95 | 35.6% | 49 |
| 40 nodes | ML | 328,744 | 0.77 | 1.7 | 50 | 0.22 | 16.3% | 1,545 |
| 40 nodes | MapReduce | 122,440 | 0.87 | 7.1 | 58 | 18.43 | 38.5% | 2,403 |
| 40 nodes | Video | 6,605 | 1.08 | 3.1 | 19 | 0.92 | 32.8% | 58 |
| 40 nodes | ExCamera | 1,438 | 1.86 | 16.2 | 34 | 29.31 | 36.3% | 89 |

10 nodes: median over the 12 cells of the per-cell p50 = 1.00 ms, of the per-cell p99 = 5.4 ms, largest single plan 135 ms.

20 nodes: median over the 12 cells of the per-cell p50 = 0.81 ms, of the per-cell p99 = 4.7 ms, largest single plan 47 ms.

40 nodes: median over the 12 cells of the per-cell p50 = 0.89 ms, of the per-cell p99 = 5.3 ms, largest single plan 58 ms.

**Cold starts (total of the run incl. warm-up, mean of seeds)**

| Nodes | App | CLU | Heu | B* | RL |
|---|---|---|---|---|---|
| 10 nodes | ML | 6,779 | 66,551 | 2,820 | 14,084 |
| 10 nodes | MapReduce | 38,749 | 113,064 | 2,650 | 122,510 |
| 10 nodes | Video | 224 | 1,499 | 5,150 | 1,987 |
| 10 nodes | ExCamera | 509 | 1,867 | 3,682 | 3,077 |
| 20 nodes | ML | 10,308 | 140,558 | 3,794 | 16,415 |
| 20 nodes | MapReduce | 71,504 | 243,055 | 5,185 | 245,296 |
| 20 nodes | Video | 823 | 2,914 | 7,498 | 4,274 |
| 20 nodes | ExCamera | 1,022 | 3,635 | 5,921 | 6,376 |
| 40 nodes | ML | 18,820 | 265,128 | 3,972 | 16,702 |
| 40 nodes | MapReduce | 116,779 | 440,772 | 8,525 | 332,753 |
| 40 nodes | Video | 1,438 | 6,135 | 9,219 | 7,426 |
| 40 nodes | ExCamera | 2,134 | 7,142 | 8,166 | 11,238 |

### R6. Cold-start duration (live cell: nominal load 0.5, peak cap 300 tasks/s; one duration for every function)

Geometric-mean ratio CLU / system over the 12 cells of a duration, bootstrap 95% CI. Below 1: CLU is lower.




**P99 makespan**

| Condition | vs F6 | vs Heu | vs B* | vs RL |
|---|---|---|---|---|
| cold start 2 s | 3.40 [1.27, 10.61]; 3/12 | 0.63 [0.24, 1.47]; 4/12 | 0.88 [0.34, 2.44]; 7/12 | 1.00 [0.45, 2.23]; 6/12 |
| cold start 5 s | 8.32 [2.45, 33.29]; 1/12 | 0.77 [0.26, 1.95]; 6/12 | 1.70 [0.57, 5.67]; 8/12 | 0.57 [0.21, 1.24]; 4/12 |
| cold start 10 s | 20.31 [5.82, 84.69]; 0/12 | 0.97 [0.39, 2.41]; 5/12 | 2.73 [0.93, 8.80]; 6/12 | 0.87 [0.31, 2.09]; 3/12 |

**average makespan**

| Condition | vs F6 | vs Heu | vs B* | vs RL |
|---|---|---|---|---|
| cold start 2 s | 2.63 [1.24, 6.28]; 1/12 | 0.72 [0.36, 1.35]; 5/12 | 1.31 [0.67, 2.76]; 8/12 | 0.93 [0.52, 1.61]; 8/12 |
| cold start 5 s | 5.29 [1.44, 21.99]; 1/12 | 0.78 [0.25, 2.33]; 6/12 | 2.17 [0.72, 7.65]; 8/12 | 0.72 [0.32, 1.47]; 4/12 |
| cold start 10 s | 8.45 [1.92, 41.27]; 0/12 | 0.72 [0.21, 2.40]; 9/12 | 2.44 [0.67, 10.11]; 8/12 | 0.61 [0.20, 1.65]; 3/12 |

**P99 makespan per application (mean of seeds 1-3, s)**


cold start 2 s

| App | CLU | F6 | Heu | B* | RL | lowest |
|---|---|---|---|---|---|---|
| ML | 0.96 | 1.72 | 21.01 | 8.64 | 6.65 | CLU |
| MapReduce | 119.99 | 1.49 | 34.52 | 8.73 | 16.34 | F6 |
| Video | 46.99 | 29.65 | 42.77 | 111.20 | 57.00 | F6 |
| ExCamera | 203.59 | 101.83 | 256.91 | 206.09 | 169.11 | F6 |

cold start 5 s

| App | CLU | F6 | Heu | B* | RL | lowest |
|---|---|---|---|---|---|---|
| ML | 4.86 | 1.72 | 62.58 | 11.51 | 74.40 | F6 |
| MapReduce | 577.91 | 1.49 | 88.16 | 12.07 | 677.35 | F6 |
| Video | 86.83 | 29.66 | 75.67 | 138.46 | 59.00 | F6 |
| ExCamera | 232.47 | 103.73 | 271.90 | 238.80 | 183.97 | F6 |

cold start 10 s

| App | CLU | F6 | Heu | B* | RL | lowest |
|---|---|---|---|---|---|---|
| ML | 14.44 | 1.72 | 147.17 | 20.45 | 314.19 | F6 |
| MapReduce | 1634.12 | 1.50 | 180.05 | 18.99 | 492.75 | F6 |
| Video | 201.37 | 29.86 | 146.45 | 224.61 | 95.22 | F6 |
| ExCamera | 292.91 | 102.56 | 431.53 | 303.15 | 215.48 | F6 |

**Average makespan per application (mean of seeds 1-3, s)**


cold start 2 s

| App | CLU | F6 | Heu | B* | RL | lowest |
|---|---|---|---|---|---|---|
| ML | 0.68 | 0.69 | 6.72 | 1.72 | 3.21 | CLU |
| MapReduce | 32.53 | 1.01 | 13.32 | 2.90 | 9.06 | F6 |
| Video | 26.75 | 23.98 | 25.65 | 41.28 | 27.28 | F6 |
| ExCamera | 136.27 | 85.66 | 119.15 | 122.01 | 121.38 | F6 |

cold start 5 s

| App | CLU | F6 | Heu | B* | RL | lowest |
|---|---|---|---|---|---|---|
| ML | 0.82 | 0.69 | 19.58 | 2.05 | 10.29 | F6 |
| MapReduce | 334.66 | 1.01 | 36.44 | 4.08 | 147.21 | F6 |
| Video | 33.08 | 23.98 | 32.39 | 50.21 | 28.61 | F6 |
| ExCamera | 150.16 | 85.75 | 141.95 | 128.52 | 129.72 | F6 |

cold start 10 s

| App | CLU | F6 | Heu | B* | RL | lowest |
|---|---|---|---|---|---|---|
| ML | 1.36 | 0.69 | 41.36 | 3.31 | 58.54 | F6 |
| MapReduce | 904.58 | 1.01 | 71.85 | 5.97 | 248.78 | F6 |
| Video | 44.67 | 24.00 | 50.36 | 79.16 | 37.86 | F6 |
| ExCamera | 160.47 | 85.95 | 206.55 | 153.77 | 146.03 | F6 |

**Lowest P99 of the five systems, count over the cells of a condition**

| Condition | CLU | F6 | Heu | B* | RL | cells |
|---|---|---|---|---|---|---|
| cold start 2 s | 3 | 9 | 0 | 0 | 0 | 12 |
| cold start 5 s | 1 | 11 | 0 | 0 | 0 | 12 |
| cold start 10 s | 0 | 12 | 0 | 0 | 0 | 12 |

**CLU's cold starts and escalations against the duration (descriptive)**

Cold starts: total of the run incl. the warm-up, mean of seeds; 'cold-mode decisions' = decisions where CLU chose cold scaling (all seeds); per request = divided by the requests of the run. Measured-duration values (0.22-0.34 s) are the live cell of Stage 1 (R4).

| App | duration | cold starts (CLU) | cold-mode decisions per request | escalations per request | predicted miss share | real miss share |
|---|---|---|---|---|---|---|
| ML | measured | 3 | 0.001 | 0.004 | 0.0% | 0.2% |
| ML | 2 s | 0 | 0.002 | 0.010 | 0.0% | 0.6% |
| ML | 5 s | 0 | 0.005 | 0.030 | 0.0% | 1.2% |
| ML | 10 s | 2 | 0.007 | 0.036 | 0.0% | 2.8% |
| MapReduce | measured | 2,118 | 0.122 | 0.712 | 0.0% | 4.1% |
| MapReduce | 2 s | 20,750 | 4.149 | 21.756 | 23.7% | 56.5% |
| MapReduce | 5 s | 20,468 | 8.323 | 43.111 | 60.1% | 100.0% |
| MapReduce | 10 s | 10,671 | 6.639 | 34.865 | 44.4% | 100.0% |
| Video | measured | 224 | 0.132 | 0.352 | 0.9% | 8.2% |
| Video | 2 s | 516 | 0.255 | 0.687 | 4.5% | 9.4% |
| Video | 5 s | 956 | 0.500 | 1.219 | 8.5% | 19.0% |
| Video | 10 s | 672 | 0.551 | 1.390 | 1.5% | 24.8% |
| ExCamera | measured | 509 | 0.961 | 25.235 | 22.5% | 36.0% |
| ExCamera | 2 s | 616 | 1.110 | 26.683 | 19.6% | 40.6% |
| ExCamera | 5 s | 321 | 1.069 | 24.312 | 13.6% | 36.4% |
| ExCamera | 10 s | 338 | 1.034 | 20.326 | 7.0% | 34.5% |

### R7. 1000Genome (10 nodes, no peak cap; ML cell's window)

These runs hold 54-88 requests, so the P99 is set by one or two requests: read the intervals as wide, no ranking is claimed.

**Per cell: P99 / average makespan (s)**

| Load | seed | requests | CLU | F6 | Heu | B* | RL | lowest P99 |
|---|---|---|---|---|---|---|---|---|
| load 0.5 | 1 | 54 | 511.2 / 326.1 | 470.5 / 323.4 | 666.2 / 339.7 | 435.3 / 322.0 | 505.7 / 297.7 | B* |
| load 0.5 | 2 | 56 | 433.2 / 317.1 | 533.2 / 302.4 | 875.2 / 370.0 | 368.3 / 288.9 | 462.3 / 290.7 | B* |
| load 0.5 | 3 | 45 | 455.0 / 364.9 | 312.6 / 263.9 | 397.7 / 280.6 | 284.5 / 262.1 | 518.7 / 294.2 | B* |
| load 0.7 | 1 | 80 | 1239.0 / 502.7 | 564.3 / 432.6 | 3220.2 / 831.0 | 814.8 / 547.5 | 790.8 / 400.4 | F6 |
| load 0.7 | 2 | 62 | 464.1 / 346.9 | 332.3 / 268.9 | 613.1 / 307.5 | 314.5 / 277.4 | 486.2 / 296.7 | B* |
| load 0.7 | 3 | 60 | 434.6 / 312.8 | 312.1 / 266.3 | 435.3 / 296.5 | 292.8 / 269.3 | 447.5 / 291.5 | B* |
| load 0.9 | 1 | 88 | 1438.8 / 522.4 | 645.3 / 499.0 | 1591.3 / 653.5 | 1062.9 / 702.2 | 747.9 / 441.6 | F6 |
| load 0.9 | 2 | 71 | 480.0 / 335.1 | 515.8 / 337.6 | 1644.2 / 485.3 | 345.4 / 295.0 | 491.9 / 313.4 | B* |
| load 0.9 | 3 | 83 | 556.3 / 359.3 | 404.2 / 283.2 | 1740.2 / 490.5 | 483.2 / 356.7 | 564.3 / 335.0 | F6 |

Lowest P99 of the five systems over the 9 cells: CLU 0, F6 3, Heu 0, B* 6, RL 0.

**Geometric-mean ratio CLU / system over the 9 cells (3 loads x seeds 1-3), bootstrap 95% CI**

| Measure | vs F6 | vs Heu | vs B* | vs RL |
|---|---|---|---|---|
| P99 makespan | 1.36 [1.10, 1.67]; 2/9 | 0.60 [0.44, 0.82]; 8/9 | 1.36 [1.26, 1.47]; 0/9 | 1.09 [0.95, 1.31]; 6/9 |
| average makespan | 1.15 [1.07, 1.24]; 1/9 | 0.88 [0.75, 1.02]; 6/9 | 1.06 [0.95, 1.19]; 2/9 | 1.14 [1.09, 1.18]; 0/9 |

**Mean over seeds 1-3 (s)**

| Load | measure | CLU | F6 | Heu | B* | RL |
|---|---|---|---|---|---|---|
| load 0.5 | P99 | 466.44 | 438.77 | 646.37 | 362.68 | 495.57 |
| load 0.5 | average | 336.07 | 296.58 | 330.07 | 291.02 | 294.20 |
| load 0.7 | P99 | 712.60 | 402.92 | 1422.87 | 474.04 | 574.84 |
| load 0.7 | average | 387.44 | 322.59 | 478.35 | 364.73 | 329.57 |
| load 0.9 | P99 | 825.00 | 521.76 | 1658.59 | 630.49 | 601.37 |
| load 0.9 | average | 405.59 | 373.28 | 543.12 | 451.30 | 363.34 |
