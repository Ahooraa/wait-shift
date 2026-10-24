"""Diagnostic of the data-affinity placement (2026-10-23): where does affinity_greedy_placement lose?

Three questions, measured on live re-layouts of the no-B* controller:
  1 DEGENERACY  when a container is placed, how many nodes are tied at the minimum cost? (a flat cost vector means the
                affinity term decides nothing and the spread/free-slot tie-break places the container)
  2 CHURN ABOVE MINIMUM  how many containers does the placement convert, against the fewest that the target counts allow
                (transportation lower bound: keep at most min(target_f, cur_kf) per node/function)
  3 ORIGIN BLINDNESS  share of the expected state-transfer cost that comes from origin->root edges, which `aff` never sees

  python output/data-analysis/placement_diag.py [case ...]
"""
import json
import pickle
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent))

import dfps.controllers as C  # noqa: E402
from dfps.o3s import O3SimAdjuster  # noqa: E402
from dfps.sim import Sim  # noqa: E402
from dfps.variants import make_adjuster, sim_kwargs  # noqa: E402

import yaml  # noqa: E402

ASSUME = yaml.safe_load((ROOT / "config" / "assumptions.yaml").read_text(encoding="utf-8"))
D1 = ROOT / "results" / "d1_headroom"
OUT = ROOT / "output" / "data-analysis" / "results"
LOG = []


def instrumented(sc, rates=None, counts=None):
    """affinity_greedy_placement with the cost vector of every placement decision recorded."""
    N, F = sc.network.ne, len(sc.functions)
    rates = C.expected_workflow_rates(sc) if rates is None else np.asarray(rates, dtype=float)
    mu = np.array([f.exec_time for f in sc.functions])
    demand, aff = np.zeros(F), np.zeros((F, F))
    for w, r in zip(sc.workflows, rates):
        for t in range(w.n):
            demand[w.ft[t]] += r * mu[w.ft[t]]
        for (u, v), size in w.ss.items():
            a, b = w.ft[u], w.ft[v]
            if a != b:
                aff[a, b] += r * size
                aff[b, a] += r * size
    S = int(sc.ecc.sum())
    n_f = np.asarray(counts, dtype=int) if counts is not None else C.proportional_counts(demand, S)
    X = np.zeros((N, F), dtype=int)
    free = sc.ecc.astype(int).copy()
    h = sc.network.h.astype(float)
    order = np.argsort(-aff.sum(axis=1))
    placed = np.zeros((N, F), dtype=int)
    ties, flat, n_dec = [], 0, 0
    for f in order:
        for _ in range(int(n_f[f])):
            cost = np.zeros(N)
            for g in range(F):
                if aff[f, g] <= 0 or placed[:, g].sum() == 0:
                    continue
                nodes_g = np.flatnonzero(placed[:, g])
                cost += aff[f, g] * h[:, nodes_g].min(axis=1)
            avail = free > 0
            c_av = cost[avail]
            rng = float(c_av.max() - c_av.min()) if c_av.size else 0.0
            scale = float(abs(c_av).max()) or 1.0
            ties.append(int((c_av <= c_av.min() + 1e-9 * scale).sum()))     # nodes tied at the minimum
            flat += rng <= 1e-9 * scale                                     # cost decides nothing at all
            n_dec += 1
            cost = cost + 1e-6 * X[:, f] - 1e-9 * free
            cost[free <= 0] = np.inf
            k = int(np.argmin(cost))
            X[k, f] += 1
            placed[k, f] += 1
            free[k] -= 1
    LOG.append(dict(kind="place", n_dec=n_dec, tie_mean=float(np.mean(ties)), tie_median=float(np.median(ties)),
                    tie_share_gt1=float(np.mean(np.array(ties) > 1)), flat_share=flat / max(n_dec, 1),
                    counts=n_f.tolist(), X=X.tolist()))
    return X


def min_changes(cur, target, ecc):
    """Fewest conversions that realise the per-function counts `target` from layout `cur` (transportation LP; the optimum of a
    transportation problem with integral supplies is integral). cur, X: [N, F]; returns (min_changes, X_minchange)."""
    from scipy.optimize import linprog
    N, F = cur.shape
    # variables: keep[k,f] in [0, cur[k,f]] (cost 0) and new[k,f] >= 0 (cost 1); keep+new = X
    nv = 2 * N * F
    c = np.concatenate([np.zeros(N * F), np.ones(N * F)])
    rows, cols, vals, beq = [], [], [], []
    r = 0
    for k in range(N):                                                      # row sums = ecc_k
        for f in range(F):
            for off in (0, N * F):
                rows.append(r)
                cols.append(off + k * F + f)
                vals.append(1.0)
        beq.append(float(ecc[k]))
        r += 1
    for f in range(F):                                                      # column sums = target_f
        for k in range(N):
            for off in (0, N * F):
                rows.append(r)
                cols.append(off + k * F + f)
                vals.append(1.0)
        beq.append(float(target[f]))
        r += 1
    from scipy.sparse import coo_matrix
    Aeq = coo_matrix((vals, (rows, cols)), shape=(r, nv))
    ub = np.concatenate([cur.reshape(-1).astype(float), np.full(N * F, np.inf)])
    res = linprog(c, A_eq=Aeq, b_eq=np.array(beq), bounds=list(zip(np.zeros(nv), ub)), method="highs")
    if not res.success:
        return None, None
    X = (res.x[:N * F] + res.x[N * F:]).reshape(N, F)
    return float(res.fun), np.rint(X).astype(int)


