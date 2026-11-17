"""Readings R5-R7 of the ClusterLess-style baseline (CLU), Stage 2, as registered in knowledge/synthesis/clusterless-baseline.md sections 8-9.

R5 node count (20, 40; the 10-node point is the load-0.5 cell without a peak cap), R6 cold-start duration (2, 5, 10 s; live cell), R7 1000Genome (loads 0.5, 0.7, 0.9).
Reads ~/testbed-results/sim-clu-s2 (CLU), sim-clu (10-node point), and the stored cells of F6 (`frozen6`), Heu, B*, RL.
Writes output/data-analysis/clu-readings/{readings_s2.md, R5_ratios.csv, R6_ratios.csv, R7_ratios.csv}.
  ~/venv-dfps/bin/python output/data-analysis/clu_readings_s2.py
"""
import glob
import json
from pathlib import Path

import numpy as np

RES = Path.home() / "testbed-results"
OUT = Path(__file__).resolve().parent / "clu-readings"
OUT.mkdir(exist_ok=True)
APPS = [("690.ml", "ML"), ("660.map-reduce", "MapReduce"), ("650.vid", "Video"), ("680.excamera", "ExCamera")]
GENOME = [("6100.1000-genome", "1000Genome")]
SEEDS = (1, 2, 3)
ARMS = ["clu", "frozen6", "heu", "bstar", "rl"]
OTHERS = [("frozen6", "F6"), ("heu", "Heu"), ("bstar", "B*"), ("rl", "RL")]
NAME = dict(clu="CLU", frozen6="F6", heu="Heu", bstar="B*", rl="RL")
C = {}


def put(st, x, arm=None):
    C[(st, x["app"], x["seed"], arm or x["arm"])] = x


for st, d in {"ne20": "sim-nodes/ne20", "ne40": "sim-nodes/ne40", "cold2": "sim-cold/cold2", "cold5": "sim-cold/cold5", "cold10": "sim-cold/cold10",
              "x0.5": "sim-load-capw2/extra-rho0.5", "x0.7": "sim-load-capw2/extra-rho0.7", "x0.9": "sim-load-capw2/extra-rho0.9",
              "ne10": "sim-load-capw2/rho0.5-uncapped"}.items():
    for f in glob.glob(str(RES / d / "*.json")):
        x = json.load(open(f))
        if x["arm"] in ARMS:
            put(st, x)
for g in ("G2",):                                                                           # F6 at 10 nodes, load 0.5, no cap (ML, MapReduce)
    for f in glob.glob(str(RES / "sim-event" / g / "*.frozen5_e0.json")):
        put("ne10", json.load(open(f)), "frozen6")
for st, d in {"ne20": "ne20", "ne40": "ne40", "cold2": "cold2", "cold5": "cold5", "cold10": "cold10", "x0.5": "x0.5", "x0.7": "x0.7", "x0.9": "x0.9"}.items():
    for f in glob.glob(str(RES / "sim-clu-s2" / d / "*.clu.json")):
        put(st, json.load(open(f)))
for f in glob.glob(str(RES / "sim-clu" / "rho0.5-uncapped" / "*.clu.json")):                # 10 nodes: ML and MapReduce own runs
    put("ne10", json.load(open(f)))
for app in ("650.vid", "680.excamera"):                                                      # Video, ExCamera: the live twin is the uncapped load-0.5 cell (the cap never binds)
    for s in SEEDS:
        for a in ARMS:
            if a == "clu":
                x = json.load(open(RES / "sim-clu" / "live" / f"{app}.s{s}.clu.json"))
            elif a == "frozen6":
                x = json.load(open(RES / "sim-event" / "G1" / f"{app}.s{s}.frozen5_e0.json"))
            else:
                x = None
                for f in glob.glob(str(RES / "azure-capw2-20261114/items/controller-*.json")):
                    for r in json.load(open(f))["rows"]:
                        if r["app"] == app and r["seed"] == s and r["arm"] == a:
                            x = dict(r["sim"]); x.update(app=app, seed=s, arm=a)
            C[("ne10", app, s, a)] = x
