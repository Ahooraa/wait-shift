"""Model objects named after the paper's notation (Table 1, p.4)."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass(frozen=True)
class Function:
    """f_l: exec_time = mu_l, the average execution time (Q-1); cold_start = cold-start delay."""
    id: int
    exec_time: float
    cold_start: float


@dataclass
class Workflow:
    """w_i = <T_i, S_i>: tasks 0..n-1 in topological order; edges carry states s_ij with size SS(s_ij) in MB."""
    id: int
    n: int
    parents: list
    children: list
    ft: list           # FT(t_ij): function type of each task
    ss: dict           # (u, v) -> SS(s_uv) in MB
    input_size: float  # size of the state the user sends to every root task
    roots: list = field(default_factory=list)

    def __post_init__(self):
        self.roots = [t for t in range(self.n) if not self.parents[t]]

    @staticmethod
    def from_edges(id, n, edges, ft, ss, input_size):
        parents = [[] for _ in range(n)]
        children = [[] for _ in range(n)]
        for u, v in edges:
            parents[v].append(u)
            children[u].append(v)
        return Workflow(id, n, parents, children, list(ft), dict(ss), input_size)

    def input_total(self, t):
        """Total size of the input states task t must store at its node (Q-2)."""
        if not self.parents[t]:
            return self.input_size
        return sum(self.ss[(u, t)] for u in self.parents[t])


@dataclass
class Scenario:
    """Everything an experiment needs; built by workload.py."""
    functions: list
    workflows: list
    network: object
    ecc: np.ndarray        # container capacity per edge node (capacity units; GB-equivalent once fw is heterogeneous)
    esc: np.ndarray        # storage capacity per edge node (MB)
    arrivals: list         # (time_s, workflow_id, origin_node), sorted by time
    meta: dict = field(default_factory=dict)
    # 2026-10-27 (problem-scope.md S2, "Containers"): per-function container resource weight w_f, in the same units
    # as ecc. None/all-ones reproduces DFPS's uniform-slot model exactly (every existing scenario and placement
    # algorithm implicitly assumes this); a heterogeneous fw turns ecc's row-sum constraint into a continuous
    # knapsack. Defaulted here, not generated yet -- the weight distribution shape is still open (problem-scope.md
    # S10, "Container-weight distribution shape").
    fw: np.ndarray = None  # per-function container weight; None -> all-ones in __post_init__

    def __post_init__(self):
        if self.fw is None:
            self.fw = np.ones(len(self.functions))
