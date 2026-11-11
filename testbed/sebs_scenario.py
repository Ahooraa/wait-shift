"""The SeBS-Flow-only workload with measured per-function data (testbed/DESIGN.md, DEV-T1 and DEV-T2).

    sc, exec_sampler = build(seed, rho=0.7, ne=20, duration_s=300.0)
    Sim(sc, X, exec_sampler=exec_sampler, ...)        # or LiveSim / LiveOnDemandSim

Everything comes from SeBS-Flow: the six applications at the paper's Table 4 configuration (dfps/sebsflow.py, whose task counts per
function match the measured invocations exactly), and the measured table testbed/sebs_profiles.json derived from the replication package
(testbed/derive_sebs_profile.py): per function the quantiles of the execution duration, the cold-start initialisation time, the bytes
written to storage and the memory used. Nothing is drawn from the DFPS paper's ranges, except what SeBS-Flow does not contain: the edge
network (80-node paper topology generator with 20 nodes by default, 50 MB/s links), node capacities (5-25 containers, 10-30 GB) and the
Poisson arrival process.

Rules, so that nothing is hidden:
  * function types: one per (application, function name); the tasks of a function share its type (25 types).
  * duration of a task: drawn by inverse transform from the measured quantiles of its function (`exec_sampler`); the mean is Function.exec_time.
  * cold start: the median measured initialisation time (Function.cold_start). This is the runtime initialisation on the cloud platform;
    it is much shorter than an image pull on an edge node and than the DFPS paper's 2-10 s range (that range is a later sensitivity run).
  * state size of an edge u -> v: the median bytes the producer u wrote to storage, divided among its successors; the request's input state:
    the median bytes its root function read. Where SeBS-Flow measured none the size is `MIN_STATE_MB` (a payload of a few kB).
  * capacity model: CAP-U (one slot per container). weights="memory" gives CAP-W2: weights from the measured memory used, normalised
    to mean 1 and clipped to [0.25, 4]; the measured memory is the median over the function's invocations.
  * arrivals: Poisson, the applications drawn with `mix` ("uniform": equal request shares, "equal_load": equal shares of the work), the rate
    chosen so that the offered work (sum of mean durations) is `rho` of the total container capacity; the origin node is uniform.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from dfps.model import Function, Scenario, Workflow
from dfps.network import transit_stub
from dfps.sebsflow import CONFIG, sebsflow_dag

PROFILES = Path(__file__).resolve().parent / "sebs_profiles.json"
MIN_STATE_MB = 0.001
QUANTILES = np.linspace(0.0, 1.0, 101)
BENCHMARKS = list(CONFIG)                    # the six applications, in dfps/sebsflow.py order


def load_profiles(path=PROFILES):
    return json.loads(Path(path).read_text())


def build(seed, rho=0.7, ne=20, duration_s=300.0, mix="uniform", weights="uniform", profiles=None, bw=None):
    prof = profiles or load_profiles()
    rng = np.random.default_rng(seed)
    functions, fid, quant, names = [], {}, [], []
    for b in BENCHMARKS:
        for name, p in prof["workflows"][b]["functions"].items():
            fid[(b, name)] = len(functions)
            functions.append(Function(len(functions), float(p["duration_s_mean"]), float(p["cold_init_s_median"])))
            quant.append(np.asarray(p["duration_s_q"], dtype=float))
            names.append(f"{b}/{name}")
    workflows, work = [], []
    for wid, b in enumerate(BENCHMARKS):
        dag = sebsflow_dag(b)
        fns = prof["workflows"][b]["functions"]
        ft = [fid[(b, n)] for n in dag["names"]]
        children = {}
        for u, v in dag["edges"]:
            children.setdefault(u, []).append(v)
        ss = {(u, v): max(MIN_STATE_MB, fns[dag["names"][u]]["blob_upload_bytes_median"] / 1e6 / len(children[u])) for u, v in dag["edges"]}
        roots = [t for t in range(dag["n"]) if not any(v == t for _, v in dag["edges"])]
        inp = max(MIN_STATE_MB, max(fns[dag["names"][t]]["blob_download_bytes_median"] for t in roots) / 1e6)
        workflows.append(Workflow.from_edges(wid, dag["n"], dag["edges"], ft, ss, inp))
        work.append(float(sum(functions[f].exec_time for f in ft)))
    net = transit_stub(ne, rng) if bw is None else transit_stub(ne, rng)
    if bw is not None:
        net.bw = float(bw)
    ecc = rng.integers(5, 26, ne)                                          # DFPS Table 2: 5-25 containers per node
    esc = rng.uniform(10, 30, ne) * 1024.0                                 # MB
    work = np.asarray(work)
    p = np.full(len(BENCHMARKS), 1.0 / len(BENCHMARKS)) if mix == "uniform" else (1.0 / work) / np.sum(1.0 / work)
    if mix not in ("uniform", "equal_load"):
        raise ValueError("mix is 'uniform' or 'equal_load'")
    lam = float(rho * ecc.sum() / np.sum(p * work))                        # requests per second
    arrivals, t = [], float(rng.exponential(1.0 / lam))
    while t < duration_s:
        arrivals.append((t, int(rng.choice(len(BENCHMARKS), p=p)), int(rng.integers(0, ne))))
        t += float(rng.exponential(1.0 / lam))
    meta = dict(seed=seed, workload="sebs-flow only, measured", capacity_model="CAP-U", rho=rho, mix=mix, rate_per_s=lam, ne=ne,
                n_arrivals=len(arrivals), mean_tasks=float(np.mean([w.n for w in workflows])), work_per_request_s=work.tolist(),
                workflows=BENCHMARKS, function_names=names, dag_source="SeBS-Flow Table 4 (dfps/sebsflow.py)",
                profile_source=prof["source"], cold_start_model="measured SeBS-Flow initialisation (AWS 2024)", duration_s=duration_s)
    sc = Scenario(functions, workflows, net, ecc, esc, arrivals, meta)
    if weights == "memory":
        mem = np.array([float(prof["workflows"][b]["functions"][n.split("/")[1]]["mem_used_mb_median"]) for n, b in
                        ((x, x.split("/")[0]) for x in names)])
        w = np.clip(mem / mem.mean(), 0.25, 4.0)
        sc.fw = w / w.mean()
        sc.meta["capacity_model"] = "CAP-W2"
    elif weights != "uniform":
        raise ValueError("weights is 'uniform' or 'memory'")

    def exec_sampler(f, r):
        return float(np.interp(r.random(), QUANTILES, quant[int(f)]))
    return sc, exec_sampler
