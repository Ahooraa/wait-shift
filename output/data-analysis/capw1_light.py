"""CAP-W1 light test (capacity model version CAP-W1: function containers differ in size) after the container-size correction (pre-registered 2 Nov 2026, knowledge/synthesis/heterogeneous-container-sizes.md,
"Light test: ours and B* on weighted scenarios"). The 18 development cases (F1/F2 x 50/70/85% load x seeds 1-3), the stored
scenario of each case with container weights from the profiles (dfps/profiles.py, agg = "mean"), an NSGA-II start layout that
respects the weights, then ours (cell D of grid2x2_v2.py) and B* on the same scenario, layout, arrivals and seeds.

  python capw1_light.py prep   [workers]   weighted scenarios + start layouts (results/capW1_light/{tag}.sc.pkl)
  python capw1_light.py smoke              one case, 200 s, ours and B*: invariants hold, no errors
  python capw1_light.py run    [workers] [ctrl ...]   ours and B* (default) or HEU / RL on the 18 cases (resumable)
  python capw1_light.py report             the pre-registered reading
"""
import json
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
import placement_extensions as pe  # noqa: E402

CAP = "CAP-W1"                                   # capacity-model version of every scenario and result here (see heterogeneous-container-sizes.md)
OUT = ROOT / "results" / "capW1_light"
D1 = ROOT / "results" / "d1_headroom"
DURATION, WARMUP = 900.0, 60.0


def cases():
    return [(f, r, s) for f in pe.FAMS for r in pe.RHOS for s in pe.SEEDS]


def offered_load(sc):
    """Offered load of the arrivals in the measured window: busy-container-seconds per capacity unit, (a) counting every
    container as one unit (CAP-U, what the trace was scaled to) and (b) weighting each by its size w_f (CAP-W1)."""
    mu = np.array([f.exec_time for f in sc.functions])
    fw = np.asarray(sc.fw, dtype=float)
    u = w = 0.0
    for t, wid, _ in sc.arrivals:
        if WARMUP <= t < DURATION:
            ft = sc.workflows[wid].ft
            u += float(sum(mu[f] for f in ft))
            w += float(sum(mu[f] * fw[f] for f in ft))
    cap = float(np.sum(sc.ecc)) * (DURATION - WARMUP)
    return u / cap, w / cap


def prep_job(tg):
    out = OUT / f"{tg}.sc.pkl"
    if out.exists():
        return str(out)
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        import numpy as _np
        assert _np.__version__.startswith("1."), "run with the Anaconda interpreter (numpy 1.26)"
        from experiments.run import ASSUME, initial_placements
        from dfps.profiles import load_profiles, with_profiled_weights
        seed = int(tg.split("_s")[1])
        sc = pickle.load(open(D1 / f"{tg}.pkl", "rb"))
        dags = json.load(open(ROOT / "data" / "alibaba_dags_lt60s.json"))
        profiles = load_profiles(ROOT / "data" / "alibaba_dags_lt60s_profiles.json")
        sc = with_profiled_weights(sc, profiles, agg="mean", alibaba_dags=dags)
        rho_u, rho_w_raw = offered_load(sc)
        # load-preserving normalisation (part of CAP-W1): the profile weights have mean 1 over the functions, but the busy
        # functions are on average heavier, so the same arrivals would load the cluster more (smoke case: 0.70 -> 0.87). Scale the
        # weights so the offered load in capacity units equals the nominal load: the test then isolates sizes, not load.
        sc.fw = np.asarray(sc.fw, dtype=float) * (rho_u / rho_w_raw)
        rho_w = offered_load(sc)[1]
        sc.meta = dict(sc.meta, capacity_model=CAP, fw_load_scale=float(rho_u / rho_w_raw), rho_w_raw=float(rho_w_raw))
        t = time.time()
        _, X0, info = initial_placements(sc, seed, ASSUME["A06_generations"], "abs")
        fw = np.asarray(sc.fw, dtype=float)
        pickle.dump(dict(sc=sc, X0=X0, info=info, wall_s=time.time() - t, rho_u=rho_u, rho_w=rho_w, rho_w_raw=rho_w_raw,
                         fill_x0=float((X0 @ fw).sum() / float(np.sum(sc.ecc)))), open(out, "wb"))
    except Exception:
        import traceback
        out.with_suffix(".err").write_text(traceback.format_exc())
        return str(out) + " FAILED"
    return str(out)


