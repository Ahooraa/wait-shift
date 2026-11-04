---
title: "Why our Figs. 5-7 differ from the DFPS paper (B*, Heu, RL)"
type: synthesis
created: 2026-11-03
updated: 2026-11-04
status: draft
author: llm
tags: [reproduction, dfps, baselines, heu, rl, protocol]
---

# Why our Figs. 5-7 differ from the DFPS paper

Capacity model of everything on this page: **CAP-U** (one slot per container), the model the reproduction was built in. It isolates the protocol and workload questions from the container-size change ([[heterogeneous-container-sizes]]).

## The gap (user, 3 Nov 2026)
Two observations, on Fig. 5 (calibrated scenario, `results/fig567_cal`, mean of 5 workloads) against [[zolfaghari-2025-dynamic-function-placement]] Fig. 5 (p. 10):
1. **Order.** SR, SG and B* keep the paper's order at every point (B* < SG < SR). Heu and RL do not. In the paper they are 1.5-20× slower than DFPS. Ours are as fast as B*, or faster.
2. **Shape.** Our curves are hockey sticks: small at low rate, steep at high rate. The paper's are steadier, with large values already at the lowest rate. The paper's count curves are also nearly flat: Heu and RL cold starts stay at about 35-58 thousand at every rate, and its utilisation hardly changes over an 8× change in arrival rate.

## Already ruled out (17-18 Oct 2026, log)
- Calibration of the scenario (load factor, function pool, depth, mapping) fixed SR, SG and B*, but not Heu or RL.
- Keep-warm policy for Heu and RL: a minor factor.
- An untrained RL: not slow enough.
- Heu with Xu et al.'s 1-5 invocations per function: matches the paper's high-rate Heu, not its low-rate Heu.
- Volume: our runs hold 4.5-4.9 thousand tasks at ×0.25. That is too few for the paper's cold-start counts, even if every task starts cold.

## New clues (3 Nov 2026)
- **Count curves are flat in the paper, and rate-proportional in ours.** Our runs have a fixed length (300 s, drained), so the number of requests grows with the rate: 2,657 at ×0.25 and 20,850 at ×2 (Uniform). The paper's Heu cold starts are flat at about 50k. DFPS's fall from 8,500 to 1,500 (×0.18) as the rate rises 8×. Ours (B*) stay flat at about 5,600. DFPS cold starts come from per-interval replacement, so they scale with run length. A count that falls about like 1/rate fits a **fixed number of requests** per workload, with the run getting shorter as the rate rises. The paper states no run length or warm-up (p. 10), so this is an inference.
- **The paper's utilisation fits busy time over alive containers, not over all slots.** The paper says RL's high utilisation comes from "the aggressive removal of idle instances" (p. 11), and that Heu's cold starts lower its utilisation. Removing idle containers changes busy time over alive-container time, but not busy time over total capacity. Ours is busy time over total slot capacity (`sim.py` results), so it rises with load for every method.
- **The calibrated workflows are small.** The depth ≤ 2 pool averages 1.54 tasks per request (median 1). The full Alibaba < 60 s pool averages 2.91. Fewer tasks means fewer function types, more slots per function, and less congestion at low rates.
- **The paper's Pareto SR and SG are flat at about 10% utilisation, with 187-226 s makespan already at ×0.25.** Their hot functions are saturated at every rate. Ours are not saturated at ×0.25 (31 s).

