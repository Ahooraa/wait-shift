"""Trace check for parent-finish binding (3 Nov 2026): which tasks carry the early repair cost? Uses the step-1 traces
(results/stale_plan_probe/, CAP-W1, controller "ours"), no new runs. Reading fixed in knowledge/synthesis/workflow-aware-decision-rules.md
("Parent-finish binding, trace check").
  python bind_trace_split.py
"""
import json
import pickle
from pathlib import Path

import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
TR = ROOT / "results" / "stale_plan_probe"
W1 = ROOT / "results" / "capW1_light"
CASES = [f"{f}_r{r}_s1" for f in ("F1", "F2") for r in (0.5, 0.7, 0.85)]
PERIOD = 4.0
KINDS = ("root", "single", "join")


def split(moves, reqs, kind_of):
    cost = {(k, w): 0.0 for k in KINDS for w in ("early", "late")}
    for rid, task, now, delay, t_first in moves:
        if int(rid) not in reqs:
            continue
        w = "early" if (t_first is not None and now - t_first <= PERIOD) else "late"
        cost[(kind_of[reqs[int(rid)]][int(task)], w)] += delay
    return cost


def main():
    n_single = n_less = 0
    for tg in CASES:
        d = json.loads((TR / f"{tg}.json").read_text())
        assert d["hash_matches_stored"], tg
        sc = pickle.load(open(W1 / f"{tg}.sc.pkl", "rb"))["sc"]
        kind_of = {w.id: ["root" if not w.parents[t] else ("single" if len(w.parents[t]) == 1 else "join") for t in range(w.n)] for w in sc.workflows}
        soj = {int(q[0]): q[3] - q[2] for q in d["reqs"]}
        wid = {int(q[0]): int(q[1]) for q in d["reqs"]}
        thr = np.quantile(list(soj.values()), 0.99)
        tail = {k: wid[k] for k, v in soj.items() if v >= thr}
        tail_mean = np.mean([soj[k] for k in tail])
        for label, sel in (("tail", tail), ("all ", wid)):
            c = split(d["moves"], sel, kind_of)
            tot = sum(c.values())
            early = sum(c[(k, "early")] for k in KINDS)
            pts = (lambda x: 100 * x / len(sel) / tail_mean) if label == "tail" else None
            line = "  ".join(f"{k} {c[(k,'early')]/tot:.0%}/{c[(k,'late')]/tot:.0%}" for k in KINDS)
            extra = f"  | tail cost {pts(tot):.1f} pts of tail sojourn, early {pts(early):.1f}, early single {pts(c[('single','early')]):.1f}" if pts else ""
            share = c[("single", "early")] / early if early else float("nan")
            print(f"{tg} {label}: share of move transfer (early/late) {line}  | single-parent share of early cost {share:.0%}{extra}")
            if label == "tail":
                n_single += share >= 0.5
                n_less += share < 0.5
        frac = {k: np.mean([x == k for w in sc.workflows for x in kind_of[w.id]]) for k in KINDS}
        print(f"{tg}      task mix: " + "  ".join(f"{k} {v:.0%}" for k, v in frac.items()))
    print(f"\nSINGLE: single-parent share of early tail cost >= 50% in {n_single}/6, < 50% in {n_less}/6 -> "
          + ("build the single-parent version first" if n_single >= 4 else ("handle joins first (design question)" if n_less >= 3 else "mixed")))


if __name__ == "__main__":
    main()
