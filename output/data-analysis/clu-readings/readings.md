### R1. CLU against F6, Heu, B*, RL

Geometric-mean ratio CLU / system over the 12 cells (4 applications x seeds 1-3) of a condition, bootstrap 95% CI (10,000 resamples). Below 1: CLU is lower. 'Lower in n/12' counts cells.


**P99 makespan**

| Condition | vs F6 | vs Heu | vs B* | vs RL |
|---|---|---|---|---|
| live cell (load 0.5, cap 300) | 1.10 [0.84, 1.40]; 4/12 | 0.86 [0.70, 1.06]; 6/12 | 0.34 [0.22, 0.52]; 11/12 | 0.55 [0.40, 0.75]; 9/12 |
| load 0.5, no cap | 2.36 [1.34, 4.26]; 1/12 | 0.82 [0.48, 1.29]; 4/12 | 0.66 [0.40, 1.08]; 8/12 | 0.90 [0.37, 1.95]; 5/12 |
| load 0.7 | 2.32 [1.71, 3.24]; 1/12 | 0.73 [0.53, 0.98]; 9/12 | 0.72 [0.51, 1.03]; 7/12 | 0.52 [0.26, 0.98]; 6/12 |
| load 0.9 | 2.64 [2.04, 3.48]; 0/12 | 0.70 [0.51, 0.95]; 10/12 | 0.77 [0.51, 1.22]; 9/12 | 0.71 [0.39, 1.19]; 5/12 |

**average makespan**

| Condition | vs F6 | vs Heu | vs B* | vs RL |
|---|---|---|---|---|
| live cell (load 0.5, cap 300) | 1.08 [1.00, 1.21]; 3/12 | 0.91 [0.81, 1.02]; 6/12 | 0.61 [0.51, 0.76]; 11/12 | 0.61 [0.45, 0.82]; 10/12 |
| load 0.5, no cap | 1.76 [1.20, 2.79]; 1/12 | 1.02 [0.73, 1.43]; 3/12 | 0.70 [0.47, 1.03]; 9/12 | 0.77 [0.33, 1.48]; 7/12 |
| load 0.7 | 1.94 [1.34, 3.01]; 0/12 | 1.28 [0.92, 1.86]; 3/12 | 0.80 [0.54, 1.22]; 8/12 | 0.64 [0.32, 1.16]; 7/12 |
| load 0.9 | 1.99 [1.45, 2.91]; 0/12 | 1.33 [0.98, 1.91]; 4/12 | 0.80 [0.48, 1.40]; 8/12 | 0.79 [0.51, 1.15]; 5/12 |

**P99 makespan per application (mean of seeds 1-3, s)**


live cell (load 0.5, cap 300)

| App | CLU | F6 | Heu | B* | RL | lowest |
|---|---|---|---|---|---|---|
| ML | 1.09 | 1.72 | 1.79 | 7.93 | 4.15 | CLU |
| MapReduce | 1.76 | 1.48 | 2.34 | 6.85 | 2.95 | F6 |
| Video | 41.14 | 29.77 | 33.23 | 90.29 | 69.78 | F6 |
| ExCamera | 170.66 | 102.75 | 158.16 | 175.25 | 148.14 | F6 |

load 0.5, no cap

| App | CLU | F6 | Heu | B* | RL | lowest |
|---|---|---|---|---|---|---|
| ML | 5.29 | 2.85 | 21.93 | 20.35 | 158.69 | F6 |
| MapReduce | 37.21 | 3.35 | 23.36 | 19.13 | 10.33 | F6 |
| Video | 41.14 | 29.77 | 33.23 | 90.29 | 69.78 | F6 |
| ExCamera | 170.66 | 102.75 | 158.16 | 175.25 | 148.14 | F6 |

load 0.7

| App | CLU | F6 | Heu | B* | RL | lowest |
|---|---|---|---|---|---|---|
| ML | 48.14 | 32.90 | 135.77 | 119.26 | 487.28 | F6 |
| MapReduce | 186.10 | 33.17 | 128.23 | 99.82 | 475.22 | F6 |
| Video | 130.64 | 58.49 | 186.59 | 259.80 | 93.74 | F6 |
| ExCamera | 338.42 | 171.02 | 482.42 | 392.15 | 242.17 | F6 |

