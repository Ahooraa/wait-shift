"""Gate G1: trace practicality screen (plan faas-edge-adaptation, Task 5, pre-registered). No simulator.

Run:  python -I output/data-analysis/g1_trace_screen.py
Reads input/data/** (read-only), writes output/data-analysis/results/g1_trace_screen.json.

Operationalisations (fixed before looking at any result; the plan's thresholds are unchanged):
  * Dev span = first 60% of each trace's time span (F1: 12,096 of 20,160 minutes; F2: first 15 of 26 days).
  * Top-200 functions = largest total invocation count within the dev span. NaN (function not yet present) = 0.
  * D1 metric 1: change points per hour per function. Series standardised (z-score) so that the plan's penalty
    2*ln(n) is scale-free; PELT, cost "l2", min_size 5 (own prefix-sum implementation; checked against ruptures on a short series). Sensitivity: the same on log1p(counts).
  * D1 metric 2: share of 1-min windows with rate >= 2x or <= 0.5x the trailing 10-min mean (windows with a
    zero trailing mean are excluded). Sensitivity: the same with a Poisson null (expected share of such
    windows if the function were stationary Poisson with its own mean), reported alongside.
  * D2: aggregate (all top-200 functions summed per minute) offered load vs capacity = median(load)/0.7;
    share of 1-min windows with load > capacity. Per-function version reported as sensitivity.
  * G1 per direction passes when the plan's threshold holds in >= 1 real-trace family (F1 or F2); F3 is
    synthetic with regime shifts by construction and is not screened here.
"""
import json
import math
import os
import sys
import time

import multiprocessing as mp

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA = os.path.join(ROOT, "input", "data")
OUT = os.path.join(ROOT, "output", "data-analysis", "results", "g1_trace_screen.json")
TOP = 200
DEV_FRAC = 0.6
RNG = np.random.default_rng(0)


def load_f1():
    """Azure 2019: per-minute invocation counts per function, dev span (first 12,096 minutes).
    Two passes to stay memory-safe: totals per function first, then only the top-200 rows."""
    need = int(14 * 1440 * DEV_FRAC)
    ndays = math.ceil(need / 1440)
    cols = [str(i) for i in range(1, 1441)]
    totals = {}
    for d in range(1, ndays + 1):
        f = os.path.join(DATA, "azure", "azure2019", "extracted", f"invocations_per_function_md.anon.d{d:02d}.csv")
        df = pd.read_csv(f)
        key = df["HashOwner"] + "|" + df["HashApp"] + "|" + df["HashFunction"]
        tot = df[cols].sum(axis=1) if d < ndays else df[cols[: need - (ndays - 1) * 1440]].sum(axis=1)
        for k, v in zip(key, tot):
            totals[k] = totals.get(k, 0) + v
    top = pd.Series(totals).nlargest(TOP).index
    mats = []
    for d in range(1, ndays + 1):
        f = os.path.join(DATA, "azure", "azure2019", "extracted", f"invocations_per_function_md.anon.d{d:02d}.csv")
        df = pd.read_csv(f)
        key = df["HashOwner"] + "|" + df["HashApp"] + "|" + df["HashFunction"]
        df = df.assign(_k=key).groupby("_k")[cols].sum().reindex(top).fillna(0)
        mats.append(df.to_numpy(dtype=np.float32))
    return np.concatenate(mats, axis=1)[:, :need]


def load_f2():
    """Huawei Public 2023: per-minute requests per function, dev span (first 15 of 26 days)."""
    base = os.path.join(DATA, "huawei", "public2023_minute", "extracted", "public_dataset", "csv_files", "requests_minute")
    days = int(26 * DEV_FRAC)
    mats = []
    for d in range(days):
        df = pd.read_csv(os.path.join(base, f"day_{d:02d}.csv"))
        mats.append(df.drop(columns=["day", "time"]).to_numpy(dtype=np.float32))
    x = np.concatenate(mats, axis=0)  # minutes x functions
    x = np.nan_to_num(x, nan=0.0).T
    return x


def top_functions(x, k=TOP):
    vol = x.sum(axis=1)
    idx = np.argsort(-vol)[:k]
    return x[idx]


def pelt_l2(z, pen, min_size=5):
    """PELT (Killick et al. 2012) with the l2 cost, prefix-sum implementation. Returns number of change points.
    Same algorithm and objective as ruptures.Pelt(model="l2"); written out because the ruptures loop took
    5-45 s per 12k-point series here (about 800 series needed)."""
    n = len(z)
    c1 = np.concatenate(([0.0], np.cumsum(z)))
    c2 = np.concatenate(([0.0], np.cumsum(z * z)))
    F = np.full(n + 1, np.inf)
    F[0] = -pen
    last = np.zeros(n + 1, dtype=np.int64)
    cand = np.array([0], dtype=np.int64)
    for t in range(min_size, n + 1):
        s_idx = cand[cand <= t - min_size]
        if s_idx.size:
            m = t - s_idx
            cost = (c2[t] - c2[s_idx]) - (c1[t] - c1[s_idx]) ** 2 / m
            tot = F[s_idx] + cost + pen
            k = int(np.argmin(tot))
            F[t] = tot[k]
            last[t] = s_idx[k]
            keep = (F[s_idx] + cost) <= F[t]
            cand = np.concatenate((cand[cand > t - min_size], s_idx[keep]))
        # candidate for next step
        nxt = t - min_size + 1
        if nxt > 0 and F[nxt] < np.inf and nxt not in cand:
            cand = np.append(cand, nxt)
    k, t = 0, n
    while t > 0:
        t = last[t]
        if t > 0:
            k += 1
    return k