## Probe: protocol × workflow size (pre-registered 3 Nov 2026, before any run)
Script `output/data-analysis/fig5_pattern_probe.py`, results `results/fig5_probe/`. Fig. 5 only, scales 0.25, 1.0 and 2.0, Uniform and Pareto, seed 1. Methods SR, SG, DFPS = B*, Heu and RL (`results/rl_policy.pt`, the RL in the user's figure). B* and the baselines are unchanged. The Heu planner has a caching change that leaves results identical (same event hash on 3 stored cells).

| variant | workflows | protocol |
|---|---|---|
| `cal300` | calibrated (depth ≤ 2) | fixed 300 s, 30 s warm-up (current) |
| `calN` | calibrated | fixed request count: run length 300 s / scale, warm-up 10% of it |
| `wide300` | full < 60 s pool (all depths) | fixed 300 s |
| `wideN` | full pool | fixed request count |

Utilisation is reported both ways: busy over slot capacity (as now), and busy over alive-container time (new; accounting only, no effect on the run).

**Reading, fixed now:** each variant is compared with the digitized paper curve on four marks.
- **(a) Order:** Kendall τ between our and the paper's makespan ranking of the 5 methods, averaged over the 6 (kind, scale) points.
- **(b) Count shape:** cold-start ratio ×2 / ×0.25 for DFPS, Heu and RL. Paper: Uniform 0.18 / 1.02 / 0.84, Pareto 0.34 / 1.11 / 0.86.
- **(c) Makespan shape:** ratio ×2 / ×0.25 per method. Paper Uniform: SR 6.2, SG 5.6, DFPS 5.7, RL 5.8, Heu 2.0. Paper Pareto: 1.5, 1.5, 5.1, 1.9, 1.9.
- **(d) Utilisation level and flatness:** under both definitions.

A variant **explains a part of the gap** if it moves that mark clearly toward the paper (for example, cold-start ratios within 0.6-1.5 of the paper's, or τ up by ≥ 0.3), compared with `cal300`. One seed, so only large changes count. A combination is adopted for a rerun of Figs. 5-7 only with the user's approval.

## Probe result (3 Nov 2026; 60 of 60 runs, seed 1)
| mark | paper | cal300 (current) | calN | wide300 | wideN |
|---|---|---|---|---|---|
| (a) Kendall τ of makespan order | 1 | 0.38 | 0.28 | 0.25 | 0.25 |
| (b) DFPS cold ×2/×0.25, Uniform / Pareto | 0.18 / 0.34 | 0.93 / 0.95 | **0.11 / 0.12** | 0.61 / 0.87 | **0.10 / 0.12** |
| (b) Heu cold ×2/×0.25 | 1.02 / 1.11 | 12.9 / 15.3 | 2.1 / 3.3 | 3.8 / 7.2 | **0.52 / 1.14** |
| (b) RL cold ×2/×0.25 | 0.84 / 0.86 | 22.8 / 2.4 | 42.7 / 3.4 | 22.5 / 20.7 | 14.4 / 27.3 |
| (c) Pareto SR / SG makespan ×2/×0.25 | 1.50 / 1.49 | 30.8 / 33.9 | 10.0 / 15.3 | 10.3 / 10.8 | **1.92 / 2.14** |
| Pareto SR makespan at ×0.25 (s) | 226 | 20 | 33 | 165 | 446 |
| Uniform SR makespan at ×0.25 (s) | 12 | 11 | 11 | 41 | 69 |

What this means:
- **Fixed request count explains the count curves.** It reproduces DFPS's falling cold starts, and with the larger workflows Heu's flat ones. This supports the fixed-request-count reading of the paper's protocol.
- **Larger workflows reproduce the steady Pareto curves.** Only `wideN` saturates the Pareto hot functions at the lowest rate, with the paper's low slope. It breaks the Uniform low-rate fit, though: SR is at 69 s against the paper's 12 s.
- **Neither explains the order.** τ does not rise in any variant. Heu and RL stay at or below B* everywhere: at ×0.25 Heu is 8-28 s against the paper's 156-199 s, and RL 9-20 s against 46-153 s.
- **Utilisation is not explained either.** Our Heu and RL keep every container alive until it is recycled, so busy-over-alive equals busy-over-capacity. Their utilisation rises with load, while the paper's stays flat or falls.
- **RL's cold starts are the clearest sign of a mechanism difference.** Ours are near zero at low rates (containers reused). The paper's are about 50k at every rate, roughly one per task. With the paper's RL utilisation of about 56% at the lowest rate, this fits RL **releasing a container after each use** (the paper's "aggressive removal of idle instances") and utilisation measured over alive containers: exec / (cold start + exec) ≈ 50%. Not tested yet.

## Probe 2: release after use (pre-registered 3 Nov 2026, before any run)
Same script, same scenarios, Heu and RL only, with `OnDemandSim(keep_warm=0)`: a container is removed the moment its task finishes, so every task starts cold. SR, SG and DFPS are taken unchanged from the matching base variant. Variants `cal300r`, `calNr` and `wideNr`, on the scenarios of `cal300`, `calN` and `wideN`.

**Reading, fixed now:**
- **(e) Mechanism check:** RL and Heu cold starts ≈ number of tasks run (ratio ≥ 0.9). If not, release-after-use is not what the variant does, and the reading stops there.
- **(d) Utilisation:** busy over alive containers, for RL and Heu. The paper (Fig. 5, digitized, ×0.25 → ×2): RL 56 → 43% Uniform and 50 → 41% Pareto; Heu 20% flat Uniform and 35 → 33% Pareto. It is explained if ours lands within ±15 points and stays flat over the 8× rate change (×2 minus ×0.25 within ±10 points).
- **(a) Order:** Kendall τ with the base variant's SR, SG and DFPS. It is explained if τ rises by ≥ 0.3 over the base variant, or if Heu and RL move above DFPS at ×0.25 as in the paper.
- **(b) Count shape:** RL and Heu cold-start ratio ×2/×0.25, as before.

One seed; only large changes count. Whatever the outcome, no Fig. 5-7 rerun without the user's approval.

## Probe 2 result (3 Nov 2026; 36 of 36 runs, seed 1)
| mark | paper | cal300r | calNr | wideNr |
|---|---|---|---|---|
| (e) cold starts per task, Heu and RL, every rate | ≈ 1 | 1.10 U / 0.83 P | 1.10 / 0.83 | 1.28 / 0.96 |
| (d) RL util over alive, ×0.25 → ×2, Uniform / Pareto (%) | 56→43 / 50→41 | 51→51 / 52→52 | 52→51 / 52→52 | 50→49 / 48→48 |
| (d) Heu util over alive (%) | 20 / 35→33 | 52 / 52 | 52 / 52 | 49 / 48 |
| (a) Kendall τ (base variant) | 1 | 0.25 (0.38) | 0.35 (0.28) | 0.35 (0.25) |
| Heu makespan ×0.25, U / P (s); base in brackets | 199 / 156 | 17 / 14 (13 / 9) | 17 / 14 (12 / 8) | 31 / 28 (28 / 19) |
| RL makespan ×0.25, U / P (s) | 46 / 153 | 18 / 15 (12 / 10) | 17 / 15 (10 / 9) | 33 / 29 (19 / 16) |
| Heu, RL cold ×2/×0.25, U / P | 1.02, 0.84 / 1.11, 0.86 | 6.8 / 8.1 | 0.86 / 0.97 | 0.40 / 0.41 |

(e) The per-task figure divides by an unweighted mean of tasks per workflow, so it is approximate. It is constant over the rates, so the mechanism does what it should. Heu and RL become indistinguishable: once every task starts cold, both reduce to "cold start on the chosen node".

What this means:
- **RL utilisation is explained** under the pre-registered rule: within 15 points of the paper's and flat. Heu is flat too, but its level misses: 52% against 20% Uniform, and 48-52% against 33-35% Pareto. This supports release-after-use plus busy-over-alive for the paper's RL. The paper's Heu has some additional idle-alive time that ours lacks.
- **The order is formally met but not in substance.** At ×0.25, Heu and RL now sit above DFPS in every variant, which meets the pre-registered "or" clause. But the margin is a few seconds (one cold start per task: +4-10 s), against the paper's 5-20×. τ rises by only 0.07-0.10 in calNr and wideNr, and falls in cal300r. At higher rates Heu and RL are still faster than DFPS on Pareto, for example cal ×2: 17 s against 57 s, while the paper has 295 s against 158 s.
- **Count shape:** fixed request count plus release reproduces Heu's flat cold starts on the calibrated pool (0.86 / 0.97 against 1.02 / 1.11). The level stays at 12-32k against 35-58k. In wideNr at ×2 the in-window count drops (0.40), because the overloaded run completes fewer tasks within its 150 s window.
- **What remains:** the paper's Heu and RL are slow already at the lowest rate (46-199 s), where nothing is congested. Container handling cannot produce that. It must come from how they place work: MOSEC's cloud offloading, or Heu's cost objective consolidating whole components onto few nodes (AB-H3). Both are untested.

## What the papers say about Heu and RL (checked 3 Nov 2026)
**DFPS paper** (pp. 9-11), on why Heu and RL are slow:
- They "do not rely on an initial placement" and decide placement per request. Instances placed for one request "may remain idle or be replaced by new instances for subsequent requests", which reduces reuse and raises cold starts, "ultimately resulting in a higher makespan" (p. 10).
- RL lacks "awareness of workflow structure". Its tasks are spread over many nodes, so it has more cold starts and transmission delay (p. 11). Its high utilisation comes from "the aggressive removal of idle instances" (p. 11).
- Heu's low utilisation comes from cold starts and little reuse (p. 11).
- The setup (Table 2, p. 10) has 80 edge nodes and **no cloud**. Nothing is said about Heu's cost weights, or about MOSEC's cloud action.

**Xu et al. 2023** (Heu): Alg. 1 l. 9 creates "an instance for each function … in partition component A_{F,q}" for **every request** (p. 7). The model allows an existing container (Eq. 2, constraint 12), but the heuristic always creates. Memory demand is per request.

**Yang et al. 2025** (MOSEC): one cloud server X0 plus edge servers (p. 3). An idle container stays in a no-load state "for a period" and is then recycled (p. 4).

What follows:
- **Neither remaining suspect is supported by the DFPS text.** The paper's setup has no cloud, so MOSEC's offloading would be an undocumented choice. Heu's cost weights are never mentioned. Both stay possible, but nothing in the text backs them.
- **The mechanism the paper names is the one probe 2 tested.** Per-request instances (Xu Alg. 1), aggressive idle removal (DFPS p. 11, MOSEC p. 4), more cold starts and less reuse. It reproduces RL's utilisation and the cold-start shape, but adds only 4-10 s per request. Every cold start is 2-10 s (Table 2), and our workflows have 1.4-2.8 tasks. So no amount of cold starts reaches the paper's 46-199 s at the lowest rate, where nothing is congested. That level would need long waiting, which neither paper describes.
- **The spreading explanation for RL** was tested in October: an untrained, effectively random RL was "not slow enough" ([[log]], 17-18 Oct).
- **Reading:** the magnitude of the paper's Heu and RL makespans is **not reproducible from the published descriptions**. The defensible choice is the text-supported container model (release after use for both; it is AB-H5's own default, which the common model AB-C1..C4 had overridden), plus a fixed request count. The remaining gap is then reported as unexplained.

