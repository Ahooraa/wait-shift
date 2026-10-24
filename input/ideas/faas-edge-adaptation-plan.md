---
title: "Headroom-gated screening of DFPS weaknesses for serverless workflows at the edge"
type: plan
created: 2026-10-13
updated: 2026-10-13
status: pre-registered   # user confirmed the Hypothesis, Falsification Criteria and thresholds as written on 2026-10-13; frozen
methodology: quantitative
author: mixed
design: "[[faas-edge-adaptation-design]]"
---

# Headroom-Gated Screening of DFPS Weaknesses — Research Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `research-superpowers:executing-research-plan` to run this plan task by task. Tasks use checkbox (`- [ ]`) syntax for TodoWrite integration.

**Research Question:** DFPS-style control of serverless workflows at the edge has three candidate weaknesses:
- **D1:** reconfiguration that is clock-driven, cost-blind and forecast-free
- **D2:** dispatch that admits everything and optimises the mean during overload
- **D3:** placement decoupled from dispatch

Which of these leaves enough exploitable headroom under realistic, non-stationary workloads to support a Q1 contribution? And does a practical method for the best-ranked direction capture that headroom?

**Hypothesis (pre-registered, immutable):** At least one direction shows oracle headroom of ≥ 25% (lower bound of the 95% CI) on its primary metric over the best-tuned corrected-DFPS baseline, in at least 2 of 3 trace families (H1–H3). The method built for the selected direction then captures ≥ 50% of that headroom on held-out test traces (H4).

**Falsification Criteria:**
- **Per direction (screening):** H1, H2 or H3 is falsified (KILL) when the CI lower bound of headroom is < 10% in all three trace families.
- **Screening as a whole:** falsified if no direction reaches GO.
- **H4 refuted:** the 95% CI upper bound of the capture ratio on test traces is < 0.5, or the 95% CI of the paired improvement over the strongest baseline includes 0.
- **H4 inconclusive:** the capture ratio's CI straddles 0.5.

**Stop Criterion:**
- **Screening:** stops when each headroom cell has 10 paired workload instances, across 3 trace families × 3 load levels on dev data, or when the task's timebox is exhausted. In the latter case the direction can be rated MAYBE at best.
- **Confirmation:** uses 20 held-out instances per family × load level, generated once in Task 18 and never inspected earlier.

**Method:** Trace-driven discrete-event simulation with a validated simulator and a corrected DFPS reimplementation (B*). The plan runs in stages:
1. A cheap practicality screen on the raw traces.
2. A clairvoyant-oracle headroom experiment plus a simple-heuristic check for each direction.
3. A pre-registered selection rule at gate G3.
4. Method development under a viability gate (G4).
5. A confirmatory run on held-out traces (G5) and a small Kubernetes testbed check (G6).

**Output target:** article (Q1 journal: IEEE TSC, TPDS, TCC, or FGCS)
**Language:** en

---

## Pre-registered Definitions

| Item | Definition |
|---|---|
| Primary metric (D1, D3) | P99 end-to-end workflow makespan: from request arrival at the controller to completion of the last task, including queueing, cold starts and state transfers |
| Primary metric (D2) | SLO-goodput: workflows completed within their SLO per second. SLO_w = 3 × the unloaded critical-path makespan of workflow w |
| Secondary metrics | Mean makespan, cold-start count, reconfiguration count, warm-memory-seconds (idle warm-instance time × memory), decision overhead (ms per decision, p95) |
| Baseline B* | DFPS with E1–E4 corrected (see the gap evaluation, §1a): Eq. 3 with \|·\|; Eq. 6 as Erlang-C with P₀ and μ as a rate; Alg. 2 accepting worse moves with probability e^(Δ/T) and keeping the best solution so far; Alg. 1 appending to FRQ_ns and removing moved requests. Replacement period T* tuned per trace family on dev data from {1, 2, 4, 8, 16, 32, 64} s |
| Headroom h | (m_B* − m_O) / m_B* for minimised metrics; (m_O − m_B*) / m_B* for goodput. Computed per paired instance (same arrivals, same seeds), reported as mean ± 95% bootstrap CI (10,000 resamples) |
| Decision rule | **GO**: CI lower bound of h ≥ 0.25 in ≥ 2 of 3 families. **KILL**: CI lower bound < 0.10 in all 3 families. **MAYBE**: anything else |
| Heuristic saturation | If the direction's simple heuristic captures ≥ 70% of the oracle headroom (mean of (m_B* − m_H)/(m_B* − m_O)) in ≥ 2 families, downgrade GO → MAYBE |
| Load levels | Median offered utilisation ρ ∈ {0.5, 0.7, 0.85} of total container capacity |
| Trace families | **F1:** Azure Functions 2019 per-minute invocation counts (top 200 functions by volume, mapped to workflow entry points), with durations from the Azure 2021 per-invocation trace. **F2:** Huawei public 2023 per-second request series. **F3:** DFPS-style synthetic Poisson (Uniform/Pareto) with popularity regime shifts every 10 min |
| Dev/test split | F1 and F2: first 60% of each trace's time span = dev, last 40% = test. F3: seeds 0–9 = dev, seeds 100–119 = test |
| Workflows | SeBS-Flow application workflows, the DFPS Fig. 1 image-processing workflow, and Alibaba-2018 batch DAGs filtered as in DFPS. Durations are sampled from Azure 2021 empirical distributions, cold starts from Huawei 2025, and state sizes from 10–50 MB |
| Infrastructure | 80 edge nodes on Waxman topologies (the GT-ITM style used by DFPS), 5–25 container slots, 10–30 GB storage, 50 MB/s links (DFPS Table 2). Link contention can be switched between off (DFPS Eq. 1–2) and fair-share |