def change_points_per_hour(series, log=False):
    s = np.log1p(series) if log else series.astype(float)
    sd = s.std()
    if sd == 0:
        return 0.0
    z = (s - s.mean()) / sd
    n = len(z)
    k = pelt_l2(z, pen=2 * math.log(n))
    return k / (n / 60.0)


def _cph_log(series):
    return change_points_per_hour(series, log=True)


def deviation_share(series, null_poisson=False):
    n = len(series)
    c = np.cumsum(np.insert(series.astype(float), 0, 0.0))
    trail = (c[10:n] - c[0 : n - 10]) / 10.0  # mean of x[t-10..t-1] for t=10..n-1
    cur = series[10:n].astype(float)
    ok = trail > 0
    if ok.sum() == 0:
        return float("nan")
    ratio = cur[ok] / trail[ok]
    return float(np.mean((ratio >= 2.0) | (ratio <= 0.5)))


def poisson_null_share(mean_rate, n=2000):
    if mean_rate <= 0:
        return float("nan")
    s = RNG.poisson(mean_rate, size=n)
    return deviation_share(s)


def screen_family(name, x):
    top = top_functions(x)
    n_min = top.shape[1]
    hours = n_min / 60.0
    t0 = time.time()
    with mp.Pool(max(1, (os.cpu_count() or 2) - 1)) as pool:
        cph = np.array(pool.map(change_points_per_hour, list(top), chunksize=4))
        cph_log = np.array(pool.map(_cph_log, list(top), chunksize=4))
    dev = np.array([deviation_share(r) for r in top])
    null = np.array([poisson_null_share(r.mean()) for r in top])
    agg = top.sum(axis=0)
    cap = np.median(agg) / 0.7
    d2_agg = float(np.mean(agg > cap))
    per_fn = []
    for r in top:
        med = np.median(r)
        if med > 0:
            per_fn.append(float(np.mean(r > med / 0.7)))
    res = {
        "family": name,
        "functions": int(top.shape[0]),
        "minutes": int(n_min),
        "hours": hours,
        "median_invocations_per_min_of_functions": float(np.median(top.mean(axis=1))),
        "d1_change_points_per_hour": {
            "median": float(np.median(cph)), "mean": float(np.mean(cph)),
            "p25": float(np.percentile(cph, 25)), "p75": float(np.percentile(cph, 75)),
            "log1p_median": float(np.median(cph_log)),
            "share_of_functions_ge_1_per_hour": float(np.mean(cph >= 1.0)),
        },
        "d1_deviation_share_ge_2x": {
            "median": float(np.nanmedian(dev)), "pooled_mean": float(np.nanmean(dev)),
            "poisson_null_median": float(np.nanmedian(null)),
            "excess_over_null_median": float(np.nanmedian(dev - null)),
        },
        "d2_overload_share_aggregate_rho0.7": d2_agg,
        "d2_overload_share_per_function_median_rho0.7": float(np.median(per_fn)) if per_fn else float("nan"),
        "d2_functions_with_positive_median": len(per_fn),
        "aggregate_load_cv": float(agg.std() / agg.mean()),
        "runtime_s": time.time() - t0,
    }
    d1_pass = res["d1_change_points_per_hour"]["median"] >= 1.0 or res["d1_deviation_share_ge_2x"]["median"] >= 0.05
    d2 = res["d2_overload_share_aggregate_rho0.7"]
    res["d1_meets_threshold"] = bool(d1_pass)
    res["d2_class"] = "PASS" if d2 >= 0.05 else ("MAYBE" if d2 >= 0.02 else "KILL")
    return res


def duration_scv():
    f = [p for p in os.listdir(os.path.join(DATA, "azure", "azure2021", "extracted")) if p.endswith(".txt")][0]
    df = pd.read_csv(os.path.join(DATA, "azure", "azure2021", "extracted", f), usecols=["func", "duration"])
    d = df["duration"].to_numpy(dtype=float)
    d = d[d > 0]
    scv = float(d.var() / d.mean() ** 2)
    g = df[df["duration"] > 0].groupby("func")["duration"]
    stats = g.agg(["count", "mean", "var"])
    stats = stats[stats["count"] >= 100]
    per = (stats["var"] / stats["mean"] ** 2).dropna()
    return {
        "invocations": int(len(d)), "mean_s": float(d.mean()), "scv_overall": scv,
        "functions_with_ge_100_invocations": int(len(per)),
        "scv_per_function_median": float(per.median()), "scv_per_function_p90": float(per.quantile(0.9)),
        "share_functions_scv_gt_1": float((per > 1).mean()),
        "expected": "much greater than 1 (heavy tail)",
    }


def main():
    out = {"script": "g1_trace_screen.py", "dev_fraction": DEV_FRAC, "top_functions": TOP}
    out["F1_azure2019"] = screen_family("F1 Azure 2019 per-minute", load_f1())
    out["F2_huawei_public2023"] = screen_family("F2 Huawei Public 2023 per-minute", load_f2())
    out["durations_azure2021"] = duration_scv()
    f = [out["F1_azure2019"], out["F2_huawei_public2023"]]
    out["G1"] = {
        "D1": "PASS" if any(r["d1_meets_threshold"] for r in f) else "FAIL",
        "D2": ("PASS" if any(r["d2_class"] == "PASS" for r in f)
               else "MAYBE" if any(r["d2_class"] == "MAYBE" for r in f) else "KILL"),
        "rule": "direction passes when the plan threshold holds in >= 1 real-trace family",
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    sys.exit(main())
