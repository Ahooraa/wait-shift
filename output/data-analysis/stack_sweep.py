"""Textbook-stack baseline (2026-10-22): HPA-style sizing (containers = load / 0.8, no backlog term) + join-the-shortest-queue request
moves, i.e. only off-the-shelf rules, in the same controller as the reference (re-layout every 60 s, data-affinity placement, no B*,
request moves per B* period, cap 300). 18 development cases. Files <case>.O3S_h120_blind_nosim_nl_stack.json."""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(ROOT))
import d3s_headroom as d  # noqa: E402
from new_layer_sweep import BASE  # noqa: E402

if __name__ == "__main__":
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    T = json.loads((d.OUT / "g2_tstar.json").read_text())
    T = {f: float(T["families"][f]["T_star"]) for f in ("F1", "F2")}
    jobs = []
    for f in ("F1", "F2"):
        for r in d.RHOS:
            for s in (1, 2, 3):
                tg = d.tag(f, r, s)
                jobs.append((tg, str(d.RUNS / f"{tg}.O3S_h120_blind_nosim_nl_stack.json"), s, T[f], d.DURATION, 60.0, 120.0, 5,
                             True, None, "hpa", dict(BASE, rebal_rule="jsq")))
    jobs.sort(key=lambda j: -float(j[0].split("_r")[1].split("_")[0]))
    with ProcessPoolExecutor(workers) as ex:
        for done in ex.map(d.job, jobs):
            print("done", done, flush=True)
