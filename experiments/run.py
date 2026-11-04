"""Run SR, SG and DFPS on one scenario (same simulator, workload, seeds and capacities for every method; PLAN.md rule 7).

python -m experiments.run --kind uniform --scale 1.0 --seed 1 [--gens 250] [--ne 80] [--nw 15]"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import yaml

from dfps.heu import HeuPolicy
from dfps.nsga2 import PlacementProblem, nsga2
from dfps.ondemand import OnDemandSim
from dfps.rl import MosecPolicy, QNet
from dfps.sa import SimulatedAnnealing
from dfps.sim import Sim
from dfps.workload import build_scenario

ROOT = Path(__file__).resolve().parent.parent
ASSUME = yaml.safe_load((ROOT / "config" / "assumptions.yaml").read_text(encoding="utf-8"))


def initial_placements(sc, seed, gens, prop_variant="abs", log=None):
    """SR: random feasible placement. SG/DFPS: the NSGA-II plan (same plan for both)."""
    prob = PlacementProblem(sc.network, sc.ecc, np.array([f.exec_time for f in sc.functions]), prop_variant, fw=sc.fw)
    x_sr = prob.random(np.random.default_rng(seed + 100))
    t = time.time()
    _, front_obj, x_sg = nsga2(prob, np.random.default_rng(seed + 200), gens=gens, log=log)
    return x_sr, x_sg, dict(nsga2_seconds=time.time() - t, front_size=int(len(front_obj)),
                            sr_objectives=prob.objectives(x_sr).tolist(), sg_objectives=prob.objectives(x_sg).tolist())


def load_rl_policy(path, seed, sizes=False):
    import torch
    torch.set_num_threads(1)
    from dfps.rl import D, D_SIZES
    q = QNet(d=D + (D_SIZES if sizes else 0))
    q.load_state_dict(torch.load(path))
    q.eval()
    return MosecPolicy(seed=seed, train=False, qnet=q, sizes=sizes)


def run_methods(sc, seed, gens, methods=("SR", "SG", "DFPS"), prop_variant="abs", fst_variant="prose",
                accept="prose", interval=None, sim_kw=None, sa_kw=None, debug=False, X=None, rl_path=None, drain_factor=None):
    need_place = any(m in ("SR", "SG", "DFPS") for m in methods)
    x_sr, x_sg, info = (X if X is not None else initial_placements(sc, seed, gens, prop_variant)) if need_place else (None, None, {})
    out = {}
    for m in methods:
        t = time.time()
        if m in ("HEU", "RL"):                       # on-demand baselines: no initial placement (DFPS p.9-11)
            pol = HeuPolicy(seed=seed + 500) if m == "HEU" else load_rl_policy(rl_path, seed + 600)
            sim = OnDemandSim(sc, pol, seed=seed + 400, warmup=ASSUME["A21_warmup_s"], debug=debug,
                              **({} if drain_factor is None else dict(drain_factor=drain_factor)))
            res = sim.run()
            sim.check_invariants()
            res["wall_s"] = time.time() - t
            out[m] = res
            continue
        adj = SimulatedAnnealing(seed=seed + 300, accept=accept, vicinity=ASSUME["A08_vicinity_hops"],
                                 t_max=ASSUME["A11_sa_t_max"], alpha=ASSUME["A11_sa_alpha"],
                                 iterations=ASSUME["A11_sa_iterations"], **(sa_kw or {})) if m == "DFPS" else None
        sim = Sim(sc, x_sr if m == "SR" else x_sg, adjuster=adj, interval=interval, seed=seed + 400,
                  fst_variant=fst_variant, k_best=ASSUME["A07_matching_k_best"], n_trees=ASSUME["A07_matching_trees"],
                  warmup=ASSUME["A21_warmup_s"], debug=debug,
                  **({} if drain_factor is None else dict(drain_factor=drain_factor)), **(sim_kw or {}))
        res = sim.run()
        sim.check_invariants()
        res["wall_s"] = time.time() - t
        out[m] = res
    return out, info


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", default="uniform")
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--gens", type=int, default=ASSUME["A06_generations"])
    ap.add_argument("--ne", type=int, default=None)
    ap.add_argument("--nw", type=int, default=None)
    ap.add_argument("--duration", type=float, default=ASSUME["A21_run_length_s"])
    ap.add_argument("--max-tasks", type=int, default=14)
    ap.add_argument("--dags", default=None, help="JSON from experiments.extract_alibaba (real Alibaba DAGs)")
    ap.add_argument("--methods", default="SR,SG,DFPS")
    ap.add_argument("--rl", default=str(ROOT / "results" / "rl_policy.pt"))
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    dags = json.load(open(a.dags)) if a.dags else None
    sc = build_scenario(a.seed, a.kind, a.scale, ne=a.ne, n_workflows=a.nw, pool_size=ASSUME["A17_function_pool_size"],
                        duration_s=a.duration, synthetic_max_tasks=a.max_tasks, dags=dags)
    print("scenario:", {k: v for k, v in sc.meta.items() if k != "per_app_rate"})
    res, info = run_methods(sc, a.seed, a.gens, methods=tuple(a.methods.split(",")), rl_path=a.rl)
    print(json.dumps(info))
    for m, r in res.items():
        print(m, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()})
    if a.out:
        Path(a.out).write_text(json.dumps(dict(meta=sc.meta, info=info, results=res, assumptions=ASSUME)))
