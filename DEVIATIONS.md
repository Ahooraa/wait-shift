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
