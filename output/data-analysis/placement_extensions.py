"""Placement-objective additions: what does a more workflow-aware placement buy? (pre-registered 1 Nov 2026,
knowledge/synthesis/workflow-aware-decision-rules.md, section "Placement-objective additions")

The frozen placement sees request origins and DIRECT edges only. Seven variants add what it leaves out, each a default-off option
of dfps/controllers.py queue_aware_placement (V0 = all off = the current controller, bit for bit):
  V1 size_aware   seconds per hop from each function's own state sizes          (o3s churn: size_aware)
  V2 path2        two-hop partners a -> b -> c, gamma 0.5                         (churn pstruct: path2)
  V3 join         parents of one task pull on each other, gamma 0.5               (churn pstruct: join)
  V4 fork         children of one task pull on each other, gamma 0.5              (churn pstruct: fork)
  V5 cp           direct edges weighted by 1 - slack/CP, floor 0.25               (churn pstruct: cp)
  V6 queue        the existing waiting term on                                    (churn queue_term)
  V7 all          V1 + V2 + V3 + V4 + V5
Two testbeds, results in results/placement_ext/:
  T1  the 18 development cases, config D of grid2x2_v2.py (FROZEN2 + lam 0.5 + criticality dispatch). V0 reference = the existing
      results/grid2x2_v2/*.D.json; placebos P1/P2 (move period +-1 ms) are run here.
  T2  the DAG Topology Suite (dag_suite.py), config `base` of dag_suite_run.py. V0, P1, P2 references = the existing
      results/dag_suite/{arch}_{base,P1,P2}_s*.json. V3, V4, V5 are identical to V0 on the chain by construction (no joins, no
      forks, zero slack) and are not run there.

  python placement_extensions.py check            re-run V0 on 3 cases and compare with the stored results (must be identical)
  python placement_extensions.py run [workers]    all missing runs, most expensive first, resumable
  python placement_extensions.py report           the pre-registered reading (see the decision-rules page)
"""
import json
import pickle
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))

RES = ROOT / "results" / "placement_ext"
T1_REF = ROOT / "results" / "grid2x2_v2"
T2_REF = HERE / "results" / "dag_suite"
FAMS, RHOS, SEEDS = ("F1", "F2"), (0.5, 0.7, 0.85), (1, 2, 3)
ARCHS = ("chain", "diamond", "grid", "composite", "heavy")
BURN_IN = 120.0
ALL = {"path2": 0.5, "join": 0.5, "fork": 0.5, "cp": 0.25}
VARIANTS = {
    "V1": {"size_aware": True},
    "V2": {"pstruct": {"path2": 0.5}},
    "V3": {"pstruct": {"join": 0.5}},
    "V4": {"pstruct": {"fork": 0.5}},
    "V5": {"pstruct": {"cp": 0.25}},
    "V6": {"queue_term": True},
    "V7": {"pstruct": dict(ALL), "size_aware": True},
}
EXTRA = {"W05": {"wait_w": 0.5}, "T05": {"tail_z": 0.5}, "T10": {"tail_z": 1.0}}                # move-rule variants run by wait_weight.py (not part of the placement experiment's matrix)
ABS_PERIOD = {"R1": 1.0, "R05": 0.5}           # move-clock rungs of move_gap_probe.py (absolute period in seconds)
PLACEBO = {"P1": 0.001, "P2": -0.001}           # added to the move period: no systematic effect, the trajectory diverges
CHAIN_SAME = ("V3", "V4", "V5")                 # identical to V0 on the chain by construction
LABEL = {"V1": "own state size", "V2": "two-hop chains", "V3": "join cohesion", "V4": "fork cohesion", "V5": "critical path",
         "V6": "waiting term", "V7": "all of V1-V5"}