load 0.9

| App | CLU | F6 | Heu | B* | RL | lowest |
|---|---|---|---|---|---|---|
| ML | 223.47 | 93.12 | 435.58 | 392.74 | 647.26 | F6 |
| MapReduce | 473.23 | 90.63 | 385.18 | 192.53 | 1500.33 | F6 |
| Video | 262.46 | 104.97 | 327.02 | 650.01 | 145.25 | F6 |
| ExCamera | 495.75 | 266.33 | 982.35 | 638.60 | 398.19 | F6 |

**Lowest P99 of the five systems, count over the 12 cells of a condition**

| Condition | CLU | F6 | Heu | B* | RL |
|---|---|---|---|---|---|
| live cell (load 0.5, cap 300) | 4 | 7 | 1 | 0 | 0 |
| load 0.5, no cap | 1 | 10 | 1 | 0 | 0 |
| load 0.7 | 0 | 11 | 0 | 0 | 1 |
| load 0.9 | 0 | 12 | 0 | 0 | 0 |

**Per seed: P99 ratio CLU / F6 (geometric mean over the 4 applications)**

| Condition | seed 1 | seed 2 | seed 3 |
|---|---|---|---|
| live cell (load 0.5, cap 300) | 1.19 | 1.12 | 1.00 |
| load 0.5, no cap | 3.22 | 2.67 | 1.53 |
| load 0.7 | 2.77 | 2.46 | 1.82 |
| load 0.9 | 3.16 | 2.24 | 2.60 |

**Per application: P99 ratio CLU / F6 (geometric mean over the 3 seeds)**

| Condition | ML | MapReduce | Video | ExCamera |
|---|---|---|---|---|
| live cell (load 0.5, cap 300) | 0.68 | 1.09 | 1.38 | 1.43 |
| load 0.5, no cap | 1.42 | 11.03 | 1.38 | 1.43 |
| load 0.7 | 1.47 | 5.45 | 2.13 | 1.70 |
| load 0.9 | 2.01 | 5.20 | 2.44 | 1.90 |

### R2. kappa sensitivity (live cell, 12 cells)

| kappa | geometric-mean P99 ratio to kappa = 1.5 | avg makespan ratio | predicted misses / requests | real misses / requests |
|---|---|---|---|---|
| 1.0 | 0.88 [0.73, 1.04] | 0.96 [0.91, 1.01] | 0.298% | 1.924% |
| 1.5 | 1 (reference) | 1 | 0.144% | 1.451% |
| 3.0 | 1.77 [1.18, 2.68] | 1.15 [1.02, 1.30] | 0.000% | 2.868% |

Per application, P99 (s, mean of seeds) and real-miss share (all requests incl. warm-up):

| App | k = 1.0 | k = 1.5 | k = 3.0 | pred. miss share k = 1.0 / 1.5 / 3.0 | real miss share k = 1.0 / 1.5 / 3.0 |
|---|---|---|---|---|---|
| ML | 0.99 | 1.09 | 1.02 | 0.0% / 0.0% / 0.0% | 0.4% / 0.2% / 0.2% |
| MapReduce | 1.49 | 1.76 | 5.07 | 0.0% / 0.0% / 0.0% | 0.9% / 4.1% / 9.9% |
| Video | 31.54 | 41.14 | 109.41 | 4.9% / 0.9% / 0.0% | 39.4% / 8.2% / 15.4% |
| ExCamera | 151.19 | 170.66 | 228.78 | 27.0% / 22.5% / 0.0% | 86.9% / 36.0% / 21.6% |

### R3. CLU (re-planned at every ready function) against CLU-S (plan at arrival only), live cell

Ratio CLU / CLU-S over 12 cells: P99 0.61 [0.51, 0.73] (CLU lower in 11/12), average makespan 0.83 [0.77, 0.88] (lower in 12/12).

