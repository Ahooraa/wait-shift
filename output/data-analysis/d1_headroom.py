"""Task 11 (pre-registered): D1 headroom, i.e. when to reconfigure and the value of forecasts.

  python -I output/data-analysis/d1_headroom.py prep    [--workers N]   # scenarios, initial placement X0, O1 schedule, S_mean
  python -I output/data-analysis/d1_headroom.py run     [--workers N]   # B*, P_true, O1, HEUR, S_MEAN (needs g2_tstar.json)
  python -I output/data-analysis/d1_headroom.py run_pfc [--workers N]   # P_fc(sigma), only if H1b condition (a) can pass
  python -I output/data-analysis/d1_headroom.py analyze

Grid (plan): families F1, F2, F3 (dev span) x rho in {0.5, 0.7, 0.85} x 10 paired instances (seeds 1-10).
Window: 15 simulated minutes after a 60 s warm-up (runtime rule of Task 8: 30-min windows were the fallback; 15-min keeps
the 450 runs inside the 12 h timebox; same window as the T* tuning). Primary metric: P99 makespan.
Controllers and their operationalisation: see dfps/oracles.py. Pairing: same scenario, arrivals, simulator seed and
initial placement for every controller; B*, P_true, P_fc and HEUR use the same annealing seed.
Decision (plan): GO if the 95% bootstrap CI lower bound of h >= 0.25 in >= 2 of 3 families; KILL if < 0.10 in all 3;
otherwise MAYBE. The family-level CI pools the 3 load levels (30 paired instances); per-cell CIs are reported too.
"""
from __future__ import annotations

import argparse
import json
import pickle
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from experiments.run import ASSUME, initial_placements  # noqa: E402
from dfps.controllers import RateChangeTrigger  # noqa: E402
from dfps.oracles import ForecastAdjuster, ScheduleAdjuster, ScheduleWithAnnealing, o1_schedule, s_mean_placement  # noqa: E402
from dfps.sim import Sim  # noqa: E402
from dfps.traces import bottleneck_utilisation, build_trace_scenario, load_counts  # noqa: E402
from dfps.variants import make_adjuster, sim_kwargs  # noqa: E402

RUNS = ROOT / "results" / "d1_headroom"
OUT = ROOT / "output" / "data-analysis" / "results"
FAMILIES, RHOS, SEEDS = ("F1", "F2", "F3"), (0.5, 0.7, 0.85), tuple(range(1, 11))
DURATION, WARMUP, SLOT = 900.0, 60.0, 10.0
BASE = ("B_STAR", "P_TRUE", "O1", "HEUR", "S_MEAN", "O1_BSTAR")   # S_MEAN and O1_BSTAR are diagnostics
SIGMAS = (0.25, 0.5, 1.0)


def tag(fam, rho, seed):
    return f"{fam}_r{rho}_s{seed}"


def _safe(fn, args, out_path):
    try:
        return fn(args)
    except Exception:
        import traceback
        Path(out_path).with_suffix(".err").write_text(traceback.format_exc())
        return str(out_path) + " FAILED"


def prep_job(args):
    return _safe(_prep, args, args[1])


def _prep(args):
    sc_path, prep_path, seed = args
    if Path(prep_path).exists():
        return prep_path
    sc = pickle.load(open(sc_path, "rb"))
    t = time.time()
    _, X0, _ = initial_placements(sc, seed, ASSUME["A06_generations"], "abs")
    sw, info = o1_schedule(sc, X0, DURATION, SLOT)
    Xs = s_mean_placement(sc, DURATION)
    info.update(prep_wall_s=time.time() - t, bottleneck_x0=bottleneck_utilisation(sc, X0),
                bottleneck_s_mean=bottleneck_utilisation(sc, Xs))
    pickle.dump(dict(X0=X0, switches=sw, o1_info=info, X_s_mean=Xs), open(prep_path, "wb"))
    return prep_path


def run_job(args):
    return _safe(_run, args, args[2])


