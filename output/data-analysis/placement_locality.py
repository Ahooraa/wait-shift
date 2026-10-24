"""How much room is there for workflow-aware co-location? (2026-10-23)

Question: if tasks of one workflow that exchange state were always on the same node, how much faster would requests be? A
transfer between two containers on the same node costs nothing in the simulator (STT = hops x (epd + size/bw)), so this is
measurable from what the dispatcher actually chose.

For every request planned inside the measured window we take the plan the dispatcher picked (task -> node) and record, per
workflow:
  local edges      share of the workflow's edges (origin->root and task->task) whose two ends are on the SAME node
  mean hops        average hop count over those edges
  transfer time    state-transfer seconds on the plan (sum over edges of hops x (epd + size/bw))
  critical path    longest source-to-sink path WITH the planned transfers, and WITHOUT them (execution time only)
The gap between the two critical paths is an upper bound on what perfect co-location could save per request (it ignores queueing
and cold starts, which co-location cannot remove, so it overstates the gain); it is reported as 'transfer share of the critical
path'. Workflows are grouped by shape (chain / diamond / fan-in / out-tree / multi-root) with the same rule as the pattern
study. B* and the frozen controller are both measured, at 50% and 85% load.

  python output/data-analysis/placement_locality.py run [workers]
  python output/data-analysis/placement_locality.py analyze
"""
import collections
import json
import pickle
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

from dfps.o3s import O3SimAdjuster  # noqa: E402
from dfps.sim import Sim  # noqa: E402
from dfps.variants import make_adjuster, sim_kwargs  # noqa: E402

ASSUME = yaml.safe_load((ROOT / "config" / "assumptions.yaml").read_text(encoding="utf-8"))
D1 = ROOT / "results" / "d1_headroom"
OUT = ROOT / "output" / "data-analysis" / "results"
RUNS = ROOT / "results" / "locality"
CTRL = {"no_inner": True, "rebal": True, "rebal_max": 10 ** 9, "placement": "kmedian", "improve": 0, "origin_weight": 1.0}
CASES = [(f, r, 1) for f in ("F1", "F2") for r in (0.5, 0.85)]
DURATION, WARMUP = 420.0, 60.0


def shape(w):
    ch, pa = w.children, w.parents
    out = [len(ch[t]) for t in range(w.n)]
    inn = [len(pa[t]) for t in range(w.n)]
    if all(o <= 1 for o in out) and all(i <= 1 for i in inn):
        return "chain"
    if len(w.roots) > 1:
        return "multi-root"
    if max(out) > 1 and max(inn) > 1:
        return "diamond"
    if max(out) > 1:
        return "out-tree"
    return "fan-in"


def critical(w, mu, edge_t, root_t):
    """Longest path (tasks are in topological order). edge_t[(u,v)] and root_t[t] are transfer seconds."""
    fin = [0.0] * w.n
    for t in range(w.n):
        start = root_t.get(t, 0.0) if t in w.roots else 0.0
        for p in w.parents[t]:
            start = max(start, fin[p] + edge_t[(p, t)])
        fin[t] = start + mu[w.ft[t]]
    return max(fin)