| App | P99 CLU | P99 CLU-S | avg CLU | avg CLU-S | real miss share CLU / CLU-S | cold starts CLU / CLU-S |
|---|---|---|---|---|---|---|
| ML | 1.09 | 1.70 | 0.69 | 0.78 | 0.2% / 2.0% | 3 / 0 |
| MapReduce | 1.76 | 3.01 | 1.04 | 1.28 | 4.1% / 7.2% | 2118 / 511 |
| Video | 41.14 | 75.92 | 25.27 | 34.13 | 8.2% / 37.7% | 224 / 916 |
| ExCamera | 170.66 | 227.91 | 117.65 | 134.86 | 36.0% / 53.6% | 509 / 707 |

### R4. Cold starts, decision time, deadline misses (CLU, kappa = 1.5)

Cold starts: total of the run including the warm-up, mean of seeds. F6 is left out: it makes the same container changes during the warm-up, so its in-window count is not comparable.

| Condition | App | cold starts CLU | Heu | B* | RL | pred. miss share | real miss share | plan ms p50 / p99 / max | escalations per request |
|---|---|---|---|---|---|---|---|---|---|
| live | ML | 3 | 28877 | 1798 | 13977 | 0.0% | 0.2% | 0.62 / 3.1 / 35 | 0.00 |
| live | MapReduce | 2118 | 48605 | 3684 | 82897 | 0.0% | 4.1% | 0.85 / 4.8 / 63 | 0.71 |
| live | Video | 224 | 1499 | 5150 | 1987 | 0.9% | 8.2% | 1.00 / 3.7 / 26 | 0.35 |
| live | ExCamera | 509 | 1867 | 3682 | 3077 | 22.5% | 36.0% | 3.05 / 32.0 / 111 | 25.23 |
| unc0.5 | ML | 6779 | 66551 | 2820 | 14084 | 17.8% | 18.9% | 0.90 / 4.4 / 58 | 0.32 |
| unc0.5 | MapReduce | 38749 | 113064 | 2650 | 122510 | 40.1% | 43.8% | 1.13 / 14.2 / 135 | 20.18 |
| unc0.5 | Video | 224 | 1499 | 5150 | 1987 | 0.9% | 8.2% | 1.00 / 3.7 / 26 | 0.35 |
| unc0.5 | ExCamera | 509 | 1867 | 3682 | 3077 | 22.5% | 36.0% | 3.05 / 32.0 / 111 | 25.23 |
| rho0.7 | ML | 8873 | 58175 | 3302 | 16656 | 55.3% | 55.9% | 0.38 / 1.1 / 47 | 0.59 |
| rho0.7 | MapReduce | 106942 | 96773 | 2229 | 102747 | 78.7% | 82.4% | 1.92 / 18.2 / 146 | 38.29 |
| rho0.7 | Video | 1553 | 3120 | 4343 | 3067 | 31.9% | 36.5% | 0.79 / 4.0 / 26 | 1.58 |
| rho0.7 | ExCamera | 1081 | 2638 | 2612 | 3583 | 46.2% | 62.9% | 5.72 / 44.9 / 148 | 38.91 |
| rho0.9 | ML | 11892 | 22458 | 3509 | 7060 | 83.4% | 83.8% | 0.57 / 2.1 / 163 | 0.81 |
| rho0.9 | MapReduce | 142279 | 44804 | 1750 | 66350 | 99.1% | 100.0% | 1.88 / 7.8 / 183 | 47.04 |
| rho0.9 | Video | 2441 | 3911 | 3815 | 2852 | 61.6% | 67.3% | 1.36 / 3.9 / 25 | 2.72 |
| rho0.9 | ExCamera | 1943 | 2841 | 2179 | 2861 | 70.0% | 84.4% | 5.74 / 44.9 / 166 | 50.31 |

Largest single plan over all 48 CLU cells of the four conditions: 183 ms. State moved between nodes by CLU: 0 MB relocated (no mover); the run-time state traffic is in the result files (`resources.state_mb`).
