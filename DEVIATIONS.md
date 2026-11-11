# Deviations, errata handling and open items (kept up to date with the code)

Legend: **E-x** erratum (literal + prose variants implemented), **Q-x** ambiguity, **A-xx** missing detail (default in
`config/assumptions.yaml`), **D-x** implementation decision recorded while coding, **OPEN** not yet verified.

## OPEN items (must be resolved before results are called a faithful reproduction)
- **OPEN-1 (matching, ref. [39]):** the paper describes the graph pattern matching only briefly. `dfps/matching.py` implements
  "top-k lowest-weight matches of spanning trees of the pattern + the weights of the non-tree pattern edges added
  (the "missing paths", O(1) in this graph structure, p.9)". This has NOT been checked against Cheng, Zeng, Yu (ICDE 2013).
  Read [39] and compare before trusting the matching step.
- **OPEN-2 (workload) - PARTLY RESOLVED 2026-10-13:** the real Alibaba 2018 `batch_task` table is now on disk (see data/README.md): 1,459,783
  qualifying DAG jobs (mean 4.31 tasks). Experiments use it via `--dags data/alibaba_dags_lt60s.json`. Still open: how the paper picks its 15 workflows
  (A-15, we sample uniformly among eligible jobs) and how tasks map to function types (A-16). The synthetic generator is kept only for fast tests.
- **OPEN-3:** Heu ([18]) and RL ([28]) baselines are not implemented. Both papers are read and specified in BASELINES_SPEC.md; the adaptation decisions AB-H1..H6 and AB-R1..R7 need the user's approval, and MOSEC's Appendix A/B (network structure, training details) are missing from the supplied PDF.
- **OPEN-4:** `pymoo` is not installed; the NSGA-II cross-check against it is pending.

## Errata (PLAN.md section 3.1): variants selectable with `variant` flags
E-1 proportionality (signed vs abs), E-2 Eq.6 (literal vs Erlang-C with P0), E-5 Alg.2 acceptance (literal vs Metropolis),
E-6 Alg.1 l.23 queue name (only the corrected reading exists).

## Implementation decisions recorded while coding
- **D-1:** A neighbour with f_n == f_r is a no-op (A-32). A move that would remove the last instance of f_r in the network
  is rejected (A-31): Alg.1 l.10-17 is undefined when no node has a warm f_r.
- **D-2:** `AET(rq, e)` = sum of input-state transfer times to e + estimated service time at e + sum of output-state
  transfer times from e to the children's planned nodes (A-26, A-30). Service estimate: list-scheduling of the requests
  ahead of rq over the instances' availability times (idle: now; busy: now + mean exec time (memoryless); cold: warm time).
