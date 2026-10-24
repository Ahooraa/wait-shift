# DFPS: Extended Limitations Audit and Gap Evaluation

*Prepared 2026-10-13 for the brainstorming phase (no design doc yet).*
*Target paper: B. Zolfaghari, S. Abrishami, A. Rasoolzadegan, B. Javadi, "Dynamic Function Placement and Request Scheduling of Serverless Workflows in Edge Environment," IEEE Transactions on Services Computing, 2025, DOI 10.1109/TSC.2025.3592226. Page numbers refer to the author's accepted version.*

---

## 0. How this was evaluated

| Step | What was done | Limits |
|---|---|---|
| Close reading | All 13 pages. Eq. 3, Eq. 6, Algorithm 1 and Algorithm 2 were checked on the rendered PDF, not only on extracted text. | One reader. Figures were not checked numerically. |
| Corpus coverage | 73 PDFs from your `function placement papers` folders. Hits for 35 gap concepts were counted by regex in the body text, with reference lists removed. | A keyword hit is a coarse proxy. Zero hits does not mean the idea is new. |
| Future-work mining | Sentences matching "future work", "beyond the scope" or "do not consider" were extracted from all 73 papers. | Heuristic filter, so some statements may be missed. |
| External check | About 15 web searches with a 2024–2026 focus, plus a Semantic Scholar and Crossref lookup of papers citing DFPS. | Not exhaustive. OpenAlex and Semantic Scholar were rate-limited. Abstracts of two citing papers were unavailable (§6). |

All novelty statements are **provisional**: "not found in the corpus or in my searches", never "proven new". The literature-review phase must confirm whichever gap you choose.

---

## 1. Limitations of DFPS

### 1a. Errors in the printed method (verified on the rendered pages)

| ID | Where | Problem | Consequence |
|---|---|---|---|
| E1 | Eq. 3, p. 6 | Σ_l (FAN − FEN) has no absolute value or square. Each node's placement vector must sum to ecc_k (p. 5–6), so Σ FAN = Σ_k ecc_k = Σ FEN. | The second NSGA-II objective is identically 0, so placement is effectively single-objective. The objective actually used is unspecified. |
| E2 | Eq. 6, p. 7 | The Erlang-C queue length omits P₀. μ_l is defined as an execution **time** but used as a **rate**. There is no stability check. | Queue lengths are overestimated. When λ ≥ cμ, the squared denominator returns a finite value instead of signalling overload. |
| E3 | Alg. 2, p. 9 | A worse move (Δ < 0) is reverted only if random(0,1) ≥ e^(−Δ/T), but that threshold is greater than 1. | Every worse move is accepted, and SA becomes a near-random walk. Also, t is never incremented and no best-so-far solution is kept. |
| E4 | Alg. 1, p. 8 | Line 23 appends the relocated f_n request to FRQ_rs, the queue of the **removed** function, instead of FRQ_ns. Lines 16 and 23 never remove moved requests from their source queue. e_s′ ← ∅ makes AET(r_q, e_s′) undefined on the first comparison. | The neighbour generator is incorrect as written, so a reimplementation has to guess the intent. |
| E5 | §4.2, p. 7 | The scheduler picks the match with the minimum **total** g-edge weight. | For DAGs with parallel branches, a sum is not the makespan, which is the maximum over paths. The objective is misaligned. |
| E6 | pp. 7, 9–10 | The reference graph is built per request (§4.2) but also per workflow type, once (§4.4). The replacement interval equals the average critical-path length (p. 7) but is also 4 s chosen empirically from 1–9 s (p. 9–10). f_r is the function with the "least number of requests" (text) but the "least utilized" one (Alg. 1). | These contradictions hurt reproducibility. |

> **Fair-comparison rule for your paper:** implement DFPS with E1–E4 corrected and state how you corrected each one. Consider emailing the corresponding author for their code before submitting.

### 1b. Modelling assumptions that likely change conclusions

