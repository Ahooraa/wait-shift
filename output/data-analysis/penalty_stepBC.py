"""Steps B/C of the move-rule penalty study (2026-10-28): full 900 s F3 window, "ours" (FROZEN2, lam=0.5) with the four switchable
move terms of dfps/o3s.py::_rebalance_terms, scored ex-ante per workflow family and per DAG type as well as pooled.

  python output/data-analysis/penalty_stepBC.py run <stage> [workers]     stage: 1 (single terms + margin sweep) | 2 (combinations)
  python output/data-analysis/penalty_stepBC.py report [stage ...]

Per (config, seed): results/penalty_stepBC/<config>_s<seed>.json -- resumable, finished runs are skipped. Families are derived from
the DAG structure (chain / fan-in / fan-out / fork-join), never from the outcome, so every statistic is an ex-ante cut."""
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))
RES = HERE / "results" / "penalty_stepBC"
SEEDS = (1, 2, 3)
FAMS = ("chain", "fan-in", "fan-out", "fork-join")
T = dict(move_terms=True)
CONFIGS = {
    "base": {},
    "terms_off": dict(T),
    "m125": dict(T, margin_theta=0.125), "m250": dict(T, margin_theta=0.25), "m375": dict(T, margin_theta=0.375),
    "m500": dict(T, margin_theta=0.5),
    "U": dict(T, urgency_priority=True), "J": dict(T, join_gate=True), "R": dict(T, relevance_out=True),
    "m250_U": dict(T, margin_theta=0.25, urgency_priority=True), "m250_J": dict(T, margin_theta=0.25, join_gate=True),
    "m250_R": dict(T, margin_theta=0.25, relevance_out=True),
    "m250_UJ": dict(T, margin_theta=0.25, urgency_priority=True, join_gate=True),
    "m250_UJR": dict(T, margin_theta=0.25, urgency_priority=True, join_gate=True, relevance_out=True),
    "UJ": dict(T, urgency_priority=True, join_gate=True),
    "m125_U": dict(T, margin_theta=0.125, urgency_priority=True), "m125_J": dict(T, margin_theta=0.125, join_gate=True),
    "m125_UJ": dict(T, margin_theta=0.125, urgency_priority=True, join_gate=True),
    "m125_UJR": dict(T, margin_theta=0.125, urgency_priority=True, join_gate=True, relevance_out=True),
}
STAGES = {1: ["base", "terms_off", "m125", "m250", "m375", "m500", "U", "J", "R"],
          2: ["m250_U", "m250_J", "m250_UJ", "m250_UJR"],
          3: ["m125_U", "m125_J", "m125_UJ", "m125_UJR", "UJ"]}                  # same combinations on the low bar: the margin x urgency interaction


def family(wf):
    forks = any(len(c) > 1 for c in wf.children)
    joins = any(len(p) > 1 for p in wf.parents)
    return {(False, False): "chain", (False, True): "fan-in", (True, False): "fan-out", (True, True): "fork-join"}[(forks, joins)]


def job(args):
    name, seed = args
    out = RES / f"{name}_s{seed}.json"
    if out.exists():
        return name, seed, "cached"
    import faaspr_fig11_f3 as m
    from dfps.o3s import O3SimAdjuster
    from dfps.sim import Sim
    from dfps.variants import make_adjuster, sim_kwargs
    from frozen2 import FROZEN2
    t0 = time.time()
    sc, X0 = m.build("F3", 0.7, 5, seed)
    kw = sim_kwargs("B_STAR", m.ASSUME)
    kw.update(warmup=m.d.WARMUP, duration=900.0, retry_min_interval=1.0, retry_max_attempts=10, trace=True)
    adj = O3SimAdjuster(make_adjuster("B_STAR", m.ASSUME, seed=seed + 300), m.MOVE_PERIOD_F3, epoch=60.0, horizon=120.0, K=5,
                        seed=seed + 800, warmup=m.d.WARMUP, blind=True, cand_mode="nosim", churn=dict(FROZEN2, lam=0.5, **CONFIGS[name]),
                        sizing_cache={})
    kw["interval"] = adj.next_interval
    sim = Sim(sc, X0.copy(), adjuster=adj, seed=seed + 400, **kw)
    res = sim.run()
    sim.check_invariants()
    fam = {w.id: family(w) for w in sc.workflows}
    rows = [(r[1], r[3] - r[2]) for r in sim.trace["reqs"]]
    reqs = [[round(r[2], 3), r[1], round(r[3] - r[2], 3)] for r in sim.trace["reqs"]]       # arrival, workflow type, sojourn

    def stat(v):
        v = np.asarray(v, float)
        if not len(v):
            return None
        return dict(n=len(v), mean=float(v.mean()), p90=float(np.percentile(v, 90)), p99=float(np.percentile(v, 99)))

    d = dict(config=name, seed=seed, p99_makespan=res["p99_makespan"], n_moved=res["n_moved"], cold_starts=res["cold_starts"],
             pooled=stat([s for _, s in rows]),
             family={f: stat([s for w, s in rows if fam[w] == f]) for f in FAMS},
             type={str(w): dict(stat([s for ww, s in rows if ww == w]), family=fam[w]) for w in sorted({w for w, _ in rows})},
             fam_of={str(w): f for w, f in fam.items()},
             mb_of={str(w.id): float(w.input_size + sum(w.ss.values())) for w in sc.workflows}, reqs=reqs, wall_s=time.time() - t0)
    RES.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(d))
    return name, seed, f"p99={res['p99_makespan']:.2f} moved={res['n_moved']} {d['wall_s']:.0f}s"


