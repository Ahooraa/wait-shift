"""Calibrate the open (unspecified) settings of the DFPS reproduction against the paper's Fig. 5 (user request 2026-10-17:
"a valid and trustworthy re-implementation, as close as possible to the paper's results").

  python -I output/data-analysis/calibrate_fig5.py run [--stage screen] [--workers 10]
  python -I output/data-analysis/calibrate_fig5.py analyze [--stage screen]

Targets: output/data-analysis/results/paper_fig5_digitized.json (read by eye from Fig. 5). Fig. 5 ONLY is used for calibration;
Figs. 6 and 7 stay held out as an independent check of the chosen setting.
Only settings the paper leaves open are varied; Table 2 values and the DFPS algorithm (B*) are never tuned.
Points: arrival scale 0.25, 1.0, 2.0 x Uniform/Pareto x seeds 1-2; methods SR, SG(|.|), B*; one job per scenario.

Stage "screen": one factor at a time from the current baseline (A-13 exponential, A-16 shared pool of 30, load factor 1):
  base | load 0.5 | load 0.25 | pool 15 | pool 60 | distinct functions | deterministic execution times |
  single-task Alibaba jobs included (the base excludes them, min 2 tasks; the paper only says "under one minute")
Loss: mean |log(ours / paper)| of the mean makespan over SR, SG, DFPS and the 6 points (secondary: utilisation in points,
DFPS cold starts), plus the paper's qualitative pattern checks.
"""
from __future__ import annotations

import argparse
import json
import pickle
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402
from dfps.sim import Sim  # noqa: E402
from dfps.variants import make_adjuster, sim_kwargs  # noqa: E402
from dfps.workload import build_scenario  # noqa: E402

ASSUME = yaml.safe_load((ROOT / "config" / "assumptions.yaml").read_text(encoding="utf-8"))   # no PyTorch import
RUNS = ROOT / "results" / "calibration_fig5"
OUT = ROOT / "output" / "data-analysis" / "results"
PAPER = json.loads((OUT / "paper_fig5_digitized.json").read_text())
SCALES, KINDS, SEEDS = (0.25, 1.0, 2.0), ("uniform", "pareto"), (1, 2)
METHODS = ("SR", "SG", "DFPS")

BASE = dict(load=1.0, pool=30, mapping="pool", exec="exponential", dags="min2", maxdepth=None)
DAG_FILES = {"min2": "alibaba_dags_lt60s.json", "min1": "alibaba_dags_lt60s_min1.json"}
STAGES = {
    "screen": {
        "base": {},
        "load0.5": dict(load=0.5),
        "load0.25": dict(load=0.25),
        "pool15": dict(pool=15),
        "pool60": dict(pool=60),
        "distinct": dict(mapping="distinct"),
        "det_exec": dict(exec="deterministic"),
        "single_task_jobs": dict(dags="min1"),
    },
    # combination round (2026-10-17), chosen from the full screen: load x0.25 fits the high-load end and the Pareto ranking;
    # the low-load floor (Uniform x0.25 about 24 s vs 12 s) needs shorter workflows, so single-task jobs and fixed execution
    # times are combined with a low load factor.
    "combo": {
        "L025_single": dict(load=0.25, dags="min1"),
        "L0125_single": dict(load=0.125, dags="min1"),
        "L035_single": dict(load=0.35, dags="min1"),
        "L025_single_det": dict(load=0.25, dags="min1", exec="deterministic"),
        "L025_det": dict(load=0.25, exec="deterministic"),
        "L025_single_distinct": dict(load=0.25, dags="min1", mapping="distinct"),
    },
    # depth x mapping at the paper's own load (2026-10-17): the makespan breakdown showed the low-load floor is execution along
    # a critical path about 3 tasks deep; the paper's utilisation (28-45% Uniform) says its load is not lower than ours, so the
    # load factor is NOT varied here. maxdepth = longest chain of tasks allowed in a sampled Alibaba DAG.
    "depth": {
        "d2_any_pool": dict(dags="min1", maxdepth=2),
        "d2_any_distinct": dict(dags="min1", maxdepth=2, mapping="distinct"),
        "d2_multi_pool": dict(maxdepth=2),
        "d2_multi_distinct": dict(maxdepth=2, mapping="distinct"),
        "d3_multi_pool": dict(maxdepth=3),
        "d3_multi_distinct": dict(maxdepth=3, mapping="distinct"),
    },
}