| ID | Assumption (page) | Why it matters | Evidence |
|---|---|---|---|
| M1 | Every container slot always holds a warm instance, so the total instance count never changes (p. 5–6). SR/SG cold starts are 0 by construction (p. 10). | There is no scale-to-zero and no trade-off between idle cost and cold starts, which is the trade-off the introduction uses as motivation (p. 2). | — |
| M2 | Requests have no origin in the model, and the proximity objective weights all nodes equally (p. 4, p. 6). The "Pareto" skew is across apps, not across space. | MEC placement exists to be near **where** demand is, but spatial hotspots are invisible to DFPS. | Mobility-aware serverless placement exists for single functions (Raith et al., UCC'22; TAROT, UCC'22). |
| M3 | States are transferred only between edge nodes (Eq. 1–2), and makespan starts when the controller receives the request (p. 5). The uplink of input data and the return of results are not modelled. | In MEC the access network is often the bottleneck. | — |
| M4 | A central controller, possibly hosted in the cloud (p. 4), sends an execute request for every ready task (p. 5). Control-plane delay is not modelled. | FaaSFlow found this master-side triggering pattern to be a major overhead. Moving triggering to the workers cut scheduling overhead by 74.6%. | FaaSFlow abstract (in your corpus) |
| M5 | Containers are identical. There is one average bandwidth, zero propagation delay, per-hop store-and-forward, and no link contention. On fan-out, the full state is sent separately to each successor's node (p. 4–5). | With 10–50 MB states over 50 MB/s links, contention and fan-out duplication would dominate in practice. | SONIC (ATC'21), PASS (2022), Databelt (2025) |
| M6 | Service times are exponential (M/M/c, p. 7). | Azure Functions durations are heavy-tailed: Raptor reports SCV ≈ 11.4 and a mean ≈ 0.7 s. Kingman's approximation scales mean waiting by (c_a² + c_s²)/2 ≈ 6.2, versus 1 for exponential service. At the same utilisation, M/M-based estimates would understate queueing by roughly 6×, even if Eq. 6 were correct. | Raptor (arXiv 2403.16457). Kingman's formula is textbook background, not re-checked here. |
| M7 | Function runtimes and cold starts are both 2–10 s (Table 2). | This doesn't match the sub-second edge apps that motivate the paper (AR, healthcare, p. 1), or Azure's ~0.7 s mean function duration. | Raptor |
| M8 | Storage is checked at scheduling time but not reserved. There is no rule for when no feasible match exists (p. 6–7). | Concurrent requests can over-commit storage, and behaviour under overload is undefined. There is no admission control. | — |
| M9 | The whole DAG is bound to instances at arrival, using steady-state estimates (early binding, p. 4–5). | Downstream queues at execution time will differ. The early-vs-late binding trade-off is never examined. | — |
| M10 | Replacement mechanics are unspecified (p. 8): what happens to in-flight executions on an evicted instance, how a 2–10 s cold start fits a 4 s interval, and whether AET on the new instance includes the cold start. | If the cold start is excluded, relocation gains are overstated. | — |
| M11 | Centralised control and a single objective (mean makespan). No node failures, user mobility, cloud offload, conditional DAGs, or interference between co-located containers. | Scope limits. | — |

### 1c. Evaluation weaknesses

| ID | Weakness |
|---|---|
| V1 | "Dynamic" adaptation is never tested against change over time. Arrival rates are stationary Poisson per app; only their skew varies (p. 9). |
| V2 | The Alibaba cluster trace contains batch-job DAGs, not serverless workflows (p. 9). |
| V3 | Weak baselines. The RL baseline [28] is not workflow-aware, which the authors acknowledge (p. 11). Its training budget is unreported. There is no exact or lower-bound reference and no recent predictive baseline (Sdser- or OPTS-type). |
| V4 | Metrics are limited to mean makespan, an undefined "utilisation", and cold-start counts. There is no P95/P99, SLO or goodput measure, and no decision latency or controller overhead. |
| V5 | The interval was tuned on the evaluation workloads. SA settings (T_max, T_min, cooling schedule) and NSGA-II generation counts are unreported. No code is released. |
| V6 | Statistics stop at an omnibus repeated-measures ANOVA (p < 0.05). There are no post-hoc tests, confidence intervals or effect sizes. |

---

## 2. Divergent exploration

| DFPS assumption | Reversal | Research question it opens | Status (from evidence) |
|---|---|---|---|
| Reconfigure every T seconds | Reconfigure only when it pays | When is a placement change worth its cost? | **Open** (T1) |
| Trust the estimates (λ, μ) | Trust forecasts only up to a bound | Can forecasts help without risking the worst case? | **Open** (T2) |
| All capacity is always warm | Warm capacity is the priced, scarce resource | Workflow-level keep-alive as a ski-rental problem | Partly covered: keep-alive is crowded, but no learning-augmented version found |
| Placement first, dispatch follows | Placement anticipates dispatch | Two-timescale or bilevel co-design | Partly covered, for monolithic services only (T5) |
| Minimise mean makespan | Maximise SLO-goodput | What should be rejected or degraded under overload? | Open-ish (T6) |
| State moves to the function | The function moves to the state | Data-gravity placement | Covered (ClusterFlow'26, Databelt'25) |
| Bind the whole DAG at arrival | Late, stage-by-stage binding | Early vs late binding trade-off | Not found; small study, fits as a component of T4/T5 |
| Demand is uniform in space | Demand has a location and moves | Spatial/mobility-aware workflow placement | Partly covered, for single functions only (T7) |