# ------------------------------------------------------------------------------------------------------------------ runs
def _t1(tg, name, seed, family, out):
    import yaml
    import d3s_headroom as d
    from frozen2 import FROZEN2, MOVE_PERIOD_S
    from dfps.dispatch_priority import QueuePriority
    from dfps.o3s import O3SimAdjuster
    from dfps.sim import Sim
    from dfps.variants import make_adjuster, sim_kwargs
    ASSUME = yaml.safe_load((ROOT / "config" / "assumptions.yaml").read_text(encoding="utf-8"))
    sc = pickle.load(open(d.D1 / f"{tg}.pkl", "rb"))
    P = pickle.load(open(d.D1 / f"{tg}.prep.pkl", "rb"))
    kw = sim_kwargs("B_STAR", ASSUME)
    kw.update(warmup=d.WARMUP, duration=d.DURATION, retry_min_interval=1.0, retry_max_attempts=10)
    kw["queue_priority"] = QueuePriority("full", aging=2.0)
    churn = dict(FROZEN2, lam=0.5)                                       # "ours" of grid2x2_v2.py, cell D
    churn.update(VARIANTS.get(name, EXTRA.get(name, {})))
    period = ABS_PERIOD.get(name, MOVE_PERIOD_S[family] + PLACEBO.get(name, 0.0))
    t0 = time.time()
    adj = O3SimAdjuster(make_adjuster("B_STAR", ASSUME, seed=seed + 300), period, epoch=60.0, horizon=30.0, K=8,
                        seed=seed + 800, warmup=d.WARMUP, blind=True, cand_mode="nosim", churn=churn)
    kw["interval"] = adj.next_interval
    sim = Sim(sc, P["X0"].copy(), adjuster=adj, seed=seed + 400, **kw)
    r = sim.run()
    sim.check_invariants()
    r["wall_s"] = time.time() - t0
    out.write_text(json.dumps(dict(testbed="T1", family=sc.meta["family"], rho=sc.meta["rho"], seed=seed, name=name, period=period,
                                   result=r, overrides=getattr(sim, "n_priority_overrides", 0))))


def _t2(arch, name, seed, out):
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
    churn = dict(FROZEN2, lam=0.5)
    churn.update(VARIANTS.get(name, {}))
    adj = O3SimAdjuster(make_adjuster("B_STAR", m.ASSUME, seed=seed + 300), m.MOVE_PERIOD_F3 + PLACEBO.get(name, 0.0), epoch=60.0,
                        horizon=120.0, K=5, seed=seed + 800, warmup=d.WARMUP, blind=True, cand_mode="nosim", churn=churn,
                        sizing_cache={})
    kw["interval"] = adj.next_interval
    sim = Sim(sc, X0.copy(), adjuster=adj, seed=seed + 400, **kw)
    res = sim.run()
    sim.check_invariants()
    reqs = [[round(r[2], 3), r[1], round(r[3] - r[2], 3)] for r in sim.trace["reqs"]]
    out.write_text(json.dumps(dict(testbed="T2", arch=arch, config=name, seed=seed, p99_makespan=res["p99_makespan"],
                                   n_moved=res["n_moved"], cold_starts=res["cold_starts"], mb_relocated=res.get("mb_relocated"),
                                   event_hash=res.get("event_hash"), reqs=reqs, wall_s=time.time() - t0)))


