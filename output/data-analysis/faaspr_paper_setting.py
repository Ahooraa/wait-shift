"""FROZEN-3 against FaaSPR under FaaSPR's own evaluation setting (protocol: knowledge/synthesis/faaspr-paper-setting.md, 6 Nov 2026).
8 servers, one workflow per scenario (functions owned by it), memory-weighted containers (0.5-2 GB) in 402 GB, 50 MB/s with a remote-store data
path (h = 2 between servers), Azure-like minute rates (mean 203.8, peak 264 req/min, Poisson within the minute), 60 s platform scaler (elastic),
3,600 s with a 300 s warm-up. Three DAG shapes after Fig. 7 of the paper; three loads (rho 0.4 / 0.55 / 0.7).
Arms: faaspr | f3_fixed (FROZEN-3, budget filled) | f3_elastic (FROZEN-3 with the same elastic scaler as FaaSPR).
  python faaspr_paper_setting.py prep                 build the 36 scenarios (seeds 7-10) + start layouts
  python faaspr_paper_setting.py run [workers] [seeds] [arm ...]
  python faaspr_paper_setting.py smoke [shape rho seed arm]   short debug run (seed 1)
  python faaspr_paper_setting.py status | report
Results: results/capW1_faaspr_setting/{shape}_r{rho}_s{seed}.{arm}.json
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
OUT = ROOT / "results" / "capW1_faaspr_setting"
DURATION, WARMUP = 3600.0, 300.0
CAP = "CAP-W1"
SHAPES = {                                   # (tasks, edges), task 0 = the "upload" function
    "chain5": (5, [(0, 1), (1, 2), (2, 3), (3, 4)]),                                 # Fig. 7c, ResNet50 training
    "fan6": (6, [(0, 1), (1, 2), (1, 3), (1, 4), (2, 5), (3, 5), (4, 5)]),           # Fig. 7a, video processing, parallel branch, 3 segments
    "tree6": (6, [(0, 1), (1, 2), (1, 3), (3, 4), (4, 5)]),                          # Fig. 7e, calculator
}
RHOS = (0.4, 0.55, 0.7)
SEEDS = (7, 8, 9, 10)
ARMS = ("faaspr", "f3_fixed", "f3_elastic")
MEM_GB = [51, 51, 50, 50, 50, 50, 50, 50]    # 402 GB over 8 servers
RATE_MEAN, RATE_PEAK = 203.8, 264.0          # req/min
N_PATHS = 1500


def tag(shape, rho, seed):
    return f"{shape}_r{rho}_s{seed}"


def minute_rates(rng, minutes):
    """One-minute request rates with mean RATE_MEAN and maximum RATE_PEAK (the paper's trace statistics)."""
    z = RATE_MEAN + 25.0 * rng.standard_normal(minutes)
    for _ in range(20):
        z = np.clip(z + (RATE_MEAN - np.clip(z, 60.0, RATE_PEAK).mean()), 60.0, RATE_PEAK)
    return z


def build(shape, rho, seed):
    from dfps.model import Function, Scenario, Workflow
    from dfps.network import Network
    rng = np.random.default_rng(10_000 * seed + 100 * list(SHAPES).index(shape) + int(round(rho * 100)))
    n, edges = SHAPES[shape]
    fw = rng.uniform(0.5, 2.0, n)
    mu0 = rng.uniform(2.0, 10.0, n)
    cold = rng.uniform(2.0, 10.0, n)
    ss = {e: float(rng.uniform(10.0, 50.0)) for e in edges}
    wf = Workflow.from_edges(0, n, edges, list(range(n)), ss, 0.01)
    ne = 8
    net = Network(ne, [(a, b) for a in range(ne) for b in range(a + 1, ne)], bw=50.0)
    net.h = (2 * (1 - np.eye(ne))).astype(np.int64)             # a transfer between servers goes through the remote store: two transfers
    net.diameter = 2
    ecc = np.array(MEM_GB)
    esc = np.full(ne, 1e7)                                       # per-server storage never binds (paper: Redis, no per-server budget)
    rates = minute_rates(rng, int(DURATION // 60) + 1)
    arr = []
    for m, r in enumerate(rates):
        k = rng.poisson(r)
        for t in np.sort(rng.uniform(60.0 * m, 60.0 * (m + 1), k)):
            if t < DURATION:
                arr.append((float(t), 0, int(rng.integers(0, ne))))
    arr.sort()
    nwin = sum(1 for t, _, _ in arr if WARMUP <= t < DURATION)
    rho0 = nwin * float((mu0 * fw).sum()) / (float(ecc.sum()) * (DURATION - WARMUP))
    factor = rho / rho0                                          # exec-time factor: sets the load (free parameter of the experiment)
    mu = mu0 * factor
    fns = [Function(i, float(mu[i]), float(cold[i])) for i in range(n)]
    meta = dict(capacity_model=CAP, setting="faaspr-paper", shape=shape, rho=rho, seed=seed, exec_factor=float(factor), n_arrivals=len(arr),
                rate_mean_per_min=float(rates.mean()), rate_peak_per_min=float(rates.max()), memory_gb=float(ecc.sum()))
    return Scenario(fns, [wf], net, ecc, esc, arr, meta, fw=fw)


def prep_job(tg):
    p = OUT / f"{tg}.sc.pkl"
    if p.exists():
        return str(p)
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        from experiments.run import ASSUME, initial_placements
        shape, rho, seed = tg.rsplit("_", 2)[0], float(tg.split("_r")[1].split("_")[0]), int(tg.split("_s")[1])
        sc = build(shape, rho, seed)
        _, X0, info = initial_placements(sc, seed, ASSUME["A06_generations"], "abs")
        fw = np.asarray(sc.fw, float)
        assert (X0 @ fw <= sc.ecc + 1e-9).all() and (X0.sum(axis=0) >= 1).all(), "start layout infeasible"
        tmp = p.with_suffix(".tmp")
        pickle.dump(dict(sc=sc, X0=X0, info=info), open(tmp, "wb"))
        tmp.replace(p)
    except Exception:
        import traceback
        p.with_suffix(".err").write_text(traceback.format_exc())
        return str(p) + " FAILED"
    return str(p)


def tags(seeds=SEEDS):
    return [tag(s, r, d) for s in SHAPES for r in RHOS for d in seeds]


def _low_priority():
    try:
        import psutil
        psutil.Process().nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
    except Exception:
        pass


def run_job(args):
    tg, arm, duration, out_dir = args
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
        from dfps.dispatch_priority import QueuePriority
        from dfps.o3s import O3SimAdjuster
        from dfps.sim import Sim
        from dfps.variants import make_adjuster, sim_kwargs
        from frozen2 import FROZEN3, FROZEN4, FROZEN3_DISPATCHER
        for _k in list(FAASPR_W_DIAG):
            FAASPR_W_DIAG[_k] = 0
        A = yaml.safe_load((ROOT / "config" / "assumptions.yaml").read_text(encoding="utf-8"))
        P = pickle.load(open(OUT / f"{tg}.sc.pkl", "rb"))
        sc, X0 = P["sc"], P["X0"]
        assert sc.meta.get("capacity_model") == CAP
        seed = int(tg.split("_s")[1])
        fw = np.asarray(sc.fw, float)
        kw = sim_kwargs("B_STAR", A)
        kw.update(warmup=WARMUP, duration=duration, retry_min_interval=1.0, retry_max_attempts=10)
        router = None
        if arm == "faaspr":
            router = D.FaaSPRRouterPaper(seed=seed + 900, n_paths=N_PATHS, window=60.0)
            kw["dispatcher"] = router
            period, cand, churn = 60.0, "hpa", dict(no_inner=True, placement="faaspr_w", elastic=True)
        elif arm in ("f3_fixed", "f3_elastic", "f4_fixed", "f4_elastic"):
            kw["dispatcher"] = D.DISPATCHERS[FROZEN3_DISPATCHER]
            kw["queue_priority"] = QueuePriority("full", aging=2.0)
            period, cand, churn = 4.0, "nosim", dict(FROZEN4 if arm.startswith("f4") else FROZEN3, lam=0.5)
            if arm.endswith("_elastic"):
                churn["elastic"] = True
        else:
            raise ValueError(arm)
        adj = O3SimAdjuster(make_adjuster("B_STAR", A, seed=seed + 300), period, epoch=60.0, horizon=30.0, K=8, seed=seed + 800,
                            warmup=WARMUP, blind=True, cand_mode=cand, churn=churn)
        kw["interval"] = adj.next_interval
        sim = Sim(sc, X0.copy(), adjuster=adj, seed=seed + 400, **kw)
        ev = [(0.0, float((sim.cnt.T @ fw).sum() if sim.cnt.shape[0] != len(fw) else (sim.cnt * fw[:, None]).sum()))]
        orig = sim.apply_placement

        def tracked(X, _o=orig, _s=sim):                           # time-averaged provisioned memory
            r_ = _o(X)
            ev.append((float(_s.now), float((np.asarray(_s.cnt) * fw[:, None]).sum())))
            return r_
        sim.apply_placement = tracked
        t0 = time.time()
        r = sim.run()
        sim.check_invariants()
        r["wall_s"] = time.time() - t0
        t_lo, t_hi = WARMUP, duration
        ts = [t for t, _ in ev] + [t_hi]
        vs = [v for _, v in ev]
        acc = 0.0
        for i, v in enumerate(vs):
            a, b = max(ts[i], t_lo), min(ts[i + 1], t_hi)
            acc += v * max(0.0, b - a)
        info = dict(prov_gb_mean=acc / (t_hi - t_lo), n_relayouts=len(ev) - 1, exec_factor=sc.meta["exec_factor"])
        if arm == "faaspr":
            info.update(n_solves=router.n_solves, n_wf_solves=router.n_wf_solves, n_slack=router.n_slack, solve_log=router.solve_log,
                        window=dict(router.win), x_frac_mean=float(np.mean(router.x_frac)) if router.x_frac else None,
                        n_paths_last=len(router.paths.get(0, [])), n_pure=router.n_pure, n_repaired_req=router.n_repaired_req,
                        n_unplanned=router.n_unplanned, placement_diag=dict(FAASPR_W_DIAG))
        out.write_text(json.dumps(dict(capacity_model=CAP, setting="faaspr-paper", case=tg, system=arm, info=info, result=r)))
    except Exception:
        import traceback
        out.with_suffix(".err").write_text(traceback.format_exc())
        return str(out) + " FAILED"
    return str(out)


def path_of(tg, arm):
    return OUT / f"{tg}.{arm}.json"


def run(workers, seeds, arms):
    jobs = [(t, a, DURATION, str(OUT)) for t in tags(seeds) for a in arms if not path_of(t, a).exists()]
    print(len(jobs), "runs", flush=True)
    with ProcessPoolExecutor(workers, initializer=_low_priority) as ex:
        for r in ex.map(run_job, jobs):
            print("done", r, flush=True)


def status():
    for a in ARMS:
        n = sum(path_of(t, a).exists() for t in tags())
        e = sum(path_of(t, a).with_suffix(".err").exists() for t in tags())
        print(f"{a:11s} {n:2d}/36 done, {e} errors")


def gm_ci(x, seed=0):
    x = np.log(np.asarray(x, float))
    rng = np.random.default_rng(seed)
    bs = [x[rng.integers(0, len(x), len(x))].mean() for _ in range(10000)]
    lo, hi = np.exp(np.percentile(bs, [2.5, 97.5]))
    return float(np.exp(x.mean())), float(lo), float(hi)


def load(tg, arm):
    p = path_of(tg, arm)
    return json.loads(p.read_text()) if p.exists() else None


def report():
    cs = tags()
    print("FaaSPR's own setting (8 servers, 402 GB, 203.8 req/min, 3,600 s). Ratio FaaSPR / FROZEN-3 (geometric mean [95% bootstrap CI]; wins of FROZEN-3)")
    for ours in ("f3_fixed", "f3_elastic"):
        for metric, lab in (("p99_makespan", "P99"), ("avg_makespan", "mean")):
            rows = [(c, load(c, "faaspr"), load(c, ours)) for c in cs]
            rows = [(c, a["result"][metric], b["result"][metric]) for c, a, b in rows if a and b]
            if not rows:
                continue
            r = [a / b for _, a, b in rows]
            g = gm_ci(r)
            print(f"\n{lab} makespan, FaaSPR / {ours}: all {len(r)} cases {g[0]:.2f} [{g[1]:.2f}, {g[2]:.2f}], FROZEN-3 lower in {sum(x > 1 for x in r)}/{len(r)}")
            for key in list(SHAPES) + [f"_r{x}_" for x in RHOS]:
                q = [x for (c, _, _), x in zip(rows, r) if key in c]
                if q:
                    print(f"   {key:10s} {np.exp(np.mean(np.log(q))):6.2f}  ({len(q)} cases)")
    print("\nMean P99 (s) / mean makespan (s) / provisioned memory (GB, time average) per arm:")
    for a in ARMS:
        x = [load(c, a) for c in cs]
        x = [j for j in x if j]
        if x:
            print(f"  {a:11s} n={len(x):2d}  P99 {np.mean([j['result']['p99_makespan'] for j in x]):8.1f}  mean {np.mean([j['result']['avg_makespan'] for j in x]):7.1f}  "
                  f"memory {np.mean([j['info']['prov_gb_mean'] for j in x]):6.1f} GB  cold starts {np.mean([j['result']['cold_starts'] for j in x]):7.0f}")
    h = []
    for c in cs:
        j = load(c, "faaspr")
        if j:
            i = j["info"]; w = i["window"]
            lg = [x for x in i["solve_log"] if x[0] < DURATION]
            h.append((sum(x[2] for x in lg) / max(1, sum(x[1] for x in lg)), float(np.mean([x[2] > 0 for x in lg])) if lg else 0.0,
                      w["rep_req"] / max(1, w["pure"] + w["rep_req"]), w["unplanned"] / max(1, w["arrived"]), j["result"]["n_parked"] / max(1, j["result"]["n_arrived"]), i["n_paths_last"]))
    if h:
        m = np.array(h)
        print(f"\nFaaSPR health over {len(h)} cases (setting-fidelity check: slack-LP share per solve, median {np.median(m[:, 1]):.2f}, mean {m[:, 1].mean():.2f}): "
              f"workflow-solves needing slack {m[:, 0].mean():.2f}, repaired requests {m[:, 2].mean():.2f}, unplannable {m[:, 3].mean():.2f}, parked {m[:, 4].mean():.2f}, distinct paths in the last solve {m[:, 5].mean():.0f}")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "prep":
        todo = [t for t in tags() if not (OUT / f"{t}.sc.pkl").exists()]
        print(len(todo), "scenarios", flush=True)
        with ProcessPoolExecutor(int(sys.argv[2]) if len(sys.argv) > 2 else 4, initializer=_low_priority) as ex:
            for r in ex.map(prep_job, todo):
                print("prep", r, flush=True)
    elif cmd == "smoke":
        shape, rho, seed, arm = (sys.argv[2:6] + ["chain5", "0.55", "1", "faaspr"][len(sys.argv) - 2:]) if len(sys.argv) > 2 else ("chain5", "0.55", "1", "faaspr")
        tg = tag(shape, float(rho), int(seed))
        print(prep_job(tg), flush=True)
        res = run_job((tg, arm, float(os.environ.get("SMOKE_S", 600)), str(ROOT / "results" / "capW1_faaspr_setting_smoke")))
        print(res)
        if not res.endswith("FAILED"):
            j = json.loads(Path(res).read_text())
            r = j["result"]
            print({k: r[k] for k in ("n_completed", "n_arrived", "n_unfinished", "p99_makespan", "avg_makespan", "cold_starts", "n_moved", "n_parked", "wall_s")})
            print({k: v for k, v in j["info"].items() if k != "solve_log"})
        else:
            print(Path(res.replace(" FAILED", "")).with_suffix(".err").read_text())
    elif cmd == "run":
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 4, tuple(int(x) for x in sys.argv[3].split(",")) if len(sys.argv) > 3 else SEEDS, tuple(sys.argv[4:]) or ARMS)
    elif cmd == "status":
        status()
    elif cmd == "report":
        report()
