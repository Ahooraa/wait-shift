"""Where does a request's time go, and how much of the workflow structure does the controller break? (2026-10-25)

Works on the optional task trace of dfps.sim.Sim(trace=True): for every task of every request that arrived in the measured window
(id, workflow, task, planned node, executing node, first time its inputs were complete and it joined a queue, start of execution, end of
execution, number of relocations) and for every such request its arrival and completion time.

Per request the realised critical path is rebuilt backwards from the last task to finish: at each task the parent that delivered its last
input is the critical parent, and the request's sojourn time splits exactly into
  execution   end - start of the tasks on the path
  wait        start - first enqueue (queueing, cold start, and the transfer of a relocated request)
  transfer    first enqueue - end of the critical parent (the state transfer to the planned node of the child); for a root: first
              enqueue - arrival (input transfer plus any wait for a plan)
Workflow fracturing is measured on EVERY edge u -> t of the traced requests:
  planned edge cost   stt(state, planned node of u, planned node of t)         what the plan assumed
  actual first hop    stt(state, node where u ran, planned node of t)           the parent's output goes to the child's PLANNED node
  child relocated     t ran elsewhere than planned: its inputs travelled again
An edge is 'fractured' when its parent ran away from its plan and the child kept the old plan, or when the child was relocated.
Everything is reported for all requests and for the tail (sojourn >= the 99th percentile), as means per request in seconds, plus
shares. The wait on tasks OFF the realised critical path is the wait a priority rule that knew the workflow could reorder.
"""
from __future__ import annotations

import numpy as np


def summarize(sim):
    tr = sim.trace
    if not tr or not tr["reqs"]:
        return {}
    net = sim.net
    wfs = {w.id: w for w in sim.sc.workflows}
    tasks = {}
    for row in tr["tasks"]:
        tasks.setdefault(row[0], {})[row[2]] = row
    reqs = {r[0]: r for r in tr["reqs"]}
    soj = np.array([r[3] - r[2] for r in reqs.values()])
    p99 = float(np.percentile(soj, 99))
    acc = {"all": [], "tail": []}
    for rid, (_, wid, t_arr, t_done) in reqs.items():
        wf = wfs[wid]
        T = tasks.get(rid, {})
        if len(T) < wf.n:
            continue
        # realised critical path, backwards from the task that finished last
        t = max(T, key=lambda x: T[x][7])
        on_path = set()
        ex = wait_u = wait_m = tra = 0.0
        while True:
            on_path.add(t)
            row = T[t]
            ex += row[7] - row[6]
            w = row[6] - row[5]
            if row[8] > 0:
                wait_m += w
            else:
                wait_u += w
            if not wf.parents[t]:
                tra += row[5] - t_arr
                break
            best, bp = -1.0, None
            for u in wf.parents[t]:
                arr = T[u][7] + net.stt(wf.ss[(u, t)], T[u][4], T[t][3])
                if arr > best:
                    best, bp = arr, u
            tra += row[5] - T[bp][7]
            t = bp
        # fracturing and locality over all edges; wait split by critical / non-critical
        n_e = n_frac = n_loc_plan = n_loc_final = 0
        extra = 0.0
        for (u, v), size in wf.ss.items():
            n_e += 1
            pu, pv, au = T[u][3], T[v][3], T[u][4]
            n_loc_plan += int(pu == pv)
            n_loc_final += int(au == T[v][4])
            if au != pu or T[v][4] != pv:
                n_frac += 1
            extra += net.stt(size, au, pv) - net.stt(size, pu, pv)
        wait_all = sum(T[x][6] - T[x][5] for x in T)
        wait_crit = sum(T[x][6] - T[x][5] for x in on_path)
        joins = [max(T[u][7] + net.stt(wf.ss[(u, x)], T[u][4], T[x][3]) for u in wf.parents[x]) -
                 min(T[u][7] + net.stt(wf.ss[(u, x)], T[u][4], T[x][3]) for u in wf.parents[x]) for x in T if len(wf.parents[x]) > 1]
        rec = dict(soj=t_done - t_arr, exec=ex, wait_unmoved=wait_u, wait_moved=wait_m, transfer=tra, edges=n_e,
                   fractured=n_frac / max(n_e, 1), local_plan=n_loc_plan / max(n_e, 1), local_final=n_loc_final / max(n_e, 1),
                   extra_first_hop=extra, moved_tasks=sum(1 for x in T if T[x][8] > 0) / wf.n, moves=sum(T[x][8] for x in T) / wf.n,
                   pingpong=sum(1 for x in T if T[x][8] >= 2) / wf.n,       # share of tasks moved MORE THAN ONCE (2026-10-25)
                   wait_off_path=(wait_all - wait_crit), wait_on_path=wait_crit, join_gap=float(np.mean(joins)) if joins else 0.0,
                   tasks=wf.n)
        acc["all"].append(rec)
        if rec["soj"] >= p99:
            acc["tail"].append(rec)
    out = {"p99": p99, "n_requests": len(acc["all"]), "n_tail": len(acc["tail"])}
    for name, rows in acc.items():
        if not rows:
            continue
        for k in rows[0]:
            out[f"{name}_{k}"] = float(np.mean([r[k] for r in rows]))
    return out