def run_job(args):
    tg, ctrl, duration = args
    out = OUT / f"{tg}.{ctrl}.json" if duration == DURATION else OUT / f"smoke_{tg}.{ctrl}.json"
    if out.exists():
        return str(out)
    try:
        import numpy as _np
        assert _np.__version__.startswith("1."), "run with the Anaconda interpreter (numpy 1.26)"
        import yaml
        from dfps.dispatch_priority import QueuePriority
        from dfps.o3s import O3SimAdjuster
        from dfps.sim import Sim
        from dfps.variants import make_adjuster, sim_kwargs
        from frozen2 import FROZEN2, MOVE_PERIOD_S
        ASSUME = yaml.safe_load((ROOT / "config" / "assumptions.yaml").read_text(encoding="utf-8"))
        P = pickle.load(open(OUT / f"{tg}.sc.pkl", "rb"))
        sc, X0 = P["sc"], P["X0"]
        seed, family = int(tg.split("_s")[1]), tg.split("_r")[0]
        kw = sim_kwargs("B_STAR", ASSUME)
        kw.update(warmup=WARMUP, duration=duration, retry_min_interval=1.0, retry_max_attempts=10)
        t0 = time.time()
        if ctrl in ("HEU", "RL"):                            # on-demand baselines: empty start, as their stored CAP-U runs
            from experiments.run import load_rl_policy
            from dfps.heu import HeuPolicy
            from dfps.ondemand import OnDemandSim
            # RL under CAP-W1: the policy trained under CAP-W1 (size features on), not the CAP-U policy (2 Nov 2026 correction)
            pol = HeuPolicy(seed=seed + 500) if ctrl == "HEU" else load_rl_policy(str(ROOT / "results" / "rl_policy_capw1.pt"), seed + 600, sizes=True)
            sim = OnDemandSim(sc, pol, seed=seed + 400, duration=duration, warmup=WARMUP)
            r = sim.run()
            sim.check_invariants()
            r["wall_s"] = time.time() - t0
            out.write_text(json.dumps(dict(capacity_model=CAP, case=tg, ctrl=ctrl, duration=duration, result=r,
                                           fw_min=float(np.min(sc.fw)), fw_max=float(np.max(sc.fw)), rho_u=P["rho_u"],
                                           rho_w=P["rho_w"], rho_w_raw=P["rho_w_raw"], fill_x0=P["fill_x0"])))
            return str(out)
        if ctrl == "ours":
            kw["queue_priority"] = QueuePriority("full", aging=2.0)
            churn = dict(FROZEN2, lam=0.5)
            adj = O3SimAdjuster(make_adjuster("B_STAR", ASSUME, seed=seed + 300), MOVE_PERIOD_S[family], epoch=60.0, horizon=30.0, K=8,
                                seed=seed + 800, warmup=WARMUP, blind=True, cand_mode="nosim", churn=churn)
            kw["interval"] = adj.next_interval
        else:
            period = json.loads((D1 / f"{tg}.B_STAR.json").read_text())["period"]
            adj = make_adjuster("B_STAR", ASSUME, seed=seed + 300)
            kw["interval"] = float(period)
        sim = Sim(sc, X0.copy(), adjuster=adj, seed=seed + 400, **kw)
        r = sim.run()
        sim.check_invariants()
        r["wall_s"] = time.time() - t0
        out.write_text(json.dumps(dict(capacity_model=CAP, case=tg, ctrl=ctrl, duration=duration, result=r,
                                       fw_min=float(np.min(sc.fw)), fw_max=float(np.max(sc.fw)), rho_u=P["rho_u"], rho_w=P["rho_w"], rho_w_raw=P["rho_w_raw"],
                                       fill_x0=P["fill_x0"])))
    except Exception:
        import traceback
        out.with_suffix(".err").write_text(traceback.format_exc())
        return str(out) + " FAILED"
    return str(out)


