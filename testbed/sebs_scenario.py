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
  * duration of a task: drawn by inverse transform from the measured quantiles of its function, with common random numbers (CrnSampler:
    the same task of the same request gets the same duration under every controller); the mean is Function.exec_time.
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


_M32, _M64, _M128 = 0xFFFFFFFF, (1 << 64) - 1, (1 << 128) - 1
_PCG_MULT = 47026247687942121848144207491837523525


def _consts():
    """SeedSequence's hash constants do not depend on the data, only on the position in the sequence, so they are laid out once."""
    hc, first = 0x43B0D7E5, []
    for _ in range(4):                                               # the four entropy words
        first.append((hc, (hc * 0x931E8875) & _M32))
        hc = (hc * 0x931E8875) & _M32
    mixing = []
    for i in range(4):
        for j in range(4):
            if i != j:
                mixing.append((i, j, hc, (hc * 0x931E8875) & _M32))
                hc = (hc * 0x931E8875) & _M32
    hc, gen = 0x8B51F9DD, []
    for i in range(8):
        n = (hc * 0x58F38DED) & _M32
        gen.append((i & 3, hc, n))
        hc = n
    return first, mixing, gen


_FIRST, _MIXING, _GEN = _consts()


def crn_uniform(seed, req, task):
    """`np.random.default_rng([seed, req, task]).random()` without building the generator (15 Nov 2026: that call took about 100 us, one per task).
    The same arithmetic as numpy's SeedSequence (pool of four 32-bit words, mixing and state generation) and PCG64's seeding and first output, in Python integers;
    `tests/test_crn_uniform.py` checks it against numpy bit for bit. Keys that need more than one 32-bit word each go through numpy."""
    if not (0 <= seed <= _M32 and 0 <= req <= _M32 and 0 <= task <= _M32):
        return float(np.random.default_rng([seed, req, task]).random())
    pool = []
    for v, (a, b) in zip((seed, req, task, 0), _FIRST):              # entropy words, padded with a zero up to the pool size
        v = ((v ^ a) * b) & _M32
        pool.append(v ^ (v >> 16))
    for i, j, a, b in _MIXING:                                       # mix every word into every other
        h = ((pool[i] ^ a) * b) & _M32
        h ^= h >> 16
        r = (0xCA01F9DD * pool[j] - 0x4973F715 * h) & _M32
        pool[j] = r ^ (r >> 16)
    st = []
    for i, a, b in _GEN:                                             # eight 32-bit words of state, cycling through the pool
        v = ((pool[i] ^ a) * b) & _M32
        st.append(v ^ (v >> 16))
    initstate = (st[0] | (st[1] << 32)) << 64 | (st[2] | (st[3] << 32))
    inc = ((((st[4] | (st[5] << 32)) << 64 | (st[6] | (st[7] << 32))) << 1) | 1) & _M128
    state = ((inc + initstate) * _PCG_MULT + inc) & _M128            # PCG64 seeding: state = 0; step; state += initstate; step
    state = (state * _PCG_MULT + inc) & _M128                        # the step of the first output
    x = (state >> 64) ^ (state & _M64)                               # XSL-RR
    rot = state >> 122
    return ((((x >> rot) | (x << ((-rot) & 63))) & _M64) >> 11) * (1.0 / 9007199254740992.0)


class CrnSampler:
    """Task durations from the measured quantiles with COMMON RANDOM NUMBERS: `for_run(function, request id, task)` draws from the seed and the
    run's identity, so every controller that runs the scenario sees the same duration for the same task of the same request (paired
    comparisons need this; with one shared random stream the duration a task gets depends on the order in which a method starts its tasks).
    Called as sampler(function, rng) it behaves like any other exec_sampler (shared stream)."""

    def __init__(self, quantiles, seed):
        self.q, self.seed = quantiles, int(seed)

    def for_run(self, f, req_id, task):
        u = crn_uniform(self.seed, int(req_id), int(task))
        return float(np.interp(u, QUANTILES, self.q[int(f)]))

    def __call__(self, f, rng):
        return float(np.interp(rng.random(), QUANTILES, self.q[int(f)]))


def load_profiles(path=PROFILES):
    return json.loads(Path(path).read_text())


PTM_RANGE = (1.5, 2.5)                       # Azure arrivals: peak-to-mean of the per-minute series over the run (a bursty but not collapsing segment)
PEAK_TASKS_CAP = 300.0                       # Azure arrivals: the most tasks per second any minute may offer (the hub sustains about 350)


