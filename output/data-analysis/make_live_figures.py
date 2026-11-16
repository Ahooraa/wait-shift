"""Figures for the live (emulated-testbed) runs, CAP-W2, Azure arrivals.

Reads the two live result directories (never writes into them) and writes PNG + PDF into output/data-analysis/live-figures/.

  ~/venv-dfps/bin/python output/data-analysis/make_live_figures.py

Runs  : azure-capw2-20261114 (nominal load 0.5; 4 apps x 4 systems x seeds 1-3 = 48 runs)
        azure-capw2-rho07-20261115 (nominal load 0.7; Video and ExCamera, F5 and Heu, seeds 1-3 = 12 runs)
Colours: the reference palette's first four slots in fixed order (one colour per system, in every figure).
Seeds 1-3 are development seeds; the held-out seeds 7-10 are not used.
"""
import glob
import json
from pathlib import Path

import matplotlib
import matplotlib.ticker

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HOME = Path.home()
MAIN = HOME / "testbed-results/azure-capw2-20261114/items"
HIGH = HOME / "testbed-results/azure-capw2-rho07-20261115/items"
OUT = Path(__file__).resolve().parent / "live-figures"
OUT.mkdir(exist_ok=True)

APPS = [("690.ml", "ML"), ("660.map-reduce", "MapReduce"), ("650.vid", "Video"), ("680.excamera", "ExCamera")]
SYS = [("frozen5", "F5 (ours)", "#2a78d6"), ("heu", "Heu", "#eb6834"), ("bstar", "B*", "#1baf7a"), ("rl", "RL", "#eda100")]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": INK2, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "text.color": INK, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.7,
                     "axes.axisbelow": True, "figure.facecolor": "white", "axes.facecolor": "white", "legend.frameon": False})


def load(d):
    rows = []
    for f in sorted(glob.glob(str(d / "controller-*.json"))):
        rows += json.load(open(f))["rows"]
    return rows


main, high = load(MAIN), load(HIGH)
assert len(main) == 48 and len(high) == 12, (len(main), len(high))


def pick(rows, app, arm, key):
    return np.array([r["live"][key] if key in r["live"] else r["resources"][key] for r in sorted(rows, key=lambda r: r["seed"]) if r["app"] == app and r["arm"] == arm])


def save(fig, name):
    fig.savefig(OUT / f"{name}.png", dpi=200, bbox_inches="tight")
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)


def legend_handles():
    from matplotlib.patches import Patch
    return [Patch(facecolor=c, label=n) for _, n, c in SYS]


# ---- Figure 1: the main result, nominal load 0.5 -------------------------------------------------------------------------------------
def fig_main():
    fig, axes = plt.subplots(2, 4, figsize=(12.5, 6.2))
    for j, (app, an) in enumerate(APPS):
        for i, (key, lab) in enumerate([("avg_makespan", "Average makespan (s)"), ("p99_makespan", "P99 makespan (s)")]):
            ax = axes[i, j]
            for k, (arm, _, col) in enumerate(SYS):
                v = pick(main, app, arm, key)
                ax.bar(k, v.mean(), width=0.62, color=col, zorder=2)
                ax.scatter(np.full(len(v), k) + np.linspace(-0.1, 0.1, len(v)), v, s=14, color=INK, zorder=3, linewidths=0)     # the three seeds
                ax.text(k, v.max() + 0.02 * ax.get_ylim()[1], f"{v.mean():.2f}" if v.mean() < 10 else f"{v.mean():.0f}", ha="center", va="bottom", fontsize=8.5, color=INK2)
            ax.set_xticks([])
            ax.margins(y=0.14)
            ax.set_ylim(bottom=0)
            if i == 0:
                ax.set_title(an, fontsize=12, fontweight="bold", color=INK)
            if j == 0:
                ax.set_ylabel(lab)
    fig.legend(handles=legend_handles(), loc="lower center", ncol=4, bbox_to_anchor=(0.5, -0.02), fontsize=10)
    fig.suptitle("Makespan on the emulated testbed at nominal load 0.5 (mean of seeds 1-3; dots are the individual seeds)", fontsize=12, y=1.0)
    fig.tight_layout(rect=(0, 0.03, 1, 0.97))
    save(fig, "fig1_makespan_load0.5")