## Figs. 5-7 rerun with protocol v2 (4 Nov 2026; 1320 of 1320 runs, 5 seeds)
Protocol v2 has two parts:
- A fixed request count: the run lasts 300 s / scale, with a 10% warm-up.
- Heu and RL release every container after its task (`keep_warm=0`).

Utilisation is reported as busy over alive containers (`util_alive`). This is the same as busy over slots for the static methods. The run is `fig567_reproduction.py --protocol v2`, the summary is `output/data-analysis/results/fig567_reproduction_v2.json`, and the per-run files are in `results/fig567_v2/`. No marks were pre-registered for the rerun, since it is the adopted setup and not a test. The comparison below is descriptive:
- Fig. 5 is compared with the digitised values.
- Figs. 6 and 7 are compared with the paper's text claims (p. 11), since their values are not digitised.

**Fig. 5 (rates ×0.25 → ×2; v1 = `fig567_cal`, 300 s runs)**

| | paper | v1 | v2 |
|---|---|---|---|
| Kendall τ of makespan order, mean over rates, U / P | 1 / 1 | 0.15 / 0.49 | 0.24 / 0.52 |
| Heu ÷ DFPS makespan, U | 6-22 | 1.0-1.8 | 1.2-1.7 |
| RL ÷ DFPS makespan, U | 4-12 | 0.7-1.3 | 1.2-1.7 |
| Heu, RL ÷ DFPS makespan, P | 1.8-5.0 | 0.2-1.0 | 0.5-1.6 |
| DFPS cold starts ×0.25 → ×2, U | 8.5k → 1.5k | 5.8k → 5.3k | 23.3k → 2.7k |
| Heu cold starts, U / P | ≈ 50k / 35-39k, flat | 2.1k → 25.9k / 1.1k → 19.6k | 15.3k flat (13.4k at ×2) / 18.6k → 13.6k |
| RL cold starts, U / P | 58k → 49k / 50k → 43k | 1.0k → 17.6k / 1.0k → 13.5k | as Heu, within 0.1% |
| RL util over alive, U / P (%) | 56 → 43 / 50 → 41 | – | 50 → 50 / 50 → 51 |
| Heu util over alive, U / P (%) | 20 / 35 → 33 | – | 51 → 50 / 50 → 51 |
| DFPS util, U / P (%) | 30 → 75 / ≈ 55 | – | 7 → 52 / 9 → 38 |
| Makespan ×0.25 → ×2, U: SR / SG / DFPS (s) | 12→74 / 12→67 / 11→63 | – | 11→48 / 10→36 / 10→18 |
| Makespan ×0.25 → ×2, P: SR / SG / DFPS (s) | 226→340 / 187→278 / 31→158 | – | 72→361 / 62→332 / 11→79 |

