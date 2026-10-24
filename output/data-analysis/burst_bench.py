"""Burst benchmark and the two-timescale controller (2026-10-24).

Question: does a SMALL, TRIGGERED fast capacity loop between two re-layouts catch sharp bursts that a 60 s re-layout misses, without
the churn of re-laying out every 30 s?

Why a benchmark is needed: the development scenarios contain almost no sharp bursts (Huawei seed 5 is the one that does, and it is a
held-out seed, reserved). The measure that matters is the Fano factor of 10 s arrival counts (Poisson = 1; Huawei seed 5: 56.7, the
rest of the 22 scenarios inspected: 1.2-11). Here sharp bursts are injected into the development scenarios, which are otherwise the
same scenarios.

Burst injection (make_burst_scenario): 4 bursts of 45 s at random times in [150, 820] s, at least 90 s apart. Each burst picks one of
the three busiest workflows and multiplies ITS arrival rate by 3 (extra arrivals are copies of that workflow's own arrivals inside the
window, jittered, with the origins it already used). An equal number of arrivals is removed at random elsewhere in the measured
window, so the total number of requests and the offered load are unchanged. The burst windows are stored in the scenario.

Controllers (all with B* annealing off except the reference):
  bstar   B* as published/corrected, for reference
  fz60    FROZEN-1: re-layout every 60 s + request moves
  fz30    FROZEN-1 with the re-layout every 30 s
  fast    FROZEN-1 at 60 s + the emergency loop (dfps/o3s.py fast_step): short-window sizing, Fifer-style trigger (queue drain time
          longer than a cold start), donors only from containers above both the long and the short need, at most 40 conversions
          per action, one action per 10 s

Scenarios: Azure and Huawei x 50% and 70% load x development seeds 1-2 = 8, each run under the four controllers = 32 runs. Besides
overall P99, P99 is split into requests that arrive inside a burst window (plus 60 s after it) and the rest.

  python output/data-analysis/burst_bench.py build | run [workers] | analyze
"""
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
import d3s_headroom as d  # noqa: E402
from new_layer_sweep import BASE  # noqa: E402

import yaml  # noqa: E402

from dfps.o3s import O3SimAdjuster  # noqa: E402
from dfps.sim import Sim  # noqa: E402
from dfps.variants import make_adjuster, sim_kwargs  # noqa: E402

ASSUME = yaml.safe_load((ROOT / "config" / "assumptions.yaml").read_text(encoding="utf-8"))
OUTD = ROOT / "results" / "bursts"
FROZEN = dict(BASE, placement="qaware", origin_weight=1.0, rebal_max=10 ** 9, tau=1.0, queue_term=False)
CONFIGS = {  # name -> (epoch, churn); bstar handled separately
    "fz60": (60.0, dict(FROZEN)), "fz30": (30.0, dict(FROZEN)),
    "fast": (60.0, dict(FROZEN, fast=True, fast_window=20.0, fast_clear=30.0, fast_trigger=1.0, fast_budget=40, fast_cooldown=10.0)),
}
FAST = CONFIGS["fast"][1]
# options borrowed from FRAP-DWS (Wang et al., IEEE TC 2026), as learning-free heuristics:
#   fast_hold  window caching: the slow re-layout may not undo an emergency fix for 60 s
#   fast_mu    burst weight: the budget grows with how far the worst queue exceeds a cold start (budget x (1 + mu x severity))
#   fast_gate  regime weight: while the 20 s rate stays within 15% of the 2-minute baseline the trigger needs two cold starts
CONFIGS["fast_hold"] = (60.0, dict(FAST, fast_hold=60.0))
CONFIGS["fast_full"] = (60.0, dict(FAST, fast_hold=60.0, fast_mu=1.0, fast_gate=0.15))
CONFIGS["fast_gate"] = (60.0, dict(FAST, fast_gate=0.15))
# Narrowed 2026-10-24 after the smoke tests (no P99 gain, +8-10% cold starts at 50-70% load where 580-820 containers were spare):
# one option only, the regime gate (the review's pick: the statistically motivated guard against false alarms); hold and severity stay
# implemented but are not run. 85% load is added because that is where spare capacity is tight enough for an emergency fix to matter.
NAMES = ("fz60", "fz30", "fast_gate")
SCEN = [(f, r, s) for f in ("F1", "F2") for r in (0.5, 0.7, 0.85) for s in (1, 2)]   # 85% added 2026-10-24: where spare capacity is tight
WARM, DUR = 60.0, 900.0
N_BURST, FACTOR, BURST_S, MIN_GAP = 4, 3.0, 45.0, 90.0
M = "p99_makespan"