# ---- Figure 2: the same two systems at load 0.5 and 0.7 ---------------------------------------------------------------------------------
def fig_load():
    fig, axes = plt.subplots(2, 2, figsize=(8.6, 6.4))
    for j, (app, an) in enumerate([("650.vid", "Video"), ("680.excamera", "ExCamera")]):
        for i, (key, lab) in enumerate([("avg_makespan", "Average makespan (s)"), ("p99_makespan", "P99 makespan (s)")]):
            ax = axes[i, j]
            for arm, name, col in SYS[:2]:
                lo, hi = pick(main, app, arm, key), pick(high, app, arm, key)
                ax.plot([0.5, 0.7], [lo.mean(), hi.mean()], color=col, lw=2, marker="o", ms=8, markeredgecolor="white", markeredgewidth=1.5, zorder=3, label=name)
                ax.scatter(np.full(3, 0.5), lo, s=12, color=col, alpha=0.45, zorder=2, linewidths=0)
                ax.scatter(np.full(3, 0.7), hi, s=12, color=col, alpha=0.45, zorder=2, linewidths=0)
                ax.annotate(f"{hi.mean():.0f}", (0.7, hi.mean()), textcoords="offset points", xytext=(8, 0), va="center", fontsize=9, color=INK2)
            ax.set_xticks([0.5, 0.7])
            ax.set_xlim(0.45, 0.76)
            ax.set_ylim(bottom=0)
            if i == 1:
                ax.set_xlabel("nominal load")
            if j == 0:
                ax.set_ylabel(lab)
            if i == 0:
                ax.set_title(an, fontsize=12, fontweight="bold")
    axes[0, 0].legend(loc="upper left")
    fig.suptitle("F5 against Heu when the load rises (lines: mean of seeds 1-3; faint dots: seeds)", fontsize=11.5, y=0.995)
    fig.text(0.5, -0.01, "Heu left 26 and 5 requests unfinished on ExCamera seeds 1 and 2 at load 0.7; these are not counted in its makespans.", ha="center", fontsize=8.5, color=INK2)
    fig.tight_layout(rect=(0, 0.01, 1, 0.97))
    save(fig, "fig2_load_0.5_vs_0.7")


# ---- Figure 3: what each system spends (cold starts, data moved) -------------------------------------------------------------------------
def fig_resources():
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), sharey=True)
    for ax, (key, lab) in zip(axes, [("cold_starts", "Cold starts per run (log scale)"), ("state_mb", "State moved between nodes, MB per run (log scale)")]):
        for j, (app, an) in enumerate(APPS):
            for k, (arm, _, col) in enumerate(SYS):
                v = pick(main, app, arm, key).astype(float)
                v = np.maximum(v, 1.0)
                y = j + (k - 1.5) * 0.17
                ax.scatter(v, np.full(len(v), y), s=14, color=col, alpha=0.35, linewidths=0, zorder=2)
                ax.scatter([v.mean()], [y], s=70, color=col, edgecolors="white", linewidths=1.2, zorder=3)
        ax.set_xscale("log")
        ax.set_yticks(range(4))
        ax.set_yticklabels([a for _, a in APPS])
        ax.set_xlabel(lab)
        ax.grid(axis="y", visible=False)
    axes[0].invert_yaxis()                                   # the axes share y: invert once, so ML is on top
    fig.legend(handles=legend_handles(), loc="lower center", ncol=4, bbox_to_anchor=(0.5, -0.04))
    fig.suptitle("Cost side at nominal load 0.5 (large dot: mean of seeds 1-3; small dots: seeds; values below 1 are drawn at 1)", fontsize=11, y=1.0)
    fig.tight_layout(rect=(0, 0.04, 1, 0.97))
    save(fig, "fig3_cold_starts_and_state_moved")


