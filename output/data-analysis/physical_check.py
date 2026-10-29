"""Physical check of the move terms (2026-10-28): the latency proxy is not enough -- did join gating actually shrink join desync, did
relevance actually move fewer bytes, and does relevance veto moves the plain rule would make (the "gridlock" question)?

Re-runs selected (scenario, config, seed) cases with the per-task trace and O3SimAdjuster's decision instrumentation (churn
log_terms: at every move decision the plain lam-weighted rule is evaluated on the same state, counting moves the configured rule
vetoes or adds; total queue backlog sampled at every move step). The simulator is deterministic per seed, so a re-run is the
same run as the suite's; the baseline is terms_off (move_terms on, every term off), which reproduces the plain rule exactly.

Per run, arrivals >= 120 s, mean per request: sojourn; join desync on the realised critical path (the extra lateness at a join
caused by its branches being delayed by different amounts, see penalty_stepA_analyze.py); extra first-hop transfer time from
fracturing; transferred state volume MB x hops on the realised placement; relocated MB.

  python output/data-analysis/physical_check.py run <workers> [case ...]        cases: see CASES
  python output/data-analysis/physical_check.py report
  python output/data-analysis/physical_check.py selftest                         decomposition on the Step A dump
"""
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))
RES = HERE / "results" / "physical_check"
SEEDS = (1, 2, 3)
BURN_IN = 120.0
T = dict(move_terms=True, log_terms=True)
CONFIGS = {"terms_off": dict(T), "R": dict(T, relevance_out=True), "J": dict(T, join_gate=True),
           "U": dict(T, urgency_priority=True), "UR": dict(T, urgency_priority=True, relevance_out=True)}
# case -> (scenario, [configs]); scenario "f3" = the F3 mix (faaspr_fig11_f3.build), else a dag_suite archetype
CASES = {"f3_R": ("f3", ["terms_off", "R"]), "heavy_R": ("heavy", ["terms_off", "R"]), "diamond_J": ("diamond", ["terms_off", "J"]),
         "grid_J": ("grid", ["terms_off", "J"]), "composite_UR": ("composite", ["U", "UR"]),
         # added after the suite (exploratory, not pre-registered): join gating's two significant cells were heavy and composite
         "heavy_J": ("heavy", ["terms_off", "J"]), "composite_J": ("composite", ["terms_off", "J"])}


def decompose(tasks, reqs, wfs, ex_time, stt, burn_in=BURN_IN, hops=None):
    """tasks: rows (rid, wid, t, plan, node, t_first, t_start, t_end, n_moves); reqs: rows (rid, wid, t_arr, t_done);
    wfs: wid -> dict(n, ft, parents, children, ss). Returns per-request means and the per-request sojourns."""
    T = {}
    for row in tasks:
        T.setdefault(row[0], {})[row[2]] = row
    out = dict(soj=[], desync=[], extra_hop=[], extra_hop_on_path=[], mb_hops=[], wait_moved=[], wait_unmoved=[])
    for rid, wid, t_arr, t_done in reqs:
        if t_arr < burn_in:
            continue
        w, R = wfs[wid], T.get(rid, {})
        if len(R) < w["n"]:
            continue
        ex = [ex_time[w["ft"][t]] for t in range(w["n"])]
        est = [0.0] * w["n"]
        for t in range(w["n"]):
            est[t] = max((est[u] + ex[u] for u in w["parents"][t]), default=0.0)
        arr_in = {(u, t): R[u][7] + stt(w["ss"][(u, t)], R[u][4], R[t][3]) for t in R for u in w["parents"][t]}
        t = max(R, key=lambda x: R[x][7])
        chain, crit = {t}, set()
        while w["parents"][t]:
            u = max(w["parents"][t], key=lambda x: arr_in[(x, t)])
            crit.add((u, t))
            chain.add(u)
            t = u
        desync = 0.0
        for x in range(w["n"]):
            ps = w["parents"][x]
            if len(ps) < 2 or x not in chain:
                continue
            arr = {u: arr_in[(u, x)] for u in ps}
            nom = {u: est[u] + ex[u] for u in ps}
            dly = {u: arr[u] - t_arr - nom[u] for u in ps}
            desync += max(arr.values()) - (t_arr + min(dly.values()) + max(nom.values()))
        eh = ehp = mbh = 0.0
        for (u, v), size in w["ss"].items():
            e = stt(size, R[u][4], R[v][3]) - stt(size, R[u][3], R[v][3])
            eh += e
            ehp += e if (u, v) in crit else 0.0
            mbh += size * hops(R[u][4], R[v][3])
        wm = sum(R[x][6] - R[x][5] for x in chain if R[x][8] > 0)
        wu = sum(R[x][6] - R[x][5] for x in chain if R[x][8] == 0)
        for k, v in (("soj", t_done - t_arr), ("desync", desync), ("extra_hop", eh), ("extra_hop_on_path", ehp), ("mb_hops", mbh),
                     ("wait_moved", wm), ("wait_unmoved", wu)):
            out[k].append(v)
    return out


