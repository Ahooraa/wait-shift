"""Operating envelope: where does the controller's advantage over the textbook stack live? (2026-10-25)

Extends what we already have (workflow_stress.py: 50/70/85% load x data scale 1/4/10, standard mix + four shapes) along the
two axes a reviewer flagged as the safest high-value addition: LOAD into overload (no admission control here -- this shows
raw behaviour, not what admission buys) and DATA INTENSITY to k = 20. No new mechanism; this is a map, not a build.
Scenarios are built fresh (traces.build_trace_scenario supports arbitrary rho, unlike the cached D1 pickles which only have
50/70/85%), the same way pattern_scenarios.py and admission_sweep.py do.

  LOADS  0.5, 0.7, 0.85, 0.92 (92% = approaching overload, no admission control)
  KS     1, 10, 20 (storage scales with k, as in workflow_stress.py, so storage pressure stays what it is at k=1)
  FAMS   F1 (Azure), F2 (Huawei)
  CTRLS  ours (FROZEN2), stack (HPA sizing + join-shortest-queue moves, our placement)
  48 runs (4 x 3 x 2 x 2), seed 1, full 900 s window. Trace on (dfps/diagnostics.py), so the pingpong stat (share of tasks
  moved >=2 times, added 2026-10-25) comes for free -- answers whether moves are being wasted re-moving the same task.
  python operating_envelope.py run [workers] | analyze
"""
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(ROOT))
import yaml  # noqa: E402

import d3s_headroom as d  # noqa: E402
import workflow_stress as w  # noqa: E402
from frozen2 import FROZEN2, MOVE_PERIOD_S  # noqa: E402

import dfps.traces as T  # noqa: E402
from dfps.nsga2 import PlacementProblem, nsga2  # noqa: E402
from dfps.o3s import O3SimAdjuster  # noqa: E402
from dfps.sim import Sim  # noqa: E402
from dfps.variants import make_adjuster, sim_kwargs  # noqa: E402

ASSUME = yaml.safe_load((ROOT / "config" / "assumptions.yaml").read_text(encoding="utf-8"))


def initial_layout(sc, seed, gens):
    """The NSGA-II layout other experiments start from (admission_sweep.py's helper: same result as experiments.run's
    initial_placements, minus its PyTorch import, which conflicts with this project's OpenMP runtime -- OMP error #15)."""
    prob = PlacementProblem(sc.network, sc.ecc, np.array([f.exec_time for f in sc.functions]), "abs")
    return nsga2(prob, np.random.default_rng(seed + 200), gens=gens)[2]

RUNS = ROOT / "results" / "envelope"
_ALIBABA = None


def alibaba_dags():
    global _ALIBABA
    if _ALIBABA is None:
        import json as _json
        _ALIBABA = _json.load(open(ROOT / "data" / "alibaba_dags_lt60s.json"))
    return _ALIBABA


LOADS = (0.5, 0.7, 0.85, 0.92)
KS = (1, 10, 20)
FAMS = ("F1", "F2")
CTRLS = {"ours": ("nosim", {}), "stack": ("hpa", dict(rebal_rule="jsq"))}
SEED = 1


def tag(fam, rho, k):
    return f"{fam}_r{rho}_k{k}"


def build(fam, rho, k):
    """Fresh scenario at an arbitrary rho (the cached D1 pickles only have 50/70/85%); scaled to data intensity k."""
    sc = T.build_trace_scenario(fam, rho, SEED, "dev", d.DURATION + d.WARMUP, 60.0, ne=80, n_workflows=15,
                                alibaba_dags=alibaba_dags(), pool_size=ASSUME["A17_function_pool_size"],
                                counts=T.load_counts(fam, "dev"))
    sc = w.scale(sc, k)
    X0 = initial_layout(sc, SEED, ASSUME["A06_generations"])
    return sc, X0


