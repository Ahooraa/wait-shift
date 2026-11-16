"""Readings R1-R4 of the ClusterLess-style baseline (CLU), as registered in knowledge/synthesis/clusterless-baseline.md section 9.

Reads ~/testbed-results/sim-clu (CLU arms) and the stored cells of F6, Heu, B*, RL (same loaders as make_sim_figures.py).
Writes output/data-analysis/clu-readings/{R1..R4}.csv and readings.md (the tables pasted into the wiki page).
  ~/venv-dfps/bin/python output/data-analysis/clu_readings.py
"""
import glob
import json
from pathlib import Path

import numpy as np

HOME = Path.home()
RES = HOME / "testbed-results"
OUT = Path(__file__).resolve().parent / "clu-readings"
OUT.mkdir(exist_ok=True)
APPS = [("690.ml", "ML"), ("660.map-reduce", "MapReduce"), ("650.vid", "Video"), ("680.excamera", "ExCamera")]
SEEDS = (1, 2, 3)
OTHERS = [("frozen6", "F6"), ("heu", "Heu"), ("bstar", "B*"), ("rl", "RL")]
CONDS = [("live", "live cell (load 0.5, cap 300)"), ("unc0.5", "load 0.5, no cap"), ("rho0.7", "load 0.7"), ("rho0.9", "load 0.9")]
C = {}


def put(st, x, arm=None):
    C[(st, x["app"], x["seed"], arm or x["arm"])] = x


for st, d in {"rho0.7": "sim-load-capw2/rho0.7", "rho0.9": "sim-load-capw2/rho0.9", "unc0.5": "sim-load-capw2/rho0.5-uncapped"}.items():
    for f in glob.glob(str(RES / d / "*.json")):
        put(st, json.load(open(f)))
for g, st in {"G1": "live", "G2": "unc0.5", "G3": "rho0.7", "G4": "rho0.9"}.items():
    for f in glob.glob(str(RES / "sim-event" / g / "*.frozen5_e0.json")):
        put(st, json.load(open(f)), "frozen6")
for f in glob.glob(str(RES / "azure-capw2-20261114/items/controller-*.json")):
    for r in json.load(open(f))["rows"]:
        s = dict(r["sim"]); s.update(app=r["app"], seed=r["seed"], arm=r["arm"]); put("live", s)
for st, d in {"live": "live", "unc0.5": "rho0.5-uncapped", "rho0.7": "rho0.7", "rho0.9": "rho0.9"}.items():
    for f in glob.glob(str(RES / "sim-clu" / d / "*.json")):
        put(st, json.load(open(f)))
for app in ("650.vid", "680.excamera"):          # the peak cap never binds for these two: the live cell is the uncapped load-0.5 cell
    for s in SEEDS:
        for a in ["clu", "frozen6", "heu", "bstar", "rl"]:
            if ("live", app, s, a) in C:
                C[("unc0.5", app, s, a)] = C[("live", app, s, a)]
for k, v in C.items():
    assert v["n_unfinished"] == 0, k
CELLS = [(a, s) for a, _ in APPS for s in SEEDS]
rng = np.random.default_rng(20261117)
md = []


def g(st, app, s, arm, key="p99_makespan"):
    return C[(st, app, s, arm)][key]


def gm_ci(ratios, n=10000):
    r = np.log(np.asarray(ratios, float))
    bs = np.array([r[rng.integers(0, len(r), len(r))].mean() for _ in range(n)])
    return float(np.exp(r.mean())), float(np.exp(np.percentile(bs, 2.5))), float(np.exp(np.percentile(bs, 97.5)))


def fmt(t):
    return f"{t[0]:.2f} [{t[1]:.2f}, {t[2]:.2f}]"


# ---------------------------------------------------------------------------------------------------------------- R1
rows = []
md.append("### R1. CLU against F6, Heu, B*, RL\n")
md.append("Geometric-mean ratio CLU / system over the 12 cells (4 applications x seeds 1-3) of a condition, bootstrap 95% CI (10,000 resamples). Below 1: CLU is lower. 'Lower in n/12' counts cells.\n")
for key, label in [("p99_makespan", "P99 makespan"), ("avg_makespan", "average makespan")]:
    md.append(f"\n**{label}**\n")
    md.append("| Condition | vs F6 | vs Heu | vs B* | vs RL |\n|---|---|---|---|---|")
    for st, cl in CONDS:
        cs = []
        for a, _ in OTHERS:
            r = [g(st, ap, s, "clu", key) / g(st, ap, s, a, key) for ap, s in CELLS]
            t = gm_ci(r)
            cs.append(f"{fmt(t)}; {sum(x < 1 for x in r)}/12")
            rows.append((label, st, a, *t, sum(x < 1 for x in r)))
        md.append(f"| {cl} | " + " | ".join(cs) + " |")
