"""Build-phase evaluation of criticality-aware dispatch (2026-10-28). PRE-REGISTERED before any of these runs existed; the
analysis below is the registered analysis (see knowledge/_meta/log.md, entry "dispatch evaluation pre-registration").

Scenarios (loaded only: baseline mean stretch >= 3): f3 (F3 mix, data x5, rho 0.7), heavy (suite data-heavy composite, rho 0.7),
diamond and grid (suite archetypes at the rho calibrated by dispatch_calib.py, RHO below). Seeds 1-6.
Configs: base (FIFO), P1 / P2 (placebo nulls: FIFO, move clock 2.001 / 1.999 s), gate (join-gating override, else FIFO),
full2 (tiers overdue > gating > aged > urgency, aging 2x the function's median wait, overdue = type's online P95 sojourn).
Sensitivity (not tested for significance): full3 / full5 (aging 3x / 5x) on all scenarios, seeds 1-3; full2_aet (move rule's wait
estimate made priority-aware) on heavy, seeds 1-6. Every run is "ours" (FROZEN2, lam 0.5) otherwise.

Registered analysis (burn-in: arrivals >= 120 s; reference = mean of the three null runs of the same seed):
  PRIMARY (mechanism claim)  per-type P99: cells (seed, workflow type) with >= 100 requests in the variant and in all three nulls;
      cell change = P99 / mean null P99 - 1. Two-sided sign test of the share of improved cells against 1/2, Bonferroni over the
      8 (scenario x {gate, full2}) tests: p < 0.05 / 8. Calibration: the same test on P1 vs mean(base, P2) must not reject.
  SECONDARY (SLA table)      pooled P99 change; z = mean of per-seed changes / (null sigma * sqrt(1 + 1/3) / sqrt(n_seeds)),
      null sigma from the spread of the three null runs around their mean, per scenario; claim only if z < -2.95 AND >= 4/6 seeds
      improve.
  PHYSICAL                   full2: mean critical-path wait of moved tasks falls (mean of per-seed changes < 0 and >= 4/6 seeds);
      gate: join desync on the realised critical path falls on diamond and grid (same rule).
  STARVATION (reported)      per-task wait P99 / P99.9 / max; per-type mean change over seeds, types worse than +5% flagged;
      how often each tier decided a dispatch.
A variant is established on a scenario if PRIMARY rejects in its favour AND its PHYSICAL criterion holds.

  python output/data-analysis/dispatch_eval.py run <workers> [primary|sensitivity|all]   |   report
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
RES = HERE / "results" / "dispatch_eval"
SCENS = ("f3", "heavy", "diamond", "grid")
RHO = {"f3": 0.7, "heavy": 0.7, "diamond": 0.93, "grid": 0.85}     # dispatch_calib.py, seed 1 baseline: grid stretch 3.20 at 0.85, diamond 3.15 at 0.93
SEEDS = (1, 2, 3, 4, 5, 6)
NULLS = ("base", "P1", "P2")
CONFIGS = {"base": {}, "P1": dict(period=2.001), "P2": dict(period=1.999), "gate": dict(prio="gate"),
           "full1": dict(prio="full", aging=1.0), "full2": dict(prio="full", aging=2.0), "full3": dict(prio="full", aging=3.0),
           "full5": dict(prio="full", aging=5.0), "full2_aet": dict(prio="full", aging=2.0, aet=True)}
AGING_VALUES = ("full1", "full2", "full3", "full5")
BURN_IN = 120.0
Z_POOLED = 2.95
ALPHA_SIGN = 0.05 / 8
ALPHA_SIGN_AGING = 0.05 / 16     # aging-multiplier selection (knowledge/_meta/log.md, 2026-10-29): 4 values x 4 scenarios


def jobs(which, scens=SCENS):
    out = []
    if which in ("primary", "all"):
        out += [(sc, c, s) for s in SEEDS for sc in scens for c in NULLS + ("gate", "full2")]
    if which in ("sensitivity", "all"):
        out += [(sc, c, s) for s in (1, 2, 3) for sc in scens for c in ("full3", "full5")]
        out += [("heavy", "full2_aet", s) for s in SEEDS if "heavy" in scens]
    if which in ("aging", "all"):
        out += [(sc, c, s) for s in SEEDS for sc in scens for c in ("full1", "full3", "full5")]
    return out


def job(args):
    scen, name, seed = args
    out = RES / f"{scen}_{name}_s{seed}.json"
    if out.exists():
        return scen, name, seed, "cached"
    import d3s_headroom as d
    import faaspr_fig11_f3 as m
    import dag_suite
    from physical_check import decompose
    from dfps.dispatch_priority import QueuePriority
    from dfps.o3s import O3SimAdjuster
    from dfps.sim import Sim
    from dfps.variants import make_adjuster, sim_kwargs
    from frozen2 import FROZEN2
    t0 = time.time()
    cfg = CONFIGS[name]
    assert RHO[scen] is not None, f"calibrate rho for {scen} first"
    sc, X0 = m.build("F3", RHO[scen], 5, seed) if scen == "f3" else dag_suite.build(scen, seed, rho=RHO[scen])
    kw = sim_kwargs("B_STAR", m.ASSUME)
    kw.update(warmup=d.WARMUP, duration=900.0, retry_min_interval=1.0, retry_max_attempts=10, trace=True)
    churn = dict(FROZEN2, lam=0.5)
    if "prio" in cfg:
        kw["queue_priority"] = QueuePriority(cfg["prio"], aging=cfg.get("aging"))
        churn["prio_aet"] = bool(cfg.get("aet"))
    adj = O3SimAdjuster(make_adjuster("B_STAR", m.ASSUME, seed=seed + 300), cfg.get("period", m.MOVE_PERIOD_F3), epoch=60.0,
                        horizon=120.0, K=5, seed=seed + 800, warmup=d.WARMUP, blind=True, cand_mode="nosim", churn=churn,
                        sizing_cache={})
    kw["interval"] = adj.next_interval
    sim = Sim(sc, X0.copy(), adjuster=adj, seed=seed + 400, **kw)
    res = sim.run()
    sim.check_invariants()
    wfs = {w.id: dict(n=w.n, ft=list(w.ft), parents=w.parents, children=w.children, ss=w.ss) for w in sc.workflows}
    dec = decompose(sim.trace["tasks"], sim.trace["reqs"], wfs, list(sim.exec_time), sim.net.stt, hops=lambda a, b: float(sim.net.h[a, b]))
    arr = {r[0]: r[2] for r in sim.trace["reqs"]}
    waits = np.array([row[6] - row[5] for row in sim.trace["tasks"] if arr.get(row[0], 0) >= BURN_IN])
    qp = kw.get("queue_priority")
    cp = {w.id: float(sim.crit_path[w.id]) for w in sc.workflows}
    rec = dict(scen=scen, config=name, seed=seed, rho=RHO[scen], p99_makespan=res["p99_makespan"], n_moved=res["n_moved"],
               overrides=getattr(sim, "n_priority_overrides", 0), tiers=getattr(qp, "tier_counts", None),
               reqs=[[round(r[2], 3), r[1], round(r[3] - r[2], 3)] for r in sim.trace["reqs"]], cp=cp,
               means={k: float(np.mean(v)) for k, v in dec.items()},
               task_wait=dict(mean=float(waits.mean()), p99=float(np.percentile(waits, 99)), p999=float(np.percentile(waits, 99.9)),
                              max=float(waits.max())), wall_s=time.time() - t0)
    RES.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec))
    return scen, name, seed, f"p99={res['p99_makespan']:.1f} overrides={rec['overrides']} {rec['wall_s']:.0f}s"


def run(workers, which, scens=SCENS):
    RES.mkdir(parents=True, exist_ok=True)
    js = jobs(which, scens)
    print(f"{len(js)} runs, {workers} workers", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        for sc, c, s, msg in ex.map(job, js):
            print(f"done {sc} {c} s{s}: {msg}", flush=True)


# ------------------------------------------------------------------ registered analysis
def load(sc, c):
    return {s: json.loads((RES / f"{sc}_{c}_s{s}.json").read_text()) for s in SEEDS if (RES / f"{sc}_{c}_s{s}.json").exists()}


def pct(rec, q, wid=None):
    v = [x[2] for x in rec["reqs"] if x[0] >= BURN_IN and (wid is None or x[1] == wid)]
    return float(np.percentile(v, q)) if (wid is None or len(v) >= 100) else None


def sign_test(k, n):
    from scipy.stats import binomtest
    return binomtest(k, n, 0.5).pvalue if n else float("nan")


def type_cells(x, refs, seeds):
    """(seed, wid) -> change of the per-type P99 vs the mean of the reference runs."""
    cells = {}
    for s in seeds:
        for w in sorted({r[1] for r in x[s]["reqs"]}):
            v, rr = pct(x[s], 99, w), [pct(r[s], 99, w) for r in refs]
            if v is not None and None not in rr:
                cells[(s, w)] = 100 * (v / np.mean(rr) - 1)
    return cells


def report():
    for sc in SCENS:
        nulls = [load(sc, c) for c in NULLS]
        seeds = [s for s in SEEDS if all(s in n for n in nulls)]
        if not seeds:
            continue
        base = nulls[0]
        st = np.mean([np.mean([r[2] / base[s]["cp"][str(r[1])] for r in base[s]["reqs"] if r[0] >= BURN_IN]) for s in seeds])
        devs = [100 * (pct(n[s], 99) / np.mean([pct(m[s], 99) for m in nulls]) - 1) for s in seeds for n in nulls]
        sig = np.sqrt(np.sum(np.square(devs)) / (len(devs) - len(seeds)))
        print(f"\n=== {sc} (rho {base[seeds[0]]['rho']}): seeds {seeds}, baseline stretch {st:.2f}, null sigma (pooled P99) {sig:.2f}% ===")
        pl = type_cells(nulls[1], [nulls[0], nulls[2]], seeds)
        k = sum(v < 0 for v in pl.values())
        print(f"  calibration (P1 vs base,P2): per-type cells improved {k}/{len(pl)} = {k / max(len(pl), 1):.0%}, sign-test p {sign_test(k, len(pl)):.3f} "
              f"(must not reject); median {np.median(list(pl.values())):+.1f}%, worse > +5% {np.mean([v > 5 for v in pl.values()]):.0%}")
        for c in ("gate", "full2", "full3", "full5", "full2_aet"):
            x = load(sc, c)
            ss = [s for s in seeds if s in x]
            if not ss:
                continue
            cells = type_cells(x, nulls, ss)
            k = sum(v < 0 for v in cells.values())
            p = sign_test(k, len(cells))
            sens = c in ("full3", "full5", "full2_aet")
            prim = "" if sens else (" -> PRIMARY REJECTS (better)" if p < ALPHA_SIGN and k > len(cells) / 2 else
                                    (" -> primary rejects (WORSE)" if p < ALPHA_SIGN else " -> primary: no effect"))
            d99 = [100 * (pct(x[s], 99) / np.mean([pct(n[s], 99) for n in nulls]) - 1) for s in ss]
            z = np.mean(d99) / (sig * np.sqrt(1 + 1 / 3) / np.sqrt(len(ss)))
            nb = sum(v < 0 for v in d99)
            pooled = "" if sens else (" -> SLA claim" if z < -Z_POOLED and nb >= 4 else " -> no SLA claim")
            key = "wait_moved" if c != "gate" else "desync"
            phys = [100 * (x[s]["means"][key] / np.mean([n[s]["means"][key] for n in nulls]) - 1) for s in ss]
            ph_ok = np.mean(phys) < 0 and sum(v < 0 for v in phys) >= 4
            tw = {q: (np.mean([x[s]["task_wait"][q] for s in ss]), np.mean([base[s]["task_wait"][q] for s in ss])) for q in ("p99", "p999", "max")}
            by_type = {}
            for (s, w), v in cells.items():
                by_type.setdefault(w, []).append(v)
            harmed = sorted((w, np.mean(v)) for w, v in by_type.items() if len(v) >= 3 and np.mean(v) > 5)
            tiers = np.sum([x[s]["tiers"] for s in ss if x[s].get("tiers")], axis=0) if any(x[s].get("tiers") for s in ss) else None
            tag = " [sensitivity]" if sens else ""
            print(f"  {c}{tag}")
            print(f"    PRIMARY per-type P99: {k}/{len(cells)} cells improved ({k / max(len(cells), 1):.0%}), sign p {p:.2g}, median "
                  f"{np.median(list(cells.values())):+.1f}%, worse > +5% {np.mean([v > 5 for v in cells.values()]):.0%}{prim}")
            print(f"    SECONDARY pooled P99: {np.mean(d99):+.1f}% (z {z:+.2f}; seeds {', '.join(f'{v:+.1f}' for v in d99)}; {nb}/{len(ss)} better){pooled}")
            print(f"    PHYSICAL {key}: {np.mean(phys):+.1f}% ({sum(v < 0 for v in phys)}/{len(ss)} seeds lower) -> {'holds' if ph_ok else 'fails'}")
            print(f"    STARVATION task wait P99 {tw['p99'][0]:.1f} vs {tw['p99'][1]:.1f}s, P99.9 {tw['p999'][0]:.1f} vs {tw['p999'][1]:.1f}s, "
                  f"max {tw['max'][0]:.1f} vs {tw['max'][1]:.1f}s; types worse than +5% on average: "
                  f"{', '.join(f'{w} ({v:+.1f}%)' for w, v in harmed) or 'none'}"
                  + (f"; tiers won (rest/aged/gating/overdue) {tiers.tolist()}" if tiers is not None else ""))


def report_aging():
    """Aging-multiplier selection (knowledge/_meta/log.md, 2026-10-29 pre-registration): head-to-head of full1/full2/full3/full5,
    same PRIMARY/PHYSICAL/STARVATION criteria as the main registration, Bonferroni over 16 tests, fixed selection rule."""
    winners = {}
    for sc in SCENS:
        nulls = [load(sc, c) for c in NULLS]
        seeds = [s for s in SEEDS if all(s in n for n in nulls)]
        base = nulls[0]
        print(f"\n=== {sc}: aging-multiplier comparison, seeds {seeds} ===")
        candidates = []
        for c in AGING_VALUES:
            x = load(sc, c)
            ss = [s for s in seeds if s in x]
            if len(ss) < len(seeds):
                print(f"  {c}: incomplete ({len(ss)}/{len(seeds)} seeds) -- skipped")
                continue
            cells = type_cells(x, nulls, ss)
            k = sum(v < 0 for v in cells.values())
            p = sign_test(k, len(cells))
            rejects = p < ALPHA_SIGN_AGING and k > len(cells) / 2
            phys = [100 * (x[s]["means"]["wait_moved"] / np.mean([n[s]["means"]["wait_moved"] for n in nulls]) - 1) for s in ss]
            ph_ok = np.mean(phys) < 0 and sum(v < 0 for v in phys) >= 4
            by_type = {}
            for (s, w), v in cells.items():
                by_type.setdefault(w, []).append(v)
            harmed = [w for w, v in by_type.items() if len(v) >= 3 and np.mean(v) > 5]
            med = np.median(list(cells.values()))
            tw = {q: (np.mean([x[s]["task_wait"][q] for s in ss]), np.mean([base[s]["task_wait"][q] for s in ss])) for q in ("p99", "p999", "max")}
            eligible = rejects and ph_ok and not harmed
            print(f"  {c}: PRIMARY {k}/{len(cells)} cells improved, p {p:.2g} ({'rejects' if rejects else 'no reject'}); "
                  f"PHYSICAL wait_moved {np.mean(phys):+.1f}% ({'holds' if ph_ok else 'fails'}); median {med:+.1f}%; "
                  f"harmed types {harmed or 'none'}; task_wait P99 {tw['p99'][0]:.1f} vs base {tw['p99'][1]:.1f}, "
                  f"max {tw['max'][0]:.1f} vs {tw['max'][1]:.1f} -> {'ELIGIBLE' if eligible else 'not eligible'}")
            if eligible:
                candidates.append((med, c))
        if candidates:
            candidates.sort()
            winners[sc] = candidates[0][1]
            print(f"  winner: {candidates[0][1]} (median {candidates[0][0]:+.1f}%)")
        else:
            winners[sc] = "full2"
            print(f"  winner: full2 (default -- no aging value cleared all three gates)")
    vals = set(winners.values())
    print(f"\n=== per-scenario winners: {winners} ===")
    if len(vals) == 1:
        print(f"=== SINGLE GLOBAL WINNER: {vals.pop()} wins on all four scenarios ===")
    else:
        print(f"=== NO SINGLE GLOBAL WINNER -- scenarios disagree; keep full2 (aging=2.0) as the global default ===")


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(int(sys.argv[2]), sys.argv[3] if len(sys.argv) > 3 else "primary", tuple(sys.argv[4:]) or SCENS)
    elif sys.argv[1] == "report_aging":
        report_aging()
    else:
        report()
