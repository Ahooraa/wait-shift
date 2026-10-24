---
title: "DFPS printed errata (E1-E6)"
type: concept
created: 2026-10-13
updated: 2026-10-16
status: review
author: llm
tags: [reproduction, errata, dfps]
sources:
  - "[[zolfaghari-2025-dynamic-function-placement]]"
---

# DFPS printed errata (E1-E6)

## Definition
The six places where the printed DFPS method contradicts the paper's own prose or mathematics, or contradicts itself ([[zolfaghari-2025-dynamic-function-placement]]). Numbering follows `input/description/dfps-gap-evaluation.md` section 1a: E1 Eq. 3, E2 Eq. 6, E3 Alg. 2, E4 Alg. 1, E5 total-weight matching, E6 internal contradictions. The numbering differs from `PLAN.md`/`DEVIATIONS.md` (see below).

## How it is applied
Check done in this ingest, against the PDF text and rendered pages 6, 7 and 9 (all six items below are reproduced from the PDF; the table says where the three existing notes agree or differ).

| ID | Where | Reading from the PDF | Existing notes |
|---|---|---|---|
| E1 | Eq. 3, p. 6 | Signed sum of FAN minus FEN, no absolute value (rendered page confirms). Each node vector sums to ecc_k (pp. 5-6) and Eq. 4 distributes the same total, so the sum is identically 0. | Agree (gap eval E1; PLAN E-1; DEVIATIONS D-8) |
| E2 | Eq. 6, p. 7 | Erlang-C style term without P0. mu_l is "average execution time" (p. 7) and Eq. 4 treats it as a time, but Eq. 6 uses it as a rate (lambda/mu, n*mu - lambda). Eq. 6 also adds lambda/mu, so it gives the number in the system, while the text says "number of requests in the queue". No stability check. | Agree (gap eval E2; PLAN E-2, Q-1). The in-system versus in-queue label mismatch is not in the notes. |
| E3 | Alg. 2, p. 9 | For delta < 0 the revert test is random >= exp(-delta/T), which is > 1, so a worse move is never reverted. t is set to 1 and never incremented; the loop returns the last solution. | Agree (gap eval E3; PLAN E-5, L-1). Disagree on handling: PLAN keeps "return last" literal; the adaptation plan baseline B* adds best-so-far. |
| E4 | Alg. 1, p. 8 | Line 23 appends to FRQ_rs (queue of the removed function) though lines 19-25 relocate f_n requests; lines 16 and 23 do not remove a request from its source queue; e_s' is initialised empty so the first AET comparison is undefined. | Agree (gap eval E4; PLAN E-6 covers only the queue name). The missing removal and the empty e_s' are in the gap eval and DEVIATIONS D-1/D-3 only. |
| E5 | Sec. 4.2, p. 7 | The scheduler picks the match with the least total g-edge weight, while the stated goal is minimum makespan (p. 6). | Agree (gap eval E5). PLAN does not list it as an erratum; it sits in OPEN-1. |
| E6 | pp. 7, 9, 10, 8 | Reference graph per request (p. 7) versus per workflow type, once (p. 9); interval "average critical path length" (p. 7) versus 4 s from a 1-9 s sweep (pp. 9-10); f_r "least number of requests" (text, p. 8) versus "least utilized" (Alg. 1 l. 3). | Agree (gap eval E6). PLAN L-3 and Q-6 cover the last two. |

Re-checked 2026-10-16 against the user's screenshots of Eq. 3, Eq. 6, Alg. 1 and Alg. 2:
- Eq. 3 sums over functions f_l in F (not over nodes); the cancellation argument holds unchanged.
- Eq. 6 equals the textbook M/M/c number in system L = P0 (lambda/mu)^c lambda mu / ((c-1)! (c mu - lambda)^2) + lambda/mu with P0 omitted; the formula itself treats mu as a rate.
- Alg. 2 does lower T every loop (l. 12); the t-index problem is that t = 1 is never incremented, so l. 5 literally rebuilds Sol_1 from Sol_0. Delta = EF(Sol_t) (l. 6), not a difference.
- Alg. 1: the missing source-queue removal matters at l. 23 (f_n request stays in FRQ_ns'); at l. 16 the source queue belongs to the instance just removed. l. 23 puts an f_n request into the queue of f_r, a different function.

Further inconsistency not in the gap eval: Table 2 gives an incoming request rate of 0.5-100 per second, which does not map one to one onto the per-application Poisson means of Sec. 5.1 (PLAN Q-7 records it).

## Not to be confused with
The numbering in `PLAN.md` and `DEVIATIONS.md` (E-1, E-2, E-5, E-6): PLAN E-5 is gap-eval E3, PLAN E-6 is gap-eval E4, and PLAN has no E-3 or E-4 entries. Translate before comparing results.

## Relevance to this project
The adaptation plan's baseline B* is DFPS with E1-E4 corrected; E5 and E6 are handled as alternative variants.

## Sources
- [[zolfaghari-2025-dynamic-function-placement]]
- [[dfps]]