np.savetxt(OUT / "R1_ratios.csv", np.array([[r[3], r[4], r[5], r[6]] for r in rows]), delimiter=",", header="gm,lo,hi,lower_count (rows: key x cond x system)")
md.append("\n**P99 makespan per application (mean of seeds 1-3, s)**\n")
for st, cl in CONDS:
    md.append(f"\n{cl}\n\n| App | CLU | F6 | Heu | B* | RL | lowest |\n|---|---|---|---|---|---|---|")
    for ap, an in APPS:
        v = {a: np.mean([g(st, ap, s, a) for s in SEEDS]) for a in ["clu", "frozen6", "heu", "bstar", "rl"]}
        best = min(v, key=v.get)
        md.append(f"| {an} | " + " | ".join(f"{v[a]:.2f}" for a in ["clu", "frozen6", "heu", "bstar", "rl"]) + f" | {dict(frozen6='F6', clu='CLU', heu='Heu', bstar='B*', rl='RL')[best]} |")
md.append("\n**Lowest P99 of the five systems, count over the 12 cells of a condition**\n")
md.append("| Condition | CLU | F6 | Heu | B* | RL |\n|---|---|---|---|---|---|")
for st, cl in CONDS:
    cnt = dict.fromkeys(["clu", "frozen6", "heu", "bstar", "rl"], 0)
    for ap, s in CELLS:
        cnt[min(cnt, key=lambda a: g(st, ap, s, a))] += 1
    md.append(f"| {cl} | " + " | ".join(str(cnt[a]) for a in ["clu", "frozen6", "heu", "bstar", "rl"]) + " |")
md.append("\n**Per seed: P99 ratio CLU / F6 (geometric mean over the 4 applications)**\n")
md.append("| Condition | seed 1 | seed 2 | seed 3 |\n|---|---|---|---|")
for st, cl in CONDS:
    md.append(f"| {cl} | " + " | ".join(f"{np.exp(np.mean([np.log(g(st, ap, s, 'clu') / g(st, ap, s, 'frozen6')) for ap, _ in APPS])):.2f}" for s in SEEDS) + " |")
md.append("\n**Per application: P99 ratio CLU / F6 (geometric mean over the 3 seeds)**\n")
md.append("| Condition | ML | MapReduce | Video | ExCamera |\n|---|---|---|---|---|")
for st, cl in CONDS:
    md.append(f"| {cl} | " + " | ".join(f"{np.exp(np.mean([np.log(g(st, ap, s, 'clu') / g(st, ap, s, 'frozen6')) for s in SEEDS])):.2f}" for ap, _ in APPS) + " |")

# ---------------------------------------------------------------------------------------------------------------- R2
md.append("\n### R2. kappa sensitivity (live cell, 12 cells)\n")
md.append("| kappa | geometric-mean P99 ratio to kappa = 1.5 | avg makespan ratio | predicted misses / requests | real misses / requests |\n|---|---|---|---|---|")
for arm, kap in [("clu_k10", "1.0"), ("clu", "1.5"), ("clu_k30", "3.0")]:
    r = [g("live", ap, s, arm) / g("live", ap, s, "clu") for ap, s in CELLS]
    ra = [g("live", ap, s, arm, "avg_makespan") / g("live", ap, s, "clu", "avg_makespan") for ap, s in CELLS]
    pv = sum(C[("live", ap, s, arm)]["clu"]["pred_violated"] for ap, s in CELLS); rv = sum(C[("live", ap, s, arm)]["clu"]["real_violated"] for ap, s in CELLS)
    rq = sum(C[("live", ap, s, arm)]["clu"]["requests"] for ap, s in CELLS)
    md.append(f"| {kap} | {fmt(gm_ci(r)) if arm != 'clu' else '1 (reference)'} | {fmt(gm_ci(ra)) if arm != 'clu' else '1'} | {pv / rq:.3%} | {rv / rq:.3%} |")