# ---- Figure 4: does the live testbed agree with the simulator? ------------------------------------------------------------------------------
def fig_twin():
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    ax.axhspan(0.83, 1.21, color=GRID, zorder=0)
    ax.axhline(1.0, color=INK2, lw=1, zorder=1)
    for j, (app, an) in enumerate(APPS):
        for k, (arm, _, col) in enumerate(SYS):
            rs = [r for r in main + high if r["app"] == app and r["arm"] == arm and r["live"]["n_completed"] >= 0.99 * r["live"]["n_arrived"]]
            y = np.array([r["p99_ratio"] for r in rs])
            ax.scatter(np.full(len(y), j) + (k - 1.5) * 0.17 + np.linspace(-0.03, 0.03, len(y)), y, s=26, color=col, edgecolors="white", linewidths=0.6, zorder=3)
    ax.set_xticks(range(4))
    ax.set_xticklabels([a for _, a in APPS])
    ax.set_yscale("log")
    ax.set_yticks([0.5, 0.7, 1, 1.4, 2])
    ax.set_yticklabels(["0.5", "0.7", "1", "1.4", "2"])
    ax.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.set_ylim(0.4, 2.6)
    ax.set_ylabel("live P99 / simulator P99")
    ax.grid(axis="x", visible=False)
    ax.legend(handles=legend_handles(), loc="upper center", ncol=4, bbox_to_anchor=(0.5, -0.08))
    ax.set_title("Live testbed against the simulator twin, one dot per run (grey band: 0.83-1.21)", fontsize=11)
    fig.text(0.5, -0.1, "Completed runs only (those with all requests finished). Includes the load 0.5 and load 0.7 batches.", ha="center", fontsize=8.5, color=INK2)
    fig.tight_layout()
    save(fig, "fig4_live_vs_simulator_p99")


fig_main()
fig_load()
fig_resources()
fig_twin()

# ---- Figure 5/6: average, median, P99 and cold starts as bars (one panel per app) ------------------------------------------------------------
def fig_bars(rows, apps, systems, title, name):
    stats = [("avg_makespan", "Average makespan (s)", False), ("p50_makespan", "Median makespan (s)", False), ("p99_makespan", "P99 makespan (s)", False), ("cold_starts", "Cold starts per run\n(log scale)", True)]
    fig, axes = plt.subplots(4, len(apps), figsize=(3.1 * len(apps) + 0.6, 9.2), squeeze=False)
    for j, (app, an) in enumerate(apps):
        for i, (key, lab, logy) in enumerate(stats):
            ax = axes[i, j]
            for k, (arm, _, col) in enumerate(systems):
                v = np.array([r["live"][key] for r in sorted(rows, key=lambda r: r["seed"]) if r["app"] == app and r["arm"] == arm], dtype=float)
                if logy:
                    v = np.maximum(v, 1.0)
                ax.bar(k, v.mean(), width=0.62, color=col, zorder=2)
                ax.scatter(np.full(len(v), k) + np.linspace(-0.1, 0.1, len(v)), v, s=13, color=INK, zorder=3, linewidths=0)
                txt = f"{v.mean():,.0f}" if (logy or v.mean() >= 10) else f"{v.mean():.2f}"
                ax.annotate(txt, (k, v.max()), textcoords="offset points", xytext=(0, 4), ha="center", fontsize=8.5, color=INK2)
            ax.set_xticks([])
            if logy:
                ax.set_yscale("log")
                ax.set_ylim(1, ax.get_ylim()[1] * 3)
            else:
                ax.margins(y=0.14)
                ax.set_ylim(bottom=0)
            if i == 0:
                ax.set_title(an, fontsize=12, fontweight="bold")
            if j == 0:
                ax.set_ylabel(lab)
    from matplotlib.patches import Patch
    fig.legend(handles=[Patch(facecolor=c, label=n) for _, n, c in systems], loc="lower center", ncol=len(systems), bbox_to_anchor=(0.5, 0.012), fontsize=10)
    fig.suptitle(title, fontsize=12, y=0.998)
    initial = "F5 and B* start" if any(a == "bstar" for a, _, _ in systems) else "F5 starts"
    totals = "(F5 creates 158-270 containers per run in total, B* 2,100-5,400)" if initial.startswith("F5 and") else "(F5 creates about 240-270 containers per run in total)"
    fig.text(0.5, -0.005, f"Bars: mean of seeds 1-3; dots: seeds. Cold starts count containers created on demand: {initial} from an initial layout that is not counted\n{totals}. A cold-start count of 0 is drawn at 1.", ha="center", fontsize=8, color=INK2)
    fig.tight_layout(rect=(0, 0.045, 1, 0.985))
    save(fig, name)


fig_bars(main, APPS, SYS, "Average, median, P99 makespan and cold starts at nominal load 0.5 (48 runs)", "fig5_bars_makespan_and_cold_starts_load0.5")
fig_bars(high, [("650.vid", "Video"), ("680.excamera", "ExCamera")], SYS[:2], "Same measures at nominal load 0.7 (F5 and Heu; Video and ExCamera)", "fig6_bars_makespan_and_cold_starts_load0.7")