def job(args):
    case, cfg, seed = args
    scen = CASES[case][0]
    out = RES / f"{scen}_{cfg}_s{seed}.json"
    if out.exists():
        return case, cfg, seed, "cached"
    import d3s_headroom as d
    import faaspr_fig11_f3 as m
    import dag_suite
    from dfps.o3s import O3SimAdjuster
    from dfps.sim import Sim
    from dfps.variants import make_adjuster, sim_kwargs
    from frozen2 import FROZEN2
    t0 = time.time()
    sc, X0 = m.build("F3", 0.7, 5, seed) if scen == "f3" else dag_suite.build(scen, seed)
    kw = sim_kwargs("B_STAR", m.ASSUME)
    kw.update(warmup=d.WARMUP, duration=900.0, retry_min_interval=1.0, retry_max_attempts=10, trace=True)
    adj = O3SimAdjuster(make_adjuster("B_STAR", m.ASSUME, seed=seed + 300), m.MOVE_PERIOD_F3, epoch=60.0, horizon=120.0, K=5,
                        seed=seed + 800, warmup=d.WARMUP, blind=True, cand_mode="nosim", churn=dict(FROZEN2, lam=0.5, **CONFIGS[cfg]),
                        sizing_cache={})
    kw["interval"] = adj.next_interval
    sim = Sim(sc, X0.copy(), adjuster=adj, seed=seed + 400, **kw)
    res = sim.run()
    sim.check_invariants()
    wfs = {w.id: dict(n=w.n, ft=list(w.ft), parents=w.parents, children=w.children, ss=w.ss) for w in sc.workflows}
    dec = decompose(sim.trace["tasks"], sim.trace["reqs"], wfs, list(sim.exec_time), sim.net.stt,
                    hops=lambda a, b: float(sim.net.h[a, b]))
    bl = np.array([b for t, b in getattr(adj, "backlog_log", []) if t >= BURN_IN], float)
    rec = dict(scen=scen, config=cfg, seed=seed, p99_makespan=res["p99_makespan"], n_moved=res["n_moved"],
               mb_relocated=res.get("mb_relocated"), decision_stats=getattr(adj, "decision_stats", None),
               term_stats=getattr(adj, "term_stats", None),
               backlog=dict(mean=float(bl.mean()), p95=float(np.percentile(bl, 95)), max=float(bl.max())) if len(bl) else None,
               means={k: float(np.mean(v)) for k, v in dec.items()},
               p99=float(np.percentile(dec["soj"], 99)), p90=float(np.percentile(dec["soj"], 90)), n=len(dec["soj"]),
               wall_s=time.time() - t0)
    RES.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec))
    return case, cfg, seed, f"p99={res['p99_makespan']:.1f} {rec['wall_s']:.0f}s"


