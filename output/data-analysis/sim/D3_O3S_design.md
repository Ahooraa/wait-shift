# D3: simulation-scored oracle O3S (design for the user's approval, 2026-10-17)

**Status: proposed, not implemented.** Replaces nothing: the pre-registered option-2 result (surrogate O3, KILL, tau about 0)
stays on record. O3S is a logged design deviation that asks the question O3 could not answer.

## Why O3 failed (from the D3 run, 71/90)
1. **Wrong scorer.** The Erlang-C surrogate ranks candidates no better than chance (tau about 0 over about 570 checks): it assumes
   steady state and requests spread evenly over instances, the simulation shows bursts, bottleneck functions and data-locality
   dispatch.
2. **No annealing underneath.** O3 replaced B*'s SA. In D1 the only winning oracle (O1+B*) kept SA and added switches on top;
   oracles without SA (O1 alone, O3) lost.
3. **Weak candidates.** 31 random 1-8-instance swaps of the current placement: small moves, like SA's own, so nothing new to find.

## O3S in one paragraph
B* runs unchanged every T*. Every `D` seconds (decision epoch, default 30 s) O3S builds K = 8 candidate placements, clones the
live simulator once per candidate, applies the candidate, and runs the clone forward for H seconds (default 30 s) on the TRUE
upcoming arrivals with the real matching scheduler (so placement is scored together with dispatch). Score = request-seconds in
the system over the horizon (Little), plus the cold starts the switch causes (they are inside the simulation). O3S switches to the
best candidate only if it beats "keep" by a margin (2%). Clairvoyance: future arrivals and their workflows; execution times in the
clone are drawn from the clone's own stream (not the realised ones), so it is a realistic look-ahead, not a perfect replay.

## Candidate set (K = 8)
| # | Candidate | Why |
|---|---|---|
| 1 | keep the current placement | the switch has to pay for itself |
| 2 | affinity-greedy target from the TRUE rates of the next H s | O1's slot target, the one that won inside O1+B* |
| 3 | bottleneck-first target: hot functions to utilisation <= 0.8, rest by affinity | idea 1 of the parked ablations / D2 capacity finding |
| 4 | half-way move from current to #2 (move only the largest 50% of instance differences) | cheaper switch, fewer cold starts |
| 5 | half-way move from current to #3 | same |
| 6-8 | 3 local variants of the best of #2-#3 (biased swaps, existing `candidates()` generator) | local refinement |

## Grid and cost (measured costs from Task 13 feasibility note)
- clone about 0.9 s + forward simulation about 0.35-0.9 s wall per simulated second -> one candidate at H = 30 s about 10-28 s,
  one decision (K = 8) about 1.5-4 min; 30 decisions per 15-min run -> about 1-2 h per run.
- **Grid: 3 seeds per family x load = 27 runs** (seeds 1-3 of the D1 scenarios) -> about 3-6 h on 10 workers.
- Full 90 would take about 9-18 h; possible later if the 27 show a gap.

## Outputs and decision
- h_O3S = (B* - O3S) / B* on P99, per family (bootstrap CI), same scenarios and seeds as D1/D3.
- **Key comparison: O3S vs O1+B* on the same 27 instances.** O1+B* switches placement with oracle timing but scores with the
  pooled queueing model; O3S scores placement with dispatch by simulation. If O3S > O1+B*, coupling placement with dispatch adds
  headroom beyond D1; if O3S ~ O1+B*, D3 collapses into D1.
- Scorer check (replaces tau): at 5 decisions per run, re-score the 8 candidates with a second clone seed; report tau between the two
  simulated rankings (noise floor of the scorer). Low tau here = horizon too short / too noisy.
- Stop rule: with 27 instances the plan's rule allows at most MAYBE for D3 (reduced grid). Logged as a deviation.

## Choices to confirm
1. Decision epoch D and horizon H: 30 s / 30 s (alternatives: 10/20 s cheaper and more reactive, 60/60 s smoother).
2. Grid: 27 runs (recommended) or 90.
3. Order: run O3S right after D3 (about 04:30) and before the queued Figs. 5-7 reproduction (recommended: G3 needs D3, the figures
   do not), or after the figures.
