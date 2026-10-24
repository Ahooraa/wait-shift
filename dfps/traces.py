"""Trace-driven workloads for the headroom study (plan faas-edge-adaptation, Task 7).

Everything here is an EXTENSION of the DFPS model (DFPS itself uses stationary Poisson arrivals, p.9); the DFPS-faithful
path in `workload.py` is unchanged.

* Arrival processes: a non-homogeneous Poisson process obtained by thinning a per-bin rate series (F1 Azure 2019,
  F2 Huawei Public 2023, F3 synthetic popularity-regime shifts). Series are scaled so that the long-run offered
  utilisation equals the requested rho: rho = sum_i lambda_i * W_i / sum_k ecc_k, with W_i the sum of the mean execution
  times of workflow i's tasks (the plan's "median offered utilisation of total container capacity" is approximated by the
  mean here; the median is reported by `offered_load_profile`).
* Duration model: `EmpiricalSampler` bootstraps the shape of an empirical duration pool and rescales it to the function's
  mean mu_l, so heavy tails change while the calibrated load does not.
"""
from __future__ import annotations

import os

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "input", "data")
CACHE = os.path.join(ROOT, "data", "traces_cache")


def workflow_work(sc):
    """W_i: expected busy slot-seconds per request of workflow i (sum of mean execution times of its tasks)."""
    mu = np.array([f.exec_time for f in sc.functions])
    return np.array([sum(mu[w.ft[t]] for t in range(w.n)) for w in sc.workflows])


def scale_to_rho(sc, rate_series, rho):
    """rate_series: [n_workflows, n_bins] non-negative relative rates. Returns the same array scaled (requests per second
    per workflow, assuming `bin_s` handled by the caller) so that mean offered utilisation = rho."""
    W = workflow_work(sc)
    mean_rate = rate_series.mean(axis=1)
    cap = float(sc.ecc.sum())
    norm = float((mean_rate * W).sum())
    if norm <= 0:
        raise ValueError("rate series has no load")
    return rate_series * (rho * cap / norm)


