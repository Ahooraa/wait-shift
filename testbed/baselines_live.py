"""The comparison systems of the testbed experiment, built once for the simulator (the reference) and for the testbed (DESIGN.md, phase 4b).

`build_rl`: the RL baseline (MOSEC, Yang et al. 2025, adapted to the DFPS model: `dfps/rl.py`), an on-demand system: no initial layout, every task is
placed when it becomes ready by a learned Q-network that scores each node. Constructed as in `experiments/run.py` (`load_rl_policy`, policy seed+600,
simulator seed+400). The policy scores ONE node from task and node features with shared weights, so the same checkpoint serves any node count.

Checkpoint: `results/rl_policy.pt` (CAP-U, empty start) by default. It was trained on the paper-style scenarios, NOT on SeBS-Flow, so on SeBS it is the
paper's baseline applied to a workload it has not seen. Whether the pre-registered comparison trains it on SeBS development seeds instead is a decision
for the pre-registration (knowledge/synthesis/testbed-preregistration.md).

On the testbed the policy's decision time (a forward pass over all nodes, about 0.6 ms per task in the simulator) is real wall time on the hub.
"""
from __future__ import annotations

import sys
import time
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dfps.ondemand import OnDemandSim          # noqa: E402

RL_CKPT = ROOT / "results" / "rl_policy.pt"


def load_rl(path, seed):
    from experiments.run import load_rl_policy
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)         # torch.load's pickle notice: our own checkpoint, as in every earlier RL run
        return load_rl_policy(str(path), seed + 600)


def build_rl(sc, seed, *, warmup, duration, sim_cls=OnDemandSim, ckpt=RL_CKPT, **extra):
    """(sim, None) for one run of the RL baseline on scenario `sc`. `sim_cls` is `OnDemandSim` or `LiveOnDemandSim`; `extra` goes to its constructor
    (link=, drain_s=, exec_sampler=, record_requests=, ...). The second value keeps the shape of `frozen_live.build` (no adjuster here)."""
    return sim_cls(sc, load_rl(ckpt, seed), seed=seed + 400, duration=duration, warmup=warmup, **extra), None


def warm_up_rl(sc, seed=1, seconds=40.0, ckpt=RL_CKPT):
    """One short plain-simulator run, so the network is loaded and torch's first-call costs are paid BEFORE a live run."""
    t0 = time.time()
    sim, _ = build_rl(sc, seed, warmup=min(10.0, seconds / 3), duration=seconds, ckpt=ckpt)
    sim.run()
    return time.time() - t0