def run(stage, workers):
    RES.mkdir(parents=True, exist_ok=True)
    jobs = [(c, s) for s in SEEDS for c in STAGES[stage]]
    print(f"{len(jobs)} runs, {workers} workers", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        for name, seed, msg in ex.map(job, jobs):
            print(f"done {name} s{seed}: {msg}", flush=True)


def load(name):
    return [json.loads(p.read_text()) for p in sorted(RES.glob(f"{name}_s*.json"))]


BURN_IN = 120.0                                   # arrivals before this are dropped (the simulator's own warm-up is 60 s)
WINDOWS = {"pre [120,600)": (BURN_IN, 600.0), "transition [600,720)": (600.0, 720.0), "settled [720,900)": (720.0, 1e9)}


def cut(r, lo, hi, fam=None):
    s = np.array([x[2] for x in r["reqs"] if lo <= x[0] < hi and (fam is None or r["fam_of"][str(x[1])] == fam)])
    return dict(n=len(s), mean=float(s.mean()), p90=float(np.percentile(s, 90)), p99=float(np.percentile(s, 99))) if len(s) else None


def report(stages):
    names = [c for s in stages for c in STAGES[s]]
    base = {r["seed"]: r for r in load("base")}
    if not base:
        print("no base runs")
        return
    print(f"=== burn-in delta on the baseline (arrivals >= 60 s as simulated vs >= {BURN_IN:.0f} s), mean over seeds {sorted(base)} ===")
    for lab, fam in (("pooled", None),) + tuple((f, f) for f in FAMS):
        a = [x for x in (cut(r, 0, 1e9, fam) for r in base.values()) if x]
        b = [x for x in (cut(r, BURN_IN, 1e9, fam) for r in base.values()) if x]
        if not a:
            continue
        print(f"  {lab:10s} n {np.mean([x['n'] for x in a]):6.0f} -> {np.mean([x['n'] for x in b]):6.0f}   "
              f"mean {np.mean([x['mean'] for x in a]):6.1f} -> {np.mean([x['mean'] for x in b]):6.1f}   "
              f"P90 {np.mean([x['p90'] for x in a]):6.1f} -> {np.mean([x['p90'] for x in b]):6.1f}   "
              f"P99 {np.mean([x['p99'] for x in a]):6.1f} -> {np.mean([x['p99'] for x in b]):6.1f} "
              f"({100 * (np.mean([x['p99'] for x in b]) / np.mean([x['p99'] for x in a]) - 1):+.1f}%)")

    mb_all = [mb for f in RES.glob("*_s*.json") for mb in json.loads(f.read_text()).get("mb_of", {}).values()]
    med_mb = float(np.median(mb_all)) if mb_all else 0.0              # one fixed threshold for every seed and config

    def sel(r, x, fam):
        if fam is None:
            return True
        if fam in ("heavy", "light"):
            return (r["mb_of"][str(x[1])] >= med_mb) == (fam == "heavy")
        return r["fam_of"][str(x[1])] == fam

    def pooled(rs, lo, hi, fam):
        """Requests of all seeds concatenated, then the percentile (not a mean of per-seed percentiles)."""
        s = np.array([x[2] for r in rs for x in r["reqs"] if lo <= x[0] < hi and sel(r, x, fam)])
        if not len(s):
            return None
        return dict(n=len(s), p90=float(np.percentile(s, 90)), p99=float(np.percentile(s, 99)), mean=float(s.mean()))

    def table(title, key, cols):
        print(f"\n=== {title} ===")
        print(f"{'config':10s} {'seeds':>5s} | " + " ".join(f"{c[0][:13]:>13s}" for c in cols) + " | moves d%")
        for c in names:
            rs = [r for r in load(c) if r["seed"] in base]
            if not rs:
                continue
            bs = [base[r["seed"]] for r in rs]
            cells = []
            for _, fam, lo, hi in cols:
                a, b = pooled(rs, lo, hi, fam), pooled(bs, lo, hi, fam)
                cells.append(None if a is None or b is None else 100 * (a[key] / b[key] - 1))
            print(f"{c:10s} {len(rs):5d} | " + " ".join(f"{'n/a':>13s}" if x is None else f"{x:+12.1f}%" for x in cells)
                  + f" | {np.mean([100 * (r['n_moved'] / base[r['seed']]['n_moved'] - 1) for r in rs]):+7.1f}%")

    fam_cols = [(f, f, BURN_IN, 1e9) for f in FAMS] + [("data-heavy", "heavy", BURN_IN, 1e9), ("data-light", "light", BURN_IN, 1e9), ("POOLED", None, BURN_IN, 1e9)]
    win_cols = [(w, None) + v for w, v in WINDOWS.items()]
    table(f"FAMILY level, P99 change vs baseline (%), requests of all seeds pooled, burn-in {BURN_IN:.0f} s (negative = better)", "p99", fam_cols)
    table("FAMILY level, P90 change vs baseline (%), same cut", "p90", fam_cols)
    table("REGIME windows (all families), P90 change vs baseline (%) -- primary metric for windows", "p90", win_cols)
    table("REGIME windows, P99 change vs baseline (%)", "p99", win_cols)
    for w, (lo, hi) in WINDOWS.items():
        table(f"FAMILY x window, P90 change (%), window {w}", "p90", [(f, f, lo, hi) for f in FAMS])

    print("\n=== INTERACTION in pooled P99 change (%): d(theta+X) - d(theta) - d(X); negative = the pair beats the sum of its parts ===")
    def d99(c, lo=BURN_IN, hi=1e9, fam=None):
        rs = [r for r in load(c) if r["seed"] in base]
        if not rs:
            return None
        a, b = pooled(rs, lo, hi, fam), pooled([base[r["seed"]] for r in rs], lo, hi, fam)
        return None if a is None or b is None else 100 * (a["p99"] / b["p99"] - 1)
    for m_tag in ("m125", "m250"):
        for x_tag in ("U", "J", "R"):
            a, b, ab = d99(m_tag), d99(x_tag), d99(f"{m_tag}_{x_tag}")
            if None not in (a, b, ab):
                print(f"  {m_tag} + {x_tag}: theta {a:+.1f}  {x_tag} {b:+.1f}  pair {ab:+.1f}  interaction {ab - a - b:+.1f}")
    for lab, fam in (("pooled", None),) + tuple((f, f) for f in FAMS) + (("data-heavy", "heavy"), ("data-light", "light")):
        u, j, uj = d99("U", fam=fam), d99("J", fam=fam), d99("UJ", fam=fam)
        if None not in (u, j, uj):
            print(f"  urgency x join gating, {lab:10s}: U {u:+.1f}  J {j:+.1f}  pair {uj:+.1f}  interaction {uj - u - j:+.1f}")

    print("\n=== SEED AGREEMENT: seeds (of those run) in which the cell's P99 beats the baseline of the same seed; burn-in applied ===")
    cols = fam_cols + win_cols
    print(f"{'config':10s} | " + " ".join(f"{c[0][:13]:>13s}" for c in cols))
    for c in names:
        rs = [r for r in load(c) if r["seed"] in base]
        if not rs:
            continue
        cells = []
        for _, fam, lo, hi in cols:
            pairs = [(pooled([r], lo, hi, fam), pooled([base[r["seed"]]], lo, hi, fam)) for r in rs]
            pairs = [(a, b) for a, b in pairs if a is not None and b is not None]
            cells.append(f"{sum(a['p99'] < b['p99'] for a, b in pairs)}/{len(pairs)}" if pairs else "n/a")
        print(f"{c:10s} | " + " ".join(f"{x:>13s}" for x in cells))
    print("\nper seed, pooled P99 after burn-in / n_moved:")
    for c in names:
        rs = load(c)
        if rs:
            print(f"  {c:10s} " + "  ".join(f"s{r['seed']}: {cut(r, BURN_IN, 1e9)['p99']:.1f}/{r['n_moved']}" for r in rs))
    print("\nnote: family x window cells hold few requests (e.g. fan-out is ~1000 in total); the P99 of such a cell rests on a handful of requests")


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(int(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else 2)
    else:
        report([int(x) for x in sys.argv[2:]] or [1, 2])
