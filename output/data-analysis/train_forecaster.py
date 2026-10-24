"""Train the blind-O3S rate forecaster (per family) and check it against simple rules on the real test scenarios.

Error = sum |predicted - true| / sum true of per-workflow mean rate over the next 120 s, at every 60 s decision time (60..840 s).
Rules: persistence = mean of the last min(120 s, t) (what the first blind attempt used); last5 = mean of the last up to 5 minutes.
"""
import pickle
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from dfps import forecast as F  # noqa: E402

D1 = ROOT / "results" / "d1_headroom"
OUT = ROOT / "results" / "forecaster"
OUT.mkdir(exist_ok=True)
rows = {}
for fam in (sys.argv[1:] or ("F1", "F2", "F3")):
    p = OUT / f"forecaster_{fam}.pkl"
    fc, n = F.train(fam, p, loss="poisson", mode="mean")
    err = {"trained": [0.0, 0.0], "persistence": [0.0, 0.0], "last5": [0.0, 0.0], "oracle": [0.0, 0.0]}
    for s in range(1, 11):
        for rho in (0.5, 0.7, 0.85):
            sc = pickle.load(open(D1 / f"{fam}_r{rho}_s{s}.pkl", "rb"))
            R = np.asarray(sc.meta["rate_series"])
            arr, times, nw = sc.arrivals, [a[0] for a in sc.arrivals], R.shape[0]
            for t in range(60, 840 + 1, 60):
                true = R[:, t // 60:t // 60 + 2].mean(axis=1)
                pred = {"trained": fc.rates(t, arr, times, nw)}
                import bisect
                for name, L in (("persistence", min(120, t)), ("last5", min(300, t))):
                    lo, hi = bisect.bisect_left(times, t - L), bisect.bisect_left(times, t)
                    c = np.zeros(nw)
                    for _, w, _ in arr[lo:hi]:
                        c[w] += 1
                    pred[name] = c / L
                pred["oracle"] = true
                for k, v in pred.items():
                    err[k][0] += np.abs(v - true).sum()
                    err[k][1] += true.sum()
    rows[fam] = {k: v[0] / v[1] for k, v in err.items()}
    print(fam, "train samples", n, {k: round(v, 3) for k, v in rows[fam].items()}, flush=True)
