"""2x2 grid, re-run under the current code (2026-10-29): the original grid2x2.py (2026-10-22) is stale -- controllers.py,
dispatchers.py and model.py changed since (fw-weighted proportional_counts, min-replication floor, new dispatchers; all
verified backward-compatible for fw=None/ones, but the Scenario pickle itself needed a __setstate__ fix, dfps/model.py,
2026-10-29, to load at all under current code). User decision (2026-10-29): cells B and D now also carry the established
criticality-aware dispatch (QueuePriority("full", aging=2.0), the registered default from the dispatch-eval work) on top
of the finish-time move rule, so this grid tests the interaction of {re-layout} x {moves + criticality dispatch}, not
just {re-layout} x {moves}. Same scenarios as the original: F1/F2 x rho in (0.5, 0.7, 0.85) x seeds 1-3 (18 cases).

  A fixed layout, nothing adapts         churn = {no_inner, no_relayout}
  B fixed layout + moves + crit. dispatch  churn = FROZEN2 + lam=0.5 + no_relayout; queue_priority=full(aging=2.0)
  C re-layout only, no moves             churn = FROZEN2 + lam=0.5 + rebal=False
  D re-layout + moves + crit. dispatch (= "ours", current)   churn = FROZEN2 + lam=0.5; queue_priority=full(aging=2.0)

  python output/data-analysis/grid2x2_v2.py run [workers]   |   analyze
"""
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
import d3s_headroom as d  # noqa: E402
from frozen2 import FROZEN2, MOVE_PERIOD_S  # noqa: E402

RUNS = ROOT / "results" / "grid2x2_v2"
OUT = HERE / "results"
M = "p99_makespan"
FAMS, RHOS, SEEDS = ("F1", "F2"), (0.5, 0.7, 0.85), (1, 2, 3)
CHURN_OURS = dict(FROZEN2, lam=0.5)                 # "ours", identical to dispatch_eval.py / graphaware_sweep.py
CELLS = {
    "A": dict(no_inner=True, no_relayout=True),
    "B": dict(CHURN_OURS, no_relayout=True, prio=True),
    "C": dict(CHURN_OURS, rebal=False),
    "D": dict(CHURN_OURS, prio=True),
}


def job(args):
    try:
        return _job(args)
    except Exception:
        import traceback
        Path(args[1]).with_suffix(".err").write_text(traceback.format_exc())
        return args[1] + " FAILED"


def _job(args):
    import pickle
    assert np.__version__.startswith("1."), "run with the Anaconda interpreter (numpy 1.26): numpy 2 changes the random streams"
    tg, out_path, seed, period, churn = args
    from dfps.dispatch_priority import QueuePriority
    from dfps.o3s import O3SimAdjuster
    from dfps.sim import Sim
    from dfps.variants import make_adjuster, sim_kwargs
    import yaml
    if Path(out_path).exists():
        return out_path
    ASSUME = yaml.safe_load((ROOT / "config" / "assumptions.yaml").read_text(encoding="utf-8"))
    sc = pickle.load(open(d.D1 / f"{tg}.pkl", "rb"))
    P = pickle.load(open(d.D1 / f"{tg}.prep.pkl", "rb"))
    kw = sim_kwargs("B_STAR", ASSUME)
    kw.update(warmup=d.WARMUP, duration=d.DURATION, retry_min_interval=1.0, retry_max_attempts=10)
    churn = dict(churn)
    use_prio = churn.pop("prio", False)
    if use_prio:
        kw["queue_priority"] = QueuePriority("full", aging=2.0)
    t0 = time.time()
    adj = O3SimAdjuster(make_adjuster("B_STAR", ASSUME, seed=seed + 300), period, epoch=60.0, horizon=30.0, K=8,
                        seed=seed + 800, warmup=d.WARMUP, blind=True, cand_mode="nosim", churn=churn)
    kw["interval"] = adj.next_interval
    sim = Sim(sc, P["X0"].copy(), adjuster=adj, seed=seed + 400, **kw)
    r = sim.run()
    sim.check_invariants()
    r["wall_s"] = time.time() - t0
    Path(out_path).write_text(json.dumps(dict(family=sc.meta["family"], rho=sc.meta["rho"], seed=seed, period=period,
                                              result=r, n_moved=r.get("n_moved"),
                                              overrides=getattr(sim, "n_priority_overrides", 0))))
    return out_path


