# Task 13 (D3) — feasibility of the pre-registered O3 oracle, and options (2026-10-15, for the user's decision)

**Status: not implemented; waiting for a design decision.** Everything below is measured or derived from measurements in this session.

## What the plan pre-registers
O3: at each re-plan period, generate K = 32 candidate placements by corrected local search from the current one, score each by
simulating the next window on the actual upcoming requests, and pick the best. Grid: B*, O3, affinity-greedy heuristic on F1-F3
dev data, 3 load levels, 10 instances (90 instances). Plus the surrogate check (Kendall tau between the queueing model's ranking of the
32 candidates and the simulated ranking). Timebox 14 h.

## Measured cost (F3, rho 0.7, at t = 300 s, backlog about 2,200 requests, CPU shared with the D1 grid)
| Step | Cost |
|---|---|
| Deep copy of the live simulator state (scenario shared) | about 0.9 s |
| Running a copy forward | about 0.35-0.9 s wall per simulated second (from the D1 runs) |
| One candidate, look-ahead = one period (2-8 s) | about 2-5 s |
| One period, K = 32 candidates | about 1-2.5 min |
| Periods per 15-min run (900 s / T*) | F1 225, F2 112, F3 450 |
| **One O3 run** | **about 2-19 h** (normal run: about 10 min) |
| 90 instances on 10 workers | about 30-170 h of wall time |

So the pre-registered O3 does not fit the 14 h timebox (and not the +50% overrun allowance) by one to two orders of magnitude.
A technical note: the simulator's event-hash object cannot be deep-copied; a clone needs `__deepcopy__` that copies the hash
(`blake2b.copy()`); trivial to add.

## Options (each changes the pre-registered design; log as a deviation, results become at best MAYBE per the stop rule if the grid shrinks)
1. **Thin the oracle**: K = 8 candidates, score every 4th period only (the others keep the placement), look-ahead = one period.
   Cost per O3 run about 16-75 min; full 90-instance grid about 20-60 h. Still over budget; with 3 instances per cell (27): about 6-18 h.
2. **Surrogate-in-the-loop first**: score the 32 candidates with the corrected queueing model (milliseconds each); run the
   simulation-scored O3 only on a small subset (e.g. 1 instance per family x load, K = 8) to measure Kendall tau between surrogate and
   simulation. If tau >= 0.7 (the plan's own threshold), the surrogate-scored O3 is an acceptable stand-in on the full grid
   (about 1-2 h); if tau < 0.7, that is itself the D3 finding (a learned or simulation-based scorer is needed).
3. **Smaller grid, faithful oracle**: K = 32, full look-ahead, but 1 instance per family (3 runs, about 6-50 h). Shows feasibility
   of the effect, cannot pass G3 (MAYBE at best).
4. **Defer D3**: decide D1/D2 first at G3 (Task 14) and run D3 only if neither reaches GO.

**Recommendation:** option 2. It follows the plan's own logic (the surrogate tau check is part of Task 13), keeps the full grid,
and the expensive simulation-scored oracle is used where it is needed, to validate the cheap one.

## Related observation from Tasks 11-12 (same family of risk)
The pre-registered O1 (D1) and O2 (D2) oracles both looked weak in early checks: O1 lost to B* in all 9 instances seen so far
(its target placements are balanced in the pooled queueing model but perform badly in the node-level simulation), and in a smoke
test O2's hindsight-shedding passes lowered goodput. Any surrogate-scored oracle for D3 has the same risk, which is why option 2
validates it against simulation before trusting it.
