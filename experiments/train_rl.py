"""Train the MOSEC-style RL baseline on TRAINING workloads (seeds >= 1000; the evaluation seeds are 1..999, so training and
test workloads never share a seed, network, workflow set or arrival sequence).

python -m experiments.train_rl --episodes 24 --duration 90 --out results/rl_policy.pt"""
from __future__ import annotations

import argparse
import itertools
import json
import time
from pathlib import Path

import numpy as np
import torch

from dfps.ondemand import OnDemandSim
from dfps.rl import MosecPolicy
from dfps.workload import build_scenario

ROOT = Path(__file__).resolve().parent.parent


def training_plan(episodes, base_seed=1000):
    kinds = list(itertools.product(["uniform", "pareto"], [0.5, 1.0, 1.5, 2.0]))
    return [(base_seed + i, *kinds[i % len(kinds)]) for i in range(episodes)]


def train(dags, episodes=24, duration=90.0, seed=0, log=print, calibrated=False):
    plan = training_plan(episodes)
    if calibrated:
        # calibrated reproduction scenario (2026-10-18): depth<=2 Alibaba jobs, one function per task; network size and number of
        # applications vary across episodes so the policy also sees the Fig. 7 range (training seeds only, >= 1000)
        nes, nws = (80, 80, 80, 80), (10, 15, 25, 35)   # NER compares whole states, so the node count stays 80 (as originally)
        scs = [build_scenario(s, kind, scale, ne=nes[i % 4], n_workflows=nws[(i // 4) % 4], duration_s=duration, dags=dags,
                              function_mapping="distinct") for i, (s, kind, scale) in enumerate(plan)]
    else:
        scs = [build_scenario(s, kind, scale, duration_s=duration, dags=dags) for s, kind, scale in plan]
    total = sum(sum(sc.workflows[w].n for _, w, _ in sc.arrivals) for sc in scs)
    pol = MosecPolicy(seed=seed, train=True, total_train_decisions=total)
    hist = []
    for ep, ((s, kind, scale), sc) in enumerate(zip(plan, scs)):
        t = time.time()
        sim = OnDemandSim(sc, pol, seed=s + 7, duration=duration, warmup=0.0, drain_factor=3.0)
        res = sim.run()
        hist.append(dict(episode=ep, seed=s, kind=kind, scale=scale, avg_makespan=res["avg_makespan"], n_completed=res["n_completed"],
                         cold_starts=res["cold_starts"], epsilon=pol.epsilon(), grad_steps=pol.n_grad,
                         loss=float(np.mean(pol.losses[-500:])) if pol.losses else None, wall_s=time.time() - t))
        log(json.dumps(hist[-1]))
    return pol, hist


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=int, default=24)
    ap.add_argument("--duration", type=float, default=90.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--dags", default=str(ROOT / "data" / "alibaba_dags_lt60s.json"))
    ap.add_argument("--out", default=str(ROOT / "results" / "rl_policy.pt"))
    ap.add_argument("--calibrated", action="store_true", help="train on the calibrated reproduction scenario")
    a = ap.parse_args()
    if a.calibrated:
        import sys
        sys.path.insert(0, str(ROOT / "output" / "data-analysis"))
        from calibrate_fig5 import dag_depth
        dags = [d for d in json.load(open(ROOT / "data" / "alibaba_dags_lt60s_min1.json")) if dag_depth(d) <= 2]
    else:
        dags = json.load(open(a.dags))
    pol, hist = train(dags, a.episodes, a.duration, a.seed, calibrated=a.calibrated)
    torch.save(pol.q.state_dict(), a.out)
    Path(a.out).with_suffix(".json").write_text(json.dumps(hist))