## Screening Hypotheses (pre-registered)

| ID | Direction (gaps) | Oracle | Simple heuristic | Practicality check (gate G1) | Extra decision |
|---|---|---|---|---|---|
| H1 | D1: when to reconfigure (T1) | O1: offline trigger oracle (DP over 10-s slots with true future rates and switching cost) | Rate-change trigger (\|Δλ\|/λ ≥ 0.3), no cost model | Median top-200 function has ≥ 1 change point/h, or ≥ 5% of 1-min windows deviate ≥ 2× from the trailing 10-min mean | Report h_timing = (P_true − O1)/P_true. If its CI lower bound < 0.10, the "when" claim is dropped and D1 reduces to forecasting |
| H1b | D1 add-on: forecasts with worst-case guarantee (T2) | P_true: perfect forecasts at period T* | Forecast-trusting controller P_fc (seasonal-naive forecast plus injected error σ ∈ {0.25, 0.5, 1.0}) | — | Include the learning-augmented layer only if both hold: (a) CI lower bound of h_forecast = (B* − P_true)/B* ≥ 0.10; (b) P_fc is ≥ 10% worse than B* (CI lower bound) in ≥ 1 family at σ ≤ 0.5 |
| H2 | D2: overload admission + critical-path dispatch (T4 + T6) | O2: offline admission oracle (knows future arrivals and true durations) + critical-path dispatch | Queue-length-threshold admission | ≥ 5% of 1-min windows overloaded at median ρ = 0.7 (2–5% → MAYBE; < 2% → KILL for practicality) | Also report P99 makespan of admitted workflows |
| H3 | D3: coupled placement–dispatch (T5) | O3: simulation-in-the-loop placement (K = 32 candidates scored on the actual upcoming requests) | Affinity-greedy placement (co-locate DAG neighbours, weighted by state size × rate) | — | If the corrected queueing surrogate ranks candidates with Kendall τ ≥ 0.7 against simulation, the learned-encoder angle adds little: downgrade GO → MAYBE |

**Selection rule at G3:**
- Pick the GO direction with the highest CI lower bound of h. Ties (within 0.05) go to the higher gap-evaluation score (D1 = 21, D3 = 20, D2 = 17–20).
- Only one direction enters method development. A second GO direction may be merged only after the first passes G4.
- If no direction reaches GO: present the ledger and let the user choose a MAYBE direction or the fallback (Task 21).

## Gates and Timeboxes

| Gate | Passes when | Max effort spent if it fails |
|---|---|---|
| G0 Novelty | No direction is pre-empted by Sun 2026, Lei 2026, Jayanthi 2026 or Nguyen 2025 (Task 2) | ≈ 10 h |
| G1 Trace practicality | Thresholds in the screening table (Task 5); failing affects only the direction concerned | ≈ 28 h |
| G2 Harness validity | Validation tests pass and ≥ 2 of 3 DFPS qualitative claims reproduce (Tasks 8, 10) | ≈ 75 h (harness reusable for every direction and the fallback) |
| G3 Headroom | At least one GO (Tasks 11–14) | ≈ 113 h |
| G4 Method viability | Capture ratio ≥ 0.30 on dev traces (mean, ≥ 2 families) and decision overhead p95 ≤ 50 ms, within 60 h (+ one 20 h refinement round) | +80 h, then pivot or fallback |
| G5 Confirmation | H4 confirmed (Task 18) | — (any outcome is reported) |
| G6 Sim-to-real | Testbed improvement has the same sign and is ≥ 50% of the simulated improvement (Task 19) | Reported as a limitation |

**Overrun rule:** if any task exceeds its timebox by 50%, stop, log it in `knowledge/_meta/log.md`, and review with the user before continuing.

---

## Data Sources

