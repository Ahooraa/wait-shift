---
title: "Purohit, Svitkina, Kumar 2018 — Improving Online Algorithms via ML Predictions"
type: source
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
bibkey: purohit-2018-online-algorithms-predictions
depth: standard
tags: [learning-augmented-algorithms, ski-rental, non-clairvoyant-scheduling, keep-alive, h1b]
relations:
  - target: ski-rental
    type: builds-on
    confidence: extracted
    because: "Gives deterministic (Thm 2.2) and randomized (Thm 2.3) ski-rental algorithms that use a prediction y of the number of skiing days (Sect. 2, pp. 3-5)."
  - target: non-clairvoyant-scheduling
    type: builds-on
    confidence: extracted
    because: "Preferential Round-Robin combines SPJF with RR, Thm 3.3 (Sect. 3, p. 7)."
  - target: consistency-robustness-tradeoff
    type: builds-on
    confidence: extracted
    because: "Defines rho-robust / delta-consistent via c(eta) <= rho for all eta and c(0) = delta (Sect. 1, p. 2)."
  - target: container-keep-alive
    type: supports
    confidence: inferred
    because: "Not in the paper: a keep-alive timeout has the same rent-or-buy structure with OPT = min(b, x); this is the project's reading (see Focus block)."
  - target: cold-start
    type: mentions
    confidence: inferred
    because: "Cold-start cost plays the role of the buy price b in the keep-alive mapping; the paper never mentions serverless."
---

# Improving Online Algorithms via ML Predictions

## Bibliographic Details
Purohit, Manish; Svitkina, Zoya; Kumar, Ravi. 2018. *Improving Online Algorithms via ML Predictions*. In *Advances in Neural Information Processing Systems 31 (NeurIPS 2018)*, Montreal. 10 pp. No DOI; proceedings URL https://proceedings.neurips.cc/paper/2018/hash/73a427badebe0e32caa2e1fc7530b7f3-Abstract.html (registered UNVERIFIED in the library). Page numbers below are printed pages 1-10 (identical to PDF pages). Read from `library/pdf/purohit-2018-online-algorithms-predictions.pdf`; theorem statements were checked against page images because text extraction drops the Greek symbols.

## Section map

| Covered | Section | pp. |
|---|---|---|
| ✓ F1 | 1 Introduction (consistency/robustness, main results, related work) | 1-3 |
| ✓ F1 | 2.1 Warm-up: Algorithm 1 (naive, 1-consistent, not robust), Lemma 2.1 | 3 |
| ✓ F1 | 2.2 Deterministic algorithm (Alg. 2), Theorem 2.2 | 3-4 |
| ✓ F1 | 2.3 Randomized algorithm (Alg. 3), Theorem 2.3 | 4-5 |
| ✓ F1 | 2.4 Extension: ski rental with varying demand (proofs omitted) | 5-6 |
| ✓ F1 | 3.1 Preferential Round-Robin: Lemma 3.1 (combiner), Lemma 3.2 (SPJF), Theorems 3.3, 3.4 | 6-8 |
| ✓ F1 | 4 Experiments (4.1 ski rental, 4.2 scheduling, Fig. 2, Table 1) | 8-9 |
| — | 5 Conclusions (k-server, portfolio optimisation, error-distribution-aware bounds as future work) | 9 |

## Kernthesen

### 1. ⭐⭐ Consistency and robustness are the two guarantees a prediction-using online algorithm should have (p. 2)
Competitive ratio is written as a function c(eta) of the prediction error eta. An algorithm is rho-robust if c(eta) <= rho for all eta and delta-consistent if c(0) = delta. The algorithm must be oblivious to predictor quality and assume nothing about error types (p. 2). Robustness is the "no worse than the prediction-free online algorithm" side; consistency is "close to offline optimum with perfect predictions".

