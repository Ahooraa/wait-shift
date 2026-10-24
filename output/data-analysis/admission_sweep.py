"""Admission control, second round (2026-10-24), on the D2 overload set (Azure and Huawei overload windows, seeds 1-10).

Reasons (second review): the first round (overload_admission.py) used the k-median version of the controller, the threshold was B*'s and
untuned, and it did not say whether admission changes the regime in which unlimited request moves are needed. Controller here = FROZEN-2
(frozen2.py: FROZEN-1 + moves right after a re-layout + 4 s move period on both families).

  base0 / base1     FROZEN-2 without / with admission (theta 1.0 x slots)                         20 cases each
  cap100_adm, cap300_adm   request-move cap 100 / 300 per round, with admission                    20 cases each
  cap100_no, cap300_no     the same caps without admission                                         10 cases (seeds 1-5)
  theta0.5, theta2.0       admission threshold 0.5 / 2.0 x slots (1.0 = base1), unlimited moves    10 cases (seeds 1-5)
  bstar0, bstar1    B* without / with admission (theta 1.0), same logging                          10 cases (seeds 1-5)
Every run logs each request and its unloaded critical path, so the SLO factor (goodput counts workflows finishing within factor x their
unloaded critical path; 3 so far) is swept OFFLINE at 2, 3, 5 and 10 from the same runs.
Questions: (1) does admission flatten the move-cap curve (does it remove the pressure that made unlimited moves necessary)?
(2) how sensitive is admission to its threshold? (3) does the conclusion depend on the SLO factor of 3?

Files results/d2_headroom/<case>.adm2_<name>.json.   python output/data-analysis/admission_sweep.py run [workers] | analyze
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

import yaml  # noqa: E402

from dfps.nsga2 import PlacementProblem, nsga2  # noqa: E402
from dfps.controllers import QueueThresholdAdmission  # noqa: E402
from dfps.o3s import O3SimAdjuster  # noqa: E402
from dfps.sim import Sim  # noqa: E402
from dfps.variants import make_adjuster, sim_kwargs  # noqa: E402
from frozen2 import FROZEN2, MOVE_PERIOD_S  # noqa: E402

ASSUME = yaml.safe_load((ROOT / "config" / "assumptions.yaml").read_text(encoding="utf-8"))   # no PyTorch import (OMP #15)
RUNS = ROOT / "results" / "d2_headroom"
OUT = ROOT / "output" / "data-analysis" / "results"
DURATION, WARMUP = 900.0, 60.0
ALL = [(f, s) for f in ("F1", "F2") for s in range(1, 11)]
HALF = [(f, s) for f in ("F1", "F2") for s in range(1, 6)]
# name -> (controller churn, admission theta or None, cases, controller kind)
CONFIGS = {
    "base1": (dict(FROZEN2), 1.0, ALL, "ours"), "base0": (dict(FROZEN2), None, ALL, "ours"),
    "cap100_adm": (dict(FROZEN2, rebal_max=100), 1.0, ALL, "ours"), "cap300_adm": (dict(FROZEN2, rebal_max=300), 1.0, ALL, "ours"),
    "theta0.5": (dict(FROZEN2), 0.5, HALF, "ours"), "theta2.0": (dict(FROZEN2), 2.0, HALF, "ours"),
    "cap100_no": (dict(FROZEN2, rebal_max=100), None, HALF, "ours"), "cap300_no": (dict(FROZEN2, rebal_max=300), None, HALF, "ours"),
    "bstar1": ({}, 1.0, HALF, "bstar"), "bstar0": ({}, None, HALF, "bstar"),
}
M = "p99_makespan"


def initial_layout(sc, seed, gens):
    """The NSGA-II layout the other experiments start from (same as experiments.run.initial_placements, minus its PyTorch import)."""
    prob = PlacementProblem(sc.network, sc.ecc, np.array([f.exec_time for f in sc.functions]), "abs")
    return nsga2(prob, np.random.default_rng(seed + 200), gens=gens)[2]


def job(args):
    name, fam, seed, period_b = args
    out = RUNS / f"{fam}_s{seed}.adm2_{name}.json"
    if out.exists():
        return str(out)
    try:
        import numpy as _np
        assert _np.__version__.startswith("1."), "run with the Anaconda interpreter (numpy 1.26)"
        churn, theta, _, kind = CONFIGS[name]
        sc = pickle.load(open(RUNS / f"{fam}_s{seed}.pkl", "rb"))
        X = initial_layout(sc, seed, ASSUME["A06_generations"])
        kw = sim_kwargs("B_STAR", ASSUME)
        kw.update(warmup=WARMUP, duration=DURATION, retry_min_interval=1.0, retry_max_attempts=10, record_requests=True)
        if theta is not None:
            kw["admission"] = QueueThresholdAdmission(theta)
        if kind == "ours":
            adj = O3SimAdjuster(make_adjuster("B_STAR", ASSUME, seed=seed + 300), MOVE_PERIOD_S[fam], epoch=60.0, horizon=120.0, K=5,
                                seed=seed + 800, warmup=WARMUP, blind=True, cand_mode="nosim", churn=dict(churn))
            kw["interval"] = adj.next_interval
        else:
            adj = make_adjuster("B_STAR", ASSUME, seed=seed + 300)
            kw["interval"] = float(period_b)
        t = time.time()
        sim = Sim(sc, X, adjuster=adj, seed=seed + 400, **kw)
        r = sim.run()
        r["wall_s"] = time.time() - t
        out.write_text(json.dumps(dict(name=name, family=fam, seed=seed, theta=theta, result=r,
                                       log=[(a, round(b, 2), round(c, 2)) for a, b, c, _ in sim.request_log], cp=[round(x, 2) for x in sim.request_cp])))
        return str(out)
    except Exception:
        import traceback
        out.with_suffix(".err").write_text(traceback.format_exc())
        return str(out) + " FAILED"


def run(workers, only=None):
    T = json.loads((OUT / "g2_tstar.json").read_text())
    T = {f: float(T["families"][f]["T_star"]) for f in ("F1", "F2")}
    order = ["base1", "base0", "cap100_adm", "cap300_adm", "theta0.5", "theta2.0", "cap100_no", "cap300_no", "bstar1", "bstar0"]
    jobs = [(n, f, s, T[f]) for n in order if (only is None or n in only) for f, s in CONFIGS[n][2] if not (RUNS / f"{f}_s{s}.adm2_{n}.json").exists()]
    print(f"{len(jobs)} runs", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        for done in ex.map(job, jobs):
            print("done", done, flush=True)


def load(name):
    o = {}
    for f in RUNS.glob(f"*.adm2_{name}.json"):
        x = json.loads(f.read_text())
        o[(x["family"], x["seed"])] = x
    return o


def goodput(x, k):
    """Workflows finishing within k x their unloaded critical path, per second of the measured window."""
    cap_t = DURATION - WARMUP
    return sum(1 for (_, _, m), cp in zip(x["log"], x["cp"]) if m <= k * cp) / cap_t


def analyze():
    from d1_rlla import boot
    R = {n: load(n) for n in CONFIGS}
    p = lambda b: f"{b['mean'] * 100:+6.1f}% ({b['lo'] * 100:+.0f} to {b['hi'] * 100:+.0f})"  # noqa: E731
    row = lambda n, ks: (np.mean([R[n][k]["result"]["slo_goodput"] for k in ks]),  # noqa: E731
                         np.mean([R[n][k]["result"]["n_rejected"] / max(1, R[n][k]["result"]["n_arrived"]) for k in ks]),
                         np.mean([R[n][k]["result"][M] for k in ks]), np.mean([R[n][k]["result"]["n_parked"] for k in ks]),
                         np.mean([R[n][k]["result"]["n_moved"] / max(1, R[n][k]["result"]["n_completed"]) for k in ks]))
    print("=== 1. FROZEN-2 with and without admission (theta 1.0), 20 overload cases ===")
    ks = [k for k in ALL if k in R["base0"] and k in R["base1"]]
    for n in ("base0", "base1"):
        if ks:
            g, rj, p99, pk, mv = row(n, ks)
            print("  %-8s goodput %6.2f | rejected %3.0f%% | P99 of admitted %6.0f s | parked %7.1f | moves/request %.2f" % (n, g, 100 * rj, p99, pk, mv))
    print("\n=== 2. Move-cap curve with and without admission (same cases within each row) ===")
    for lab, cases, trio in (("with admission (20 cases)", ALL, ("cap100_adm", "cap300_adm", "base1")),
                             ("without admission (10 cases)", HALF, ("cap100_no", "cap300_no", "base0"))):
        ks = [k for k in cases if all(k in R[n] for n in trio)]
        if not ks:
            continue
        print("  " + lab)
        for n, c in zip(trio, ("cap 100", "cap 300", "unlimited")):
            g, rj, p99, pk, mv = row(n, ks)
            print("     %-10s goodput %6.2f | rejected %3.0f%% | P99 %6.0f s | parked %8.1f | moves/request %.2f  (n=%d)" % (c, g, 100 * rj, p99, pk, mv, len(ks)))
    print("\n=== 3. Admission threshold (10 cases, unlimited moves) ===")
    ks = [k for k in HALF if all(k in R[n] for n in ("theta0.5", "base1", "theta2.0", "base0"))]
    for n, c in (("base0", "none"), ("theta0.5", "0.5 x slots"), ("base1", "1.0 x slots"), ("theta2.0", "2.0 x slots")):
        if ks:
            g, rj, p99, pk, mv = row(n, ks)
            print("     %-12s goodput %6.2f | rejected %3.0f%% | P99 of admitted %6.0f s | parked %7.1f  (n=%d)" % (c, g, 100 * rj, p99, pk, len(ks)))
    print("\n=== 4. SLO factor (goodput re-evaluated from the request logs; 20 cases for ours, 10 for B*) ===")
    for k_ in (2, 3, 5, 10):
        ks = [k for k in ALL if k in R["base0"] and k in R["base1"]]
        if not ks:
            break
        a0, a1 = np.mean([goodput(R["base0"][k], k_) for k in ks]), np.mean([goodput(R["base1"][k], k_) for k in ks])
        s = "  factor %2d x: ours %.2f -> %.2f with admission (x%.1f)" % (k_, a0, a1, a1 / max(a0, 1e-9))
        kb = [k for k in HALF if k in R["bstar0"] and k in R["bstar1"]]
        if kb:
            b0, b1 = np.mean([goodput(R["bstar0"][k], k_) for k in kb]), np.mean([goodput(R["bstar1"][k], k_) for k in kb])
            kk = [k for k in kb if k in R["base0"] and k in R["base1"]]
            o1 = np.mean([goodput(R["base1"][k], k_) for k in kk])
            s += " | B* %.2f -> %.2f (x%.1f) | ours+admission over B*+admission: x%.1f" % (b0, b1, b1 / max(b0, 1e-9), o1 / max(b1, 1e-9))
        print(s)


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 8, sys.argv[3].split(",") if len(sys.argv) > 3 else None)
    else:
        analyze()
