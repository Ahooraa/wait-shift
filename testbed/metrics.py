"""Cold-start metrics for the testbed results (DEV-T6).

The measured SeBS-Flow cold starts are short (0.22-0.35 s, runtime initialisation on a cloud platform). If a cold start only counted by the
latency it adds, a controller that avoids cold starts would look less valuable than it is: every cold start still costs an initialisation
on an edge node (CPU, memory, an image pull on a real edge node) however brief it is on a cloud platform. So the COUNT of cold starts is
reported next to the latency, per request and per task, and the time they cost is shown under two models, the measured one and the DFPS
paper's 2-10 s range (mean 6 s), labelled as what they are. The count itself does not depend on the duration model at all.

    from testbed.metrics import cold_start_metrics
    res.update(cold_start_metrics(res, sc, window_s=sim.duration - sim.warmup, warmup=sim.warmup))
"""
from __future__ import annotations

import numpy as np

PAPER_MEAN_COLD_S = 6.0                    # DFPS Table 2: cold-start delay 2-10 s, mean 6 s


def cold_start_metrics(res, sc, window_s, warmup=0.0, paper_mean_cold_s=PAPER_MEAN_COLD_S):
    """Counts of cold starts in the measured window, normalised, and the time they cost under two models."""
    n_cold = int(res["cold_starts"])
    in_window = [(t, w) for t, w, _ in sc.arrivals if warmup <= t < warmup + window_s]
    n_req = int(res.get("n_arrived") or len(in_window))
    n_tasks = int(sum(sc.workflows[w].n for _, w in in_window))
    mean_init = float(np.mean([f.cold_start for f in sc.functions]))
    ratios = sc.meta.get("cold_init_over_median_task") or {}
    return {
        "cold_starts": n_cold,                                          # containers started cold in the window (the primary number)
        "cold_starts_per_request": n_cold / n_req if n_req else float("nan"),
        "cold_starts_per_100_tasks": 100.0 * n_cold / n_tasks if n_tasks else float("nan"),
        "cold_starts_per_s": n_cold / window_s if window_s > 0 else float("nan"),
        "cold_starts_total": int(res.get("cold_starts_total", n_cold)),  # including the warm-up
        "cold_time_measured_model_s": n_cold * mean_init,               # estimate: count x mean measured initialisation of the scenario's functions
        "cold_time_paper_model_s": n_cold * paper_mean_cold_s,          # what the same count would cost under the DFPS 2-10 s range (hypothetical)
        "cold_init_over_median_task_mean": float(np.mean(list(ratios.values()))) if ratios else float("nan"),
    }
