"""Where does workflow awareness pay? Data-intensive and large workflows, ours against the textbook stacks (2026-10-24).

Question: the textbook stack (HPA-style sizing + join-shortest-queue moves) reaches about 95% of our gain over the best existing
method on the standard scenarios, where state transfer is only 7-11% of the critical path. If transfer and workflow depth grow,
the parts that know about data (our finish-time moves, which include the transfer in and out; our placement, which pulls each
function toward its partners' nodes) should matter more. This study measures that before anything new is built.

Scenarios (all from the development set, seeds 1-2):
  mix     the standard 15-workflow mix (6 SeBS-Flow + DFPS Fig. 1 + 8 Alibaba DAGs), F1/F2 x 70/85% load
  chain12 / layered12 / wide16   every workflow of one large shape (pattern study), F1/F2 x 85% load, seed 1
Data intensity k: every state size and every request input size is multiplied by k (1, 4, 10), and node storage is multiplied by k
too, so storage pressure stays what it is at k = 1 and the experiment isolates the cost of moving more data. (First design: storage
unchanged. Smoke test 24 Oct: at k = 10 the requests in flight would need 2-7 times the whole cluster's storage by Little's law, so
every controller stalls in storage waits and the run does not finish; k = 4 needs 0.8-3 times. Storage is therefore scaled.)
Bandwidth and arrival rates are unchanged.

Controllers:
  ours    FROZEN-2 (sizing from load and backlog, incremental soft-routing placement, finish-time moves, no cap)
  stack   HPA-style sizing + join-shortest-queue moves, with OUR placement and the DFPS dispatcher (as in final_ablation.py)
  kstack  HPA-style sizing + join-shortest-queue moves + data-oblivious (random, capacity-respecting) placement: the closest thing
          to an off-the-shelf Kubernetes stack
  bstar   B* (DFPS with the errata fixed), its tuned period
Files results/wfstress/<scenario>.<ctrl>.json        python workflow_stress.py smoke | run [workers] | analyze
"""
import copy
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
from frozen2 import FROZEN2, MOVE_PERIOD_S  # noqa: E402

import yaml  # noqa: E402

from dfps.nsga2 import PlacementProblem, nsga2  # noqa: E402
from dfps.o3s import O3SimAdjuster  # noqa: E402
from dfps.sim import Sim  # noqa: E402
from dfps.variants import make_adjuster, sim_kwargs  # noqa: E402

ASSUME = yaml.safe_load((ROOT / "config" / "assumptions.yaml").read_text(encoding="utf-8"))
RUNS = ROOT / "results" / "wfstress"
PAT = ROOT / "results" / "patterns"
M = "p99_makespan"
KS = (1, 4, 10)
CTRLS = ("ours", "stack", "kstack", "bstar")
MIX = [("mix", f, r, s) for f in ("F1", "F2") for r in (0.7, 0.85) for s in (1, 2)]
SHAPES = [(p, f, 0.85, 1) for p in ("chain12", "layered12", "wide16") for f in ("F1", "F2")]
SHAPE_KS = (1, 10)


def tag(scen, k):
    p, f, r, s = scen
    return f"{p}_{f}_r{r}_s{s}_k{k}"


def scale(sc, k):
    """Copy of the scenario with every state and every request input k times larger."""
    sc = copy.deepcopy(sc)
    for w in sc.workflows:
        w.ss = {e: v * k for e, v in w.ss.items()}
        w.input_size = w.input_size * k
    sc.esc = sc.esc * k
    sc.meta["data_scale"] = k
    return sc