def job(args):
    ctrl, fam, rho, seed, period = args
    out_path = RUNS / f"{ctrl}_{fam}_r{rho}_s{seed}.json"
    if out_path.exists():
        return str(out_path)
    try:
        sc = pickle.load(open(D1 / f"{fam}_r{rho}_s{seed}.pkl", "rb"))
        P = pickle.load(open(D1 / f"{fam}_r{rho}_s{seed}.prep.pkl", "rb"))
        bw, epd, h = sc.network.bw, sc.network.epd, sc.network.h
        mu = np.array([f.exec_time for f in sc.functions])
        wid = {id(w): i for i, w in enumerate(sc.workflows)}
        agg = collections.defaultdict(lambda: collections.Counter())
        base_cp = {i: critical(w, mu, {e: 0.0 for e in w.ss}, {}) for i, w in enumerate(sc.workflows)}
        real = Sim._plan

        def hooked(self, r):
            ok = real(self, r)
            if ok and self.in_window(self.now):
                w, plan, i = r.wf, r.plan, wid[id(r.wf)]
                edge_t, root_t, a = {}, {}, agg[i]
                for (u, v), size in w.ss.items():
                    hp = int(h[plan[u], plan[v]])
                    edge_t[(u, v)] = hp * (epd + size / bw)
                    a["edges"] += 1
                    a["local"] += hp == 0
                    a["hops"] += hp
                    a["transfer_s"] += edge_t[(u, v)]
                for t in w.roots:
                    hp = int(h[r.origin, plan[t]])
                    root_t[t] = hp * (epd + w.input_size / bw)
                    a["edges"] += 1
                    a["local"] += hp == 0
                    a["hops"] += hp
                    a["transfer_s"] += root_t[t]
                a["n"] += 1
                a["cp_with"] += critical(w, mu, edge_t, root_t)
                a["cp_without"] += base_cp[i]
            return ok
        Sim._plan = hooked
        kw = sim_kwargs("B_STAR", ASSUME)
        kw.update(warmup=WARMUP, duration=DURATION, retry_min_interval=1.0, retry_max_attempts=10)
        try:
            if ctrl == "B_STAR":
                kw["interval"] = float(period)
                adj = make_adjuster("B_STAR", ASSUME, seed=seed + 300)
            else:
                adj = O3SimAdjuster(make_adjuster("B_STAR", ASSUME, seed=seed + 300), period, epoch=60.0, horizon=120.0, K=5,
                                    seed=seed + 800, warmup=WARMUP, blind=True, cand_mode="nosim", churn=dict(CTRL))
                kw["interval"] = adj.next_interval
            t = time.time()
            sim = Sim(sc, P["X0"], adjuster=adj, seed=seed + 400, **kw)
            res = sim.run()
        finally:
            Sim._plan = real
        out_path.write_text(json.dumps(dict(ctrl=ctrl, family=fam, rho=rho, seed=seed, p99=res["p99_makespan"],
                                            wall_s=time.time() - t, shapes=[shape(w) for w in sc.workflows],
                                            tasks=[w.n for w in sc.workflows],
                                            agg={str(i): dict(a) for i, a in agg.items()})))
        return str(out_path)
    except Exception:
        import traceback
        out_path.with_suffix(".err").write_text(traceback.format_exc())
        return str(out_path) + " FAILED"


def run(workers):
    RUNS.mkdir(parents=True, exist_ok=True)
    T = json.loads((OUT / "g2_tstar.json").read_text())
    jobs = [(c, f, r, 1, float(T["families"][f]["T_star"])) for r in (0.85, 0.5) for c in ("OURS", "B_STAR") for f in ("F1", "F2")]
    with ProcessPoolExecutor(workers) as ex:
        for done in ex.map(job, jobs):
            print("done", done, flush=True)


def analyze():
    rows = collections.defaultdict(lambda: collections.Counter())
    for f in RUNS.glob("*.json"):
        d = json.loads(f.read_text())
        for i, a in d["agg"].items():
            key = (d["ctrl"], d["rho"], d["shapes"][int(i)])
            for k, v in a.items():
                rows[key][k] += v
            rows[key]["tasks"] += d["tasks"][int(i)] * a["n"]
    print("Co-location headroom on the dispatcher's own plans (Azure + Huawei, seed 1; per request, averaged within shape)\n")
    print("%-7s %5s %-11s %7s %7s | %7s %9s | %9s %9s %9s" % ("ctrl", "load", "shape", "reqs", "tasks", "local%", "hops/edge", "transfer s", "crit. path", "transfer%"))
    out = {}
    for (ctrl, rho, shp), a in sorted(rows.items(), key=lambda kv: (kv[0][1], kv[0][0], kv[0][2])):
        n = a["n"]
        if not n:
            continue
        row = dict(reqs=int(n), tasks=a["tasks"] / n, local=a["local"] / a["edges"], hops=a["hops"] / a["edges"], transfer=a["transfer_s"] / n,
                   cp=a["cp_with"] / n, share=1 - a["cp_without"] / a["cp_with"])
        out[f"{ctrl}|{rho}|{shp}"] = row
        print("%-7s %4.0f%% %-11s %7d %7.1f | %6.0f%% %9.2f | %9.1f %9.1f %8.0f%%" % (
            ctrl, rho * 100, shp, n, row["tasks"], 100 * row["local"], row["hops"], row["transfer"], row["cp"], 100 * row["share"]))
    print("\nall shapes pooled:")
    for ctrl in ("B_STAR", "OURS"):
        for rho in (0.5, 0.85):
            sub = [a for (c, r, s), a in rows.items() if c == ctrl and r == rho]
            if not sub:
                continue
            e, l, n = sum(a["edges"] for a in sub), sum(a["local"] for a in sub), sum(a["n"] for a in sub)
            cw, cwo = sum(a["cp_with"] for a in sub), sum(a["cp_without"] for a in sub)
            out[f"{ctrl}|{rho}|ALL"] = dict(local=l / e, share=1 - cwo / cw, reqs=int(n))
            print("  %-7s load %2.0f%%: %5.1f%% of edges are local | transfer is %4.1f%% of the planned critical path | %d requests"
                  % (ctrl, rho * 100, 100 * l / e, 100 * (1 - cwo / cw), n))
    (OUT / "placement_locality.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 8)
    else:
        analyze()