def run(workers, cases):
    RES.mkdir(parents=True, exist_ok=True)
    jobs = [(c, cfg, s) for s in SEEDS for c in cases for cfg in CASES[c][1]]
    print(f"{len(jobs)} runs, {workers} workers", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        for c, cfg, s, msg in ex.map(job, jobs):
            print(f"done {c} {cfg} s{s}: {msg}", flush=True)


def report():
    for case, (scen, cfgs) in CASES.items():
        base_cfg, cfg = cfgs
        b = {s: json.loads((RES / f"{scen}_{base_cfg}_s{s}.json").read_text()) for s in SEEDS if (RES / f"{scen}_{base_cfg}_s{s}.json").exists()}
        c = {s: json.loads((RES / f"{scen}_{cfg}_s{s}.json").read_text()) for s in SEEDS if (RES / f"{scen}_{cfg}_s{s}.json").exists()}
        ss = sorted(set(b) & set(c))
        if not ss:
            continue
        print(f"\n=== {case}: {cfg} vs {base_cfg} on {scen}, seeds {ss} (change in %, per seed then mean) ===")
        keys = [("P99 sojourn", lambda r: r["p99"]), ("P90 sojourn", lambda r: r["p90"]), ("mean sojourn", lambda r: r["means"]["soj"]),
                ("join desync on path", lambda r: r["means"]["desync"]), ("extra first-hop", lambda r: r["means"]["extra_hop"]),
                ("extra hop on path", lambda r: r["means"]["extra_hop_on_path"]), ("transfer MB x hops", lambda r: r["means"]["mb_hops"]),
                ("relocated MB", lambda r: r["mb_relocated"]), ("moves", lambda r: r["n_moved"]),
                ("wait of moved (path)", lambda r: r["means"]["wait_moved"]), ("backlog mean", lambda r: r["backlog"]["mean"]),
                ("backlog p95", lambda r: r["backlog"]["p95"])]
        for name, get in keys:
            try:
                vals = [(get(b[s]), get(c[s])) for s in ss]
            except (TypeError, KeyError):
                continue
            per = [100 * (y / x - 1) if x else float("nan") for x, y in vals]
            print(f"  {name:22s} base {np.mean([x for x, _ in vals]):10.2f}  {cfg} {np.mean([y for _, y in vals]):10.2f}   "
                  + "  ".join(f"s{s} {p:+6.1f}%" for s, p in zip(ss, per)) + f"   mean {np.nanmean(per):+6.1f}%")
        for lab, r in (("baseline", b), (cfg, c)):
            ds = [r[s]["decision_stats"] for s in ss if r[s].get("decision_stats")]
            if ds:
                ev = sum(d["evals"] for d in ds)
                pa = sum(d["plain_accepts"] for d in ds)
                print(f"  decisions [{lab:9s}] evaluated {ev:8d}  rule accepts {sum(d['rule_accepts'] for d in ds) / ev:6.1%}  "
                      f"plain rule accepts {pa / ev:6.1%}  vetoed (plain yes, rule no) {sum(d['vetoed'] for d in ds) / max(pa, 1):6.1%} of plain accepts  "
                      f"added (rule yes, plain no) {sum(d['added'] for d in ds):6d}  same dest {sum(d['both_same_dest'] for d in ds):7d} "
                      f"other dest {sum(d['both_other_dest'] for d in ds):6d}  downstream s added by accepted moves {sum(d['out_delta_s'] for d in ds):9.0f}")


def selftest():
    import pickle
    D = pickle.load(open(HERE / "results" / "penalty_stepA" / "stepA.pkl", "rb"))
    H = np.array(D["h"])
    stt = lambda s, a, b: float(H[a][b] * (D["epd"] + s / D["bw"]))  # noqa: E731
    wfs = {int(k): dict(n=v["n"], ft=v["ft"], parents=v["parents"], children=v["children"], ss=v["ss"]) for k, v in D["wfs"].items()}
    dec = decompose(D["trace"]["tasks"], D["trace"]["reqs"], wfs, D["exec_time"], stt, burn_in=60.0, hops=lambda a, b: float(H[a][b]))
    print({k: round(float(np.mean(v)), 2) for k, v in dec.items()}, "n", len(dec["soj"]),
          "P99", round(float(np.percentile(dec["soj"], 99)), 2), "(Step A: p99 211.37, extra/req 5.12, extra on path 3.23)")


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(int(sys.argv[2]), tuple(sys.argv[3:]) or tuple(CASES))
    elif sys.argv[1] == "report":
        report()
    else:
        selftest()