def bounds(sim):
    """First-order ceilings on what two workflow-aware fixes could save, replayed on the trace of a finished run (2026-10-25).

    The sojourn of every traced request is recomputed forward through its DAG with one change at a time:
      A  slack-ordering ceiling   a task on the realised critical path that waited at a (node, function) pool may start at the
                                  moment a task of ANOTHER request started there during its wait, if that task had slack >= the
                                  waiting task's execution time (it could have been delayed behind it without delaying its own
                                  request). Slack = how long a task's end can slip before its request's completion moves, from the
                                  realised times. 'A_unmoved' uses only tasks that were never relocated (exact queue), 'A_all'
                                  also relocated ones (their wait includes the relocation, so this overstates).
      B1 co-location ceiling      every state transfer on the realised critical path costs 0.
      B2 fracture ceiling         only the critical-path transfers whose parent ran away from its plan or whose child was relocated
                                  cost 0 (a perfect re-binding of descendants).
    Savings propagate through the DAG (a second path may become critical), but the effect of freed slots on other requests is
    ignored, and only tasks of requests that arrived in the measured window are candidates, so the ceilings are first-order.
    Returns P99 and mean sojourn for the baseline replay and for each ceiling."""
    import bisect
    tr = sim.trace
    if not tr or not tr["reqs"]:
        return {}
    net = sim.net
    wfs = {w.id: w for w in sim.sc.workflows}
    tasks = {}
    for row in tr["tasks"]:
        tasks.setdefault(row[0], {})[row[2]] = row
    reqs = {r[0]: r for r in tr["reqs"]}

    def stt(wf, u, t, node_u, node_t):
        return net.stt(wf.ss[(u, t)], node_u, node_t)

    info = {}                                            # per request: tasks, slack per task, critical chain
    pool = {}                                            # (node, function) -> [(start, slack, exec, rid, task, moved)]
    for rid, (_, wid, t_arr, t_done) in reqs.items():
        wf, T = wfs[wid], tasks.get(rid, {})
        if len(T) < wf.n:
            continue
        end = {t: T[t][7] for t in T}
        edge_slack = {}
        for t in T:
            for u in wf.parents[t]:
                edge_slack[(u, t)] = T[t][5] - (end[u] + stt(wf, u, t, T[u][4], T[t][3]))
        slack = {}
        for t in sorted(T, reverse=True):
            slack[t] = (t_done - end[t]) if not wf.children[t] else min(edge_slack[(t, c)] + slack[c] for c in wf.children[t])
        t = max(T, key=lambda x: end[x])
        chain = [t]
        while wf.parents[t]:
            t = min(wf.parents[t], key=lambda u: edge_slack[(u, t)])
            chain.append(t)
        info[rid] = (wf, T, slack, set(chain))
        for t, row in T.items():
            pool.setdefault((row[4], wf.ft[t]), []).append((row[6], slack[t], row[7] - row[6], rid, t, row[8] > 0))
    for lst in pool.values():
        lst.sort()
    starts = {key: [x[0] for x in lst] for key, lst in pool.items()}

    def replay(rid, saved=None, zero_edges=None):
        wf, T, slack, chain = info[rid]
        t_arr = reqs[rid][2]
        new_end = {}
        for t in range(wf.n):
            row = T[t]
            if wf.parents[t]:
                real = max(T[u][7] + stt(wf, u, t, T[u][4], row[3]) for u in wf.parents[t])
                gap = max(0.0, row[5] - real)                # delay between the last input and the first enqueue (a reroute before the first enqueue)
                first = max(new_end[u] + (0.0 if zero_edges and (u, t) in zero_edges else stt(wf, u, t, T[u][4], row[3])) for u in wf.parents[t]) + gap
            else:
                first = row[5]
            wait = max(0.0, (row[6] - row[5]) - (saved.get(t, 0.0) if saved else 0.0))
            new_end[t] = first + wait + (row[7] - row[6])
        return max(new_end.values()) - t_arr

    out = {}
    base, a_un, a_all, b1, b2 = [], [], [], [], []
    for rid in info:
        wf, T, slack, chain = info[rid]
        base.append(replay(rid))
        for tag, acc in (("unmoved", a_un), ("all", a_all)):
            saved = {}
            for t in chain:
                row = T[t]
                if row[6] - row[5] <= 1e-9 or (tag == "unmoved" and row[8] > 0):
                    continue
                key, ex = (row[4], wf.ft[t]), row[7] - row[6]
                lst, st = pool.get(key, []), starts.get(key, [])
                i = bisect.bisect_left(st, row[5])
                best = None
                while i < len(lst) and lst[i][0] < row[6]:
                    s, sl, exu, r2, t2, mv = lst[i]
                    if r2 != rid and sl >= ex and (tag == "all" or not mv):
                        best = s
                        break
                    i += 1
                if best is not None:
                    saved[t] = row[6] - best
            acc.append(replay(rid, saved=saved))
        crit_edges = {(u, c) for c in chain for u in wf.parents[c] if u in chain}
        fr = {(u, t) for (u, t) in crit_edges if T[u][4] != T[u][3] or T[t][8] > 0}
        b1.append(replay(rid, zero_edges=crit_edges))
        b2.append(replay(rid, zero_edges=fr))
    for name, arr in (("base", base), ("A_unmoved", a_un), ("A_all", a_all), ("B1_colocation", b1), ("B2_fracture", b2)):
        a = np.array(arr)
        out[name + "_p99"] = float(np.percentile(a, 99))
        out[name + "_mean"] = float(a.mean())
    out["n_requests"] = len(base)
    out["replay_error"] = float(np.max(np.abs(np.array(base) - np.array([reqs[r][3] - reqs[r][2] for r in info]))))
    return out