Fig. 5, what is now reproduced:
- **DFPS's falling cold-start curve.** ×2/×0.25 is 0.12, against the paper's 0.18. The level at ×1 matches on Uniform: 5.6k against 5.1k.
- **The flat Heu and RL count curves.** The level, though, is 0.3-0.5 of the paper's.
- **RL utilisation.** It is flat at about 50%, within the 15-point band of the paper's 56-41%.

Fig. 5, what is not reproduced:
- **The order.** τ rises by only 0.03-0.09. Heu and RL are at most 1.7× DFPS, against the paper's 4-22× on Uniform. From ×1 on Uniform they are faster than SR and SG; in the paper they are slower everywhere. On Pareto from ×0.75 on they are faster than DFPS (0.5-0.9×).
- **Heu's low utilisation.** Ours is 50%, against 20 / 33-35%.
- **The distinction between Heu and RL.** Under release-after-use both reduce to "one cold start per task on the chosen node". Their cold-start counts agree within 0.1%, and their makespans within 1 s. In the paper, Heu is 4× RL on Uniform at ×0.25 (199 s against 46 s). v2 therefore removes a difference that the paper has.
- **DFPS's steep rise at ×2 on Uniform.** Ours goes from 15 s to 18 s; the paper's from 19 s to 63 s.
- **SR and SG at low rates on Pareto.** Ours are 72 / 62 s, against the paper's 226 / 187 s. Our curves are steeper, and they reach the paper's level only at ×2.