# the cold-start rows' reference ("measured" durations) is not part of R6 (it is in R1/R4 as the live cell)
for k, v in C.items():
    assert v["n_unfinished"] == 0, k
CELLS = [(a, s) for a, _ in APPS for s in SEEDS]
GCELLS = [("6100.1000-genome", s, st) for st in ("x0.5", "x0.7", "x0.9") for s in SEEDS]
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


def ratio_tables(title, conds, cells_of, csvname, key_note):
    """Geometric-mean ratio CLU / system per condition, for P99 and average makespan."""
    rows = []
    md.append(f"{title}\n")
    md.append(key_note + "\n")
    for key, label in [("p99_makespan", "P99 makespan"), ("avg_makespan", "average makespan")]:
        md.append(f"\n**{label}**\n")
        md.append("| Condition | vs F6 | vs Heu | vs B* | vs RL |\n|---|---|---|---|---|")
        for st, cl in conds:
            cs = []
            for a, _ in OTHERS:
                r = [g(st, ap, s, "clu", key) / g(st, ap, s, a, key) for ap, s in cells_of(st)]
                t = gm_ci(r)
                cs.append(f"{fmt(t)}; {sum(x < 1 for x in r)}/{len(r)}")
                rows.append((label, st, a, *t, sum(x < 1 for x in r), len(r)))
            md.append(f"| {cl} | " + " | ".join(cs) + " |")
    np.savetxt(OUT / csvname, np.array([[r[3], r[4], r[5], r[6], r[7]] for r in rows]), delimiter=",", header="gm,lo,hi,lower_count,n (rows: key x cond x system)")


def p99_tables(conds, cells_of_apps):
    md.append("\n**P99 makespan per application (mean of seeds 1-3, s)**\n")
    for st, cl in conds:
        md.append(f"\n{cl}\n\n| App | CLU | F6 | Heu | B* | RL | lowest |\n|---|---|---|---|---|---|---|")
        for ap, an in cells_of_apps:
            v = {a: np.mean([g(st, ap, s, a) for s in SEEDS]) for a in ARMS}
            md.append(f"| {an} | " + " | ".join(f"{v[a]:.2f}" for a in ARMS) + f" | {NAME[min(v, key=v.get)]} |")
    md.append("\n**Average makespan per application (mean of seeds 1-3, s)**\n")
    for st, cl in conds:
        md.append(f"\n{cl}\n\n| App | CLU | F6 | Heu | B* | RL | lowest |\n|---|---|---|---|---|---|---|")
        for ap, an in cells_of_apps:
            v = {a: np.mean([g(st, ap, s, a, "avg_makespan") for s in SEEDS]) for a in ARMS}
            md.append(f"| {an} | " + " | ".join(f"{v[a]:.2f}" for a in ARMS) + f" | {NAME[min(v, key=v.get)]} |")


def lowest(conds, cells_of):
    md.append("\n**Lowest P99 of the five systems, count over the cells of a condition**\n")
    md.append("| Condition | CLU | F6 | Heu | B* | RL | cells |\n|---|---|---|---|---|---|---|")
    for st, cl in conds:
        cnt = dict.fromkeys(ARMS, 0)
        cs = cells_of(st)
        for ap, s in cs:
            cnt[min(cnt, key=lambda a: g(st, ap, s, a))] += 1
        md.append(f"| {cl} | " + " | ".join(str(cnt[a]) for a in ARMS) + f" | {len(cs)} |")


def clu_stats(st, ap, seeds=SEEDS):
    return [C[(st, ap, s, "clu")]["clu"] for s in seeds]