def cfg_of(name, stage):
    return dict(BASE, **STAGES[stage][name])


def job(args):
    try:
        return _job(args)
    except Exception:
        import traceback
        Path(args[1]).with_suffix(".err").write_text(traceback.format_exc())
        return args[1] + " FAILED"


def _job(args):
    cfg, out_path, kind, scale, seed = args
    if Path(out_path).exists():
        return out_path
    sc = pickle.load(open(Path(out_path).with_suffix(".pkl"), "rb"))
    X_sr, X_sg = placements(sc, seed)
    kw = sim_kwargs("B_STAR", ASSUME)
    if cfg["exec"] == "deterministic":
        mu = np.array([f.exec_time for f in sc.functions])
        kw["exec_sampler"] = lambda f, rng: float(mu[f])
    g2_over = kind == "pareto" and scale >= 0.5 or scale >= 2.0             # same overload handling as G2
    retry, cap = (1.0, 10) if g2_over else (0.0, None)
    res = {}
    for m in METHODS:
        t = time.time()
        adj = make_adjuster("B_STAR", ASSUME, seed=seed + 300) if m == "DFPS" else None
        sim = Sim(sc, X_sr if m == "SR" else X_sg, adjuster=adj, seed=seed + 400, retry_min_interval=retry,
                  retry_max_attempts=cap, **kw)
        r = sim.run()
        sim.check_invariants()
        r["wall_s"] = time.time() - t
        res[m] = {k: r[k] for k in ("avg_makespan", "utilization", "cold_starts", "n_completed", "n_unfinished", "p99_makespan", "wall_s")}
    Path(out_path).write_text(json.dumps(dict(cfg=cfg, kind=kind, scale=scale, seed=seed, n_functions=len(sc.functions),
                                              mean_tasks=sc.meta["mean_tasks"], total_rate=sc.meta["total_rate_per_s"], results=res)))
    return out_path


def placements(sc, seed):
    """SR and SG placements exactly as in G2 and the figure runs."""
    from experiments.run import initial_placements   # imports PyTorch; fine here (G2 used the same import with Sim)
    x_sr, x_sg, _ = initial_placements(sc, seed, ASSUME["A06_generations"], "abs")
    return x_sr, x_sg


def dag_depth(d):
    """Number of tasks on the longest chain (Kahn's topological order; edges need not be index-ordered)."""
    n = d["n"]
    ch, indeg = [[] for _ in range(n)], [0] * n
    for u, v in d["edges"]:
        ch[u].append(v)
        indeg[v] += 1
    lv, stack = [1] * n, [i for i in range(n) if indeg[i] == 0]
    while stack:
        u = stack.pop()
        for v in ch[u]:
            lv[v] = max(lv[v], lv[u] + 1)
            indeg[v] -= 1
            if indeg[v] == 0:
                stack.append(v)
    return max(lv)


def run(a):
    RUNS.mkdir(parents=True, exist_ok=True)
    jobs = []
    for name in STAGES[a.stage]:
        cfg = cfg_of(name, a.stage)
        for kind in KINDS:
            for s in SCALES:
                for seed in SEEDS:
                    jobs.append((cfg, str(RUNS / f"{a.stage}_{name}_{kind}_x{s}_s{seed}.json"), kind, s, seed))
    for dkey in DAG_FILES:                                                    # build scenarios once per DAG file (big JSON)
        todo = [j for j in jobs if j[0]["dags"] == dkey and not Path(j[1]).exists() and not Path(j[1]).with_suffix(".pkl").exists()]
        if not todo:
            continue
        dags_all = json.load(open(ROOT / "data" / DAG_FILES[dkey]))
        by_depth = {}
        for cfg, out_path, kind, s, seed in todo:
            md = cfg.get("maxdepth")
            if md not in by_depth:
                by_depth[md] = dags_all if md is None else [d for d in dags_all if dag_depth(d) <= md]
            dags = by_depth[md]
            sc = build_scenario(seed, kind, s * cfg["load"], duration_s=ASSUME["A21_run_length_s"], dags=dags,
                                pool_size=cfg["pool"], function_mapping=cfg["mapping"])
            pickle.dump(sc, open(Path(out_path).with_suffix(".pkl"), "wb"))
        del dags_all, by_depth, dags
    jobs.sort(key=lambda j: -j[3])                                            # heavy points first
    print(len(jobs), "jobs", flush=True)
    with ProcessPoolExecutor(a.workers) as ex:
        for d in ex.map(job, jobs):
            print("done", d, flush=True)