def _run(args):
    sc_path, prep_path, out_path, seed, ctrl, period = args
    if Path(out_path).exists():
        return out_path
    sc = pickle.load(open(sc_path, "rb"))
    P = pickle.load(open(prep_path, "rb"))
    kw = sim_kwargs("B_STAR", ASSUME)
    kw.update(warmup=WARMUP, duration=DURATION, retry_min_interval=1.0, retry_max_attempts=10)
    X, adj, extra = P["X0"], None, {}
    sa = lambda: make_adjuster("B_STAR", ASSUME, seed=seed + 300)  # noqa: E731
    if ctrl == "B_STAR":
        adj, kw["interval"] = sa(), float(period)
    elif ctrl == "P_TRUE" or ctrl.startswith("P_FC"):
        sigma = 0.0 if ctrl == "P_TRUE" else float(ctrl.split("_")[-1])
        adj = ForecastAdjuster(sa(), period, sigma, seed=seed + 900)
        kw["interval"], kw["lam_source"] = float(period), adj.lam_source
    elif ctrl == "O1":
        sw = list(P["switches"])
        if sw and sw[0][0] <= 0.0:                                   # a switch at t = 0 is the initial placement
            X, sw = sw[0][1], sw[1:]
        adj, kw["interval"] = ScheduleAdjuster(sw, SLOT), SLOT
        extra["o1_switches"] = len(P["switches"])
    elif ctrl == "O1_BSTAR":
        sw = list(P["switches"])
        if sw and sw[0][0] <= 0.0:
            X, sw = sw[0][1], sw[1:]
        adj = ScheduleWithAnnealing(sw, sa(), period, SLOT)
        kw["interval"] = adj.next_interval
    elif ctrl == "HEUR":
        adj, kw["interval"] = RateChangeTrigger(sa(), threshold=0.3, check_s=1.0), 1.0
    elif ctrl == "S_MEAN":
        X = P["X_s_mean"]
    else:
        raise ValueError(ctrl)
    t = time.time()
    sim = Sim(sc, X, adjuster=adj, seed=seed + 400, **kw)
    r = sim.run()
    sim.check_invariants()
    r["wall_s"] = time.time() - t
    if ctrl == "HEUR":
        extra["heur_triggers"] = adj.n_triggered
    Path(out_path).write_text(json.dumps(dict(family=sc.meta["family"], rho=sc.meta["rho"], seed=seed, ctrl=ctrl, period=period,
                                              result=r, extra=extra, o1_info=P["o1_info"])))
    return out_path


def build_scenarios():
    RUNS.mkdir(parents=True, exist_ok=True)
    dags = None
    for fam in FAMILIES:
        counts = None if fam == "F3" else load_counts(fam, "dev")
        for rho in RHOS:
            for seed in SEEDS:
                p = RUNS / f"{tag(fam, rho, seed)}.pkl"
                if p.exists():
                    continue
                if dags is None:
                    dags = json.load(open(ROOT / "data" / "alibaba_dags_lt60s.json"))
                sc = build_trace_scenario(fam, rho, seed, "dev", DURATION, 60.0, ne=80, n_workflows=15, alibaba_dags=dags,
                                          pool_size=ASSUME["A17_function_pool_size"], counts=counts)
                pickle.dump(sc, open(p, "wb"))
                print("built", p.name, sc.meta["n_arrivals"], flush=True)


def prep(a):
    build_scenarios()
    jobs = [(str(RUNS / f"{tag(f, r, s)}.pkl"), str(RUNS / f"{tag(f, r, s)}.prep.pkl"), s)
            for f in FAMILIES for r in RHOS for s in SEEDS]
    with ProcessPoolExecutor(a.workers) as ex:
        for d in ex.map(prep_job, jobs):
            print("prep", d, flush=True)


def tstar():
    d = json.loads((OUT / "g2_tstar.json").read_text())
    out = {}
    for fam in FAMILIES:
        v = d["families"].get(fam)
        if v is None or not v.get("complete"):
            raise SystemExit(f"T* for {fam} is missing or incomplete: run g2_tstar.py first")
        out[fam] = float(v["T_star"])
    return out


def run(a, ctrls):
    T = tstar()
    jobs = []
    for f in FAMILIES:
        for r in RHOS:
            for s in SEEDS:
                tg = tag(f, r, s)
                for c in ctrls:
                    jobs.append((str(RUNS / f"{tg}.pkl"), str(RUNS / f"{tg}.prep.pkl"), str(RUNS / f"{tg}.{c}.json"), s, c, T[f]))
    with ProcessPoolExecutor(a.workers) as ex:
        for d in ex.map(run_job, jobs):
            print("done", d, flush=True)