# ---------------------------------------------------------------------------------------------------------------- R5
NODE = [("ne10", "10 nodes (load 0.5, no cap)"), ("ne20", "20 nodes"), ("ne40", "40 nodes")]
md.append("### R5. Node count (nominal load 0.5 per node, no peak cap)\n")
ratio_tables("Geometric-mean ratio CLU / system over the 12 cells (4 applications x seeds 1-3) of a node count, bootstrap 95% CI (10,000 resamples). Below 1: CLU is lower. 'n/12' counts cells where CLU is lower. The 10-node row is the load-0.5 cell without a peak cap of Stage 1 (ML and MapReduce own runs; Video and ExCamera the live twin).",
             NODE, lambda st: CELLS, "R5_ratios.csv", "")
p99_tables(NODE, APPS)
lowest(NODE, lambda st: CELLS)
md.append("\n**CLU's plan time against the node count (all cells of the application, 3 seeds)**\n")
md.append("| Nodes | App | requests (mean) | plan ms p50 | p99 | max | escalations per request | real miss share | wall s (mean) |\n|---|---|---|---|---|---|---|---|---|")
for st, cl in NODE:
    for ap, an in APPS:
        cl_ = clu_stats(st, ap)
        rq = sum(c["requests"] for c in cl_)
        wall = np.mean([C[(st, ap, s, "clu")]["wall_s"] for s in SEEDS])
        md.append(f"| {cl.split(' (')[0]} | {an} | {rq / 3:,.0f} | {np.mean([c['plan_ms_p50'] for c in cl_]):.2f} | {np.mean([c['plan_ms_p99'] for c in cl_]):.1f} | {max(c['plan_ms_max'] for c in cl_):.0f} | "
                  f"{sum(c['escalations'] for c in cl_) / rq:.2f} | {sum(c['real_violated'] for c in cl_) / rq:.1%} | {wall:,.0f} |")
for st, cl in NODE:
    allc = [c for ap, _ in APPS for c in clu_stats(st, ap)]
    md.append(f"\n{cl.split(' (')[0]}: median over the 12 cells of the per-cell p50 = {np.median([c['plan_ms_p50'] for c in allc]):.2f} ms, of the per-cell p99 = {np.median([c['plan_ms_p99'] for c in allc]):.1f} ms, largest single plan {max(c['plan_ms_max'] for c in allc):.0f} ms.")
md.append("\n**Cold starts (total of the run incl. warm-up, mean of seeds)**\n")
md.append("| Nodes | App | CLU | Heu | B* | RL |\n|---|---|---|---|---|---|")
for st, cl in NODE:
    for ap, an in APPS:
        md.append(f"| {cl.split(' (')[0]} | {an} | " + " | ".join(f"{np.mean([g(st, ap, s, a, 'cold_starts') for s in SEEDS]):,.0f}" for a in ("clu", "heu", "bstar", "rl")) + " |")

# ---------------------------------------------------------------------------------------------------------------- R6
COLD = [("cold2", "cold start 2 s"), ("cold5", "cold start 5 s"), ("cold10", "cold start 10 s")]
md.append("\n### R6. Cold-start duration (live cell: nominal load 0.5, peak cap 300 tasks/s; one duration for every function)\n")
ratio_tables("Geometric-mean ratio CLU / system over the 12 cells of a duration, bootstrap 95% CI. Below 1: CLU is lower.", COLD, lambda st: CELLS, "R6_ratios.csv", "")
p99_tables(COLD, APPS)
lowest(COLD, lambda st: CELLS)
md.append("\n**CLU's cold starts and escalations against the duration (descriptive)**\n")
md.append("Cold starts: total of the run incl. the warm-up, mean of seeds; 'cold-mode decisions' = decisions where CLU chose cold scaling (all seeds); per request = divided by the requests of the run. Measured-duration values (0.22-0.34 s) are the live cell of Stage 1 (R4).\n")
md.append("| App | duration | cold starts (CLU) | cold-mode decisions per request | escalations per request | predicted miss share | real miss share |\n|---|---|---|---|---|---|---|")
for ap, an in APPS:
    for st, lab in [("live", "measured")] + [(s, c.split()[-2] + " s") for s, c in COLD]:
        if st == "live":
            cl_ = [json.load(open(RES / "sim-clu" / "live" / f"{ap}.s{s}.clu.json")) for s in SEEDS]
            cs = np.mean([x["cold_starts"] for x in cl_])
            cl_ = [x["clu"] for x in cl_]
        else:
            cl_ = clu_stats(st, ap)
            cs = np.mean([g(st, ap, s, "clu", "cold_starts") for s in SEEDS])
        rq = sum(c["requests"] for c in cl_)
        md.append(f"| {an} | {lab} | {cs:,.0f} | {sum(c['cold_mode_decisions'] for c in cl_) / rq:.3f} | {sum(c['escalations'] for c in cl_) / rq:.3f} | "
                  f"{sum(c['pred_violated'] for c in cl_) / rq:.1%} | {sum(c['real_violated'] for c in cl_) / rq:.1%} |")

