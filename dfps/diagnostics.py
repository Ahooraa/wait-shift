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
