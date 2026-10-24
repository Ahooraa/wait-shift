"""Multi-workload runs (DFPS Sec.5.2: 10 workloads per point). Every method runs on the SAME scenario (= one seed) in each job.

Scenarios are built once in the parent (the 1.1 GB DAG pool is not loaded by the workers) and pickled; jobs are resumable
(a finished job's JSON is never recomputed).

python -m experiments.batch --kinds uniform --scales 0.5,1,2 --seeds 1-10 --workers 6 --out results/batch_u"""
from __future__ import annotations

import argparse
import json
import pickle
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from experiments.run import ASSUME, ROOT, run_methods
from dfps.workload import build_scenario

METHODS = ("SR", "SG", "DFPS", "HEU", "RL")


def job(args):
    sc_path, out_path, seed, gens, rl, drain = args
    if Path(out_path).exists():
        return out_path
    sc = pickle.load(open(sc_path, "rb"))
    res, info = run_methods(sc, seed, gens, methods=METHODS, rl_path=rl, drain_factor=drain)
    Path(out_path).write_text(json.dumps(dict(meta=sc.meta, info=info, results=res)))
    return out_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--kinds", default="uniform")
    ap.add_argument("--scales", default="0.5,1,2")
    ap.add_argument("--seeds", default="1-10")
    ap.add_argument("--duration", type=float, default=ASSUME["A21_run_length_s"])
    ap.add_argument("--gens", type=int, default=ASSUME["A06_generations"])
    ap.add_argument("--drain", type=float, default=1.0, help="drain time after the run, as a multiple of the run length")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--rl", default=str(ROOT / "results" / "rl_policy.pt"))
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    lo, hi = (int(x) for x in a.seeds.split("-"))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    dags = json.load(open(ROOT / "data" / "alibaba_dags_lt60s.json"))
    jobs = []
    for kind in a.kinds.split(","):
        for scale in (float(x) for x in a.scales.split(",")):
            for seed in range(lo, hi + 1):
                tag = f"{kind}_x{scale}_s{seed}"
                sc_path, out_path = out / f"{tag}.pkl", out / f"{tag}.json"
                if not out_path.exists():
                    pickle.dump(build_scenario(seed, kind, scale, duration_s=a.duration, dags=dags,
                                               pool_size=ASSUME["A17_function_pool_size"]), open(sc_path, "wb"))
                jobs.append((str(sc_path), str(out_path), seed, a.gens, a.rl, a.drain))
    del dags
    with ProcessPoolExecutor(a.workers) as ex:
        for done in ex.map(job, jobs):
            print("done", done, flush=True)
