"""Candidate re-layouts that are allowed to decide differently from PL-4. Same objective for choosing hosts; different ORDER and fewer pricings.
  rounds=0, order=ratio : one container at a time, the function furthest below its target goes next (no global best-gain comparison)
  rounds=0, order=size  : one container at a time, largest containers first
  rounds=R, order=...   : R passes over the functions; each function is priced once per pass and places need/(passes left) containers, at the best hosts at least rmin hops apart
Every function that still fits is served before leftover capacity goes to functions already at target."""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_argv, sys.argv = sys.argv, sys.argv[:1]
import replay10 as R10
sys.argv = _argv
STAT, META = {}, []
REF = [None]


def _pl4left():
    """PL-4's own code, unchanged except that the leftover stage uses the furthest-below-target rule."""
    K = R10.K
    s = R10.src
    a, b = s.index("    if fill_leftover:"), s.index("    assert (X @ fw <= ecc + 1e-9)")
    block = """    if fill_leftover:
        while True:
            ok = fw <= free.max() + 1e-9
            if not ok.any():
                break
            have = X.sum(axis=0)
            ratio = (n_f - have) / np.maximum(n_f, 1)
            f = int(np.lexsort((-np.where(ok, fw, -1.0), -np.where(ok, ratio, -np.inf)))[0])
            idx = np.flatnonzero(free >= fw[f] - 1e-9)
            new, base = price(f, X[:, f].astype(float), idx, 1.0)
            k = int(idx[int(np.argmax(base - new))])
            need[f] = 1
            place(f, k)
"""
    ns = dict(vars(K)); exec(s[:a] + block + s[b:], ns)
    return ns["cand"]


