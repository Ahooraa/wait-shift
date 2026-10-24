"""Worked examples (computed by hand, PLAN.md section 5.2-5.3) for the paper's equations."""
import math

import numpy as np
import pytest

from dfps.network import Network
from dfps.queueing import frn, fst, p0


def line_network(n):
    return Network(n, [(i, i + 1) for i in range(n - 1)])


def test_eq1_eq2_stt():
    net = line_network(5)
    # SS = 30 MB, h = 3, bw = 50 MB/s, epd = 0  ->  3 * (0 + 30/50) = 1.8 s
    assert net.stt(30.0, 0, 3) == pytest.approx(1.8)
    assert net.stt(30.0, 2, 2) == 0.0  # same node: h = 0


def test_eq5_eq6_mmc_example():
    lam, rate, c = 1.5, 1.0, 2          # exec time 1 s -> rate 1/s
    assert p0(lam, rate, c) == pytest.approx(1 / 7)
    assert frn(lam, rate, c, "prose") == pytest.approx(3.428571, abs=1e-6)
    assert fst(lam, 1.0, c, "prose") == pytest.approx(2.285714, abs=1e-6)
    # paper-literal Eq. 6 (no P0): 2.25*1.5/(1*0.25) + 1.5 = 15 ; FST = 10
    assert frn(lam, rate, c, "literal") == pytest.approx(15.0)
    assert fst(lam, 1.0, c, "literal") == pytest.approx(10.0)


def test_mmc_matches_simulation():
    """10^6-arrival M/M/2 simulation must match the Erlang-C (prose) mean time in system within 2%."""
    rng = np.random.default_rng(1)
    lam, mu, c, n = 1.5, 1.0, 2, 1_000_000
    arr = np.cumsum(rng.exponential(1 / lam, n))
    svc = rng.exponential(1 / mu, n)
    free = np.zeros(c)
    tot = 0.0
    for t, s in zip(arr, svc):
        j = int(np.argmin(free))
        start = max(t, free[j])
        free[j] = start + s
        tot += free[j] - t
    sim = tot / n
    assert sim == pytest.approx(fst(lam, 1 / mu, c, "prose"), rel=0.02)


def test_mm1_special_case():
    assert fst(0.5, 1.0, 1, "prose") == pytest.approx(2.0)   # c = 1: 1/(rate - lam)


def test_limits():
    assert fst(0.0, 3.0, 4) == 3.0                    # Q-4: lam = 0 -> exec time
    assert math.isinf(fst(1.0, 3.0, 0))               # no instance
