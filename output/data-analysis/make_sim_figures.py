"""Figures for the simulator sensitivity studies (twin simulator, CAP-W2 weights, Azure arrivals, F6 / Heu / B* / RL / CLU, development seeds 1-3).

Reads the simulator result folders and the simulator twins stored in the live result files (never writes into them); writes PNG + PDF + one CSV table
into output/data-analysis/sim-figures/.

  ~/venv-dfps/bin/python output/data-analysis/make_sim_figures.py

Studies (all in ~/testbed-results):
  baseline   the simulator twin of the live cell (nominal load 0.5, 10 nodes, peak cap 300 tasks/s, measured cold starts), stored in azure-capw2-20261114
  load       sim-load-capw2/rho0.7, rho0.9 (no peak cap) and rho0.5-uncapped (ML, MapReduce); Trip Booking and 1000Genome in extra-rho0.5/0.7/0.9
  nodes      sim-nodes/ne20, ne40 (nominal load 0.5 per node, no peak cap)
  cold       sim-cold/cold2, cold5, cold10 (one cold-start duration for every function; the live cell, peak cap 300 tasks/s)
Colour and marker: one per system in every figure (the reference palette's first four slots in fixed order; marker shape is the second channel).
The held-out seeds 7-10 are not used.
"""
import csv
import glob
import json
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D

HOME = Path.home()
RES = HOME / "testbed-results"
OUT = Path(__file__).resolve().parent / "sim-figures"
OUT.mkdir(exist_ok=True)

APPS = [("690.ml", "ML"), ("660.map-reduce", "MapReduce"), ("650.vid", "Video"), ("680.excamera", "ExCamera")]
EXTRA = [("6100.1000-genome", "1000Genome")]                                  # Trip Booking was not run for F6, B* and RL (16 Nov 2026, user)
SYS = [("frozen6", "F6 (ours)", "#e87ba4", "P"), ("heu", "Heu", "#eb6834", "s"), ("bstar", "B*", "#1baf7a", "^"), ("rl", "RL", "#eda100", "D")]   # F5 is not drawn (16 Nov 2026, user)
CLU_SYS = ("clu", "CLU", "#8a63d2", "v")                                       # 17 Nov 2026 (user): ClusterLess-style baseline as a fifth series in the load and cost figures and the overview; violet (min. OKLab distance 15 to the others in normal vision, deutan, protan and tritan) and a down triangle
SYS5 = SYS + [CLU_SYS]
SEEDS = (1, 2, 3)
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]       # sequential blue, steps 100-700

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": INK2, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "text.color": INK, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID,
                     "grid.linewidth": 0.7, "axes.axisbelow": True, "figure.facecolor": "white", "axes.facecolor": "white", "legend.frameon": False})

# ------------------------------------------------------------------------------------------------------------------------------------- data
STUDY_DIRS = {"rho0.7": "sim-load-capw2/rho0.7", "rho0.9": "sim-load-capw2/rho0.9", "unc0.5": "sim-load-capw2/rho0.5-uncapped",
              "x0.5": "sim-load-capw2/extra-rho0.5", "x0.7": "sim-load-capw2/extra-rho0.7", "x0.9": "sim-load-capw2/extra-rho0.9",
              "ne20": "sim-nodes/ne20", "ne40": "sim-nodes/ne40", "cold2": "sim-cold/cold2", "cold5": "sim-cold/cold5", "cold10": "sim-cold/cold10"}
CELL = {}                                                                  # (study, app, seed, arm) -> numbers


def cell(x, res):
    res = res or {}
    return dict(avg=x["avg_makespan"], p50=x["p50_makespan"], p99=x["p99_makespan"], cold=float(x["cold_starts"]), mb=float(res.get("state_mb", np.nan)),
                unf=int(x["n_unfinished"]), arrived=int(x["n_arrived"]))


for study, d in STUDY_DIRS.items():
    for f in sorted(glob.glob(str(RES / d / "*.json"))):
        x = json.load(open(f))
        CELL[(study, x["app"], x["seed"], x["arm"])] = cell(x, x.get("resources"))
