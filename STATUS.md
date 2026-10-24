# DFPS re-implementation: status

Paper: Zolfaghari et al., *Dynamic Function Placement and Request Scheduling of Serverless Workflows in Edge Environment*,
IEEE TSC 2025 (DOI 10.1109/TSC.2025.3592226). Plan: `PLAN.md`. Open items and decisions: `DEVIATIONS.md`.

## What exists (PLAN.md phases 0-5 done; phases 6-9 not started)

| Phase | Module | State |
|---|---|---|
| 0 | `config/paper_constants.yaml` (+ guard test), `config/assumptions.yaml`, `DEVIATIONS.md` | done |
| 1 | `dfps/network.py` (Eq.1-2, transit-stub topology), `dfps/workload.py` (vectorised Alibaba parser, arrivals; synthetic stand-in kept for tests) | done; **real Alibaba trace downloaded and used** (data/README.md) |
| 2 | `dfps/sim.py` (discrete-event simulator), `dfps/solution.py` (Eq.7 solution + AET) | done |
| 3 | `dfps/queueing.py` (Eq.5-6, literal and corrected), `dfps/matching.py` (pattern matching) | done; **matching not verified against ref. [39] (OPEN-1)** |
| 4 | `dfps/nsga2.py` (initial placement; SR and SG) | done; pymoo cross-check pending (OPEN-4) |
| 5 | `dfps/sa.py` (Alg.1, Alg.2 line by line, both acceptance variants) | done |
| 6-7 | Heu ([18]) and RL ([28]) baselines | **implemented** (`dfps/heu.py`, `dfps/rl.py`, `dfps/ondemand.py`, `experiments/train_rl.py`); spec and decisions in BASELINES_SPEC.md; 41 fast tests pass |
| 8 | Figs. 5-7, interval sweep, ANOVA, erratum impact, sensitivity | not started |

## Tests (`python -m pytest -q`): 27 pass; 3 slow statistical tests (`-m slow`)
- constants guard; Eq.1-2 and Eq.5-6 worked examples (corrected value 2.2857 s, printed formula 10.0 s) and an M/M/2 Monte-Carlo check;
- NSGA-II operators, non-dominated sort, proximity and proportionality (incl. the erratum E-1 demonstration: signed Eq.3 is 0 for any placement);
- matching: tree dynamic programming equals brute-force enumeration (K-best), exact on tree workflows, exact on 40/40 random small DAGs, storage repair;
- Alg.1/Alg.2 with scripted random choices and hand-computed values (AET, forced relocation gains, pull gains, acceptance variants, rollback);
- whole-simulation invariants (capacity, storage, conservation, reproducibility);
- simulator queueing against M/M/c theory (8-seed mean 2.2869 vs theory 2.2857, sem 0.021).

## Results with the REAL Alibaba DAGs (Uniform, 120 s runs, 1 seed, mean 4.5 tasks per workflow)
| Setting | SR | SG | DFPS |
|---|---|---|---|
| x0.5 (15 req/s) | 79.9 s | 61.3 s | 34.0 s |
| x1.0 (30 req/s) | 182.0 s | 130.8 s | 54.1 s |
| x2.0 (61 req/s) | 343.6 s | 269.1 s | 113.6 s |
Same scenario, seed 1, 120 s, with the baselines (Heu / RL, on-demand containers; RL trained on seeds >= 1000):
| Setting | Heu | RL |
|---|---|---|
| x0.5 | 31.6 s | 24.8 s |
| x1.0 | 55.6 s | 55.5 s |
| x2.0 | 170.7 s | 157.2 s |
Single seed, not a verdict: here the on-demand baselines are about level with DFPS (34.0 / 54.1 / 113.6 s), unlike the paper. Needs the 10-workload runs and the A-16/A-11 sensitivity before any claim.

SG < SR as in the paper; makespans are still far above the paper's (about 10-70 s) and DFPS is far better than SG under Uniform load (the paper: about equal).
Per-function load imbalance (A-16) and the annealing budget (A-11) remain the main suspects; the sensitivity runs separate them.

## Earlier smoke results with the synthetic stand-in DAGs (NOT comparable to the paper's figures; 120 s runs; 1 seed)
| Setting | SR | SG | DFPS |
|---|---|---|---|
| Uniform x0.5, mean 4.3 tasks | 48.0 s | 50.0 s | 24.5 s |
| Uniform x1.0 | 112.8 s | 121.3 s | 40.6 s |
| Uniform x2.0 | 263.9 s | 278.2 s | 92.8 s |
(average makespan; DFPS cold starts in the measured window about 1.5-1.9k; utilization SR 0.27-0.55, DFPS 0.30-0.77)

**Why makespans are far above the paper's (about 10-70 s):** with the stand-in DAGs and A-16 (each task draws its function type
uniformly from a pool of 30), the offered load per function type is very unbalanced against the instance counts (a few
functions run at rho 0.8-0.94 while the average utilization is about 30%). The queueing itself is validated against M/M/c
theory, so this is a property of the workload model, not of the simulator. Resolving it needs the real Alibaba trace and
the paper's function-type mapping (A-16 sensitivity: pool size and sharing).

**Do not read these numbers as a reproduction.** The paper reports SR, SG and DFPS roughly equal under Uniform load; here DFPS
is far better. Likely causes (not yet separated): synthetic DAGs and A-16 (load imbalance helps a dynamic method), A-11
(about 100 replacements per 4 s adjustment, since neighbours with EF >= 0 are always accepted), A-22 (utilization definition).

## Next steps
1. (done 2026-10-13) Alibaba `batch_task` obtained and parsed; remaining: paper's workflow selection and task->function mapping (A-15/A-16).
2. Read ref. [39] and compare/replace the matching step (OPEN-1).
3. Sensitivity runs: A-16/A-17, A-11 iteration budget, A-22, literal vs corrected E-1/E-2/E-5.
4. Heu and RL: papers read, see BASELINES_SPEC.md; implement after the user approves AB-H1..H6 and AB-R1..R5 (phases 6-7).
5. Figs. 5-7 grid with 10 workloads per point and repeated-measures ANOVA (phase 8).

## How to run
```
python -m pytest -q                      # fast tests (27)
python -m pytest -q -m slow              # statistical queueing validation
python -m experiments.run --kind uniform --scale 1.0 --seed 1 --gens 250 --duration 300 --max-tasks 6 --out results/x.json
```
