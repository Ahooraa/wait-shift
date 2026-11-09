"""Structure-based pricing, version 2. No topology assumption: from the hop matrix alone find classes, offsets and a class-distance matrix with
    h[u, x] = c_u + H[class u, class x] + c_x      for all pairs except a listed set of exceptions,
which are corrected exactly. Correct on ANY network; how much it saves depends on how compressible the network is.
Also: first sums from the same factorisation; only D*M table entries; no sort per pricing; per-pricing choice between this and direct K*D pricing."""
import sys, os, pickle, time, inspect
for v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ[v] = "1"
sys.path.insert(0, "D:/DFPS implementation")
import numpy as np
import dfps.controllers as K
ORIG = K._place_incremental
src = inspect.getsource(ORIG).replace("def _place_incremental(", "def cand(")
KAPPA = float(os.environ.get("KAPPA", "1"))
BM = float(os.environ.get("BM", "4000"))


def R(s, a, b):
    assert s.count(a) == 1, a
    return s.replace(a, b)


LINE = "        new = ((T[None, :] + sign * Bh[idx]) / np.maximum(S[None, :] + sign * Wh[idx], 1e-12) * ra[None, :]).sum(axis=1) * t_hop_f[f]\n"
ST, STAT = {}, {}


def factor(h, L):
    N = h.shape[0]
    c = h[:, L].min(axis=1)
    _, cls = np.unique(h[:, L] - c[:, None], axis=0, return_inverse=True)
    cls = np.asarray(cls).ravel()
    C = int(cls.max()) + 1
    Res = h - c[:, None] - c[None, :]
    lo, V = int(Res.min()), int(Res.max() - Res.min()) + 1
    cnt = np.bincount(((cls[:, None] * C + cls[None, :]) * V + (Res - lo)).ravel(), minlength=C * C * V).reshape(C, C, V)
    Hm = np.maximum(cnt.argmax(axis=2) + lo, 0)
    fl = c[:, None] + Hm[cls[:, None], cls[None, :]] + c[None, :]
    nk, nd = np.nonzero(h != fl)
    return dict(c=c, cls=cls, C=C, H=Hm, nk=nk, nd=nd, fl=fl[nk, nd], hl=h[nk, nd])