for st, d in {"base": "live", "unc0.5": "rho0.5-uncapped", "rho0.7": "rho0.7", "rho0.9": "rho0.9"}.items():         # CLU (kappa 1.5, re-planned at every ready function): Stage 1 of knowledge/synthesis/clusterless-baseline.md
    for f in sorted(glob.glob(str(RES / "sim-clu" / d / "*.clu.json"))):
        x = json.load(open(f))
        CELL[(st, x["app"], x["seed"], "clu")] = cell(x, x.get("resources"))
for st in ("ne20", "ne40", "cold2", "cold5", "cold10", "x0.5", "x0.7", "x0.9"):                  # CLU Stage 2 (17 Nov 2026): node count, cold-start duration, 1000Genome
    for f in sorted(glob.glob(str(RES / "sim-clu-s2" / st / "*.clu.json"))):
        x = json.load(open(f))
        CELL[(st, x["app"], x["seed"], "clu")] = cell(x, x.get("resources"))
EVENT_STUDY = {"G1": "base", "G2": "unc0.5", "G3": "rho0.7", "G4": "rho0.9"}
for g, st in EVENT_STUDY.items():                                           # F6 = frozen5_e0 of the event-driven grid (same configuration, same event hash)
    for f in sorted(glob.glob(str(RES / "sim-event" / g / "*.frozen5_e0.json"))):
        x = json.load(open(f))
        CELL[(st, x["app"], x["seed"], "frozen6")] = cell(x, x.get("resources"))
for f in sorted(glob.glob(str(RES / "azure-capw2-20261114/items/controller-*.json"))):          # the simulator twin of every live run of the load 0.5 batch
    for r in json.load(open(f))["rows"]:
        CELL[("base", r["app"], r["seed"], r["arm"])] = cell(r["sim"], r["sim_resources"])
        if r["app"] in ("650.vid", "680.excamera"):
            assert abs(r["peak_scale"] - 1.0) < 1e-9, "the peak cap binds for this cell: its twin is not an uncapped load-0.5 cell"

for arm, *_ in SYS:                                                        # every cell the figures need must exist
    for app, _ in APPS:
        for s in SEEDS:
            for st in ("base", "rho0.7", "rho0.9", "ne20", "ne40", "cold2", "cold5", "cold10"):
                assert (st, app, s, arm) in CELL, (st, app, s, arm)
            if app in ("690.ml", "660.map-reduce"):
                assert ("unc0.5", app, s, arm) in CELL
for arm, *_ in SYS:
    for app, _ in EXTRA:
        for s_ in SEEDS:
            for st in ("x0.5", "x0.7", "x0.9"):
                assert (st, app, s_, arm) in CELL, (st, app, s_, arm)
for app, _ in APPS:                                                        # CLU: Stage 1 (load conditions) and Stage 2 (node count, cold-start duration, 1000Genome), all cells
    for s in SEEDS:
        for st in ("base", "rho0.7", "rho0.9", "ne20", "ne40", "cold2", "cold5", "cold10") + (("unc0.5",) if app in ("690.ml", "660.map-reduce") else ()):
            assert (st, app, s, "clu") in CELL, (st, app, s, "clu")
for app, _ in EXTRA:
    for s in SEEDS:
        for st in ("x0.5", "x0.7", "x0.9"):
            assert (st, app, s, "clu") in CELL, (st, app, s, "clu")
assert not [k for k, v in CELL.items() if v["unf"] > 0], "a cell has unfinished requests: the makespans would need a censoring note"


def ref(app):
    """The load-0.5, 10-node cell without a peak cap: an own study for ML and MapReduce; for Video and ExCamera the cap never binds, so the live-cell twin is that cell."""
    return "unc0.5" if app in ("690.ml", "660.map-reduce") else "base"


def get(study, app, arm):
    return [CELL[(study, app, s, arm)] for s in SEEDS]


