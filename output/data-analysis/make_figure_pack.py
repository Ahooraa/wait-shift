"""One PDF with every figure: a cover page (what the runs are, how to read the figures, the caveats) followed by the live-testbed figures and the simulator sensitivity figures.

  ~/venv-dfps/bin/python output/data-analysis/make_live_figures.py      # first the figures themselves
  ~/venv-dfps/bin/python output/data-analysis/make_sim_figures.py
  ~/venv-dfps/bin/python output/data-analysis/make_figure_pack.py       # then the pack: output/data-analysis/figures-for-professor.pdf

The pages are the PDFs written by the two figure scripts, joined with pdfunite (poppler); nothing is redrawn.
"""
import subprocess
import tempfile
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
LIVE, SIM = HERE / "live-figures", HERE / "sim-figures"
OUT = HERE / "figures-for-professor.pdf"
INK, INK2 = "#0b0b0b", "#52514e"

PAGES = [LIVE / n for n in ("fig1_makespan_load0.5", "fig2_load_0.5_vs_0.7", "fig4_live_vs_simulator_p99", "fig5_bars_makespan_and_cold_starts_load0.5",
                            "fig6_bars_makespan_and_cold_starts_load0.7", "fig3_cold_starts_and_state_moved", "fig7_costs_load0.5", "fig8_costs_load0.7")] + \
        [SIM / n for n in ("sim6_overview_p99", "sim1_load_sweep", "sim2_node_count", "sim3_cold_start_duration", "sim4_1000genome", "sim5_costs_vs_load")]

BLOCKS = [
    ("What this is", [
        "Evaluation of our controller against three baselines: Heu (online heuristic), B* (search-based planner) and RL (learned policy); in the load and cost figures of the simulator studies a fourth baseline, CLU, is added (17 Nov 2026). F5 is the controller of the live runs; F6 (adopted 16 Nov 2026) is F5 with its first re-layout at 10 s instead of at the end of the warm-up, which removes a start-up backlog in the first two minutes of the measured window.",
        "Workflows: ML, MapReduce, Video and ExCamera (live testbed and simulator); Trip Booking and 1000Genome (simulator only). Arrivals follow the Azure 2019 trace.",
        "Ten logical nodes (20 and 40 in one simulator study), container sizes by memory (CAP-W2). Seeds 1-3 only: the development seeds; the held-out seeds 7-10 have not been run.",
        "Makespan = time from a request's arrival to the end of its last task. P99 is taken over the requests that arrive in the measured window.",
        "Nominal load = offered load relative to the cluster's capacity. The peak cap scales the arrival trace so that its busiest minute offers at most 300 tasks/s (the testbed hub sustains about 350). "
        "The live runs and the cold-start studies use it; the load and node-count studies do not. For Video and ExCamera the cap never binds.",
    ]),
    ("Part A - main runs on the emulated testbed (60 live runs)", [
        "Pages 2-9. 48 runs at nominal load 0.5 (4 apps x 4 systems x 3 seeds) and 12 runs at load 0.7 (Video and ExCamera, F5 and Heu). These are F5 runs: F6 has not been run on the testbed yet, and the live F5 runs started from the late first re-layout.",
        "Contents: makespan (average and P99); F5 against Heu at load 0.5 and 0.7; each live run's P99 against its simulator twin (page 4: ratio, grey band 0.83-1.21); "
        "average, median, P99 and cold starts as bars (load 0.5 and 0.7); cold starts and data moved; cold starts, container creations, cold-start time and data moved (load 0.5 and 0.7).",
    ]),
    ("Part B - sensitivity studies in the simulator: F6, Heu, B*, RL and CLU (all runs finished)", [
        "Pages 10-15. An overview heat map of the mean P99 of every study, then one figure per study: load 0.5 / 0.7 / 0.9; 10 / 20 / 40 nodes; "
        "cold-start duration measured (0.2-0.3 s) / 2 / 5 / 10 s; 1000Genome (a fifth workflow, tiny runs of 54-88 requests); data moved against load. F5 is not drawn in these figures; it is the controller of the live runs in Part A. Trip Booking, the sixth workflow, was not run for F6, B* and RL. CLU is an independent single-cluster reduction of ClusterLess (arXiv 2605.04310), a deadline-aware workflow scheduler (deadline = 1.5 x the longest path of nominal times, re-planned at every ready function); it uses the container model of Heu and RL and received no tuning. It was run for the load conditions only (live-cell twin, load 0.5 without cap, 0.7, 0.9; 4 apps x seeds 1-3); the node-count, cold-start and 1000Genome studies show no CLU, and the overview marks those rows 'not run'.",
    ]),
    ("Read with care", [
        "Three seeds per cell: the dots in the figures are the individual seeds, there are no confidence intervals.",
        "P99 includes the first minutes of the measured window. For MapReduce at load 0.5 without a peak cap, F5's P99 is a start-up transient of the first ~120 s "
        "(diagnosed on seeds 1-3; from 120 s on its P99 is 2-5 s). Other cells have not been examined for this, and it is not yet decided whether the warm-up or the reporting window changes.",
        "Cold starts: F5 and B* start from an initial layout that is not counted as cold starts; Heu and RL start empty and create every container on demand. In the sensitivity figures F6 is left out of the cold-start panels: cold starts are counted inside the measured window only and F6's first re-layout happens in the warm-up, so its in-window count would look lower than it is (the total over the run equals F5's).",
        "F6 was chosen on the development seeds 1-3 that these figures use; a confirmation on fresh seeds (4-6) and a live run are still to do.",
        "Live load 0.7: Heu left requests unfinished on ExCamera (26 and 5 requests on seeds 1 and 2); they are not counted in its makespans.",
        "1000Genome runs hold only 54-88 requests, so its P99 is set by one or two requests and differences of 10-20% are within the spread of the seeds.",
        "Not yet run: the payload-size sensitivity, the repeatability runs and the held-out seeds.",
    ]),
]


def cover(path):
    fig = plt.figure(figsize=(11.69, 8.27))
    fig.text(0.06, 0.94, "F5 evaluation: figures", fontsize=20, fontweight="bold", color=INK, va="top")
    fig.text(0.06, 0.895, "Emulated testbed (main runs) and simulator sensitivity studies - generated 16-17 November 2026", fontsize=11, color=INK2, va="top")
    y = 0.845
    for title, paras in BLOCKS:
        fig.text(0.06, y, title, fontsize=12.5, fontweight="bold", color=INK, va="top")
        y -= 0.036
        for para in paras:
            for k, ln in enumerate(textwrap.wrap(para, 150)):
                fig.text(0.07 + (0.012 if k else 0), y, ln, fontsize=9, color=INK, va="top")
                y -= 0.025
            y -= 0.006
        y -= 0.018
    fig.savefig(path)
    plt.close(fig)


with tempfile.TemporaryDirectory() as tmp:
    c = Path(tmp) / "cover.pdf"
    cover(c)
    pdfs = [c] + [Path(str(p) + ".pdf") for p in PAGES]
    missing = [str(p) for p in pdfs if not p.exists()]
    assert not missing, missing
    subprocess.run(["pdfunite", *map(str, pdfs), str(OUT)], check=True)
print("written:", OUT, f"({len(pdfs)} pages)")
