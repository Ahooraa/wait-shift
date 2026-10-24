"""Capacity- and queue-aware placement in the simulator (2026-10-23). Same controller as the frozen one (busiest-first sizing,
finish-time request moves with NO cap, no B*); only the placement rule changes, always incremental.
  qa          queue-aware: soft routing + transfer + M/M/1 waiting, tau = 1 hop   (dfps/controllers.py queue_aware_placement)
  qa_tau2     the same with tau = 2 (a flatter routing: demand spreads over more containers)
  qa_noqueue  soft routing and transfer, WITHOUT the waiting term (isolates what the queue model adds)
Reference: nl_km_rmall (incremental k-median, unlimited moves: P99 140.3 s, cold starts 1,396 on these 18 cases).
18 development cases (F1/F2 x 50/70/85% x seeds 1-3). Files <case>.O3S_h120_blind_nosim_nl_<variant>.json"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(ROOT))
import d3s_headroom as d  # noqa: E402
from new_layer_sweep import BASE  # noqa: E402

QA = dict(BASE, placement="qaware", origin_weight=1.0, rebal_max=10 ** 9)
VARIANTS = {"qa": dict(QA, tau=1.0), "qa_tau2": dict(QA, tau=2.0), "qa_noqueue": dict(QA, tau=1.0, queue_term=False)}

if __name__ == "__main__":
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 11
    T = json.loads((d.OUT / "g2_tstar.json").read_text())
    T = {f: float(T["families"][f]["T_star"]) for f in ("F1", "F2")}
    jobs = []
    for name, churn in VARIANTS.items():
        part = []
        for f in ("F1", "F2"):
            for r in d.RHOS:
                for s in (1, 2, 3):
                    tg = d.tag(f, r, s)
                    part.append((tg, str(d.RUNS / f"{tg}.O3S_h120_blind_nosim_nl_{name}.json"), s, T[f], d.DURATION, 60.0, 120.0, 5,
                                 True, None, "nosim", dict(churn)))
        part.sort(key=lambda j: -float(j[0].split("_r")[1].split("_")[0]))
        jobs += part
    with ProcessPoolExecutor(workers) as ex:
        for done in ex.map(d.job, jobs):
            print("done", done, flush=True)