def save(fig, name):
    fig.savefig(OUT / f"{name}.png", dpi=200, bbox_inches="tight")
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------------------------------------------------------------- line figures
def foot(fig, note, fig_w, fig_h):
    """Footnote wrapped to the figure's width (8 pt text is about 0.0645 in per character). Returns the fraction of the figure height it occupies."""
    lines = []
    for para in note.split("\n"):
        lines += textwrap.wrap(para, int(fig_w / 0.0645)) or [""]
    fig.text(0.5, 0.0, "\n".join(lines), ha="center", va="bottom", fontsize=8, color=INK2, linespacing=1.35)
    return len(lines) * 8 * 1.35 / 72 / fig_h


def end_labels(ax, ends):
    """Name each line at the right edge of the panel; labels are spread apart and joined to the line end by a thin leader line (nudged labels never float free)."""
    to_ax = ax.transData + ax.transAxes.inverted()
    pts = sorted(((to_ax.transform((x, y))[1], x, y, lab) for x, y, lab in ends))
    pos = [p[0] for p in pts]
    for i in range(1, len(pos)):
        pos[i] = max(pos[i], pos[i - 1] + 0.1)
    top = pos[-1] - 0.96
    if top > 0:
        pos = [p - top for p in pos]
    for (_, x, y, lab), p in zip(pts, pos):
        ax.annotate(lab, xy=(x, y), xycoords="data", xytext=(1.07, p), textcoords="axes fraction", fontsize=8.5, color=INK, va="center", annotation_clip=False,
                    arrowprops=dict(arrowstyle="-", lw=0.6, color=INK2, shrinkA=1, shrinkB=4, relpos=(0, 0.5)))


def sweep(name, title, xs, xticklabels, xlab, study_of, rows, apps, systems, note, jitter, xlim):
    nr, nc = len(rows), len(apps)
    fw, fh = max(3.0 * nc + 1.5, 7.2), 2.85 * nr + 1.3
    fig, axes = plt.subplots(nr, nc, figsize=(fw, fh), squeeze=False)
    for j, (app, an) in enumerate(apps):
        for i, row in enumerate(rows):
            key, lab, floor = row[:3]
            skip = row[3] if len(row) > 3 else ()
            ax = axes[i, j]
            ends, allv = [], []
            for k, (arm, aname, col, mk) in enumerate(systems):
                if arm in skip:
                    continue
                xo = (k - (len(systems) - 1) / 2) * jitter
                means = []
                for x in xs:
                    v = np.maximum(np.array([c[key] for c in get(study_of(app, x), app, arm)], dtype=float), floor)
                    ax.scatter(np.full(len(v), x + xo), v, s=9, color=col, alpha=0.4, linewidths=0, zorder=2)
                    means.append(v.mean())
                    allv += list(v)
                ax.plot(np.array(xs) + xo, means, color=col, lw=1.8, marker=mk, ms=7, mec="white", mew=1.2, zorder=3, solid_capstyle="round", solid_joinstyle="round")
                ends.append((xs[-1] + xo, means[-1], aname))
            lo, hi = min(allv) / 1.7, max(allv) * 1.7
            ax.set_yscale("log")
            ax.set_ylim(lo, hi)
            ax.yaxis.set_major_locator(mt.LogLocator(base=10, subs=((1.0,) if hi / lo > 400 else (1.0, 2.0, 5.0))))
            ax.yaxis.set_major_formatter(mt.FuncFormatter(lambda v, _: f"{v:,.0f}" if v >= 10 else f"{v:g}"))
            ax.yaxis.set_minor_locator(mt.NullLocator())
            ax.set_xlim(*xlim)
            ax.set_xticks(xs)
            ax.set_xticklabels(xticklabels)
            ax.tick_params(labelbottom=(i == nr - 1))
            ax.grid(axis="x", visible=False)
            if i == 0:
                ax.set_title(an, fontsize=12, fontweight="bold")
            if i == nr - 1:
                ax.set_xlabel(xlab)
            if j == 0:
                ax.set_ylabel(lab)
            if j == nc - 1:
                end_labels(ax, ends)
    handles = [Line2D([0], [0], color=c, marker=m, lw=1.8, ms=7, mec="white", mew=1.2, label=n) for _, n, c, m in systems]
    foot_h = foot(fig, note, fw, fh)
    fig.legend(handles=handles, loc="lower center", ncol=len(systems), bbox_to_anchor=(0.5, foot_h + 0.012), fontsize=10)
    fig.suptitle(title, fontsize=12.5, y=0.998)
    fig.tight_layout(rect=(0, foot_h + 0.012 + 0.05, 0.93 if nc > 2 else 0.9, 0.972))
    save(fig, name)