### 2. ⭐⭐ Trusting the prediction naively gives consistency but no robustness (Alg. 1, Lemma 2.1, p. 3)
Algorithm 1: buy on day 1 if y >= b, else always rent. Lemma 2.1: ALG <= OPT + eta (so 1-consistent), but its competitive ratio is unbounded if y is small while x >> b (p. 3).

### 3. ⭐⭐ Deterministic ski rental: hedge the buy day by a factor lambda (Alg. 2, Thm 2.2, pp. 3-4)
Algorithm 2: if y >= b buy at the start of day ceil(lambda*b), else at day ceil(b/lambda). Theorem 2.2: competitive ratio at most min{ (1+lambda)/lambda , (1+lambda) + eta/((1-lambda)OPT) }, hence (1+1/lambda)-robust and (1+lambda)-consistent, for lambda in (0,1). lambda -> 0 trusts the predictor, lambda -> 1 is conservative; lambda = 1 recovers break-even with ratio 2 (p. 5).

### 4. ⭐⭐ Randomized ski rental gives a strictly better trade-off (Alg. 3, Thm 2.3, pp. 4-5)
Algorithm 3 (lambda in (1/b, 1)): with k = floor(lambda*b), l = ceil(b/lambda), sample the buy day from a truncated geometric-type distribution q_i (if y >= b, on 1..k) or r_i (if y < b, on 1..l). Theorem 2.3: ratio at most min{ 1/(1 - e^{-(lambda - 1/b)}) , (lambda/(1 - e^{-lambda})) (1 + eta/OPT) }; so 1/(1-e^{-(lambda-1/b)})-robust and lambda/(1-e^{-lambda})-consistent. The adversary is oblivious. lambda = 1 recovers the e/(e-1) Karlin et al. algorithm (p. 5).

### 5. The consistency bounds beat the classical lower bounds only because of predictions (p. 2)
Classical break-even is 2-competitive and optimal among deterministic algorithms; Karlin et al.'s randomized e/(e-1) ~ 1.58 is optimal (p. 2). The (1+lambda) and lambda/(1-e^{-lambda}) consistencies go below these.

### 6. Ski rental generalises to rent-or-buy problems with varying demand (Sect. 2.4, pp. 5-6)
With per-day demand x_i and predictions y_i, eta = sum_i |x_i - y_i|; Algorithms 2 and 3 "extend naturally" with the same bounds, by splitting into k disjoint classical instances. Proofs are omitted by the authors.

### 7. Non-clairvoyant scheduling: single machine, free preemption, sum of completion times (Sect. 3, pp. 6-7)
n jobs, all present at time 0, true sizes x_j unknown until completion; predictions y_j; eta = sum_j |x_j - y_j|; no zero-length jobs, shortest job >= 1 after normalisation. Round-Robin is 2-competitive and optimal (Motwani et al., cited p. 2).

### 8. ⭐ A generic combiner: run a good-on-average and a robust algorithm in parallel (Lemma 3.1, p. 7)
Given monotonic algorithms with ratios alpha and beta, running A at rate lambda and B at rate 1-lambda yields min{alpha/lambda, beta/(1-lambda)}. Monotonicity (smaller sizes never hurt) is the hypothesis that makes concurrency harmless.

### 9. ⭐ SPJF is optimal under perfect predictions but unbounded under bad ones; its ratio is at most 1 + 2*eta/n (Lemma 3.2, p. 7)
Shortest Predicted Job First has ratio <= 1 + 2 eta / n (asymptotically tight by the example on p. 7).

### 10. ⭐⭐ Preferential Round-Robin: Thm 3.3 and Thm 3.4 (pp. 7-8)
Theorem 3.3: ratio at most min{ (1/lambda)(1 + 2 eta/n) , 2/(1-lambda) }; 2/(1-lambda)-robust, 1/lambda-consistent. lambda > 0.5 beats RR's 2 for good predictions (p. 8). Theorem 3.4: when eta = 0 (or the predicted order equals the true order), ratio at most (1+lambda)/(2 lambda) (proof p. 8).