def job(args):
    testbed, key, name, seed, extra, folder = args
    out = RES / folder / (f"{key}.{name}.json" if testbed == "T1" else f"{key}_{name}_s{seed}.json")
    if out.exists():
        return str(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        import numpy as _np
        assert _np.__version__.startswith("1."), "run with the Anaconda interpreter (numpy 1.26)"
        _t1(key, name, seed, extra, out) if testbed == "T1" else _t2(key, name, seed, out)
    except Exception:
        import traceback
        out.with_suffix(".err").write_text(traceback.format_exc())
        return str(out) + " FAILED"
    return str(out)


def tag(f, r, s):
    return f"{f}_r{r}_s{s}"


def jobs():
    out = []
    for f in FAMS:
        for r in RHOS:
            for s in SEEDS:
                for n in list(VARIANTS) + list(PLACEBO):
                    out.append(("T1", tag(f, r, s), n, s, f, "T1"))
    for a in ARCHS:
        for s in SEEDS:
            for n in VARIANTS:
                if a == "chain" and n in CHAIN_SAME:
                    continue
                out.append(("T2", a, n, s, None, "T2"))
    est = {"T1": 330.0, "chain": 220.0, "diamond": 510.0, "grid": 710.0, "composite": 470.0, "heavy": 540.0}
    return sorted(out, key=lambda j: -est[j[0] if j[0] == "T1" else j[1]])


def run(workers):
    todo = [j for j in jobs() if not (RES / j[5] / (f"{j[1]}.{j[2]}.json" if j[0] == "T1" else f"{j[1]}_{j[2]}_s{j[3]}.json")).exists()]
    print(f"{len(todo)} runs to do, {workers} workers", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        for r in ex.map(job, todo):
            print("done", r, flush=True)


# ------------------------------------------------------------------------------------------------------------- identity check
def check():
    """V0 must reproduce the stored results exactly, otherwise the references are not valid and must be re-run."""
    t1 = sorted(T1_REF.glob("*.D.json"), key=lambda p: json.loads(p.read_text())["result"]["wall_s"])[0]
    x = json.loads(t1.read_text())
    tg1 = t1.name[:-len(".D.json")]
    cases = [("T1", tg1, "V0", x["seed"], x["family"], "check"), ("T2", "chain", "V0", 1, None, "check"),
             ("T2", "diamond", "V0", 1, None, "check")]
    with ProcessPoolExecutor(3) as ex:
        outs = list(ex.map(job, cases))
    ok = True
    ref = json.loads(t1.read_text())["result"]
    new = json.loads((RES / "check" / f"{cases[0][1]}.V0.json").read_text())["result"]
    same = new["event_hash"] == ref["event_hash"] and new["p99_makespan"] == ref["p99_makespan"]
    print(f"T1 {cases[0][1]}: p99 {new['p99_makespan']:.6f} vs stored {ref['p99_makespan']:.6f}, hash {new['event_hash']} vs {ref['event_hash']}: "
          f"{'IDENTICAL' if same else 'DIFFERENT'}")
    ok &= same
    for a in ("chain", "diamond"):
        new = json.loads((RES / "check" / f"{a}_V0_s1.json").read_text())
        ref = json.loads((T2_REF / f"{a}_base_s1.json").read_text())
        same = new["p99_makespan"] == ref["p99_makespan"] and new["n_moved"] == ref["n_moved"] and new["cold_starts"] == ref["cold_starts"]
        print(f"T2 {a} s1: p99 {new['p99_makespan']:.6f} vs stored {ref['p99_makespan']:.6f}, moved {new['n_moved']} vs {ref['n_moved']}: "
              f"{'IDENTICAL' if same else 'DIFFERENT'}")
        ok &= same
    print("ALL IDENTICAL: references valid" if ok else "NOT IDENTICAL: re-run the references before any variant")
    return outs


# ----------------------------------------------------------------------------------------------------------------- report
def boot_ci(x, n=10000, seed=0):
    x = np.asarray(x, dtype=float)
    m = np.random.default_rng(seed).choice(x, (n, len(x))).mean(axis=1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def t1_load():
    ref, runs = {}, {}
    for f in T1_REF.glob("*.D.json"):
        x = json.loads(f.read_text())
        if x["family"] in FAMS and x["seed"] in SEEDS:
            ref[(x["family"], x["rho"], x["seed"])] = x["result"]
    for f in (RES / "T1").glob("*.json"):
        x = json.loads(f.read_text())
        runs.setdefault(x["name"], {})[(x["family"], x["rho"], x["seed"])] = x["result"]
    return ref, runs


def t2_p99(rec):
    return float(np.percentile([r[2] for r in rec["reqs"] if r[0] >= BURN_IN], 99))


def t2_load():
    ref, runs = {}, {}
    for f in T2_REF.glob("*.json"):
        a, rest = f.stem.split("_", 1)
        c, s = rest.rsplit("_s", 1)
        if a in ARCHS and c in ("base", "P1", "P2"):
            ref.setdefault((a, int(s)), {})["V0" if c == "base" else c] = t2_p99(json.loads(f.read_text()))
    for f in (RES / "T2").glob("*.json"):
        x = json.loads(f.read_text())
        runs.setdefault((x["arch"], x["config"]), {})[x["seed"]] = (t2_p99(x), x)
    return ref, runs


def report():
    ref, runs = t1_load()
    keys = sorted(ref)
    nulls = {k: [ref[k]["p99_makespan"]] + [runs[p][k]["p99_makespan"] for p in PLACEBO if p in runs and k in runs[p]] for k in keys}
    full = [k for k in keys if len(nulls[k]) == 3]
    print(f"=== T1: 18 development cases ({len(full)} with both placebos). Effect = ln P99 - ln(geometric mean of the three null runs); "
          f"negative = better ===")
    if full:
        dev = [np.log(v) - np.mean(np.log(nulls[k])) for k in full for v in nulls[k]]
        print(f"per-run noise sigma (pooled null deviations): {np.std(dev, ddof=1) * 100:.1f}% ; single-baseline deviation max {max(abs(d) for d in dev) * 100:.1f}%")
    print(f"{'variant':26s} {'n':>3s} {'P99 vs null':>14s} {'95% CI':>16s} {'wins':>6s} {'P95':>7s} {'mean':>7s} {'cold':>7s} {'mv/req':>12s}  verdict")
    for n in VARIANTS:
        if n not in runs:
            continue
        ks = [k for k in full if k in runs[n]]
        if not ks:
            continue
        e = [np.log(runs[n][k]["p99_makespan"]) - np.mean(np.log(nulls[k])) for k in ks]
        lo, hi = boot_ci(e)
        g = lambda key: np.exp(np.mean([np.log(runs[n][k][key]) - np.log(ref[k][key]) for k in ks])) - 1  # noqa: E731
        cold = np.mean([runs[n][k]["cold_starts"] / ref[k]["cold_starts"] for k in ks]) - 1
        mv = np.mean([runs[n][k]["n_moved"] / max(1, runs[n][k]["n_completed"]) for k in ks])
        mv0 = np.mean([ref[k]["n_moved"] / max(1, ref[k]["n_completed"]) for k in ks])
        r50 = [np.exp(np.log(runs[n][k]["p99_makespan"]) - np.mean(np.log(nulls[k]))) - 1 for k in ks if k[1] == 0.5]
        gm = np.exp(np.mean(e)) - 1
        pays = gm <= -0.03 and hi < 0 and cold <= 0.20 and (not r50 or np.mean(r50) <= 0.01)
        p95 = np.exp(np.mean([np.log(runs[n][k]["p95_makespan"]) - np.log(ref[k]["p95_makespan"]) for k in ks])) - 1
        print(f"{n + ' ' + LABEL[n]:26s} {len(ks):3d} {gm * 100:+13.1f}% [{(np.exp(lo) - 1) * 100:+5.1f},{(np.exp(hi) - 1) * 100:+5.1f}]% "
              f"{sum(x < 0 for x in e):3d}/{len(ks):<2d} {p95 * 100:+6.1f}% {g('avg_makespan') * 100:+6.1f}% {cold * 100:+6.1f}% "
              f"{mv:5.2f} vs {mv0:4.2f}  {'PAYS' if pays else '-'}")
    print("\n=== T2: DAG Topology Suite (3 seeds per archetype; P99 of requests after the 120 s burn-in) ===")
    rf, rr = t2_load()
    print(f"{'archetype':10s} {'null spread (max |dev|)':>24s}   " + "  ".join(f"{n:>8s}" for n in VARIANTS) + "   per-seed effects are in the json; * = pays structurally")
    TARGET = {"V1": ("heavy",), "V2": ("chain", "composite"), "V3": ("diamond", "grid", "composite"), "V4": ("diamond", "grid", "composite"),
              "V5": ("composite", "diamond", "grid"), "V6": (), "V7": ARCHS}
    for a in ARCHS:
        seeds = [s for s in SEEDS if (a, s) in rf and len(rf[(a, s)]) == 3]
        if not seeds:
            continue
        nul = {s: np.mean(np.log(list(rf[(a, s)].values()))) for s in seeds}
        spread = max(abs(np.log(v) - nul[s]) for s in seeds for v in rf[(a, s)].values())
        cells = []
        for n in VARIANTS:
            if a == "chain" and n in CHAIN_SAME:
                cells.append(f"{'= V0':>8s}")
                continue
            got = rr.get((a, n), {})
            es = [np.log(got[s][0]) - nul[s] for s in seeds if s in got]
            if len(es) < len(seeds):
                cells.append(f"{'..':>8s}")
                continue
            m = float(np.mean(es))
            star = "*" if (a in TARGET[n] and m <= -0.03 and all(x < 0 for x in es) and abs(m) > spread) else " "
            cells.append(f"{(np.exp(m) - 1) * 100:+7.1f}%{star}")
        print(f"{a:10s} {(np.exp(spread) - 1) * 100:23.1f}%   " + "  ".join(cells))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "check":
        check()
    elif cmd == "run":
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 10)
    else:
        report()