def one(args, duration=None, out=None):
    fam, rho, k, ctrl = args
    out = RUNS / f"{tag(fam, rho, k)}.{ctrl}.json" if out is None else out
    if out.exists():
        return str(out)
    try:
        assert np.__version__.startswith("1."), "run with the Anaconda interpreter (numpy 1.26)"
        T_ = json.loads((d.OUT / "g2_tstar.json").read_text())
        tstar = float(T_["families"][fam]["T_star"])
        sc, X0 = build(fam, rho, k)
        kw = sim_kwargs("B_STAR", ASSUME)
        kw.update(warmup=d.WARMUP, duration=d.DURATION if duration is None else duration, retry_min_interval=1.0, retry_max_attempts=10)
        cand, extra = CTRLS[ctrl]
        adj = O3SimAdjuster(make_adjuster("B_STAR", ASSUME, seed=SEED + 300), MOVE_PERIOD_S[fam], epoch=60.0, horizon=120.0, K=5,
                            seed=SEED + 800, warmup=d.WARMUP, blind=True, cand_mode=cand, churn=dict(FROZEN2, **extra))
        kw["interval"] = adj.next_interval
        t = time.time()
        sim = Sim(sc, X0, adjuster=adj, seed=SEED + 400, trace=True, **kw)
        r = sim.run()
        sim.check_invariants()
        r["wall_s"] = time.time() - t
        from dfps.diagnostics import summarize
        try:
            diag = summarize(sim)
        except Exception:
            diag = {}
        out.write_text(json.dumps(dict(fam=fam, rho=rho, k=k, ctrl=ctrl, result=r, diag=diag)))
        return str(out)
    except Exception:
        import traceback
        out.with_suffix(".err").write_text(traceback.format_exc())
        return str(out) + " FAILED"


def run(workers):
    RUNS.mkdir(parents=True, exist_ok=True)
    jobs = [(f, r, k, c) for r in LOADS for k in KS for f in FAMS for c in CTRLS]
    jobs = [j for j in jobs if not (RUNS / f"{tag(j[0], j[1], j[2])}.{j[3]}.json").exists()]
    jobs.sort(key=lambda j: (-j[1], j[2]))              # heaviest (highest load, then highest k) first
    print(f"{len(jobs)} runs", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        for r in ex.map(one, jobs):
            print("done", r, flush=True)


def analyze():
    rows = {}
    for f in RUNS.glob("*.json"):
        x = json.loads(f.read_text())
        rows[(x["fam"], x["rho"], x["k"], x["ctrl"])] = x
    print("%-4s %5s %3s | %8s %8s %7s | %6s %6s | %6s %6s | %5s %5s | %6s %6s" % (
        "fam", "load", "k", "ours P99", "stack P99", "gain", "cold_o", "cold_s", "mv/r_o", "mv/r_s", "pp_o", "pp_s", "unfin_o", "unfin_s"))
    for fam in FAMS:
        for rho in LOADS:
            for k in KS:
                a = rows.get((fam, rho, k, "ours"))
                b = rows.get((fam, rho, k, "stack"))
                if not a or not b:
                    continue
                ra, rb = a["result"], b["result"]
                gain = 100 * (rb["p99_makespan"] - ra["p99_makespan"]) / rb["p99_makespan"]
                da, db = a.get("diag", {}), b.get("diag", {})
                mv_a = ra["n_moved"] / max(1, ra["n_completed"])
                mv_b = rb["n_moved"] / max(1, rb["n_completed"])
                pp_a = da.get("all_pingpong", float("nan")) / max(da.get("all_moved_tasks", 1e-9), 1e-9) if da else float("nan")
                pp_b = db.get("all_pingpong", float("nan")) / max(db.get("all_moved_tasks", 1e-9), 1e-9) if db else float("nan")
                print("%-4s %5.2f %3d | %8.1f %8.1f %+6.1f%% | %6d %6d | %6.2f %6.2f | %4.0f%% %4.0f%% | %6d %6d" % (
                    fam, rho, k, ra["p99_makespan"], rb["p99_makespan"], gain, ra["cold_starts"], rb["cold_starts"],
                    mv_a, mv_b, 100 * pp_a, 100 * pp_b, ra["n_unfinished"], rb["n_unfinished"]))


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 4)
    else:
        analyze()