def jobs():
    out = []
    for f in FAMS:
        for r in RHOS:
            for s in SEEDS:
                tg = d.tag(f, r, s)
                for c, churn in CELLS.items():
                    out.append((tg, str(RUNS / f"{tg}.{c}.json"), s, MOVE_PERIOD_S[f], churn))
    return out


def run(workers):
    RUNS.mkdir(parents=True, exist_ok=True)
    js = jobs()
    print(f"{len(js)} runs, {workers} workers", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        for done in ex.map(job, js):
            print("done", done, flush=True)


def analyze():
    from d1_rlla import BASE, D1, boot
    bstar, rl, rl_cal = {}, {}, {}
    for d_ in (D1, BASE):
        for f in d_.glob("*.json"):
            x = json.loads(f.read_text())
            if x["family"] not in FAMS:
                continue
            k = (x["family"], x["rho"], x["seed"])
            if x.get("ctrl") == "B_STAR":
                bstar[k] = x["result"][M]
            elif x.get("ctrl") == "RL":
                rl[k] = x["result"][M]
            elif x.get("ctrl") == "RL_CAL":
                rl_cal[k] = x["result"][M]
    runs = {c: {} for c in CELLS}
    for c in CELLS:
        for f in RUNS.glob(f"*.{c}.json"):
            x = json.loads(f.read_text())
            runs[c][(x["family"], x["rho"], x["seed"])] = x["result"][M]
    p = lambda b: f"{b['mean'] * 100:+7.1f}% ({b['lo'] * 100:+.0f} to {b['hi'] * 100:+.0f})"  # noqa: E731
    out = {}
    for rhos, rl_lab in (((0.5,), "50% load"), ((0.7, 0.85), "70-85% load"), ((0.5, 0.7, 0.85), "all loads")):
        ks = sorted(k for k in set.intersection(*(set(r) for r in runs.values())) if k[1] in rhos and k in bstar)
        if not ks:
            continue
        print(f"\n=== {rl_lab}: {len(ks)} cases; gain over B* (P99) ===")
        g = {c: [(bstar[k] - runs[c][k]) / bstar[k] for k in ks] for c in CELLS}
        for c, lab in (("A", "A fixed layout, nothing adapts"), ("B", "B fixed layout + moves + crit. dispatch"),
                       ("C", "C re-layout only"), ("D", "D re-layout + moves + crit. dispatch (ours)")):
            out[f"{c}|{rl_lab}"] = boot(g[c])
            print(f"  {lab:40s} {p(out[f'{c}|{rl_lab}'])}")
        best_existing = {k: min(bstar[k], rl.get(k, np.inf), rl_cal.get(k, np.inf)) for k in ks}
        for name, ref in (("B*", bstar), ("best-existing (B*/RL/RL_CAL)", best_existing)):
            avail = [k for k in ks if k in ref and np.isfinite(ref[k])]
            if not avail:
                continue
            gD = [(ref[k] - runs["D"][k]) / ref[k] for k in avail]
            b = boot(gD)
            out[f"D_vs_{name}|{rl_lab}"] = b
            print(f"  D (ours+crit.dispatch) vs {name:30s} {p(b)}  n={len(avail)}")
        # effects on the log-P99 scale so they add: effect = ln(P99_without / P99_with)
        L = {c: np.array([np.log(runs[c][k]) for k in ks]) for c in CELLS}
        e_moves_fixed, e_moves_relay = L["A"] - L["B"], L["C"] - L["D"]
        e_relay_nomoves, e_relay_moves = L["A"] - L["C"], L["B"] - L["D"]
        inter = (L["A"] - L["B"]) - (L["C"] - L["D"])
        for name, v in (("moves+dispatch, on a fixed layout   (A to B)", e_moves_fixed), ("moves+dispatch, with re-layout       (C to D)", e_moves_relay),
                        ("re-layout, without moves+dispatch   (A to C)", e_relay_nomoves), ("re-layout, with moves+dispatch      (B to D)", e_relay_moves),
                        ("interaction (A-B)-(C-D), 0 = additive", inter)):
            b = boot(v)
            out[f"{name.split('(')[0].strip()}|{rl_lab}"] = b
            print(f"  log-P99 effect {name}: {b['mean']:+.2f} ({b['lo']:+.2f} to {b['hi']:+.2f})  [x{np.exp(b['mean']):.1f}]")
    (OUT / "grid2x2_v2.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 6)
    else:
        analyze()
