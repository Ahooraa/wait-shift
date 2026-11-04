"""Join binding at last-parent finish (3 Nov 2026): what does holding the parents' states cost, against the repair moves it avoids?
Step-1 traces (results/stale_plan_probe/, CAP-W1, controller "ours"), no new runs. Reading fixed in
knowledge/synthesis/workflow-aware-decision-rules.md ("Join binding at last-parent finish").
  python join_hold_cost.py
"""
import collections
import json
import pickle
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
TR = ROOT / "results" / "stale_plan_probe"
W1 = ROOT / "results" / "capW1_light"
CASES = [f"{f}_r{r}_s1" for f in ("F1", "F2") for r in (0.5, 0.7, 0.85)]
PERIOD = 4.0


def main():
    n_build = n_hold = 0
    for tg in CASES:
        d = json.loads((TR / f"{tg}.json").read_text())
        assert d["hash_matches_stored"], tg
        sc = pickle.load(open(W1 / f"{tg}.sc.pkl", "rb"))["sc"]
        net, wfs = sc.network, {w.id: w for w in sc.workflows}
        soj = {int(q[0]): q[3] - q[2] for q in d["reqs"]}
        thr = np.quantile(list(soj.values()), 0.99)
        tasks = {(int(t[0]), int(t[2])): t for t in d["tasks"]}       # (rid, wid, task, plan, exec, t_first, t_start, t_done, n_moves)
        save_all, save_early = collections.Counter(), collections.Counter()
        for rid, task, now, delay, t_first in d["moves"]:
            save_all[(int(rid), int(task))] += delay
            if t_first is not None and now - t_first <= PERIOD:
                save_early[(int(rid), int(task))] += delay
        res = {"tail": [], "all": []}
        for (rid, t), row in tasks.items():
            wf = wfs[int(row[1])]
            ps = wf.parents[t]
            if len(ps) < 2 or any((rid, p) not in tasks for p in ps):
                continue
            k = int(row[4])
            dn = [tasks[(rid, p)][7] for p in ps]
            st = [net.stt(wf.ss[(p, t)], int(tasks[(rid, p)][4]), k) for p in ps]
            today = max(a + b for a, b in zip(dn, st))
            hold = max(dn) + max(st) - today
            rec = (hold, save_all[(rid, t)], save_early[(rid, t)], max(dn) - min(dn), max(st))
            res["all"].append(rec)
            if soj.get(rid, -1) >= thr:
                res["tail"].append(rec)
        for lab in ("tail", "all"):
            a = np.array(res[lab])
            h, s, se, gap, mst = a.T
            print(f"{tg} {lab:4s} joins {len(a):6d}: HOLD mean {h.mean():.3f}s (P90 {np.quantile(h,0.9):.3f}, zero {np.mean(h<1e-9):.0%})  "
                  f"SAVE all {s.mean():.3f}s early {se.mean():.3f}s  | parent-finish gap median {np.median(gap):.2f}s vs largest input transfer "
                  f"median {np.median(mst):.2f}s, gap >= transfer {np.mean(gap>=mst):.0%}")
            if lab == "tail":
                n_build += h.mean() < s.mean()
                n_hold += h.mean() >= s.mean()
    print(f"\nHOLD: mean HOLD < mean SAVE for tail joins in {n_build}/6, >= in {n_hold}/6 -> "
          + ("build option 1 (bind joins at last-parent finish)" if n_build >= 4 else ("holding costs more: option 3 or 2 next" if n_hold >= 3 else "mixed")))


if __name__ == "__main__":
    main()
