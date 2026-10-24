# Harness decision (plan faas-edge-adaptation, Task 6) — 2026-10-13

**Decision: extend the existing `dfps/` package in place. faas-sim is not adopted and no new SimPy simulator is built.**
Approved by the user on 2026-10-13 (logged in `knowledge/_meta/log.md` as a deviation). The plan's first two Task 6 steps (install faas-sim, run a toy case in it) were **not run**: the reuse decision made them moot. This is a decision from a code audit, not from a measured comparison with faas-sim.

## Why
- `dfps/` already implements DFPS faithfully, with the paper's equations, matching, NSGA-II, simulated annealing, the Heu and RL baselines and 41 fast tests (`STATUS.md`). A new simulator would re-derive all of it before any headroom experiment could start.
- The plan's candidate faas-sim has no documented DAG or workflow support (plan, Data Sources); DFPS's model (per-task states, transfers, per-node queues) is exactly what `dfps/sim.py` implements.
- The simulator's queueing is already checked against M/M/c theory (`tests/test_sim_queueing.py`, `experiments/check_mmc.py`: 8-seed mean 2.2869 vs Erlang-C 2.2857, from `STATUS.md`; 3 slow tests pass, `results/slow_tests.log`).

## Audit of `dfps/sim.py` (366 lines) against the plan's needs
| Need (Tasks 7-13) | State | Work |
|---|---|---|
| DAG tasks, state sizes, per-(function, node) FCFS queues, transfers (Eq. 1-2) | present | none |
| Instance replacement with cold start (`swap_instance`, `_convert`) | present | none |
| Arbitrary arrival sequences (`sc.arrivals` list of (t, workflow, origin)) | present: F1/F2 replay by thinning only needs a generator | `workload.py`: non-homogeneous generator |
| Seeded randomness | present (`rng`, `sched_rng`) | add event-log hash (determinism check, Task 8) |
| Execution time model | exponential, mean mu_l (A-13) | add pluggable sampler: Azure 2021 empirical durations (heavy tail), Huawei 2025 cold-start sampler |
| Metrics | mean makespan, cold starts, utilisation, moves | add P50/P95/P99, SLO-goodput (SLO = 3 x unloaded critical path), reconfiguration count, warm-memory-seconds, decision time p95 |
| Controller hook | fixed-interval `adjust` event only | add controller interface: event/cost-triggered re-plan, forecast input, so O1, P_fc and the proposed method plug in |
| Admission decision | none (all requests admitted, `waiting` retry only for storage) | add admission hook in `_ev_arrive` (D2 oracle, heuristic, proposed) |
| Link contention (plan `network.py` fair-share mode) | not modelled, as in the paper (p. 5) | add optional fair-share mode; default off = DFPS Eq. 1-2 |
| Scale-to-zero / warm-idle instances | **not present**: every `ecc` slot always holds an instance (invariant D-7), so warm memory is constant | decide in Task 7: needed only for H1b (keep-alive trust); otherwise keep DFPS semantics |
| Runtime budget (one simulated hour, 80 nodes, rho = 0.85, <= 10 min wall) | **not met on current evidence**: 120 s of simulated time took 31-62 s wall (`results/real_u*.log`), i.e. about 15-30 min per simulated 30 min | profile (matching `schedule` is the likely cost), then shorten runs to 15-30-min windows per the plan's rule and log it |

## Risks
- Single-threaded Python simulator; headroom grid (3 families x 3 loads x 10 instances x several controllers) needs process-level parallelism (the `experiments/batch.py` pattern).
- DFPS-faithful semantics (fixed slots, exponential service, no link contention) are deliberate; the realism toggles must default to off so B* stays comparable to the paper, and results with toggles on are reported as sensitivity.
- The simulator's results so far are single-seed and not a reproduction of the paper's trends (`STATUS.md`); Task 10 (G2) is the check.

## Consequence for the plan
Task 7 shrinks from "simulator core, 20 h" to "extensions listed above"; Task 9 to the audit vs E1-E6 plus the missing controllers (static, heuristics, oracles). Tasks 8 and 10 and their pre-registered criteria are unchanged.
