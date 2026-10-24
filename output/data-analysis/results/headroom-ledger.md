---
title: "Headroom ledger"
type: ledger
plan: faas-edge-adaptation
created: 2026-10-13
---

# Headroom ledger

One row per gate (G0-G6). Values are filled by the task that decides the gate; unfilled rows read "not reached".

| gate | direction | metric | value | CI | threshold | decision | date |
|---|---|---|---|---|---|---|---|
| G0 Novelty | D1 | pre-emption status | clear in 7 full-text reads (Jayanthi, Lei, Sun, Liao, ClusterLess, Guo); partial: Nguyen (periodic forecast MPC, single function), Jia/FaaSPR (clock-triggered placement with cold-start-reuse bias, unguaranteed forecast) | - | not pre-empted | clear | 2026-10-13 |
| G0 Novelty | D2 | pre-emption status | partial: Lei, Sun, ClusterLess (deadline/urgency/critical-path ordering, no admission, no goodput); clear: Jayanthi, Nguyen, Liao, FaaSPR | - | not pre-empted | partially overlapping (admission + SLO-goodput half open; must differentiate from Lei/Sun/ClusterLess ordering) | 2026-10-13 |
| G0 Novelty | D3 | pre-emption status | partial: FaaSPR (placement+routing coupling, one-directional, open-loop LP, cloud), Lei, Sun, ClusterLess, Liao (per-function joint decisions); placement scored by dispatch response on upcoming requests: not found in any | - | not pre-empted | partially overlapping (differentiator: placement scored by simulated dispatch response; position against FaaSPR) | 2026-10-13 |
| G1 Practicality | D1 | median change points/h (F1 Azure 2019 / F2 Huawei Public 2023); median share of 1-min windows deviating >= 2x from trailing 10-min mean | CP/h: F1 0.184, F2 0.008 (both < 1). Deviation share: F1 1.6% (< 5%), F2 49.0% (>= 5%) | Poisson-null share F2 40.8% (excess 6.1 pp); F1 null 0% | >= 1 CP/h or >= 5% windows (plan) | PASS by the literal rule (F2 deviation share), but noise-driven: change points show F2 essentially stationary and F1 smooth | 2026-10-13 |
| G1 Practicality | D2 | share of 1-min windows with aggregate top-200 load > median/0.7 (rho = 0.7) | F1 0.02%, F2 13.3% | - | >= 5% PASS; 2-5% MAYBE; < 2% KILL | PASS via F2 only; F1 (Azure) KILL | 2026-10-13 |
| G2 Harness (Task 8 part) | all | M/M/c (9 cells, 10^6 requests, mean wait vs Erlang-C): max rel. error 3.2% (c=16, rho=0.5; others <= 2.6%); Little's law error <= 0.001%; conservation, determinism pass | batch-means SE 0.4-5% of theory | 5% / 2% | validation PASS; G2 as a whole still needs Task 10 (>= 2 of 3 DFPS claims) | 2026-10-13 |
| G2 Harness (Task 10 part) | all | DFPS claims on 80 jobs (2 kinds x 4 scales x 10 workloads): (i) makespan rises with scale, all methods; (ii) Pareto DFPS < SG < SR on means; (iii) SR/SG zero cold starts | B*: 3 of 3 (ii holds at all 4 Pareto scales); as printed: 2 of 3 (ii fails at x0.5-2.0 because SG with printed Eq. 3 is no better than SR) | 10 paired workloads per cell | >= 2 of 3 | **G2 PASS** (with Task 8). Caveats: Uniform DFPS >> SG (paper: about equal); overloaded cells use retry cap (A-24 dev.) and A-25b; Pareto x2.0 static methods left up to 5,921 requests unfinished (means of completed requests, biased low) | 2026-10-15 |
| G2 T* tuning (Task 10) | B* | replacement period with lowest mean P99 (3 dev instances, rho 0.7, 15-min windows) | T* = 4 s (F1), 8 s (F2; 4 s within 2%, tie rule picks longer), 2 s (F3) | U-shaped: P99 at 1 s 757/960/457, at T* 602/585/382, at 64 s 1404/1817/1052 | tie within 2% -> longer period | T* fixed for Tasks 11-13 | 2026-10-15 |
| G3 Headroom | D1 | h_total, h_timing, h_forecast; envelope (B* - best clairvoyant)/B*, P99 | envelope mean (CI): F1 23.1% (17.0-29.6), F2 42.2% (33.7-50.5), F3 4.2% (1.2-7.2); pre-registered O1 h_total < 0 in all | - | GO >= 0.25 in >= 2 of 3 families; KILL < 0.10 in all | envelope rule (approved deviation): MAYBE; pre-registered O1 rule: KILL; gain only from O1+B*, P_TRUE and HEUR worse than B* | 2026-10-16 |
| G3 Headroom | D2 | SLO-goodput gain; envelope max(HEUR,O2,O2H) vs B*; beyond heuristic | envelope: F1 +311% (182-466), F2 +1979% (639-3837), F3 +248% (184-313); beyond HEUR: F1 19.5% (4.5-38.1), F2 54.7% (15-117), F3 10.3% (6.4-14.4); HEUR share 71-80% | - | same; downgrade if HEUR >= 70% in >= 2 | envelope with O2H (deviation): MAYBE (downgraded); pre-registered O2: KILL (O2 ~= B*, shown to be a flawed oracle) | 2026-10-16 |
| G3 Headroom | D3 | P99 makespan reduction; Kendall tau | not reached | - | same; tau < 0.7 keeps GO | - | - |
| G4 Method viability | selected | capture ratio; p95 decision overhead | not reached | - | c >= 0.30 (>= 2 families); <= 50 ms | - | - |
| G5 Confirmation | selected | capture ratio on held-out traces | not reached | - | H4: c >= 0.5 | - | - |
| G6 Sim-to-real | selected | testbed vs simulated improvement | not reached | - | same sign, >= 50% | - | - |
