"""Runs the DAG Topology Suite (dag_suite.py): baseline vs. each move term in isolation, 3 seeds, full 900 s window, burn-in 120 s.

  python output/data-analysis/dag_suite_run.py run <workers> [arch ...]      resumable, one json per (arch, config, seed)
  python output/data-analysis/dag_suite_run.py report [arch ...]

Targets (user spec): U (urgency priority) -> chain; J (join gating) -> diamond; R (relevance-weighted downstream cost) -> grid and
heavy; the full set is run on the composite after the isolated terms. Reported per archetype: P99 and P90 change vs baseline,
mean over seeds of per-seed changes with a paired request-level bootstrap CI, seed agreement, moves, relocated MB, and how often
join gating fired."""
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))
RES = HERE / "results" / "dag_suite"
SEEDS = (1, 2, 3)
ARCHS = ("chain", "diamond", "grid", "composite", "heavy")
T = dict(move_terms=True)
CONFIGS = {"base": {}, "U": dict(T, urgency_priority=True), "J": dict(T, join_gate=True), "R": dict(T, relevance_out=True),
           "UJR": dict(T, urgency_priority=True, join_gate=True, relevance_out=True),
           "UJ": dict(T, urgency_priority=True, join_gate=True), "UR": dict(T, urgency_priority=True, relevance_out=True),
           "JR": dict(T, join_gate=True, relevance_out=True),
           # placebos: the baseline policy with the move clock shifted by 1 ms -- no systematic effect, but the trajectory diverges,
           # so their change vs baseline is the run-to-run noise floor that a request-level bootstrap cannot see
           "P1": {"_period": 2.001}, "P2": {"_period": 1.999}}
ISOLATED = ("base", "U", "J", "R")
PAIRS = ("UJ", "UR", "JR")
BURN_IN = 120.0


def job(args):
    arch, name, seed = args
    out = RES / f"{arch}_{name}_s{seed}.json"
    if out.exists():
        return arch, name, seed, "cached"
    import d3s_headroom as d
    import faaspr_fig11_f3 as m
    import dag_suite
    from dfps.o3s import O3SimAdjuster
    from dfps.sim import Sim
    from dfps.variants import make_adjuster, sim_kwargs
    from frozen2 import FROZEN2
    t0 = time.time()
    sc, X0 = dag_suite.build(arch, seed)
    kw = sim_kwargs("B_STAR", m.ASSUME)
    kw.update(warmup=d.WARMUP, duration=900.0, retry_min_interval=1.0, retry_max_attempts=10, trace=True)
    cfg = CONFIGS[name]
    adj = O3SimAdjuster(make_adjuster("B_STAR", m.ASSUME, seed=seed + 300), cfg.get("_period", m.MOVE_PERIOD_F3), epoch=60.0,
                        horizon=120.0, K=5, seed=seed + 800, warmup=d.WARMUP, blind=True, cand_mode="nosim",
                        churn=dict(FROZEN2, lam=0.5, **{k: v for k, v in cfg.items() if not k.startswith("_")}), sizing_cache={})
    kw["interval"] = adj.next_interval
    sim = Sim(sc, X0.copy(), adjuster=adj, seed=seed + 400, **kw)
    res = sim.run()
    sim.check_invariants()
    cp = {w.id: float(sim.crit_path[w.id]) for w in sc.workflows}
    reqs = [[round(r[2], 3), r[1], round(r[3] - r[2], 3)] for r in sim.trace["reqs"]]
    rec = dict(arch=arch, config=name, seed=seed, p99_makespan=res["p99_makespan"], n_moved=res["n_moved"],
               cold_starts=res["cold_starts"], mb_relocated=res.get("mb_relocated"), term_stats=getattr(adj, "term_stats", None),
               cp=cp, n_tasks={str(w.id): w.n for w in sc.workflows}, reqs=reqs, wall_s=time.time() - t0)
    RES.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec))
    return arch, name, seed, f"p99={res['p99_makespan']:.1f} moved={res['n_moved']} {rec['wall_s']:.0f}s"