CLU_NOTE = ("CLU = an independent single-cluster reduction of ClusterLess (arXiv 2605.04310): deadline-aware placement with kappa 1.5 (deadline = 1.5 x the longest path), re-planned at every ready function; Heu's and RL's container model; no tuning. "
            "Run in every condition of this study (development seeds 1-3).")
AVGP99 = [("avg", "Average makespan (s)", 1e-9), ("p99", "P99 makespan (s)", 1e-9)]
SEED_NOTE = "Lines: mean of seeds 1-3; faint dots: the individual seeds (development seeds; the held-out seeds 7-10 are not used). Log y-axes. Simulator twin, CAP-W2 weights, Azure arrivals."
F6_NOTE = ("F6 = the controller F5 with its first re-layout at 10 s instead of at the end of the warm-up (adopted 16 Nov 2026 on these development seeds; not yet confirmed on fresh seeds). "
           "Its load cells are the early-start arm of the event-driven grid (same configuration, same event hash).")


def fig_load():
    note = (SEED_NOTE + "\n" + F6_NOTE + "\nLoad 0.5 is the cell without a peak cap: ML and MapReduce have their own runs; for Video and ExCamera the cap of 300 tasks/s never binds, so the live-cell twin is that cell.\n"
            "MapReduce at load 0.5: the P99 of F5 was set by a start-up transient in the first ~120 s of the measured window (seeds 1-3 diagnosed); F6 removes it (first-120 s P99 x0.13-0.20).\n" + CLU_NOTE)
    sweep("sim1_load_sweep", "Sensitivity to load: average and P99 makespan at nominal load 0.5, 0.7 and 0.9 (simulator)", [0.5, 0.7, 0.9], ["0.5", "0.7", "0.9"], "nominal load",
          lambda app, x: ref(app) if x == 0.5 else f"rho{x}", AVGP99, APPS, SYS5, note, 0.012, (0.455, 0.945))


def fig_nodes():
    note = (SEED_NOTE + "\n" + F6_NOTE + "\nNominal load 0.5 per node (the arrivals grow with the node count), no peak cap. The 10-node point is the same load-0.5 cell as in the load figure.\n" + CLU_NOTE)
    sweep("sim2_node_count", "Sensitivity to cluster size: average and P99 makespan with 10, 20 and 40 nodes (simulator)", [0, 1, 2], ["10", "20", "40"], "logical nodes",
          lambda app, x: (ref(app), "ne20", "ne40")[x], AVGP99, APPS, SYS5, note, 0.07, (-0.4, 2.4))


def fig_cold():
    note = (SEED_NOTE + "\n" + F6_NOTE + "\nThe live cell (nominal load 0.5, peak cap 300 tasks/s: effective load ML 0.31, MapReduce 0.25, Video and ExCamera 0.5) with one cold-start duration for every function.\n"
            "'measured' keeps the SeBS-Flow medians (0.22-0.34 s). F6 and B* start from an initial layout that is not counted as cold starts.\n" + CLU_NOTE)
    sweep("sim3_cold_start_duration", "Sensitivity to the cold-start duration: average and P99 makespan (simulator)", [0, 1, 2, 3], ["measured\n(0.2-0.3 s)", "2 s", "5 s", "10 s"], "cold-start duration of every function",
          lambda app, x: ("base", "cold2", "cold5", "cold10")[x], AVGP99, APPS, SYS5, note, 0.07, (-0.4, 3.4))


