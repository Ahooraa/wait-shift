"""Diagnosis (6 Nov 2026): where do the extra cold starts of the trigger configuration come from?
Logs every container change (adds, removes per function) with its source (slow re-layout vs trigger), then measures
  undo   containers the slow loop removed from a function within 120 s after the trigger had added to it (trigger adds that were reversed)
  readd  containers the trigger added to a function within 120 s after the slow loop had removed from it (slow removals that were reversed)
Development cases, seed 1, F1/F2 x rho 0.5/0.7/0.85; arms frozen3_od (no trigger) and frozen3_od_fs (60 s re-layout + trigger).
Diagnostic only: it patches Sim.apply_placement and O3SimAdjuster.fast_scale in this process and writes to results/capW1_audit_coldsrc."""
import sys, json
from pathlib import Path
import numpy as np
ROOT = next(p for p in (Path("D:/DFPS implementation"), Path.home() / "DFPS-implementation") if p.exists()); sys.path.insert(0, str(ROOT / "output" / "data-analysis")); sys.path.insert(0, str(ROOT))
from dfps.sim import Sim
from dfps.o3s import O3SimAdjuster
import capw1_ondemand as O

EV, CTX = [], {"src": "slow"}
_orig_apply = Sim.apply_placement
_orig_fast = O3SimAdjuster.fast_scale


def apply(self, X):
    T = np.asarray(X).T
    cur = np.asarray(self.cnt)
    EV.append((float(self.now), CTX["src"], np.maximum(0, T - cur).sum(axis=1).astype(int), np.maximum(0, cur - T).sum(axis=1).astype(int)))
    return _orig_apply(self, X)


def fast(self, sim):
    CTX["src"] = "trigger"
    try:
        return _orig_fast(self, sim)
    finally:
        CTX["src"] = "slow"


Sim.apply_placement = apply
O3SimAdjuster.fast_scale = fast
WIN = 120.0


def analyse(ev):
    out = dict(slow_add=0, slow_rem=0, trig_add=0, trig_rem=0, undo=0, readd=0)
    last_trig_add, last_slow_rem = {}, {}
    for t, src, add, rem in ev:
        if t < O.WARMUP:
            continue
        for f in range(len(add)):
            if src == "slow":
                out["slow_add"] += int(add[f]); out["slow_rem"] += int(rem[f])
                if rem[f] > 0:
                    if f in last_trig_add and t - last_trig_add[f][0] <= WIN:
                        q = min(int(rem[f]), last_trig_add[f][1]); out["undo"] += q
                        last_trig_add[f] = (last_trig_add[f][0], last_trig_add[f][1] - q)
                    last_slow_rem[f] = (t, int(rem[f]))
            else:
                out["trig_add"] += int(add[f]); out["trig_rem"] += int(rem[f])
                if add[f] > 0:
                    if f in last_slow_rem and t - last_slow_rem[f][0] <= WIN:
                        q = min(int(add[f]), last_slow_rem[f][1]); out["readd"] += q
                        last_slow_rem[f] = (last_slow_rem[f][0], last_slow_rem[f][1] - q)
                    last_trig_add[f] = (t, int(add[f]))
    return out


rows = []
sm = str(ROOT / "results" / "capW1_audit_coldsrc")
for fam in ("F1", "F2"):
    for rho in ("0.5", "0.7", "0.85"):
        tg = f"{fam}_r{rho}_s1"
        for arm in ("frozen3_od", "frozen3_od_fs"):
            EV.clear(); CTX["src"] = "slow"
            r = O.run_job((tg, arm, O.DURATION, sm))
            j = json.load(open(r)); a = analyse(EV)
            a.update(case=tg, arm=arm, cold=j["result"]["cold_starts"], p99=j["result"]["p99_makespan"])
            rows.append(a)
            print(tg, arm, {k: a[k] for k in ("cold", "slow_add", "slow_rem", "trig_add", "trig_rem", "undo", "readd")}, flush=True)
tot = {}
for arm in ("frozen3_od", "frozen3_od_fs"):
    x = [a for a in rows if a["arm"] == arm]
    tot[arm] = {k: sum(a[k] for a in x) for k in ("cold", "slow_add", "slow_rem", "trig_add", "trig_rem", "undo", "readd")}
    print("TOTAL", arm, tot[arm])
json.dump(rows, open(ROOT / "results" / "diag_cold_sources.json", "w"))