- **D-3:** Forced relocations (Alg.1 l.8-17) use as gain AET_old(rq, e_s) - AET_new(rq, e_s'), with AET_old computed in
  the solution before the change (the paper's EF is "relocation gains ... during the transition Sol_{t-1} -> Sol_t").
- **D-4:** Relocating a request requires free storage at the destination for its input states (A-23); moves that do not fit are skipped.
- **D-5:** Replacing a *busy* instance: the instance finishes its running request, then becomes a cold instance of f_n
  (the container slot is never double-booked, so ecc_k is never exceeded). Idle instances are replaced at once.
- **D-6:** Tasks that become ready on a node whose f has no instance (after a replacement) are rerouted by the AET rule (A-25).
- **D-7:** Capacity check: every node always holds exactly ecc_k placed instances (the initial placement fills every slot, p.5-6).
- **D-8:** NSGA-II final choice: if a criterion's minimum on the front is 0 (always for the literal signed Eq.3) it is not normalised (divisor 1).
- **D-9 (metrics):** average makespan = mean over requests that ARRIVE in [warmup, duration] (A-21); utilization = busy instance-time in that window /
  (sum ecc_k x window length) (A-22); cold starts = replacements that begin in that window. Requests are drained after the window (cap 20x duration).
- **D-10 (OPEN-2 detail):** `synthetic_alibaba_like` produces layered random DAGs of 3..`synthetic_max_tasks` tasks; the size distribution is NOT from the paper or
  the trace. With 3..14 tasks the system is overloaded at Uniform x1.0 (36.8 requests/s x about 8 tasks x 6 s > 1235 slots). The experiments log `mean_tasks`.
- **D-11:** apply_solution pairs net instance changes per node 1-for-1; pending replacements of busy instances are redirected if the solution removes them again.

## Testbed (real-system) sub-study, decided 2026-11-11 (user decision; design in testbed/DESIGN.md)
- **DEV-T1 (workload, deviates from the frozen plan):** `input/ideas/faas-edge-adaptation-plan.md` (status pre-registered, frozen 2026-10-13) lists
  SeBS-Flow, the DFPS Fig. 1 workflow and Alibaba-2018 DAGs as the workflow sources. The multi-laptop testbed, and the simulator runs it is
  compared with, use **only the 6 SeBS-Flow applications at the paper's Table 4 configuration** (Video Analysis 4 functions, Trip Booking 7,
  MapReduce 10, ExCamera 16, Machine Learning 3, 1000Genome 19; mean about 9.8 tasks). Reasons: one source for the DAG structure instead of a
  mixture, and one unit for container sizes (the `memory` setting of each workflow's config.json), which removes the median rescaling that
  `dfps/profiles.py` needs to mix Alibaba and SeBS-Flow profiles. The DFPS Fig. 1 workflow is left out because it is not from SeBS-Flow.
  Not changed: the earlier simulator results (CAP-U, CAP-W1) keep the original mixed workload; they are not re-labelled.
- **DEV-T2 (SUPERSEDED 2026-11-11 by DEV-T4; what was and was not SeBS-Flow data):** SeBS-Flow publishes workflow-level runtimes and total transfer volumes, not per-function
  durations or per-edge payloads. Those still come from the frozen plan (durations from Azure 2021 empirical distributions, state sizes 10-50 MB) and
  must be stated as assumptions in any write-up. Known mismatches with the SeBS-Flow tables (see dfps/sebsflow.py): MapReduce unrolls to 10 functions
  (paper: 9), ExCamera critical path 8 (paper: 6), 1000Genome critical path 3 (paper: 4). With only six DAGs a "workload" is defined by its seed
  (arrival times, origin nodes, popularity weights), not by which DAGs were drawn.
- **DEV-T3 (draft written 2026-11-12, not frozen):** the pre-registration is drafted in `knowledge/synthesis/testbed-preregistration.md` (decisions open in its section 11); until it is frozen, the testbed grid, metrics and stop rule are not pre-registered; the methodology (quantitative) requires that before any
  measured run. Optional, not decided: measuring real per-function runtimes by running the SeBS-Flow function code once on one laptop (not
  checked whether the benchmark inputs are available offline).
- **DEV-T4 (workload data, user decision 2026-11-11: measured SeBS-Flow):** the testbed workload uses only measurements from the SeBS-Flow
  replication package (Zenodo 10.5281/zenodo.14907321, CC BY 4.0, AWS 2024): task durations are drawn from the measured quantiles of each of the
  25 functions (provider execution duration; warm run; 1000Genome from its burst run, which has no warm run), cold start is the measured
  initialisation time (0.22-0.35 s), state sizes are the measured bytes (producer's median upload split over its successors, the root's median
  download as input; 1 kB where none was measured), capacity is CAP-U (CAP-W2 = weights from the measured memory is available). Code:
  `testbed/derive_sebs_profile.py`, `testbed/sebs_profiles.json` (derived summary, attribution in `testbed/SEBS_DATA_NOTICE.md`),
  `testbed/sebs_scenario.py`. This replaces the Azure 2021 durations, Huawei cold starts and 10-50 MB states of the frozen plan for the
  testbed. Consequences: cold starts are about 10 times shorter than the DFPS paper's 2-10 s; most tasks are far below 10 s (MapReduce,
  ML, Trip Booking: milliseconds to a third of a second) while Video (19 s), ExCamera (7-28 s) and 1000Genome (about 120 s) are long. The
  DFPS-paper ranges (2-10 s durations and cold starts, 10-50 MB states) become a sensitivity run, not yet built. Limits: measured on cloud
  hardware, not on edge nodes; the cold start is the runtime initialisation, not an image pull; Trip Booking's failing `confirm` has no
  measured row and uses the pooled reserve_* calls; the measured functions per request match the DAG expansions of `dfps/sebsflow.py` for
  five applications, and Trip Booking has 7 tasks in the DAG against 6 recorded (the failing call leaves no record); MapReduce is
  confirmed at 10 tasks (the paper text says 9).
- **DEV-T5 (mix RESOLVED 2026-11-11: one application per experiment, see DEV-T6; timing resolution still open):** with equal request shares, 1000Genome (about 1,340 container-seconds per request
  against 0.2 to 213 for the others) is about 84% of the offered work, so results are dominated by that application; `mix="equal_load"`
  gives each application an equal share of the work instead. Which mix to pre-register is open. Also open: the control plane's own
  latencies (hub to agent round trip 2-5 ms, timer lateness 2-3 ms on the laptops) are comparable to the millisecond tasks of Trip Booking,
  ML and MapReduce, so for those the testbed measures orchestration overhead as much as work; this is realistic but must be stated.
- **DEV-T6 (experiments per application, cold-start counts; user decision 2026-11-11):** each application is its own experiment, so one
  application cannot dominate (`sebs_scenario.build(apps=[...])`; the mixed workload stays available but is not the main design). Cold starts
  are reported as a COUNT (`testbed/metrics.py`: per window, per request, per 100 tasks, per second), next to the latency, because the
  measured cold starts are short (0.22-0.35 s) and a latency-only view would understate their importance; the time they cost is shown under
  the measured model and, labelled hypothetical, under the DFPS 2-10 s range. How large a cold start is next to a task differs by application
  (median ratio of cold-start initialisation to task duration: Trip Booking 11.8, ML 1.2, MapReduce 1.0, Video 0.1, 1000Genome 0.1, ExCamera 0.0):
  for Trip Booking one cold start costs more than the request's whole work (0.18 s).
- **DEV-T7 (open, load regime per application):** at 20 nodes (about 324 container slots) the request rate needed for a load of 0.7 is
  1,227/s for Trip Booking, 266/s for ML, 99/s for MapReduce, 5.4/s for Video, 1.1/s for ExCamera and 0.2/s for 1000Genome. The three
  millisecond-scale applications cannot be driven to that load on a real testbed; the rate cap (`rate_cap`) reports the load actually offered
  (`rho_effective`). Run lengths: 20 critical paths are 444 s (Video), 1,394 s (ExCamera) and 4,845 s (1000Genome), which makes a full
  grid for 1000Genome very long. Options not yet chosen: a smaller cluster per application so that the target load is reached at a feasible
  rate; a capped rate with the reached load reported; short applications only for cold-start counts.
- **DEV-T7 update (2026-11-11, from the calibration on the laptops):** the hub drives about 700 tasks/s cleanly and saturates near 1,000 tasks/s, so the
  millisecond-scale applications cannot reach the target load (Trip Booking 8,592 tasks/s for rho 0.7), as expected. Intermittent Wi-Fi stall episodes
  (transfers of 0.5 to 3.7 s for a stretch of time, independent of load) make single runs unreliable; repeated, interleaved runs with per-run network
  health logging are needed, and a stall episode must be reported, not dropped. See `testbed/DESIGN.md`, "Calibration of the testbed".