def fig_extra():
    note = (SEED_NOTE + "\n" + F6_NOTE.split(" Its load cells")[0] + "\n1000Genome was run in the simulator only (no live cell), with the ML cell's window, 10 nodes and no peak cap. Each run holds only 54, 80 and 88 requests (loads 0.5, 0.7, 0.9), "
            "so its P99 is set by one or two requests: differences of 10-20% are within the spread of the seeds. Trip Booking (350,000-630,000 requests per run) was not run for F6, B* and RL.\n" + CLU_NOTE)
    sweep("sim4_1000genome", "1000Genome (simulator): average and P99 makespan against nominal load", [0.5, 0.7, 0.9], ["0.5", "0.7", "0.9"], "nominal load",
          lambda app, x: f"x{x}", AVGP99, EXTRA, SYS5, note, 0.012, (0.455, 0.945))


def fig_costs():
    rows = [("cold", "Cold starts per run", 1.0, ("frozen6",)), ("mb", "State moved between nodes\n(MB per run)", 1.0)]
    note = (SEED_NOTE + "\n" + F6_NOTE + "\nCold starts: F6 is not drawn in that row. Cold starts are counted inside the measured window only, and F6's first re-layout happens in the warm-up, so its in-window count would look lower than it is (over the whole run its total equals that of F5, the same controller without the early start: 62 against 60 on MapReduce, 75 against 75 on Video, one cell each).\n"
            "A value of 0 is drawn at 1. B* starts from an initial layout that is not counted as cold starts; Heu and RL start empty and create every container on demand.\n"
            "State MB: every state moved between nodes, nominal size (the real bytes on the wire are 1/100). Load 0.5 as in the load figure.\n" + CLU_NOTE + " CLU starts empty like Heu and RL, so its cold starts are counted the same way.")
    sweep("sim5_costs_vs_load", "Cost side of the load sweep: cold starts and data moved (simulator)", [0.5, 0.7, 0.9], ["0.5", "0.7", "0.9"], "nominal load",
          lambda app, x: ref(app) if x == 0.5 else f"rho{x}", rows, APPS, SYS5, note, 0.012, (0.455, 0.945))


# ------------------------------------------------------------------------------------------------------------------- overview heat map
CONDS = [("base", "Live-cell twin\n(cap 300 tasks/s)"), ("unc", "Load 0.5, no cap"), ("rho0.7", "Load 0.7"), ("rho0.9", "Load 0.9"), ("ne20", "20 nodes"), ("ne40", "40 nodes"),
         ("cold2", "Cold start 2 s"), ("cold5", "Cold start 5 s"), ("cold10", "Cold start 10 s")]
CMAP = LinearSegmentedColormap.from_list("blue", SEQ)
CAP_RATIO = 30.0