md.append("\nPer application, P99 (s, mean of seeds) and real-miss share (all requests incl. warm-up):\n\n| App | k = 1.0 | k = 1.5 | k = 3.0 | pred. miss share k = 1.0 / 1.5 / 3.0 | real miss share k = 1.0 / 1.5 / 3.0 |\n|---|---|---|---|---|---|")
for ap, an in APPS:
    p = [np.mean([g("live", ap, s, a) for s in SEEDS]) for a in ["clu_k10", "clu", "clu_k30"]]
    sh = lambda key: " / ".join(f"{sum(C[('live', ap, s, a)]['clu'][key] for s in SEEDS) / sum(C[('live', ap, s, a)]['clu']['requests'] for s in SEEDS):.1%}" for a in ["clu_k10", "clu", "clu_k30"])
    md.append(f"| {an} | {p[0]:.2f} | {p[1]:.2f} | {p[2]:.2f} | {sh('pred_violated')} | {sh('real_violated')} |")

# ---------------------------------------------------------------------------------------------------------------- R3
md.append("\n### R3. CLU (re-planned at every ready function) against CLU-S (plan at arrival only), live cell\n")
r = [g("live", ap, s, "clu") / g("live", ap, s, "clu_s") for ap, s in CELLS]
ra = [g("live", ap, s, "clu", "avg_makespan") / g("live", ap, s, "clu_s", "avg_makespan") for ap, s in CELLS]
md.append(f"Ratio CLU / CLU-S over 12 cells: P99 {fmt(gm_ci(r))} (CLU lower in {sum(x < 1 for x in r)}/12), average makespan {fmt(gm_ci(ra))} (lower in {sum(x < 1 for x in ra)}/12).\n")
md.append("| App | P99 CLU | P99 CLU-S | avg CLU | avg CLU-S | real miss share CLU / CLU-S | cold starts CLU / CLU-S |\n|---|---|---|---|---|---|---|")
for ap, an in APPS:
    m = lambda a, k: np.mean([g("live", ap, s, a, k) for s in SEEDS])
    sh = lambda a: sum(C[("live", ap, s, a)]["clu"]["real_violated"] for s in SEEDS) / sum(C[("live", ap, s, a)]["clu"]["requests"] for s in SEEDS)
    md.append(f"| {an} | {m('clu', 'p99_makespan'):.2f} | {m('clu_s', 'p99_makespan'):.2f} | {m('clu', 'avg_makespan'):.2f} | {m('clu_s', 'avg_makespan'):.2f} | {sh('clu'):.1%} / {sh('clu_s'):.1%} | {m('clu', 'cold_starts'):.0f} / {m('clu_s', 'cold_starts'):.0f} |")

# ---------------------------------------------------------------------------------------------------------------- R4
md.append("\n### R4. Cold starts, decision time, deadline misses (CLU, kappa = 1.5)\n")
md.append("Cold starts: total of the run including the warm-up, mean of seeds. F6 is left out: it makes the same container changes during the warm-up, so its in-window count is not comparable.\n")
md.append("| Condition | App | cold starts CLU | Heu | B* | RL | pred. miss share | real miss share | plan ms p50 / p99 / max | escalations per request |\n|---|---|---|---|---|---|---|---|---|---|")
for st, cl in CONDS:
    for ap, an in APPS:
        cs = {a: np.mean([g(st, ap, s, a, "cold_starts") for s in SEEDS]) for a in ["clu", "heu", "bstar", "rl"]}
        cl_ = [C[(st, ap, s, "clu")]["clu"] for s in SEEDS]
        rq = sum(c["requests"] for c in cl_)
        md.append(f"| {st} | {an} | {cs['clu']:.0f} | {cs['heu']:.0f} | {cs['bstar']:.0f} | {cs['rl']:.0f} | {sum(c['pred_violated'] for c in cl_) / rq:.1%} | {sum(c['real_violated'] for c in cl_) / rq:.1%} | "
                  f"{np.mean([c['plan_ms_p50'] for c in cl_]):.2f} / {np.mean([c['plan_ms_p99'] for c in cl_]):.1f} / {max(c['plan_ms_max'] for c in cl_):.0f} | {sum(c['escalations'] for c in cl_) / rq:.2f} |")
mx = max(C[(st, ap, s, "clu")]["clu"]["plan_ms_max"] for st, _ in CONDS for ap, s in CELLS)
md.append(f"\nLargest single plan over all 48 CLU cells of the four conditions: {mx:.0f} ms. State moved between nodes by CLU: 0 MB relocated (no mover); the run-time state traffic is in the result files (`resources.state_mb`).")
(OUT / "readings.md").write_text("\n".join(md) + "\n")
print("\n".join(md))