### 11. Experiments are synthetic and small (pp. 8-9)
Ski rental: b = 100, x uniform on [1, 4b], y = x + Normal(0, sigma), 10000 trials; lambda = 0.5 deterministic and lambda = ln(3/2) randomized, both stated to give worst-case ratio 3. Scheduling: 50 Pareto(1.1) jobs, 1000 trials, lambda = 0.5. No real traces.

## Figures and tables
Fig. 1 (p. 6): ski rental robustness vs. consistency for Alg. 2 vs Alg. 3. Fig. 2 (p. 9): average competitive ratio vs error sigma. Table 1 (p. 9): job-length statistics (N=50, min 1, max 22352, mean 5475.42).

## What this source does not address
No serverless, caching-with-state or edge setting; no repeated-gap or learning-over-time analysis; no error-distribution-aware bound (listed as future work, p. 9); no DAG or workflow precedence, no release dates, no multiple machines (scheduling is single machine, p. 6); no lower bounds on the consistency-robustness trade-off; no switching-cost / reconfiguration model beyond rent-or-buy. Caching with predictions is Lykouris and Vassilvitskii (cited, p. 2); the optimal-trade-off follow-up is [[wei-2020-robustness-consistency]], which proves these ski-rental bounds tight.

## Focus: H1b, forecasts with worst-case guarantee for keep-alive (ski-rental and non-clairvoyant results, transfer to a keep-alive / reconfiguration decision) — 2026-10-13

**Carries Kernthesen 1, 2, 3, 4, 6, 8, 9, 10.**

### What this focus needs beyond the Kernthesen

**Exact statements to cite**
- Definitions (p. 2): rho-robust: c(eta) <= rho for all eta; delta-consistent: c(0) = delta; eta is the L1 prediction error.
- Setting (p. 3): unit rent per day, buy price b, true days x, prediction y, eta = |y - x|, OPT = min{b, x}.
- Lemma 2.1 (p. 3): Alg. 1 has ALG <= OPT + eta.
- Theorem 2.2 (p. 3): deterministic Alg. 2, lambda in (0,1): ratio <= min{(1+lambda)/lambda, (1+lambda) + eta/((1-lambda)OPT)}; (1+1/lambda)-robust, (1+lambda)-consistent.
- Theorem 2.3 (p. 4): randomized Alg. 3, lambda in (1/b, 1): ratio <= min{1/(1-e^{-(lambda-1/b)}), (lambda/(1-e^{-lambda}))(1+eta/OPT)}.
- Lemma 3.1 (p. 7): combiner min{alpha/lambda, beta/(1-lambda)} for monotonic algorithms.
- Lemma 3.2 (p. 7): SPJF ratio <= 1 + 2 eta/n.
- Theorem 3.3 (p. 7): PRR ratio <= min{(1/lambda)(1+2 eta/n), 2/(1-lambda)}.
- Theorem 3.4 (p. 8): PRR ratio <= (1+lambda)/(2 lambda) when eta = 0.

**Numerical illustrations (own arithmetic from the printed formulas unless marked; flagged)**
- Deterministic, lambda = 0.5: robustness 1 + 1/0.5 = 3 (the paper states worst-case ratio 3, p. 9) and consistency 1.5.
- Randomized, lambda = ln(3/2): the paper says worst-case ratio 3 (p. 9); exact Thm 2.3 robustness at b = 100 is 1/(1 - e^{-(0.4055 - 0.01)}), about 3.06, so "3" holds as b grows (own arithmetic). Consistency lambda/(1-e^{-lambda}) = 0.4055/(1 - 2/3), about 1.22 (own arithmetic).
- Scheduling, lambda = 0.5: Thm 3.3 gives 4-robust and 2-consistent (no gain over RR at eta = 0 from Thm 3.3 alone); Thm 3.4 gives (1+0.5)/(2*0.5) = 1.5 at eta = 0 (own arithmetic).

