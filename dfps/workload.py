"""Scenario construction: workflows, functions, edge nodes, Poisson arrivals (p.9 Sec.5.1, Table 2).

* Alibaba trace (OPEN-2): `load_alibaba_batch_task` parses the 2018 batch_task table. The trace is NOT available on
  this machine, so `synthetic_alibaba_like` (clearly labelled, meta['dag_source']) is used until the file is supplied.
* Table-2 values are only RANGES; the distribution inside a range is A-01 (uniform).
* Arrivals follow the text exactly (Q-7): per-application Poisson process with the stated mean inter-arrival
  (Uniform: 200-700 ms; Pareto: ~20% of apps 50-100 ms, others 2-4 s); the scaling factor multiplies the arrival RATE."""
from __future__ import annotations

import re

import numpy as np

from .constants import PAPER
from .model import Function, Scenario, Workflow
from .network import transit_stub

_TASK = re.compile(r"^([A-Za-z]+)(\d+)((?:_\d+)*)$")


def load_alibaba_batch_task(path, max_exec_s=None, min_tasks=2, max_jobs=None, with_profile=False):
    """Parse cluster-trace-v2018 `batch_task.csv` (9 columns, no header, times in seconds; verified on the real file):
    task_name, instance_num, job_name, task_type, status, start_time, end_time, plan_cpu, plan_mem.
    DAG dependencies are encoded in task names ("M5_3_4" = task 5 depends on tasks 3 and 4; the letter is irrelevant).
    Keeps jobs whose tasks are all DAG-named and Terminated with start_time > 0, that form a valid acyclic DAG of at least
    `min_tasks` tasks, and whose execution time (A-29: max(end_time) - min(start_time), seconds) is under `max_exec_s`
    (the paper: applications with short execution times, under one minute, p.9). Vectorised: ~15M rows, ~1 minute.

    with_profile (2026-11-02): also return each task's resource request, in the same topological order as `edges`'
    indices: `plan_cpu` (100 = one core) and `plan_mem` (trace-normalised memory, 0..1), per instance of the task; None where
    the trace leaves the field empty. Selection and order of the jobs are identical with and without it."""
    import pandas as pd

    max_exec_s = PAPER["alibaba_job_max_execution_s"]["value"] if max_exec_s is None else max_exec_s
    cols = [0, 2, 4, 5, 6] + ([7, 8] if with_profile else [])
    names = ["task_name", "job_name", "status", "start", "end"] + (["plan_cpu", "plan_mem"] if with_profile else [])
    df = pd.read_csv(path, header=None, usecols=cols, names=names, dtype={"task_name": str, "job_name": str, "status": str})
    df["bad"] = (df["status"] != "Terminated") | (df["start"] <= 0) | ~df["task_name"].str.match(r"^[A-Za-z]+\d+(?:_\d+)*$")
    g = df.groupby("job_name")
    stats = g.agg(bad=("bad", "max"), n=("bad", "size"), t0=("start", "min"), t1=("end", "max"))
    keep = stats[(~stats["bad"]) & (stats["n"] >= min_tasks) & ((stats["t1"] - stats["t0"]) < max_exec_s)]
    sub = df[df["job_name"].isin(set(keep.index))]
    out = []
    for job, grp in sub.groupby("job_name", sort=False):
        ids, deps, ok = [], {}, True
        prof = {}
        pc = grp["plan_cpu"].tolist() if with_profile else None
        pm = grp["plan_mem"].tolist() if with_profile else None
        for i, name in enumerate(grp["task_name"]):
            m = _TASK.match(name)
            tid = int(m.group(2))
            ids.append(tid)
            deps[tid] = [int(x) for x in m.group(3).split("_") if x]
            if with_profile:
                prof[tid] = (None if pc[i] != pc[i] else float(pc[i]), None if pm[i] != pm[i] else float(pm[i]))
        if len(set(ids)) != len(ids) or any(d not in deps for v in deps.values() for d in v):
            continue
        order, seen = [], set()
        while len(order) < len(ids):  # topological order; reject cycles
            nxt = [t for t in ids if t not in seen and all(d in seen for d in deps[t])]
            if not nxt:
                ok = False
                break
            order += nxt
            seen.update(nxt)
        if not ok:
            continue
        idx = {t: i for i, t in enumerate(order)}
        edges = [(idx[d], idx[t]) for t in order for d in deps[t]]
        rec = dict(job=job, n=len(order), edges=edges, span=float(keep.loc[job, "t1"] - keep.loc[job, "t0"]))
        if with_profile:
            rec["plan_cpu"] = [prof[t][0] for t in order]
            rec["plan_mem"] = [prof[t][1] for t in order]
        out.append(rec)
        if max_jobs and len(out) >= max_jobs:
            break
    return out


