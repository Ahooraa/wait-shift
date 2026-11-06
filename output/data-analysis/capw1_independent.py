"""Independent baseline systems under CAP-W1 (protocol: knowledge/synthesis/independent-baselines-capw1.md, 5 Nov 2026).
Each system runs on its own mechanism, none of ours (no re-layout of ours, no request mover, FIFO queues) except where stated.
  faaspr_rs  the same with the per-node input-state storage relaxed x1000 (sensitivity arm: the paper has a remote store, no per-node budget)
  faaspr_el  audit arm (5 Nov 2026, development cases only): the scaler's counts are used as they are, the cluster is not filled to 100%
             run_job also takes an optional 6th element, the LP rate window in s (default 30, the held-out run's value)
  faaspr   FaaSPR (Jia et al. 2025), "FP-2": the stock autoscaler every 60 s (HPA sizing, as for every independent system; the paper: platforms
           "deploy more instances than concurrency"), weighted horizontal/vertical-grouping + migration-minimising placement, per-workflow
           multi-stage LP routing with the exact x-index threshold
  ga_p     Graph-Aware (Liang et al. 2026) on substrate S-P: stock HPA sizing every 60 s (ceil(load / 0.8)) + our data-affinity placement,
           no request mover; alpha 1, beta 1.1 (top of the paper's own sweep), no tuning
  heft_p   HEFT-like dispatcher on S-P
  ga_s     Graph-Aware on substrate S-S: the NSGA-II start layout only, no re-layout
  heft_s   HEFT-like on S-S
  ga_p2, heft_p2, ga_s2, heft_s2   the same four with the v2 tie-break (5 Nov 2026, after the audit): exact ties go to the lowest queue estimate, then at random,
           not to the lowest node index. The v1 arms are kept unchanged beside them.
Held-out cases: F1/F2 x rho 0.5/0.7/0.85 x seeds 7-10 (scenarios prepared by capw1_light.prep_job, same weights and normalisation).
  python capw1_independent.py prep [workers]                       scenarios for seeds 7-10
  python capw1_independent.py run  [workers] [seeds] [arm ...]     e.g. run 6 1,2,3 faaspr   (default seeds 7-10, all arms)
  python capw1_independent.py smoke [arm]                          one case, 150 s, health numbers
"""
import json
import os
import pickle
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
OUT = ROOT / "results" / "capW1_independent"
W1 = ROOT / "results" / "capW1_light"
DURATION, WARMUP = 900.0, 60.0
CAP = "CAP-W1"
ARMS = ("faaspr", "faaspr_rs", "ga_p", "heft_p", "ga_s", "heft_s")


def tags(seeds):
    return [f"{f}_r{r}_s{s}" for f in ("F1", "F2") for r in (0.5, 0.7, 0.85) for s in seeds]