# ---- Figure 7/8: cold starts, creations incl. the initial layout, cold container-seconds, state MB ------------------------------------------------
def creations(r):
    """Containers created in the run: cold starts plus the initial layout. The initial layout is estimated by the containers provisioned on average over the window (F5, B*); the
    on-demand systems (Heu, RL) start empty, so for them the cold starts are the creations."""
    init = r["resources"]["provisioned_container_s"] / r["resources"]["window_s"] if r["arm"] in ("frozen5", "bstar") else 0.0
    return r["live"]["cold_starts"] + init


COSTS = [(lambda r: r["live"]["cold_starts"], "Cold starts per run", 1.0),
         (creations, "Container creations incl.\ninitial layout per run", 1.0),
         (lambda r: r["resources"]["cold_container_s"], "Cold-start container-seconds\nper run", 0.1),
         (lambda r: r["resources"]["state_mb"], "State moved between\nnodes (MB) per run", 1.0)]


def fig_costs(rows, apps, systems, title, name):
    fig, axes = plt.subplots(4, len(apps), figsize=(3.1 * len(apps) + 0.8, 9.4), squeeze=False)
    for j, (app, an) in enumerate(apps):
        for i, (f, lab, floor) in enumerate(COSTS):
            ax = axes[i, j]
            for k, (arm, _, col) in enumerate(systems):
                raw = np.array([f(r) for r in sorted(rows, key=lambda r: r["seed"]) if r["app"] == app and r["arm"] == arm], dtype=float)
                v = np.maximum(raw, floor)
                ax.bar(k, v.mean(), width=0.62, color=col, zorder=2)
                ax.scatter(np.full(len(v), k) + np.linspace(-0.1, 0.1, len(v)), v, s=13, color=INK, zorder=3, linewidths=0)
                m = raw.mean()                                              # the label shows the real mean (0 stays 0), the bar is drawn at the axis floor
                txt = "0" if m == 0 else (f"{m:,.0f}" if m >= 10 else f"{m:.1f}")
                ax.annotate(txt, (k, v.max()), textcoords="offset points", xytext=(0, 4), ha="center", fontsize=8.5, color=INK2)
            ax.set_xticks([])
            ax.set_yscale("log")
            lo = ax.get_ylim()[0]
            ax.set_ylim(floor, ax.get_ylim()[1] * 4)
            if i == 0:
                ax.set_title(an, fontsize=12, fontweight="bold")
            if j == 0:
                ax.set_ylabel(lab + "\n(log scale)")
    from matplotlib.patches import Patch
    fig.legend(handles=[Patch(facecolor=c, label=n) for _, n, c in systems], loc="lower center", ncol=len(systems), bbox_to_anchor=(0.5, 0.012), fontsize=10)
    fig.suptitle(title, fontsize=12, y=0.998)
    fig.text(0.5, -0.012, "Bars: mean of seeds 1-3; dots: seeds. Log axes: a value of 0 is drawn at the axis floor (1; 0.1 for container-seconds).\n"
             f"Creations = cold starts + initial layout. {'F5 and B* start' if any(a == 'bstar' for a, _, _ in systems) else 'F5 starts'} from an initial layout that is not counted as cold starts; its size is estimated by the containers provisioned on average over the window.\n"
             f"{'Heu and RL start empty and create' if any(a == 'rl' for a, _, _ in systems) else 'Heu starts empty and creates'} everything on demand. State MB: every state moved between nodes, nominal size (the real bytes on the wire are 1/100).",
             ha="center", fontsize=7.8, color=INK2)
    fig.tight_layout(rect=(0, 0.06, 1, 0.985))
    save(fig, name)


fig_costs(main, APPS, SYS, "Cold starts, container creations, cold-start time and data moved at nominal load 0.5 (48 runs)", "fig7_costs_load0.5")
fig_costs(high, [("650.vid", "Video"), ("680.excamera", "ExCamera")], SYS[:2], "Same measures at nominal load 0.7 (F5 and Heu; Video and ExCamera)", "fig8_costs_load0.7")

print("written:", sorted(p.name for p in OUT.iterdir()))