def tag(c):
    return f"{c[0]}_r{c[1]}_s{c[2]}"


def make_burst_scenario(c):
    sc = pickle.load(open(d.D1 / f"{tag(c)}.pkl", "rb"))
    rng = np.random.default_rng(c[2] * 7919 + int(c[1] * 100) + (13 if c[0] == "F1" else 29))
    arr = sorted(sc.arrivals)
    rate = np.asarray(sc.meta["per_app_rate"], float)
    top = np.argsort(-rate)[:3]
    starts = []
    while len(starts) < N_BURST:                                              # random starts, at least MIN_GAP + BURST_S apart
        t0 = float(rng.uniform(150.0, 820.0 - BURST_S))
        if all(abs(t0 - s) >= MIN_GAP + BURST_S for s in starts):
            starts.append(t0)
    starts.sort()
    extra, bursts = [], []
    for t0 in starts:
        w = int(rng.choice(top))
        inside = [a for a in arr if a[1] == w and t0 <= a[0] < t0 + BURST_S]
        n_extra = int(round((FACTOR - 1.0) * len(inside)))
        origins = [a[2] for a in arr if a[1] == w] or [0]
        for _ in range(n_extra):
            extra.append((float(rng.uniform(t0, t0 + BURST_S)), w, int(rng.choice(origins))))
        bursts.append(dict(t0=t0, dur=BURST_S, workflow=w, base_in_window=len(inside), extra=n_extra))
    # keep the total number of requests: drop as many as were added, at random, from the measured window outside the bursts
    in_burst = lambda t: any(b["t0"] <= t < b["t0"] + b["dur"] for b in bursts)  # noqa: E731
    cand = [i for i, a in enumerate(arr) if WARM <= a[0] < DUR and not in_burst(a[0])]
    drop = set(rng.choice(cand, size=min(len(extra), len(cand)), replace=False).tolist())
    new = [a for i, a in enumerate(arr) if i not in drop] + extra
    new.sort()
    sc.arrivals = new
    sc.meta = dict(sc.meta, bursts=bursts, n_arrivals=len(new), burst_factor=FACTOR, kind=sc.meta.get("kind", "") + "+bursts")
    return sc


def fano10(sc):
    t = np.array([a[0] for a in sc.arrivals])
    t = t[(t >= WARM) & (t < DUR)]
    cnt = np.histogram(t, bins=np.arange(WARM, DUR + 1, 10))[0].astype(float)
    return float(cnt.var() / cnt.mean())


def build():
    OUTD.mkdir(parents=True, exist_ok=True)
    for c in SCEN:
        p = OUTD / f"{tag(c)}_B.pkl"
        if p.exists():
            continue
        sc = make_burst_scenario(c)
        pickle.dump(sc, open(p, "wb"))
        base = pickle.load(open(d.D1 / f"{tag(c)}.pkl", "rb"))
        print(f"{tag(c)}: requests {len(base.arrivals)} -> {len(sc.arrivals)}; Fano of 10 s counts {fano10(base):.1f} -> {fano10(sc):.1f};"
              f" bursts at {[round(b['t0']) for b in sc.meta['bursts']]} (workflows {[b['workflow'] for b in sc.meta['bursts']]})", flush=True)


def one(args):
    name, c, period = args
    out = OUTD / f"{tag(c)}_B.{name}.json"
    if out.exists():
        return str(out)
    try:
        assert np.__version__.startswith("1."), "run with the Anaconda interpreter (numpy 1.26)"
        sc = pickle.load(open(OUTD / f"{tag(c)}_B.pkl", "rb"))
        P = pickle.load(open(d.D1 / f"{tag(c)}.prep.pkl", "rb"))
        seed = c[2]
        kw = sim_kwargs("B_STAR", ASSUME)
        kw.update(warmup=WARM, duration=DUR, retry_min_interval=1.0, retry_max_attempts=10, record_requests=True)
        if name == "bstar":
            kw["interval"] = float(period)
            adj = make_adjuster("B_STAR", ASSUME, seed=seed + 300)
        else:
            epoch, churn = CONFIGS[name]
            adj = O3SimAdjuster(make_adjuster("B_STAR", ASSUME, seed=seed + 300), period, epoch=epoch, horizon=120.0, K=5, seed=seed + 800,
                                warmup=WARM, blind=True, cand_mode="nosim", churn=dict(churn))
            kw["interval"] = adj.next_interval
        t = time.time()
        sim = Sim(sc, P["X0"], adjuster=adj, seed=seed + 400, **kw)
        r = sim.run()
        r["wall_s"] = time.time() - t
        fl = getattr(adj, "fast_log", [])
        out.write_text(json.dumps(dict(name=name, case=list(c), result=r, log=sim.request_log, bursts=sc.meta["bursts"],
                                       n_fast_changes=int(getattr(adj, "n_fast", 0)), fast_actions=[x for x in fl if x.get("applied")],
                                       fast_checks=len(fl))))
        return str(out)
    except Exception:
        import traceback
        out.with_suffix(".err").write_text(traceback.format_exc())
        return str(out) + " FAILED"