def synthetic_alibaba_like(rng, count, min_tasks=3, max_tasks=14):
    """SYNTHETIC stand-in (OPEN-2): random layered DAGs. NOT the paper's data."""
    out = []
    for i in range(count):
        n = int(rng.integers(min_tasks, max_tasks + 1))
        layers = max(2, int(rng.integers(2, max(3, n // 2 + 1))))
        layer_of = np.sort(rng.integers(0, layers, n))
        layer_of[0] = 0
        edges = set()
        for v in range(n):
            if layer_of[v] == 0:
                continue
            prev = [u for u in range(n) if layer_of[u] < layer_of[v]]
            for u in rng.choice(prev, size=int(rng.integers(1, min(3, len(prev)) + 1)), replace=False):
                edges.add((int(u), v))
        out.append(dict(job=f"synthetic-{i}", n=n, edges=sorted(edges), span=float("nan")))
    return out


def arrival_means(rng, n_apps, kind):
    """Mean inter-arrival time (seconds) per application: Uniform or Pareto workload (p.9)."""
    if kind == "uniform":
        u = PAPER["uniform_workload_mean_ms"]
        return rng.uniform(u["min"], u["max"], n_apps) / 1000.0
    if kind == "pareto":
        p = PAPER["pareto_workload"]
        n_high = int(round(p["high_rate_fraction"] * n_apps))
        high = set(rng.choice(n_apps, n_high, replace=False).tolist())
        return np.array([rng.uniform(p["high_mean_ms_min"], p["high_mean_ms_max"]) / 1000.0 if a in high
                         else rng.uniform(p["low_mean_s_min"], p["low_mean_s_max"]) for a in range(n_apps)])
    raise ValueError(kind)


def build_scenario(seed, kind="uniform", scale=1.0, ne=None, n_workflows=None, pool_size=30, duration_s=300.0,
                   dags=None, topology=None, synthetic_max_tasks=14, function_mapping="pool"):
    """One workload (= one seed). `dags`: list of DAG dicts (Alibaba parser output); None -> synthetic stand-in.
    function_mapping: "pool" (A-16 default: every task draws a function from a shared pool of `pool_size`) or "distinct"
    (calibration variant 2026-10-17: every task of every workflow is its own function type; pool_size is then ignored)."""
    rng = np.random.default_rng(seed)
    ne = PAPER["number_of_edge_nodes"]["default"] if ne is None else ne
    nw = PAPER["number_of_workflows"]["default"] if n_workflows is None else n_workflows
    net = topology if topology is not None else transit_stub(ne, rng)
    fr, cs, st = PAPER["function_runtime_s"], PAPER["cold_start_delay_s"], PAPER["intermediate_state_mb"]
    cap, sto = PAPER["edge_node_function_capacity"], PAPER["edge_node_storage_capacity_gb"]
    ecc = rng.integers(cap["min"], cap["max"] + 1, ne)                     # A-01 uniform integer in 5..25
    esc = rng.uniform(sto["min"], sto["max"], ne) * 1024.0                 # MB
    new_fn = lambda l: Function(l, float(rng.uniform(fr["min"], fr["max"])), float(rng.uniform(cs["min"], cs["max"])))  # noqa: E731
    functions = [new_fn(l) for l in range(pool_size)] if function_mapping == "pool" else []
    source = "alibaba-2018 batch_task (real)" if dags is not None else "SYNTHETIC-alibaba-like (OPEN-2)"
    pool = dags if dags is not None else synthetic_alibaba_like(rng, max(nw * 4, 60), max_tasks=synthetic_max_tasks)
    picks = rng.choice(len(pool), nw, replace=False)
    workflows, picked_jobs = [], []
    for wid, p in enumerate(picks):
        picked_jobs.append(pool[int(p)].get("job"))
        d = pool[int(p)]
        d = dict(d, edges=[tuple(e) for e in d["edges"]])
        if function_mapping == "pool":
            ft = rng.integers(0, pool_size, d["n"]).tolist()               # A-16 global pool, uniform
        else:
            ft = list(range(len(functions), len(functions) + d["n"]))
            functions += [new_fn(l) for l in ft]
        ss = {e: float(rng.uniform(st["min"], st["max"])) for e in d["edges"]}
        workflows.append(Workflow.from_edges(wid, d["n"], d["edges"], ft, ss, float(rng.uniform(st["min"], st["max"]))))
    means = arrival_means(rng, nw, kind) / scale                           # scale multiplies the arrival rate
    arrivals = []
    for wid in range(nw):
        t = rng.exponential(means[wid])
        while t < duration_s:
            arrivals.append((float(t), wid, int(rng.integers(0, ne))))     # A-20 origin uniform
            t += rng.exponential(means[wid])
    arrivals.sort()
    total_rate = float(np.sum(1.0 / means))
    meta = dict(synthetic_max_tasks=(None if dags is not None else synthetic_max_tasks),
                mean_tasks=float(np.mean([w.n for w in workflows])), seed=seed, kind=kind, scale=scale, ne=ne, nw=nw, pool_size=len(functions), function_mapping=function_mapping, duration_s=duration_s,
                dag_source=source, workflow_jobs=picked_jobs, per_app_rate=(1.0 / means).tolist(), total_rate_per_s=total_rate,
                rate_within_table2=bool(PAPER["incoming_request_rate_per_s"]["min"] <= total_rate
                                        <= PAPER["incoming_request_rate_per_s"]["max"]))
    return Scenario(functions, workflows, net, ecc, esc, arrivals, meta)
