"""Why does the request mover still move tasks under FROZEN-5? Simulator only, development seeds 1-3, the planned cells.

Every call of `Sim.relocate` is one move. It is tagged with
  * who called it: the request mover (periodic pass), or `_reroute` (a task whose node lost its container at a re-layout);
  * the task's in-degree: root (no parent), single parent (late-bound under FROZEN-5), join (two or more parents);
  * whether the task had been moved before (a repeat move);
  * the task's age in the queue when it was moved (seconds since it first joined a queue).
    ~/venv-dfps/bin/python testbed/diag/moves_by_cause.py [seeds, default 1,2,3] > ~/testbed-results/moves_by_cause.txt
Run it when no live run is going: it uses a core for a few minutes."""
import collections
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from testbed import frozen_live as FL, sebs_scenario as S               # noqa: E402
from dfps.nsga2 import PlacementProblem                                 # noqa: E402
from dfps.sim import Sim                                                # noqa: E402

CELLS = [("690.ml", 0.56, None, 60, 300), ("660.map-reduce", 0.45, None, 60, 300), ("650.vid", 0.7, None, 60, 600),
         ("6200.trip-booking", 0.7, 42.0, 60, 300), ("680.excamera", 0.5, None, 180, 1800), ("680.excamera", 0.7, None, 180, 1800)]


class Tagged(Sim):
    def _reroute(self, run):
        self._why = "re-layout"
        try:
            super()._reroute(run)
        finally:
            self._why = "mover"

    def relocate(self, run, k_new):
        if self.in_window(self.now):
            wf, t = run.req.wf, run.task
            n_par = len(wf.parents[t])
            kind = "root" if n_par == 0 else "single parent" if n_par == 1 else "join"
            age = self.now - (run.t_first if run.t_first is not None else self.now)
            self.__dict__.setdefault("_moves", []).append((getattr(self, "_why", "mover"), kind, run.n_moves > 0, age))
        super().relocate(run, k_new)


def main():
    seeds = [int(x) for x in (sys.argv[1] if len(sys.argv) > 1 else "1,2,3").split(",")]
    for app, rho, cap, warm, window in CELLS:
        dur = warm + window
        print(f"\n{app} @ {rho}  (seeds {seeds}; moves inside the window, summed over seeds)")
        for arm in ("frozen4", "frozen5"):
            mv, n_req, n_task_kinds = [], 0, collections.Counter()
            for seed in seeds:
                sc, samp = S.build(seed, apps=[app], rho=rho, ne=10, duration_s=dur, rate_cap=cap)
                X0 = PlacementProblem(sc.network, sc.ecc, np.array([f.exec_time for f in sc.functions])).random(np.random.default_rng(seed))
                sim, _ = FL.build(sc, X0, seed, arm=arm, warmup=warm, duration=dur, exec_sampler=samp, sim_cls=Tagged)
                r = sim.run()
                mv += sim.__dict__.get("_moves", [])
                n_req += r["n_completed"]
                for t in range(sc.workflows[0].n):
                    n_task_kinds[("root" if not sc.workflows[0].parents[t] else "single parent" if len(sc.workflows[0].parents[t]) == 1 else "join")] += r["n_completed"]
            tot = max(1, len(mv))
            by = collections.Counter(m[0] for m in mv); kd = collections.Counter(m[1] for m in mv)
            rep = sum(m[2] for m in mv); ages = np.array([m[3] for m in mv]) if mv else np.zeros(1)
            per_task = {k: kd[k] / max(1, n_task_kinds[k]) for k in ("root", "single parent", "join")}
            print(f"  {arm}: {len(mv):7d} moves, {len(mv) / n_req:5.2f} per request | caused by: mover {100 * by['mover'] / tot:3.0f}%, re-layout re-route {100 * by['re-layout'] / tot:3.0f}% | "
                  f"task kind: root {100 * kd['root'] / tot:3.0f}%, single parent {100 * kd['single parent'] / tot:3.0f}%, join {100 * kd['join'] / tot:3.0f}% | "
                  f"moves per task of that kind: root {per_task['root']:.2f}, single {per_task['single parent']:.2f}, join {per_task['join']:.2f} | "
                  f"repeat moves {100 * rep / tot:3.0f}% | age when moved: median {np.median(ages):.1f} s, p90 {np.percentile(ages, 90):.1f} s", flush=True)


if __name__ == "__main__":
    main()