def run(workers):
    build()
    T = json.loads((d.OUT / "g2_tstar.json").read_text())
    jobs = [(n, c, float(T["families"][c[0]]["T_star"])) for c in SCEN for n in NAMES]
    with ProcessPoolExecutor(workers) as ex:
        for done in ex.map(one, jobs):
            print("done", done, flush=True)


def split_p99(log, bursts):
    """P99 of requests arriving inside a burst window (plus 60 s after it) and of the rest; log = (id, t_arr, makespan, ok)."""
    inb, outb = [], []
    for _, ta, m, _ in log:
        (inb if any(b["t0"] <= ta < b["t0"] + b["dur"] + 60.0 for b in bursts) else outb).append(m)
    q = lambda v: float(np.percentile(v, 99)) if len(v) > 20 else float("nan")  # noqa: E731
    return q(inb), q(outb)


def analyze():
    from d1_rlla import boot
    R = {}
    for c in SCEN:
        for n in NAMES + ("bstar",):
            f = OUTD / f"{tag(c)}_B.{n}.json"
            if f.exists():
                R[(n, c)] = json.loads(f.read_text())
    cs = [c for c in SCEN if all((n, c) in R for n in NAMES)]
    part = [c for c in SCEN if ("fz60", c) in R and any((n, c) in R for n in NAMES[1:])]
    print(f"{len(cs)} of {len(SCEN)} burst scenarios have all five controllers ({len(part)} have fz60 plus at least one other)\n")
    print("P99 of ALL requests / of requests arriving INSIDE a burst window (+60 s), seconds")
    print("%-14s | %s" % ("scenario", " | ".join("%-15s" % n for n in NAMES)))
    for c in part:
        cells = []
        for n in NAMES:
            if (n, c) in R:
                x = R[(n, c)]
                cells.append("%6.0f /%6.0f  " % (x["result"][M], split_p99(x["log"], x["bursts"])[0]))
            else:
                cells.append("%-15s" % "-")
        print("%-14s | %s" % (tag(c), " | ".join(cells)))
    p = lambda b: f"{b['mean'] * 100:+6.1f}% ({b['lo'] * 100:+.0f} to {b['hi'] * 100:+.0f})"  # noqa: E731
    print("\nP99 gain over FROZEN-1 at 60 s (paired over the scenarios each variant has):")
    out = {}
    for n in NAMES[1:]:
        cc = [c for c in part if (n, c) in R]
        if not cc:
            continue
        sp = lambda k, c: split_p99(R[(k, c)]["log"], R[(k, c)]["bursts"])  # noqa: E731
        g = [(R[("fz60", c)]["result"][M] - R[(n, c)]["result"][M]) / R[("fz60", c)]["result"][M] for c in cc]
        gb = [(sp("fz60", c)[0] - sp(n, c)[0]) / sp("fz60", c)[0] for c in cc]
        go = [(sp("fz60", c)[1] - sp(n, c)[1]) / sp("fz60", c)[1] for c in cc]
        cold = np.mean([R[(n, c)]["result"]["cold_starts"] / R[("fz60", c)]["result"]["cold_starts"] - 1 for c in cc])
        acts = np.mean([len(R[(n, c)].get("fast_actions", [])) for c in cc])
        chg = np.mean([R[(n, c)].get("n_fast_changes", 0) for c in cc])
        out[n] = dict(n=len(cc), all=boot(g), in_burst=boot(gb), outside=boot(go), cold_change=float(cold), actions=float(acts), changes=float(chg))
        print(f"  {n:9s} n={len(cc)}: all {p(boot(g))}, better in {sum(x > 0 for x in g)}/{len(cc)} | in bursts {p(boot(gb))} |"
              f" outside {p(boot(go))} | cold starts {100 * cold:+.0f}% | emergency actions {acts:.1f}, conversions {chg:.0f} per run")
    (d.OUT / "burst_bench.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "build":
        build()
    elif cmd == "run":
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 6)
    else:
        analyze()
