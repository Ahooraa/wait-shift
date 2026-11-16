"""testbed.sebs_scenario.crn_uniform must equal numpy's default_rng([seed, req, task]).random() bit for bit (15 Nov 2026)."""
import random

import numpy as np

from testbed.sebs_scenario import crn_uniform


def test_crn_uniform_matches_numpy():
    r = random.Random(7)
    keys = [(r.randrange(0, 5000), r.randrange(0, 5_000_000), r.randrange(0, 400)) for _ in range(5000)]
    keys += [(0, 0, 0), (1, 0, 1), (7, 1, 0), (2**32 - 1,) * 3, (5, 2**32, 3), (5, 3, 2**32), (2**40, 1, 1)]
    for k in keys:
        assert crn_uniform(*k) == np.random.default_rng(list(k)).random(), k
