"""Task 8 / gate G2 part 1: simulator validation (pre-registered criteria, plan faas-edge-adaptation).

Criteria (frozen in the plan):
  * M/M/c: c in {1, 4, 16}, rho in {0.5, 0.8, 0.9}: simulated mean WAIT within 5% of Erlang-C over 10^6 requests
  * Little's law: L = lambda * W within 2%
  * Conservation: arrivals = completions + in-flight at the end, in every run
  * Determinism: the same seed gives an identical event-log hash
  * Runtime budget: one simulated hour at 80 nodes and rho = 0.85 takes <= 10 min wall clock (else shorten to 30-min windows
    and log it)

Full run (writes output/data-analysis/results/g2_validation.json):  python -m tests.test_validation
pytest runs a reduced version (10^5 requests per cell, three cells) plus the cheap criteria.
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dfps.model import Function, Scenario, Workflow  # noqa: E402
from dfps.network import Network  # noqa: E402
from dfps.sim import Sim  # noqa: E402

OUT = ROOT / "output" / "data-analysis" / "results" / "g2_validation.json"


def erlang_c_wait(c, lam, mu=1.0):
    """Mean queueing delay Wq of an M/M/c queue (independent of dfps.queueing)."""
    a = lam / mu
    rho = a / c
    s = sum(a ** k / math.factorial(k) for k in range(c))
    top = a ** c / math.factorial(c)
    p_wait = top / ((1 - rho) * s + top)
    return p_wait / (c * mu - lam)


class ValidationSim(Sim):
    """Sim that also records the exact queueing delay of every in-window request and the time-integral of the number in system."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.waits, self.area, self._last_t = [], 0.0, 0.0

    def _start(self, ins, run):
        if self.in_window(run.req.t_arr):
            self.waits.append(self.now - run.t_enq)
        super()._start(ins, run)

    def run(self):
        import heapq
        lo, hi = self.warmup, self.duration
        while self.events:
            t, _, kind, a, b, c = heapq.heappop(self.events)
            if t > self.t_end:
                break
            # integrate the number of requests in system over [warmup, duration]
            s0, s1 = max(self._last_t, lo), min(t, hi)
            if s1 > s0:
                self.area += self.active * (s1 - s0)
            self._last_t = t
            self.now = t
            self._hash.update(f"{t:.9f}|{kind}|{a if isinstance(a, int) else ''}|{b if isinstance(b, int) else ''};".encode())
            getattr(self, "_ev_" + kind)(a, b, c)
        self.n_unfinished = self.active + len(self.waiting)
        return self.results()


def mmc_system(c, lam, horizon, seed, warmup):
    net = Network(1, [])
    wf = Workflow.from_edges(0, 1, [], [0], {}, 0.0)
    rng = np.random.default_rng(seed)
    n = int(lam * horizon * 1.2) + 100
    t = np.cumsum(rng.exponential(1 / lam, n))
    t = t[t < horizon]
    arr = [(float(x), 0, 0) for x in t]
    sc = Scenario([Function(0, 1.0, 5.0)], [wf], net, np.array([c]), np.array([1e12]), arr, dict(duration_s=horizon))
    return ValidationSim(sc, np.array([[c]]), seed=seed + 1, warmup=warmup, duration=horizon, k_best=1, n_trees=1,
                         drain_factor=50.0)


def run_cell(args):
    c, rho, n_req, seed = args
    lam = rho * c
    warm = 2000.0
    horizon = n_req / lam + warm
    sim = mmc_system(c, lam, horizon, seed, warm)
    r = sim.run()
    w = np.array(sim.waits)
    T = horizon - warm
    wq_th = erlang_c_wait(c, lam)
    n_in = len(w)
    L = sim.area / T
    lam_hat = r["n_arrived"] / T
    W_hat = r["avg_makespan"]
    nb = 50                                                   # batch means: waits are autocorrelated, the iid SE is far too small
    bm = np.array([x.mean() for x in np.array_split(w, nb)])
    return dict(c=c, rho=rho, seed=seed, n_requests=int(n_in), wait_sim=float(w.mean()),
                wait_se=float(bm.std(ddof=1) / math.sqrt(nb)), wait_se_iid=float(w.std(ddof=1) / math.sqrt(n_in)),
                wait_theory=wq_th, rel_err=float(abs(w.mean() - wq_th) / wq_th),
                little_L=float(L), little_lam_W=float(lam_hat * W_hat), little_rel_err=float(abs(L - lam_hat * W_hat) / L),
                util=r["utilization"], util_theory=rho,
                conserved=bool(r["n_arrived"] == r["n_completed"] + r["n_unfinished"] and r["n_unfinished"] == 0),
                event_hash=r["event_hash"])


