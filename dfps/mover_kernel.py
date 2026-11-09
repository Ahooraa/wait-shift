"""MV-4 (9 Nov 2026): the gain-ordered request-move pass of MV-3 as a compiled kernel. The same decisions as MV-3 (checked by event hash); the cost changes:
  - one evaluation prices only the hosts that can still win: each function's hosts are kept sorted by wait estimate, and the scan stops at the first host whose lower
    bound (wait estimate + the input transfer every remote host must pay) is above the best price found;
  - a queue whose function has not changed since its last evaluation reuses that result;
  - the wait estimate is kept as a prefix table per (function, node), so a queue one request longer costs one heap step instead of a replay;
  - queues are linked stacks, so a move is O(1) instead of copying two lists.
Floating-point operations are in the order MV-3 uses, so prices are equal bit for bit. Ties: smallest host, as numpy.argmin over ascending hosts; the heap orders by (-gain, f, k).
Rounding is monotonic and every transfer term is non-negative, so a lower bound computed with the same additions can never exceed the true price."""
import numpy as np

try:
    from numba import njit
    HAVE_NUMBA = True
except ImportError:
    HAVE_NUMBA = False

    def njit(*a, **k):
        return (lambda f: f)

INF = float("inf")


@njit(cache=True)
def _svc(p, ah, mu, av_start, av, pre_start, pre_cap, pre_n, pool, pool_end):
    """Estimated finish of a request with `ah` requests ahead on availability heap p: heap[0] + mu after `ah` list-scheduling steps. Results are kept, so each step runs once."""
    if p < 0:
        return INF
    if ah < pre_n[p]:
        return pool[pre_start[p] + ah]
    if pre_start[p] < 0 or ah >= pre_cap[p]:
        cap = max(8, 2 * pre_cap[p], ah + 1)
        st = pool_end[0]
        pool_end[0] = st + cap
        for i in range(pre_n[p]):
            pool[st + i] = pool[pre_start[p] + i]
        pre_start[p], pre_cap[p] = st, cap
    a0, c = av_start[p], av_start[p + 1] - av_start[p]
    n, st = pre_n[p], pre_start[p]
    while n <= ah:
        v = av[a0] + mu
        pool[st + n] = v
        n += 1
        i = 0                                                           # heapreplace(root + mu)
        while True:
            l = 2 * i + 1
            if l >= c:
                break
            r = l + 1
            m = r if (r < c and av[a0 + r] < av[a0 + l]) else l
            if av[a0 + m] < v:
                av[a0 + i] = av[a0 + m]
                i = m
            else:
                break
        av[a0 + i] = v
    pre_n[p] = n
    return pool[st + ah]


@njit(cache=True)
def _set_vec(s, val, lo, hi, vec, order, pos):
    """New value of host slot s; keep order[lo:hi] sorted by vec. The value moves by about one service time, so few places shift."""
    vec[s] = val
    i = pos[s]
    while i + 1 < hi and vec[order[i + 1]] < val:
        order[i] = order[i + 1]
        pos[order[i]] = i
        i += 1
    while i > lo and vec[order[i - 1]] > val:
        order[i] = order[i - 1]
        pos[order[i]] = i
        i -= 1
    order[i] = s
    pos[s] = i


@njit(cache=True)
def _heap_push(hk, hq, n, key, q):
    i = n
    while i > 0:
        p = (i - 1) // 2
        if hk[p] < key or (hk[p] == key and hq[p] < q):
            break
        hk[i], hq[i] = hk[p], hq[p]
        i = p
    hk[i], hq[i] = key, q
    return n + 1


@njit(cache=True)
def _heap_pop(hk, hq, n):
    n -= 1
    key, q = hk[n], hq[n]
    i = 0
    while True:
        l = 2 * i + 1
        if l >= n:
            break
        r = l + 1
        m = r if (r < n and (hk[r] < hk[l] or (hk[r] == hk[l] and hq[r] < hq[l]))) else l
        if hk[m] < key or (hk[m] == key and hq[m] < q):
            hk[i], hq[i] = hk[m], hq[m]
            i = m
        else:
            break
    hk[i], hq[i] = key, q
    return n


