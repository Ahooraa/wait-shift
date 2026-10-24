"""Plot our reproduction of DFPS Figs. 5-7 in the paper's own panel layout, and crop the paper's figures for side-by-side slides.

  python -I output/data-analysis/plot_fig567.py

Input:  output/data-analysis/results/fig567_reproduction_cal.json (calibrated scenario, seeds 1-5, mean per point)
Output: output/data-analysis/figures/repro_fig{5,6,7}.png            (ours, 3 metrics x Uniform/Pareto)
        output/presentation/figs/repro_fig{5,6,7}.png                 (copies for the deck)
        output/presentation/figs/paper_fig{5,6,7}.png                 (the paper's figures, cropped from the PDF, internal use only)
Panel layout, method names, colours and markers follow the paper (Figs. 5-7, pp. 10-12) so the two can be compared at a glance.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
RES = ROOT / "output" / "data-analysis" / "results" / "fig567_reproduction_cal.json"
FIGDIR = ROOT / "output" / "data-analysis" / "figures"
DECK = ROOT / "output" / "presentation" / "figs"

# the paper's legend order, colours and markers (Figs. 5-7)
STYLE = {
    "SR": dict(color="#1f4e79", marker="D", label="SR"),
    "SG": dict(color="#ed7d31", marker="s", label="SG"),
    "RL": dict(color="#2e7d32", marker="^", label="RL"),
    "DFPS": dict(color="#4fc3f7", marker="x", label="B*"),
    "HEU": dict(color="#a0449e", marker="*", label="Heu"),
}
ORDER = ("SR", "SG", "RL", "DFPS", "HEU")
XLAB = {"fig5": "Request rate", "fig6": "Network size", "fig7": "Application types"}
METRICS = (("makespan", "Average makespan (sec)", 1.0), ("util", "Utilization (%)", 1.0), ("cold", "Cold start count", 1.0))
TITLE = {"fig5": "Fig. 5 reproduced: varying arrival rates", "fig6": "Fig. 6 reproduced: varying network sizes",
         "fig7": "Fig. 7 reproduced: varying application diversity"}


def xs_of(fig, pts):
    if fig == "fig5":                       # the paper labels the 8 scale factors 0.25..2 as request rate 1..8
        return list(range(1, len(pts) + 1))
    return [p["x"] for p in pts]


def plot(fig, data):
    f, axes = plt.subplots(3, 2, figsize=(10, 11.5), dpi=150)
    for r, (key, ylab, _) in enumerate(METRICS):
        for c, kind in enumerate(("uniform", "pareto")):
            ax = axes[r, c]
            for m in ORDER:
                pts = data[kind][m]
                ys = [p[key] for p in pts]
                st = STYLE[m]
                ax.plot(xs_of(fig, pts), ys, color=st["color"], marker=st["marker"], markersize=5, linewidth=1.6, label=st["label"])
            ax.set_title(f"{kind.capitalize()} Workload", fontsize=12, fontweight="bold", color="#555555")
            ax.set_xlabel(XLAB[fig], fontsize=9)
            ax.set_ylabel(ylab, fontsize=9)
            ax.set_ylim(bottom=0)
            if fig != "fig5":
                ax.set_xticks([p["x"] for p in data[kind]["SR"]])
            ax.grid(axis="y", color="#dddddd", linewidth=0.6)
            ax.tick_params(labelsize=8)
            for s in ("top", "right"):
                ax.spines[s].set_visible(False)
            ax.legend(fontsize=7.5, frameon=False, loc="best")
    f.suptitle(TITLE[fig] + " (our simulator, calibrated scenario, mean of 5 workloads)", fontsize=11)
    f.tight_layout(rect=(0, 0, 1, 0.975))
    out = FIGDIR / f"repro_{fig}.png"
    f.savefig(out, facecolor="white")
    plt.close(f)
    shutil.copy(out, DECK / out.name)
    return out


def crop_paper():
    import fitz
    from library import pdf_for
    doc = fitz.open(pdf_for("zolfaghari-2025-dynamic-function-placement"))
    for fig, page in (("fig5", 9), ("fig6", 10), ("fig7", 11)):
        p = doc[page]
        r = p.rect
        clip = fitz.Rect(0.08 * r.width, 0.055 * r.height, 0.49 * r.width, 0.515 * r.height)
        p.get_pixmap(dpi=200, clip=clip).save(str(DECK / f"paper_{fig}.png"))


if __name__ == "__main__":
    FIGDIR.mkdir(parents=True, exist_ok=True)
    DECK.mkdir(parents=True, exist_ok=True)
    data = json.loads(RES.read_text())
    for fig in ("fig5", "fig6", "fig7"):
        print(plot(fig, data[fig]))
    crop_paper()
    print("paper figures cropped to", DECK)
