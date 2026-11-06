"""On-demand (elastic) re-comparison on the held-out set (protocol: knowledge/synthesis/independent-baselines-capw1.md, section 8, 6 Nov 2026).
Every system that can scale runs on-demand: its scaler's own container counts, memory beyond them stays empty (the default everywhere else
fills the cluster). Same 24 held-out cases (F1/F2 x rho 0.5/0.7/0.85 x seeds 7-10), 900 s, warm-up 60 s, CAP-W1 as capw1_heldout.py.
  frozen3_od   FROZEN-3 (frozen2.FROZEN3, transfer_only router, criticality queue order) with churn elastic=True
  stack_od     textbook stack (FROZEN-2, HPA sizing, jsq moves), elastic, qaware placement kept (churn elastic_qaware)
  faaspr_od    FaaSPR (1,500 paths, 30 s window), elastic
  ga_p2_od, heft_p2_od   Graph-Aware / HEFT-like on substrate S-P, tie-break v2, elastic, qaware placement kept
Not scaled, by design: RL (its own on-demand container model), B* (fixed-budget replacement), the static S-S arms.
  python capw1_ondemand.py run [workers] | status | report
Results: results/capW1_ondemand/{tag}.{arm}.json
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
import capw1_heldout as H  # noqa: E402

OUT = ROOT / "results" / "capW1_ondemand"
W1 = ROOT / "results" / "capW1_light"
DURATION, WARMUP = 900.0, 60.0
CAP = "CAP-W1"
ARMS = ("frozen3_od", "stack_od", "ga_p2_od", "heft_p2_od", "faaspr_od")
SEEDS = H.SEEDS


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
        from frozen2 import FROZEN2, FROZEN3, FROZEN3_DISPATCHER, MOVE_PERIOD_S
        for _k in list(FAASPR_W_DIAG):
            FAASPR_W_DIAG[_k] = 0
        A = yaml.safe_load((ROOT / "config" / "assumptions.yaml").read_text(encoding="utf-8"))
        P = pickle.load(open(W1 / f"{tg}.sc.pkl", "rb"))
        sc, X0 = P["sc"], P["X0"]
        assert sc.meta.get("capacity_model") == CAP
        seed, fam = int(tg.split("_s")[1]), tg.split("_r")[0]
        fw = np.asarray(sc.fw, float)
        kw = sim_kwargs("B_STAR", A)
        kw.update(warmup=WARMUP, duration=duration, retry_min_interval=1.0, retry_max_attempts=10)
        router = None
        epoch = 60.0
        fast_order, fast_place, lazy_place = "_fo" in arm, "_fp" in arm, "_lz" in arm  # speed-ups (7 Nov 2026): _fo, _fp exact or rounding-level; _lz lazy re-layout scoring
        arm = arm.replace("_fo", "").replace("_fp", "").replace("_lz", "")
        import re as _re
        _sd = _re.search(r"_sd(\d+)$", arm)                 # _sd2: a function shrinks only after its need was lower at 2 consecutive re-layouts
        shrink_delay = int(_sd.group(1)) if _sd else 0
        if _sd:
            arm = arm[:_sd.start()]
        _m = _re.search(r"_h(\d+)$", arm)                  # _h120: the trigger's added containers are held 120 s against the slow loop
        hold = float(_m.group(1)) if _m else 0.0
        if _m:
            arm = arm[:_m.start()]
        fs = arm.endswith("_fs")                            # trigger-based add / shrink between re-layouts (dfps.o3s fast_scale), development cases only
        if fs:
            arm = arm[:-3]
        util = None
        if "_u" in arm:                                     # utilisation-target test, development cases only: _u65 = containers for 0.65 utilisation
            arm, util = arm.split("_u")[0], int(arm.split("_u")[1]) / 100.0
        if "_e" in arm:                                     # cadence test, development cases only: frozen3_od_e30 = re-layout every 30 s
            arm, epoch = arm.split("_e")[0], float(arm.split("_e")[1])
        if arm == "frozen3_od":
            kw["dispatcher"] = D.DISPATCHERS[FROZEN3_DISPATCHER]
            kw["queue_priority"] = QueuePriority("full", aging=2.0)
            period, cand, churn = MOVE_PERIOD_S[fam], "nosim", dict(FROZEN3, lam=0.5, elastic=True)
        elif arm == "stack_od":
            period, cand, churn = MOVE_PERIOD_S[fam], "hpa", dict(FROZEN2, rebal_rule="jsq", elastic=True, elastic_qaware=True)
        elif arm in ("ga_p2_od", "heft_p2_od"):
            kw["dispatcher"] = D.GraphAware(tie="fst") if arm.startswith("ga") else D.DISPATCHERS["heft_like_v2"]
            period, cand = 60.0, "hpa"
            churn = dict(no_inner=True, placement="qaware", origin_weight=1.0, tau=1.0, queue_term=False, elastic=True, elastic_qaware=True)
        elif arm == "faaspr_od":
            router = D.FaaSPRRouterPaper(seed=seed + 900, n_paths=H.FP_PATHS, window=30.0)
            kw["dispatcher"] = router
            period, cand, churn = 60.0, "hpa", dict(no_inner=True, placement="faaspr_w", elastic=True)
        else:
            raise ValueError(arm)
        if util is not None:
            churn["util_cap"] = util
        if shrink_delay:
            churn["shrink_delay"] = shrink_delay
        if fast_order:
            churn["fast_order"] = True
        if fast_place:
            churn["fast_place"] = True
        if lazy_place:
            churn["lazy_place"] = True
        if fs:
            churn["fast_scale"] = True
            churn["fast_hold"] = hold
        adj = O3SimAdjuster(make_adjuster("B_STAR", A, seed=seed + 300), period, epoch=epoch, horizon=30.0, K=8, seed=seed + 800,
                            warmup=WARMUP, blind=True, cand_mode=cand, churn=churn)
        kw["interval"] = adj.next_interval
        sim = Sim(sc, X0.copy(), adjuster=adj, seed=seed + 400, **kw)
        ev = [(0.0, float((np.asarray(sim.cnt) * fw[:, None]).sum()))]
        orig = sim.apply_placement

        def tracked(X, _o=orig, _s=sim):                           # time-averaged provisioned memory (weight units)
            r_ = _o(X)
            ev.append((float(_s.now), float((np.asarray(_s.cnt) * fw[:, None]).sum())))
            return r_
        sim.apply_placement = tracked
        t0 = time.time()
        r = sim.run()
        sim.check_invariants()
        r["wall_s"] = time.time() - t0
        ts = [t for t, _ in ev] + [duration]
        acc = sum(v * max(0.0, min(ts[i + 1], duration) - max(ts[i], WARMUP)) for i, (_, v) in enumerate(ev))
        info = dict(provisioning="on-demand (elastic)", epoch=epoch, util_cap=util or 0.8, prov_mean=acc / (duration - WARMUP), capacity_total=float(np.sum(sc.ecc)), n_relayouts=len(ev) - 1, trigger=dict(actions=sum(e.get('applied', 0) for e in adj.fast_log), added=sum(e['added'] for e in adj.fast_log if e.get('applied')), removed=sum(e['removed'] for e in adj.fast_log if e.get('applied'))))
        out.write_text(json.dumps(dict(capacity_model=CAP, case=tg, system=arm, info=info, result=r)))
    except Exception:
        import traceback
        out.with_suffix(".err").write_text(traceback.format_exc())
        return str(out) + " FAILED"
    return str(out)


def path_of(tg, arm):
    return OUT / f"{tg}.{arm}.json"


def tags():
    return H.I.tags(SEEDS)


def run(workers):
    jobs = [(t, a, DURATION, str(OUT)) for a in ARMS for t in tags() if not path_of(t, a).exists()]
    print(len(jobs), "runs", flush=True)
    with ProcessPoolExecutor(workers, initializer=H.I._low_priority) as ex:
        for r in ex.map(run_job, jobs):
            print("done", r, flush=True)


def status():
    for a in ARMS:
        n = sum(path_of(t, a).exists() for t in tags())
        e = sum(path_of(t, a).with_suffix(".err").exists() for t in tags())
        print(f"{a:11s} {n:2d}/24 done, {e} errors")


def res(tg, arm):
    if arm.endswith("_od"):
        p = path_of(tg, arm)
        return json.loads(p.read_text())["result"] if p.exists() else None
    return H.result(tg, arm)


def block(title, systems, ref="frozen3_od"):
    cs = tags()
    print(f"\n{title}\n{'system':12s} {'cases':>5s} {'P99 ratio to ' + ref:>34s} {'rho 0.5':>8s} {'rho 0.7':>8s} {'rho 0.85':>8s}   {'mean ratio':>10s}   mean P99 (s)")
    for arm in systems:
        rows = [(c, res(c, arm), res(c, ref)) for c in cs]
        rows = [(c, a, f) for c, a, f in rows if a and f]
        if not rows:
            continue
        r = [a["p99_makespan"] / f["p99_makespan"] for _, a, f in rows]
        m = [a["avg_makespan"] / f["avg_makespan"] for _, a, f in rows]
        g = H.gm_ci(r)
        per = []
        for rho in ("0.5", "0.7", "0.85"):
            q = [x for (c, _, _), x in zip(rows, r) if f"_r{rho}_" in c]
            per.append(f"{np.exp(np.mean(np.log(q))):8.2f}" if q else f"{'-':>8s}")
        print(f"{arm:12s} {len(rows):5d} {g[0]:8.2f} [{g[1]:6.2f}, {g[2]:6.2f}] FROZEN-3 lower {sum(x > 1 for x in r):2d}/{len(r)} " + " ".join(per)
              + f"   {np.exp(np.mean(np.log(m))):10.2f}   {np.mean([a['p99_makespan'] for _, a, _ in rows]):8.1f}")


def report():
    print("On-demand re-comparison, held-out CAP-W1, seeds 7-10 (24 cases). Ratio = system / FROZEN-3 on-demand (geometric mean, 95% bootstrap CI over case log-ratios).")
    block("A. every scalable system on-demand (RL on-demand by design; B* fixed-budget and the S-S arms static, by design)",
          ["stack_od", "faaspr_od", "ga_p2_od", "heft_p2_od", "RL", "B_STAR", "ga_s2", "heft_s2"])
    block("B. FROZEN-3 on-demand against the baselines as already run (filled): FROZEN-3 has less memory here",
          ["stack", "faaspr", "ga_p2", "heft_p2", "frozen3"])
    print("\nProvisioned memory, mean over the 24 cases, as a share of the cluster (weight units); filled arms are ~98-100% by construction:")
    cs = tags()
    for a in ARMS:
        x = [json.loads(path_of(c, a).read_text()) for c in cs if path_of(c, a).exists()]
        if x:
            sh = [j["info"]["prov_mean"] / j["info"]["capacity_total"] for j in x]
            by = {rho: np.mean([s for s, c in zip(sh, [c for c in cs if path_of(c, a).exists()]) if f"_r{rho}_" in c]) for rho in ("0.5", "0.7", "0.85")}
            print(f"  {a:11s} {np.mean(sh):.2f}  (rho 0.5: {by['0.5']:.2f}, 0.7: {by['0.7']:.2f}, 0.85: {by['0.85']:.2f})   cold starts {np.mean([j['result']['cold_starts'] for j in x]):7.0f}")
    f3 = [res(c, "frozen3") for c in cs]
    print(f"  frozen3 (filled) cold starts {np.mean([r['cold_starts'] for r in f3 if r]):7.0f}")


if __name__ == "__main__":
    {"run": lambda: run(int(sys.argv[2]) if len(sys.argv) > 2 else 4), "status": status, "report": report}[sys.argv[1]]()
