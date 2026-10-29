"""Step A analysis (2026-10-28): which dimensions and causes drive the four P99 problems of 'ours' on F3.
Input: stepA.pkl from stepA_collect.py. Prints a report; writes stepA_result.json next to the pickle."""
import json
import pickle
import sys
from bisect import bisect_left, bisect_right
from collections import Counter, defaultdict

import numpy as np
from scipy.stats import spearmanr

P = sys.argv[1]
D = pickle.load(open(P, "rb"))
H = np.array(D["h"])
BW, EPD, EX, SLO = D["bw"], D["epd"], D["exec_time"], D["slo_factor"]
PERIOD = D["period"]
SHIFT = 600.0


def stt(s, a, b):
    return float(H[a][b] * (EPD + s / BW))


def auc(score, y):
    """P(score of a positive > score of a negative), ties 0.5."""
    score, y = np.asarray(score, float), np.asarray(y, bool)
    if y.all() or not y.any():
        return float("nan")
    from scipy.stats import rankdata
    r = rankdata(score)
    n1, n0 = float(y.sum()), float((~y).sum())
    return float((r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def q(x, ps=(50, 90, 99)):
    x = np.asarray(x, float)
    return {f"p{p}": round(float(np.percentile(x, p)), 2) for p in ps} if len(x) else {}


# ---------------------------------------------------------------- workflow structure (exec-only nominal schedule)
W = {}
for wid, w in D["wfs"].items():
    n, ft, par, ch = w["n"], w["ft"], w["parents"], w["children"]
    ex = [EX[ft[t]] for t in range(n)]
    est = [0.0] * n
    for t in range(n):
        est[t] = max((est[u] + ex[u] for u in par[t]), default=0.0)
    rem = [0.0] * n
    for t in reversed(range(n)):
        rem[t] = ex[t] + max((rem[c] for c in ch[t]), default=0.0)
    cp = max(est[t] + rem[t] for t in range(n))
    flt = [cp - est[t] - rem[t] for t in range(n)]
    anc = [set() for _ in range(n)]
    for t in range(n):
        for u in par[t]:
            anc[t] |= anc[u] | {u}
    joins = [t for t in range(n) if len(par[t]) > 1]
    # dist[t][j]: longest exec path from the start of t to the start of join j (t an ancestor of j)
    dist = {}
    for j in joins:
        d = {}
        for t in sorted(anc[j], reverse=True):
            best = None
            for c in ch[t]:
                if c == j:
                    v = ex[t]
                elif c in anc[j]:
                    v = ex[t] + d[c]
                else:
                    continue
                best = v if best is None else max(best, v)
            d[t] = best
        dist[j] = d
    mb = w["input_size"] + sum(w["ss"].values())
    W[int(wid)] = dict(n=n, ft=ft, par=par, ch=ch, ss=w["ss"], ex=ex, est=est, rem=rem, cp=cp, flt=flt, anc=anc, joins=joins,
                       dist=dist, mb=mb, crit=w["crit"])

# ---------------------------------------------------------------- trace
tasks = defaultdict(dict)
for row in D["trace"]["tasks"]:
    tasks[row[0]][row[2]] = row          # (rid, wid, t, plan, node, t_first, t_start, t_end, n_moves)
reqs = {r[0]: r for r in D["trace"]["reqs"]}
soj_all = np.array([r[3] - r[2] for r in reqs.values()])
P99, P95 = np.percentile(soj_all, 99), np.percentile(soj_all, 95)

# last move per (rid, task) and the move sequence per run
moves_of = defaultdict(list)
for i, mv in enumerate(D["mlog"]):
    moves_of[(mv["rid"], mv["task"])].append(i)

R = {}                                   # per complete in-window request
for rid, (_, wid, t_arr, t_done) in reqs.items():
    w, T = W[wid], tasks.get(rid, {})
    if len(T) < w["n"]:
        continue
    end = {t: T[t][7] for t in T}
    arr_in = {}                          # realised arrival of u's output at t's planned node
    for t in T:
        for u in w["par"][t]:
            arr_in[(u, t)] = end[u] + stt(w["ss"][(u, t)], T[u][4], T[t][3])
    edge_slack = {(u, t): T[t][5] - a for (u, t), a in arr_in.items()}
    slack = {}
    for t in sorted(T, reverse=True):
        slack[t] = (t_done - end[t]) if not w["ch"][t] else min(edge_slack[(t, c)] + slack[c] for c in w["ch"][t])
    t = max(T, key=lambda x: end[x])
    chain, crit_edges = [t], set()
    while w["par"][t]:
        u = max(w["par"][t], key=lambda x: arr_in[(x, t)])
        crit_edges.add((u, t))
        chain.append(u)
        t = u
    s = t_done - t_arr
    R[rid] = dict(wid=wid, t_arr=t_arr, soj=s, tail=s >= P99, top5=s >= P95, T=T, arr_in=arr_in, slack=slack,
                  chain=set(chain), crit_edges=crit_edges)
print(f"requests {len(R)}  p99 {P99:.1f}  p95 {P95:.1f}  moves logged {len(D['mlog'])}")
OUT = {"p99": float(P99), "n_req": len(R)}

# ================================================================ 0. who is in the tail: workflow size dimensions
print("\n=== 0. tail membership by workflow size ===")
rows = [(r["wid"], r["soj"], r["tail"]) for r in R.values()]
by = defaultdict(list)
for wid, s, tl in rows:
    by[wid].append((s, tl))
feat = {"n_tasks": lambda w: w["n"], "crit_path_s": lambda w: w["cp"], "state_MB": lambda w: w["mb"],
        "n_joins": lambda w: len(w["joins"])}
x = {k: np.array([f(W[r["wid"]]) for r in R.values()]) for k, f in feat.items()}
y_tail = np.array([r["tail"] for r in R.values()])
soj = np.array([r["soj"] for r in R.values()])
stretch = soj / np.array([W[r["wid"]]["cp"] for r in R.values()])
o0 = {}
for k, v in x.items():
    o0[k] = dict(auc_tail=round(auc(v, y_tail), 3), rho_soj=round(spearmanr(v, soj)[0], 3), rho_stretch=round(spearmanr(v, stretch)[0], 3))
    print(f"{k:12s} AUC(tail)={o0[k]['auc_tail']:.3f}  rho(sojourn)={o0[k]['rho_soj']:+.3f}  rho(sojourn/CP)={o0[k]['rho_stretch']:+.3f}")
qs = np.percentile(x["crit_path_s"], [0, 25, 50, 75, 100])
for lo, hi in zip(qs[:-1], qs[1:]):
    m = (x["crit_path_s"] >= lo) & (x["crit_path_s"] <= hi)
    print(f"  CP {lo:6.1f}-{hi:6.1f}s: share of requests {m.mean():.2f}  share of tail {y_tail[m].sum()/y_tail.sum():.2f}  "
          f"median stretch {np.median(stretch[m]):.2f}")
OUT["tail_by_size"] = o0

# ================================================================ 1. fracturing: physics is exact, relevance is the question
print("\n=== 1. fracturing (extra first-hop cost) ===")
E = []
for rid, r in R.items():
    w, T = W[r["wid"]], r["T"]
    for (u, v), size in w["ss"].items():
        pu, pv, au = T[u][3], T[v][3], T[u][4]
        extra = stt(size, au, pv) - stt(size, pu, pv)
        mv = moves_of.get((rid, u))
        src = D["mlog"][mv[-1]]["src"] if mv else "none"
        E.append(dict(extra=extra, size=size, dh=int(H[au][pv] - H[pu][pv]), on=(u, v) in r["crit_edges"], tail=r["tail"],
                      src=src, flt=w["flt"][v], n=w["n"], moved=au != pu, wid=r["wid"]))
ex_ = np.array([e["extra"] for e in E])
pred = np.array([e["dh"] * (EPD + e["size"] / BW) for e in E])
print(f"edges {len(E)}; extra == dh*(epd+size/bw) exactly: max abs err {np.max(np.abs(ex_-pred)):.2e}  (the dimension is size x hops, no fit needed)")
o1 = {}
for grp in ("all", "tail"):
    sel = [e for e in E if grp == "all" or e["tail"]]
    nreq = len(R) if grp == "all" else int(y_tail.sum())
    tot = sum(e["extra"] for e in sel)
    on = sum(e["extra"] for e in sel if e["on"])
    bysrc = Counter()
    bysrc_on = Counter()
    for e in sel:
        bysrc[e["src"]] += e["extra"]
        if e["on"]:
            bysrc_on[e["src"]] += e["extra"]
    o1[grp] = dict(extra_per_req=round(tot / nreq, 2), on_path_per_req=round(on / nreq, 2), on_path_share=round(on / tot, 3) if tot else None,
                   by_src_per_req={k: round(v / nreq, 2) for k, v in bysrc.items()},
                   on_path_by_src_per_req={k: round(v / nreq, 2) for k, v in bysrc_on.items()})
    print(f"[{grp}] extra/req {o1[grp]['extra_per_req']}s, of which on realised critical path {o1[grp]['on_path_per_req']}s "
          f"({o1[grp]['on_path_share']})")
    print(f"     by cause of the parent's (last) move: {o1[grp]['by_src_per_req']}")
    print(f"     on-path part by cause:                {o1[grp]['on_path_by_src_per_req']}")
# relevance: P(edge on the critical path | features) -- what should weight the downstream term instead of a constant lambda
moved_edges = [e for e in E if e["moved"]]
on = np.array([e["on"] for e in moved_edges])
o1["relevance_auc_on_path"] = {}
for k in ("flt", "size", "n"):
    v = np.array([e[k] for e in moved_edges], float)
    a = auc(-v if k == "flt" else v, on)
    o1["relevance_auc_on_path"][k] = round(a, 3)
print(f"moved-parent edges {len(moved_edges)}: P(on path) = {on.mean():.3f};  AUC predicting on-path: "
      f"-structural float of child {o1['relevance_auc_on_path']['flt']:.3f}, size {o1['relevance_auc_on_path']['size']:.3f}, n_tasks {o1['relevance_auc_on_path']['n']:.3f}")
fl = np.array([e["flt"] for e in moved_edges])
for lo, hi in ((0, 1e-9), (1e-9, 5), (5, 20), (20, 1e9)):
    m = (fl >= lo) & (fl < hi) if hi > 1e-9 else (fl <= 1e-9)
    if m.sum():
        print(f"  child float {lo:>5}-{hi:<6}: edges {m.sum():6d}  P(on path) {on[m].mean():.3f}")
OUT["fracture"] = o1

# ================================================================ 2. join gap -> desync cost
print("\n=== 2. join gap: raw gap vs structural imbalance vs desync cost ===")
J = []
for rid, r in R.items():
    w, T, t_arr = W[r["wid"]], r["T"], r["t_arr"]
    for x_ in w["joins"]:
        ps = w["par"][x_]
        arr = {u: r["arr_in"][(u, x_)] for u in ps}
        nom = {u: w["est"][u] + w["ex"][u] for u in ps}               # nominal end of u, exec only
        dly = {u: arr[u] - t_arr - nom[u] for u in ps}                 # delay of branch u (wait, transfer, exec noise)
        gap = max(arr.values()) - min(arr.values())
        sgap = max(nom.values()) - min(nom.values())
        desync = max(arr.values()) - (t_arr + min(dly.values()) + max(nom.values()))
        late = max(ps, key=lambda u: arr[u])
        # was an earlier sibling already delivered while the late parent was still waiting in a queue?
        others = [arr[u] for u in ps if u != late]
        known = min(others) <= T[late][6]
        J.append(dict(gap=gap, sgap=sgap, desync=desync, on=x_ in r["chain"], tail=r["tail"], known=known,
                      late_wait=T[late][6] - T[late][5], late_moves=T[late][8],
                      late_extra=stt(w["ss"][(late, x_)], T[late][4], T[x_][3]) - stt(w["ss"][(late, x_)], T[late][3], T[x_][3])))
o2 = {}
for grp in ("all", "tail"):
    sel = [j for j in J if grp == "all" or j["tail"]]
    sel_on = [j for j in sel if j["on"]]
    o2[grp] = dict(n=len(sel), gap=round(np.mean([j["gap"] for j in sel]), 2), structural=round(np.mean([j["sgap"] for j in sel]), 2),
                   desync=round(np.mean([j["desync"] for j in sel]), 2),
                   desync_on_path=round(np.mean([j["desync"] for j in sel_on]), 2) if sel_on else None,
                   known_share_of_desync_on_path=round(sum(j["desync"] for j in sel_on if j["known"]) / max(1e-9, sum(j["desync"] for j in sel_on)), 3) if sel_on else None)
    print(f"[{grp}] joins {o2[grp]['n']}: raw gap {o2[grp]['gap']}s = structural {o2[grp]['structural']}s + ...; "
          f"desync cost {o2[grp]['desync']}s (on critical path: {o2[grp]['desync_on_path']}s); "
          f"share of on-path desync where a sibling had ALREADY delivered while the late parent waited: {o2[grp]['known_share_of_desync_on_path']}")
dj = np.array([j["desync"] for j in J])
o2["rho_desync"] = {}
for k in ("late_wait", "late_moves", "late_extra", "sgap"):
    v = np.array([j[k] for j in J], float)
    o2["rho_desync"][k] = round(spearmanr(v, dj)[0], 3)
print(f"rho(desync, x): late parent's own wait {o2['rho_desync']['late_wait']:+.3f}, its moves {o2['rho_desync']['late_moves']:+.3f}, "
      f"its fracture extra {o2['rho_desync']['late_extra']:+.3f}, structural gap {o2['rho_desync']['sgap']:+.3f}")
OUT["join"] = o2

# ================================================================ 3. urgency: which online slack has the right dimension
print("\n=== 3. urgency: online slack signals vs realised slack / tail-criticality ===")
U = defaultdict(list)
for rid, r in R.items():
    w, T, t_arr = W[r["wid"]], r["T"], r["t_arr"]
    cp = w["cp"]
    for t, row in T.items():
        el = row[5] - t_arr
        lag = el - w["est"][t]
        req_slack = SLO * w["crit"] - el - w["rem"][t]          # = dfps/o3s.py _slack (2026-10-27)
        local = cp - el - w["rem"][t]                           # = structural float - lag
        jl = None                                               # sibling-aware: will t's branch reach a join after an already delivered sibling?
        for j in w["joins"]:
            if t not in w["anc"][j]:
                continue
            sib = [r["arr_in"][(u, j)] for u in w["par"][j] if u != t and u not in w["anc"][t] and t not in w["anc"][u] and u != j
                   and r["arr_in"][(u, j)] <= row[5]]
            if sib:
                v = row[5] + w["dist"][j][t] - max(sib)
                jl = v if jl is None else max(jl, v)
        U["neg_projected_soj"].append(-(el + w["rem"][t]))         # absolute: elapsed + own remaining critical path
        U["neg_rem"].append(-w["rem"][t])
        U["req_slack"].append(req_slack)
        U["local_slack"].append(local)
        U["local_slack_over_cp"].append(local / cp)
        U["lag"].append(-lag)
        U["lag_over_cp"].append(-lag / cp)
        U["join_lag"].append(-(jl if jl is not None else -1e9))
        U["_has_jl"].append(jl is not None)
        U["_real"].append(r["slack"][t])
        U["_crit_tail"].append(r["tail"] and t in r["chain"])
        U["_crit"].append(t in r["chain"])
real = np.array(U["_real"])
ct = np.array(U["_crit_tail"])
cr = np.array(U["_crit"])
o3 = {}
for k in ("req_slack", "local_slack", "local_slack_over_cp", "lag", "lag_over_cp", "neg_projected_soj", "neg_rem"):
    v = np.array(U[k])
    o3[k] = dict(rho_realised_slack=round(spearmanr(v, real)[0], 3), auc_on_path=round(auc(-v, cr), 3), auc_on_path_tail=round(auc(-v, ct), 3))
    print(f"{k:20s} rho(realised slack)={o3[k]['rho_realised_slack']:+.3f}  AUC(on path)={o3[k]['auc_on_path']:.3f}  "
          f"AUC(on path of a tail request)={o3[k]['auc_on_path_tail']:.3f}")
hj = np.array(U["_has_jl"])
if hj.any():
    jv = np.array(U["join_lag"])[hj]
    lv = np.array(U["local_slack"])[hj]
    o3["join_lag"] = dict(defined_share=round(hj.mean(), 3), rho_realised_slack=round(spearmanr(jv, real[hj])[0], 3),
                          auc_on_path=round(auc(-jv, cr[hj]), 3), local_slack_same_subset_auc=round(auc(-lv, cr[hj]), 3))
    print(f"join_lag (defined for {o3['join_lag']['defined_share']:.1%} of tasks) rho={o3['join_lag']['rho_realised_slack']:+.3f} "
          f"AUC(on path)={o3['join_lag']['auc_on_path']:.3f}  vs local_slack on the same subset {o3['join_lag']['local_slack_same_subset_auc']:.3f}")
OUT["urgency"] = o3

# ================================================================ 4. moves and ping-pong kinds, scored against the queue-neighbour counterfactual
print("\n=== 4. moves: kinds of re-move and whether they paid off ===")
starts = D["starts"]
ce = defaultdict(list)                                          # f -> sorted [(t, k)] container-count changes
for t, lst in D["cnt_events"]:
    for f, k in lst:
        ce[f].append((t, k))
for f in ce:
    ce[f].sort()


def changed(f, k, t0, t1):
    lst = ce.get(f, [])
    i, j = bisect_right(lst, (t0, 10 ** 9)), bisect_left(lst, (t1, -1))
    return any(kk == k for _, kk in lst[i:j])


def nb_start(key, k_old):
    if key is None:
        return None
    s = starts.get((key[0], key[1]))
    if s is None or s[2] != key[2] or s[1] != k_old:            # neighbour moved later or ran elsewhere: no counterfactual
        return None
    return s[0]


pool = defaultdict(list)                                        # (node, f) -> sorted [(start, rid, task)] of every run
for (rid_, task_), s in starts.items():
    if len(s) > 3:
        pool[(s[1], s[3])].append((s[0], rid_, task_))
for k_ in pool:
    pool[k_].sort()
pool_t = {k_: [x[0] for x in v] for k_, v in pool.items()}


def slot_start(k_old, f, t, pos, me):
    """FIFO counterfactual: had the run stayed at position pos of (k_old, f) at time t, it would have taken the (pos+1)-th
    start there after t (later arrivals queue behind it). Its own start is skipped if it later returned and ran there."""
    lst, ts = pool.get((k_old, f), []), pool_t.get((k_old, f), [])
    i = bisect_left(ts, t)
    c = -1
    while i < len(lst):
        if (lst[i][1], lst[i][2]) != me:
            c += 1
            if c == pos:
                return lst[i][0]
        i += 1
    return None


ML = D["mlog"]
co = Counter((round(mv["t"], 3), mv["f"], mv["k_new"]) for mv in ML if mv["src"] == "rebal")
K = []
for (rid, task), idx in moves_of.items():
    st = starts.get((rid, task))
    visited = []
    for n_i, i in enumerate(idx):
        mv = ML[i]
        prev = ML[idx[n_i - 1]] if n_i else None
        kind = "first" if n_i == 0 else ("return" if mv["k_new"] in visited or mv["k_new"] == (ML[idx[0]]["k_old"]) else "onward")
        visited.append(mv["k_old"])
        rec = dict(rid=rid, task=task, src=mv["src"], kind=kind, n=n_i, t=mv["t"], delay=mv["delay"], inwin=mv["inwin"], wid=mv["wid"], f=mv["f"],
                   total=mv["total"], plan=mv["plan"], k_new=mv["k_new"], k_old=mv["k_old"],
                   herd=co[(round(mv["t"], 3), mv["f"], mv["k_new"])] if mv["src"] == "rebal" else 0)
        if prev is not None:
            rec["dt"] = mv["t"] - prev["t"]
            rec["placement_changed"] = changed(mv["f"], mv["k_old"], prev["t"], mv["t"] + 1e-9) or changed(mv["f"], mv["k_new"], prev["t"], mv["t"] + 1e-9)
            rec["prev_src"] = prev["src"]
            rec["crossed_shift"] = prev["t"] < SHIFT <= mv["t"]
        if "a_old" in mv and st is not None:
            ao, an = mv["a_old"], mv["a_new"]
            rec["pred_gain"] = (ao[0] + ao[1] + 0.5 * ao[2]) - (an[0] + an[1] + 0.5 * an[2])
            rec["pred_gain_wait"] = (ao[0] + ao[1]) - (an[0] + an[1])     # start-time part only
            rec["out_delta"] = an[2] - ao[2]                               # extra first-hop output transfer this move causes
            rr = R.get(rid)
            rec["tail_crit"] = bool(rr and rr["tail"] and task in rr["chain"])
            rec["crit"] = bool(rr and task in rr["chain"])
            act = st[0]
            cf = slot_start(mv["k_old"], mv["f"], mv["t"], mv["pos"], (rid, task))
            if cf is not None:
                rec["real_gain_wait"] = cf - act                             # >0: started earlier than had it stayed
            lo = nb_start(mv["ahead"], mv["k_old"])
            if lo is not None:
                rec["gain_lower_bound"] = lo - act                           # the neighbour ahead started no later than it would have
            rec["qlen_old"], rec["pos"], rec["qlen_new"] = mv["qlen_old"], mv["pos"], mv["qlen_new"]
            rec["cnt_old"], rec["cnt_new"] = mv["cnt_old"], mv["cnt_new"]
        K.append(rec)
src = Counter(k["src"] for k in K)
print("moves by source:", dict(src))
print("re-moves (n>=2nd move of a run):", dict(Counter((k["src"], k["kind"]) for k in K if k["n"] > 0)))


def summ(sel, label):
    g = [k for k in sel if "real_gain_wait" in k]
    if not g:
        print(f"  {label:44s} n={len(sel):6d} (no counterfactual)")
        return None
    rg = np.array([k["real_gain_wait"] for k in g])
    pg = np.array([k["pred_gain_wait"] for k in g])
    net = rg - np.array([k["out_delta"] for k in g])
    lb = [k["gain_lower_bound"] for k in g if "gain_lower_bound" in k]
    d = dict(n=len(sel), n_cf=len(g), pred_wait_gain=round(float(np.mean(pg)), 2), real_wait_gain=round(float(np.mean(rg)), 2),
             real_median=round(float(np.median(rg)), 2), net_gain=round(float(np.mean(net)), 2),
             share_harmful=round(float((net < 0).mean()), 3), overestimate=round(float(np.mean(pg - rg)), 2),
             lower_bound=round(float(np.mean(lb)), 2) if lb else None)
    print(f"  {label:46s} n={d['n']:6d} cf={d['n_cf']:6d} pred {d['pred_wait_gain']:+6.2f}s real {d['real_wait_gain']:+6.2f}s "
          f"(med {d['real_median']:+6.2f}, lb {d['lower_bound']}) net-of-fracture {d['net_gain']:+6.2f}s harmful {d['share_harmful']:.1%}")
    return d


reb = [k for k in K if k["src"] == "rebal"]
o4 = {"by_source": dict(src)}
print("rebalance moves, realised start-time gain vs the queue neighbours that stayed:")
o4["rebal_first"] = summ([k for k in reb if k["n"] == 0], "first move")
o4["rebal_re"] = summ([k for k in reb if k["n"] > 0], "re-move (any)")
o4["rebal_re_return"] = summ([k for k in reb if k["n"] > 0 and k["kind"] == "return"], "re-move, RETURN to a node it left")
o4["rebal_re_onward"] = summ([k for k in reb if k["n"] > 0 and k["kind"] == "onward"], "re-move, onward to a new node")
o4["rebal_re_after_forced"] = summ([k for k in reb if k["n"] > 0 and k.get("prev_src") in ("reroute", "orphan")], "re-move after a FORCED move")
o4["rebal_re_placement_changed"] = summ([k for k in reb if k["n"] > 0 and k.get("placement_changed")], "re-move, placement changed since last move")
o4["rebal_re_static"] = summ([k for k in reb if k["n"] > 0 and not k.get("placement_changed") and k.get("prev_src") == "rebal"],
                             "re-move, nothing changed, prev move voluntary")
o4["rebal_re_quick"] = summ([k for k in reb if k["n"] > 0 and k.get("dt", 1e9) <= PERIOD + 1e-6], f"re-move within one period ({PERIOD}s)")
o4["rebal_re_slow"] = summ([k for k in reb if k["n"] > 0 and k.get("dt", 0) > PERIOD + 1e-6], "re-move after > one period")
o4["rebal_re_shift"] = summ([k for k in reb if k["n"] > 0 and k.get("crossed_shift")], "re-move across the regime shift")
o4["tail_crit_first"] = summ([k for k in reb if k["n"] == 0 and k.get("tail_crit")], "first move, task on a TAIL request's critical path")
o4["tail_crit_re"] = summ([k for k in reb if k["n"] > 0 and k.get("tail_crit")], "re-move, task on a TAIL request's critical path")
o4["tail_crit_re_return"] = summ([k for k in reb if k["n"] > 0 and k.get("tail_crit") and k["kind"] == "return"], "  ... of which RETURN")
for lo, hi in ((1, 1), (2, 4), (5, 15), (16, 10 ** 6)):
    o4[f"herd_{lo}_{hi}"] = summ([k for k in reb if lo <= k["herd"] <= hi], f"any move, {lo}-{hi} moved to the same pool in the step")
# what predicts a harmful move: dimension of a hysteresis margin
g = [k for k in reb if "real_gain_wait" in k]
rg = np.array([k["real_gain_wait"] for k in g])
err = np.array([k["pred_gain_wait"] for k in g]) - rg
o4["rho_overestimate"] = {}
for name, f in (("pred_gain", lambda k: k["pred_gain_wait"]), ("herd", lambda k: k["herd"]), ("qlen_new/cnt_new", lambda k: k["qlen_new"] / max(1, k["cnt_new"])),
                ("delay(transfer)", lambda k: k["delay"]), ("n_prev_moves", lambda k: k["n"]), ("pos/cnt_old", lambda k: k["pos"] / max(1, k["cnt_old"]))):
    v = np.array([f(k) for k in g], float)
    o4["rho_overestimate"][name] = round(spearmanr(v, err)[0], 3)
print("rho(AET over-estimate of the gain, x):", o4["rho_overestimate"])
pg = np.array([k["pred_gain_wait"] for k in g])
for lo, hi in ((0, 2), (2, 5), (5, 10), (10, 30), (30, 1e9)):
    m = (pg >= lo) & (pg < hi)
    if m.sum():
        print(f"  predicted gain {lo:>4}-{hi:<5}s: n={m.sum():6d} realised mean {rg[m].mean():+7.2f}s harmful {(rg[m] < 0).mean():.1%}")
OUT["moves"] = o4

# ================================================================ 5. ex-ante cuts (what the controller can see) and dimension tests
print("\n=== 5. ex-ante: moves by workflow size class; margin and fracture-weight dimensions ===")
cp_req = np.array([W[r["wid"]]["cp"] for r in R.values()])
CPQ = float(np.percentile(cp_req, 75))
o5 = {"cp_q75": round(CPQ, 2)}
big = [k for k in g if W[k["wid"]]["cp"] >= CPQ]
small = [k for k in g if W[k["wid"]]["cp"] < CPQ]
print(f"workflow class 'large' = critical path >= {CPQ:.1f}s (the class holding the whole tail)")
for name, sel in (("large", big), ("small", small)):
    o5[name] = {}
    for kind in ("first", "return", "onward"):
        o5[name][kind] = summ([k for k in sel if k["kind"] == kind], f"{name} workflows, {kind}")
    o5[name]["out_delta_mean"] = round(float(np.mean([k["out_delta"] for k in sel])), 2)
    o5[name]["state_MB_mean"] = round(float(np.mean([k["total"] for k in sel])), 1)
    print(f"    {name}: mean state moved {o5[name]['state_MB_mean']} MB, mean extra first-hop out cost per move {o5[name]['out_delta_mean']}s")
pos_w = np.array([k["real_gain_wait"] > 0 for k in g])
net_ok = np.array([k["real_gain_wait"] - k["out_delta"] > 0 for k in g])
pg = np.array([k["pred_gain_wait"] for k in g])
mu = np.array([EX[k["f"]] for k in g])
cn = np.array([max(1, k["cnt_new"]) for k in g], float)
od = np.array([k["out_delta"] for k in g])
o5["margin_auc_wait_gain_positive"] = {
    "pred_gain_s": round(auc(pg, pos_w), 3), "pred_gain/mu": round(auc(pg / mu, pos_w), 3),
    "pred_gain/(mu/cnt_new)": round(auc(pg / (mu / cn), pos_w), 3), "pred_gain/(mu/sqrt(cnt_new))": round(auc(pg / (mu / np.sqrt(cn)), pos_w), 3)}
print("which normalisation of the predicted gain best separates moves that really helped (AUC):", o5["margin_auc_wait_gain_positive"])
o5["fracture_weight_auc_net_positive"] = {f"lam={lam}": round(auc(pg - lam * od, net_ok), 3) for lam in (0.0, 0.25, 0.5, 0.75, 1.0)}
print("which weight on the downstream transfer best separates net-beneficial moves (AUC):", o5["fracture_weight_auc_net_positive"])
for name, sel in (("large", big), ("small", small)):
    a = np.array([k["pred_gain_wait"] for k in sel]); o = np.array([k["out_delta"] for k in sel])
    y = np.array([k["real_gain_wait"] - k["out_delta"] > 0 for k in sel])
    o5[f"fracture_weight_auc_{name}"] = {f"lam={lam}": round(auc(a - lam * o, y), 3) for lam in (0.0, 0.5, 1.0)}
    print(f"   {name}: {o5[f'fracture_weight_auc_{name}']}")
r_ = np.array([k["real_gain_wait"] for k in g])
x_ = pg / mu
for lo, hi in ((0, 0.25), (0.25, 0.5), (0.5, 1), (1, 2), (2, 1e9)):
    m = (x_ >= lo) & (x_ < hi)
    if m.sum():
        print(f"  predicted gain / mu_f {lo:>4}-{hi:<5}: n={m.sum():6d} realised {r_[m].mean():+6.2f}s harmful(wait) {(r_[m] < 0).mean():.1%}")
OUT["ex_ante"] = o5
json.dump(OUT, open(P.replace(".pkl", "_result.json"), "w"), indent=1, default=str)
print("\nwritten", P.replace(".pkl", "_result.json"))