**Transfer to keep-alive / reconfiguration (project reading, NOT from the paper)**
1. Mapping. For one idle container let x be the idle gap until the next request and b the cold-start cost in the same units as idle cost. Keeping the container warm for tau units and then evicting costs x if x <= tau and tau + b if x > tau; OPT = min{b, x}. This is the ski-rental cost structure with "buy at day i" read as "evict at idle time i" (paper's cost b + i - 1, p. 4). The prediction y is a forecast of the gap. Alg. 2 then reads: forecast gap y >= b, evict early at about lambda*b; forecast gap < b, keep warm until about b/lambda.
2. What carries over cleanly: the single-gap bounds (Thm 2.2, 2.3) with eta = |y - x| per gap, and a sum over instances if gaps are independent instances (the paper asserts this only for Sect. 2.4, with omitted proofs, p. 6).
3. What does not carry over without new work: (a) cold-start cost is not constant and depends on function and node (paper: constant b); (b) idle-cost rate varies with memory size (paper: unit rent); (c) gaps interact through shared pools and concurrency limits, so they are not independent instances; (d) reconfiguration with switching costs is not a one-shot rent-or-buy and no result here covers it; (e) error enters additively as L1 eta, so a relative forecast error (the project's sigma in {0.25, 0.5, 1.0}) needs conversion; (f) no guidance on choosing lambda from data; (g) the randomized algorithm needs an oblivious adversary.
4. Scheduling results. Lemma 3.1 is a reusable device for a trust-lambda blend of a forecast-driven and a forecast-free controller, provided both are monotonic in the paper's sense. Sect. 3 itself is single machine, no release dates, free preemption (p. 6), so it does not give a bound for DAG dispatch or non-preemptive containers.
5. Verification status. Theorem statements were read from page images of pp. 3, 4, 7, 8 and agree with the text layer; re-checked against the UTF-8 text extraction on 2026-10-13 (repair pass, numbers unchanged). Proofs were read, not re-derived; cases (iii)-(iv) of the Thm 2.3 proof (pp. 4-5) were not independently re-checked. The Sect. 2.4 extension is unproved in the paper.

### Direct quotes (for the draft)
> "if the predictor is good, then the online algorithm should perform close to the best offline algorithm (consistency) and (ii) if the predictor is bad, then the online algorithm should gracefully degrade, i.e., its performance should be close to that of the online algorithm without predictions (robustness)." (p. 1)

> "its competitive ratio can be unbounded if the prediction y is small but x >> b." (p. 3)

> "greater trust in the predictor suggests setting lambda close to zero as this leads to a better competitive ratio when eta is small." (p. 4)

> "we do not assume anything about the input; in fact, we do not assume anything about the predictor either!" (p. 3)

### Examples & illustrations (for later drafting)
- Ski-rental simulation with b = 100, x ~ U[1, 400], Gaussian prediction noise; the deterministic prediction-using algorithm beats classical randomized ski rental up to sigma = 2b (p. 8).
- Tightness example for SPJF: n-1 jobs of size 1 and one of size 1 + eps, all predicted 1 (p. 7).
- Naive-prediction counterexample (Alg. 1 with small y but x >> b) (p. 3).

### Boundary of this focus
Answers only what the guarantees are and what hypotheses they need; whether keep-alive gaps in the Azure/Huawei traces fit the model, and the value of eta for real forecasters, are empirical questions outside this source.

## Mentioned entities
- Concepts: [[ski-rental]], [[learning-augmented-online-algorithms]], [[consistency-robustness-tradeoff]], [[non-clairvoyant-scheduling]], [[container-keep-alive]], [[cold-start]]

## Connections
- Builds on: [[ski-rental]], [[non-clairvoyant-scheduling]] (classical problems, results extended with predictions).
- Defines: [[consistency-robustness-tradeoff]]. Tightness proved in [[wei-2020-robustness-consistency]].
- Supports (project reading, inferred): [[container-keep-alive]].