# --------------------------------------------------------------------------------------------------- pytest (reduced)
@pytest.mark.parametrize("c,rho", [(1, 0.8), (4, 0.8), (16, 0.9)])
def test_mmc_reduced(c, rho):
    r = run_cell((c, rho, 100_000, 7))
    assert r["conserved"]
    assert abs(r["wait_sim"] - r["wait_theory"]) < 4 * r["wait_se"]
    assert r["little_rel_err"] < 0.02
    assert r["util"] == pytest.approx(rho, rel=0.03)


def test_determinism_same_seed_same_hash():
    a = run_cell((2, 0.7, 20_000, 3))
    b = run_cell((2, 0.7, 20_000, 3))
    assert a["event_hash"] == b["event_hash"] and a["wait_sim"] == b["wait_sim"]
    assert run_cell((2, 0.7, 20_000, 4))["event_hash"] != a["event_hash"]


def test_erlang_c_reference_values():
    assert erlang_c_wait(1, 0.5) == pytest.approx(1.0, rel=1e-9)         # M/M/1: Wq = rho / (mu - lam)
    assert erlang_c_wait(2, 1.5) == pytest.approx(9 / 7, rel=1e-9)         # a = 1.5, c = 2: C = 9/14, Wq = C / (c mu - lam) = 9/7 (STATUS.md: W = 2.2857)


# --------------------------------------------------------------------------------------------------- full run
def runtime_budget():
    """One simulated window at 80 nodes, rho = 0.85 (constant rate), measured wall clock; extrapolates to one hour."""
    from dfps.nsga2 import PlacementProblem
    from dfps.traces import scale_to_rho, thin_arrivals
    from dfps.workload import build_scenario
    from experiments.run import ASSUME
    sim_s = 300.0
    sc = build_scenario(11, "uniform", 1.0, ne=80, n_workflows=15, pool_size=ASSUME["A17_function_pool_size"], duration_s=sim_s,
                        synthetic_max_tasks=14)
    rng = np.random.default_rng(1)
    rate = scale_to_rho(sc, np.ones((len(sc.workflows), 30)), 0.85)
    sc.arrivals = thin_arrivals(rate, 10.0, sim_s, sc.network.ne, rng)
    prob = PlacementProblem(sc.network, sc.ecc, np.array([f.exec_time for f in sc.functions]), "abs")
    X = prob.random(np.random.default_rng(2))
    t0 = time.time()
    sim = Sim(sc, X, seed=1, warmup=30.0, duration=sim_s, drain_factor=2.0)
    r = sim.run()
    wall = time.time() - t0
    return dict(simulated_s=sim_s, wall_s=wall, n_arrivals=len(sc.arrivals), wall_per_simulated_hour_min=wall / sim_s * 3600 / 60,
                longest_window_min_within_10min=600.0 / (wall / sim_s) / 60.0, ms_per_arrival=wall / len(sc.arrivals) * 1e3,
                avg_makespan=r["avg_makespan"], n_unfinished=r["n_unfinished"])


def main(n_req=1_000_000, seeds=(11,)):
    cells = [(c, rho, n_req, s) for c in (1, 4, 16) for rho in (0.5, 0.8, 0.9) for s in seeds]
    t0 = time.time()
    with ProcessPoolExecutor(min(len(cells), max(1, (os.cpu_count() or 2) - 1))) as ex:
        res = list(ex.map(run_cell, cells))
    out = dict(criteria=dict(mmc_rel_err=0.05, little_rel_err=0.02, n_requests_per_cell=n_req), cells=res,
               wall_s=time.time() - t0)
    for r in res:
        r["pass_literal_5pct"] = bool(r["rel_err"] <= 0.05)
        r["pass_within_3se"] = bool(abs(r["wait_sim"] - r["wait_theory"]) <= 3 * r["wait_se"])
    out["mmc_pass_literal"] = all(r["pass_literal_5pct"] for r in res)
    out["mmc_pass_literal_or_3se"] = all(r["pass_literal_5pct"] or r["pass_within_3se"] for r in res)
    out["little_pass"] = all(r["little_rel_err"] <= 0.02 for r in res)
    out["conservation_pass"] = all(r["conserved"] for r in res)
    a = run_cell((4, 0.8, 50_000, 5))
    b = run_cell((4, 0.8, 50_000, 5))
    out["determinism_pass"] = bool(a["event_hash"] == b["event_hash"])
    out["runtime_budget"] = runtime_budget()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    o = main()
    print(json.dumps({k: v for k, v in o.items() if k != "cells"}, indent=2))
    for r in o["cells"]:
        print(r["c"], r["rho"], "wait sim %.5f th %.5f err %.2f%% se %.5f | little %.2f%% | util %.3f" %
              (r["wait_sim"], r["wait_theory"], 100 * r["rel_err"], r["wait_se"], 100 * r["little_rel_err"], r["util"]))
