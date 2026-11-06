"""Decision times of on-demand FROZEN-3 against cluster size (7 Nov 2026; plan: knowledge/synthesis/independent-baselines-capw1.md, section 8, step 5).
FROZEN-3 on-demand, re-layout every 30 s, target 0.7, moves every 4 s. Times the controller's three decisions with perf_counter, in one process:
  relayout  bottleneck_first_placement (sizing + placement computation; not the simulator applying it)
  move      rebalance_step (one request-move pass)
  route     the transfer_only dispatcher, per request
Scenarios: synthetic DAGs (no Alibaba parse), DFPS ranges, memory-like weights U(0.5, 2), load rho 0.7 per server at every size, random feasible start layout.
Sweep A: functions and workflows fixed (30, 15). Sweep B: scaled with the servers. CAP-W1.
  python capw1_scale.py one N F W [seed]    one size, writes results/capW1_scale/N{N}_F{F}_W{W}_s{seed}.json (also partial, every 120 s of wall time)
  python capw1_scale.py sweep [timeout_s]   sizes in order, each in its own process with a time limit
  python capw1_scale.py report
"""
import json
import os
for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ[_v] = "1"             # one core: the feasibility rule is stated for one core, and BLAS threads would hide the growth
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
FAST = os.environ.get("FASTPATH", "")             # "1": fast_order + fast_place; "2": fast_order + lazy_place; results kept apart
OUT = ROOT / "results" / {"": "capW1_scale", "1": "capW1_scale_fast", "2": "capW1_scale_lazy"}[FAST]
DURATION, WARMUP = 240.0, 60.0
RHO, TARGET, EPOCH, MOVE_S = 0.7, 0.7, 30.0, 4.0
SWEEP_A = [(n, 30, 15) for n in (80, 160, 320, 640, 1280)]
SWEEP_B = [(n, 30 * n // 80, 15 * n // 80) for n in (160, 320, 640, 1280)]
LIMITS_MS = dict(relayout=3000.0, move=400.0, route=10.0)     # the feasibility rule fixed in the plan


def scenario(N, F, W, seed):
    from dfps.workload import build_scenario
    def rho_of(sc, fw):
        mu = np.array([f.exec_time for f in sc.functions])
        busy = sum(float(sum(mu[f] * fw[f] for f in sc.workflows[w].ft)) for t, w, _ in sc.arrivals if WARMUP <= t < DURATION)
        return busy / (float(np.sum(sc.ecc)) * (DURATION - WARMUP))
    sc0 = build_scenario(seed, kind="uniform", scale=0.05, ne=N, n_workflows=W, pool_size=F, duration_s=DURATION)
    fw = np.random.default_rng(seed + 77).uniform(0.5, 2.0, F)
    scale = 0.05 * RHO / rho_of(sc0, fw)
    sc = build_scenario(seed, kind="uniform", scale=scale, ne=N, n_workflows=W, pool_size=F, duration_s=DURATION)
    sc.fw = fw
    sc.meta = dict(sc.meta, capacity_model="CAP-W1", setting="scalability, synthetic DAGs", rho_w=float(rho_of(sc, fw)))
    return sc


def stats(x):
    if not len(x):
        return None
    a = np.asarray(x, dtype=float) * 1e3
    return dict(n=int(a.size), median=float(np.median(a)), p99=float(np.percentile(a, 99)), max=float(a.max()), mean=float(a.mean()))


def one(N, F, W, seed=1):
    import yaml
    from dfps.nsga2 import PlacementProblem
    import dfps.o3s as O3
    from dfps import dispatchers as D
    from dfps.dispatch_priority import QueuePriority
    from dfps.sim import Sim
    from dfps.variants import make_adjuster, sim_kwargs
    from frozen2 import FROZEN3
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"N{N}_F{F}_W{W}_s{seed}.json"
    A = yaml.safe_load((ROOT / "config" / "assumptions.yaml").read_text(encoding="utf-8"))
    t_build = time.time()
    sc = scenario(N, F, W, seed)
    fw = np.asarray(sc.fw, float)
    prob = PlacementProblem(sc.network, sc.ecc, np.array([f.exec_time for f in sc.functions]), "abs", fw=sc.fw)
    X0 = prob.random(np.random.default_rng(seed + 100))
    assert (X0 @ fw <= sc.ecc + 1e-9).all() and (X0.sum(axis=0) >= 1).all()
    t_build = time.time() - t_build
    T = dict(relayout=[], move=[], route=[], queued=[], moves=[])
    t0, last = time.time(), [time.time()]

    def save(done, r=None):
        row = dict(capacity_model="CAP-W1", N=N, F=F, W=W, seed=seed, done=done, build_s=t_build, wall_s=time.time() - t0, sim_now=float(sim.now), n_arrivals=len(sc.arrivals),
                   rho_w=sc.meta["rho_w"], relayout=stats(T["relayout"]), relayout_later=stats(T["relayout"][1:]), move=stats(T["move"]), route=stats(T["route"]),
                   queued_mean=float(np.mean(T["queued"])) if T["queued"] else 0.0, moves_per_pass=float(np.mean(T["moves"])) if T["moves"] else 0.0)
        if r:
            row.update(p99_makespan=r["p99_makespan"], avg_makespan=r["avg_makespan"], n_completed=r["n_completed"], cold_starts=r["cold_starts"], mover_impl=r.get("mover_impl"), mover_pass=r.get("mover_pass"))
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(row))
        tmp.replace(path)

    def tick():
        if time.time() - last[0] > 120.0:
            last[0] = time.time()
            save(False)

    o_bfp = O3.bottleneck_first_placement

    def bfp(*a, **k):
        t = time.perf_counter()
        x = o_bfp(*a, **k)
        T["relayout"].append(time.perf_counter() - t)
        tick()
        return x
    O3.bottleneck_first_placement = bfp
    o_reb = O3.O3SimAdjuster.rebalance_step

    def reb(self, s, max_moves=None):
        q = sum(len(s.queue[k][f]) for k in range(s.N) for f in range(s.F))
        m0 = getattr(self, "rebal_moves", 0)
        t = time.perf_counter()
        x = o_reb(self, s, max_moves)
        T["move"].append(time.perf_counter() - t)
        T["queued"].append(q)
        T["moves"].append(getattr(self, "rebal_moves", 0) - m0)
        tick()
        return x
    O3.O3SimAdjuster.rebalance_step = reb
    route0 = D.DISPATCHERS["transfer_only"]

    def route(s, r):
        t = time.perf_counter()
        x = route0(s, r)
        T["route"].append(time.perf_counter() - t)
        return x
    kw = sim_kwargs("B_STAR", A)
    kw.update(warmup=WARMUP, duration=DURATION, retry_min_interval=1.0, retry_max_attempts=10, dispatcher=route, queue_priority=QueuePriority("full", aging=2.0))
    churn = dict(FROZEN3, lam=0.5, elastic=True, util_cap=TARGET)
    if FAST == "1":
        churn.update(fast_order=True, fast_place=True)
    elif FAST == "2":
        churn.update(fast_order=True, lazy_place=True)
    adj = O3.O3SimAdjuster(make_adjuster("B_STAR", A, seed=seed + 300), MOVE_S, epoch=EPOCH, horizon=30.0, K=8, seed=seed + 800, warmup=WARMUP, blind=True, cand_mode="nosim", churn=churn)
    kw["interval"] = adj.next_interval
    sim = Sim(sc, X0.copy(), adjuster=adj, seed=seed + 400, **kw)
    t0 = time.time()
    r = sim.run()
    save(True, r)
    print(path, flush=True)


def sweep(timeout_s):
    for N, F, W in SWEEP_A + SWEEP_B:
        p = OUT / f"N{N}_F{F}_W{W}_s1.json"
        if p.exists() and json.loads(p.read_text()).get("done"):
            continue
        print("start", N, F, W, time.strftime("%H:%M:%S"), flush=True)
        try:
            subprocess.run([sys.executable, str(Path(__file__).resolve()), "one", str(N), str(F), str(W)], timeout=timeout_s, check=False)
        except subprocess.TimeoutExpired:
            print("timed out, partial result kept:", N, F, W, flush=True)


def fit(xs, ys):
    return float(np.polyfit(np.log(xs), np.log(ys), 1)[0])


def report():
    rows = [json.loads(p.read_text()) for p in sorted(OUT.glob("N*_s1.json"))]
    for name, sw in (("A: functions and workflows fixed (30, 15)", SWEEP_A), ("B: functions and workflows scaled with servers", [(80, 30, 15)] + SWEEP_B)):
        print("\nSweep", name)
        print(f"{'N':>5s} {'F':>4s} {'W':>4s} {'done':>5s} {'sim s':>6s} {'wall s':>7s} | {'relayout ms: median':>20s} {'later max':>10s} {'first+all max':>13s} | {'move ms: median':>16s} {'p99':>8s} {'queued':>7s} {'moves/pass':>10s} | {'route ms: median':>16s} {'p99':>7s}")
        ok = []
        for N, F, W in sw:
            x = [r for r in rows if (r["N"], r["F"], r["W"]) == (N, F, W)]
            if not x:
                continue
            r = x[0]
            rl, rl2, mv, rt = r["relayout"], r["relayout_later"], r["move"], r["route"]
            if rl and mv and rt:
                ok.append((N, (rl2 or rl)["median"], mv["median"], rt["median"], rl["max"], mv["p99"], rt["p99"]))
                print(f"{N:5d} {F:4d} {W:4d} {str(r['done']):>5s} {r['sim_now']:6.0f} {r['wall_s']:7.0f} | {(rl2 or rl)['median']:20.1f} {(rl2 or rl)['max']:10.1f} {rl['max']:13.1f} | {mv['median']:16.1f} {mv['p99']:8.1f} {r['queued_mean']:7.0f} {r['moves_per_pass']:10.0f} | {rt['median']:16.2f} {rt['p99']:7.2f}")
        if len(ok) >= 3:
            a = np.array(ok)
            print("  growth exponent with N (median): relayout %.2f, move %.2f, route %.2f" % (fit(a[:, 0], a[:, 1]), fit(a[:, 0], a[:, 2]), fit(a[:, 0], a[:, 3])))
            for n, _, _, _, rlm, mvp, rtp in ok:
                print(f"  N={int(n):5d} feasible? relayout max {rlm:9.1f} ms (limit {LIMITS_MS['relayout']:.0f}): {rlm <= LIMITS_MS['relayout']}; move p99 {mvp:8.1f} ms (limit {LIMITS_MS['move']:.0f}): {mvp <= LIMITS_MS['move']}; route p99 {rtp:6.2f} ms (limit {LIMITS_MS['route']:.0f}): {rtp <= LIMITS_MS['route']}")


if __name__ == "__main__":
    c = sys.argv[1]
    if c == "one":
        one(int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]) if len(sys.argv) > 5 else 1)
    elif c == "sweep":
        sweep(float(sys.argv[2]) if len(sys.argv) > 2 else 2400.0)
    else:
        report()
