"""Container sizes from workflow and task profiles (2026-11-02).

DFPS (Sec. 3.1, p. 4) says each container "requires a fixed, specific amount of CPU and memory resources" and bounds a node by
`ecc_k` containers; it never says all functions are the same size. The first versions of this simulator read that as one slot
per container for every function. Real functions differ, so the capacity model is now weighted: each function f has a container
weight `w_f` (`Scenario.fw`) and node k holds a set of containers whose weights sum to at most `ecc_k`. This module derives
`w_f` from the profiles that the workflow sources actually carry:

  * Alibaba cluster-trace-v2018 jobs: every task has `plan_mem` (trace-normalised memory request, per instance) and `plan_cpu`
    (100 = one core). Re-extracted by experiments/extract_alibaba_profiles.py (same jobs, same order as the DAG-only file).
  * SeBS-Flow benchmarks: one `memory` setting (MB) per workflow in its config.json -- a workflow-level profile; all of its
    functions get it. The paper publishes nothing finer.
  * The DFPS Fig. 1 workflow has no published profile: it gets the reference size.

Capacity is memory. A warm container holds its memory whether it runs or not, so memory is what a node's container budget buys;
CPU is only used while a task runs and is a contention matter (problem-scope.md S2, "Compute resource contention"), not a
capacity one. `plan_cpu` is carried through for that later extension but does not enter `w_f`.

Scales. The two sources are in different units (Alibaba: a normalised fraction of an unspecified machine; SeBS: MB), so each is
divided by its own median before the two are mixed ("relative demand", 1 = the typical container of that source). That is an
assumption, not a measurement; it is recorded in `Scenario.meta['fw_source']`.

From tasks to functions. A function's container must hold any task that runs on it, so with `agg="max"` (default) w_f is the
largest relative demand over the tasks mapped to it. The pool mapping (A-16) assigns tasks to function types at random, so a
type's tasks are unrelated; "max" is then the conservative reading, "mean"/"median" the optimistic one. Weights are clipped to
[lo, hi] (a handful of Alibaba tasks ask for 8x the median) and divided by their mean over the functions in use, so `ecc_k`
keeps meaning "containers of the average size" and a profiled scenario is comparable in total capacity to the uniform one.
"""
from __future__ import annotations

import json
import os

import numpy as np

from .sebsflow import BASE as _SEBS_BASE, CONFIG as _SEBS_CONFIG

LO, HI = 0.25, 4.0                      # clip on relative demand


def sebs_memory_mb():
    """{benchmark: memory setting in MB} from the SeBS-Flow config.json files that sebsflow.CONFIG uses."""
    out = {}
    for b in _SEBS_CONFIG:
        out[b] = float(json.load(open(os.path.join(_SEBS_BASE, b, "config.json"), encoding="utf-8"))["memory"])
    return out


def load_profiles(path, jobs=None):
    """{job: (plan_cpu list, plan_mem list, edges)} from data/alibaba_dags_lt60s_profiles.json; only `jobs` if given."""
    want = None if jobs is None else set(jobs)
    out = {}
    for d in json.load(open(path)):
        if want is None or d["job"] in want:
            out[d["job"]] = (d["plan_cpu"], d["plan_mem"], tuple(sorted(map(tuple, d["edges"]))))
    return out


def _shape(n, edges):
    return (int(n), tuple(sorted(map(tuple, edges))))


def replay_jobs(sc, alibaba_dags):
    """Exact job order of an older scenario: rebuild it from its own seed and parameters (the build is deterministic), check the
    rebuilt workflows are the pickled ones (task count, function types, edges), and return the rebuilt scenario's
    meta['workflow_jobs']. `alibaba_dags` is the DAG list the scenario was built from (data/alibaba_dags_lt60s.json)."""
    from .traces import workflow_mix
    from .workload import build_scenario
    m = sc.meta
    mix = workflow_mix(int(m["seed"]), int(m["nw"]), alibaba_dags)
    re = build_scenario(int(m["seed"]), "uniform", 1.0, ne=int(m["ne"]), n_workflows=len(mix), pool_size=int(m["pool_size"]),
                        duration_s=float(m["duration_s"]), dags=mix)
    ok = len(re.workflows) == len(sc.workflows) and all(
        a.n == b.n and a.ft == b.ft and a.parents == b.parents for a, b in zip(re.workflows, sc.workflows))
    return re.meta["workflow_jobs"] if ok else None