def build(h):
    N = h.shape[0]
    deg = (h == 1).sum(axis=1)
    order = np.argsort(-deg, kind="stable")
    best = None
    for m in sorted({max(2, N // 32), max(2, N // 16), max(2, N // 8), max(2, N // 4)}):
        F = factor(h, order[:m])
        cost = F["C"] ** 2 + F["nk"].size
        if best is None or cost < best[0]:
            best = (cost, F, m)
    F = best[1]
    cm, Hx = int(F["c"].max()), int(F["H"].max())
    M = cm + Hx + 1
    Lv = max(cm + M, int(h.max()) + 1, int(F["fl"].max(initial=0)) + 1)
    lv = np.arange(Lv, dtype=float)
    wl, bl = np.exp(-lv), np.exp(-lv) * lv
    assert np.array_equal(wl[h], np.exp(-h.astype(float)))
    F["Vs"] = [int(v) for v in np.unique(F["H"])]
    F["MV"] = [(F["H"] == v).astype(float) for v in F["Vs"]]
    F.update(N=N, M=M, cm=cm, Lv=Lv, wl=wl, bl=bl, h=h, wc=wl[np.arange(cm + 1)[:, None] + np.arange(M)[None, :]], bc=bl[np.arange(cm + 1)[:, None] + np.arange(M)[None, :]],
             WH=wl[F["H"]], BH=bl[F["H"]], mark=np.zeros((cm + 1) * F["C"], dtype=bool), remap=np.zeros((cm + 1) * F["C"], dtype=np.intp), landmarks=best[2])
    return F


class Info:
    __slots__ = ("perm", "starts", "cq", "cd", "WL", "BL", "ra", "Hc", "nk", "j", "hl", "fl", "Cp", "D", "ex", "WHc", "BHc", "cdu")


def info(act, ra):
    s = ST["s"]
    I = Info(); cl = s["cls"][act]
    I.perm = np.argsort(cl, kind="stable"); cp = cl[I.perm]
    I.starts = np.flatnonzero(np.r_[True, cp[1:] != cp[:-1]]) if cp.size else np.zeros(0, dtype=np.intp); I.cq = cp[I.starts]; I.cd = s["c"][act][I.perm]
    I.WL, I.BL, I.ra = s["wc"][I.cd], s["bc"][I.cd], ra[I.perm]
    I.Hc = s["H"][:, I.cq]; I.WHc, I.BHc = s["WH"][:, I.cq], s["BH"][:, I.cq]
    I.Cp, I.D = I.cq.size, act.size
    pos = np.full(s["N"], -1); pos[act] = np.arange(act.size)
    keep = pos[s["nd"]] >= 0
    I.nk, I.j, I.hl, I.fl = s["nk"][keep], pos[s["nd"][keep]], s["hl"][keep], s["fl"][keep]
    I.ex = I.nk.size
    return I


def first_sums(c, act, I, W, B):
    s = ST["s"]
    h_ = np.flatnonzero(c)
    if h_.size * I.D <= KAPPA * (s["C"] * I.Cp + I.D + I.ex):
        return c[h_] @ W[h_][:, act], c[h_] @ B[h_][:, act]
    cn, cls = s["c"][h_], s["cls"][h_]
    y = c[h_] * s["wl"][cn]
    Y = np.bincount(cls, weights=y, minlength=s["C"]); Z = np.bincount(cls, weights=y * cn, minlength=s["C"])
    Ph = Y @ I.WHc; Ps = Z @ I.WHc + Y @ I.BHc
    n = np.diff(np.r_[I.starts, I.D])
    Phd = np.repeat(Ph, n); Psd = np.repeat(Ps, n)
    wd = s["wl"][I.cd]
    Sp = wd * Phd; Tp = wd * (Psd + I.cd * Phd)
    S = np.empty(I.D); T = np.empty(I.D); S[I.perm] = Sp; T[I.perm] = Tp
    m = c[I.nk] > 0
    if m.any():
        cc = c[I.nk[m]]
        S += np.bincount(I.j[m], weights=cc * (s["wl"][I.hl[m]] - s["wl"][I.fl[m]]), minlength=I.D)
        T += np.bincount(I.j[m], weights=cc * (s["bl"][I.hl[m]] - s["bl"][I.fl[m]]), minlength=I.D)
    return S, T


def price_g(S, T, ra, act, I, idx, sign, W, B):
    s = ST["s"]
    Kn, D = idx.size, I.D
    STAT["n"] = STAT.get("n", 0) + 1
    if Kn * D <= KAPPA * (D * s["M"] + Kn * I.Cp + I.ex):
        STAT["direct"] = STAT.get("direct", 0) + 1
        ix = np.ix_(idx, act)
        return ((T[None, :] + sign * B[ix]) / np.maximum(S[None, :] + sign * W[ix], 1e-12) * ra[None, :]).sum(axis=1)
    Sp, Tp = S[I.perm], T[I.perm]
    g = (Tp[:, None] + sign * I.BL) / np.maximum(Sp[:, None] + sign * I.WL, 1e-12) * I.ra[:, None]
    A = np.add.reduceat(g, I.starts, axis=0)
    w = s["cm"] + 1
    code = s["cls"][idx] * w + s["c"][idx]
    mark, remap = s["mark"], s["remap"]
    mark[code] = True; u = np.flatnonzero(mark); mark[u] = False
    remap[u] = np.arange(u.size)
    if u.size * I.Cp >= BM:                                     # far field as a dense matrix product over (class, offset)
        up = u // w; ux = u % w
        pu = up[np.r_[True, up[1:] != up[:-1]]]
        xs = np.flatnonzero(np.bincount(ux, minlength=w))
        ip = np.searchsorted(pu, up); ix = np.searchsorted(xs, ux)
        Af = np.zeros((s["C"], s["M"])); Af[I.cq] = A
        Fm = np.zeros((pu.size, xs.size))
        for mv, v in zip(s["MV"], s["Vs"]):
            Fm += mv[pu] @ Af[:, xs + v]
        far = Fm[ip, ix]
    else:
        far = A[np.arange(I.Cp)[None, :], (u % w)[:, None] + I.Hc[u // w]].sum(axis=1)
    new = far[remap[code]]
    if I.ex:
        cm = np.zeros(s["N"], dtype=bool); cm[idx] = True
        m = cm[I.nk]
        if m.any():
            nk, j, hl, fl = I.nk[m], I.j[m], I.hl[m], I.fl[m]
            wl, bl = s["wl"], s["bl"]
            v = ((T[j] + sign * bl[hl]) / np.maximum(S[j] + sign * wl[hl], 1e-12) - (T[j] + sign * bl[fl]) / np.maximum(S[j] + sign * wl[fl], 1e-12)) * ra[j]
            new = new + np.bincount(nk, weights=v, minlength=s["N"])[idx]
    STAT["Q"] = STAT.get("Q", 0) + u.size; STAT["ops"] = STAT.get("ops", 0) + D * s["M"] + u.size * I.Cp + I.ex; STAT["KD"] = STAT.get("KD", 0) + Kn * D; STAT["kn"] = STAT.get("kn", 0) + 1
    return new


def make():
    s = R(src, "            q = pre[f] = (r, W, B) if active.size >= 0.7 * N else (r[active], W[:, active], B[:, active])     # zero-weight points add nothing to a sum\n",
          "            _a = r[active]\n            q = pre[f] = (_a, active, INFO(active, _a))\n")
    s = R(s, "            s[0] += sign * Wh[k]\n            s[1] += sign * Bh[k]\n", "            s[0] += sign * W[k, Wh]\n            s[1] += sign * B[k, Wh]\n")
    s = R(s, "            sums[f] = [c @ Wh, c @ Bh]\n", "            sums[f] = list(FS(c, Wh, Bh, W, B))\n")
    s = R(s, LINE, "        new = FP(S, T, ra, Wh, Bh, idx, sign, W, B) * t_hop_f[f]\n")
    ns = dict(vars(K)); ns.update(FP=price_g, FS=first_sums, INFO=info); exec(s, ns); return ns["cand"]


C = make()


def run(sc, r, f):
    K._place_incremental = f
    i = r["inp"]; kw = dict(i["kw"]); kw["incr"] = True; kw["fast_cost"] = False; kw["lazy"] = False; kw["thin"] = 0
    t = time.perf_counter(); X = K.queue_aware_placement(sc, rates=i["rates"], counts=i["counts"], cur=i["cur"], busy=i["busy"], **kw)
    return X, time.perf_counter() - t


def compare(sc, rec, label):
    t0 = time.perf_counter(); ST["s"] = build(sc.network.h); tb = time.perf_counter() - t0
    s = ST["s"]; later = rec[1:]
    cf = "pl4_cache_" + label + ".pkl"
    if os.path.exists(cf):
        A, x0, t0_ = pickle.load(open(cf, "rb"))
    else:
        A = [min((run(sc, r, ORIG) for _ in range(2)), key=lambda x: x[1]) for r in later]
        x0, t0_ = run(sc, rec[0], ORIG)
        pickle.dump((A, x0, t0_), open(cf, "wb"))
    STAT.clear()
    B = [min((run(sc, r, C) for _ in range(2)), key=lambda x: x[1]) for r in later]
    st = dict(STAT); n = st["n"]; kn = max(st.get("kn", 0), 1)
    ta, tn = np.median([t for _, t in A]), np.median([t for _, t in B])
    d = sum(int(np.abs(a - b).sum()) for (a, _), (b, _) in zip(A, B))
    x1, t1_ = run(sc, rec[0], C)
    K._place_incremental = ORIG
    print(f"{label:30s} N {s['N']:5d} C {s['C']:4d} exc {s['nk'].size:7d} build {tb*1e3:5.0f} ms | later PL-4 {ta*1e3:8.1f} new {tn*1e3:8.1f} x{ta/tn:6.2f} slowest {max(t for _, t in B)*1e3:7.1f} diff {d:3d}/{sum(r['changed'] for r in later)} | first PL-4 {t0_:7.2f} s new {t1_:6.2f} s x{t0_/t1_:5.1f} diff {int(np.abs(x0-x1).sum()):3d} | direct {st.get('direct',0)/n:4.0%} KD {st.get('KD',0)/kn:9.0f} ops {st.get('ops',0)/kn:8.0f} Q {st.get('Q',0)/kn:5.0f}", flush=True)


if __name__ == "__main__":
    for fn in sys.argv[1:]:
        P = pickle.load(open(fn, "rb"))
        compare(P["sc"], P["rec"], os.path.basename(fn))
