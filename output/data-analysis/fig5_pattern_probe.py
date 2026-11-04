"""Probe: which setting makes our Fig. 5 look like the DFPS paper's (order of B*, Heu, RL; flat count curves)?
Pre-registered in knowledge/synthesis/fig5-7-reproduction-gap.md (3 Nov 2026). Capacity model CAP-U, as the reproduction.

  python output/data-analysis/fig5_pattern_probe.py run [workers]
  python output/data-analysis/fig5_pattern_probe.py report

Variants (workflows x protocol):
  cal300   calibrated pool (Alibaba < 60 s, longest chain <= 2), fixed 300 s, 30 s warm-up   (= results/fig567_cal)
  calN     calibrated pool, fixed request count: run length 300 s / scale, warm-up 10% of it
  wide300  full < 60 s pool (all depths),          fixed 300 s
  wideN    full pool, fixed request count
Utilisation is reported as busy / slot capacity (as the reproduction) and busy / alive-container time (accounting only).
"""
from __future__ import annotations

import json
import pickle
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from experiments.run import ASSUME, initial_placements, load_rl_policy  # noqa: E402
from dfps.heu import HeuPolicy  # noqa: E402
from dfps.ondemand import OnDemandSim  # noqa: E402
from dfps.sim import Sim  # noqa: E402
from dfps.variants import make_adjuster, sim_kwargs  # noqa: E402
from dfps.workload import build_scenario  # noqa: E402
from fig567_reproduction import CAL_DAGS, CAL_MAPPING, CAL_MAXDEPTH, offered_util  # noqa: E402

CAP = "CAP-U"
OUT = ROOT / "results" / "fig5_probe"
CAL = ROOT / "results" / "fig567_cal"
PAPER = json.loads((ROOT / "output" / "data-analysis" / "results" / "paper_fig5_digitized.json").read_text())
VARIANTS = {"cal300": ("cal", False), "calN": ("cal", True), "wide300": ("wide", False), "wideN": ("wide", True)}
# probe 2 (release after use): Heu and RL with keep_warm=0 on the base variant's scenario; SR, SG, DFPS come from the base
REL = {"cal300r": "cal300", "calNr": "calN", "wideNr": "wideN"}
REL_METHODS = ("HEU", "RL")


def base(variant):
    return REL.get(variant, variant)
KINDS, SCALES, SEED = ("uniform", "pareto"), (0.25, 1.0, 2.0), 1
METHODS = ("SR", "SG", "DFPS", "HEU", "RL")
PAPER_NAME = {"SR": "SR", "SG": "SG", "DFPS": "DFPS", "HEU": "Heu", "RL": "RL"}
BASE_S, BASE_W = float(ASSUME["A21_run_length_s"]), float(ASSUME["A21_warmup_s"])


def timing(variant, scale):
    """(run length, warm-up) of a variant: fixed 300 s, or a fixed request count (the x1 count) with a 10% warm-up."""
    if VARIANTS[base(variant)][1]:
        d = BASE_S / scale
        return d, 0.1 * d
    return BASE_S, BASE_W


def tag(variant, kind, scale):
    return f"{variant}_{kind}_x{scale}_s{SEED}"


