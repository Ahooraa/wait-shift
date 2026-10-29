"""Gate 1 of criticality-aware dispatch (2026-10-28): the honest upper bound, on loaded scenarios only.

  f3     the F3 mix at the project's default data scale x5 (stretch ~3)
  heavy  the DAG suite's data-heavy composite (x10 states, stretch ~3.95)

Configs (all "ours" = FROZEN2, lam 0.5): base (FIFO), P1/P2 (placebos: FIFO, move clock 2.001 / 1.999 s), gate (join-gating runs
first, else FIFO), full (join-gating first, then normalised projected sojourn). gate/full are UNCAPPED (no starvation control):
the most this lever can deliver online. The move rule is left unchanged, so its queue-position estimate still assumes FIFO.

Upper bound = full's P99 change vs the mean of the three null runs per seed (base, P1, P2), with the null spread as the noise
floor. The base runs also report the first-order replay ceiling A_all (dfps/diagnostics.py::bounds, optimistic: ignores
knock-on effects) for comparison. Decision rule (user, pre-registered 2026-10-28): ceiling < 3% -> do not build; >= 6% -> build
and evaluate; 3-6% -> build only the minimal join-gating override.

  python output/data-analysis/dispatch_ceiling.py run <workers>   |   report
"""
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))
RES = HERE / "results" / "dispatch_ceiling"
SEEDS = (1, 2, 3)
SCENS = ("f3", "heavy")
CONFIGS = {"base": {}, "P1": dict(period=2.001), "P2": dict(period=1.999), "gate": dict(prio="gate"), "full": dict(prio="full")}
BURN_IN = 120.0


def job(args):
    scen, name, seed = args
    out = RES / f"{scen}_{name}_s{seed}.json"
    if out.exists():
        return scen, name, seed, "cached"
    import d3s_headroom as d
    import faaspr_fig11_f3 as m
    import dag_suite
    from physical_check import decompose
    from dfps import diagnostics
    from dfps.dispatch_priority import QueuePriority
    from dfps.o3s import O3SimAdjuster
    from dfps.sim import Sim
    from dfps.variants import make_adjuster, sim_kwargs
    from frozen2 import FROZEN2
    t0 = time.time()
    cfg = CONFIGS[name]
    sc, X0 = m.build("F3", 0.7, 5, seed) if scen == "f3" else dag_suite.build(scen, seed)
    kw = sim_kwargs("B_STAR", m.ASSUME)
    kw.update(warmup=d.WARMUP, duration=900.0, retry_min_interval=1.0, retry_max_attempts=10, trace=True)
    if "prio" in cfg:
        kw["queue_priority"] = QueuePriority(cfg["prio"], aging=None)     # uncapped: no overdue / aging tiers
    adj = O3SimAdjuster(make_adjuster("B_STAR", m.ASSUME, seed=seed + 300), cfg.get("period", m.MOVE_PERIOD_F3), epoch=60.0,
                        horizon=120.0, K=5, seed=seed + 800, warmup=d.WARMUP, blind=True, cand_mode="nosim",
                        churn=dict(FROZEN2, lam=0.5), sizing_cache={})
    kw["interval"] = adj.next_interval
    sim = Sim(sc, X0.copy(), adjuster=adj, seed=seed + 400, **kw)
    res = sim.run()
    sim.check_invariants()
    wfs = {w.id: dict(n=w.n, ft=list(w.ft), parents=w.parents, children=w.children, ss=w.ss) for w in sc.workflows}
    dec = decompose(sim.trace["tasks"], sim.trace["reqs"], wfs, list(sim.exec_time), sim.net.stt, hops=lambda a, b: float(sim.net.h[a, b]))
    arr = {r[0]: r[2] for r in sim.trace["reqs"]}
    waits = np.array([row[6] - row[5] for row in sim.trace["tasks"] if arr.get(row[0], 0) >= BURN_IN])
    rec = dict(scen=scen, config=name, seed=seed, p99_makespan=res["p99_makespan"], n_moved=res["n_moved"],
               overrides=getattr(sim, "n_priority_overrides", 0),
               reqs=[[round(r[2], 3), r[1], round(r[3] - r[2], 3)] for r in sim.trace["reqs"]],
               means={k: float(np.mean(v)) for k, v in dec.items()},
               task_wait=dict(mean=float(waits.mean()), p99=float(np.percentile(waits, 99)), p999=float(np.percentile(waits, 99.9)),
                              max=float(waits.max())),
               bounds=diagnostics.bounds(sim) if name == "base" else None, wall_s=time.time() - t0)
    RES.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec))
    return scen, name, seed, f"p99={res['p99_makespan']:.1f} overrides={rec['overrides']} {rec['wall_s']:.0f}s"