RL_CAL (RL trained on the calibrated pool) is the slowest of the per-request group on Uniform (41-51 s). The paper has no counterpart to it.

**Fig. 6 (network size 20 → 160 nodes): the paper's claims (p. 11) against v2**

| claim | v2 |
|---|---|
| makespan falls with size, all methods | met. SR and SG on Pareto flatten from 120 nodes. At 20 nodes SR and SG on Pareto are overloaded (up to 969 / 712 requests unfinished). |
| Uniform: SR, SG and DFPS below Heu and RL | DFPS met at every size (64 against 225 s at 20, 13 against 17 at 80). SR and SG are not met: at or above Heu and RL from 40 to 100 nodes (e.g. 49 / 35 against 18 at 60), comparable from 120. |
| Uniform: SG comparable to or slightly better than DFPS | only at 120 nodes (12 against 11 s). SG is 2× DFPS at 20-60 nodes. |
| Pareto: DFPS best | met at 20-60 nodes. Not met from 80: Heu and RL take 16-19 s, DFPS 21-32 s. |
| Pareto: SG below SR at every size | met, 8 of 8 |
| DFPS utilisation falls with size | met: 84 → 16% U, 81 → 21% P |
| Heu utilisation consistently low | not met: 47-53%, the highest of all methods from 60 nodes |
| RL utilisation steady with size | met: 47-53% |

**Fig. 7 (5 → 40 applications): the paper's claims (p. 11) against v2**

| claim | v2 |
|---|---|
| makespan rises with the number of applications, all methods | met overall. It is non-monotone at 25 → 30 and 35 → 40 for every method at once, so the cause is the sampled workload set, not a method. |
| Uniform: DFPS utilisation rises with applications | met: 14 → 69% |
| Pareto: DFPS, Heu and RL have high utilisation even with few applications | met for Heu and RL (47-55%). Not met for DFPS: 13% at 5 applications, 52-54% from 35. |

What follows:
- **v2 is closer to the paper in the count and utilisation curves, but not in the result that matters.** In the paper Heu and RL are by far the slowest. In v2 they are close to DFPS and often faster than the static methods.
- This matches the conclusion from the paper check above: container handling adds a few seconds per request, while the paper's gap is tens to hundreds of seconds.
- The new cost is that v2 makes Heu and RL indistinguishable.
- The Fig. 6 and 7 claims about the static methods and about DFPS's utilisation hold. The claims that need Heu or RL to be slow do not.

## Evidence base
- Paper text and Fig. 5, pp. 10-11 ([[zolfaghari-2025-dynamic-function-placement]]); digitized values in `output/data-analysis/results/paper_fig5_digitized.json` (read by eye, about ±2%).
- Our runs: `results/fig567_cal` (5 seeds, v1), `results/fig567_v2` (5 seeds, v2; summary `output/data-analysis/results/fig567_reproduction_v2.json`), calibration logs 17-18 Oct 2026 in [[log]].
- Figs. 6 and 7 are compared only with the paper's text. Their curves are not digitised.
- Gaps: the paper gives no run length, warm-up, utilisation definition, number of function types or task-to-function mapping (p. 10). Every cause on this page is an inference from the curves and the text.

## What stays open
- Whether the paper's Heu and RL carry delays our adaptations lack: MOSEC's cloud offloading, and Heu's cost objective (AB-H3).
- Which container model to report: v2 (text-supported, fixes the count curves, merges Heu and RL) or v1 (keeps Heu and RL distinct, wrong count shapes). Neither reproduces the paper's Heu and RL magnitude.
- The DFPS utilisation level: ours is 7-52% on Uniform against the paper's 30-75%, with the same rising shape. The definition the paper uses for DFPS is not stated.
- Digitising Figs. 6 and 7 for a τ comparison.