class AcctOnDemand(OnDemandSim):
    """OnDemandSim plus the integral of alive containers over the measured window (accounting only: every event handler is
    wrapped to add tot.sum() x elapsed time before it runs; the run itself is unchanged)."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self._prov, self._tp = 0.0, 0.0
        for name in [n for n in dir(self) if n.startswith("_ev_")]:
            setattr(self, name, self._wrap(getattr(self, name)))

    def _add(self, t):
        lo, hi = max(self._tp, self.warmup), min(t, self.duration)
        if hi > lo:
            self._prov += float(self.tot.sum()) * (hi - lo)
        self._tp = max(self._tp, t)

    def _wrap(self, fn):
        def g(a, b, c):
            self._add(self.now)
            return fn(a, b, c)
        return g

    def run(self):
        r = super().run()
        self._add(self.duration)
        r["provisioned_slot_s"] = self._prov
        return r


def scenarios():
    """Build (or reuse) the scenario of every (variant, kind, scale); returns {tag: pkl path}."""
    OUT.mkdir(parents=True, exist_ok=True)
    paths, pools = {}, {}
    for v, (pool, _) in VARIANTS.items():
        for kind in KINDS:
            for s in SCALES:
                p = OUT / f"{tag(v, kind, s)}.pkl"
                paths[tag(v, kind, s)] = p
                if p.exists():
                    continue
                if v == "cal300":                                   # the reproduction's own scenario, unchanged
                    src = CAL / f"{kind}_x{s}_n80_a15_s{SEED}.pkl"
                    p.write_bytes(src.read_bytes())
                    continue
                if pool not in pools:
                    from calibrate_fig5 import dag_depth
                    allp = json.load(open(ROOT / "data" / CAL_DAGS))
                    pools[pool] = [d for d in allp if dag_depth(d) <= CAL_MAXDEPTH] if pool == "cal" else allp
                d, _ = timing(v, s)
                sc = build_scenario(SEED, kind, s, ne=80, n_workflows=15, duration_s=d, dags=pools[pool],
                                    function_mapping=CAL_MAPPING, pool_size=ASSUME["A17_function_pool_size"])
                sc.meta = dict(sc.meta, capacity_model=CAP, probe_variant=v)
                pickle.dump(sc, open(p, "wb"))
    return paths


def job(args):
    try:
        return _job(args)
    except Exception:
        import traceback
        Path(args[1]).with_suffix(".err").write_text(traceback.format_exc())
        return args[1] + " FAILED"


def _job(args):
    sc_path, out_path, variant, method = args
    if Path(out_path).exists():
        return out_path
    import torch
    torch.set_num_threads(1)
    sc = pickle.load(open(sc_path, "rb"))
    scale = float(sc.meta["scale"])
    dur, warm = timing(variant, scale)
    rho = offered_util(sc)
    overloaded = bool(rho >= 0.8 or (sc.meta["kind"] == "pareto" and scale >= 0.5) or scale >= 2.0)  # as fig567_reproduction
    t = time.time()
    if method in ("HEU", "RL"):
        pol = HeuPolicy(seed=SEED + 500) if method == "HEU" else load_rl_policy(str(ROOT / "results" / "rl_policy.pt"), SEED + 600)
        sim = AcctOnDemand(sc, pol, seed=SEED + 400, duration=dur, warmup=warm,
                           keep_warm=0 if variant in REL else None)
        r = sim.run()
    else:
        x_sr, x_sg, _ = initial_placements(sc, SEED, ASSUME["A06_generations"], "abs")
        kw = sim_kwargs("B_STAR", ASSUME)
        kw["warmup"] = warm
        retry, cap = (1.0, 10) if overloaded else (0.0, None)
        adj = make_adjuster("B_STAR", ASSUME, seed=SEED + 300) if method == "DFPS" else None
        sim = Sim(sc, x_sr if method == "SR" else x_sg, adjuster=adj, seed=SEED + 400, retry_min_interval=retry,
                  retry_max_attempts=cap, **kw)
        r = sim.run()
    sim.check_invariants()
    r["wall_s"] = time.time() - t
    busy = r["utilization"] * float(sc.ecc.sum()) * (dur - warm)
    r["util_alive"] = busy / r["provisioned_slot_s"] if r.get("provisioned_slot_s") else float("nan")
    Path(out_path).write_text(json.dumps(dict(capacity_model=CAP, variant=variant, kind=sc.meta["kind"], scale=scale,
                                              method=method, overloaded=overloaded, offered_util=rho, duration=dur,
                                              warmup=warm, n_tasks_mean=float(np.mean([w.n for w in sc.workflows])),
                                              result=r)))
    return out_path


def run(workers):
    paths = scenarios()
    jobs = [(str(paths[tg]), str(OUT / f"{tg}.{m}.json"), tg.split("_")[0], m) for tg in paths for m in METHODS]
    for rv, bv in REL.items():
        jobs += [(str(paths[tg]), str(OUT / f"{rv}{tg[len(bv):]}.{m}.json"), rv, m)
                 for tg in paths if tg.split("_")[0] == bv for m in REL_METHODS]
    jobs = [j for j in jobs if not Path(j[1]).exists()]
    jobs.sort(key=lambda j: (j[3] != "HEU", "wide" not in j[2], "pareto" not in j[0], "x2.0" not in j[0]))  # slow first
    print(len(jobs), "jobs", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        for d in ex.map(job, jobs):
            print("done", d, flush=True)


def kendall(a, b):
    n, s = len(a), 0
    for i in range(n):
        for j in range(i + 1, n):
            s += np.sign(a[i] - a[j]) * np.sign(b[i] - b[j])
    return s / (n * (n - 1) / 2)


def report():
    R = {}
    for f in OUT.glob("*.json"):
        x = json.loads(f.read_text())
        R[(x["variant"], x["kind"], x["scale"], x["method"])] = x
    xi = {0.25: 0, 1.0: 3, 2.0: 7}                                   # index into the paper's 8 points
    for v in list(VARIANTS) + list(REL):
        own = [k for k in R if k[0] == v]
        if v in REL:                                                 # SR, SG, DFPS of the base variant
            for k in [k for k in R if k[0] == REL[v] and k[3] not in REL_METHODS]:
                R[(v,) + k[1:]] = R[k]
        have = [k for k in R if k[0] == v]
        print(f"\n=== {v}: {len(own)} own runs" + (f" (+ SR/SG/DFPS of {REL[v]})" if v in REL else ""))
        if not own:
            continue
        for kind in KINDS:                                           # (e) cold starts per task run (all tasks, warm-up included)
            row = []
            for m in ("HEU", "RL"):
                vals = []
                for s in SCALES:
                    x = R.get((v, kind, s, m))
                    if x:
                        vals.append(x["result"]["cold_starts_total"] / (x["result"]["n_arrived"] * x["n_tasks_mean"]))
                row.append(f"{m} " + "/".join(f"{a:.2f}" for a in vals))
            print(f"  {kind} cold starts per task (x0.25/x1/x2): " + "   ".join(row))
        taus = []
        for kind in KINDS:
            P = PAPER[kind]
            print(f"  {kind}  (ours | paper)   tasks/request "
                  f"{np.mean([R[k]['n_tasks_mean'] for k in have if k[1] == kind]):.2f}")
            for s in SCALES:
                ms = [R.get((v, kind, s, m), {}).get("result", {}).get("avg_makespan") for m in METHODS]
                pm = [P["makespan"][PAPER_NAME[m]][xi[s]] for m in METHODS]
                if None not in ms:
                    taus.append(kendall(ms, pm))
                print(f"    x{s}: makespan " + "  ".join(
                    f"{m} {('-' if a is None else f'{a:.0f}')}|{b:.0f}" for m, a, b in zip(METHODS, ms, pm)))
            for lab, key, pk in (("cold", "cold_starts", "cold"), ("util cap %", "utilization", "util"),
                                 ("util alive %", "util_alive", "util")):
                row = []
                for m in METHODS:
                    vals = [R.get((v, kind, s, m), {}).get("result", {}).get(key) for s in SCALES]
                    mul = 100 if "util" in lab else 1
                    pv = [P[pk][PAPER_NAME[m]][xi[s]] for s in SCALES]
                    row.append(f"{m} " + "/".join("-" if a is None else f"{a * mul:.0f}" for a in vals)
                               + " | " + "/".join(f"{b:.0f}" for b in pv))
                print(f"    {lab}: " + "   ".join(row))
            for lab, key, pk in (("ratio x2/x0.25 makespan", "avg_makespan", "makespan"), ("ratio x2/x0.25 cold", "cold_starts", "cold")):
                row = []
                for m in METHODS:
                    a = [R.get((v, kind, s, m), {}).get("result", {}).get(key) for s in (0.25, 2.0)]
                    b = [P[pk][PAPER_NAME[m]][xi[s]] for s in (0.25, 2.0)]
                    ours = (a[1] / a[0]) if None not in a and a[0] else None
                    pap = (b[1] / b[0]) if b[0] else None
                    row.append(f"{m} {'-' if ours is None else f'{ours:.2f}'}|{'-' if pap is None else f'{pap:.2f}'}")
                print(f"    {lab}: " + "  ".join(row))
        print(f"  (a) mean Kendall tau of the makespan order vs paper: "
              f"{np.mean(taus):.2f} over {len(taus)} points" if taus else "  (a) -")


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 6)
    else:
        report()
