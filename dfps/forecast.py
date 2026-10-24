"""Causal request-rate forecaster for the blind O3S run (replaces the true future of the oracle).

One pooled gradient-boosting model per trace family predicts, for one workflow, the mean arrival rate over the next two minutes from the
arrivals seen so far (per-minute counts of the last up to 5 minutes). It is trained on trace minutes that are NOT inside any test
window (leave-window-out), with Poisson noise added so the training inputs look like observed arrival counts.

F3 (synthetic popularity shifts) is trained on freshly generated series from the same generator with other random seeds; the model has no
clock, so it cannot know when a shift happens.
"""
from __future__ import annotations

import bisect
import pickle
from pathlib import Path

import numpy as np

LAGS, EPS = 5, 0.1
SEEDS_ALL = tuple(range(1, 11))


def feats(counts):
    """counts: per-minute observed counts, oldest first, 1..LAGS values -> feature vector."""
    c = np.asarray(counts, dtype=float)[-LAGS:]
    k = len(c)
    L = float(c.mean())
    x = np.full(LAGS + 3, np.nan)
    for i in range(k):
        x[i] = (c[k - 1 - i] + 0.5) / (L + 0.5)                        # lag 1 = most recent minute
    x[LAGS], x[LAGS + 1], x[LAGS + 2] = np.log(L + EPS), k, (c[-1] - c[0]) / (L + 0.5) if k > 1 else 0.0
    return x, L


def test_offsets(family, counts, n_seeds=SEEDS_ALL, duration_s=900.0):      # D1/D3 scenarios use DURATION = 900 s (bug fixed 2026-10-20: was 1800, wrong held-out windows)
    need = int(np.ceil(duration_s / 60.0)) + 1
    return [int(np.random.default_rng(s + 1000).integers(0, max(1, counts.shape[1] - need))) for s in n_seeds]


def _samples(lam, rng):
    """lam: expected per-minute counts of one series (T minutes). Returns feature rows and targets for decisions d = 1..T-3."""
    obs = rng.poisson(lam)
    X, y = [], []
    for d in range(1, len(lam) - 2):
        x, L = feats(obs[max(0, d - LAGS):d])
        X.append(x)
        y.append((lam[d:d + 2].mean(), L))
    return X, y


def build_training(family, n_windows=6000, seed=0, win_min=17):
    from .traces import load_counts, regime_shift_series
    rng = np.random.default_rng(seed)
    mrange = (np.log(0.02), np.log(12.0))                               # per-workflow mean rate (req/s) seen in the test scenarios
    X, y = [], []
    if family == "F3":
        for _ in range(n_windows // 10):
            rel = regime_shift_series(15, 15 * 60 + 600.0, 60.0, rng, shift_every_s=600.0)
            for w in range(15):
                s = int(rng.integers(0, 10))
                lam = rel[w, s:s + win_min] * np.exp(rng.uniform(*mrange)) * 60.0
                a, b = _samples(lam, rng)
                X += a
                y += b
        return np.array(X), np.array(y)
    counts = load_counts(family, "dev").astype(float)
    bad = np.zeros(counts.shape[1], bool)
    for o in test_offsets(family, counts):
        bad[max(0, o - 6):o + 40] = True                                # held out: every test window (all 10 seeds) plus a margin
    ok = [s for s in range(counts.shape[1] - win_min) if not bad[s:s + win_min].any()]
    for _ in range(n_windows):
        r, s = int(rng.integers(0, counts.shape[0])), ok[int(rng.integers(0, len(ok)))]
        row = counts[r, s:s + win_min]
        if row[:win_min].mean() <= 0:
            continue
        lam = row / row.mean() * np.exp(rng.uniform(*mrange)) * 60.0
        a, b = _samples(lam, rng)
        X += a
        y += b
    return np.array(X), np.array(y)


class RateForecaster:
    def __init__(self, model, mode="log_ratio"):
        self.model, self.mode = model, mode

    def rates(self, sim_now, arrivals, times, n_workflows):
        """Predicted mean arrival rate (req/s) of every workflow over the next two minutes, from arrivals before sim_now."""
        k = int(min(LAGS, sim_now // 60.0))
        out = np.zeros(n_workflows)
        if k < 1:
            return out
        edges = sim_now - 60.0 * np.arange(k, -1, -1)                  # k full minutes ending now, oldest first
        lo, hi = bisect.bisect_left(times, edges[0]), bisect.bisect_left(times, sim_now)
        cnt = np.zeros((n_workflows, k))
        for t, w, _ in arrivals[lo:hi]:
            cnt[w, min(k - 1, int((t - edges[0]) // 60.0))] += 1
        F, Ls = zip(*[feats(cnt[w]) for w in range(n_workflows)])
        yhat = self.model.predict(np.array(F))
        if self.mode == "mean":
            pred_min = np.maximum(0.0, yhat)
        else:
            pred_min = np.maximum(0.0, np.exp(yhat) * (np.array(Ls) + EPS) - EPS)
        return pred_min / 60.0


def train(family, path, n_windows=6000, loss="squared_error", mode="log_ratio"):
    """mode 'log_ratio': target log(next mean / recent level); mode 'mean': target the next two-minute mean count itself
    (use loss='poisson': log link, so the prediction is an unbiased mean rather than a median)."""
    from sklearn.ensemble import HistGradientBoostingRegressor
    X, yy = build_training(family, n_windows)
    y = np.array([np.log((a + EPS) / (L + EPS)) for a, L in yy]) if mode == "log_ratio" else np.array([a for a, _ in yy])
    m = HistGradientBoostingRegressor(loss=loss, max_depth=5, learning_rate=0.08, max_iter=250, l2_regularization=1.0, random_state=0)
    m.fit(X, y)
    pickle.dump(dict(model=m, n=len(y), mode=mode), open(path, "wb"))
    return RateForecaster(m, mode), len(y)


def load(family, root):
    p = Path(root) / f"forecaster_{family}.pkl"
    d = pickle.load(open(p, "rb"))
    return RateForecaster(d["model"], d.get("mode", "log_ratio"))