def transfer_proxy(sc, X, rates):
    """Expected state-transfer cost per second of a layout, split into origin->root and task->task edges.
    Proxy: a state travels from a node holding the producing function to the NEAREST node holding the consuming one
    (what the dispatcher tries to do); origins are the request origins of the trace, uniformly weighted."""
    h = sc.network.h.astype(float)
    bw, epd = sc.network.bw, sc.network.epd
    origins = np.array([o for _, _, o in sc.arrivals[:20000]]) if sc.arrivals else np.arange(sc.network.ne)
    o_w = np.bincount(origins, minlength=sc.network.ne).astype(float)
    o_w /= o_w.sum()
    hosts = [np.flatnonzero(X[:, f]) for f in range(X.shape[1])]
    src, inter = 0.0, 0.0
    for w, r in zip(sc.workflows, rates):
        for t in w.roots:
            hv = hosts[w.ft[t]]
            if hv.size:
                src += r * (epd + w.input_size / bw) * float(o_w @ h[:, hv].min(axis=1))
        for (u, v), size in w.ss.items():
            a, b = w.ft[u], w.ft[v]
            ha, hb = hosts[a], hosts[b]
            if ha.size and hb.size:
                inter += r * (epd + size / bw) * float(h[np.ix_(ha, hb)].min(axis=1).mean())
    return dict(origin_to_root=src, task_to_task=inter, total=src + inter,
                origin_share=src / (src + inter) if src + inter else 0.0)


def main(cases):
    from dfps.traces import workflow_rates
    out = {}
    for case in cases:
        LOG.clear()
        sc = pickle.load(open(D1 / f"{case}.pkl", "rb"))
        P = pickle.load(open(D1 / f"{case}.prep.pkl", "rb"))
        T = json.loads((OUT / "g2_tstar.json").read_text())
        period = float(T["families"][sc.meta["family"]]["T_star"])
        kw = sim_kwargs("B_STAR", ASSUME)
        kw.update(warmup=60.0, duration=300.0, retry_min_interval=1.0, retry_max_attempts=10)
        adj = O3SimAdjuster(make_adjuster("B_STAR", ASSUME, seed=301), period, epoch=60.0, horizon=120.0, K=5, seed=801,
                            warmup=60.0, blind=True, cand_mode="nosim",
                            churn={"no_inner": True, "rebal": True, "rebal_max": 300})
        orig = C.affinity_greedy_placement
        C.affinity_greedy_placement = instrumented
        import dfps.o3s as O
        O.affinity_greedy_placement = instrumented
        layouts = []
        real_apply = Sim.apply_placement

        def spy(self, X):
            layouts.append((self.cnt.T.copy(), np.asarray(X).copy()))
            return real_apply(self, X)
        Sim.apply_placement = spy
        try:
            kw["interval"] = adj.next_interval
            sim = Sim(sc, P["X0"], adjuster=adj, seed=401, **kw)
            sim.run()
        finally:
            C.affinity_greedy_placement = orig
            O.affinity_greedy_placement = orig
            Sim.apply_placement = real_apply
        deg = [d for d in LOG if d["kind"] == "place"]
        rows = []
        for cur, X in layouts:
            tgt = X.sum(axis=0)
            actual = int(np.maximum(0, X - cur).sum())
            lo, Xm = min_changes(cur, tgt, sc.ecc.astype(int))
            naive = int(sc.ecc.sum() - np.minimum(tgt, cur.sum(axis=0)).sum())
            rates = workflow_rates(sc, 0.0, 300.0)
            rows.append(dict(actual_changes=actual, min_changes=None if lo is None else int(round(lo)), naive_lb=naive,
                             cost_affinity=transfer_proxy(sc, X, rates), cost_minchange=None if Xm is None else transfer_proxy(sc, Xm, rates)))
        out[case] = dict(degeneracy=deg and dict(tie_mean=float(np.mean([d["tie_mean"] for d in deg])),
                                                 tie_median=float(np.median([d["tie_median"] for d in deg])),
                                                 tie_share_gt1=float(np.mean([d["tie_share_gt1"] for d in deg])),
                                                 flat_share=float(np.mean([d["flat_share"] for d in deg])),
                                                 n_placements=len(deg)) or {},
                         relayouts=rows)
        print(f"=== {case} ===")
        d = out[case]["degeneracy"]
        if d:
            print(f"  degeneracy: {d['n_placements']} placements | nodes tied at the minimum cost: mean {d['tie_mean']:.1f},"
                  f" median {d['tie_median']:.0f} | decisions with >1 tied node {d['tie_share_gt1']:.0%}"
                  f" | decisions where the cost vector is completely flat {d['flat_share']:.0%}")
        for i, r in enumerate(rows):
            c, cm = r["cost_affinity"], r["cost_minchange"]
            print(f"  re-layout {i + 1}: converts {r['actual_changes']} containers; fewest possible {r['min_changes']}"
                  f" (naive bound {r['naive_lb']}) -> avoidable {r['actual_changes'] - (r['min_changes'] or 0)}")
            print(f"      transfer cost/s: affinity {c['total']:.1f} (origin->root share {c['origin_share']:.0%})"
                  + (f" | min-change layout {cm['total']:.1f}" if cm else ""))
    (OUT / "placement_diag.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main(sys.argv[1:] or ["F1_r0.7_s1", "F2_r0.85_s1"])