def azure_series(seed, n_bins, span="dev", ptm_range=PTM_RANGE, tries=4000):
    """A per-minute request-rate shape from the Azure 2019 trace (family F1 of dfps/traces.py, the top 200 functions by development-span volume, per-minute counts).
    Rule, fixed before any run (13 Nov 2026): a (function, start minute) pair is drawn at random, by the seed, from the development span, and kept if the peak-to-mean of
    its `n_bins` consecutive minutes lies in `ptm_range` (the first accepted draw; the median 16-minute segment of the trace is almost steady, peak-to-mean 1.2, so an
    unrestricted draw would test nothing). The same seed gives the same segment. Returns (counts[n_bins], row, offset, peak_to_mean)."""
    from dfps.traces import load_counts
    counts = load_counts("F1", span).astype(float)
    rng = np.random.default_rng(seed + 1000)
    for _ in range(int(tries)):
        row = int(rng.integers(0, counts.shape[0]))
        off = int(rng.integers(0, counts.shape[1] - n_bins))
        w = counts[row, off:off + n_bins]
        if w.mean() > 0 and ptm_range[0] <= w.max() / w.mean() <= ptm_range[1]:
            return w.copy(), row, off, float(w.max() / w.mean())
    raise RuntimeError(f"no segment with peak-to-mean in {ptm_range} found in {tries} draws")