# ---------------------------------------------------------------------------------------------------------------- R7
GEN = [("x0.5", "load 0.5"), ("x0.7", "load 0.7"), ("x0.9", "load 0.9")]
ga = "6100.1000-genome"
md.append("\n### R7. 1000Genome (10 nodes, no peak cap; ML cell's window)\n")
md.append("These runs hold 54-88 requests, so the P99 is set by one or two requests: read the intervals as wide, no ranking is claimed.\n")
md.append("**Per cell: P99 / average makespan (s)**\n")
md.append("| Load | seed | requests | CLU | F6 | Heu | B* | RL | lowest P99 |\n|---|---|---|---|---|---|---|---|---|")
cnt = dict.fromkeys(ARMS, 0)
for st, lab in GEN:
    for s in SEEDS:
        v = {a: g(st, ga, s, a) for a in ARMS}
        cnt[min(v, key=v.get)] += 1
        md.append(f"| {lab} | {s} | {C[(st, ga, s, 'clu')]['n_arrived']} | " + " | ".join(f"{g(st, ga, s, a):.1f} / {g(st, ga, s, a, 'avg_makespan'):.1f}" for a in ARMS) + f" | {NAME[min(v, key=v.get)]} |")
md.append("\nLowest P99 of the five systems over the 9 cells: " + ", ".join(f"{NAME[a]} {cnt[a]}" for a in ARMS) + ".\n")
rows = []
md.append("**Geometric-mean ratio CLU / system over the 9 cells (3 loads x seeds 1-3), bootstrap 95% CI**\n")
md.append("| Measure | vs F6 | vs Heu | vs B* | vs RL |\n|---|---|---|---|---|")
for key, label in [("p99_makespan", "P99 makespan"), ("avg_makespan", "average makespan")]:
    cs = []
    for a, _ in OTHERS:
        r = [g(st, ga, s, "clu", key) / g(st, ga, s, a, key) for st, _ in GEN for s in SEEDS]
        t = gm_ci(r)
        cs.append(f"{fmt(t)}; {sum(x < 1 for x in r)}/9")
        rows.append((label, "genome", a, *t, sum(x < 1 for x in r), 9))
    md.append(f"| {label} | " + " | ".join(cs) + " |")
np.savetxt(OUT / "R7_ratios.csv", np.array([[r[3], r[4], r[5], r[6], r[7]] for r in rows]), delimiter=",", header="gm,lo,hi,lower_count,n (rows: key x system)")
md.append("\n**Mean over seeds 1-3 (s)**\n")
md.append("| Load | measure | CLU | F6 | Heu | B* | RL |\n|---|---|---|---|---|---|---|")
for st, lab in GEN:
    for key, ml in [("p99_makespan", "P99"), ("avg_makespan", "average")]:
        md.append(f"| {lab} | {ml} | " + " | ".join(f"{np.mean([g(st, ga, s, a, key) for s in SEEDS]):.2f}" for a in ARMS) + " |")
(OUT / "readings_s2.md").write_text("\n".join(md) + "\n")
print("\n".join(md))