def thin_arrivals(rate_per_s, bin_s, duration_s, n_nodes, rng):
    """Non-homogeneous Poisson arrivals by thinning. rate_per_s: [n_workflows, n_bins] requests/second in each bin.
    Returns a sorted list of (t, workflow, origin) with origin uniform over the edge nodes (A-20)."""
    out = []
    n_bins = rate_per_s.shape[1]
    for wid in range(rate_per_s.shape[0]):
        lam_max = float(rate_per_s[wid].max())
        if lam_max <= 0:
            continue
        t = rng.exponential(1.0 / lam_max)
        while t < duration_s:
            b = min(int(t // bin_s), n_bins - 1)
            if rng.random() < rate_per_s[wid, b] / lam_max:
                out.append((float(t), wid, int(rng.integers(0, n_nodes))))
            t += rng.exponential(1.0 / lam_max)
    out.sort()
    return out


def offered_load_profile(sc, rate_per_s, bin_s):
    """Offered utilisation per bin: sum_i lambda_i(bin) * W_i / sum ecc (returns the series; its median and mean are the
    quantities the plan calls the load level)."""
    W = workflow_work(sc)
    return (rate_per_s * W[:, None]).sum(axis=0) / float(sc.ecc.sum())


def regime_shift_series(n_workflows, duration_s, bin_s, rng, shift_every_s=600.0, kind="pareto", burst_cv=0.0):
    """F3: popularity regime shifts. Every `shift_every_s` the relative popularity of the workflows is redrawn
    (Pareto with shape 1.5, or uniform); total rate is constant within and across regimes, so the ONLY non-stationarity is
    the popularity shift (which moves load between functions and therefore between nodes)."""
    n_bins = int(np.ceil(duration_s / bin_s))
    bins_per_regime = max(1, int(round(shift_every_s / bin_s)))
    out = np.zeros((n_workflows, n_bins))
    for start in range(0, n_bins, bins_per_regime):
        w = rng.pareto(1.5, n_workflows) + 1.0 if kind == "pareto" else rng.uniform(0.5, 1.5, n_workflows)
        out[:, start:start + bins_per_regime] = (w / w.sum() * n_workflows)[:, None]
    return out


def trace_series(counts, n_workflows, duration_s, bin_s, rng, offset_bins=0):
    """F1/F2: map the first `n_workflows` randomly chosen trace functions (rows of `counts`, per-minute counts) onto the
    workflows' entry points; the series is resampled to `bin_s`-wide bins starting at `offset_bins` (cyclic)."""
    rows = rng.choice(counts.shape[0], n_workflows, replace=False)
    n_bins = int(np.ceil(duration_s / bin_s))
    src_bin_s = 60.0
    out = np.zeros((n_workflows, n_bins))
    for i, r in enumerate(rows):
        series = counts[r].astype(float)
        idx = (offset_bins + (np.arange(n_bins) * bin_s // src_bin_s).astype(int)) % len(series)
        out[i] = series[idx]
    return out


def load_counts(family, span="dev", top=200):
    """Per-minute count matrix [top functions, minutes] for F1 (Azure 2019) or F2 (Huawei Public 2023); `span` is
    'dev' (first 60%) or 'test' (last 40%). The top functions are chosen by DEV-span volume only, and the same functions are
    used for the test span (no test information leaks into selection). Cached as .npy under data/traces_cache/ (v2)."""
    os.makedirs(CACHE, exist_ok=True)
    f = os.path.join(CACHE, f"{family}_{span}_top{top}_devsel.npy")
    if os.path.exists(f):
        return np.load(f)
    import pandas as pd
    if family == "F1":
        cols = [str(i) for i in range(1, 1441)]
        days = range(1, 15)
        cut = int(14 * 1440 * 0.6)                                  # dev = first 60% of minutes (12,096)

        def day_frame(d):
            df = pd.read_csv(os.path.join(DATA, "azure", "azure2019", "extracted", f"invocations_per_function_md.anon.d{d:02d}.csv"))
            k = df["HashOwner"] + "|" + df["HashApp"] + "|" + df["HashFunction"]
            return df.assign(_k=k).groupby("_k")[cols].sum()

        dev_vol = {}                                                # pass 1: dev-span volume per function (memory-safe)
        for d in days:
            lo = (d - 1) * 1440
            if lo >= cut:
                break
            df = day_frame(d)
            v = df[cols[: min(1440, cut - lo)]].sum(axis=1)
            for key, x in zip(df.index, v):
                dev_vol[key] = dev_vol.get(key, 0.0) + float(x)
        order = pd.Series(dev_vol).sort_values(ascending=False, kind="stable").index[:top]   # top functions by DEV volume only
        full = np.concatenate([day_frame(d).reindex(order).fillna(0).to_numpy(dtype=np.float32) for d in days], axis=1)
    elif family == "F2":
        base = os.path.join(DATA, "huawei", "public2023_minute", "extracted", "public_dataset", "csv_files", "requests_minute")
        mats = []
        for d in range(26):
            df = pd.read_csv(os.path.join(base, f"day_{d:02d}.csv"))
            mats.append(df.drop(columns=["day", "time"]).to_numpy(dtype=np.float32))
        x = np.nan_to_num(np.concatenate(mats, axis=0), nan=0.0).T
        cut = int(x.shape[1] * 0.6)
        full = x[np.argsort(-x[:, :cut].sum(axis=1), kind="stable")[:top]]          # top functions by DEV volume only
    else:
        raise ValueError(family)
    cut = int(full.shape[1] * 0.6)
    out = full[:, :cut] if span == "dev" else full[:, cut:]
    np.save(f, out)
    return out


class EmpiricalSampler:
    """exec_sampler for Sim: bootstrap from `pool` (durations, seconds), rescaled to each function's mean mu_l."""

    def __init__(self, pool, mu):
        pool = np.asarray(pool, dtype=float)
        pool = pool[pool > 0]
        self.shape = pool / pool.mean()
        self.mu = np.asarray(mu, dtype=float)

    def __call__(self, f, rng):
        return float(self.mu[f] * self.shape[rng.integers(0, len(self.shape))])


def azure2021_duration_pool(max_rows=2_000_000, seed=0):
    """Empirical per-invocation duration pool (seconds) from the Azure 2021 trace (resampled, at most max_rows)."""
    import pandas as pd
    d = os.path.join(DATA, "azure", "azure2021", "extracted")
    f = [p for p in os.listdir(d) if p.endswith(".txt")][0]
    df = pd.read_csv(os.path.join(d, f), usecols=["duration"])
    v = df["duration"].to_numpy(dtype=float)
    v = v[v > 0]
    if len(v) > max_rows:
        v = np.random.default_rng(seed).choice(v, max_rows, replace=False)
    return v


def workflow_mix(seed, n_workflows=15, alibaba_dags=None):
    """The plan's workflow set: the 6 SeBS-Flow applications + the DFPS Fig. 1 workflow + Alibaba-2018 DAGs (DFPS filter)
    filling the rest. Returns DAG dicts (workload.build_scenario format)."""
    from .sebsflow import all_named_dags
    named = all_named_dags()
    rng = np.random.default_rng(seed + 7)
    k = max(0, n_workflows - len(named))
    ali = [] if not k else [alibaba_dags[int(i)] for i in rng.choice(len(alibaba_dags), k, replace=False)]
    return named[:n_workflows] + ali


def build_trace_scenario(family, rho, seed, span="dev", duration_s=1800.0, bin_s=60.0, ne=80, n_workflows=15,
                         alibaba_dags=None, pool_size=30, counts=None):
    """Trace-driven scenario: DFPS Table-2 infrastructure (workload.build_scenario), the plan's workflow mix, and arrivals
    from family F1 (Azure 2019), F2 (Huawei Public 2023) or F3 (synthetic popularity shifts every 10 min), scaled to offered
    utilisation rho (mean over the window) and generated by thinning. `counts`: preloaded load_counts(family, span)."""
    from .workload import build_scenario
    mix = workflow_mix(seed, n_workflows, alibaba_dags)
    sc = build_scenario(seed, "uniform", 1.0, ne=ne, n_workflows=len(mix), pool_size=pool_size, duration_s=duration_s, dags=mix)
    rng = np.random.default_rng(seed + 1000)
    n_bins = int(np.ceil(duration_s / bin_s))
    if family == "F3":
        rel = regime_shift_series(len(sc.workflows), duration_s, bin_s, rng, shift_every_s=600.0)
    else:
        counts = load_counts(family, span) if counts is None else counts
        need_min = int(np.ceil(duration_s / 60.0)) + 1
        offset = int(rng.integers(0, max(1, counts.shape[1] - need_min)))
        rel = trace_series(counts, len(sc.workflows), duration_s, bin_s, rng, offset_bins=offset)
        rel = np.maximum(rel, 0.0)
        rel[rel.sum(axis=1) == 0] = 1e-6                          # a silent trace function still gets a (negligible) rate
    rate = scale_to_rho(sc, rel, rho)
    sc.arrivals = thin_arrivals(rate, bin_s, duration_s, sc.network.ne, rng)
    prof = offered_load_profile(sc, rate, bin_s)
    sc.meta = dict(sc.meta, family=family, rho=rho, span=span, bin_s=bin_s, kind=f"trace-{family}",
                   offered_util_mean=float(prof.mean()), offered_util_median=float(np.median(prof)),
                   offered_util_p95=float(np.percentile(prof, 95)), n_arrivals=len(sc.arrivals),
                   workflows=[w.get("job") for w in mix], per_app_rate=rate.mean(axis=1).tolist(),
                   rate_series=rate.tolist())
    return sc


def bottleneck_utilisation(sc, X):
    """Offered load of each function divided by its instance count under placement X [N, F] (static view, mean rates).
    > 1 means that function is overloaded even though the aggregate rho is below 1 (the Task 8 finding)."""
    mu = np.array([f.exec_time for f in sc.functions])
    rates = np.array(sc.meta["per_app_rate"], dtype=float)
    load = np.zeros(len(sc.functions))
    for w, r in zip(sc.workflows, rates):
        for t in range(w.n):
            load[w.ft[t]] += r * mu[w.ft[t]]
    inst = X.sum(axis=0)
    with np.errstate(divide="ignore"):
        u = np.where(inst > 0, load / np.maximum(inst, 1), np.inf)
    return dict(max=float(u.max()), median=float(np.median(u)), n_over_1=int((u > 1).sum()))


def function_rates(sc, t0, t1):
    """True mean request rate of every function over [t0, t1) from the scenario's workflow rate series (requests/s):
    lambda_f = sum_w rate_w x (number of tasks of w that run f)."""
    R = np.asarray(sc.meta["rate_series"], dtype=float)
    b = float(sc.meta["bin_s"])
    lo, hi = int(t0 // b), max(int(t0 // b) + 1, int(np.ceil(t1 / b)))
    lo, hi = min(lo, R.shape[1] - 1), min(hi, R.shape[1])
    w_rate = R[:, lo:hi].mean(axis=1)
    lam = np.zeros(len(sc.functions))
    for w, r in zip(sc.workflows, w_rate):
        for t in range(w.n):
            lam[w.ft[t]] += r
    return lam


def workflow_rates(sc, t0, t1):
    R = np.asarray(sc.meta["rate_series"], dtype=float)
    b = float(sc.meta["bin_s"])
    lo, hi = int(t0 // b), max(int(t0 // b) + 1, int(np.ceil(t1 / b)))
    lo, hi = min(lo, R.shape[1] - 1), min(hi, R.shape[1])
    return R[:, lo:hi].mean(axis=1)


def build_overload_scenario(family, seed, burst_rho=None, span="dev", duration_s=900.0, bin_s=60.0, ne=80, n_workflows=15,
                            alibaba_dags=None, pool_size=30, counts=None, base_rho=0.7):
    """D2 overload scenarios (plan Task 12).
    F1/F2: G1's rule on the top-200 aggregate (provision so the median minute is at base_rho; overloaded = above capacity).
    The 15-min window is centred on an overloaded minute (else the maximum, reported); the offered-utilisation profile of the
    window follows that aggregate, and 15 trace functions from the same window supply the mix between workflows.
    F3: regime-shift series at base_rho with one burst of 2-10 min (seeded) at offered utilisation `burst_rho` (1.2 or 1.5)."""
    from .workload import build_scenario
    mix = workflow_mix(seed, n_workflows, alibaba_dags)
    sc = build_scenario(seed, "uniform", 1.0, ne=ne, n_workflows=len(mix), pool_size=pool_size, duration_s=duration_s, dags=mix)
    rng = np.random.default_rng(seed + 2000)
    W = workflow_work(sc)
    cap = float(sc.ecc.sum())
    n_bins = int(np.ceil(duration_s / bin_s))
    info = {}
    if family == "F3":
        rel = regime_shift_series(len(sc.workflows), duration_s, bin_s, rng, shift_every_s=600.0)
        rate = scale_to_rho(sc, rel, base_rho)
        blen = int(rng.integers(2, 11)) * 60.0
        b0 = float(rng.uniform(120.0, max(121.0, duration_s - blen - 60.0)))
        lo, hi = int(b0 // bin_s), int(np.ceil((b0 + blen) / bin_s))
        prof = (rate * W[:, None]).sum(axis=0) / cap
        rate[:, lo:hi] *= (burst_rho / np.maximum(prof[lo:hi], 1e-9))[None, :]
        info = dict(burst_rho=burst_rho, burst_start_s=b0, burst_len_s=blen)
    else:
        counts = load_counts(family, span) if counts is None else counts
        agg200 = counts.sum(axis=0).astype(float)                     # G1's D2 aggregate: all top-200 functions per minute
        util = agg200 * base_rho / np.median(agg200)                  # G1 provisioning: median minute at base_rho
        over = np.flatnonzero(util > 1.0)
        half = n_bins // 2
        cand = over[(over >= half) & (over < len(util) - half)]
        centre = int(rng.choice(cand)) if len(cand) else int(np.argmax(util[half:len(util) - half]) + half)
        start = centre - half
        rows = rng.choice(counts.shape[0], len(sc.workflows), replace=False)
        mixw = counts[rows, start:start + n_bins].astype(float) + 1e-6   # workflow mix from 15 trace functions in the window
        prof_mix = (mixw * W[:, None]).sum(axis=0) / cap
        rate = mixw * (util[start:start + n_bins] / prof_mix)[None, :]  # offered utilisation per minute = G1's profile
        info = dict(overloaded_minutes_in_trace=int(len(over)), window_start_min=int(start),
                    window_peak_util=float(util[start:start + n_bins].max()), window_mean_util=float(util[start:start + n_bins].mean()),
                    centre_on_overload=bool(len(cand)))
    sc.arrivals = thin_arrivals(rate, bin_s, duration_s, sc.network.ne, rng)
    prof = offered_load_profile(sc, rate, bin_s)
    sc.meta = dict(sc.meta, family=family, kind=f"overload-{family}", span=span, bin_s=bin_s, n_arrivals=len(sc.arrivals),
                   offered_util_mean=float(prof.mean()), offered_util_max=float(prof.max()),
                   offered_util_share_over_1=float((prof > 1.0).mean()), workflows=[w.get("job") for w in mix],
                   per_app_rate=rate.mean(axis=1).tolist(), rate_series=rate.tolist(), **info)
    return sc