def build(seed, rho=0.7, ne=20, duration_s=300.0, mix="uniform", weights="uniform", profiles=None, bw=None, apps=None, rate_cap=None,
          arrivals="poisson", span="dev", peak_tasks_cap=PEAK_TASKS_CAP, mem_scale=1.0):
    """apps: the applications of this experiment (names from BENCHMARKS; default all six). One application per experiment keeps one of
    them from dominating the results. rate_cap: the most requests per second the testbed can drive; when the rate needed for `rho` is higher
    the rate is capped and meta["rho_effective"] says what load was actually offered.
    arrivals: "poisson" (constant rate, the default) or "azure" (13 Nov 2026, user): a non-homogeneous Poisson process whose per-minute rate follows a segment of the Azure
    2019 trace (`azure_series`), one application only, scaled so that the MEAN offered load over the run is `rho`, then scaled down if the busiest minute would offer more
    than `peak_tasks_cap` tasks per second; meta["rho_effective"] is the mean load actually offered, meta["rho_peak"] the busiest minute's. The cluster (network,
    capacities) is the same as for Poisson arrivals of the same seed."""
    prof = profiles or load_profiles()
    benches = list(apps) if apps else list(BENCHMARKS)
    bad = [b for b in benches if b not in BENCHMARKS]
    if bad:
        raise ValueError(f"unknown application(s) {bad}; known: {BENCHMARKS}")
    rng = np.random.default_rng(seed)
    functions, fid, quant, names = [], {}, [], []
    for b in benches:
        for name, p in prof["workflows"][b]["functions"].items():
            fid[(b, name)] = len(functions)
            functions.append(Function(len(functions), float(p["duration_s_mean"]), float(p["cold_init_s_median"])))
            quant.append(np.asarray(p["duration_s_q"], dtype=float))
            names.append(f"{b}/{name}")
    cold_ratio = {n: round(float(prof["workflows"][n.split("/")[0]]["functions"][n.split("/")[1]]["cold_init_s_median"]
                               / max(prof["workflows"][n.split("/")[0]]["functions"][n.split("/")[1]]["duration_s_q"][50], 1e-6)), 2) for n in names}
    workflows, work = [], []
    for wid, b in enumerate(benches):
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
    p = np.full(len(benches), 1.0 / len(benches)) if mix == "uniform" else (1.0 / work) / np.sum(1.0 / work)
    if mix not in ("uniform", "equal_load"):
        raise ValueError("mix is 'uniform' or 'equal_load'")
    lam = float(rho * ecc.sum() / np.sum(p * work))                        # requests per second needed for the target load
    lam_needed = lam
    trace_meta = {}
    if arrivals == "azure":
        if len(benches) != 1:
            raise ValueError("azure arrivals drive one application per experiment")
        from dfps.traces import thin_arrivals
        n_bins = int(np.ceil(duration_s / 60.0))
        series, trow, toff, ptm = azure_series(seed, n_bins, span)
        mean_tasks = float(workflows[0].n)
        rate = series / series.mean() * lam                                 # requests/s per minute, mean = the rate the target load needs
        scale = min(1.0, float(peak_tasks_cap) / (float(rate.max()) * mean_tasks)) if peak_tasks_cap else 1.0
        rate = rate * scale
        lam, rho_eff = float(rate.mean()), float(rate.mean() * work[0] / ecc.sum())
        arr = thin_arrivals(rate[None, :], 60.0, duration_s, ne, np.random.default_rng(seed + 1000))
        trace_meta = dict(arrivals="azure2019-F1", trace_span=span, trace_row=trow, trace_offset_min=toff, trace_peak_to_mean=ptm, peak_scale=float(scale),
                          rho_peak=float(rate.max() * work[0] / ecc.sum()), rate_series=rate.tolist(), bin_s=60.0, peak_tasks_per_s=float(rate.max() * mean_tasks))
    else:
        if arrivals != "poisson":
            raise ValueError("arrivals is 'poisson' or 'azure'")
        if rate_cap is not None and lam > rate_cap:
            lam = float(rate_cap)
        rho_eff = float(lam * np.sum(p * work) / ecc.sum())
        arr, t = [], float(rng.exponential(1.0 / lam))
        while t < duration_s:
            arr.append((t, int(rng.choice(len(benches), p=p)), int(rng.integers(0, ne))))
            t += float(rng.exponential(1.0 / lam))
    arrivals = arr
    meta = dict(seed=seed, workload="sebs-flow only, measured", capacity_model="CAP-U", rho=rho, rho_effective=rho_eff, rate_needed_per_s=lam_needed, rate_cap=rate_cap, apps=benches, mix=mix,
                rate_per_s=lam, ne=ne,
                n_arrivals=len(arrivals), mean_tasks=float(np.mean([w.n for w in workflows])), work_per_request_s=work.tolist(),
                workflows=benches, function_names=names,
                cold_init_over_median_task=cold_ratio, dag_source="SeBS-Flow Table 4 (dfps/sebsflow.py)",
                profile_source=prof["source"], cold_start_model="measured SeBS-Flow initialisation (AWS 2024)", duration_s=duration_s, **trace_meta)
    sc = Scenario(functions, workflows, net, ecc, esc, arrivals, meta)
    if mem_scale != 1.0:
        # cost test (16 Nov 2026): the same arrivals on a cluster with a fraction of the memory. The rate was fixed above from the ORIGINAL capacity, so the load against the
        # scaled cluster is rho / mem_scale. Per-node capacities are scaled and rounded (at least 1); the node count is unchanged.
        sc.meta.update(mem_scale=float(mem_scale), ecc_total_original=int(ecc.sum()))
        sc.ecc = np.maximum(1, np.rint(np.asarray(ecc, dtype=float) * float(mem_scale))).astype(int)
        sc.meta["ecc_total"] = int(sc.ecc.sum())
    if weights == "memory":
        # CAP-W2 (13 Nov 2026, user: "measured memory weights"): a container's size is the memory its function used in the SeBS-Flow runs, relative to the median function of all
        # six workflows, clipped to [0.25, 4] as in CAP-W1, scaled to mean 1 over the functions of the scenario, then scaled so that the offered load in capacity units equals
        # the nominal load (the CAP-W1 load-preserving step: without it a weighted run offers a different load than the CAP-U run it is compared with). CPU is not measured in
        # the data; from the AWS rule (1,769 MB = one vCPU, proportional to configured memory) it is one value per workflow, so it adds no per-function difference and is recorded only.
        # The earlier, unnormalised definition of this label was never used for a result.
        ref_mb = float(np.median([float(f["mem_used_mb_median"]) for w_ in prof["workflows"].values() for f in w_["functions"].values()]))
        mem = np.array([float(prof["workflows"][x.split("/")[0]]["functions"][x.split("/")[1]]["mem_used_mb_median"]) for x in names])
        w = np.clip(mem / ref_mb, 0.25, 4.0)
        fw = w / w.mean()
        mu = np.array([f.exec_time for f in functions])
        raw = sum(float(sum(mu[f] * fw[f] for f in workflows[wid].ft)) for _, wid, _ in arrivals)
        base = sum(float(sum(mu[f] for f in workflows[wid].ft)) for _, wid, _ in arrivals)
        scale = base / raw if raw > 0 else 1.0
        # Rounded to 0.01 (13 Nov 2026, found by the FaaSPR Video explosion): the load-preserving scale makes the function that dominates the offered load weigh almost exactly 1
        # (Video: 1.0002), and with integer node capacities a weight of 1.0002 fits one container fewer per node (20 / 1.0002 -> 19): a 7% capacity cut that is rounding noise, not
        # a property of the workload. FaaSPR's placement skips what does not fit, left `decode` with 1 container and 877 queued tasks (P99 6,039 s; 250 s with the rounded weights).
        fw = np.round(fw * scale, 2)
        raw2 = sum(float(sum(mu[f] * fw[f] for f in workflows[wid].ft)) for _, wid, _ in arrivals)
        sc.fw = fw
        cfg = {b: int(str(prof["workflows"][b]["duration_run"]).rsplit("_", 1)[1]) for b in benches}
        sc.meta.update(capacity_model="CAP-W2", fw_source="SeBS-Flow measured memory used (median per function)", fw_reference_mb=ref_mb, fw_clip=[0.25, 4.0],
                       fw_load_scale=float(scale), fw_rounding=0.01, fw_load_error=float(raw2 / base - 1.0) if base > 0 else 0.0, fw_by_function={n: float(v) for n, v in zip(names, sc.fw)},
                       configured_memory_mb=cfg, derived_vcpu_aws_1769mb={b: cfg[b] / 1769.0 for b in benches})
    elif weights != "uniform":
        raise ValueError("weights is 'uniform' or 'memory'")

    return sc, CrnSampler(quant, seed)
