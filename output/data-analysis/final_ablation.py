"""Re-run of the sizing / request-move ablations on the FINAL controller (2026-10-24).

The earlier ablations (stack_sweep, lb_baseline_sweep, sizing-rule sweeps) ran on the older reference (affinity placement, moves capped at 300).
Here each variant is FROZEN-2 (incremental soft-routing placement, unlimited moves, 4 s period, moves right after a re-layout) with ONE part replaced.
Sizing rules are placed by the same incremental placement. Reference: nl_fz2_60. 18 development cases per variant.
  hpa / fifer / kraken   sizing rule replaced      jsq / steal   request-move rule replaced      stack   hpa sizing + jsq moves
Files <case>.O3S_h120_blind_nosim_nl_fx_<variant>.json   (python final_ablation.py run [workers] | analyze)
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(ROOT))
import d3s_headroom as d  # noqa: E402
from frozen2 import FROZEN2, MOVE_PERIOD_S  # noqa: E402

M = "p99_makespan"
VARIANTS = {"stack": ("hpa", dict(rebal_rule="jsq")), "jsq": ("nosim", dict(rebal_rule="jsq")), "steal": ("nosim", dict(rebal_rule="steal")),
            "hpa": ("hpa", {}), "fifer": ("fifer", {}), "kraken": ("kraken", {})}
CASES = [(f, r, s) for f in ("F1", "F2") for r in d.RHOS for s in (1, 2, 3)]


def jobs(v):
    cand, extra = VARIANTS[v]
    return [(d.tag(f, r, s), str(d.RUNS / f"{d.tag(f, r, s)}.O3S_h120_blind_nosim_nl_fx_{v}.json"), s, MOVE_PERIOD_S[f], d.DURATION,
             60.0, 120.0, 5, True, None, cand, dict(FROZEN2, **extra)) for f, r, s in CASES]


def run(workers):
    todo = [j for v in VARIANTS for j in jobs(v) if not Path(j[1]).exists()]
    todo.sort(key=lambda j: -float(j[0].split("_r")[1].split("_")[0]))
    print(f"{len(todo)} runs", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        for done in ex.map(d.job, todo):
            print("done", done, flush=True)


def analyze():
    from d1_rlla import BASE, D1, boot
    base = {}
    for d_ in (D1, BASE):
        for f in d_.glob("*.json"):
            x = json.loads(f.read_text())
            if x.get("ctrl") in ("B_STAR", "RL", "RL_CAL"):
                base.setdefault((x["family"], x["rho"], x["seed"]), {})[x["ctrl"]] = x["result"][M]

    def load(s):
        o = {}
        for f in d.RUNS.glob(f"*.O3S_h120_blind_nosim_{s}.json"):
            x = json.loads(f.read_text())
            if x["seed"] <= 3:
                o[(x["family"], x["rho"], x["seed"])] = x["result"]
        return o
    ref = load("nl_fz2_60")
    p = lambda v: f"{v['mean'] * 100:+6.1f}% ({v['lo'] * 100:+.0f} to {v['hi'] * 100:+.0f})"  # noqa: E731
    print("Variant of FROZEN-2 with one part replaced, 18 development cases. 'worse' = P99 higher than FROZEN-2 (positive = FROZEN-2 better)\n")
    print("%-8s %3s | %-26s | %5s | %-22s | %6s | %8s %8s" % ("variant", "n", "FROZEN-2 better by", "wins", "gain over best existing", "ours", "cold", "mv/req"))
    for v in VARIANTS:
        x = load(f"nl_fx_{v}")
        ks = [k for k in ref if k in x]
        if not ks:
            continue
        g = [(x[k][M] - ref[k][M]) / x[k][M] for k in ks]
        be = [min(base[k].values()) for k in ks]
        print("%-8s %3d | %-26s | %2d/%2d | %+6.1f%% (ref %+6.1f%%)   | %6.0f | %8.0f %8.2f" % (
            v, len(ks), p(boot(g)), sum(a > 0 for a in g), len(ks), 100 * np.mean([(b - x[k][M]) / b for b, k in zip(be, ks)]),
            100 * np.mean([(b - ref[k][M]) / b for b, k in zip(be, ks)]), np.mean([ref[k][M] for k in ks]),
            np.mean([x[k]["cold_starts"] for k in ks]), np.mean([x[k]["n_moved"] / x[k]["n_completed"] for k in ks])))


if __name__ == "__main__":
    run(int(sys.argv[2]) if len(sys.argv) > 2 else 6) if sys.argv[1] == "run" else analyze()
