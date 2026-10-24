"""Our controller under overload, with and without admission control (2026-10-23).

Structural limit it addresses: the three mechanisms (busiest-first sizing, incremental k-median placement, finish-time request
moves) have no way to turn work away, so there is no story for load at or above capacity -- every scenario so far is at 50-85%.
D2 already measured the headroom there (rejecting requests under overload multiplies on-time work, and a fixed queue threshold
captures most of it), so this reuses D2's overload scenarios, baselines and oracle rather than building new ones.

Scenarios: results/d2_headroom/{F1,F2}_s{1..10}.pkl -- Azure and Huawei overload windows (built by G1's rule: top-200 aggregate
provisioned at median rho 0.7, window centred on a minute above capacity). F3 (synthetic) is excluded, as for every other
experiment since 2026-10-20. 15 min window after 60 s warm-up, 10 seeds per family = 20 cases.
Primary metric: SLO-goodput (workflows finishing within 3x their unloaded critical path, per second) -- P99 makespan is
meaningless once requests are rejected, since it is computed over the ones that were admitted.

Controllers (already in results/d2_headroom/*.json, same scenarios, seeds and window):
  B_STAR  admit everything (the paper)
  HEUR    B* + queue-threshold admission: admit iff requests in system <= 1.0 x total container slots (theta not tuned)
  O2/O2H  hindsight admission oracles -- the upper bound on what admission can buy
New here:
  ours        the three mechanisms, admit everything          files {tag}.ours.json
  ours_adm    the same + the SAME queue threshold as HEUR     files {tag}.ours_adm.json

  python output/data-analysis/overload_admission.py run [workers]
  python output/data-analysis/overload_admission.py analyze
"""
import json
import pickle
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(ROOT))

from experiments.run import ASSUME, initial_placements  # noqa: E402
from dfps.controllers import QueueThresholdAdmission  # noqa: E402
from dfps.o3s import O3SimAdjuster  # noqa: E402
from dfps.sim import Sim  # noqa: E402
from dfps.variants import make_adjuster, sim_kwargs  # noqa: E402

RUNS = ROOT / "results" / "d2_headroom"
OUT = ROOT / "output" / "data-analysis" / "results"
FAMS, SEEDS = ("F1", "F2"), tuple(range(1, 11))
DURATION, WARMUP, THETA = 900.0, 60.0, 1.0
# the frozen controller: busiest-first sizing, incremental k-median placement, finish-time request moves (no cap), no B*
CTRL = {"no_inner": True, "rebal": True, "rebal_max": 10 ** 9, "placement": "kmedian", "improve": 0, "origin_weight": 1.0}
M = "slo_goodput"


def job(args):
    sc_path, out_path, seed, period, admit = args
    if Path(out_path).exists():
        return out_path
    try:
        assert np.__version__.startswith("1."), "run with the Anaconda interpreter (numpy 1.26)"
        sc = pickle.load(open(sc_path, "rb"))
        _, X, _ = initial_placements(sc, seed, ASSUME["A06_generations"], "abs")
        adj = O3SimAdjuster(make_adjuster("B_STAR", ASSUME, seed=seed + 300), period, epoch=60.0, horizon=120.0, K=5,
                            seed=seed + 800, warmup=WARMUP, blind=True, cand_mode="nosim", churn=dict(CTRL))
        kw = sim_kwargs("B_STAR", ASSUME)
        kw.update(warmup=WARMUP, duration=DURATION, retry_min_interval=1.0, retry_max_attempts=10,
                  interval=adj.next_interval)
        if admit:
            kw["admission"] = QueueThresholdAdmission(THETA)
        t = time.time()
        sim = Sim(sc, X, adjuster=adj, seed=seed + 400, **kw)
        r = sim.run()
        sim.check_invariants()
        r["wall_s"] = time.time() - t
        Path(out_path).write_text(json.dumps(dict(family=sc.meta["family"], seed=seed, period=period, admission=bool(admit),
                                                  theta=THETA if admit else None, result=r, n_switch=adj.n_switch)))
        return out_path
    except Exception:
        import traceback
        Path(out_path).with_suffix(".err").write_text(traceback.format_exc())
        return out_path + " FAILED"