def run(workers):
    RES.mkdir(parents=True, exist_ok=True)
    jobs = [(sc, c, s) for s in SEEDS for c in ("base", "full", "gate", "P1", "P2") for sc in SCENS]
    print(f"{len(jobs)} runs, {workers} workers", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        for sc, c, s, msg in ex.map(job, jobs):
            print(f"done {sc} {c} s{s}: {msg}", flush=True)


def report():
    def load(sc, c):
        return {s: json.loads((RES / f"{sc}_{c}_s{s}.json").read_text()) for s in SEEDS if (RES / f"{sc}_{c}_s{s}.json").exists()}

    def pct(rec, q):
        return float(np.percentile([x[2] for x in rec["reqs"] if x[0] >= BURN_IN], q))

    for sc in SCENS:
        nulls = [load(sc, c) for c in ("base", "P1", "P2")]
        seeds = [s for s in SEEDS if all(s in n for n in nulls)]
        if not seeds:
            continue
        devs = {q: [100 * (pct(n[s], q) / np.mean([pct(m[s], q) for m in nulls]) - 1) for s in seeds for n in nulls] for q in (99, 90)}
        sig = {q: np.sqrt(np.sum(np.square(v)) / (len(v) - len(seeds))) for q, v in devs.items()}
        b = load(sc, "base")
        print(f"\n=== {sc}: seeds {seeds}; null-run noise sigma P99 {sig[99]:.2f}%, P90 {sig[90]:.2f}% ===")
        for s in seeds:
            bd = b[s]["bounds"]
            print(f"  s{s} replay ceiling A_all (first-order, optimistic): P99 {100 * (bd['A_all_p99'] / bd['base_p99'] - 1):+.1f}%  "
                  f"(A_unmoved {100 * (bd['A_unmoved_p99'] / bd['base_p99'] - 1):+.1f}%)")
        for c in ("gate", "full"):
            x = load(sc, c)
            ss = [s for s in seeds if s in x]
            if not ss:
                continue
            line = []
            for q in (99, 90):
                d = [100 * (pct(x[s], q) / np.mean([pct(m[s], q) for m in nulls]) - 1) for s in ss]
                z = np.mean(d) / (sig[q] * np.sqrt(1 + 1 / 3) / np.sqrt(len(d)))
                line.append(f"P{q} {np.mean(d):+5.1f}% (z {z:+.2f}; seeds {', '.join(f'{v:+.1f}' for v in d)})")
            dm = {k: np.mean([x[s]["means"][k] for s in ss]) / np.mean([b[s]["means"][k] for s in ss]) - 1 for k in ("desync", "soj")}
            tw = {k: (np.mean([x[s]["task_wait"][k] for s in ss]), np.mean([b[s]["task_wait"][k] for s in ss])) for k in ("p99", "p999", "max")}
            print(f"  {c:5s} " + "   ".join(line))
            print(f"        join desync {100 * dm['desync']:+.1f}%, mean sojourn {100 * dm['soj']:+.1f}%, overrides/run "
                  f"{np.mean([x[s]['overrides'] for s in ss]):.0f}; task wait P99 {tw['p99'][0]:.1f} vs {tw['p99'][1]:.1f}s, "
                  f"P99.9 {tw['p999'][0]:.1f} vs {tw['p999'][1]:.1f}s, max {tw['max'][0]:.1f} vs {tw['max'][1]:.1f}s (starvation check)")


if __name__ == "__main__":
    run(int(sys.argv[2])) if sys.argv[1] == "run" else report()