def boot_ci(x, n=10_000, seed=0):
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < 2:
        return dict(mean=float(x.mean()) if len(x) else float("nan"), lo=float("nan"), hi=float("nan"), n=int(len(x)))
    rng = np.random.default_rng(seed)
    m = rng.choice(x, (n, len(x)), replace=True).mean(axis=1)
    return dict(mean=float(x.mean()), lo=float(np.percentile(m, 2.5)), hi=float(np.percentile(m, 97.5)), n=int(len(x)))


def analyze(a):
    res = {}
    for f in RUNS.glob("*.json"):
        d = json.loads(f.read_text())
        res.setdefault((d["family"], d["rho"], d["seed"]), {})[d["ctrl"]] = d
    metric = "p99_makespan"
    out = dict(metric=metric, cells={}, families={}, design=dict(duration_s=DURATION, warmup_s=WARMUP, slot_s=SLOT))

    def h_values(keys, num, den, ref):
        v = []
        for k in keys:
            c = res.get(k, {})
            if all(x in c for x in (num, den, ref)):
                a_, b_, r_ = (c[x]["result"][metric] for x in (num, den, ref))
                v.append((a_ - b_) / r_)
        return v

    CLAIRVOYANT = ("O1", "O1_BSTAR", "P_TRUE")

    def env_values(keys):
        """(B* - best clairvoyant) / B*, per instance (user-approved deviation 2026-10-15: lower bound on headroom)."""
        v = []
        for k in keys:
            c = res.get(k, {})
            if "B_STAR" in c and all(x in c for x in CLAIRVOYANT):
                b = c["B_STAR"]["result"][metric]
                best = min(c[x]["result"][metric] for x in CLAIRVOYANT)
                v.append((b - best) / b)
        return v

    def env_sat_values(keys):
        v = []
        for k in keys:
            c = res.get(k, {})
            if all(x in c for x in ("B_STAR", "HEUR") + CLAIRVOYANT):
                b, h = c["B_STAR"]["result"][metric], c["HEUR"]["result"][metric]
                best = min(c[x]["result"][metric] for x in CLAIRVOYANT)
                if b - best > 0:
                    v.append((b - h) / (b - best))
        return v

    def sat_values(keys):
        v = []
        for k in keys:
            c = res.get(k, {})
            if all(x in c for x in ("B_STAR", "O1", "HEUR")):
                b, o, h = (c[x]["result"][metric] for x in ("B_STAR", "O1", "HEUR"))
                if b - o > 0:
                    v.append((b - h) / (b - o))
        return v

    def summary(keys):
        s = dict(h_total=boot_ci(h_values(keys, "B_STAR", "O1", "B_STAR")),
                 h_timing=boot_ci(h_values(keys, "P_TRUE", "O1", "P_TRUE")),
                 h_forecast=boot_ci(h_values(keys, "B_STAR", "P_TRUE", "B_STAR")),
                 h_static_s_mean=boot_ci(h_values(keys, "B_STAR", "S_MEAN", "B_STAR")),
                 o1_vs_s_mean=boot_ci(h_values(keys, "S_MEAN", "O1", "S_MEAN")),
                 h_o1_bstar=boot_ci(h_values(keys, "B_STAR", "O1_BSTAR", "B_STAR")),
                 heuristic_saturation=boot_ci(sat_values(keys)),
                 h_envelope=boot_ci(env_values(keys)), heuristic_saturation_envelope=boot_ci(env_sat_values(keys)))
        for sg in SIGMAS:
            s[f"p_fc_{sg}_vs_bstar"] = boot_ci(h_values(keys, f"P_FC_{sg}", "B_STAR", "B_STAR"))   # > 0: P_fc worse than B*
        means = {}
        for c in BASE + tuple(f"P_FC_{sg}" for sg in SIGMAS):
            v = [res[k][c]["result"][metric] for k in keys if c in res.get(k, {})]
            if v:
                means[c] = float(np.mean(v))
        s["mean_p99"] = means
        return s

    for f in FAMILIES:
        fam_keys = []
        for r in RHOS:
            keys = [(f, r, s) for s in SEEDS if (f, r, s) in res]
            fam_keys += keys
            out["cells"][f"{f}_r{r}"] = summary(keys)
        out["families"][f] = summary(fam_keys)
    lo = {f: out["families"][f]["h_total"]["lo"] for f in FAMILIES}
    n_go = sum(1 for f in FAMILIES if np.isfinite(lo[f]) and lo[f] >= 0.25)
    kill = all(np.isfinite(lo[f]) and lo[f] < 0.10 for f in FAMILIES)
    decision = "GO" if n_go >= 2 else ("KILL" if kill else "MAYBE")
    sat = [out["families"][f]["heuristic_saturation"]["mean"] for f in FAMILIES]
    if decision == "GO" and sum(1 for x in sat if np.isfinite(x) and x >= 0.70) >= 2:
        decision = "MAYBE (downgraded: heuristic captures >= 70% of the headroom in >= 2 families)"
    timing_lo = {f: out["families"][f]["h_timing"]["lo"] for f in FAMILIES}
    out["decision_D1_preregistered_O1"] = decision
    # user-approved deviation: lower-bound headroom from the best clairvoyant controller, asymmetric reading
    elo = {f: out["families"][f]["h_envelope"]["lo"] for f in FAMILIES}
    n_go_e = sum(1 for f in FAMILIES if np.isfinite(elo[f]) and elo[f] >= 0.25)
    none_e = all(np.isfinite(elo[f]) and elo[f] < 0.10 for f in FAMILIES)
    dec_e = "GO" if n_go_e >= 2 else ("NO HEADROOM FOUND (with these oracles; not a KILL)" if none_e else "MAYBE")
    sat_e = [out["families"][f]["heuristic_saturation_envelope"]["mean"] for f in FAMILIES]
    if dec_e == "GO" and sum(1 for x in sat_e if np.isfinite(x) and x >= 0.70) >= 2:
        dec_e = "MAYBE (downgraded: heuristic captures >= 70% of the envelope headroom in >= 2 families)"
    out["decision_D1"] = dec_e
    out["decision_rule"] = "envelope lower bound (deviation 2026-10-15); the pre-registered O1-only decision is in decision_D1_preregistered_O1"
    out["timing_claim_dropped"] = all(np.isfinite(timing_lo[f]) and timing_lo[f] < 0.10 for f in FAMILIES)
    fc_lo = {f: out["families"][f]["h_forecast"]["lo"] for f in FAMILIES}
    out["H1b_condition_a"] = any(np.isfinite(fc_lo[f]) and fc_lo[f] >= 0.10 for f in FAMILIES)
    pfc_worse = any(np.isfinite(out["families"][f][f"p_fc_{sg}_vs_bstar"]["lo"]) and out["families"][f][f"p_fc_{sg}_vs_bstar"]["lo"] >= 0.10
                    for f in FAMILIES for sg in (0.25, 0.5))
    out["H1b_condition_b"] = pfc_worse
    out["H1b_include"] = bool(out["H1b_condition_a"] and pfc_worse)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "d1_headroom.json").write_text(json.dumps(out, indent=2))
    print("D1 decision (envelope, approved deviation):", dec_e, "| envelope CI lower bounds:", {f: round(v, 3) for f, v in elo.items()})
    print("D1 decision (pre-registered O1 only):", decision, "| h_total CI lower bounds:", {f: round(v, 3) for f, v in lo.items()})
    print("timing claim dropped:", out["timing_claim_dropped"], "| H1b (a):", out["H1b_condition_a"], "(b):", pfc_worse)
    for f in FAMILIES:
        s = out["families"][f]
        print(f, {k: (round(s[k]["mean"], 3), round(s[k]["lo"], 3), round(s[k]["hi"], 3), s[k]["n"])
                  for k in ("h_envelope", "heuristic_saturation_envelope", "h_total", "h_timing", "h_forecast", "h_static_s_mean", "o1_vs_s_mean", "h_o1_bstar", "heuristic_saturation")})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["prep", "run", "run_pfc", "analyze"])
    ap.add_argument("--workers", type=int, default=10)
    a = ap.parse_args()
    if a.cmd == "prep":
        prep(a)
    elif a.cmd == "run":
        run(a, BASE)
    elif a.cmd == "run_pfc":
        run(a, tuple(f"P_FC_{sg}" for sg in SIGMAS))
    else:
        analyze(a)
