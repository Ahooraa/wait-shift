"""DAG Topology Suite (2026-10-28): five structural archetypes, each a scenario of 15 workflow VARIANTS of that archetype (varied
length / width / depth, so not one toy graph), on the F3 moving-hotspot arrival process (popularity redrawn at 600 s), the project's
80-node edge topology and 30-function pool, offered utilisation rho = 0.7. Structure is the same for every seed (the variant table
below); the seed changes function types, state sizes, arrivals, topology and layout, so seeds ARE replicates here (unlike the F3
mix, which draws a different workflow set per seed).

  chain      pure linear pipeline, 6-14 tasks                          no parallelism
  diamond    A -> {B..} -> E, 2-6 parallel branches of one task        structural desync at the join
  grid       S stages x W tasks, every task connected to every task    dense edges, many parallel paths
             of the next stage (S 3-4, W 3-5)
  composite  chain(2-4) -> fan-out(3-6 branches of depth 1-2) ->       slack and critical paths mixed
             fan-in -> chain(2-4)
  heavy      the composite family with every state x10 (sc scaled the project's way: states, inputs and node storage)

  python output/data-analysis/dag_suite.py describe
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

ARCHETYPES = ("chain", "diamond", "grid", "composite", "heavy")
DATA_SCALE = {"chain": 1, "diamond": 1, "grid": 1, "composite": 1, "heavy": 10}


def _chain(n):
    return n, [(i, i + 1) for i in range(n - 1)]


def _diamond(w):
    n = w + 2
    return n, [(0, 1 + i) for i in range(w)] + [(1 + i, n - 1) for i in range(w)]


def _grid(s, w):
    idx = lambda st, j: st * w + j  # noqa: E731
    return s * w, [(idx(st, i), idx(st + 1, j)) for st in range(s - 1) for i in range(w) for j in range(w)]


def _composite(a, w, d, b):
    edges, n = [], 0
    for i in range(a):                                           # chain a: tasks 0..a-1
        if i:
            edges.append((i - 1, i))
    n = a
    fork = a - 1
    tails = []
    for _ in range(w):                                           # w branches, each a chain of d tasks
        prev = fork
        for _ in range(d):
            edges.append((prev, n))
            prev = n
            n += 1
        tails.append(prev)
    join = n
    n += 1
    edges += [(t, join) for t in tails]
    prev = join
    for _ in range(b):                                           # chain b after the join
        edges.append((prev, n))
        prev = n
        n += 1
    return n, edges


CHAIN_N = [6, 7, 8, 8, 9, 9, 10, 10, 10, 11, 11, 12, 12, 13, 14]
DIAMOND_W = [2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5, 6, 6, 3, 4]
GRID_SW = [(3, 3), (3, 4), (3, 4), (3, 5), (4, 3), (4, 4), (3, 4), (4, 3), (3, 3), (4, 4), (3, 5), (4, 5), (3, 4), (4, 4), (4, 3)]
COMP = [(2, 3, 1, 2), (2, 4, 1, 3), (3, 3, 1, 2), (3, 4, 1, 2), (3, 5, 1, 3), (4, 3, 1, 2), (2, 3, 2, 2), (3, 4, 2, 2),
        (4, 5, 1, 2), (2, 6, 1, 4), (3, 3, 2, 3), (4, 4, 1, 4), (2, 5, 2, 2), (4, 6, 1, 3), (3, 6, 1, 2)]


def variants(arch):
    if arch == "chain":
        raw = [_chain(n) for n in CHAIN_N]
    elif arch == "diamond":
        raw = [_diamond(w) for w in DIAMOND_W]
    elif arch == "grid":
        raw = [_grid(s, w) for s, w in GRID_SW]
    elif arch in ("composite", "heavy"):
        raw = [_composite(*c) for c in COMP]
    else:
        raise ValueError(arch)
    out = []
    for i, (n, edges) in enumerate(raw):
        assert all(u < v for u, v in edges), (arch, i)
        out.append(dict(job=f"{arch}-{i}", n=n, edges=[tuple(e) for e in edges], span=float("nan"), names=["f"] * n))
    return out


def build(arch, seed, rho=0.7, shift_every_s=600.0):
    """(scenario, X0) for one archetype and seed; the same pipeline as dfps.traces.build_trace_scenario for family F3."""
    import d3s_headroom as d
    import operating_envelope as oe
    import workflow_stress as w
    from dfps.traces import offered_load_profile, regime_shift_series, scale_to_rho, thin_arrivals
    from dfps.workload import build_scenario
    duration_s, bin_s, ne = d.DURATION + d.WARMUP, 60.0, 80
    mix = variants(arch)
    sc = build_scenario(seed, "uniform", 1.0, ne=ne, n_workflows=len(mix), pool_size=oe.ASSUME["A17_function_pool_size"],
                        duration_s=duration_s, dags=mix)
    rng = np.random.default_rng(seed + 1000)
    rel = regime_shift_series(len(sc.workflows), duration_s, bin_s, rng, shift_every_s=shift_every_s)
    rate = scale_to_rho(sc, rel, rho)
    sc.arrivals = thin_arrivals(rate, bin_s, duration_s, sc.network.ne, rng)
    prof = offered_load_profile(sc, rate, bin_s)
    sc.meta = dict(sc.meta, family="F3", rho=rho, bin_s=bin_s, kind=f"suite-{arch}", offered_util_mean=float(prof.mean()),
                   n_arrivals=len(sc.arrivals), workflows=[m["job"] for m in mix], per_app_rate=rate.mean(axis=1).tolist(),
                   rate_series=rate.tolist())
    sc = w.scale(sc, DATA_SCALE[arch])
    return sc, oe.initial_layout(sc, seed, oe.ASSUME["A06_generations"])


def describe():
    for arch in ARCHETYPES:
        vs = variants(arch)
        ns = [v["n"] for v in vs]
        ne = [len(v["edges"]) for v in vs]
        joins = [sum(1 for t in range(v["n"]) if sum(1 for e in v["edges"] if e[1] == t) > 1) for v in vs]
        print(f"{arch:10s} tasks {min(ns)}-{max(ns)} (mean {np.mean(ns):.1f})  edges {min(ne)}-{max(ne)} (mean {np.mean(ne):.1f})  "
              f"joins/workflow {np.mean(joins):.1f}  data x{DATA_SCALE[arch]}")


if __name__ == "__main__":
    describe()