def prep(workers):
    with ProcessPoolExecutor(workers) as ex:
        for r in ex.map(prep_job, [pe.tag(*c) for c in cases()]):
            print("done", r, flush=True)


def smoke():
    tg = pe.tag("F1", 0.7, 1)
    with ProcessPoolExecutor(1) as ex:                       # each step in its own process (torch and numpy each load an OpenMP runtime)
        print(ex.submit(prep_job, tg).result(), flush=True)
    with ProcessPoolExecutor(2) as ex:
        for r in ex.map(run_job, [(tg, ctrl, 200.0) for ctrl in ("ours", "B_STAR")]):
            print(r, flush=True)


def run(workers, ctrls=("ours", "B_STAR")):
    jobs = [(pe.tag(*c), ctrl, DURATION) for c in cases() for ctrl in ctrls]
    todo = [j for j in jobs if not (OUT / f"{j[0]}.{j[1]}.json").exists()]
    print(f"{len(todo)} runs, {workers} workers", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        for r in ex.map(run_job, todo):
            print("done", r, flush=True)


def report():
    rows = {}
    for f in OUT.glob("*.json"):
        if f.name.startswith("smoke_"):
            continue
        x = json.loads(f.read_text())
        if "ctrl" not in x:                                   # other files in the directory (diagnostics), not runs
            continue
        rows.setdefault(x["case"], {})[x["ctrl"]] = x
    ref_ours, ref_b = {}, {}
    for f in pe.T1_REF.glob("*.D.json"):
        x = json.loads(f.read_text())
        ref_ours[pe.tag(x["family"], x["rho"], x["seed"])] = x["result"]
    for tg in rows:
        ref_b[tg] = json.loads((D1 / f"{tg}.B_STAR.json").read_text())["result"]
    ks = sorted(k for k in rows if {"ours", "B_STAR"} <= set(rows[k]))
    print(f"=== {len(ks)} of 18 cases complete ===")
    if not ks:
        return
    lr = [np.log(rows[k]["ours"]["result"]["p99_makespan"] / rows[k]["B_STAR"]["result"]["p99_makespan"]) for k in ks]
    lu = [np.log(ref_ours[k]["p99_makespan"] / ref_b[k]["p99_makespan"]) for k in ks]
    wins = sum(x < 0 for x in lr)
    print(f"{'case':14s} {'uniform ours/B*':>16s} {'weighted ours/B*':>17s} {'ours uniform->weighted':>23s} {'B* uniform->weighted':>21s}  fw range  rho (unscaled weights)")
    for k, a, b in zip(ks, lu, lr):
        ow, bw = rows[k]["ours"]["result"], rows[k]["B_STAR"]["result"]
        print(f"{k:14s} {np.exp(a):16.2f} {np.exp(b):17.2f} {ref_ours[k]['p99_makespan']:10.0f}->{ow['p99_makespan']:<9.0f} "
              f"{ref_b[k]['p99_makespan']:9.0f}->{bw['p99_makespan']:<9.0f}  {rows[k]['ours']['fw_min']:.2f}-{rows[k]['ours']['fw_max']:.2f}  {rows[k]['ours']['rho_u']:.2f}->{rows[k]['ours']['rho_w_raw']:.2f}")
    gm_u, gm_w = np.exp(np.mean(lu)), np.exp(np.mean(lr))
    print(f"\nP99 ratio ours/B* (geometric mean over cases): uniform {gm_u:.2f} -> weighted {gm_w:.2f}; ours lower than B* in {wins} of {len(ks)} cases")
    for fam in pe.FAMS:
        for rho in pe.RHOS:
            kk = [i for i, k in enumerate(ks) if k.startswith(f"{fam}_r{rho}_")]
            if kk:
                print(f"  {fam} {int(rho * 100):2d}%: uniform {np.exp(np.mean([lu[i] for i in kk])):.2f}  weighted {np.exp(np.mean([lr[i] for i in kk])):.2f}")
    cs = lambda c, key: np.mean([rows[k][c]["result"][key] for k in ks])
    print(f"cold starts (mean per run): ours {cs('ours', 'cold_starts'):.0f}, B* {cs('B_STAR', 'cold_starts'):.0f}; moves per request ours "
          f"{np.mean([rows[k]['ours']['result']['n_moved'] / max(1, rows[k]['ours']['result']['n_completed']) for k in ks]):.2f}")
    verdict = "SURVIVES" if (wins >= 16 and gm_w <= 0.5) else ("REVERSED" if gm_w >= 1.0 else "SHRINKS")
    print("verdict (pre-registered):", verdict)
    d = np.array(lr) - np.array(lu)
    lo, hi = pe.boot_ci(d)
    print(f"change of the gap, log(r_W / r_U): mean {np.mean(d):+.3f} (x{np.exp(np.mean(d)):.2f}), 95% CI [{lo:+.3f}, {hi:+.3f}] -> "
          + ("gap GROWS" if hi < 0 else ("gap SHRINKS" if lo > 0 else "no detectable change")))
    print("\nmean P99 (s) by controller, CAP-U -> CAP-W1 (cases with both):")
    for c, refdir in (("ours", None), ("B_STAR", None), ("HEU", "d1_baselines"), ("RL", "d1_baselines")):
        kk = [k for k in rows if c in rows[k]]
        if not kk:
            print(f"  {c:6s} not run yet")
            continue
        if c == "ours":
            u = [ref_ours[k]["p99_makespan"] for k in kk]
        elif c == "B_STAR":
            u = [json.loads((D1 / f"{k}.B_STAR.json").read_text())["result"]["p99_makespan"] for k in kk]
        else:
            u = [json.loads((ROOT / "results" / refdir / f"{k}.{c}.json").read_text())["result"]["p99_makespan"] for k in kk]
        w_ = [rows[k][c]["result"]["p99_makespan"] for k in kk]
        cu = np.mean([rows[k][c]["result"]["cold_starts"] for k in kk])
        print(f"  {c:6s} {len(kk):2d} cases: P99 {np.mean(u):7.1f} -> {np.mean(w_):7.1f}  (geo-mean change x{np.exp(np.mean(np.log(np.array(w_) / np.array(u)))):.2f}), "
              f"cold starts per run (W) {cu:,.0f}")
    for b in ("HEU", "RL"):                                           # pre-registered extension: ours vs each on-demand baseline
        kk = [k for k in rows if b in rows[k] and "ours" in rows[k]]
        if not kk:
            continue
        ru = [np.log(ref_ours[k]["p99_makespan"] / json.loads((ROOT / "results" / "d1_baselines" / f"{k}.{b}.json").read_text())["result"]["p99_makespan"])
              for k in kk]
        rw = [np.log(rows[k]["ours"]["result"]["p99_makespan"] / rows[k][b]["result"]["p99_makespan"]) for k in kk]
        db = np.array(rw) - np.array(ru)
        lo, hi = pe.boot_ci(db)
        print(f"ours vs {b} ({len(kk)} cases): ratio CAP-U {np.exp(np.mean(ru)):.2f} (wins {sum(x < 0 for x in ru)}), CAP-W1 {np.exp(np.mean(rw)):.2f} "
              f"(wins {sum(x < 0 for x in rw)}); change x{np.exp(np.mean(db)):.2f} [{np.exp(lo):.2f}, {np.exp(hi):.2f}] -> "
              + ("gap GROWS" if hi < 0 else ("gap SHRINKS" if lo > 0 else "no detectable change")))


if __name__ == "__main__":
    cmd = sys.argv[1]
    w = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    ctrls = tuple(sys.argv[3:]) or ("ours", "B_STAR")                 # run: which controllers (ours, B_STAR, HEU, RL)
    {"prep": lambda: prep(w), "smoke": smoke, "run": lambda: run(w, ctrls), "report": report}[cmd]()
