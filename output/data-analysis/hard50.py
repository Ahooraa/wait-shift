"""What holds the controller back at 50% load? (2026-10-23)

Finding so far (no new runs needed): at 50% load a request's P99 is mostly irreducible. Task durations are exponential in the
simulator, so even with NO queueing and NO cold starts the P99 makespan of the workflow mix is about 88 s on average (a
Monte-Carlo critical-path floor, with the 0.72 s per edge the dispatcher's plans actually incur). Our controller sits 33 s above
that floor, RL 57 s. In 16 of 20 cases (seeds 1-10, Azure + Huawei) we are ahead; in 4 Huawei cases RL is ahead, and in three of
those the gap is 4-14 s. The exception is Huawei seed 5: floor 56 s, ours 152 s (96 s of excess), RL 130 s. Its arrival series is
the burstiest of all 20 (CV 0.27, peak 1.7x mean) with a very low median (11 s), i.e. long calm spells broken by bursts.

Hypothesis: between two re-layouts (60 s) a function whose demand jumps cannot get more containers -- request moves redistribute
queued work among the containers that exist, they cannot create capacity -- and the sizing rule sees the burst only through a
2-minute memory plus the current backlog. RL starts containers per request. Two experiments:

  timeline  Huawei seed 5, 50% load, final controller with per-request logging: when do the slow requests arrive, and do they
            coincide with the rate peaks?
  epoch     the final controller with the re-layout every 15 s / 30 s / 60 s on the six hardest cases (the four where RL is ahead
            plus the two Azure cases with the largest excess); incremental placement makes frequent re-layouts cheap.

  python output/data-analysis/hard50.py run [workers]  |  analyze
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
import d3s_headroom as d  # noqa: E402
from new_layer_sweep import BASE  # noqa: E402

import yaml  # noqa: E402

from dfps.o3s import O3SimAdjuster  # noqa: E402
from dfps.sim import Sim  # noqa: E402
from dfps.variants import make_adjuster, sim_kwargs  # noqa: E402

ASSUME = yaml.safe_load((ROOT / "config" / "assumptions.yaml").read_text(encoding="utf-8"))
FINAL = dict(BASE, placement="kmedian", improve=0, origin_weight=1.0, rebal_max=10 ** 9)
HARD = [("F2", 5), ("F2", 6), ("F2", 7), ("F2", 10), ("F1", 7), ("F1", 8)]
EPOCHS = (15, 30, 60)
M = "p99_makespan"


def timeline_job(args):
    """Final controller on Huawei seed 5 at 50% load with the per-request log; saves (arrival, makespan) of every request."""
    fam, seed, period = args
    out = d.RUNS / f"timeline_{fam}_r0.5_s{seed}.json"
    if out.exists():
        return str(out)
    try:
        tg = d.tag(fam, 0.5, seed)
        sc = pickle.load(open(d.D1 / f"{tg}.pkl", "rb"))
        P = pickle.load(open(d.D1 / f"{tg}.prep.pkl", "rb"))
        adj = O3SimAdjuster(make_adjuster("B_STAR", ASSUME, seed=seed + 300), period, epoch=60.0, horizon=120.0, K=5, seed=seed + 800,
                            warmup=d.WARMUP, blind=True, cand_mode="nosim", churn=dict(FINAL))
        kw = sim_kwargs("B_STAR", ASSUME)
        kw.update(warmup=d.WARMUP, duration=d.DURATION, retry_min_interval=1.0, retry_max_attempts=10, interval=adj.next_interval,
                  record_requests=True)
        sim = Sim(sc, P["X0"], adjuster=adj, seed=seed + 400, **kw)
        r = sim.run()
        out.write_text(json.dumps(dict(family=fam, seed=seed, p99=r[M], p50=r["p50_makespan"], log=sim.request_log,
                                       rate_series=sc.meta["rate_series"], bin_s=sc.meta["bin_s"], decisions=adj.log)))
        return str(out)
    except Exception:
        import traceback
        out.with_suffix(".err").write_text(traceback.format_exc())
        return str(out) + " FAILED"


def run(workers):
    d.RUNS.mkdir(parents=True, exist_ok=True)
    T = json.loads((d.OUT / "g2_tstar.json").read_text())
    T = {f: float(T["families"][f]["T_star"]) for f in ("F1", "F2")}
    jobs = []
    for e in EPOCHS:
        for fam, s in HARD:
            tg = d.tag(fam, 0.5, s)
            jobs.append((tg, str(d.RUNS / f"{tg}.O3S_h120_blind_nosim_nl_hardE{e}.json"), s, T[fam], d.DURATION, float(e), 120.0, 5,
                         True, None, "nosim", dict(FINAL)))
    with ProcessPoolExecutor(workers) as ex:
        f1 = ex.submit(timeline_job, ("F2", 5, T["F2"]))
        for done in ex.map(d.job, jobs):
            print("done", done, flush=True)
        print("timeline", f1.result(), flush=True)


def analyze():
    from d1_rlla import BASE as B1, D1, boot
    base = {}
    for d_ in (D1, B1):
        for f in d_.glob("*.json"):
            x = json.loads(f.read_text())
            if x.get("ctrl") in ("B_STAR", "RL"):
                base.setdefault((x["family"], x["rho"], x["seed"]), {})[x["ctrl"]] = x["result"][M]
    res = {}
    for e in EPOCHS:
        for fam, s in HARD:
            f = d.RUNS / f"{d.tag(fam, 0.5, s)}.O3S_h120_blind_nosim_nl_hardE{e}.json"
            if f.exists():
                res.setdefault(e, {})[(fam, s)] = json.loads(f.read_text())["result"]
    print("re-layout cadence on the six hardest 50%-load cases (P99 makespan, s)\n")
    print("%-9s %5s | %7s %7s %7s | %6s %6s" % ("case", "RL", "E=15", "E=30", "E=60", "cold15", "cold60"))
    for fam, s in HARD:
        rl = base.get((fam, 0.5, s), {}).get("RL", float("nan"))
        v = [res.get(e, {}).get((fam, s)) for e in EPOCHS]
        print("%-9s %5.0f | %s | %6s %6s" % (f"{fam} s{s}", rl, " ".join("%7.0f" % x[M] if x else "%7s" % "-" for x in v),
              v[0]["cold_starts"] if v[0] else "-", v[2]["cold_starts"] if v[2] else "-"))
    for e in EPOCHS[:2]:
        ks = [k for k in res.get(e, {}) if k in res.get(60, {})]
        if ks:
            dd = [(res[60][k][M] - res[e][k][M]) / res[60][k][M] for k in ks]
            b = boot(dd)
            print("\nepoch %d s vs 60 s: P99 %+.1f%% (%+.0f to %+.0f), better in %d/%d, cold starts %.0f vs %.0f" % (
                e, 100 * b["mean"], 100 * b["lo"], 100 * b["hi"], sum(x > 0 for x in dd), len(ks),
                np.mean([res[e][k]["cold_starts"] for k in ks]), np.mean([res[60][k]["cold_starts"] for k in ks])))
    f = d.RUNS / "timeline_F2_r0.5_s5.json"
    if f.exists():
        t = json.loads(f.read_text())
        log = np.array([(a, m) for _, a, m, _ in t["log"]])
        R = np.asarray(t["rate_series"]).sum(axis=0)
        b = t["bin_s"]
        print(f"\nHuawei seed 5, 50% load, final controller: P99 {t['p99']:.0f} s, median {t['p50']:.0f} s, {len(log)} requests")
        print("minute  rate/mean  requests  median  P95    max   (slow = makespan > 100 s)")
        for mnt in range(int(R.size)):
            sel = log[(log[:, 0] >= mnt * b) & (log[:, 0] < (mnt + 1) * b)]
            if len(sel):
                print("%5d  %8.2f  %8d  %6.0f %5.0f %6.0f   slow %3d" % (mnt, R[mnt] / R.mean(), len(sel), np.median(sel[:, 1]),
                      np.percentile(sel[:, 1], 95), sel[:, 1].max(), int((sel[:, 1] > 100).sum())))
        slow = log[log[:, 1] > np.percentile(log[:, 1], 99)]
        print("the slowest 1%% of requests (%d) arrived in minutes: %s" % (len(slow), sorted(set(int(a // b) for a in slow[:, 0]))))


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 6)
    else:
        analyze()