def make(rounds=0, order="ratio", rmin=0, fact_from=400, leftover="ratio", kind=None):
    if kind == "pl4left":
        return _pl4left()

    def cand(cur, n_f, fw, ecc, dem, busy, mu, t_hop_f, W, B, fill_leftover):
        N, F = W.shape[0], fw.size
        use_f = N >= fact_from
        h = np.rint(np.divide(B, W)).astype(np.intp)
        if use_f and (R10.ST.get("s") is None or R10.ST["s"]["N"] != N):
            R10.ST["s"] = R10.build(h)
        pre, sums = {}, {}

        def prep(f):
            q = pre.get(f)
            if q is None:
                w = dem[f] if dem[f].sum() > 0 else np.ones(N)
                r = (busy[f] / mu[f]) * w / w.sum()
                a = np.flatnonzero(r > 0); ra = r[a]
                q = pre[f] = (ra, a, R10.info(a, ra) if use_f else None)
            return q

        def get(f, c):
            s = sums.get(f)
            if s is None:
                ra, a, I = prep(f)
                if use_f:
                    s = list(R10.first_sums(c, a, I, W, B))
                else:
                    h_ = np.flatnonzero(c)
                    s = [c[h_] @ W[h_][:, a], c[h_] @ B[h_][:, a]]
                sums[f] = s
            return s

        def bump(f, k, sign):
            s = sums.get(f)
            if s is not None:
                a = pre[f][1]
                s[0] += sign * W[k, a]; s[1] += sign * B[k, a]

        def price(f, c, idx, sign):
            ra, a, I = prep(f); S, T = get(f, c)
            STAT["pricings"] = STAT.get("pricings", 0) + 1
            if use_f:
                new = R10.price_g(S, T, ra, a, I, idx, sign, W, B) * t_hop_f[f]
            else:
                ix = np.ix_(idx, a)
                new = ((T[None, :] + sign * B[ix]) / np.maximum(S[None, :] + sign * W[ix], 1e-12) * ra[None, :]).sum(axis=1) * t_hop_f[f]
            return new, float((T / np.maximum(S, 1e-12) * ra).sum()) * t_hop_f[f]

        def pick(g, idx, q, rm, best_first=True):
            out = []
            for j in np.argsort(-g if best_first else g, kind="stable"):
                k = int(idx[j])
                if rm and out and h[k, out].min() < rm:
                    continue
                out.append(k)
                if len(out) >= q:
                    break
            return out

        X = cur.copy()
        for f in np.flatnonzero(cur.sum(axis=0) > n_f):                 # shrink, smallest loss first
            f = int(f); c = X[:, f].astype(float)
            rm_left = int(c.sum() - n_f[f])
            passes = rounds if rounds else rm_left
            while rm_left > 0 and c.sum() > 1:
                hosts = np.flatnonzero(c > 0)
                q = int(np.ceil(rm_left / max(passes, 1))) if rounds else 1
                q = min(q, int(c.sum()) - 1, rm_left)
                new, _ = price(f, c, hosts, -1.0)
                for k in pick(-new, hosts, q, rmin if rounds else 0):
                    X[k, f] -= 1; c[k] -= 1.0; bump(f, k, -1.0); rm_left -= 1
                passes = max(passes - 1, 1)
        free = ecc - X @ fw
        need = n_f - X.sum(axis=0)
        stuck = np.zeros(F, dtype=bool)

        def place(f, k):
            X[k, f] += 1; free[k] -= fw[f]; need[f] -= 1; bump(f, k, 1.0)

        def step(f, q, rm):
            if need[f] <= 0 or stuck[f]:
                return 0
            idx = np.flatnonzero(free >= fw[f] - 1e-9)
            if idx.size == 0:
                if X[:, f].sum() > 0:
                    stuck[f] = True
                    return 0
                donors = [(fw[g], k, g) for k in range(N) for g in np.flatnonzero(X[k]) if X[:, g].sum() > 1 and free[k] + fw[g] >= fw[f] - 1e-9]
                if not donors:
                    raise ValueError("no feasible layout: a function with no instance fits nowhere")
                _, k, g = min(donors)
                X[k, g] -= 1; free[k] += fw[g]; bump(int(g), k, -1.0)
                place(f, k)
                return 1
            have = X[:, f].sum() > 0
            new, base = price(f, X[:, f].astype(float), idx, 1.0)
            hs = pick((base - new) if have else -new, idx, q, rm)
            for k in hs:
                place(f, k)
            return len(hs)

        def order_now():
            ratio = np.where(n_f > 0, need / np.maximum(n_f, 1), 0.0)
            if order == "size":
                return np.lexsort((-ratio, -fw))
            if order == "util":                                         # the function that would be most loaded on what it holds now goes first
                return np.lexsort((-fw, -(busy / np.maximum(X.sum(axis=0), 1))))
            return np.lexsort((-fw, -ratio))

        if rounds == 0:
            while True:
                act = (need > 0) & ~stuck
                if not act.any():
                    break
                if order == "size":
                    f = int(np.lexsort((-np.where(act, need / np.maximum(n_f, 1), -1.0), -np.where(act, fw, -1.0)))[0])
                else:
                    f = int(np.lexsort((-np.where(act, fw, -1.0), -np.where(act, need / np.maximum(n_f, 1), -1.0)))[0])
                step(f, 1, 0)
        else:
            for r in range(rounds, 0, -1):
                for f in order_now():
                    if need[f] > 0:
                        step(int(f), int(np.ceil(need[f] / r)), rmin)
            while ((need > 0) & ~stuck).any():
                got = 0
                for f in order_now():
                    if need[f] > 0 and not stuck[f]:
                        got += step(int(f), int(need[f]), 0)
                if got == 0 and ((need > 0) & ~stuck).any():
                    stuck[(need > 0)] = True
        if fill_leftover and leftover == "gain":                        # PL-4's leftover stage: best gain across all functions
            bestg, bestk, gk, gv = np.full(F, -np.inf), np.zeros(F, dtype=int), {}, {}

            def reprice2(f):
                idx = np.flatnonzero(free >= fw[f] - 1e-9)
                gk[f] = idx
                if idx.size == 0:
                    gv[f] = np.zeros(0)
                    return
                new, base = price(f, X[:, f].astype(float), idx, 1.0)
                gv[f] = (base - new) if X[:, f].sum() > 0 else -new

            def refresh2(f):
                bestg[f] = -np.inf
                if need[f] > 0:
                    idx, g = gk[f], gv[f]
                    ok = free[idx] >= fw[f] - 1e-9
                    if ok.any():
                        j = int(np.argmax(np.where(ok, g, -np.inf)))
                        bestg[f], bestk[f] = g[j], idx[j]

            need[:] = 1
            for f in range(F):
                reprice2(f); refresh2(f)
            while True:
                bf = int(np.argmax(bestg))
                if bestg[bf] == -np.inf:
                    break
                bk = int(bestk[bf])
                place(bf, bk)
                need[bf] = 1
                reprice2(bf); refresh2(bf)
                for f in np.flatnonzero((bestk == bk) & (bestg > -np.inf)):
                    refresh2(int(f))
        if fill_leftover and leftover == "ratio":                       # what is left goes to whoever is furthest below target and still fits
            while True:
                ok = fw <= free.max() + 1e-9
                if not ok.any():
                    break
                have = X.sum(axis=0)
                ratio = (n_f - have) / np.maximum(n_f, 1)
                f = int(np.lexsort((-np.where(ok, fw, -1.0), -np.where(ok, ratio, -np.inf)))[0])
                idx = np.flatnonzero(free >= fw[f] - 1e-9)
                new, base = price(f, X[:, f].astype(float), idx, 1.0)
                k = int(idx[int(np.argmax(base - new))])
                need[f] = 1
                place(f, k)
        assert (X @ fw <= ecc + 1e-9).all() and (X.sum(axis=0) >= 1).all()
        if REF[0] is not None:
            def obj(Y):
                tot = 0.0
                for f_ in range(F):
                    ra, a, _ = prep(f_); c_ = Y[:, f_].astype(float); h_ = np.flatnonzero(c_)
                    S_, T_ = c_[h_] @ W[h_][:, a], c_[h_] @ B[h_][:, a]
                    tot += float((T_ / np.maximum(S_, 1e-12) * ra).sum()) * t_hop_f[f_]
                return tot
            META.append((obj(X), obj(REF[0])))
        return X
    return cand


VARIANTS = {"oracle1": dict(rounds=0, order="ratio", leftover="none"), "orderonly": dict(rounds=0, order="ratio", leftover="gain"), "leftonly": dict(kind="pl4left"), "pass8gl": dict(rounds=8, order="ratio", rmin=2, leftover="gain"),
            "ratio1": dict(rounds=0, order="ratio"), "size1": dict(rounds=0, order="size"),
            "ratio2": dict(rounds=2, order="ratio", rmin=2), "ratio8": dict(rounds=8, order="ratio", rmin=2), "util4": dict(rounds=4, order="util", rmin=2),
            "ratio4": dict(rounds=4, order="ratio", rmin=2), "size4": dict(rounds=4, order="size", rmin=2), "size2": dict(rounds=2, order="size", rmin=2), "size8": dict(rounds=8, order="size", rmin=2)}
