"""Gate G2, part 2: reproduce DFPS's own qualitative claims with the as-printed and the corrected (B*) method (plan Task 10).

  python -I output/data-analysis/g2_reproduction.py run     [--seeds 1-10] [--workers 10]
  python -I output/data-analysis/g2_reproduction.py analyze

Setting (DFPS Sec. 5.1, Table 2): 80 edge nodes, 15 workflows (real Alibaba DAGs, applications under one minute), Uniform and
Pareto arrivals, arrival scale 0.25-2, 10 workloads per point, run length 300 s with 30 s warm-up (A21), drained to completion.
Methods: SR; SG-signed and DFPS-as-printed (placement with Eq. 3 as printed, E1); SG-abs and B* (placement with |.|, Metropolis
acceptance, Erlang-C with P0, best-so-far). Same scenario, workload and simulator for every method.

Claims checked (pre-registered, plan Task 10):  (i) mean makespan rises with the arrival scale for every method, Uniform and Pareto;
(ii) under Pareto the mean makespan ranks DFPS < SG < SR; (iii) SR and SG have zero cold starts. G2 needs >= 2 of 3 to reproduce.
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
from dfps.sim import Sim  # noqa: E402
from dfps.variants import make_adjuster, sim_kwargs  # noqa: E402
from dfps.workload import build_scenario  # noqa: E402

OUT = ROOT / "output" / "data-analysis" / "results"
RUNS = ROOT / "results" / "g2_reproduction"
SCALES = (0.25, 0.5, 1.0, 2.0)
KINDS = ("uniform", "pareto")


def job(args):
    """Wrapper: an exception in one job is written to <tag>.err (with traceback) instead of stopping the whole batch."""
    try:
        return _job(args)
    except Exception:
        import traceback
        Path(args[1]).with_suffix(".err").write_text(traceback.format_exc())
        return args[1] + " FAILED"


def _job(args):
    sc_path, out_path, seed = args
    if Path(out_path).exists():
        return out_path
    sc = pickle.load(open(sc_path, "rb"))
    # Deviation (logged 2026-10-14): overloaded cells (Uniform x2.0, all Pareto) retry the waiting list at most once per simulated
    # second; with the original per-completion retry a x2.0 run did not finish in 13 h (retry storm once node storage is exhausted).
    # Second deviation (2026-10-14): the 1 s throttle alone did not bound the cost (each round re-tried the whole, growing waiting
    # list); overloaded cells now also try at most 10 waiting requests per round (round-robin).
    overloaded = sc.meta["kind"] == "pareto" and sc.meta["scale"] >= 0.5 or sc.meta["scale"] >= 2.0
    retry, cap = (1.0, 10) if overloaded else (0.0, None)
    res, info = {}, {}
    for variant, prop in (("B_STAR", "abs"), ("AS_PRINTED", "signed")):
        x_sr, x_sg, inf = initial_placements(sc, seed, ASSUME["A06_generations"], prop)
        info[variant] = inf
        kw = sim_kwargs(variant, ASSUME)
        runs = [("SG_" + prop, x_sg, None)]
        if variant == "B_STAR":
            runs.insert(0, ("SR", x_sr, None))
        runs.append(("DFPS_" + variant, x_sg, make_adjuster(variant, ASSUME, seed=seed + 300)))
        for name, X, adj in runs:
            t = time.time()
            sim = Sim(sc, X, adjuster=adj, seed=seed + 400, retry_min_interval=retry, retry_max_attempts=cap, **kw)
            r = sim.run()
            sim.check_invariants()
            r["wall_s"] = time.time() - t
            res[name] = r
    Path(out_path).write_text(json.dumps(dict(meta={k: v for k, v in sc.meta.items() if k != "per_app_rate"}, retry_min_interval=retry, retry_max_attempts=cap, info=info, results=res)))
    return out_path


def run(a):
    lo, hi = (int(x) for x in a.seeds.split("-"))
    RUNS.mkdir(parents=True, exist_ok=True)
    dags = json.load(open(ROOT / "data" / "alibaba_dags_lt60s.json"))
    jobs = []
    for kind in KINDS:
        for scale in SCALES:
            for seed in range(lo, hi + 1):
                tag = f"{kind}_x{scale}_s{seed}"
                sc_path, out_path = RUNS / f"{tag}.pkl", RUNS / f"{tag}.json"
                if not out_path.exists() and not sc_path.exists():
                    sc = build_scenario(seed, kind, scale, duration_s=ASSUME["A21_run_length_s"], dags=dags,
                                        pool_size=ASSUME["A17_function_pool_size"])
                    pickle.dump(sc, open(sc_path, "wb"))
                jobs.append((str(sc_path), str(out_path), seed))
    del dags
    with ProcessPoolExecutor(a.workers) as ex:
        for done in ex.map(job, jobs):
            print("done", done, flush=True)


def analyze(a):
    rows = {}
    for f in sorted(RUNS.glob("*.json")):
        d = json.loads(f.read_text())
        m = d["meta"]
        rows.setdefault((m["kind"], m["scale"]), []).append(d["results"])
    names = ["SR", "SG_signed", "SG_abs", "DFPS_AS_PRINTED", "DFPS_B_STAR"]
    out = {"cells": {}, "n_per_cell": {f"{k}_x{s}": len(v) for (k, s), v in rows.items()}}
    mean = {}
    for (kind, scale), rs in sorted(rows.items()):
        cell = {}
        for n in names:
            v = np.array([r[n]["avg_makespan"] for r in rs if n in r])
            c = np.array([r[n]["cold_starts"] for r in rs if n in r])
            u = np.array([r[n]["n_unfinished"] for r in rs if n in r])
            cell[n] = dict(mean=float(v.mean()), sd=float(v.std(ddof=1)) if len(v) > 1 else float("nan"), n=int(len(v)),
                           p99_mean=float(np.mean([r[n]["p99_makespan"] for r in rs if n in r])),
                           cold_starts_mean=float(c.mean()), cold_starts_max=int(c.max()), unfinished_max=int(u.max()))
            mean[(kind, scale, n)] = cell[n]["mean"]
        out["cells"][f"{kind}_x{scale}"] = cell
    # claim (i): monotone increase with the scale, per method and kind
    c1 = {}
    for kind in KINDS:
        for n in names:
            seq = [mean.get((kind, s, n)) for s in SCALES]
            if None in seq:
                continue
            c1[f"{kind}/{n}"] = bool(all(seq[i] < seq[i + 1] for i in range(len(seq) - 1)))
    out["claim_i_per_method"] = c1
    out["claim_i"] = bool(c1) and all(c1.values())
    # claim (ii): Pareto, DFPS < SG < SR at every scale (for each DFPS variant against its own SG)
    c2 = {}
    for var, sg in (("DFPS_B_STAR", "SG_abs"), ("DFPS_AS_PRINTED", "SG_signed")):
        for s in SCALES:
            if ("pareto", s, var) in mean:
                c2[f"{var}@{s}"] = bool(mean[("pareto", s, var)] < mean[("pareto", s, sg)] < mean[("pareto", s, "SR")])
    out["claim_ii_per_point"] = c2
    out["claim_ii"] = {v: bool(c2 and all(val for k, val in c2.items() if k.startswith(v))) for v in ("DFPS_B_STAR", "DFPS_AS_PRINTED")}
    # claim (iii): SR/SG zero cold starts
    c3 = all(cell[n]["cold_starts_max"] == 0 for cell in out["cells"].values() for n in ("SR", "SG_signed", "SG_abs") if n in cell)
    out["claim_iii"] = bool(c3)
    out["claims_reproduced_B_STAR"] = int(out["claim_i"]) + int(out["claim_ii"]["DFPS_B_STAR"]) + int(out["claim_iii"])
    out["claims_reproduced_AS_PRINTED"] = int(out["claim_i"]) + int(out["claim_ii"]["DFPS_AS_PRINTED"]) + int(out["claim_iii"])
    # as-printed vs corrected (motivation material)
    diff = {}
    for (kind, scale), rs in sorted(rows.items()):
        a_ = np.array([r["DFPS_AS_PRINTED"]["avg_makespan"] for r in rs])
        b_ = np.array([r["DFPS_B_STAR"]["avg_makespan"] for r in rs])
        d = a_ - b_
        diff[f"{kind}_x{scale}"] = dict(mean_diff=float(d.mean()), sem=float(d.std(ddof=1) / np.sqrt(len(d))) if len(d) > 1 else None,
                                        p99_printed=float(np.mean([r["DFPS_AS_PRINTED"]["p99_makespan"] for r in rs])),
                                        p99_bstar=float(np.mean([r["DFPS_B_STAR"]["p99_makespan"] for r in rs])))
    out["as_printed_minus_bstar_mean_makespan"] = diff
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "g2_reproduction.json").write_text(json.dumps(out, indent=2))
    print(json.dumps({k: v for k, v in out.items() if k != "cells"}, indent=2))
    for k, cell in out["cells"].items():
        print(k, " ".join(f"{n}={cell[n]['mean']:.1f}" for n in names if n in cell))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "analyze"])
    ap.add_argument("--seeds", default="1-10")
    ap.add_argument("--workers", type=int, default=10)
    a = ap.parse_args()
    run(a) if a.cmd == "run" else analyze(a)
