"""Paper tables from existing results, no new runs (2026-10-24), answering the second review's presentation points.

  T1  the 2x2 grid with raw P99 seconds per cell, the pairing, the four conditional effects and the log interaction with a CI
  T2  absolute P99 completion latency per controller, per load and family, on held-out seeds, with the number of requests behind
      each P99 (the sample size the reviewer asked for)
  T3  admission control as a 2x2 ({B*, FROZEN-1} x {off, on}) on the overload set, goodput and P99 of admitted requests

Metric: P99 completion latency = 99th percentile of (completion time - arrival time) over the requests that ARRIVE in the measured
window (900 s after a 60 s warm-up). Pairing: every controller runs the same scenario (arrivals, workflows, network), the same initial
NSGA-II layout and the same simulator seed; random task durations are drawn in event order, so they are not common random numbers.

  python output/data-analysis/paper_tables.py   ->  output/data-analysis/results/paper_tables.md
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from d1_rlla import BASE, D1, D3S, boot  # noqa: E402

M = "p99_makespan"
OUT = ROOT / "output" / "data-analysis" / "results" / "paper_tables.md"
D2 = ROOT / "results" / "d2_headroom"


def ctrl(dirs, names):
    o = {}
    for d_ in dirs:
        for f in d_.glob("*.json"):
            x = json.loads(f.read_text())
            if x.get("ctrl") in names:
                o.setdefault(x["ctrl"], {})[(x["family"], x["rho"], x["seed"])] = x["result"]
    return o


def ours(suffix):
    o = {}
    for f in D3S.glob(f"*.O3S_h120_blind_nosim_{suffix}.json"):
        x = json.loads(f.read_text())
        o[(x["family"], x["rho"], x["seed"])] = x["result"]
    return o


def main():
    L = []
    w = L.append
    base = ctrl((D1, BASE), ("B_STAR", "RL", "RL_CAL"))
    # ---------------------------------------------------------------- T1
    w("## T1. Re-layout x request moves (development seeds 1-3, 18 paired cases, B* annealing off in every cell)\n")
    cells = {"A": ("fixed starting layout, no moves", ours("x0")), "B": ("fixed starting layout + request moves", ours("x0_rebal")),
             "C": ("re-layout every 60 s, no moves", ours("noinner")), "D": ("re-layout every 60 s + request moves", ours("rebal"))}
    ks = sorted(k for k in set.intersection(*(set(v[1]) for v in cells.values())) if k[2] <= 3 and k in base["B_STAR"])
    w("Configuration used for this grid: affinity placement, request moves capped at 300 per round (the configuration at the time "
      "of the experiment, not FROZEN-1). Raw P99 completion latency in seconds.\n")
    w("| Cell | Re-layout | Request moves | Mean P99 (s) | Median (s) | Geometric mean (s) |")
    w("|---|---|---|---|---|---|")
    w("| B* (reference) | annealing swaps | inside annealing | %.0f | %.0f | %.0f |" % (
        np.mean([base["B_STAR"][k][M] for k in ks]), np.median([base["B_STAR"][k][M] for k in ks]),
        np.exp(np.mean(np.log([base["B_STAR"][k][M] for k in ks])))))
    lg = {}
    for c, (lab, r) in cells.items():
        v = np.array([r[k][M] for k in ks])
        lg[c] = np.log(v)
        w("| %s | %s | %s | %.0f | %.0f | %.0f |" % (c, "yes" if c in "CD" else "no", "yes" if c in "BD" else "no", v.mean(), np.median(v),
                                                      np.exp(lg[c].mean())))
    eff = {"moves, on a fixed layout (A to B)": lg["A"] - lg["B"], "moves, with re-layout (C to D)": lg["C"] - lg["D"],
           "re-layout, without moves (A to C)": lg["A"] - lg["C"], "re-layout, with moves (B to D)": lg["B"] - lg["D"],
           "both together (A to D)": lg["A"] - lg["D"]}
    w("\nConditional effects, as factors by which the geometric-mean P99 shrinks (95% bootstrap interval over cases):\n")
    w("| Effect | Factor | Interval |")
    w("|---|---|---|")
    for lab, v in eff.items():
        b = boot(v)
        w("| %s | x%.1f | x%.1f to x%.1f |" % (lab, np.exp(b["mean"]), np.exp(b["lo"]), np.exp(b["hi"])))
    inter = (lg["A"] - lg["B"]) - (lg["C"] - lg["D"])
    b = boot(inter)
    w("\nInteraction (log scale, 0 = the effects multiply independently): %.2f (%.2f to %.2f). Moves help more when the layout adapts:"
      " x%.1f with re-layout against x%.1f without. Consistency check: A to D = (A to B)(B to D) = (A to C)(C to D).\n" % (
          b["mean"], b["lo"], b["hi"], np.exp((lg["C"] - lg["D"]).mean()), np.exp((lg["A"] - lg["B"]).mean())))
    # ---------------------------------------------------------------- T2
    w("## T2. Absolute P99 completion latency on held-out seeds 4-10 (FROZEN-1 at 60 s vs the existing methods)\n")
    fz = ours("nl_fz60")
    w("| Family | Load | Cases | FROZEN-1 (s) | B* (s) | RL (s) | Calibrated RL (s) | Requests per P99 (mean) |")
    w("|---|---|---|---|---|---|---|---|")
    for fam in ("F1", "F2"):
        for rho in (0.5, 0.7, 0.85):
            kk = [k for k in fz if k[0] == fam and k[1] == rho and 4 <= k[2] <= 10 and all(k in base[m] for m in ("B_STAR", "RL", "RL_CAL"))]
            if not kk:
                continue
            mean = lambda r: np.mean([r[k][M] for k in kk])  # noqa: E731
            w("| %s | %.0f%% | %d | %.0f | %.0f | %.0f | %.0f | %.0f |" % ("Azure" if fam == "F1" else "Huawei", 100 * rho, len(kk), mean(fz),
                                                                             mean(base["B_STAR"]), mean(base["RL"]), mean(base["RL_CAL"]),
                                                                             np.mean([fz[k]["n_completed"] for k in kk])))
    w("\nThe P99 of one run rests on about 1% of the requests counted in the last column (e.g. 200 requests for 20,000). At 50% load "
      "even a system with no queueing and no cold starts has a P99 near 88 s (exponential task durations, Monte Carlo floor), so "
      "relative gains are compressed there; 85% load is where the controllers differ most.\n")
    # ---------------------------------------------------------------- T3
    w("## T3. Admission control on the overload set ({B*, ours} x {off, on}) (20 cases: Azure and Huawei overload windows, seeds 1-10)\n")
    g = {"B*": [], "B* + admission": [], "Ours": [], "Ours + admission": []}
    p = {k: [] for k in g}
    rej = {k: [] for k in g}
    for fam in ("F1", "F2"):
        for s in range(1, 11):
            f0, fa, fb = D2 / f"{fam}_s{s}.json", D2 / f"{fam}_s{s}.ours.json", D2 / f"{fam}_s{s}.ours_adm.json"
            if not (f0.exists() and fa.exists() and fb.exists()):
                continue
            d0 = json.loads(f0.read_text())
            rows = {"B*": d0["B_STAR"], "B* + admission": d0["HEUR"], "Ours": json.loads(fa.read_text())["result"],
                    "Ours + admission": json.loads(fb.read_text())["result"]}
            for k, r in rows.items():
                g[k].append(r["slo_goodput"])
                p[k].append(r[M])
                rej[k].append(r.get("n_rejected", 0) / max(1, r["n_arrived"]))
    w("Admission rule (both controllers, untuned): admit a request only if the requests in the system are at most 1.0 x the number "
      "of container slots. Goodput = workflows finishing within 3 x their unloaded critical path, per second. The controller in "
      "these runs is ours in its k-median version of the time, not FROZEN-1; the admission effect is the comparison of interest.\n")
    w("| Controller | No admission: goodput | With admission: goodput | Rejected | P99 of admitted (s) |")
    w("|---|---|---|---|---|")
    for a, b2 in (("B*", "B* + admission"), ("Ours", "Ours + admission")):
        w("| %s | %.2f | %.2f | %.0f%% | %.0f -> %.0f |" % (a, np.mean(g[a]), np.mean(g[b2]), 100 * np.mean(rej[b2]), np.mean(p[a]), np.mean(p[b2])))
    w("\nAdmission multiplies goodput by x%.1f for B* and x%.1f for our controller; with and without admission our controller is ahead "
      "(x%.1f without, x%.1f with). Cases: %d.\n" % (np.mean(g["B* + admission"]) / np.mean(g["B*"]), np.mean(g["Ours + admission"]) / np.mean(g["Ours"]),
                                                     np.mean(g["Ours"]) / np.mean(g["B*"]), np.mean(g["Ours + admission"]) / np.mean(g["B* + admission"]),
                                                     len(g["B*"])))
    OUT.write_text("# Paper tables (generated by paper_tables.py, no new runs)\n\n" + "\n".join(L), encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
