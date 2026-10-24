"""DFPS variants used by the headroom study (plan faas-edge-adaptation, Task 9/10).

AS_PRINTED : the method exactly as the paper prints it (errata E1-E3 left in; E4 is an obvious typo already fixed in sa.py).
B_STAR     : the plan's baseline B*: E1 (|FAN-FEN| in Eq. 3), E2 (Erlang-C with P0, rate vs time), E3 (Metropolis acceptance
             e^(delta/T) and best-so-far), E4 (corrected queue handling, always on). E5 (total weight vs critical path) is NOT
             part of B*: it is a method choice, available as match_objective="critical".
`period` (replacement interval T*) is tuned per trace family on dev data from PERIODS (Task 10).
"""
from __future__ import annotations

import yaml

from .constants import PAPER  # noqa: F401  (keeps the paper-constants guard imported)
from .sa import SimulatedAnnealing

PERIODS = (1, 2, 4, 8, 16, 32, 64)          # seconds, plan Task 10

VARIANTS = {
    "AS_PRINTED": dict(prop_variant="signed", fst_variant="literal", accept="literal", best_so_far=False),
    "B_STAR": dict(prop_variant="abs", fst_variant="prose", accept="prose", best_so_far=True),
}


def make_adjuster(variant, assume, seed=0):
    v = VARIANTS[variant]
    return SimulatedAnnealing(seed=seed, accept=v["accept"], best_so_far=v["best_so_far"], vicinity=assume["A08_vicinity_hops"],
                              t_max=assume["A11_sa_t_max"], alpha=assume["A11_sa_alpha"], iterations=assume["A11_sa_iterations"])


def sim_kwargs(variant, assume):
    v = VARIANTS[variant]
    return dict(fst_variant=v["fst_variant"], k_best=assume["A07_matching_k_best"], n_trees=assume["A07_matching_trees"],
                warmup=assume["A21_warmup_s"])