def run(workers):
    T = json.loads((OUT / "g2_tstar.json").read_text())
    T = {f: float(T["families"][f]["T_star"]) for f in FAMS}
    jobs = []
    for admit, suf in ((True, "ours_adm"), (False, "ours")):
        for fam in FAMS:
            for s in SEEDS:
                tg = f"{fam}_s{s}"
                p = RUNS / f"{tg}.pkl"
                if not p.exists():
                    raise SystemExit(f"missing D2 scenario {p}; run d2_headroom.py run first")
                jobs.append((str(p), str(RUNS / f"{tg}.{suf}.json"), s, T[fam], admit))
    with ProcessPoolExecutor(workers) as ex:
        for done in ex.map(job, jobs):
            print("done", done, flush=True)


def analyze():
    from d1_rlla import boot
    base, ours, ours_adm, o2h = {}, {}, {}, {}
    for fam in FAMS:
        for s in SEEDS:
            tg, key = f"{fam}_s{s}", (fam, s)
            f = RUNS / f"{tg}.json"
            if f.exists():
                d = json.loads(f.read_text())
                base[key] = {c: d[c] for c in ("B_STAR", "HEUR", "O2") if c in d}
            f = RUNS / f"{tg}.o2h.json"
            if f.exists():
                o2h[key] = json.loads(f.read_text()).get("O2H")
            for src, dst in ((f"{tg}.ours.json", ours), (f"{tg}.ours_adm.json", ours_adm)):
                f = RUNS / src
                if f.exists():
                    dst[key] = json.loads(f.read_text())["result"]
    ks = sorted(set(base) & set(ours) & set(ours_adm))
    print(f"{len(ks)} overload cases (Azure + Huawei, seeds 1-10); metric: SLO-goodput, workflows/s within 3x critical path\n")
    rows = [("B* (admit everything)", {k: base[k]["B_STAR"] for k in ks}),
            ("B* + admission (HEUR, theta 1.0)", {k: base[k]["HEUR"] for k in ks if "HEUR" in base[k]}),
            ("ours, admit everything", ours), ("ours + admission (same theta)", ours_adm)]
    if all(k in o2h and o2h[k] for k in ks):
        rows.append(("O2H (hindsight admission oracle)", {k: o2h[k] for k in ks}))
    p = lambda b: f"{b['mean'] * 100:+6.1f}% ({b['lo'] * 100:+.0f} to {b['hi'] * 100:+.0f})"  # noqa: E731
    out = {}
    print("%-36s %10s %10s %10s %10s" % ("controller", "goodput", "vs B*", "rejected", "P99 (adm.)"))
    for lab, r in rows:
        kk = [k for k in ks if k in r]
        if not kk:
            continue
        g = [(r[k][M] - base[k]["B_STAR"][M]) / base[k]["B_STAR"][M] for k in kk]
        row = dict(n=len(kk), goodput=float(np.mean([r[k][M] for k in kk])), vs_bstar=boot(g),
                   rejected=float(np.mean([r[k].get("n_rejected", 0) for k in kk])),
                   p99=float(np.mean([r[k]["p99_makespan"] for k in kk])), wins=int(sum(x > 0 for x in g)))
        out[lab] = row
        print("%-36s %10.2f %10s %10.0f %10.1f" % (lab, row["goodput"], p(row["vs_bstar"]), row["rejected"], row["p99"]))
    for a, b in (("ours + admission (same theta)", "ours, admit everything"),
                 ("ours + admission (same theta)", "B* + admission (HEUR, theta 1.0)")):
        if a in out and b in out:
            ra = ours_adm
            rb = ours if b.startswith("ours") else {k: base[k]["HEUR"] for k in ks if "HEUR" in base[k]}
            kk = [k for k in ks if k in ra and k in rb]
            d_ = [(ra[k][M] - rb[k][M]) / rb[k][M] for k in kk]
            bb = boot(d_)
            out[f"paired|{a}|{b}"] = dict(diff=bb, wins=int(sum(x > 0 for x in d_)), n=len(kk))
            print(f"  paired: '{a}' vs '{b}': {p(bb)} goodput, wins {sum(x > 0 for x in d_)}/{len(kk)}")
    if "O2H (hindsight admission oracle)" in out:
        o = out["O2H (hindsight admission oracle)"]["goodput"]
        b0 = out["B* (admit everything)"]["goodput"]
        for lab in ("ours + admission (same theta)", "B* + admission (HEUR, theta 1.0)"):
            if lab in out and o > b0:
                print(f"  {lab}: captures {(out[lab]['goodput'] - b0) / (o - b0):.0%} of the oracle's headroom over B*")
    (OUT / "overload_admission.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 6)
    else:
        analyze()
