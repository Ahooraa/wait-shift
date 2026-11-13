"""Audit of B* (our rebuild of DFPS, errata E1-E4 corrected): is its churn DFPS's own behaviour, or something of ours? Simulator only, development seeds 1 and 2.

Question behind it (13 Nov 2026): a referee may call B* a weak reimplementation. In the first live runs B* made 20-60 times the cold starts of F5. Three checks, each readable on its own:
  A. WHERE do B*'s cold starts come from (window only)? Annealer replacements of an idle / cold / busy container, deferred starts, anything else; how many container changes per round,
     and what share of the 4 s rounds change anything; the annealer's own counters (rejected / reverted / accepted worse / accepted better).
  B. Is the period T* = 4 s a bad choice? P50, P99 and cold starts for T* in (2, 4, 8, 16, 64 s) and for NO annealing at all (static layout: the initial layout and the matcher only).
  C. Is the matcher objective (E5: total weight, as printed, versus critical path) the issue? B* with match_objective="critical" at T* = 4 s.
Nothing here changes B*, F5 or any stored result; the live results of 12-13 Nov stay as they are. Same scenarios, arrivals and random initial layout as the live runs.

    ~/venv-dfps/bin/python testbed/diag/bstar_audit.py run      # about 30-40 min, one core; run when no live run is going
    ~/venv-dfps/bin/python testbed/diag/bstar_audit.py report > ~/testbed-results/bstar_audit.txt
"""
import collections
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
OUT = Path.home() / "testbed-results" / "bstar_audit"
CELLS = [("690.ml", 0.56, None, 60, 300), ("660.map-reduce", 0.45, None, 60, 300), ("650.vid", 0.7, None, 60, 600), ("680.excamera", 0.7, None, 180, 1800)]
SEEDS = (1, 2)
SWEEP_APPS = ("690.ml", "660.map-reduce", "650.vid")            # ExCamera only at T* = 4 (the sweep would triple an already long cell)
PERIODS = {"T2": 2.0, "T4": 4.0, "T8": 8.0, "T16": 16.0, "T64": 64.0, "static": 1e7}
STATE = {0: "idle", 1: "cold", 2: "busy"}


def tagged_cls():
    from dfps.sim import Sim

    class Tagged(Sim):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            self.tag = collections.Counter()           # window only
            self.rounds, self.round_changes = 0, []
            self._ctx = "other"

        def apply_solution(self, sol):
            before = self.cold_starts
            self._ctx = "apply"
            try:
                changed = int(sum(max(0, int(x)) for x in (sol.cnt - self.cnt).clip(min=0).ravel()))
                super().apply_solution(sol)
            finally:
                self._ctx = "other"
            if self.in_window(self.now):
                self.rounds += 1
                self.round_changes.append(changed)

        def _convert(self, ins, g):
            if self.in_window(self.now):
                self.tag[("swap now" if self._ctx == "apply" else "swap after a busy container finished", STATE.get(ins.state, "?"))] += 1
            super()._convert(ins, g)

        def _new_instance(self, k, f):
            if self.in_window(self.now):
                self.tag[("add in the round" if self._ctx == "apply" else "deferred add" if self._ctx == "pending" else "add elsewhere", "-")] += 1
            super()._new_instance(k, f)

        def _start_pending(self, k):
            old, self._ctx = self._ctx, "pending"
            try:
                super()._start_pending(k)
            finally:
                self._ctx = old

    return Tagged