def load(scen):
    """(scenario, initial layout X0 [N, F]). The NSGA-II start layout depends only on network, slots and run times, so it is
    the same for every k."""
    p, f, r, s = scen
    if p == "mix":
        tg = d.tag(f, r, s)
        return pickle.load(open(d.D1 / f"{tg}.pkl", "rb")), pickle.load(open(d.D1 / f"{tg}.prep.pkl", "rb"))["X0"]
    base = PAT / f"{p}_{f}_r{r}_s{s}"
    sc = pickle.load(open(f"{base}.pkl", "rb"))
    x0p = RUNS / f"{p}_{f}_r{r}_s{s}.x0.pkl"
    if x0p.exists():
        return sc, pickle.load(open(x0p, "rb"))
    prob = PlacementProblem(sc.network, sc.ecc, np.array([fn.exec_time for fn in sc.functions]), "abs")
    X0 = nsga2(prob, np.random.default_rng(s + 200), gens=ASSUME["A06_generations"])[2]
    pickle.dump(X0, open(x0p, "wb"))
    return sc, X0


def transfer_share(sc):
    """Unloaded critical path with and without state transfers (mean hop distance), averaged over workflows: the ceiling on what
    co-location could save per request. Exec times are the mean run times."""
    net = sc.network
    hop = float(net.h[np.triu_indices(net.ne, 1)].mean())
    mu = np.array([fn.exec_time for fn in sc.functions])
    out = []
    for w in sc.workflows:
        a = np.zeros(w.n)
        b = np.zeros(w.n)
        for t in range(w.n):
            pa = max((a[u] for u in w.parents[t]), default=0.0)
            pb = max((b[u] + hop * (net.epd + w.ss[(u, t)] / net.bw) for u in w.parents[t]),
                     default=hop * (net.epd + w.input_size / net.bw))
            a[t], b[t] = pa + mu[w.ft[t]], pb + mu[w.ft[t]]
        out.append(1.0 - a.max() / b.max())
    return float(np.mean(out))


def one(args, duration=None, out=None):
    scen, k, ctrl, tstar = args
    out = RUNS / f"{tag(scen, k)}.{ctrl}.json" if out is None else out
    if out.exists():
        return str(out)
    try:
        assert np.__version__.startswith("1."), "run with the Anaconda interpreter (numpy 1.26)"
        sc0, X0 = load(scen)
        sc = scale(sc0, k)
        seed = scen[3]
        kw = sim_kwargs("B_STAR", ASSUME)
        kw.update(warmup=d.WARMUP, duration=d.DURATION if duration is None else duration, retry_min_interval=1.0, retry_max_attempts=10)
        if ctrl == "bstar":
            kw["interval"] = float(tstar)
            adj = make_adjuster("B_STAR", ASSUME, seed=seed + 300)
        else:
            cand, churn = {"ours": ("nosim", dict(FROZEN2)),
                           "stack": ("hpa", dict(FROZEN2, rebal_rule="jsq")),
                           "kstack": ("hpa", dict(FROZEN2, rebal_rule="jsq", placement="random"))}[ctrl]
            adj = O3SimAdjuster(make_adjuster("B_STAR", ASSUME, seed=seed + 300), MOVE_PERIOD_S[scen[1]], epoch=60.0, horizon=120.0, K=5,
                                seed=seed + 800, warmup=d.WARMUP, blind=True, cand_mode=cand, churn=churn)
            kw["interval"] = adj.next_interval
        t = time.time()
        sim = Sim(sc, X0, adjuster=adj, seed=seed + 400, trace=True, **kw)
        r = sim.run()
        sim.check_invariants()
        r["wall_s"] = time.time() - t
        from dfps.diagnostics import summarize
        try:
            diag = summarize(sim)
        except Exception:                                   # a diagnostics bug must not lose the run
            import traceback
            diag = {"error": traceback.format_exc()[-600:]}
        out.write_text(json.dumps(dict(scenario=list(scen), k=k, ctrl=ctrl, transfer_share=transfer_share(sc), result=r, diag=diag)))
        return str(out)
    except Exception:
        import traceback
        out.with_suffix(".err").write_text(traceback.format_exc())
        return str(out) + " FAILED"


def tstars():
    T = json.loads((d.OUT / "g2_tstar.json").read_text())
    return {f: float(T["families"][f]["T_star"]) for f in ("F1", "F2")}