@njit(cache=True)
def run_pass(N, lam, remote_hop1, h, free, mu, hs_start, hs, slot, av_idx, av_start, av, pool, active, tail, qlen, below, total, loc, in_start, in_d, out_start, out_d, out_pc, move_cap):
    """The pass. tail, qlen, below, loc, free and av are changed in place. Returns (number of moves, requests moved, destinations, counters)."""
    F = hs_start.size - 1
    A, P, H = active.size, av_start.size - 1, hs.size
    pre_start, pre_cap, pre_n = np.full(P, -1, dtype=np.int64), np.zeros(P, dtype=np.int64), np.zeros(P, dtype=np.int64)
    pool_end = np.zeros(1, dtype=np.int64)
    vec, order, pos = np.empty(H, dtype=np.float64), np.empty(H, dtype=np.int64), np.empty(H, dtype=np.int64)
    ready = np.zeros(F, dtype=np.bool_)
    ver = np.zeros(F, dtype=np.int64)
    m_ver, m_gain, m_host, m_r, m_blk = np.full(A, -1, dtype=np.int64), np.empty(A, dtype=np.float64), np.empty(A, dtype=np.int64), np.empty(A, dtype=np.int64), np.empty(A, dtype=np.bool_)
    hk, hq = np.empty(A + 1, dtype=np.float64), np.empty(A + 1, dtype=np.int64)
    mv_r, mv_k = np.empty(move_cap, dtype=np.int64), np.empty(move_cap, dtype=np.int64)
    aidx = {}
    for i in range(A):
        aidx[int(active[i])] = i
    c = np.zeros(5, dtype=np.int64)                                     # evaluations, reused results, hosts priced, hosts available, evaluations that met a full host
    n_h, n_mv = 0, 0
    first = True
    ia = 0
    while True:
        if first:                                                       # initial evaluation of every non-empty queue, then the gain-ordered loop
            if ia >= A:
                first = False
                continue
            q = int(active[ia])
            ia += 1
        else:
            if n_h == 0 or n_mv >= move_cap:
                break
            q = int(hq[0])
            n_h = _heap_pop(hk, hq, n_h)
        f, k = q // N, q % N
        r = tail[q]
        if r < 0:
            continue
        a = aidx[q]
        lo, hi = hs_start[f], hs_start[f + 1]
        if not ready[f]:                                                # wait estimates of this function at its hosts, sorted
            for s in range(lo, hi):
                qq = f * N + hs[s]
                vec[s] = _svc(av_idx[qq], qlen[qq], mu[f], av_start, av, pre_start, pre_cap, pre_n, pool, pool_end)
            o = np.argsort(vec[lo:hi]) + lo
            for i in range(hi - lo):
                order[lo + i] = o[i]
                pos[o[i]] = lo + i
            ready[f] = True
        if m_ver[a] == ver[f] and m_r[a] == r and not m_blk[a] and m_host[a] >= 0 and free[m_host[a]] >= total[r]:
            gain, best_h = m_gain[a], m_host[a]                         # nothing this result depends on has changed
            c[1] += 1
        else:
            c[0] += 1
            c[3] += hi - lo
            lc = loc[r]
            inp_k, inp_lb = 0.0, 0.0
            for i in range(in_start[r], in_start[r + 1]):
                inp_k = inp_k + h[lc, k] * in_d[i]
                inp_lb = inp_lb + in_d[i]
            out_k = 0.0
            for i in range(out_start[r], out_start[r + 1]):
                out_k = out_k + h[k, out_pc[i]] * out_d[i]
            if lc != k or not remote_hop1:                              # a host may then be at zero hops from the inputs
                inp_lb = 0.0
            a0 = (inp_k + _svc(av_idx[q], qlen[q] - 1, mu[f], av_start, av, pre_start, pre_cap, pre_n, pool, pool_end)) + lam * out_k
            best, best_h, blocked = INF, -1, False
            for i in range(lo, hi):
                s = order[i]
                v = vec[s]
                if inp_lb + v > best or inp_lb + v >= a0:       # no remaining host can win, or none can beat staying (then no move, as without this stop)
                    break
                x = hs[s]
                if x == k:
                    continue
                if free[x] < total[r]:
                    blocked = True
                    continue
                c[2] += 1
                inp = 0.0
                for j in range(in_start[r], in_start[r + 1]):
                    inp = inp + h[lc, x] * in_d[j]
                out = 0.0
                for j in range(out_start[r], out_start[r + 1]):
                    out = out + h[x, out_pc[j]] * out_d[j]
                p_ = (inp + v) + lam * out
                if p_ < best or (p_ == best and x < best_h):
                    best, best_h = p_, x
            if blocked:
                c[4] += 1
            if not (best_h >= 0 and best < a0):
                continue                                                # early stop: this queue is done
            gain = a0 - best
            m_ver[a], m_gain[a], m_host[a], m_r[a], m_blk[a] = ver[f], gain, best_h, r, blocked
        if first:
            n_h = _heap_push(hk, hq, n_h, -gain, q)
            continue
        if n_h > 0 and gain < -hk[0]:
            n_h = _heap_push(hk, hq, n_h, -gain, q)                     # stale: wait for its turn
            continue
        k2 = best_h                                                     # apply the move
        q2 = f * N + k2
        tail[q], qlen[q] = below[r], qlen[q] - 1
        below[r], tail[q2], qlen[q2] = tail[q2], r, qlen[q2] + 1
        loc[r] = k2
        free[k] += total[r]
        free[k2] -= total[r]
        mv_r[n_mv], mv_k[n_mv] = r, k2
        n_mv += 1
        ver[f] += 1
        for qq in (q, q2):
            s = slot[qq]
            if s >= 0:
                _set_vec(s, _svc(av_idx[qq], qlen[qq], mu[f], av_start, av, pre_start, pre_cap, pre_n, pool, pool_end), lo, hi, vec, order, pos)
        if qlen[q] > 0:
            n_h = _heap_push(hk, hq, n_h, -gain, q)                     # its next request: re-evaluated on pop
    return n_mv, mv_r, mv_k, c
