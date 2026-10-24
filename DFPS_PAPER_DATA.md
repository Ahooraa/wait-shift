# Data extracted from the DFPS paper (Zolfaghari, Abrishami, Rasoolzadegan, Javadi; IEEE TSC 2025, DOI 10.1109/TSC.2025.3592226, vol.18 no.5 pp.2781-2793)
Everything below is stated in the text; section/table references are the paper's. Nothing is inferred. "NOT STATED" marks what the paper omits.

## 1. Headline claim
- Reduces the average workflow makespan "by up to 86% compared to state-of-the-art methods" (abstract). The conclusion also says it reduces the number of cold starts "compared to two state-of-the-art methods" (Heu, RL).

## 2. Method (components)
| Component | Algorithm | Detail given |
|---|---|---|
| Initial placement | NSGA-II | population Np = 100, 2 objectives; chromosome = per-node placement vector of length \|F\| whose sum equals ecc_k; crossover swaps node vectors; mutation moves one instance between functions; final pick = lowest sum of min-normalised criteria (Sec.4.1/4.4) |
| Request scheduling | graph pattern matching, method of ref. [39] | spanning trees, missing paths replaced by shortest alternatives, least total edge weight chosen; edge weight = FST + STT; queueing model M/M/c (Sec.4.2) |
| Dynamic adjustment | simulated annealing (Alg.1 neighbour, Alg.2 loop) | every 4 s; EF = sum of relocation gains; NOT STATED: T_max, T_min, cooling, iterations |
| Transfer time | Eq.1-2: STT = h x (epd + SS/bw) | epd = 0, bw = 50 MB/s |

## 3. Simulation setup (Sec.5.1, Table 2)
| Item | Value |
|---|---|
| Simulator | EdgeCloudSim [42], modified for serverless |
| Workflows | Alibaba Cluster Trace [43], applications under one minute |
| Topology | GT-ITM [44] (parameters NOT STATED) |
| Function run-time | 2-10 s (from [45]) |
| Cold-start delay | 2-10 s (from [45]) |
| Intermediate state size | 10-50 MB |
| Number of workflows | 15 (5-40 in Sec.5.2.3) |
| Edge nodes | 80 (20-160 in Sec.5.2.2) |
| Bandwidth | 50 MB/s |
| Node function capacity ecc | 5-25 |
| Node storage capacity esc | 10-30 GB |
| Incoming request rate | 0.5-100 per second |
| Replacement interval | 4 s (chosen from a sweep 1-9 s by lowest average execution delay) |
| Uniform workload | Poisson, per-application mean inter-arrival drawn from 200-700 ms |
| Pareto workload | about 20% of applications 50-100 ms; the rest 2-4 s |
| Arrival scaling factors | 0.25, 0.5, 0.75, ..., 2 (rate multiplier) |
| Repetitions | 10 different workloads per point; repeated-measures ANOVA, p < 0.05 |
| Metrics | average makespan, resource utilization, number of cold starts |
| NOT STATED | run length, warm-up, distribution inside ranges, number of function types, task-to-function mapping, request origin, utilization definition |

## 4. Compared methods
SR (static, random initial placement), SG (static, NSGA-II placement), Heu = Xu et al. 2023 [18] (placement and scheduling per function request), RL = Yang et al. 2025 MOSEC [28]. DFPS = NSGA-II + matching + annealing.

## 5. Reported findings (qualitative; exact values are in Figures 5-7, not in the text)
Scenario 1, arrival rate (Fig.5)
- Makespan rises with arrival rate for all methods (congestion).
- Uniform: DFPS, SR and SG have significantly lower makespan than Heu and RL.
- Pareto: static initial placement fails to match the skewed demand; dynamic adjustment helps DFPS most.
- Cold starts of SR and SG are zero by construction.
- Utilization: Heu low (many cold starts, little reuse). Pareto: SR and SG lowest, SG slightly above SR; DFPS and RL high (RL by aggressively removing idle instances, at the cost of more cold starts).
- RL weakness: no awareness of workflow structure, tasks spread over nodes, more cold starts and transfer delay.

Scenario 2, network size 20-160 nodes (Fig.6)
- Makespan decreases with size for all methods.
- Uniform: the three proposed variants beat Heu and RL; SG equal to or slightly better than DFPS. Pareto: DFPS best. SG always beats SR.
- DFPS utilization declines with size; Heu consistently low; RL most consistent.

Scenario 3, number of applications 5-40 (Fig.7)
- Makespan rises with the number of applications.
- DFPS utilization rises with the number of applications under Uniform; under Pareto, DFPS, Heu and RL are high even with few applications.

## 6. What this extraction cannot give
- The numeric values behind Figures 5-7 (only plotted). I can read approximate values from the page images if you want; those would be estimates, with reading error.
- The "86%" claim is a maximum over unspecified scenarios and methods; the text does not say which.