def jobs():
    T = tstars()
    js = [(sc, k, c, T[sc[1]]) for sc in MIX for k in KS for c in CTRLS]
    js += [(sc, k, c, T[sc[1]]) for sc in SHAPES for k in SHAPE_KS for c in CTRLS]
    order = {10: 0, 1: 1, 4: 2}                      # the extremes first, so the trend is visible early
    js.sort(key=lambda j: (order[j[1]], -j[0][2], j[0][0] != "mix"))
    return [j for j in js if not (RUNS / f"{tag(j[0], j[1])}.{j[2]}.json").exists()]


def smoke():
    RUNS.mkdir(parents=True, exist_ok=True)
    T = tstars()
    sp = Path(sys.argv[2])
    for k in (1, 10):
        sc0, _ = load(("mix", "F1", 0.85, 1))
        print(f"k={k}: transfer share of the unloaded critical path {transfer_share(scale(sc0, k)):.1%}", flush=True)
        for c in ("ours", "stack"):
            t = time.time()
            o = sp / f"wfs_smoke_k{k}_{c}.json"
            res = one((("mix", "F1", 0.85, 1), k, c, T["F1"]), duration=140.0, out=o)
            if res.endswith("FAILED"):
                print(c, "FAILED", o.with_suffix(".err").read_text()[-1200:], flush=True)
                continue
            x = json.loads(o.read_text())["result"]
            print("  %-6s P99 %7.1f | mean %6.1f | completed %d of %d | parked %d | cold %d | moves/request %.2f | %.0f s" % (
                c, x[M], x["avg_makespan"], x["n_completed"], x["n_arrived"], x["n_parked"], x["cold_starts"],
                x["n_moved"] / max(1, x["n_completed"]), time.time() - t), flush=True)


def run(workers):
    RUNS.mkdir(parents=True, exist_ok=True)
    js = jobs()
    print(f"{len(js)} runs", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        for done in ex.map(one, js):
            print("done", done, flush=True)


def analyze():
    from d1_rlla import boot
    R = {}
    for f in RUNS.glob("*.json"):
        x = json.loads(f.read_text())
        R[(tuple(x["scenario"]), x["k"], x["ctrl"])] = x
    p = lambda b: f"{b['mean'] * 100:+6.1f}% ({b['lo'] * 100:+.0f} to {b['hi'] * 100:+.0f})"  # noqa: E731
    groups = [("mix 70%", lambda s: s[0] == "mix" and s[2] == 0.7, KS), ("mix 85%", lambda s: s[0] == "mix" and s[2] == 0.85, KS)]
    groups += [(sh, lambda s, sh=sh: s[0] == sh, SHAPE_KS) for sh in ("chain12", "layered12", "wide16")]
    print("P99 completion latency; 'ours better by' = (other - ours) / other per scenario, mean with 95% bootstrap interval\n")
    for name, sel, ks in groups:
        for k in ks:
            scs = sorted({s for (s, kk, c) in R if sel(s) and kk == k})
            scs = [s for s in scs if all((s, k, c) in R for c in CTRLS)]
            if not scs:
                continue
            ts = np.mean([R[(s, k, "ours")]["transfer_share"] for s in scs])
            line = f"{name:10s} k={k:2d} n={len(scs)} transfer share {ts:5.1%} | P99 ours {np.mean([R[(s, k, 'ours')]['result'][M] for s in scs]):7.1f}"
            for c in ("stack", "kstack", "bstar"):
                g = [(R[(s, k, c)]["result"][M] - R[(s, k, 'ours')]["result"][M]) / R[(s, k, c)]["result"][M] for s in scs]
                line += f" | vs {c}: {p(boot(g)) if len(g) > 1 else f'{g[0] * 100:+.1f}%'}"
            print(line)
            cold = " ".join(f"{c} {np.mean([R[(s, k, c)]['result']['cold_starts'] for s in scs]):.0f}" for c in CTRLS)
            park = " ".join(f"{c} {np.mean([R[(s, k, c)]['result']['n_parked'] for s in scs]):.0f}" for c in CTRLS)
            print(f"{'':10s}       cold starts: {cold} | parked: {park}")


if __name__ == "__main__":
    a = sys.argv[1]
    if a == "smoke":
        smoke()
    elif a == "run":
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 5)
    else:
        analyze()