def one(app, rho, cap, warm, window, seed, name, period, objective):
    out = OUT / f"{app}.s{seed}.{name}.json"
    if out.exists():
        return
    from testbed import bstar_live as BSL, sebs_scenario as S
    from dfps.nsga2 import PlacementProblem
    dur = warm + window
    sc, samp = S.build(seed, apps=[app], rho=rho, ne=10, duration_s=dur, rate_cap=cap)
    X0 = PlacementProblem(sc.network, sc.ecc, np.array([f.exec_time for f in sc.functions])).random(np.random.default_rng(seed))
    extra = {} if objective == "sum" else {"match_objective": objective}
    sim, adj = BSL.build(sc, X0, seed, warmup=warm, duration=dur, exec_sampler=samp, sim_cls=tagged_cls(), period=period, **extra)
    r = sim.run()
    rc = np.array(sim.round_changes) if sim.round_changes else np.zeros(1)
    n_containers = int(np.sum(sc.ecc))
    rec = {"app": app, "seed": seed, "name": name, "period": period, "objective": objective,
           "p50": r["p50_makespan"], "p99": r["p99_makespan"], "cold": int(r["cold_starts"]), "moved": int(r.get("n_moved") or 0),
           "n_completed": int(r["n_completed"]), "n_unfinished": int(r["n_unfinished"]), "containers": n_containers,
           "rounds": sim.rounds, "rounds_changing": int((rc > 0).sum()), "changes_per_round": float(rc.mean()),
           "changes_p90": float(np.percentile(rc, 90)), "tags": {f"{a} | {b}": int(v) for (a, b), v in sim.tag.items()},
           "sa": {k: (float(v) if isinstance(v, (int, float, np.floating)) else v) for k, v in adj.stats.items()}}
    OUT.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, default=float))
    print(f"{app} s{seed} {name}: P99 {rec['p99']:.2f} cold {rec['cold']}", flush=True)


def run():
    for app, rho, cap, warm, window in CELLS:
        for seed in SEEDS:
            one(app, rho, cap, warm, window, seed, "T4", PERIODS["T4"], "sum")
    for app, rho, cap, warm, window in CELLS:
        if app not in SWEEP_APPS:
            continue
        for seed in SEEDS:
            for name in ("static", "T2", "T8", "T16", "T64"):
                one(app, rho, cap, warm, window, seed, name, PERIODS[name], "sum")
            one(app, rho, cap, warm, window, seed, "T4.critical", PERIODS["T4"], "critical")
    print("finished", flush=True)


def load(app, name):
    rs = [json.loads((OUT / f"{app}.s{s}.{name}.json").read_text()) for s in SEEDS if (OUT / f"{app}.s{s}.{name}.json").exists()]
    return rs


def report():
    print("B* audit (simulator, seeds 1 and 2 averaged, window only)\n")
    print("A. Where B*'s cold starts come from (T* = 4 s)")
    for app, *_ in CELLS:
        rs = load(app, "T4")
        if not rs:
            continue
        tot = collections.Counter()
        for r in rs:
            tot.update(r["tags"])
        cold = sum(r["cold"] for r in rs)
        n = len(rs)
        print(f"\n  {app}: cold starts {cold / n:.0f}/run, containers {rs[0]['containers']}, rounds {np.mean([r['rounds'] for r in rs]):.0f}/run, "
              f"rounds that change anything {100 * sum(r['rounds_changing'] for r in rs) / max(1, sum(r['rounds'] for r in rs)):.0f}%, "
              f"container changes per round mean {np.mean([r['changes_per_round'] for r in rs]):.1f} (p90 {np.mean([r['changes_p90'] for r in rs]):.0f})")
        for k, v in sorted(tot.items(), key=lambda kv: -kv[1]):
            print(f"      {k:55s} {v / n:8.0f}/run  {100 * v / max(1, cold):4.0f}%")
        sa = rs[0]["sa"]
        print("      annealer counters (seed 1, whole run): " + ", ".join(f"{k} {int(sa[k])}" for k in ("iterations", "rejected", "reverted", "accepted_worse", "accepted_better") if k in sa))
    print("\nB. Replacement period and no annealing (P50 s / P99 s / cold starts / moves; seeds averaged)")
    names = ["static", "T2", "T4", "T8", "T16", "T64", "T4.critical"]
    print(f"  {'':16}" + "".join(f"{n:>26}" for n in names))
    for app in SWEEP_APPS:
        cells = []
        for nme in names:
            rs = load(app, nme)
            cells.append("-" if not rs else f"{np.mean([r['p50'] for r in rs]):.2f}/{np.mean([r['p99'] for r in rs]):.1f}/{np.mean([r['cold'] for r in rs]):.0f}/{np.mean([r['moved'] for r in rs]):.0f}")
        print(f"  {app:16}" + "".join(f"{c:>26}" for c in cells))
    print("\n  Reading: if a period or the static layout beats T* = 4 s by a wide margin, T* = 4 s was a poor choice for these cells; if B* stays far behind F5 whatever T*, the gap is not the period.")


if __name__ == "__main__":
    {"run": run, "report": report}[sys.argv[1] if len(sys.argv) > 1 else "run"]()
