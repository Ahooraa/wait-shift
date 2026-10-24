"""Does an existing method already close the D1-D3 gap? (user request 2026-10-18)

  python output/data-analysis/d1_vs_baselines.py run [--workers 10]
  python output/data-analysis/d1_vs_baselines.py analyze

The headroom of D1-D3 was measured against B* only. Here Heu and RL (original policy, trained on the original workload that the D1
scenarios use, and RL_CAL, retrained on the calibrated reproduction scenario) run on the SAME 90 D1 scenarios (F1-F3 traces, rho 0.5 /
0.7 / 0.85, seeds 1-10, 15-min windows after 60 s warm-up), with the same seeds as the D1 runs. Metric: P99 makespan.
Headroom against the best existing method:  h_exist = (best of B*, Heu, RL, RL_CAL  -  best cheater) / best of B*, Heu, RL, RL_CAL
  cheaters on all 90:  O1, O1+B*, P_TRUE (D1 envelope);   on the 27 O3S instances (seeds 1-3) also O3S with 120 s look-ahead.
Run without -I: experiments.run imports the project package and PyTorch.
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

D1 = ROOT / "results" / "d1_headroom"
D3S = ROOT / "results" / "d3s_headroom"
RUNS = ROOT / "results" / "d1_baselines"
OUT = ROOT / "output" / "data-analysis" / "results"
FAMILIES, RHOS, SEEDS = ("F1", "F2", "F3"), (0.5, 0.7, 0.85), tuple(range(1, 11))
DURATION, WARMUP = 900.0, 60.0
METHODS = ("RL", "RL_CAL")   # Heu dropped for the remaining runs (user, 2026-10-18): 2.5-5.3 h per run at rho 0.7; done Heu runs are kept


def tag(f, r, s):
    return f"{f}_r{r}_s{s}"


def job(args):
    tg, m, seed, out = args
    if Path(out).exists():
        return out
    try:
        from experiments.run import load_rl_policy
        from dfps.heu import HeuPolicy
        from dfps.ondemand import OnDemandSim
        sc = pickle.load(open(D1 / f"{tg}.pkl", "rb"))
        if m == "HEU":
            pol = HeuPolicy(seed=seed + 500)
        else:
            pt = "rl_policy_cal.pt" if m == "RL_CAL" else "rl_policy.pt"
            pol = load_rl_policy(str(ROOT / "results" / pt), seed + 600)
        t = time.time()
        sim = OnDemandSim(sc, pol, seed=seed + 400, duration=DURATION, warmup=WARMUP)
        r = sim.run()
        sim.check_invariants()
        r["wall_s"] = time.time() - t
        Path(out).write_text(json.dumps(dict(family=sc.meta["family"], rho=sc.meta["rho"], seed=seed, ctrl=m, result=r)))
    except Exception:
        import traceback
        Path(out).with_suffix(".err").write_text(traceback.format_exc())
        return out + " FAILED"
    return out


def run(a):
    RUNS.mkdir(parents=True, exist_ok=True)
    jobs = [(tag(f, r, s), m, s, str(RUNS / f"{tag(f, r, s)}.{m}.json")) for f in FAMILIES for r in RHOS for s in SEEDS for m in METHODS]
    with ProcessPoolExecutor(a.workers) as ex:
        for d in ex.map(job, jobs):
            print("done", d, flush=True)


def boot(x, n=10_000, seed=0):
    x = np.asarray(x, dtype=float)
    if len(x) < 2:
        return dict(mean=float(x.mean()) if len(x) else float("nan"), lo=float("nan"), hi=float("nan"), n=int(len(x)))
    m = np.random.default_rng(seed).choice(x, (n, len(x))).mean(axis=1)
    return dict(mean=float(x.mean()), lo=float(np.percentile(m, 2.5)), hi=float(np.percentile(m, 97.5)), n=int(len(x)), median=float(np.median(x)))


def analyze(a):
    res = {}
    for f in list(D1.glob("*.json")) + list(RUNS.glob("*.json")):
        d = json.loads(f.read_text())
        if "ctrl" not in d:
            continue
        res.setdefault((d["family"], d["rho"], d["seed"]), {})[d["ctrl"]] = d["result"]["p99_makespan"]
    for f in D3S.glob("*.O3S_h120.json"):
        d = json.loads(f.read_text())
        res.setdefault((d["family"], d["rho"], d["seed"]), {})["O3S120"] = d["result"]["p99_makespan"]
    exist, cheat90 = ("B_STAR", "HEU", "RL", "RL_CAL"), ("O1", "O1_BSTAR", "P_TRUE")
    out = dict(metric="p99_makespan", families={})
    for fam in FAMILIES:
        keys = [k for k in res if k[0] == fam]
        best_exist_name = {}
        h90, h27, hb = [], [], []
        p99 = {m: [] for m in exist + cheat90 + ("O3S120",)}
        for k in keys:
            c = res[k]
            if not all(m in c for m in ("B_STAR", "RL", "RL_CAL") + cheat90):
                continue
            ex = [m for m in exist if m in c]                          # Heu only where it was run (F1 rho 0.5 / 0.7)
            be = min(c[m] for m in ex)
            bn = min(ex, key=lambda m: c[m])
            best_exist_name[bn] = best_exist_name.get(bn, 0) + 1
            h90.append((be - min(c[m] for m in cheat90)) / be)
            hb.append((c["B_STAR"] - be) / c["B_STAR"])
            for m in p99:
                if m in c:
                    p99[m].append(c[m])
            if "O3S120" in c:
                h27.append((be - min([c[m] for m in cheat90] + [c["O3S120"]])) / be)
        out["families"][fam] = dict(
            headroom_vs_best_existing_D1envelope=boot(h90), headroom_vs_best_existing_with_O3S=boot(h27),
            best_existing_gain_over_Bstar=boot(hb), best_existing_counts=best_exist_name,
            p99_mean={m: float(np.mean(v)) for m, v in p99.items() if v})
    (OUT / "d1_vs_baselines.json").write_text(json.dumps(out, indent=1))
    for fam, v in out["families"].items():
        f = lambda b: f"{b['mean']*100:.1f}% ({b['lo']*100:.1f}-{b['hi']*100:.1f}), n={b['n']}"  # noqa: E731
        print(fam, "| best existing:", v["best_existing_counts"])
        print("   best existing vs B*:", f(v["best_existing_gain_over_Bstar"]))
        print("   headroom vs best existing, D1 envelope:", f(v["headroom_vs_best_existing_D1envelope"]))
        print("   headroom vs best existing, incl. O3S (27):", f(v["headroom_vs_best_existing_with_O3S"]))
        print("   mean P99:", {m: round(x) for m, x in v["p99_mean"].items()})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "analyze"])
    ap.add_argument("--workers", type=int, default=10)
    a = ap.parse_args()
    run(a) if a.cmd == "run" else analyze(a)
