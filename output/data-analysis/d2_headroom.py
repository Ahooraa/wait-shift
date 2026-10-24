"""Task 12 (pre-registered): D2 headroom, i.e. overload admission + critical-path dispatch.

  python -I output/data-analysis/d2_headroom.py run [--workers N]
  python -I output/data-analysis/d2_headroom.py analyze

Scenarios (dfps.traces.build_overload_scenario): F1 and F2 overload windows chosen by G1's rule (top-200 aggregate provisioned
at median rho 0.7; window centred on a minute above capacity), F3 synthetic bursts to rho 1.2 and 1.5 for 2-10 min on a rho
0.7 base. 10 paired instances per scenario type (seeds 1-10); F3 pools both burst levels (20 instances).
Window 15 min + 60 s warm-up; primary metric SLO-goodput (workflows within 3 x unloaded critical path, per second).
Controllers (same scenario, initial placement, seeds):
  B_STAR  admit-all, T* per family (Task 10), total-weight matching (the paper)
  HEUR    B* + queue-threshold admission (admit iff requests in system <= 1.0 x total container slots; theta fixed, not tuned)
  O2      offline admission oracle, operationalised as iterative hindsight shedding with critical-path dispatch: pass 0 admits
          all; pass k+1 additionally rejects every in-window request that missed its SLO or did not finish in pass k (request
          ids are stable across re-runs); at most 4 passes; the best SLO-goodput over the passes is O2's value. It knows the
          future arrivals and the realised durations only through the previous pass (durations are re-drawn when the service
          order changes), so it is an approximate oracle (logged).
Decision (plan): h = (G_O2 - G_B*) / G_B*; GO if CI lower bound >= 0.25 in >= 2 of 3 families, KILL if < 0.10 in all,
else MAYBE; downgrade GO -> MAYBE if the heuristic captures >= 70% of the headroom in >= 2 families.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from experiments.run import ASSUME, initial_placements  # noqa: E402
from dfps.controllers import QueueThresholdAdmission, RejectSet  # noqa: E402
from dfps.sim import Sim  # noqa: E402
from dfps.traces import bottleneck_utilisation, build_overload_scenario, load_counts  # noqa: E402
from dfps.variants import make_adjuster, sim_kwargs  # noqa: E402

RUNS = ROOT / "results" / "d2_headroom"
OUT = ROOT / "output" / "data-analysis" / "results"
GROUPS = (("F1", None), ("F2", None), ("F3", 1.2), ("F3", 1.5))
SEEDS = tuple(range(1, 11))
DURATION, WARMUP, MAX_PASSES = 900.0, 60.0, 4


def gtag(fam, b, seed):
    return f"{fam}{'' if b is None else '_b' + str(b)}_s{seed}"


def job(args):
    try:
        return _job(args)
    except Exception:
        import traceback
        Path(args[1]).with_suffix(".err").write_text(traceback.format_exc())
        return args[1] + " FAILED"


def _sim(sc, X, seed, period, **extra):
    kw = sim_kwargs("B_STAR", ASSUME)
    kw.update(warmup=WARMUP, duration=DURATION, retry_min_interval=1.0, retry_max_attempts=10, interval=float(period))
    kw.update(extra)
    t = time.time()
    sim = Sim(sc, X, adjuster=make_adjuster("B_STAR", ASSUME, seed=seed + 300), seed=seed + 400, **kw)
    r = sim.run()
    sim.check_invariants()
    r["wall_s"] = time.time() - t
    return sim, r


def _job(args):
    sc_path, out_path, seed, period = args
    if Path(out_path).exists():
        return out_path
    import pickle
    sc = pickle.load(open(sc_path, "rb"))
    _, X, _ = initial_placements(sc, seed, ASSUME["A06_generations"], "abs")
    out = dict(meta={k: v for k, v in sc.meta.items() if k not in ("per_app_rate", "rate_series")}, seed=seed, period=period,
               bottleneck_x0=bottleneck_utilisation(sc, X))
    _, out["B_STAR"] = _sim(sc, X, seed, period)
    _, out["HEUR"] = _sim(sc, X, seed, period, admission=QueueThresholdAdmission(1.0))
    rejected, passes = set(), []
    for k in range(MAX_PASSES):
        sim, r = _sim(sc, X, seed, period, admission=RejectSet(rejected), match_objective="critical", record_requests=True)
        r["n_reject_set"] = len(rejected)
        passes.append(r)
        missed = {rid for rid, _, _, ok in sim.request_log if not ok} | set(sim.win.keys())
        new = missed - rejected
        if not new:
            break
        rejected |= new
    best = max(range(len(passes)), key=lambda i: passes[i]["slo_goodput"])
    out["O2"] = dict(passes[best], best_pass=best, n_passes=len(passes))
    out["O2_passes_goodput"] = [p["slo_goodput"] for p in passes]
    Path(out_path).write_text(json.dumps(out))
    return out_path


THETAS, REPAIR_PASSES, READMIT_LOAD = (0.5, 1.0, 2.0), 3, 0.8


def job_o2h(args):
    try:
        return _job_o2h(args)
    except Exception:
        import traceback
        Path(args[1]).with_suffix(".o2h.err").write_text(traceback.format_exc())
        return args[1] + " FAILED"


def _job_o2h(args):
    """O2H (deviation 2026-10-16, replaces O2 after it was shown to shed monotonically and never re-admit):
    stage A: hindsight-tuned queue threshold theta in THETAS, critical-path dispatch; best SLO-goodput wins.
    stage B: REPAIR_PASSES passes from the best pass: reject = (previous rejected U admitted-but-missed)
             minus re-admit (previously rejected requests that arrived while the system load was < READMIT_LOAD x slots).
    O2H = best over all passes. Uses the future only through previous passes of the same scenario and seed."""
    sc_path, out_path, seed, period = args
    o_path = Path(out_path).with_suffix(".o2h.json")
    if o_path.exists():
        return str(o_path)
    import pickle
    from dfps.controllers import RecordingAdmission
    sc = pickle.load(open(sc_path, "rb"))
    _, X, _ = initial_placements(sc, seed, ASSUME["A06_generations"], "abs")
    passes = []

    def one(adm, label):
        rec = RecordingAdmission(adm)
        sim, r = _sim(sc, X, seed, period, admission=rec, match_objective="critical", record_requests=True)
        r["label"] = label
        rej = {i for i, _, _, ok in rec.log if not ok}
        miss = {rid for rid, _, _, ok in sim.request_log if not ok} | set(sim.win.keys())
        load = {i: l for i, _, l, _ in rec.log}
        passes.append(r)
        return r, rej, miss, load

    stage = [one(QueueThresholdAdmission(th), f"theta={th}") for th in THETAS]
    r, rej, miss, load = max(stage, key=lambda s: s[0]["slo_goodput"])
    for k in range(REPAIR_PASSES):
        readmit = {i for i in rej if load.get(i, 9.9) < READMIT_LOAD}
        new_rej = (rej | miss) - readmit
        r2, rej2, miss2, load2 = one(RejectSet(new_rej), f"repair{k + 1}")
        if r2["slo_goodput"] > r["slo_goodput"]:
            r, rej, miss, load = r2, rej2 | new_rej, miss2, load2
        else:
            break
    best = max(range(len(passes)), key=lambda i: passes[i]["slo_goodput"])
    out = dict(O2H=dict(passes[best], best_pass=best, n_passes=len(passes)),
               passes=[dict(label=p["label"], slo_goodput=p["slo_goodput"], n_rejected=p["n_rejected"], p99=p["p99_makespan"]) for p in passes])
    o_path.write_text(json.dumps(out))
    return str(o_path)


def run_o2h(a):
    T = json.loads((OUT / "g2_tstar.json").read_text())
    T = {f: float(T["families"][f]["T_star"]) for f in ("F1", "F2", "F3")}
    jobs = [(str(RUNS / f"{gtag(fam, b, s)}.pkl"), str(RUNS / f"{gtag(fam, b, s)}.json"), s, T[fam]) for fam, b in GROUPS for s in SEEDS]
    with ProcessPoolExecutor(a.workers) as ex:
        for d in ex.map(job_o2h, jobs):
            print("done", d, flush=True)


def run(a):
    import pickle
    RUNS.mkdir(parents=True, exist_ok=True)
    T = json.loads((OUT / "g2_tstar.json").read_text())
    T = {f: float(T["families"][f]["T_star"]) for f in ("F1", "F2", "F3")}
    dags, jobs = None, []
    for fam, b in GROUPS:
        counts = None if fam == "F3" else load_counts(fam, "dev")
        for seed in SEEDS:
            tg = gtag(fam, b, seed)
            p = RUNS / f"{tg}.pkl"
            if not p.exists():
                if dags is None:
                    dags = json.load(open(ROOT / "data" / "alibaba_dags_lt60s.json"))
                sc = build_overload_scenario(fam, seed, b, "dev", DURATION, 60.0, ne=80, n_workflows=15, alibaba_dags=dags,
                                             pool_size=ASSUME["A17_function_pool_size"], counts=counts)
                pickle.dump(sc, open(p, "wb"))
            jobs.append((str(p), str(RUNS / f"{tg}.json"), seed, T[fam]))
    del dags
    with ProcessPoolExecutor(a.workers) as ex:
        for d in ex.map(job, jobs):
            print("done", d, flush=True)


def boot_ci(x, n=10_000, seed=0):
    x = np.asarray([v for v in x if np.isfinite(v)], dtype=float)
    if len(x) < 2:
        return dict(mean=float(x.mean()) if len(x) else float("nan"), lo=float("nan"), hi=float("nan"), n=int(len(x)))
    m = np.random.default_rng(seed).choice(x, (n, len(x)), replace=True).mean(axis=1)
    return dict(mean=float(x.mean()), lo=float(np.percentile(m, 2.5)), hi=float(np.percentile(m, 97.5)), n=int(len(x)))


def analyze(a):
    rows = {}
    for f in RUNS.glob("*.json"):
        if f.name.endswith(".o2h.json"):
            continue
        d = json.loads(f.read_text())
        o = f.with_suffix(".o2h.json")
        if o.exists():
            d["O2H"] = json.loads(o.read_text())["O2H"]
        rows.setdefault(d["meta"]["family"], []).append(d)
    out = dict(metric="slo_goodput", families={})
    out["o2h"] = {}
    for fam, ds in sorted(rows.items()):
        ds = [d for d in ds if "O2H" in d]
        if not ds:
            continue
        g = lambda d, c: d[c]["slo_goodput"]
        env = lambda d: max(g(d, "HEUR"), g(d, "O2"), g(d, "O2H"))
        out["o2h"][fam] = dict(
            n=len(ds),
            h_envelope=boot_ci([(env(d) - g(d, "B_STAR")) / g(d, "B_STAR") for d in ds if g(d, "B_STAR") > 0]),
            beyond_heuristic=boot_ci([(env(d) - g(d, "HEUR")) / g(d, "HEUR") for d in ds if g(d, "HEUR") > 0]),
            heuristic_saturation_envelope=boot_ci([(g(d, "HEUR") - g(d, "B_STAR")) / (env(d) - g(d, "B_STAR"))
                                                   for d in ds if env(d) - g(d, "B_STAR") > 0]),
            goodput_mean={c: float(np.mean([g(d, c) for d in ds])) for c in ("B_STAR", "HEUR", "O2", "O2H")},
            p99_admitted_mean={c: float(np.mean([d[c]["p99_makespan"] for d in ds])) for c in ("B_STAR", "HEUR", "O2", "O2H")})
    for fam, ds in sorted(rows.items()):
        h = [(d["O2"]["slo_goodput"] - d["B_STAR"]["slo_goodput"]) / d["B_STAR"]["slo_goodput"] for d in ds if d["B_STAR"]["slo_goodput"] > 0]
        sat = [(d["HEUR"]["slo_goodput"] - d["B_STAR"]["slo_goodput"]) / (d["O2"]["slo_goodput"] - d["B_STAR"]["slo_goodput"])
               for d in ds if d["O2"]["slo_goodput"] - d["B_STAR"]["slo_goodput"] > 0]
        out["families"][fam] = dict(
            h=boot_ci(h), heuristic_saturation=boot_ci(sat), n=len(ds),
            goodput_mean={c: float(np.mean([d[c]["slo_goodput"] for d in ds])) for c in ("B_STAR", "HEUR", "O2")},
            p99_admitted_mean={c: float(np.mean([d[c]["p99_makespan"] for d in ds])) for c in ("B_STAR", "HEUR", "O2")},
            rejected_mean={c: float(np.mean([d[c]["n_rejected"] for d in ds])) for c in ("HEUR", "O2")},
            o2_best_pass_mean=float(np.mean([d["O2"]["best_pass"] for d in ds])),
            offered_util_max_mean=float(np.mean([d["meta"]["offered_util_max"] for d in ds])),
            bottleneck_x0_mean=float(np.mean([d["bottleneck_x0"]["max"] for d in ds])))
    lo = {f: v["h"]["lo"] for f, v in out["families"].items()}
    n_go = sum(1 for v in lo.values() if np.isfinite(v) and v >= 0.25)
    kill = bool(lo) and all(np.isfinite(v) and v < 0.10 for v in lo.values())
    dec = "GO" if n_go >= 2 else ("KILL" if kill else "MAYBE")
    sats = [v["heuristic_saturation"]["mean"] for v in out["families"].values()]
    if dec == "GO" and sum(1 for x in sats if np.isfinite(x) and x >= 0.70) >= 2:
        dec = "MAYBE (downgraded: heuristic captures >= 70% of the headroom in >= 2 families)"
    out["decision_D2"] = dec
    if len(out["o2h"]) == 3:
        lo_e = {f: v["h_envelope"]["lo"] for f, v in out["o2h"].items()}
        d_e = "GO" if sum(v >= 0.25 for v in lo_e.values()) >= 2 else ("KILL" if all(v < 0.10 for v in lo_e.values()) else "MAYBE")
        sat_e = [v["heuristic_saturation_envelope"]["mean"] for v in out["o2h"].values()]
        if d_e == "GO" and sum(1 for x in sat_e if np.isfinite(x) and x >= 0.70) >= 2:
            d_e = "MAYBE (downgraded: heuristic captures >= 70% of the envelope headroom in >= 2 families)"
        out["decision_D2_envelope_o2h"] = d_e
        print("D2 decision (envelope with O2H, deviation 2026-10-16):", d_e)
    for f, v in out["o2h"].items():
        print(f, "O2H", {k: (round(x["mean"], 3), round(x["lo"], 3), round(x["hi"], 3)) for k, x in v.items() if isinstance(x, dict) and "lo" in x},
              "| goodput", {k: round(x, 2) for k, x in v["goodput_mean"].items()})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "d2_headroom.json").write_text(json.dumps(out, indent=2))
    print("D2 decision:", dec)
    for f, v in out["families"].items():
        print(f, "h", {k: round(x, 3) if isinstance(x, float) else x for k, x in v["h"].items()}, "| sat", round(v["heuristic_saturation"]["mean"], 3),
              "| goodput", {k: round(x, 2) for k, x in v["goodput_mean"].items()}, "| p99 admitted", {k: round(x) for k, x in v["p99_admitted_mean"].items()})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "run_o2h", "analyze"])
    ap.add_argument("--workers", type=int, default=10)
    a = ap.parse_args()
    dict(run=run, run_o2h=run_o2h, analyze=analyze)[a.cmd](a)