def run_job(args):
    tg, arm, duration, out_dir, *rest = args
    n_paths = int(rest[0]) if rest else int(os.environ.get("FP_PATHS", 300))
    out = Path(out_dir) / f"{tg}.{arm}.json"
    if out.exists():
        return str(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        import numpy as _np
        assert _np.__version__.startswith("1."), "run with the Anaconda interpreter (numpy 1.26)"
        import yaml
        from dfps import dispatchers as D
        from dfps.controllers import FAASPR_W_DIAG
        for _k in list(FAASPR_W_DIAG):                   # per-run counters (a pool worker runs several jobs; until 5 Nov 2026 they accumulated)
            FAASPR_W_DIAG[_k] = 0
        from dfps.o3s import O3SimAdjuster
        from dfps.sim import Sim
        from dfps.variants import make_adjuster, sim_kwargs
        A = yaml.safe_load((ROOT / "config" / "assumptions.yaml").read_text(encoding="utf-8"))
        P = pickle.load(open(W1 / f"{tg}.sc.pkl", "rb"))
        sc, X0 = P["sc"], P["X0"]
        assert sc.meta.get("capacity_model") == CAP
        seed = int(tg.split("_s")[1])
        kw = sim_kwargs("B_STAR", A)
        kw.update(warmup=WARMUP, duration=duration, retry_min_interval=1.0, retry_max_attempts=10)
        tie = "fst" if arm.endswith("2") else "index"       # ga_*2 / heft_*2: tie-break v2 (dfps.dispatchers.break_ties); the other arms keep v1 (lowest node index)
        router, info = None, dict(tie_break=("lowest queue estimate, then random" if tie == "fst" else "lowest node index (v1)"))
        t0 = time.time()
        if arm in ("faaspr", "faaspr_rs", "faaspr_el"):
            if arm == "faaspr_rs":                       # storage-relaxed sensitivity arm: per-node input-state storage not binding (paper: remote store)
                import copy
                sc = copy.copy(sc)
                sc.esc = np.asarray(sc.esc, dtype=float) * 1000.0
            win = float(rest[1]) if len(rest) > 1 else 30.0     # rate window of the LP input (audit sensitivity; the held-out run used 30 s)
            router = D.FaaSPRRouterPaper(seed=seed + 900, n_paths=n_paths, window=win)
            churn = dict(no_inner=True, placement="faaspr_w")
            if arm == "faaspr_el":                       # audit arm (5 Nov 2026): the scaler's own counts, the cluster is NOT filled to 100% (paper: the platform scales to demand)
                churn["elastic"] = True
            cand, horizon = "hpa", 30.0
        elif arm in ("ga_p", "heft_p", "ga_p2", "heft_p2"):
            router = D.GraphAware(tie=tie) if arm.startswith("ga") else D.DISPATCHERS["heft_like_v2" if tie == "fst" else "heft_like"]
            churn = dict(no_inner=True, placement="qaware", origin_weight=1.0, tau=1.0, queue_term=False)
            cand, horizon = "hpa", 30.0
        elif arm in ("ga_s", "heft_s", "ga_s2", "heft_s2"):
            router = D.GraphAware(tie=tie) if arm.startswith("ga") else D.DISPATCHERS["heft_like_v2" if tie == "fst" else "heft_like"]
            churn = None
        else:
            raise ValueError(arm)
        kw["dispatcher"] = router
        if churn is None:
            sim = Sim(sc, X0.copy(), adjuster=None, seed=seed + 400, **kw)
        else:
            adj = O3SimAdjuster(make_adjuster("B_STAR", A, seed=seed + 300), 60.0, epoch=60.0, horizon=horizon, K=8, seed=seed + 800,
                                warmup=WARMUP, blind=True, cand_mode=cand, churn=churn)
            kw["interval"] = adj.next_interval
            sim = Sim(sc, X0.copy(), adjuster=adj, seed=seed + 400, **kw)
        r = sim.run()
        sim.check_invariants()
        r["wall_s"] = time.time() - t0
        if arm in ("faaspr", "faaspr_rs", "faaspr_el"):
            n_req = max(1, r["n_completed"])
            info = dict(faaspr_impl="FP-2", sizing=("scaler counts, not filled" if arm == "faaspr_el" else "scaler floor + fill to the slot budget"), storage=("relaxed x1000" if arm == "faaspr_rs" else "model"), n_solves=router.n_solves, n_wf_solves=router.n_wf_solves, n_slack=router.n_slack, n_wf_slack=router.n_wf_slack, slack_share_mean=float(np.mean(router.slack_share)) if router.slack_share else 0.0,
                        x_frac_mean=float(np.mean(router.x_frac)) if router.x_frac else None, solve_ms_mean=float(np.mean(router.solve_ms)),
                        window=dict(router.win), solve_log=router.solve_log, n_pure=router.n_pure, n_repaired_req=router.n_repaired_req, n_repaired_tasks=router.n_repaired_tasks,
                        n_unplanned=router.n_unplanned, repaired_req_share=router.n_repaired_req / max(1, router.n_pure + router.n_repaired_req),
                        placement_diag=dict(FAASPR_W_DIAG), n_paths=router.n_paths)
        out.write_text(json.dumps(dict(capacity_model=CAP, case=tg, system=arm, mover="none", queue="FIFO", info=info, result=r)))
    except Exception:
        import traceback
        out.with_suffix(".err").write_text(traceback.format_exc())
        return str(out) + " FAILED"
    return str(out)


def _low_priority():
    """Pool initializer: workers run below normal priority so the laptop stays usable (psutil is available with the Anaconda install)."""
    try:
        import psutil
        psutil.Process().nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
    except Exception:
        pass


def _place_job(tg):
    """Second half of capw1_light.prep_job (start layout), from the weighted scenario the parent wrote. Small memory per worker."""
    out = W1 / f"{tg}.sc.pkl"
    tmp = W1 / f"{tg}.scw.pkl"
    if out.exists():
        return str(out)
    try:
        import capw1_light as L
        from experiments.run import ASSUME, initial_placements
        seed = int(tg.split("_s")[1])
        P = pickle.load(open(tmp, "rb"))
        sc = P["sc"]
        t = time.time()
        _, X0, info = initial_placements(sc, seed, ASSUME["A06_generations"], "abs")
        fw = np.asarray(sc.fw, dtype=float)
        tmp_out = out.with_suffix(".tmp")
        pickle.dump(dict(sc=sc, X0=X0, info=info, wall_s=time.time() - t, rho_u=P["rho_u"], rho_w=P["rho_w"], rho_w_raw=P["rho_w_raw"],
                         fill_x0=float((X0 @ fw).sum() / float(np.sum(sc.ecc)))), open(tmp_out, "wb"))
        tmp_out.replace(out)                                # atomic: an interrupted run never leaves a half-written scenario
        tmp.unlink()
    except Exception:
        import traceback
        out.with_suffix(".err").write_text(traceback.format_exc())
        return str(out) + " FAILED"
    return str(out)


def prep(workers, seeds=(7, 8, 9, 10)):
    """capw1_light.prep_job, restructured for memory (5 Nov 2026): the two Alibaba JSON files (115 MB and 227 MB) cost 3.4 GB of RAM to
    parse and prep_job kept them alive through the multi-minute NSGA-II, in every worker at once (6 workers about 20 GB on a 16 GB machine:
    paging storm, apps that would not restart). Here the PARENT parses them once, writes the weighted scenarios, frees them, and only then
    do the workers run the start-layout search. Same arithmetic as prep_job, so the scenarios are the same as capw1_light would write."""
    import gc
    import capw1_light as L
    todo = [t for t in tags(seeds) if not (W1 / f"{t}.sc.pkl").exists()]
    todo_w = [t for t in todo if not (W1 / f"{t}.scw.pkl").exists()]
    if todo_w:
        from dfps.profiles import load_profiles, with_profiled_weights
        dags = json.load(open(ROOT / "data" / "alibaba_dags_lt60s.json"))
        profiles = load_profiles(ROOT / "data" / "alibaba_dags_lt60s_profiles.json")
        for tg in todo_w:
            sc = pickle.load(open(L.D1 / f"{tg}.pkl", "rb"))
            sc = with_profiled_weights(sc, profiles, agg="mean", alibaba_dags=dags)
            rho_u, rho_w_raw = L.offered_load(sc)
            sc.fw = np.asarray(sc.fw, dtype=float) * (rho_u / rho_w_raw)
            rho_w = L.offered_load(sc)[1]
            sc.meta = dict(sc.meta, capacity_model=CAP, fw_load_scale=float(rho_u / rho_w_raw), rho_w_raw=float(rho_w_raw))
            tmp = W1 / f"{tg}.scw.tmp"
            pickle.dump(dict(sc=sc, rho_u=rho_u, rho_w=rho_w, rho_w_raw=rho_w_raw), open(tmp, "wb"))
            tmp.replace(W1 / f"{tg}.scw.pkl")
            print("weighted", tg, flush=True)
        del profiles, dags
        gc.collect()
    with ProcessPoolExecutor(workers, initializer=_low_priority) as ex:
        for r in ex.map(_place_job, todo):
            print("prep", r, flush=True)


def run(workers, seeds, arms):
    jobs = [(t, a, DURATION, str(OUT)) for a in arms for t in tags(seeds) if not (OUT / f"{t}.{a}.json").exists()]
    print(len(jobs), "runs", flush=True)
    with ProcessPoolExecutor(workers, initializer=_low_priority) as ex:
        for r in ex.map(run_job, jobs):
            print("done", r, flush=True)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "prep":
        prep(int(sys.argv[2]) if len(sys.argv) > 2 else 4)
    elif cmd == "smoke":
        arm = sys.argv[2] if len(sys.argv) > 2 else "faaspr"
        sm = ROOT / "results" / "capW1_independent_smoke"
        res = run_job(("F1_r0.7_s1", arm, float(os.environ.get("SMOKE_S", 150)), str(sm)))
        print(res)
        j = json.loads(Path(res).read_text()) if not res.endswith("FAILED") else None
        if j:
            r = j["result"]
            print({k: r[k] for k in ("n_completed", "n_arrived", "n_unfinished", "p99_makespan", "avg_makespan", "cold_starts", "n_moved", "n_rejected", "n_parked", "wall_s")})
            print(j["info"])
        else:
            print(Path(res.replace(" FAILED", "")).with_suffix(".err").read_text())
    else:
        seeds = tuple(int(x) for x in sys.argv[3].split(",")) if len(sys.argv) > 3 else (7, 8, 9, 10)
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 4, seeds, tuple(sys.argv[4:]) or ARMS)
