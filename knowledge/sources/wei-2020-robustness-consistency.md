---
title: "Wei and Zhang 2020 — Optimal Robustness-Consistency Trade-offs for Learning-Augmented Online Algorithms"
type: source
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
bibkey: wei-2020-robustness-consistency
depth: standard
tags: [learning-augmented-algorithms, ski-rental, lower-bounds, non-clairvoyant-scheduling, keep-alive, h1b]
relations:
  - target: ski-rental
    type: builds-on
    confidence: extracted
    because: "Proves tight deterministic (Thm 1.1, p. 3) and randomized (Thm 1.2, p. 3) robustness-consistency lower bounds for ski rental with a prediction."
  - target: learning-augmented-online-algorithms
    type: builds-on
    confidence: extracted
    because: "«we provide the first set of non-trivial lower bounds for competitive analysis using machine-learned predictions» (abstract, p. 1)."
  - target: purohit-2018-online-algorithms-predictions
    type: supports
    confidence: extracted
    because: "Lower bounds «matching the guarantees of the algorithms given by [KPS18]» (p. 2); Thms 2.1, 2.2 (p. 6) restate KPS18 Thms 2.2, 2.3."
  - target: purohit-2018-online-algorithms-predictions
    type: builds-on
    confidence: extracted
    because: "For two jobs gives a better scheduling trade-off than KPS18: «We provide a significantly better trade-off» (p. 4; Thm 1.4)."
---

# Optimal Robustness-Consistency Trade-offs for Learning-Augmented Online Algorithms