def workflow_jobs(sc, profiles, alibaba_dags=None):
    """The job behind each workflow of `sc`, in workflow order. build_scenario draws the workflows as a permutation of the mix
    (`rng.choice(len(pool), nw, replace=False)`), so meta['workflows'] -- the mix order -- is NOT the workflow order. Order of
    preference: meta['workflow_jobs'] (scenarios built after 2026-11-02); an exact replay of the build (`alibaba_dags` given);
    DAG-shape matching (task count + edge set), where two jobs sharing a shape (two identical chains) are told apart only by
    taking the first unused one -- `ambiguous` counts the workflows where that guess was needed."""
    if sc.meta.get("workflow_jobs"):
        return list(sc.meta["workflow_jobs"]), 0
    if alibaba_dags is not None:
        jobs = replay_jobs(sc, alibaba_dags)
        if jobs is not None:
            return list(jobs), 0
    from .sebsflow import all_named_dags
    named = {d["job"]: _shape(d["n"], d["edges"]) for d in all_named_dags()}
    shape_of = {}
    for j in sc.meta["workflows"]:
        shape_of[j] = named[j] if j in named else _shape(len(profiles[j][1]), profiles[j][2])
    used, out, amb = set(), [], 0
    for w in sc.workflows:
        sh = _shape(w.n, [(u, v) for v in range(w.n) for u in w.parents[v]])
        cand = [j for j in sc.meta["workflows"] if shape_of[j] == sh]
        if not cand:
            raise ValueError("no job in meta['workflows'] has this workflow's DAG shape")
        free = [j for j in cand if j not in used]
        amb += len(cand) > 1
        j = (free or cand)[0]
        used.add(j)
        out.append(j)
    return out, amb


ALIBABA_MEDIAN_PLAN_MEM = 0.30         # median plan_mem over all 6,298,698 tasks of the 1,459,783 jobs kept (extract_alibaba_profiles)


def reference_demands(profiles=None):
    """Median of each source, the unit of 'relative demand'. A fixed constant for Alibaba (measured once over the whole kept
    trace), not the median of whichever jobs a scenario happens to hold, so two scenarios use the same scale."""
    sebs = sebs_memory_mb()
    return dict(alibaba=ALIBABA_MEDIAN_PLAN_MEM, sebs=float(np.median(list(sebs.values()))))


def task_demands(job, n, profiles, ref, sebs=None):
    """Relative memory demand of each task of workflow `job` (length n), 1 = the typical container of its source."""
    if job in profiles:
        pm = profiles[job][1]
        return np.array([ref["alibaba"] if m is None else m for m in pm], dtype=float) / ref["alibaba"]
    if isinstance(job, str) and job.startswith("sebsflow-"):
        mb = (sebs or sebs_memory_mb())[job[len("sebsflow-"):]]
        return np.full(n, mb / ref["sebs"])
    return np.ones(n)                                                   # DFPS Fig. 1 and anything without a profile


def container_weights(sc, profiles, agg="mean", lo=LO, hi=HI, alibaba_dags=None):
    """Per-function container weight w_f (mean 1 over the functions in use) for scenario `sc`. Returns (fw, detail).
    agg="mean" (default) is the average relative demand of the tasks mapped to the function; "max" gives the container that fits
    its largest task, but with the random task-to-function pool (A-16) it saturates: on a development scenario 14 of 30 function
    types took the weight of the one big SeBS-Flow workflow, so "mean" keeps the spread the profiles actually have."""
    jobs, amb = workflow_jobs(sc, profiles, alibaba_dags)
    ref = reference_demands(profiles)
    sebs = sebs_memory_mb()
    F = len(sc.functions)
    per_f = [[] for _ in range(F)]
    for w, job in zip(sc.workflows, jobs):
        dem = np.clip(task_demands(job, w.n, profiles, ref, sebs), lo, hi)
        for t in range(w.n):
            per_f[w.ft[t]].append(float(dem[t]))
    red = dict(max=np.max, mean=np.mean, median=np.median)[agg]
    used = np.array([bool(x) for x in per_f])
    raw = np.array([float(red(x)) if x else 1.0 for x in per_f])
    fw = raw / raw[used].mean()
    return fw, dict(agg=agg, ref=ref, clip=(lo, hi), ambiguous_jobs=int(amb), n_used=int(used.sum()), raw_min=float(raw[used].min()),
                    raw_max=float(raw[used].max()), fw_min=float(fw[used].min()), fw_max=float(fw[used].max()),
                    fw_cv=float(fw[used].std() / fw[used].mean()))


def with_profiled_weights(sc, profiles, **kw):
    """The same scenario with sc.fw set from the profiles (the scenario object is modified and returned)."""
    fw, detail = container_weights(sc, profiles, **kw)
    sc.fw = fw
    sc.meta = dict(sc.meta, fw_source="profiles", fw_detail=detail)
    return sc