**Literature: on disk** (user corpus: `C:\Users\ahoor\Desktop\University\Papers\function placement papers\most-related\Ranked Papers\` and `...\most-related\`), add to library and ingest:
- [[zolfaghari2025dynamic]] — DFPS, IEEE TSC 2025, DOI 10.1109/TSC.2025.3592226 — *on disk, ingest pending*
- [[liu2025sdser]] — Sdser (Liu, Zhou, Ma) — *on disk, ingest pending*
- [[ma2025online]] — Online deployment of dynamic edge DAG functions / OPTS (Ma et al.) — *on disk, ingest pending*
- [[guo2026popularity]] — Popularity-aware layer-wise caching (Guo et al., IEEE TMC 2026) — *on disk, ingest pending*
- [[tian2024sfsm]] — SFSM (Tian et al.) — *on disk, ingest pending*
- [[ahmadpanah2026clusterflow]] — ClusterFlow (Computer Networks 2026) — *on disk, ingest pending*
- [[li2022faasflow]] — FaaSFlow (Li et al.) — *on disk, ingest pending*
- [[jia2025faaspr]] — FaaSPR (IEEE ToN 2025) — *on disk, ingest pending*
- [[galavani2026jet]] — JET (Galavani, Younesi, Ansari) — *on disk, ingest pending*
- [[xu2026structure]] — GRL-Orch (Xu, Ding) — *on disk, ingest pending*
- [[fan2026deep]] — DMPPO-WS (Fan et al.) — *on disk, ingest pending*
- [[liang2023edgeorcher]] — EdgeOrcher (Liang, Zhou, Chen) — *on disk, ingest pending*
- [[adamek2026large]] — Large-scale workflow placement with INLP (IEEE Access 2026) — *on disk, ingest pending*

**Literature: acquire pending:**
- [[sun2026hybrid]] — FGCS 2026, DOI 10.1016/j.future.2026.108822 — *paywalled, G0-critical*
- [[lei2026adaptive]] — JPDC 2026, DOI 10.1016/j.jpdc.2026.105308 — *paywalled, G0-critical*
- [[jayanthi2026quantum]] — Discover Computing 2026, DOI 10.1007/s10791-026-10504-3 — *G0*
- [[nguyen2025taming]] — MPC cold starts, MASCOTS 2025, arXiv:2508.07640 — *open access, G0*
- [[exton2024raptor]] — Raptor (Exton, Read), arXiv:2403.16457 — *open access*
- [[joosen2024serverless]] — Serverless cold starts and where to find them (Joosen et al.), arXiv:2410.06145 — *open access; documents the Huawei traces*
- [[schmid2025sebsflow]] — SeBS-Flow, EuroSys 2025, DOI 10.1145/3689031.3717465, arXiv:2410.03480 — *open access*
- [[shahrad2020serverless]] — Serverless in the Wild, USENIX ATC 2020 — *open access; documents the Azure 2019 trace*
- [[wei2020optimal]] — Robustness–consistency trade-offs, NeurIPS 2020 — *open access*
- [[purohit2018improving]] — Online algorithms via ML predictions, NeurIPS 2018 — *open access*
- [[farhadi2021service]] — Two-timescale placement and scheduling, IEEE/ACM ToN 2021 — *paywalled*
- [[rausch2021optimized]] — Skippy / faas-sim, FGCS 2021 — *paywalled*
- [[xu2023stateful]] — Heu baseline used by DFPS, IEEE TC 2023 — *paywalled*
- [[yang2025multiobjective]] — RL baseline used by DFPS, IEEE TSC 2025 — *paywalled*

**Gap evaluation (on disk):** `input/description/dfps-gap-evaluation.md` (moved from the workspace root in Task 0).

**Datasets (download pending; URLs verified 2026-10-13):**
- **Azure:** https://github.com/Azure/AzurePublicDataset
  - AzureFunctionsDataset2019: per-minute invocation counts, per-function duration distributions, per-app memory; about 2 weeks of July 2019.
  - AzureFunctionsInvocationTrace2021: per-invocation end timestamp and duration in ms; 2 weeks from 2021-01-31.
  - Destination: `input/data/azure/`
- **Huawei:** https://github.com/sir-lab/data-release
  - Huawei Public cold start traces 2025: 31 days, 5 regions, 19 metrics per function.
  - Huawei public traces 2023: per-minute and per-second request time series, 235 days.
  - Destination: `input/data/huawei/`
- **Alibaba:** https://github.com/alibaba/clusterdata (cluster-trace-v2018 batch DAGs). Destination: `input/data/alibaba/`
- **SeBS-Flow workflows:** https://github.com/spcl/serverless-benchmarks (`benchmarks/600.workflows`). Destination: `input/data/workflows/sebs-flow/`
- **Simulator candidate:** https://github.com/edgerun/faas-sim (MIT, SimPy; DAG support not documented, evaluated in Task 6).

**Handling rule:** extract each downloaded archive into its own new directory. Keep scripts in `output/data-analysis/`, outside the data directories, and run them with `python -I`.

---

## Tasks

### Task 0: Scaffold the project (timebox 1 h)
**Files:** `CLAUDE.md`, `knowledge/`, `output/`, `scripts/`, `input/description/dfps-gap-evaluation.md`, `output/data-analysis/results/headroom-ledger.md`

- [x] Run `scaffold-research-project` (methodology: quantitative; discipline: computer science / distributed systems; language: en). Preserve the existing `input/ideas/faas-edge-adaptation-*.md` and `knowledge/_meta/gate-overrides.log`
- [x] Move `DFPS-limitations-and-gap-evaluation.md` → `input/description/dfps-gap-evaluation.md`
- [x] Update the gap-evaluation path in `input/ideas/faas-edge-adaptation-design.md` and in this plan
- [x] Create `output/data-analysis/results/headroom-ledger.md` with one row per gate (G0–G6) and these columns: direction, metric, value, CI, threshold, decision, date

### Task 1: Acquire source PDFs (timebox 3 h)
**Files:** `<library>/pdf/*.pdf`, `input/bibliography/acquisition-todo.md`

- [x] Run `acquire-sources` on the 14 acquire-pending keys above
- [x] Manually download the paywalled originals through the university VPN: sun2026hybrid, lei2026adaptive, jayanthi2026quantum, farhadi2021service, rausch2021optimized, xu2023stateful, yang2025multiobjective
- [x] Add the 13 on-disk corpus PDFs with `add-to-library`, copying rather than moving them from the user's folder
- [x] Re-run `acquire-sources` to reconcile; record anything still missing as explicitly deferred

### Task 2: Gate G0 — novelty check against the newest competitors (timebox 6 h)
**Files:** `knowledge/sources/sun2026hybrid.md`, `knowledge/sources/lei2026adaptive.md`, `knowledge/sources/jayanthi2026quantum.md`, `knowledge/sources/nguyen2025taming.md`, `input/bibliography/literaturguide.md`, `output/data-analysis/results/headroom-ledger.md`

- [x] Ingest sun2026hybrid. Focus: whether it decides when to reconfigure, uses forecasts with guarantees, does admission control, or couples placement and dispatch
- [x] Ingest lei2026adaptive (same focus)
- [x] Ingest jayanthi2026quantum (same focus)
- [x] Ingest nguyen2025taming. Focus: MPC horizon, trigger policy, robustness to forecast error
- [x] Run `literature-review` (search only) with the queries below, saving the hits to `literaturguide.md`:
  - "event-triggered reconfiguration serverless"
  - "learning-augmented OR algorithms with predictions + keep-alive OR placement"
  - "admission control serverless workflow edge"
  - METIS (SoCC 2025) metadata
- [x] For D1, D2 and D3, record in the ledger one of: *pre-empted* (a 2024–2026 paper already does the core idea for workflows at the edge), *partially overlapping*, or *clear*
- [x] A pre-empted direction is KILLed for novelty, unless a one-sentence differentiator is written and approved by the user (log it)

### Task 3: Ingest foundational sources (timebox 6 h)
**Files:** `knowledge/sources/*.md`, `output/bibtex/references.bib`

- [x] Ingest zolfaghari2025dynamic. Focus: reproduction parameters (Table 2), E1–E6 corrections, evaluation protocol
- [x] Ingest liu2025sdser and ma2025online. Focus: prediction and pre-deployment, as baseline designs
- [x] Ingest guo2026popularity and tian2024sfsm. Focus: online guarantees and the assumptions they need
- [x] Ingest exton2024raptor, joosen2024serverless and shahrad2020serverless. Focus: duration, arrival and cold-start distributions for the simulator
- [x] Ingest wei2020optimal and purohit2018improving. Focus: robustness–consistency results usable for H1b
- [x] Ingest schmid2025sebsflow. Focus: workflow DAG shapes, fan-out and payload sizes
- [ ] Verify all BibTeX entries with `research-desk:citation-check`

### Task 4: Acquire datasets (timebox 4 h)
**Files:** `input/data/azure/`, `input/data/huawei/`, `input/data/alibaba/`, `input/data/workflows/sebs-flow/`, `input/data/README.md`

- [x] Download AzureFunctionsDataset2019 and AzureFunctionsInvocationTrace2021 into `input/data/azure/` (one new directory per archive)
- [x] Download the Huawei 2023 public traces (per-second request series) and the Huawei 2025 cold-start traces into `input/data/huawei/`
- [x] Download cluster-trace-v2018 `batch_task` into `input/data/alibaba/`
- [x] Copy the SeBS-Flow workflow definitions (`benchmarks/600.workflows`) into `input/data/workflows/sebs-flow/`
- [x] Record size, sha256, licence and download date for each dataset in `input/data/README.md`
- [x] If a dataset exceeds 50 GB, keep a documented subset (7 days, top 200 functions by volume) and log the reduction

### Task 5: Gate G1 — trace practicality screen, no simulator (timebox 8 h) — pre-registered
**Files:** `output/data-analysis/g1_trace_screen.py`, `output/data-analysis/results/g1_trace_screen.json`

- [x] Load F1 (Azure 2019, per-minute) and F2 (Huawei 2023, aggregated to 10 s and 1 min) for the top 200 functions by volume, dev span only
- [x] D1 metric 1: change points per hour per function (PELT from `ruptures`, penalty 2·ln n)
- [x] D1 metric 2: share of 1-min windows whose rate deviates ≥ 2× from the trailing 10-min mean
- [x] D2 metric: provision capacity so that median utilisation = 0.7, then compute the share of 1-min windows with offered load > capacity
- [x] Tail check: squared coefficient of variation (SCV) of per-invocation durations (Azure 2021). Expected ≫ 1; record the value
- [x] Apply the G1 thresholds from the screening table and write the G1 rows of the ledger
- [x] If D1 or D2 fails G1, skip its headroom task (11 or 12) and log the skip

### Task 6: Harness decision (timebox 3 h)
**Files:** `output/data-analysis/sim/DECISION.md`

- [~] Install faas-sim in an isolated virtual environment (skipped: reuse of dfps/ approved, see log)
- [~] Try to express a toy case in it (skipped, same reason)
- [x] Decision: extend dfps/ in place (neither faas-sim nor a new simulator)
- [x] Record the decision and the reasons in `DECISION.md`

### Task 7: Simulator core (timebox 20 h; reduced to extensions of dfps/, see DECISION.md)
**Files:** `dfps/sim.py`, `dfps/matching.py`, `dfps/traces.py`, `tests/test_invariants.py`, `tests/test_traces.py`

- [x] Model, engine, network (DFPS Eq. 1-2): already present in `dfps/`; audited in `output/data-analysis/sim/DECISION.md`
- [x] `traces.py` (workload): non-homogeneous arrivals by thinning (F1/F2 replay, F3 popularity regime shifts), calibration to offered utilisation rho, empirical heavy-tail duration sampler (Azure 2021 shape rescaled to mu_l); trace loaders with cache
- [x] Metrics: P50/P95/P99, SLO-goodput (SLO = 3 x unloaded critical path), rejected count, no-op re-plan count, warm-idle slot-seconds, decision time (p95 of re-plan and per-request scheduling)
- [x] Hooks: admission(sim, req), exec_sampler(f, rng), adjuster may return None (no reconfiguration) and set `next_interval` (event/cost-triggered controllers)
- [x] Seeded randomness and event-log hash (blake2b over event stream)
- [~] Link contention (fair-share): deferred to Task 17 sensitivity (default off = DFPS)
- [~] Cold-start sampler from Huawei 2025: deferred (static per-function cold starts as in DFPS); needed only for the sensitivity sweep
- [~] Scale-to-zero instances: deferred; decide when H1b (keep-alive trust) is built
- Runtime: `matching.py` sped up 1.4x with identical schedules (45 compared); scheduling is still about 15 ms per arrival (about 95% of wall time). Windows must be shortened (see log)

### Task 8: Simulator validation (timebox 6 h; part of G2) — pre-registered
**Result (2026-10-13): all criteria PASS** (g2_validation.json). **Files:** `output/data-analysis/sim/tests/test_validation.py`, `output/data-analysis/results/g2_validation.json`

- [x] **M/M/c check:** one node, one function, c ∈ {1, 4, 16}, ρ ∈ {0.5, 0.8, 0.9}. Simulated mean wait must be within 5% of Erlang-C (with P₀) over 10⁶ requests
- [x] **Little's law:** L = λW within 2%
- [x] **Conservation:** arrivals = completions + in-flight at the end, in every run
- [x] **Determinism:** the same seed gives an identical event-log hash
- [x] **Runtime budget:** one simulated hour at 80 nodes and ρ = 0.85 takes ≤ 10 min wall clock. If it doesn't, shorten runs to 30-min windows and log the change

### Task 9: DFPS (as printed and corrected), static baselines, simple heuristics (timebox 14 h; reduced to audit + missing pieces)
**Files:** `dfps/variants.py`, `dfps/controllers.py`, `dfps/sa.py`, `dfps/matching.py`, `dfps/solution.py`, `tests/test_controllers.py`

- [x] NSGA-II initial placement with Eq. 3 as printed (`prop_variant="signed"`) and with |.| (E1): existing, tested (`test_nsga2.py`)
- [x] Queue estimate: Eq. 6 as printed and corrected Erlang-C with P0 and mu as a rate (E2): existing (`queueing.py`, `fst_variant`)
- [x] Matching: total weight (as printed) and critical-path variant (E5): `match(..., objective="critical")`, `Sim(match_objective=...)`; new
- [x] Annealing: printed acceptance and corrected e^(delta/T) (`accept`), plus best-so-far (`best_so_far`, E3): best-so-far new
- [x] Alg. 1 corrected queue handling (E4): existing in `sa.py`, tested (`test_sa.py`)
- [x] SR and SG static baselines (DFPS 5.1): existing (`experiments/run.py`)
- [x] Heuristics: rate-change trigger (D1), queue-threshold admission (D2), affinity-greedy placement (D3): new (`controllers.py`)
- [x] Unit tests for every component (65 fast tests pass)
- [x] B* / AS_PRINTED defined in `variants.py` (E1-E4 corrected / left as printed); E5 is a method choice, not part of B*
- Note: erratum numbering differs between the gap evaluation (E1-E6) and PLAN.md/DEVIATIONS.md (E-1, E-2, E-5, E-6); this plan uses the gap evaluation's. Departure from PLAN.md: B* adds best-so-far (PLAN.md L-1 keeps "return last")

### Task 10: Gate G2 — DFPS reproduction and B* tuning (timebox 4 h) — pre-registered
**Files:** `output/data-analysis/g2_reproduction.py`, `output/data-analysis/results/g2_reproduction.json`

- [x] Run DFPS's own setting for DFPS-as-printed, DFPS-corrected, SR and SG, with 10 instances each:
  - F3 Uniform and Pareto, 80 nodes, 15 workflows
  - Table 2 parameters, arrival scale 0.25–2.0
- [x] Check DFPS's three qualitative claims:
  - (i) makespan rises with the arrival scale for every method
  - (ii) under Pareto, mean makespan ranks DFPS < SG < SR
  - (iii) SR and SG have zero cold starts
- [x] Report the as-printed vs corrected difference in mean and P99 makespan (motivation material)
- [x] G2 passes if Task 8 passes and at least 2 of the 3 claims reproduce. If claim (ii) fails, investigate for at most 4 h, log the finding and continue with corrected DFPS as B*
- [x] Tune T* per trace family on dev data from {1, 2, 4, 8, 16, 32, 64} s and record T* in the ledger

### Task 11: D1 headroom — when to reconfigure + value of forecasts (timebox 12 h) — pre-registered
**Files:** `output/data-analysis/sim/controllers/oracles.py`, `output/data-analysis/d1_headroom.py`, `output/data-analysis/results/d1_headroom.json`

- [ ] P_true: corrected DFPS at period T*, using the true future per-function rates (perfect forecast)
- [ ] O1, an offline trigger oracle:
  - dynamic programming over 10-s slots, choosing in each slot to keep the current placement or switch to one computed from that slot's true rates
  - slot cost = corrected queueing model plus switching cost (cold starts × sampled cold-start delay)
  - evaluate the chosen schedule by full simulation
- [ ] P_fc: forecast-trusting controller using a seasonal-naive forecast, plus injected multiplicative error σ ∈ {0.25, 0.5, 1.0}
- [ ] Run B*, P_true, O1, P_fc(σ) and the rate-change heuristic on F1–F3 dev data, ρ ∈ {0.5, 0.7, 0.85}, 10 paired instances
- [ ] Compute, with bootstrap CIs:
  - h_total = (B* − O1)/B*
  - h_timing = (P_true − O1)/P_true
  - h_forecast = (B* − P_true)/B*
  - P_fc vs B*
  - heuristic saturation
- [ ] Write the ledger rows: D1 = GO / MAYBE / KILL; H1b learning-augmented layer = include / exclude

### Task 12: D2 headroom — overload admission + critical-path dispatch (timebox 10 h) — pre-registered
**Files:** `output/data-analysis/d2_headroom.py`, `output/data-analysis/results/d2_headroom.json`

- [ ] Build overload scenarios from the windows G1 identified as overloaded (F1, F2), plus synthetic bursts where ρ ramps to 1.2 and 1.5 for 2–10 min
- [ ] O2: offline admission oracle (greedy by marginal goodput, with known future arrivals and true durations) plus critical-path dispatch
- [ ] Run B* (admit-all), O2 and the queue-threshold heuristic, with 10 paired instances per scenario × family
- [ ] Compute the goodput gain with CIs, heuristic saturation, and P99 makespan of admitted workflows
- [ ] Write the ledger row: D2 = GO / MAYBE / KILL

### Task 13: D3 headroom — coupled placement–dispatch (timebox 14 h) — pre-registered
**Files:** `output/data-analysis/d3_headroom.py`, `output/data-analysis/results/d3_headroom.json`

- [ ] O3: at each period, generate K = 32 candidate placements by corrected local search from the current one, score each by simulating the next window on the actual upcoming requests, and pick the best
- [ ] Run B*, O3 and the affinity-greedy heuristic on F1–F3 dev data, 3 load levels, 10 instances
- [ ] Surrogate check: Kendall τ between the corrected queueing model's ranking of the 32 candidates and the simulated ranking, averaged over periods
- [ ] Compute h with CIs, heuristic saturation and τ
- [ ] Write the ledger row: D3 = GO / MAYBE / KILL, applying the τ ≥ 0.7 downgrade

### Task 14: Gate G3 — select the direction and freeze H4 specifics (timebox 2 h)
**Files:** `output/data-analysis/results/headroom-ledger.md`, `knowledge/synthesis/headroom-results.md`, `knowledge/_meta/log.md`

- [ ] Apply the selection rule and write the decision, with numbers, to the ledger
- [ ] Write `knowledge/synthesis/headroom-results.md`: the H1–H3 results table, the decomposition plots and the decision rationale
- [ ] Freeze H4's specifics in `log.md`: selected direction, primary metric, oracle headroom value, baseline set, test-instance generation seeds. The user confirms before any Task 15 work
- [ ] If no direction reaches GO, present the ledger to the user and choose: a MAYBE direction (logged as exploratory) or the fallback (Task 21)

### Task 15: Gate G4 — method MVP for the selected direction (timebox 60 h + one 20 h refinement round)
**Files:** `output/data-analysis/sim/controllers/proposed.py`, `output/data-analysis/g4_mvp.py`, `output/data-analysis/results/g4_mvp.json`

- [ ] Implement the MVP for the selected direction:
  - **D1:** a cost-benefit trigger with hysteresis (expected queueing benefit over horizon H vs switching cost) on the corrected queueing model. If H1b passed, add a trust-λ blend of forecast-driven and forecast-free plans
  - **D2:** marginal-goodput admission using queue and storage state, plus fork-join/critical-path dispatch
  - **D3:** coupled placement scored by a dispatch-response surrogate (analytic, or learned if τ < 0.7)
- [ ] Evaluate on dev data with the Stage 3 grid
- [ ] Compute the capture ratio c = (B* − MVP)/(B* − Oracle) and the p95 decision overhead
- [ ] G4 passes if c ≥ 0.30 (mean, ≥ 2 families) and overhead ≤ 50 ms
- [ ] If G4 fails: run one 20 h refinement round. If it still fails, pivot to the next-ranked GO/MAYBE direction or to the fallback, and log the pivot

### Task 16: Theory component (timebox 40 h)
**Files:** `knowledge/synthesis/theory-notes.md`, `output/article/text/appendix-proofs.qmd`

- [ ] **All directions:** NP-hardness of the selected problem by reduction (from bin packing or the generalised assignment problem); state the reduction precisely
- [ ] **D1 with H1b:** single-node keep-alive as ski rental with predictions. Derive the consistency/robustness of the trust-λ rule, building on wei2020optimal and purohit2018improving
- [ ] **D1:** bound the number of reconfigurations by (total variation of demand)/(threshold) under hysteresis. Prove it, or downgrade it to an empirical claim
- [ ] **D2/D3:** numerically validate the tail or surrogate approximation used, with its error against simulation
- [ ] Label every claim proved / computer-assisted / numerical / conjectured (`research-integrity:research-integrity`)

### Task 17: Full method, baselines, ablations and sensitivity, dev data only (timebox 50 h)
**Files:** `output/data-analysis/sim/controllers/baselines_extra.py`, `output/data-analysis/ablations.py`, `output/data-analysis/results/ablations.json`, `output/data-analysis/results/sensitivity.json`

- [ ] Complete the method. Ablate each component (trigger off, trust fixed at 0 and 1, cost model off, admission off, critical-path off, as applicable)
- [ ] Add baselines:
  - an Sdser-style predictive pre-deployment controller (liu2025sdser)
  - an MPC-style controller (nguyen2025taming)
  - one PPO-based DRL controller in the style of fan2026deep, with its training budget documented
  - Heu (xu2023stateful) if it fits the timebox
- [ ] Sensitivity sweeps:
  - state size {1, 10, 50, 200} MB
  - link contention off / on
  - cold-start scale × {0.5, 1, 2}
  - nodes {20, 80, 160}

### Task 18: Gate G5 — confirmatory evaluation on held-out test traces (timebox 12 h) — pre-registered
**Files:** `output/data-analysis/g5_confirmatory.py`, `output/data-analysis/results/g5_confirmatory.json`

- [ ] Generate the test instances once: F1/F2 test spans and F3 seeds 100–119, giving 20 instances per family × load level
- [ ] Run the proposed method, all baselines and the oracle
- [ ] Compute:
  - paired improvements with 95% bootstrap CIs
  - Wilcoxon signed-rank tests with Holm correction across families
  - rank-biserial effect sizes
  - the capture ratio with its CI
- [ ] Record the H4 verdict (confirmed / refuted / inconclusive) in `knowledge/_meta/log.md`, without editing this plan

### Task 19: Gate G6 — sim-to-real check on a small testbed (timebox 30 h)
**Files:** `output/testbed/cluster.md`, `output/testbed/deploy/`, `output/testbed/results/g6_testbed.json`

- [ ] Set up 4–6 nodes: K3s on VMs or Raspberry Pis, OpenFaaS or Knative, and `tc netem` for 50 MB/s inter-node bandwidth and delay
- [ ] Implement the selected controller as an external placement/dispatch agent using the Kubernetes API, with corrected DFPS as the baseline
- [ ] Run 2 SeBS-Flow workflows on a down-scaled F1 test trace: 30 min, 3 seeds per controller
- [ ] Run the same scenario in the simulator, configured to match the testbed
- [ ] G6 passes if the testbed improvement has the same sign and is ≥ 50% of the simulated one. Otherwise spend ≤ 6 h analysing the discrepancy and report it as a limitation

### Task 20: Synthesis pages (timebox 8 h)
**Files:** `knowledge/synthesis/dfps-limitations.md`, `knowledge/synthesis/related-work-positioning.md`, `knowledge/synthesis/evaluation-results.md`

- [ ] `dfps-limitations.md`: built from `input/description/dfps-gap-evaluation.md` plus the G2 numbers (printed vs corrected)
- [ ] `related-work-positioning.md`: ≥ 25 sources from `output/bibtex/references.bib`, grouped into pre-warming/prediction, caching, fusion, online guarantees, two-timescale, tail/critical path, and robust placement
- [ ] `evaluation-results.md`: the G5 and G6 numbers and the list of planned figures and tables
- [ ] Set each page to `status: stable` after user review

### Task 21: Fallback — realism re-evaluation study (only if chosen at G3; timebox 60 h)
**Files:** `output/data-analysis/fallback_reeval.py`, `output/data-analysis/results/fallback_reeval.json`, `knowledge/synthesis/realism-reevaluation.md`

- [ ] Evaluate DFPS-as-printed, DFPS-corrected, SR, SG, Heu and an Sdser-style controller under each fidelity toggle:
  - heavy-tailed durations
  - link contention
  - non-stationary traces
  - empirical cold starts
- [ ] Test whether DFPS's method ranking holds under each toggle (Kendall τ of the rankings, with CIs)
- [ ] Switch the output target to an evaluation-realism article (e.g., FGCS) and log the change

### Task 22: Draft the article
**Files:** `output/article/text/01-introduction.qmd` … `output/article/text/07-conclusion.qmd`

- [ ] Confirm `wiki-lint` is green
- [ ] Draft via `drafting-manuscript`, with citations as `[@bibkey]` from `output/bibtex/references.bib`. Target lengths:

| Section | Words |
|---|---|
| `01-introduction.qmd` | 1,500–2,000 |
| `02-related-work.qmd` | 1,800–2,500 |
| `03-system-model.qmd` (formulation and NP-hardness) | 1,800–2,500 |
| `04-method.qmd` | 2,500–3,500 |
| `05-evaluation.qmd` (G5 primary results, ablations, sensitivity, G6) | 3,500–4,500 |
| `06-discussion-limitations.qmd` | 900–1,300 |
| `07-conclusion.qmd` | 350–600 |

### Task 23: Review and release
**Files:** `output/article/review/`, `output/artifact/README.md`

- [ ] Run `requesting-peer-review` (constructive and adversarial) and resolve the major points
- [ ] Run `research-desk:citation-check` on the final bibliography
- [ ] Package the code, configs, seeds and result JSONs. Write `output/artifact/README.md` with commands that reproduce every table

---

## Verification

The project is complete when:
- [ ] `headroom-ledger.md` has a row for every gate G0–G6, with values, CIs, thresholds and decisions, or an explicit "not reached" with the reason
- [ ] Every Task 8 validation criterion passes and is stored in `g2_validation.json`
- [ ] Every headroom cell has 10 paired instances and a 95% CI
- [ ] The H1–H3 decisions are timestamped in `log.md` before the first commit of `proposed.py`
- [ ] The H4 verdict is stated as confirmed, refuted, or "inconclusive — exploratory"
- [ ] ≥ 25 sources are ingested with `status: stable` or `review`
- [ ] `scripts/lint-wiki.py` exits 0
- [ ] The article renders without errors
- [ ] One peer-review round is completed
- [ ] Re-running `g5_confirmatory.py` from the artifact reproduces the reported numbers within 1%

## Effort Summary

| Stage | Tasks | Timebox (h) |
|---|---|---|
| Screening (to G3) | 0–14 | ≈ 113 |
| Development (G4) | 15–17 | 150–170 |
| Confirmation (G5, G6) | 18–19 | 42 |
| Writing and release | 20, 22, 23 | ≈ 80 |
| **Total** | | **≈ 385–405** |

## Deviations Log

Append to `knowledge/_meta/log.md`, referencing the slug `faas-edge-adaptation`, whenever scope, method, thresholds or data sources change after pre-registration. Results that follow a deviation are marked exploratory, never confirmatory.
