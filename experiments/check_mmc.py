"""Statistical check of the simulator's queueing against M/M/c over several independent seeds."""
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dfps.queueing import fst  # noqa: E402
from tests.test_sim_queueing import one_node_system  # noqa: E402


def go(args):
    c, lam, seed, horizon = args
    r = one_node_system(c, 1.0, lam, horizon, seed=seed).run()
    return r["avg_makespan"], r["utilization"]


if __name__ == "__main__":
    c, lam = int(sys.argv[1]), float(sys.argv[2])
    seeds = range(100, 100 + int(sys.argv[3]))
    horizon = float(sys.argv[4])
    with ProcessPoolExecutor(8) as p:
        res = list(p.map(go, [(c, lam, s, horizon) for s in seeds]))
    m = np.array([r[0] for r in res])
    u = np.array([r[1] for r in res])
    print("per-seed makespan", np.round(m, 3))
    print("mean %.4f  sem %.4f  theory %.4f  | util mean %.4f theory %.4f" %
          (m.mean(), m.std(ddof=1) / np.sqrt(len(m)), fst(lam, 1.0, c, "prose"), u.mean(), lam / c))
