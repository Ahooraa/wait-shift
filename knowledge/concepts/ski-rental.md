---
title: "Ski rental (rent-or-buy) problem"
type: concept
created: 2026-10-13
updated: 2026-10-13
status: review
author: llm
tags: [online-algorithms, competitive-analysis, keep-alive]
---

# Ski rental (rent-or-buy) problem

## Definition
A skier skis for an unknown number of days x. Each morning, until skis are bought, she either rents for $1 or buys for $B and then skis free. The goal is to minimise the competitive ratio ALG/OPT, where OPT = min(x, B) (Wei and Zhang 2020, Sec. 1.1 and 2, pp. 3, 5; OPT = x for x <= B and OPT = B for x > B, p. 7). Attributed there to Karlin, Manasse, Rudolph and Sleator (1988).

## Where it comes from
Classic results quoted in [[wei-2020-robustness-consistency]] (p. 5): a 2-competitive deterministic algorithm exists (Karlin et al. 1988); randomisation improves this to e/(e-1), which is optimal (Karlin, Manasse, McGeoch, Owicki 1994). Used there to model snoopy caching, dynamic TCP acknowledgement and renting cloud servers (p. 3).

## How it is applied
With a prediction y of x (error eta = |x - y|), the problem is studied in [[wei-2020-robustness-consistency]] as a learning-augmented problem; see [[learning-augmented-online-algorithms]] for the (lambda, consistency, robustness) results.

## Criticism
Assumes a known, fixed B, a single decision (buy once, irrevocably) and a single scalar x; the theorems of Wei and Zhang do not cover multi-item or time-varying B.

## Not to be confused with
General online caching/paging (Lykouris and Vassilvitskii 2018), a different problem with O(log k) worst-case ratio (p. 2, fn. 2).

## Relevance to this project
Candidate abstraction for single-node keep-alive (plan Task 3, H1b): holding a warm instance = renting, evicting and paying the next cold start = buying; mapping is derived in [[wei-2020-robustness-consistency]] (Focus block), not stated in the paper. Related: [[cold-start]].

## Sources
- [[wei-2020-robustness-consistency]]
- [[purohit-2018-online-algorithms-predictions]]