## Bibliographic Details
Wei, Alexander; Zhang, Fred. 2020. *Optimal Robustness-Consistency Trade-offs for Learning-Augmented Online Algorithms*. In *Advances in Neural Information Processing Systems 33 (NeurIPS 2020)*. arXiv:2010.11443. No DOI (registered UNVERIFIED in the library; title and authors, both at UC Berkeley, confirmed from the PDF front page). **Provenance note:** the library file is the arXiv v1 manuscript dated 21 October 2020, 20 pages; all page numbers below are its printed pages (identical to PDF pages) and will differ from the NeurIPS camera-ready. Read in full from `library/pdf/wei-2020-robustness-consistency.pdf` (text extracted as UTF-8, non-layout mode; Greek symbols and fractions are partly garbled in the text layer, so formulas below were cross-checked against the paper's own proof steps).

## Section map

| Covered | Section | pp. |
|---|---|---|
| ✓ F1 | Abstract | 1 |
| ✓ F1 | 1 Introduction (motivation, consistency/robustness, summary of contributions) | 2-3 |
| ✓ F1 | 1.1 Our results: ski rental (Fig. 1.1, Thms 1.1, 1.2); non-clairvoyant scheduling (Fig. 1.2, Thms 1.3, 1.4) | 3-4 |
| — | 1.2 Related work | 4-5 |
| ✓ F1 | 1.3 Preliminaries and notation (ALG, OPT, beta-consistent, gamma-robust) | 5 |
| ✓ F1 | 2 Ski rental: setting; Deterministic-/Randomized-Ski-Rental of KPS18; Thms 2.1, 2.2 | 5-6 |
| ✓ F1 | 2.1 Deterministic lower bound (proof of Thm 1.1) | 6-7 |
| ✓ F1 | 2.2 Randomized lower bound (LP formulation, proof sketch of Thm 1.2) | 7-8 |
| ✓ F1 | 3 Non-clairvoyant scheduling (setting, round robin) | 8 |
| ✓ F1 | 3.1 General lower bound (proof of Thm 1.3) | 8-9 |
| ✓ F1 | 3.2 Tight trade-off for two jobs (Lemma 3.1 lower bound, Lemma 3.2 Two-Stage-Schedule) | 9-10 |
| ✓ F1 | 4 Conclusion | 10-11 |
| — | References | 11-14 |
| ✓ F1 | Appendix A: full proof of Thm 1.2 (LP, Lemmas A.1-A.5) | 15-18 |
| ✓ F1 | Appendix B: proof of Lemma 3.2 (Two-Stage-Schedule) | 19-20 |

## Kernthesen

### 1. ⭐⭐ Consistency and robustness are defined on the competitive ratio ALG/OPT, with prediction error eta (pp. 3, 5)
ALG is the algorithm's cost for a given input and prediction; OPT depends only on the input (p. 5). An algorithm is beta-consistent if ALG/OPT <= beta whenever the input equals the prediction, and gamma-robust if ALG/OPT <= gamma for all input/prediction pairs (p. 5). In ski rental, eta = |x - y| (days skied x, prediction y) and c(eta) is the worst-case ratio over all y given eta, so gamma-robust means c(eta) <= gamma for every eta and beta-consistent means c(0) <= beta (p. 3). Randomised algorithms are judged by expected cost (fn. 1, p. 2). No assumption is made about the distribution of inputs (p. 5).

### 2. ⭐⭐ The trade-off between consistency and robustness is intrinsic, not an artefact of the earlier algorithms (pp. 1-3, 10-11)
The prior works (Lykouris-Vassilvitskii; Kumar-Purohit-Svitkina) gave algorithms with a trade-off but did not show it necessary. This paper provides the first non-trivial lower bounds (abstract, p. 1), and concludes that «merely demanding good performance under perfect prediction can require substantial sacrifices in overall robustness» (p. 3). The caching result of Lykouris-Vassilvitskii (constant under perfect predictions, O(log k) worst case) is noted as already optimal up to constants (fn. 2, p. 2).

### 3. ⭐⭐ Theorem 1.1 (deterministic ski-rental lower bound, p. 3): (1+lambda)-consistent implies at least (1+1/lambda)-robust
Statement: for fixed lambda in (0,1), any (1+lambda)-consistent deterministic algorithm for ski rental with a prediction is at least (1+1/lambda)-robust. It also appears in Gollapudi-Panigrahi 2019 and Angelopoulos et al. 2020 (pp. 3, 6). Proof (pp. 6-7): fix prediction y > (1+lambda)B; the algorithm commits to one purchase day t. Consistency (x = y, OPT = B) forces t <= B (otherwise ALG/OPT exceeds 1+lambda) and then t <= lambda*B + 1; the adversary sets x = t, so OPT = t and ALG = t+B-1, giving ratio >= 1 + (B-1)/(lambda*B+1), which tends to 1+1/lambda only for large B (p. 7). So the printed theorem is an asymptotic-in-B statement; at finite B the proved bound is slightly weaker.

### 4. ⭐⭐ Theorem 1.2 (randomized ski-rental lower bound, p. 3): robustness gamma forces consistency beta >= gamma*log(1 + 1/(gamma-1))
Statement: any randomised algorithm with robustness gamma has consistency beta >= gamma*log(1+1/(gamma-1)); in particular robustness gamma <= 1/(1-e^{-lambda}) forces consistency beta >= lambda/(1-e^{-lambda}) (p. 3). The second form follows from the first by direct substitution (1+1/(gamma-1) = e^lambda at gamma = 1/(1-e^{-lambda}); own check). The proof (App. A, pp. 15-18) is asymptotic: it derives beta >= (gamma/B) * log(1+1/(gamma-1)) / log(1+1/(B-1)) and uses B*log(1+1/(B-1)) -> 1, so the stated bound is the B -> infinity limit (p. 18), consistent with the remark «for large B, our randomized lower bound essentially matches» (p. 6).

### 5. ⭐⭐ The KPS18 algorithms are therefore tight (Thms 2.1, 2.2, p. 6)
The paper restates two upper bounds from Kumar, Purohit and Svitkina (their Thms 2.2, 2.3). Theorem 2.1: Deterministic-Ski-Rental is (1+1/lambda)-robust and (1+lambda)-consistent. Theorem 2.2: Randomized-Ski-Rental is (1/(1-e^{-(lambda-1/B)}))-robust and (lambda/(1-e^{-lambda}))-consistent, for lambda in (0,1) as printed (the robustness expression is meaningful only for lambda > 1/B; flagged). These match Thms 1.1 and 1.2 (deterministic in the large-B limit, randomised for large B).

### 6. ⭐⭐ The algorithms as specified (p. 6)
Deterministic-Ski-Rental(y, B): if y >= B buy at the start of day ceil(lambda*B), else at day ceil(B/lambda). Randomized-Ski-Rental(y, B): k = ceil(lambda*B) if y >= B else k = ceil(B/lambda); pick day i in [k] with probability proportional to (1-1/B)^{k-i} and buy at the start of day i. Buying on day i costs B + i - 1 (rent i-1 days, then buy), and OPT = min{B, x} (p. 7).

### 7. The randomized bound is proved through an infinite linear program reduced to a finite one (pp. 7-8, 15-18)
Randomised algorithms are distributions {p_i} over purchase day; consistency (2.2) and robustness (2.3, 2.4) are linear constraints on p (p. 7). Redundancy lemmas (A.1-A.4) reduce it to a finite LP with B+1 constraints; the "hard" case is y = 2B-1 (p. 17); the extremal solution has p_i proportional to (1+1/(B-1))^{i-1} for i < k with k = ceil(log(1+1/(gamma-1)) / log(1+1/(B-1))) (pp. 17-18); the final step uses Lemma A.5 (Jensen) (p. 17). The proof assumes gamma >= e/(e-1), the classical optimum (p. 17), and treats y >= 2B-1 only (p. 15).

### 8. ⭐ Theorem 1.3 (general non-clairvoyant lower bound, p. 4): (1+lambda)-consistency forces robustness gamma >= (n + n(n+1)lambda) / (1 + lambda(n+1)(n+2)/2)
Setting: n jobs, unknown lengths x_i, predictions y_i, eta = sum_i |x_i - y_i|, preemption allowed, objective sum of completion times (p. 4); single machine (p. 8). Tight at the endpoints only: lambda = 0 gives gamma >= n (any non-idling algorithm), and lambda = 1 - 2/(n+1) gives gamma >= 2 - 2/(n+1), the Motwani-Phillips-Torng round-robin bound (p. 4, fn. 3). Between the endpoints the gap to KPS18's algorithm remains open. Proof via the adversary x_i = d(i,i)+epsilon after job 1 finishes (pp. 8-9).

### 9. ⭐ Theorem 1.4 (two jobs, p. 4): (1+lambda)-consistency and (1 + 1/(1+6 lambda))-robustness are achievable and tight for lambda in (0, 1/3)
Lower bound is Lemma 3.1 (p. 10); the upper bound is Lemma 3.2, the algorithm Two-Stage-Schedule (p. 10, App. B pp. 19-20): run round robin until the consistency constraint is tight, then process jobs in order of predicted time; if any finished job's length differs from its prediction, switch to round robin forever (p. 19). Robustness is at most 2 for all lambda, versus KPS18's 4/(3-3 lambda), which diverges as lambda grows (p. 4). Lambda is reparametrised relative to KPS18: here small lambda means low consistency ratio, KPS18 uses large lambda for that (fn. 4, p. 4). Round robin already gives 4/3 for two jobs, so lambda >= 1/3 is uninteresting (fn. 4).

### 10. A lower bound for k jobs lifts to any n >= k by padding with zero-length dummy jobs (p. 10)
Dummy jobs with zero predicted and actual processing time reduce n-job to k-job instances, so Lemma 3.1 also bounds n > 2 (p. 10). The upper bound is only analysed for n = 2, although the algorithm is described for general n (p. 19).

### 11. Related work and open problems (pp. 4-5, 11)
Ski rental with predictions was extended by Gollapudi-Panigrahi 2019 and Lee et al. 2019 (p. 4). Classical facts quoted: 2-competitive deterministic ski rental (Karlin et al. 1988) and e/(e-1) randomised, optimal (Karlin et al. 1994) (p. 5); round robin 2-2/(n+1) with matching lower bound, randomisation helps only in lower-order terms (p. 5). Future work: tight trade-offs for other problems (online matching, generalisations of ski rental) (p. 11).

## Figures and tables
Fig. 1.1 (p. 3): tight deterministic and randomised robustness-consistency curves for ski rental. Fig. 1.2 (p. 4): tight trade-off for two jobs, against KPS18. No tables, no experiments.

## What this source does not address
No experiments, no real workloads, no data; purely theoretical. No method for choosing lambda from data or for estimating prediction quality (lambda is a fixed hyperparameter, p. 5). No error-distribution-aware bound: eta is a worst-case absolute (L1) error. No optimal n-job scheduling algorithm. No serverless, caching-with-state, switching-cost, multi-item or time-varying-B setting. Caching with predictions is Lykouris and Vassilvitskii 2018 (cited, p. 2). The ski-rental algorithms and their upper-bound proofs are in [[purohit-2018-online-algorithms-predictions]], not here (restated only).

## Focus: H1b, forecasts with a worst-case guarantee for keep-alive (exact ski-rental and online results, consistency/robustness, randomized vs deterministic hypotheses, reuse of a trust parameter) — 2026-10-13

**Carries Kernthesen 1, 3, 4, 5, 6, 8, 9.**

### What this focus needs beyond the Kernthesen

**Exact numbers, from the printed formulas (own arithmetic, large B; lambda = trust parameter, small = trusting)**

| lambda | Det. consistency 1+lambda | Det. robustness 1+1/lambda | Rand. consistency lambda/(1-e^-lambda) | Rand. robustness 1/(1-e^-lambda) |
|---|---|---|---|---|
| 0.1 | 1.10 | 11.0 | 1.051 | 10.51 |
| 0.25 | 1.25 | 5.0 | 1.130 | 4.52 |
| 0.5 | 1.50 | 3.0 | 1.271 | 2.54 |
| 1.0 | 2.00 | 2.0 | 1.582 | 1.582 |

At lambda = 1 the deterministic point is the classical 2-competitive break-even and the randomised point is e/(e-1) = 1.582, both prediction-free optima (p. 5). Reading Thm 1.2 at fixed robustness: gamma = 2 forces consistency >= 1.386, gamma = 3 forces >= 1.216, gamma = 4 forces >= 1.151 (own arithmetic). For finite B = 100 the printed Thm 2.2 robustness at lambda = 0.5 is 1/(1-e^{-(0.5-0.01)}) = 2.58, not 2.54 (own arithmetic). For n = 2 jobs the optimal robustness is 1.625 at lambda = 0.1 and 1.333 = 4/3 at lambda = 1/3.

**Hypotheses each result needs**
- Thms 1.1, 1.2, 2.1, 2.2: single decision per instance (buy once, irrevocable); known fixed integer B; unit rent per day; unknown horizon x with a single scalar prediction y; buying on day i costs B+i-1 (pp. 3, 5, 7); lower bounds hold asymptotically in B (pp. 7, 18) and Thm 1.2 is proved through the case y = 2B-1 with gamma >= e/(e-1) (pp. 15, 17).
- Randomised results use expected cost (fn. 1, p. 2); the adversary type is not named in this paper (an oblivious adversary is the standard reading, an inference, flagged).
- Deterministic lower bound: adversary argument on the unique purchase day t (p. 6).
- Scheduling: single processor, free preemption, sum of completion times, eta = L1 error; Thm 1.4 for two jobs only (pp. 4, 8).

**Transfer of the trust parameter to a keep-alive / reconfiguration decision (project reading, NOT stated in the paper)**
1. Mapping. Let x be the idle gap until the next request to a warm instance and B the cold-start cost in units of idle cost per time. Keeping warm for tau then evicting costs x if x <= tau and tau + B if x > tau, with OPT = min{x, B}. This is the cost of ski rental with purchase day tau (cost B+i-1 on day i, p. 7), so "buy on day t" reads "evict after idle time t". The paper's rule then reads: forecast gap y >= B, evict early at about lambda*B; y < B, keep warm until about B/lambda.
2. lambda as a trust dial: lambda -> 0 follows the forecast (consistency 1+lambda, robustness 1+1/lambda, so a poor forecast can cost up to 1/lambda times optimum); lambda = 1 ignores it. A reconfiguration controller can expose lambda as its trust parameter; the paper gives no rule for setting it online and no bound when lambda changes over time.
3. Randomised version: lower expected cost for the same lambda (2.54 vs 3.0 robustness at lambda = 0.5) but needs sampling the eviction time per idle episode; the guarantee is in expectation and presumes the gap is not chosen by an adversary that sees the sample (inference).
4. Tightness bears on novelty: any forecast-plus-guarantee keep-alive scheme built on this mapping cannot beat Thms 1.1/1.2 for the single-gap problem; a better trade-off requires a changed model (correlated gaps, heterogeneous B, error-distribution knowledge).
5. Not covered, needs new work: heterogeneous and node-dependent B, memory-dependent rent, interacting gaps through shared pools, multi-step reconfiguration with switching costs, relative rather than L1 forecast error, an online rule for lambda, any DAG/workflow structure. Section 3 (scheduling) is single machine and gives no bound for workflow dispatch.

### Direct quotes (for the draft)
> "we provide the first set of non-trivial lower bounds for competitive analysis using machine-learned predictions." (p. 1, abstract)

> "merely demanding good performance under perfect prediction can require substantial sacrifices in overall robustness." (p. 3)

> "Any (1 + λ)-consistent deterministic algorithm for ski-rental with machine-learned prediction problem is at least (1 + 1/λ)-robust." (Thm 1.1, p. 3)

> "we do not make any assumptions on the distribution or stochasticity of inputs." (p. 5)

### Examples & illustrations (for later drafting)
- Cloud rent-or-reserve example: pay on demand or reserve servers for a year, based on a model learned from past demand (p. 2); ski rental is said to model renting cloud servers (Khanafer et al. 2013, p. 3).
- Hard instance for the deterministic bound: prediction y > (1+lambda)B, adversary sets x = t, the day the algorithm buys (pp. 6-7).
- Scheduling instance with all predictions equal to 1 and adversarial x_i = d(i,i)+epsilon (pp. 8-9; two-job version p. 10).

### Boundary of this focus
Answers what the guarantees are and which hypotheses they need; it does not answer whether keep-alive gaps in the Azure or Huawei traces fit rent-or-buy with a fixed B, nor how large eta is for any real forecaster. Verification status: theorem statements read in the text layer and checked against the proof steps; proofs read, Appendix A algebra (pp. 17-19) not re-derived; Lemma 3.2 case analysis (p. 20) not re-checked.

## Mentioned entities
- Concepts: [[ski-rental]], [[learning-augmented-online-algorithms]], [[keep-alive-time]], [[cold-start]]
- Sources: [[purohit-2018-online-algorithms-predictions]]

## Connections
- Supports (tightness): [[purohit-2018-online-algorithms-predictions]], its ski-rental upper bounds are optimal.
- Builds on (two-job scheduling improvement): [[purohit-2018-online-algorithms-predictions]].
- Builds on: [[ski-rental]], [[learning-augmented-online-algorithms]].
- Candidate application (project reading, inferred, no typed relation): [[keep-alive-time]], [[cold-start]].