def paper_at(kind, metric, m, s):
    return PAPER[kind][metric][m][PAPER["x_scale"].index(s)]


def analyze(a):
    out = {}
    for name in STAGES[a.stage]:
        rows = {}
        for f in RUNS.glob(f"{a.stage}_{name}_*.json"):
            d = json.loads(f.read_text())
            for m, r in d["results"].items():
                rows.setdefault((d["kind"], d["scale"], m), []).append(r)
        if not rows:
            continue
        err_mk, err_ut, table = [], [], {}
        for (kind, s, m), rs in sorted(rows.items()):
            mk = float(np.mean([r["avg_makespan"] for r in rs]))
            ut = float(np.mean([r["utilization"] for r in rs]) * 100)
            cs = float(np.mean([r["cold_starts"] for r in rs]))
            p_mk, p_ut = paper_at(kind, "makespan", m, s), paper_at(kind, "util", m, s)
            err_mk.append(abs(np.log(mk / p_mk)))
            err_ut.append(abs(ut - p_ut))
            table[f"{kind}_x{s}_{m}"] = dict(ours=dict(makespan=round(mk, 1), util=round(ut, 1), cold=round(cs)),
                                             paper=dict(makespan=p_mk, util=p_ut, cold=paper_at(kind, "cold", m, s)), n=len(rs))
        g = lambda kind, s, m: table.get(f"{kind}_x{s}_{m}", {}).get("ours", {}).get("makespan", np.nan)  # noqa: E731
        checks = {
            "uniform_static_close_to_dfps_at_x1": bool(g("uniform", 1.0, "SR") <= 1.5 * g("uniform", 1.0, "DFPS")),
            "pareto_rank_dfps_sg_sr_all": all(g("pareto", s, "DFPS") < g("pareto", s, "SG") < g("pareto", s, "SR") for s in SCALES),
            "makespan_rises_with_scale_all": all(g(k, SCALES[i], m) < g(k, SCALES[i + 1], m) for k in KINDS for m in METHODS
                                                 for i in range(len(SCALES) - 1)),
        }
        out[name] = dict(cfg=cfg_of(name, a.stage), loss_log_makespan=float(np.mean(err_mk)),
                         factor=float(np.exp(np.mean(err_mk))), util_abs_err_points=float(np.mean(err_ut)),
                         checks=checks, cells=table)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"calibration_fig5_{a.stage}.json").write_text(json.dumps(out, indent=1))
    for name, v in sorted(out.items(), key=lambda kv: kv[1]["loss_log_makespan"]):
        print(f"{name:10s} makespan off by x{v['factor']:.2f} (mean |log|) | util err {v['util_abs_err_points']:.1f} pts | checks {v['checks']}")
        for k, c in v["cells"].items():
            print(f"    {k:22s} ours {c['ours']['makespan']:7.1f} s {c['ours']['util']:5.1f}% {c['ours']['cold']:6d} | paper {c['paper']['makespan']:5} s {c['paper']['util']:5}% {c['paper']['cold']:5}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "analyze"])
    ap.add_argument("--stage", default="screen")
    ap.add_argument("--workers", type=int, default=10)
    a = ap.parse_args()
    run(a) if a.cmd == "run" else analyze(a)