**Analogies from other fields worth borrowing:**
- **Dynamic facility layout problem (operations research):** layouts planned per period trade handling cost against rearrangement cost. This is DFPS's reconfiguration problem in another guise.
- **Dynamic right-sizing of data centres / smoothed online optimisation with switching costs:** provides competitive analysis for T1. (Background knowledge, not re-searched here.)
- **Ski rental with predictions:** has a known robustness–consistency trade-off (Wei & Zhang, NeurIPS'20; Purohit et al., NeurIPS'18). Relevant to T2.
- **Fork-join queueing networks:** model makespan tails for T4.
- **Inventory control with advance demand information:** the DAG gives advance notice of downstream demand. This is a new framing; the mechanism itself is partly covered by OPTS and Sdser.

---

## 3. Gap evaluation

Scores run from 1 to 5 and are my judgement:
- **N** novelty, against the corpus and searches
- **S** significance: whether addressing it changes results or matters in practice
- **R** rigour potential: a formal model and a guarantee
- **F** feasibility in about 9–12 months, using simulation plus a small testbed and public data
- **A** alignment with your `objective-ideas` / `future-works` notes

| ID | Gap | Root in DFPS | Closest prior work (evidence) | N | S | R | F | A | Σ |
|---|---|---|---|---|---|---|---|---|---|
| **T1** | **Deciding when to reconfigure:** event-triggered, cost-aware reconfiguration with a guarantee against oscillation | Fixed 4 s period; cost-blind SA (E3, M10) | ClusterFlow'26 measured oscillation (DesFaaS: 78 migrations in 30 min) and fixed it heuristically. Sdser'25 includes deployment cost but works in fixed slots. MPC (MASCOTS'25) is periodic, per-function and cloud-based. No paper found that designs the trigger itself. Corpus: almost no hits beyond DFPS itself. | 4 | 4 | 4 | 4 | 5 | **21** |
| **T2** | **Learning-augmented control:** use forecasts, but keep a worst-case guarantee when they fail (consistency vs robustness) | DFPS reacts with no forecast. Every forecast-based competitor trusts its forecast fully. | **0 corpus hits.** Sdser, WPPSO, EdgeOrcher, MPC'25 and POSEIDON's future work all trust their forecasts. Bandit regret for placement exists (arXiv 2410.13696) but is a different guarantee. Ski-rental-with-predictions theory exists, but no serverless application was found. | 5 | 4 | 5 | 3 | 4 | **21** |
| **T4** | Dispatch that targets the critical path and tail SLOs under heavy-tailed service, at the edge | E5, M6, V4 | METIS (SoCC'25) and Raptor work in the cloud. FaaSPR'25 targets tails in data centres; ClusterFlow reports P99. None combines edge placement with stochastic DAG tails. | 3 | 5 | 4 | 4 | 4 | **20** |
| **T5** | Two-timescale co-design of placement and dispatch with feedback (bilevel) | Three loosely coupled components | Two-timescale designs exist for monolithic services: Farhadi ToN'21 (DFPS ref [33]), Wei TCC'23, Hudson FGCS'24. JET'26 leaves "cross-stage feedback" as future work. Jayanthi'26 is bi-level but structured differently. | 3 | 4 | 4 | 4 | 5 | **20** |
| T3 | Queueing-correct, multi-instance online placement (concurrency, multi-workflow queues, heavy tails) | E2, M6 | Popularity-aware'25 scopes out "heavy concurrency, multi-workflow queuing". OPTS'25 proves its competitive ratio only for homogeneous servers. | 4 | 4 | 4 | 3 | 3 | 18 |
| T6 | Overload handling: admission control and graceful degradation to maximise goodput under SLOs | M8 | Only 2/73 corpus papers mention it ≥3 times. TopFull (SIGCOMM'24) covers microservices. Nothing found for edge serverless workflows. | 4 | 4 | 3 | 4 | 2 | 17 |
| T8 | Robust (two-stage or distributionally robust) placement under demand uncertainty, with cold starts and DAGs | V1, estimation error | Robust edge service placement exists (IoT-J'22, TNSM'24, arXiv'24) but isn't serverless. The INLP'26 paper lists robust/recourse formulations as future work. | 3 | 3 | 5 | 3 | 2 | 16 |
| T7 | Placement aware of where demand originates: user location, mobility and data sources | M2, M3 | Raith (UCC'22), TAROT (UCC'22) and digital-twin replicas (TC'24) handle single functions. Workflows with state plus mobility: not found. | 3 | 4 | 3 | 3 | 2 | 15 |
| T11 | Re-evaluating edge serverless workflow schedulers under realistic conditions | V1–V6, M6–M7 | No systematic study found (not searched exhaustively) | 3 | 3 | 2 | 4 | 3 | 15 |
| T9 | Contention-aware state transfer (shared links, fan-out multicast) | M5 | SONIC'21, PASS'22, DPE'22/SFSO'25 (traffic splitting), Databelt'25 | 2 | 4 | 3 | 3 | 2 | 14 |
| T12 | Serverless AI/agentic workflows at the edge (cold starts from loading model weights, GPU memory) | M5 (identical containers) | ServerlessLLM and Tangram (cloud); SCALE'26 (cluster DRL) | 4 | 4 | 2 | 2 | 2 | 14 |
| T13 | Energy and true elasticity (sleeping nodes, renewable-powered edge) | M1 | faasHouse (TSC'24), REPFS'23, Tian & Ghobaei-Arani'26, JET'26 | 2 | 3 | 3 | 4 | 2 | 14 |
| T10 | Placement aware of the control plane (decision latency, master- vs worker-side triggering) | M4 | FaaSFlow'22; ClusterFlow'26 | 2 | 3 | 2 | 4 | 2 | 13 |
| T14 | Decentralised or multi-owner control | Centralised controller | **DFPS authors' own stated future work** (race risk); also DG-DDPG and Transformer-DRL future work | 2 | 3 | 3 | 3 | 2 | 13 |

**How to use the scores:** T11 works better as a *motivation section* than as a paper. T3 is best as the *system model* underneath T1/T2. T9 and T10 are best as *model-fidelity upgrades* that reviewers will appreciate.

---

## 4. Crowded areas: use as components, not as the main contribution

| Area | Evidence |
|---|---|
| Predictive pre-warming / container pre-deployment | Sdser'25, OPTS'25, EdgeOrcher'23, WPPSO'26, MPC (MASCOTS'25) |
| Layer/package caching | Popularity-aware'25 (with a regret bound), SLO-aware layer-wise memory sharing'24, package-aware'23 |
| Function fusion + placement | Costless'18, WISEFUSE'22, EdgeOrcher'23, GRL-Orch'26 |
| Dynamic/conditional DAGs | Sdser'25, OPTS'25, Popularity-aware'25, deadline-aware heterogeneous'26 |
| GNN/DRL schedulers | 28 of 73 corpus papers have ≥10 hits (including meta-RL DMPPO-WS'26 and Adaptive EGAT'25) |
| Subgraph migration / state placement | ClusterFlow'26, Databelt'25 |
| Lyapunov online scheduling of serverless DAGs | SFSM'24, which lists cold-start cost as its own future work |
| Tail-latency/SLO wording in general | 31 of 73 papers have ≥3 hits |

---

## 5. Recommended directions (combinations of gaps)

### Direction 1 (recommended): Robust, cost-aware reconfiguration (T1 + T2 on a T3 model, judged with T4 metrics)

**Working title.** *When to adapt and how much to trust the forecast: robust reconfiguration of serverless workflows at the edge.*

**Research question.** Consider a controller for serverless workflows at the edge that does two things:

1. It reconfigures only when the predicted queueing benefit over a horizon exceeds the switching cost (cold start, state migration, idle warm capacity).
2. It blends a learned demand forecast with a forecast-free fallback, using a trust parameter.

On non-stationary traces, does it achieve lower P99 makespan and fewer cold starts than periodic controllers (DFPS-style) and forecast-trusting controllers (Sdser/MPC-style)? And does its worst case stay bounded when the forecast is wrong?

**Method sketch.**
1. **Model.** Multi-instance queues per (function, node) with G/G/c approximations; fork-join makespan; real scale-to-zero; explicit switching cost.
2. **Trigger.** A cost-benefit test with hysteresis. Aim to prove that the number of reconfigurations is bounded by demand variation divided by the switching-cost threshold, i.e. no thrashing.
3. **Learning-augmented layer.** Interpolate with a trust parameter between the forecast-driven plan and a robust, forecast-free plan. Prove consistency and robustness in a reduced setting (single node, keep-alive as ski rental), then show it empirically on the full network.
4. **Solver.** Fast local search or LP rounding. If you reuse SA, fix E3 and E4.
5. **Forecaster.** Your GNN/time-series encoder serves as the "advice". This reuses your `objective-ideas` work (Ideas 3, 7, 10) without making "yet another DRL scheduler" the claim.

**Evaluation.**
- **Data:** Azure Functions and Huawei Cloud traces (Huawei: "Serverless Cold Starts and Where to Find Them", arXiv 2410.06145).
- **Scenarios:** diurnal patterns, bursts, popularity shifts, and controlled sweeps of forecast corruption.
- **Baselines:** corrected DFPS; a periodic controller with the best-tuned period (an oracle, for fairness); an Sdser-style predictive controller; an MPC-style controller; one DRL baseline; and an offline optimum or lower bound on small instances.
- **Metrics:** P50/P95/P99 makespan, cold starts, reconfiguration count, warm-memory-seconds, and decision overhead.
- **Testbed:** a small K3s + OpenFaaS/Knative setup to validate the simulator.

**Falsifier.** The "when" contribution fails if the best-tuned periodic controller matches it within noise on non-stationary traces. Trust blending isn't worth it if robustness costs more than a pre-registered share of consistency.

**Why this is Q1-level.** It fixes the core weakness that DFPS's own design creates and its evaluation never stresses. It offers a guarantee that none of the 73 corpus papers provides. And it is evaluated empirically across realistic, shifting conditions.

**Risks.** Theory may hold only in the reduced model, so state that honestly. Reviewers will ask "why not just RL?"; answer with the robustness guarantee and a DRL baseline.

**Venues.** IEEE TSC (where DFPS appeared), TPDS, TCC, TMC (if edge-focused), FGCS.

### Direction 2: Maximising SLO-goodput under overload (T4 + T6, on a T3 model)

**Research question.** Edge capacity is small, so overload (flash crowds, storage exhaustion) is normal. Does jointly deciding admission and degradation, together with critical-path-aware dispatch, deliver more SLO-meeting throughput than makespan-minimising schedulers that admit everything?

**Q1 angle.** The objective shifts from mean makespan to goodput, which is what operators care about. It uses fork-join tail approximations and admission rules with bounds.

**Risks.** Further from your existing notes; needs a convincing degradation model (e.g., cloud spill-over, approximate function variants).

**Venues.** TSC, TNSM, IoT-J, Computer Networks.

### Direction 3: Two-timescale co-design with learned encoders (T5; your Ideas 1, 2, 5, 7, 9)

**Research question.** Does a design where slow placement anticipates fast dispatch, through a learned model of how dispatch responds, beat both DFPS's decoupled approach and Heu's per-request joint approach?

**Fit.** Closest to your existing ideas.

**Risk.** Lowest novelty of the three: two-timescale designs already exist for monolithic services, and GNN/RL is crowded. To reach Q1 it must show something pure-RL papers lack, such as generalisation to unseen topologies or DAGs (Idea 9) or explicit awareness of reconfiguration cost (Idea 10). That pulls it towards Direction 1 anyway.

---

## 6. Read these before committing (directly competing, not yet inspected)

| Paper | Why |
|---|---|
| M. Sun et al., "Hybrid scheduling for serverless function workflows in edge computing system," FGCS, 2026, DOI 10.1016/j.future.2026.108822 | **Cites DFPS.** Same problem space; abstract not retrievable here. |
| Y. Lei et al., "Adaptive container scheduling for serverless workflows in cloud-edge collaborative computing," JPDC, 2026, DOI 10.1016/j.jpdc.2026.105308 | Same problem space, very recent. |
| M. Jayanthi et al., "Quantum-inspired bi-level scheduling for resource-aware serverless function deployment in edge computing," Discover Computing, 2026, DOI 10.1007/s10791-026-10504-3 | **Cites DFPS.** Bi-level design: neural-network demand prediction, quantum-inspired environment selection, PPO container selection. |
| C. Nguyen, M. Bhuyan, E. Elmroth, "Taming Cold Starts: Proactive Serverless Scheduling with Model Predictive Control," MASCOTS 2025 (arXiv 2508.07640) | Closest to Direction 1 on the predictive side. Uses MPC for pre-warming plus dispatch, on OpenWhisk, in the cloud. |
| METIS (SoCC'25) and Raptor (arXiv 2403.16457) | Critical-path and fork-join scheduling for serverless (Direction 2 / T4) |
| Wei & Zhang, NeurIPS 2020; Purohit et al., NeurIPS 2018 | Theory of robustness vs consistency for learning-augmented algorithms (T2) |

---

## 7. Checklist for a Q1-level version

- [ ] A formal model with complexity results (NP-hardness), plus at least one guarantee or a clearly principled mechanism
- [ ] Corrected DFPS (fixes for E1–E4 stated), the newest baselines, and an exact optimum or lower bound on small instances
- [ ] Real traces (Azure Functions, Huawei Cloud) and non-stationary scenarios; tail metrics; decision overhead
- [ ] A small real testbed (K3s + OpenFaaS/Knative/OpenWhisk) validating the simulator
- [ ] Ablations, sensitivity analysis, and statistics with confidence intervals and effect sizes; code released

---

## Sources (external)

- Wei & Zhang, Optimal Robustness-Consistency Trade-offs for Learning-Augmented Online Algorithms (NeurIPS 2020): https://papers.nips.cc/paper/2020/hash/5bd844f11fa520d54fa5edec06ea2507-Abstract.html — arXiv: https://arxiv.org/abs/2010.11443v1
- Online Learning for Function Placement in Serverless Computing (arXiv 2410.13696): https://arxiv.org/pdf/2410.13696
- Cost Optimization for Serverless Edge Computing with Budget Constraints using DRL (arXiv 2501.12783): https://arxiv.org/html/2501.12783v2
- Taming Cold Starts: Proactive Serverless Scheduling with Model Predictive Control (arXiv 2508.07640): https://arxiv.org/abs/2508.07640
- OptiFaaS project (TU Dortmund, DFG): https://pas.bci.tu-dortmund.de/research/projects/optifaas-towards-optimal-and-adaptive-allocation-of-faas/
- Serverless Cold Starts and Where to Find Them (Huawei traces): https://arxiv.org/html/2410.06145v1
- Raptor: Distributed Scheduling for Serverless Functions: https://arxiv.org/html/2403.16457v2
- METIS (SoCC'25 report): https://cis.temple.edu/~wu/research/publications/Publication_files/metis-socc25-report-Wenda%20Tang.pdf
- Farhadi et al., Service placement and request scheduling for data-intensive applications (ToN 2021): https://pure.psu.edu/en/publications/service-placement-and-request-scheduling-for-data-intensive-appli/
- Hudson et al., QoS-aware edge AI placement and scheduling (FGCS 2024): https://scholars.uky.edu/en/publications/qos-aware-edge-ai-placement-and-scheduling-with-multiple-implemen/
- Raith et al., UCC 2022: https://dsg.tuwien.ac.at/~sd/papers/UCC_2022_P_Raith.pdf
- Digital-twin replicas as serverless functions with mobility (IEEE TC 2024): https://unpaywall.org/10.1109%2FTC.2024.3388897
- Two-Stage Robust Edge Service Placement and Sizing: https://arxiv.org/pdf/2004.13218
- Robust Dynamic Edge Service Placement under Spatio-Temporal Correlated Demand: https://arxiv.org/pdf/2412.15608
- Resilient Edge Service Placement under Demand and Node Failure Uncertainties: https://arxiv.org/html/2107.04748v3
- Databelt (arXiv 2508.15351): https://arxiv.org/pdf/2508.15351
- SONIC (ATC'21): https://engineering.purdue.edu/dcsl/publications/papers/2021/sonic_atc21.pdf
- TopFull (SIGCOMM'24): https://ina.kaist.ac.kr/projects/topfull
- Tangram (serverless LLM loading): https://arxiv.org/html/2512.01357v1
- DFPS citing papers (Semantic Scholar): https://api.semanticscholar.org/graph/v1/paper/DOI:10.1109/TSC.2025.3592226/citations — metadata via Crossref: https://doi.org/10.1016/j.future.2026.108822 , https://doi.org/10.1016/j.jpdc.2026.105308 , https://doi.org/10.1007/s10791-026-10504-3