def fig_overview():
    fig, axes = plt.subplots(1, 4, figsize=(14.2, 6.3))
    for j, (app, an) in enumerate(APPS):
        ax = axes[j]
        P = np.full((len(CONDS), len(SYS5)), np.nan)
        for r, (cs, _) in enumerate(CONDS):
            st = ref(app) if cs == "unc" else cs
            for c, (arm, *_) in enumerate(SYS5):
                if (st, app, 1, arm) in CELL:                                  # every condition has a CLU cell
                    P[r, c] = np.mean([x["p99"] for x in get(st, app, arm)])
        best = np.nanmin(P, axis=1, keepdims=True)
        V = np.clip(np.log(P / best) / np.log(CAP_RATIO), 0, 1)
        ax.pcolormesh(V, cmap=CMAP, vmin=0, vmax=1, edgecolors="white", linewidth=2.2)
        for r in range(P.shape[0]):
            for c in range(P.shape[1]):
                p = P[r, c]
                if np.isnan(p):
                    ax.text(c + 0.5, r + 0.5, "not run", ha="center", va="center", fontsize=7.5, color=INK2)
                    continue
                ax.text(c + 0.5, r + 0.5, f"{p:.1f}" if p < 10 else f"{p:,.0f}", ha="center", va="center", fontsize=9, color="white" if V[r, c] > 0.5 else INK,
                        fontweight="bold" if p == best[r, 0] else "normal")
        ax.set_xlim(0, len(SYS5))
        ax.set_ylim(len(CONDS), 0)
        ax.set_xticks(np.arange(len(SYS5)) + 0.5)
        ax.set_xticklabels([n.replace(" (ours)", "") for _, n, _, _ in SYS5])
        ax.xaxis.tick_top()
        ax.tick_params(length=0)
        ax.set_yticks(np.arange(len(CONDS)) + 0.5)
        ax.set_yticklabels([lab for _, lab in CONDS] if j == 0 else [])
        ax.grid(False)
        for sp in ax.spines.values():
            sp.set_visible(False)
        ax.set_title(an, fontsize=12.5, fontweight="bold", pad=26)
    cax = fig.add_axes([0.36, 0.185, 0.28, 0.02])
    grad = np.linspace(0, 1, 256)[None, :]
    cax.imshow(grad, aspect="auto", cmap=CMAP, extent=(0, 1, 0, 1))
    ticks = [1, 2, 5, 10, 30]
    cax.set_xticks([np.log(t) / np.log(CAP_RATIO) for t in ticks])
    cax.set_xticklabels([f"{t}x" if t < 30 else "30x or more" for t in ticks], fontsize=8.5)
    cax.set_yticks([])
    cax.grid(False)
    for sp in cax.spines.values():
        sp.set_visible(False)
    cax.set_xlabel("P99 relative to the best system in the same row", fontsize=9)
    fig.suptitle("Overview of the simulator studies: mean P99 makespan (s) over seeds 1-3, by system, app and condition", fontsize=12.5, y=0.985)
    fig.text(0.5, 0.0, "Bold: lowest P99 in the row. Shade: P99 relative to the row's best (white-blue 1x, dark blue 30x or more). Development seeds 1-3; simulator twin, CAP-W2 weights, Azure arrivals.\n"
             "For Video and ExCamera the peak cap never binds, so the live-cell twin and the 'Load 0.5, no cap' row are the same cell. MapReduce, load 0.5: the P99 of F5 was a start-up transient of the first ~120 s; F6 removes it.\n"
             "F6 = the controller F5 with its first re-layout at 10 s instead of at the end of the warm-up (adopted 16 Nov on these development seeds; not yet confirmed on fresh seeds).\n"
             "CLU = independent ClusterLess-style baseline (kappa 1.5, re-planned at every ready function), run in every row (Stage 1: load rows; Stage 2: node count and cold start; development seeds 1-3).",
             ha="center", va="bottom", fontsize=8, color=INK2)
    fig.subplots_adjust(left=0.115, right=0.99, top=0.83, bottom=0.29, wspace=0.06)
    save(fig, "sim6_overview_p99")


# ----------------------------------------------------------------------------------------------------------------------------- table
def write_table():
    studies = [("base", "live-cell twin (cap 300 tasks/s)"), ("unc0.5", "load 0.5, no cap"), ("rho0.7", "load 0.7"), ("rho0.9", "load 0.9"), ("ne20", "20 nodes"), ("ne40", "40 nodes"),
               ("cold2", "cold start 2 s"), ("cold5", "cold start 5 s"), ("cold10", "cold start 10 s"), ("x0.5", "1000Genome load 0.5"), ("x0.7", "1000Genome load 0.7"), ("x0.9", "1000Genome load 0.9")]
    with open(OUT / "sensitivity_table.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["study", "app", "system", "avg_makespan_s_mean", "p50_makespan_s_mean", "p99_makespan_s_mean", "p99_seed1", "p99_seed2", "p99_seed3", "cold_starts_mean", "state_mb_mean"])
        for st, lab in studies:
            for app, an in (EXTRA if st.startswith("x") else APPS):
                for arm, aname, *_ in SYS5:
                    if (st, app, 1, arm) not in CELL:
                        continue
                    c = get(st, app, arm)
                    w.writerow([lab, an, aname.replace(" (ours)", ""), f"{np.mean([x['avg'] for x in c]):.3f}", f"{np.mean([x['p50'] for x in c]):.3f}", f"{np.mean([x['p99'] for x in c]):.3f}",
                                *[f"{x['p99']:.3f}" for x in c], f"{np.mean([x['cold'] for x in c]):.0f}", f"{np.nanmean([x['mb'] for x in c]):.0f}"])


fig_load()
fig_nodes()
fig_cold()
fig_extra()
fig_costs()
fig_overview()
write_table()
print("written:", sorted(p.name for p in OUT.iterdir()))
