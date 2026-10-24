"""M/M/c service-time estimate (p.7 Eq.5-6) with the two variants of erratum E-2.

Notation (Q-1): the paper calls mu_l the "average execution time" but Eq.6 uses it as a RATE. Here
`rate = 1/exec_time` is the per-instance service rate used in Eq.5-6 and `exec_time` is mu_l of Eq.4.

variant "prose"  : standard Erlang-C, L = Lq + lam/rate, Lq = P0 (lam/rate)^c lam rate / ((c-1)!(c rate - lam)^2)
variant "literal": Eq.6 exactly as printed (the same expression WITHOUT the factor P0)
FST = FRN / lam (Eq.5, Little's law)."""
from __future__ import annotations

import math


def p0(lam, rate, c):
    a = lam / rate
    rho = a / c
    s = sum(a ** n / math.factorial(n) for n in range(c))
    return 1.0 / (s + a ** c / (math.factorial(c) * (1.0 - rho)))


def frn(lam, rate, c, variant="prose"):
    """Eq. 6: average number of requests in the system."""
    a = lam / rate
    core = a ** c * lam * rate / (math.factorial(c - 1) * (c * rate - lam) ** 2)
    if variant == "literal":
        return core + a
    if variant == "prose":
        return p0(lam, rate, c) * core + a
    raise ValueError(variant)


def fst(lam, exec_time, c, variant="prose", queued=0):
    """Eq. 5: average service time (time in system) of a request of f_l on e_k.
    Q-4: lam == 0 -> limit FRN/lam = exec_time. Unstable queue (lam >= c*rate) -> A-10 fallback; c == 0 -> inf."""
    if c <= 0:
        return math.inf
    rate = 1.0 / exec_time
    if lam <= 0.0:
        return exec_time
    if lam >= c * rate:
        return (queued + 1) * exec_time / c + exec_time * (lam / (c * rate))
    return frn(lam, rate, c, variant) / lam