def run(workers, archs, only=None):
    RES.mkdir(parents=True, exist_ok=True)
    jobs = [(a, c, s) for s in SEEDS for a in archs for c in (ISOLATED if a != "composite" else ISOLATED + ("UJR",))]
    if only:                                                     # explicit config list, e.g. the composite's pair runs
        jobs = [(a, c, s) for s in SEEDS for a in archs for c in only]
    print(f"{len(jobs)} runs, {workers} workers", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        for a, c, s, msg in ex.map(job, jobs):
            print(f"done {a} {c} s{s}: {msg}", flush=True)


def load(a, c):
    return {int(p.stem.rsplit("_s", 1)[1]): json.loads(p.read_text()) for p in RES.glob(f"{a}_{c}_s*.json")}


def window(rec, lo=BURN_IN):
    return {(x[0], x[1]): x[2] for x in rec["reqs"] if x[0] >= lo}


def delta(a, c, stat, B=400, rng=np.random.default_rng(0), ref="base"):
    base, cur = load(a, ref), load(a, c)
    pairs = []
    for s in sorted(set(base) & set(cur)):
        x, y = window(base[s]), window(cur[s])
        k = [key for key in x if key in y]
        if len(k) > 200:
            pairs.append((np.array([x[key] for key in k]), np.array([y[key] for key in k])))
    if not pairs:
        return None
    per = [100 * (np.percentile(y, stat) / np.percentile(x, stat) - 1) for x, y in pairs]
    bs = [np.mean([100 * (np.percentile(y[i], stat) / np.percentile(x[i], stat) - 1)
                   for x, y in pairs for i in [rng.integers(0, len(x), len(x))]]) for _ in range(B)]
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return float(np.mean(per)), float(lo), float(hi), sum(p < 0 for p in per), len(pairs), per


NOTES = {("chain", "R"): "  <- on a chain every edge is a cut edge (weight 1.0) while the baseline uses 0.5: this row is a downstream-weight "
                         "change 0.5 -> 1.0, NOT structural gating",
         ("chain", "J"): "  <- no joins: cannot fire"}


def interactions(a="composite"):
    print(f"\n=== {a}: interaction of urgency (U), join gating (J), relevance (R) -- mean over seeds of per-seed change (%); "
          f"pair/triple minus the sum of the parts, negative = synergy, positive = they cancel ===")
    for stat in (99, 90):
        d = {c: delta(a, c, stat) for c in ("U", "J", "R", "UJ", "UR", "JR", "UJR")}
        v = {c: (r[0] if r else None) for c, r in d.items()}
        print(f"  P{stat}: " + "  ".join(f"{c} {x:+.1f}" if x is not None else f"{c} n/a" for c, x in v.items()))
        for x, y in (("U", "J"), ("U", "R"), ("J", "R")):
            xy = x + y
            if None not in (v[x], v[y], v[xy]):
                print(f"      {x} x {y}: pair {v[xy]:+.1f} vs sum of parts {v[x] + v[y]:+.1f} -> interaction {v[xy] - v[x] - v[y]:+.1f}")
        for x, ref in (("UR", "U"), ("JR", "J")):                # does adding relevance hurt the term it is added to? (paired, direct)
            r = delta(a, x, stat, ref=ref)
            if r:
                print(f"      {x} vs {ref} directly: {r[0]:+.1f}% [{r[1]:+.1f},{r[2]:+.1f}]{'*' if r[1] > 0 or r[2] < 0 else ''}  "
                      f"per seed {', '.join(f'{p:+.1f}%' for p in r[5])}")
        if None not in (v["U"], v["J"], v["R"], v["UJR"]):
            print(f"      all three: UJR {v['UJR']:+.1f} vs U+J+R {v['U'] + v['J'] + v['R']:+.1f} -> interaction {v['UJR'] - v['U'] - v['J'] - v['R']:+.1f}")


def firing(archs):
    print("\n=== JOIN GATING firing: tasks that were the last missing input of a join when considered for a move (summed over seeds) ===")
    print(f"  {'archetype':10s} {'joins/wf':>8s} {'move candidates':>16s} {'gating candidates':>18s} {'share':>7s} {'gating moved':>13s} {'moves':>8s}   per seed (gating cands / moved)")
    for a in archs:
        recs = load(a, "J")
        ts = {s: r["term_stats"] for s, r in recs.items() if r.get("term_stats")}
        if not ts:
            continue
        cand = sum(t["candidates"] for t in ts.values())
        gc = sum(t["gating_candidates"] for t in ts.values())
        gm = sum(t["gating_moved"] for t in ts.values())
        mv = sum(t["moves"] for t in ts.values())
        jw = {"chain": 0.0, "diamond": 1.0, "grid": 9.5, "composite": 1.0, "heavy": 1.0}[a]
        print(f"  {a:10s} {jw:8.1f} {cand:16d} {gc:18d} {gc / max(cand, 1):7.2%} {gm:13d} {mv:8d}   "
              + ", ".join(f"s{s}: {t['gating_candidates']}/{t['gating_moved']}" for s, t in sorted(ts.items())))


def report(archs):
    for a in archs:
        base = load(a, "base")
        if not base:
            continue
        x = np.concatenate([[r[2] for r in rec["reqs"] if r[0] >= BURN_IN] for rec in base.values()])
        st = np.mean([np.mean([r[2] / rec["cp"][str(r[1])] for r in rec["reqs"] if r[0] >= BURN_IN]) for rec in base.values()])
        tk = np.mean([np.mean([rec["n_tasks"][str(r[1])] for r in rec["reqs"]]) for rec in base.values()])
        print(f"\n=== {a}: baseline P99 {np.mean([np.percentile([r[2] for r in rec['reqs'] if r[0] >= BURN_IN], 99) for rec in base.values()]):.1f}s "
              f"(per seed {', '.join(f'{np.percentile([r[2] for r in rec['reqs'] if r[0] >= BURN_IN], 99):.0f}' for _, rec in sorted(base.items()))}), "
              f"mean stretch {st:.2f}, {tk:.1f} tasks/request, seeds {sorted(base)} ===")
        print(f"  {'config':6s} {'P99 change':>30s} {'seeds better':>12s} {'P90 change':>30s} {'moves':>8s} {'relocMB':>8s}  gating cands/moved")
        for c in CONFIGS:
            if c == "base":
                continue
            r99, r90 = delta(a, c, 99), delta(a, c, 90)
            if r99 is None:
                continue
            recs = load(a, c)
            mv = np.mean([100 * (recs[s]["n_moved"] / base[s]["n_moved"] - 1) for s in recs if s in base])
            rl = np.mean([100 * (recs[s]["mb_relocated"] / base[s]["mb_relocated"] - 1) for s in recs if s in base and base[s]["mb_relocated"]])
            ts = [r["term_stats"] for r in recs.values() if r.get("term_stats")]
            g = f"{sum(t['gating_candidates'] for t in ts)}/{sum(t['gating_moved'] for t in ts)}" if ts else "-"
            star = "*" if (r99[1] > 0 or r99[2] < 0) else " "
            print(f"  {c:6s} {r99[0]:+6.1f}% [{r99[1]:+5.1f},{r99[2]:+5.1f}]{star:1s}        {r99[3]}/{r99[4]:<9d} "
                  f"{r90[0]:+6.1f}% [{r90[1]:+5.1f},{r90[2]:+5.1f}]  {mv:+7.1f}% {rl:+7.1f}%  {g}")
            print(f"         per-seed P99 change: {', '.join(f'{v:+.1f}%' for v in r99[5])}{NOTES.get((a, c), '')}")
    firing(archs)
    interactions()


if __name__ == "__main__":
    only = None
    if "--configs" in sys.argv:
        i = sys.argv.index("--configs")
        only = sys.argv[i + 1].split(",")
        del sys.argv[i:i + 2]
    archs = tuple(sys.argv[3:]) or ARCHS if sys.argv[1] == "run" else tuple(sys.argv[2:]) or ARCHS
    if sys.argv[1] == "run":
        run(int(sys.argv[2]), archs, only)
    else:
        report(archs)
