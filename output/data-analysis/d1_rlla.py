"""RL + look-ahead cheater (dfps/rlla.py) on the D1 scenarios: is there room above the best existing method (RL)?

  python output/data-analysis/d1_rlla.py run [--workers 10]
  python output/data-analysis/d1_rlla.py analyze

27 instances (F1-F3 x rho 0.5 / 0.7 / 0.85 x seeds 1-3, as O3S_h120), same scenario, seeds and window as the D1 runs and as RL in
d1_vs_baselines.py (policy seed + 600, simulator seed + 400, 15 min after 60 s warm-up). Original RL policy (trained on the
workload the D1 scenarios use). Look-ahead: every 30 s, pre-warm plans none / margin 0 / margin 0.5 over a 60 s lead, scored by
replaying the true arrivals 120 s ahead. Headroom above RL: (RL - RLLA) / RL on P99; also against the best of B*, Heu, RL, RL_CAL.
Run without -I (imports the project package and PyTorch).
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
BASE = ROOT / "results" / "d1_baselines"
D3S = ROOT / "results" / "d3s_headroom"
RUNS = ROOT / "results" / "d1_rlla"
OUT = ROOT / "output" / "data-analysis" / "results"
FAMILIES, RHOS, SEEDS = ("F1", "F2", "F3"), (0.5, 0.7, 0.85), (1, 2, 3)
DURATION, WARMUP = 900.0, 60.0


def tag(f, r, s):
    return f"{f}_r{r}_s{s}"


def job(args):
    tg, seed, out, duration = args
    if Path(out).exists():
        return out
    try:
        from experiments.run import load_rl_policy
        from dfps.ondemand import OnDemandSim
        from dfps.rlla import LookAhead, attach_lookahead
        sc = pickle.load(open(D1 / f"{tg}.pkl", "rb"))
        pol = load_rl_policy(str(ROOT / "results" / "rl_policy.pt"), seed + 600)
        sim = OnDemandSim(sc, pol, seed=seed + 400, duration=duration, warmup=WARMUP)
        la = LookAhead()
        attach_lookahead(sim, la, first=WARMUP)
        t = time.time()
        r = sim.run()
        sim.check_invariants()
        r["wall_s"] = time.time() - t
        Path(out).write_text(json.dumps(dict(family=sc.meta["family"], rho=sc.meta["rho"], seed=seed, ctrl="RLLA", result=r,
                                             decisions=la.log)))
    except Exception:
        import traceback
        Path(out).with_suffix(".err").write_text(traceback.format_exc())
        return out + " FAILED"
    return out


def run(a):
    RUNS.mkdir(parents=True, exist_ok=True)
    jobs = [(tag(f, r, s), s, str(RUNS / f"{tag(f, r, s)}.RLLA.json"), DURATION) for f in FAMILIES for r in RHOS for s in SEEDS]
    jobs.sort(key=lambda j: -float(j[0].split("_r")[1].split("_")[0]))
    with ProcessPoolExecutor(a.workers) as ex:
        for d in ex.map(job, jobs):
            print("done", d, flush=True)


def boot(x, n=10_000, seed=0):
    x = np.asarray(x, dtype=float)
    if len(x) < 2:
        return dict(mean=float(x.mean()) if len(x) else float("nan"), lo=float("nan"), hi=float("nan"), n=int(len(x)))
    m = np.random.default_rng(seed).choice(x, (n, len(x))).mean(axis=1)
    return dict(mean=float(x.mean()), lo=float(np.percentile(m, 2.5)), hi=float(np.percentile(m, 97.5)), n=int(len(x)))


def analyze(a):
    res = {}
    for d_ in (D1, BASE, RUNS):
        for f in d_.glob("*.json"):
            d = json.loads(f.read_text())
            if "ctrl" in d:
                res.setdefault((d["family"], d["rho"], d["seed"]), {})[d["ctrl"]] = d["result"]["p99_makespan"]
    for f in D3S.glob("*.O3S_h120.json"):
        d = json.loads(f.read_text())
        res.setdefault((d["family"], d["rho"], d["seed"]), {})["O3S120"] = d["result"]["p99_makespan"]
    out = {}
    exist = ("B_STAR", "HEU", "RL", "RL_CAL")
    for fam in FAMILIES:
        h_rl, h_ex, h_all = [], [], []
        means = {}
        for k, c in res.items():
            if k[0] != fam or "RLLA" not in c or not all(m in c for m in ("B_STAR", "RL", "RL_CAL")):
                continue
            be = min(c[m] for m in exist if m in c)                 # Heu only where it was run
            h_rl.append((c["RL"] - c["RLLA"]) / c["RL"])
            h_ex.append((be - c["RLLA"]) / be)
            cheats = [c[m] for m in ("RLLA", "O3S120", "O1_BSTAR", "O1", "P_TRUE") if m in c]
            h_all.append((be - min(cheats)) / be)
            for m in exist + ("RLLA", "O3S120", "O1_BSTAR"):
                if m in c:
                    means.setdefault(m, []).append(c[m])
        out[fam] = dict(rlla_vs_rl=boot(h_rl), rlla_vs_best_existing=boot(h_ex), best_cheater_vs_best_existing=boot(h_all),
                        p99_mean={m: float(np.mean(v)) for m, v in means.items()})
    (OUT / "d1_rlla.json").write_text(json.dumps(out, indent=1))
    for fam, v in out.items():
        f = lambda b: f"{b['mean']*100:.1f}% ({b['lo']*100:.1f}-{b['hi']*100:.1f}), n={b['n']}"  # noqa: E731
        print(fam, "| RLLA vs RL:", f(v["rlla_vs_rl"]), "| vs best existing:", f(v["rlla_vs_best_existing"]),
              "| best cheater vs best existing:", f(v["best_cheater_vs_best_existing"]))
        print("   mean P99:", {m: round(x) for m, x in v["p99_mean"].items()})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "analyze"])
    ap.add_argument("--workers", type=int, default=10)
    a = ap.parse_args()
    run(a) if a.cmd == "run" else analyze(a)
