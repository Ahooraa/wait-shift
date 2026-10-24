"""Diagnostic: can the traffic rises in the D1/D3 test windows be anticipated from information a provider would have?

For every test scenario (F1 Azure, F2 Huawei; seeds 1-10) the 15 workflow series are trace rows at a known offset, so the
trace BEFORE the window is the function's real history. At each 60 s decision time t (1..13 min into the window) we predict
the mean rate of the next two minutes with:
  last2    mean of the last 2 minutes (the first blind attempt)
  last5    mean of the last 5 minutes
  hour     the same two minutes one hour earlier, scaled by recent level / level one hour earlier (ratio clipped to [0.5, 2])
  day      the same two minutes one day earlier, scaled likewise
  day_raw  the same two minutes one day earlier, unscaled
  agg      last2 of this function x (next-2-min / last-2-min ratio of the AGGREGATE of all 200 functions one day earlier)
Error = sum |pred - true| / sum true (volume-weighted, the forecaster check metric).
Rise capture: over decision points where the next 2 minutes are >= 1.5x the last-5-min level, the share of the excess
volume (true - last5) that the predictor anticipates (clipped to [0, 1] per point, volume-weighted).
Also verifies that the reproduced windows match the scenarios' rate series (they are a scalar multiple).
"""
import pickle
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from dfps.traces import load_counts  # noqa: E402

D1 = ROOT / "results" / "d1_headroom"
NEED = int(np.ceil(900.0 / 60.0)) + 1                                   # build_trace_scenario with DURATION = 900 s


def window(counts, seed, nwf=15, nbins=15):
    rng = np.random.default_rng(seed + 1000)
    off = int(rng.integers(0, max(1, counts.shape[1] - NEED)))
    rows = rng.choice(counts.shape[0], nwf, replace=False)
    return off, rows


for fam in ("F1", "F2"):
    C = load_counts(fam, "dev").astype(float)
    agg = C.sum(axis=0)
    err = {k: [0.0, 0.0] for k in ("last2", "last5", "hour", "day", "day_raw", "agg")}
    cap = {k: [0.0, 0.0] for k in err}
    checks, n_day = [], 0
    for s in range(1, 11):
        off, rows = window(C, s)
        sc = pickle.load(open(D1 / f"{fam}_r0.7_s{s}.pkl", "rb"))
        R = np.asarray(sc.meta["rate_series"])
        rel = C[rows][:, off:off + R.shape[1]]
        m = rel > 0
        ratio = R[m] / rel[m]
        checks.append(float(ratio.std() / ratio.mean()) if m.any() else np.nan)
        if off < 1440 + 10:
            continue                                                    # no full day of history before this window
        n_day += 1
        for t in range(1, 14):
            a = off + t                                                 # first minute after the decision
            true = C[rows, a:a + 2].mean(axis=1)
            l2 = C[rows, a - 2:a].mean(axis=1)
            l5 = C[rows, a - 5:a].mean(axis=1)

            def seasonal(lag, scaled=True):
                past_next = C[rows, a - lag:a - lag + 2].mean(axis=1)
                if not scaled:
                    return past_next
                past_lvl = C[rows, a - lag - 5:a - lag].mean(axis=1)
                r = np.clip((l5 + 0.5) / (past_lvl + 0.5), 0.5, 2.0)
                return past_next * r

            ag_ratio = (agg[a - 1440:a - 1440 + 2].mean() + 1) / (agg[a - 1440 - 2:a - 1440].mean() + 1)
            pred = dict(last2=l2, last5=l5, hour=seasonal(60), day=seasonal(1440), day_raw=seasonal(1440, False), agg=l2 * ag_ratio)
            rise = true >= 1.5 * l5 + 1e-9
            excess = np.where(rise, true - l5, 0.0)
            for k, p in pred.items():
                err[k][0] += np.abs(p - true).sum()
                err[k][1] += true.sum()
                got = np.clip((p - l5) / np.maximum(true - l5, 1e-9), 0.0, 1.0)
                cap[k][0] += (got * excess).sum()
                cap[k][1] += excess.sum()
    print(f"{fam}: window check (CV of rate/trace ratio, ~0 = reproduced): {np.nanmax(checks):.3g}; windows with a day of history: {n_day}/10")
    print("   error     ", {k: round(v[0] / v[1], 3) for k, v in err.items()})
    print("   rise share", {k: round(v[0] / max(v[1], 1e-9), 3) for k, v in cap.items()},
          f"(rises carry {cap['last2'][1] / err['last2'][1]:.1%} of the volume)")
