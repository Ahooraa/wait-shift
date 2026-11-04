"""Request-move mechanism, gap diagnosis step 2 (pre-registered 2 Nov 2026, knowledge/synthesis/workflow-aware-decision-rules.md,
"Request-move mechanism, gap diagnosis step 2"). The 18 development cases, config D of grid2x2_v2.py.

  (a) timing rung: the same controller with the move period at 1 s (R1) and 0.5 s (R05); reference = geometric mean of three null
      runs per case (D at 4 s, and the placebos P1/P2 with the period +-1 ms, results/placement_ext/T1). Bounds an idle-initiated pull.
  (b) estimate-error replication: logging-only runs of the baseline (event hash must equal the stored D run), then the step-1
      analysis (predicted vs realised time to start at the destination of each rule move) with a case-level train/test split.

  python move_gap_probe.py run [workers]    missing placebos, rung runs, logging runs (resumable)
  python move_gap_probe.py check            logging runs reproduce the stored D runs exactly?
  python move_gap_probe.py report           the pre-registered reading of (a) and (b)
"""
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
import placement_extensions as pe  # noqa: E402

LOGS = ROOT / "results" / "move_gap" / "log"
FAMS, RHOS, SEEDS = pe.FAMS, pe.RHOS, pe.SEEDS


def cases():
    return [(f, r, s) for f in FAMS for r in RHOS for s in SEEDS]


def log_job(args):
    tg, seed, family = args
    out = LOGS / f"{tg}.json"
    if out.exists():
        return str(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        import pickle
        import yaml
        assert np.__version__.startswith("1."), "run with the Anaconda interpreter (numpy 1.26)"
        import d3s_headroom as d
        from frozen2 import FROZEN2, MOVE_PERIOD_S
        from dfps.dispatch_priority import QueuePriority
        from dfps.o3s import O3SimAdjuster
        from dfps.sim import Sim
        from dfps.solution import Sol
        from dfps.variants import make_adjuster, sim_kwargs

        class LSim(Sim):
            """Logging only: for every rule move, the estimate's parts at the destination (pre-step state) and, later, the start."""

            def _init_log(self):
                self.mlog, self.starts, self._pre, self.src = [], {}, None, "other"

            def _start(self, ins, run):
                super()._start(ins, run)
                self.starts[(run.req.id, run.task)] = (self.now, int(ins.node), run.n_moves)

            def apply_solution(self, sol):
                pre, s0 = {}, None
                for run, k_new in list(sol.rnode.items()):
                    if k_new != run.node and run in self.queue[run.node][run.f]:
                        if s0 is None:
                            s0 = Sol(self)
                        pre[id(run)] = (s0.aet(run, int(k_new), parts=True), len(self.queue[int(k_new)][run.f]),
                                        int(self.cnt[run.f, int(k_new)]))
                self._pre, prev, self.src = pre, self.src, "rebal"
                super().apply_solution(sol)
                self._pre, self.src = None, prev

            def relocate(self, run, k_new):
                p = self._pre.get(id(run)) if self._pre else None
                if p and self.in_window(run.req.t_arr):
                    self.mlog.append((self.now, run.req.id, run.task, int(run.f), int(k_new), run.n_moves) + tuple(p[0]) + (p[1], p[2]))
                super().relocate(run, k_new)

        ASSUME = yaml.safe_load((ROOT / "config" / "assumptions.yaml").read_text(encoding="utf-8"))
        sc = pickle.load(open(d.D1 / f"{tg}.pkl", "rb"))
        P = pickle.load(open(d.D1 / f"{tg}.prep.pkl", "rb"))
        kw = sim_kwargs("B_STAR", ASSUME)
        kw.update(warmup=d.WARMUP, duration=d.DURATION, retry_min_interval=1.0, retry_max_attempts=10)
        kw["queue_priority"] = QueuePriority("full", aging=2.0)
        churn = dict(FROZEN2, lam=0.5)
        adj = O3SimAdjuster(make_adjuster("B_STAR", ASSUME, seed=seed + 300), MOVE_PERIOD_S[family], epoch=60.0, horizon=30.0, K=8,
                            seed=seed + 800, warmup=d.WARMUP, blind=True, cand_mode="nosim", churn=churn)
        kw["interval"] = adj.next_interval
        sim = LSim(sc, P["X0"].copy(), adjuster=adj, seed=seed + 400, **kw)
        sim._init_log()
        t0 = time.time()
        res = sim.run()
        sim.check_invariants()
        mu = [float(x) for x in sim.exec_time]
        rows = []   # transfer, predicted wait, mean run time, queue length, containers at the destination, realised time to start, move time
        for t, rid, task, f, k_new, nb, inp, svc, outp, ql, cn in sim.mlog:
            st = sim.starts.get((rid, task))
            if st is None or st[1] != k_new or st[2] != nb + 1:
                continue
            rows.append([inp, svc - mu[f], mu[f], ql, cn, st[0] - t, t])
        out.write_text(json.dumps(dict(case=tg, event_hash=res["event_hash"], p99=res["p99_makespan"], n_moved=res["n_moved"],
                                       n_logged=len(sim.mlog), rows=rows, wall_s=time.time() - t0)))
    except Exception:
        import traceback
        out.with_suffix(".err").write_text(traceback.format_exc())
        return str(out) + " FAILED"
    return str(out)


def dispatch(job):
    kind, args = job
    return pe.job(args) if kind == "pe" else log_job(args)


def run(workers):
    jobs = []
    for f, r, s in cases():
        tg = pe.tag(f, r, s)
        for n in ("P1", "P2", "R1", "R05"):
            if not (pe.RES / "T1" / f"{tg}.{n}.json").exists():
                jobs.append(("pe", ("T1", tg, n, s, f, "T1")))
        if not (LOGS / f"{tg}.json").exists():
            jobs.append(("log", (tg, s, f)))
    jobs.sort(key=lambda j: 0 if j[0] == "pe" and j[1][2] in ("R05", "R1") else 1)      # the slow rungs first
    print(f"{len(jobs)} runs, {workers} workers", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        for r in ex.map(dispatch, jobs):
            print("done", r, flush=True)


def check():
    ref = {}
    for f in pe.T1_REF.glob("*.D.json"):
        x = json.loads(f.read_text())
        ref[(x["family"], x["rho"], x["seed"])] = x["result"]
    same = tot = 0
    for f in sorted(LOGS.glob("*.json")):
        x = json.loads(f.read_text())
        fam, rho, seed = x["case"].split("_r")[0], float(x["case"].split("_r")[1].split("_s")[0]), int(x["case"].split("_s")[1])
        r = ref[(fam, rho, seed)]
        tot += 1
        ok = x["event_hash"] == r["event_hash"] and x["p99"] == r["p99_makespan"]
        same += ok
        if not ok:
            print("DIFFERENT:", x["case"])
    print(f"logging runs identical to the stored D runs (event hash and P99): {same} of {tot}")


def boot_ci(x, n=10000, seed=0):
    x = np.asarray(x, dtype=float)
    m = np.random.default_rng(seed).choice(x, (n, len(x))).mean(axis=1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def rung_report():
    ref, runs = pe.t1_load()
    nulls = {k: [ref[k]["p99_makespan"]] + [runs[p][k]["p99_makespan"] for p in pe.PLACEBO if p in runs and k in runs[p]]
             for k in sorted(ref)}
    full = [k for k in nulls if len(nulls[k]) == 3]
    print(f"=== (a) timing rung: P99 vs the geometric mean of three null runs at 4 s ({len(full)} of 18 cases with all nulls) ===")
    print(f"{'period':>8s} {'n':>3s} {'P99 vs null':>12s} {'95% CI':>16s} {'better':>7s} {'moves/req':>10s} {'cold':>7s} {'P95':>7s}")
    mv0 = np.mean([ref[k]["n_moved"] / max(1, ref[k]["n_completed"]) for k in full]) if full else float("nan")
    for n, lab in (("R1", "1 s"), ("R05", "0.5 s")):
        ks = [k for k in full if n in runs and k in runs[n]]
        if not ks:
            continue
        e = [np.log(runs[n][k]["p99_makespan"]) - np.mean(np.log(nulls[k])) for k in ks]
        lo, hi = boot_ci(e)
        mv = np.mean([runs[n][k]["n_moved"] / max(1, runs[n][k]["n_completed"]) for k in ks])
        cold = np.mean([runs[n][k]["cold_starts"] / ref[k]["cold_starts"] for k in ks]) - 1
        p95 = np.exp(np.mean([np.log(runs[n][k]["p95_makespan"]) - np.log(ref[k]["p95_makespan"]) for k in ks])) - 1
        print(f"{lab:>8s} {len(ks):3d} {(np.exp(np.mean(e)) - 1) * 100:+11.1f}% [{(np.exp(lo) - 1) * 100:+5.1f},{(np.exp(hi) - 1) * 100:+5.1f}]% "
              f"{sum(x < 0 for x in e):3d}/{len(ks):<3d} {mv:5.2f} vs {mv0:4.2f} {cold * 100:+6.1f}% {p95 * 100:+6.1f}%")
    if "R05" in runs:
        ks = [k for k in full if k in runs["R05"]]
        if ks:
            e = [np.log(runs["R05"][k]["p99_makespan"]) - np.mean(np.log(nulls[k])) for k in ks]
            lo, hi = boot_ci(e)
            alive = np.exp(np.mean(e)) - 1 <= -0.03 and hi < 0
            print("verdict M3 (idle-initiated pull):", "ALIVE (>=3% better, interval excludes zero)" if alive
                  else "DEAD (<3% better or interval includes zero)", f"[based on {len(ks)} cases]")


def rows_by_case():
    out = {}
    for f in LOGS.glob("*.json"):
        x = json.loads(f.read_text())
        a = np.array(x["rows"], dtype=float)
        if len(a):
            out[x["case"]] = a
    return out


def ols(X, y):
    X1 = np.column_stack([np.ones(len(X)), X])
    b, *_ = np.linalg.lstsq(X1, y, rcond=None)
    return b


def error_report():
    D = rows_by_case()
    names = sorted(D)
    print(f"\n=== (b) estimate error, {len(names)} logged cases ===")
    if len(names) < 6:
        print("too few logged cases")
        return
    gains = []
    for sd in (0, 1):
        perm = np.random.default_rng(sd).permutation(len(names))
        tr = [names[i] for i in perm[: len(names) // 2]]
        te = [names[i] for i in perm[len(names) // 2:]]
        A, B = np.vstack([D[c] for c in tr]), np.vstack([D[c] for c in te])
        b = ols(np.column_stack([A[:, 0], A[:, 1]]), A[:, 5])
        pc, pn = B[:, 0] + B[:, 1], b[0] + b[1] * B[:, 0] + b[2] * B[:, 1]
        cur, new = np.sqrt(np.mean((B[:, 5] - pc) ** 2)), np.sqrt(np.mean((B[:, 5] - pn) ** 2))
        tot = np.sum((B[:, 5] - B[:, 5].mean()) ** 2)
        gains.append(1 - new / cur)
        print(f"  split {sd}: test rmse current {cur:.2f} s -> recalibrated {new:.2f} s ({(1 - new / cur) * 100:.1f}% lower); "
              f"R2 {1 - np.sum((B[:, 5] - pc) ** 2) / tot:.3f} -> {1 - np.sum((B[:, 5] - pn) ** 2) / tot:.3f}; "
              f"coef transfer {b[1]:.2f}, wait {b[2]:.2f}, intercept {b[0]:+.2f}")
    print("\n  per (family, load) cell, all logged seeds: coefficients, and lateness of idle-predicted destinations by transfer time")
    cell_ok = cell_late = 0
    for f in FAMS:
        for r in RHOS:
            cs = [c for c in names if c.startswith(f"{f}_r{r}_")]
            if not cs:
                continue
            A = np.vstack([D[c] for c in cs])
            b = ols(np.column_stack([A[:, 0], A[:, 1]]), A[:, 5])
            idle = A[:, 1] < 1.0
            late = []
            for lo, hi in ((0, 2), (2, 5), (5, 10), (10, 1e9)):
                m = idle & (A[:, 0] >= lo) & (A[:, 0] < hi)
                late.append((A[m, 5] - (A[m, 0] + A[m, 1])).mean() if m.sum() > 30 else float("nan"))
            ok = b[1] > 1.1 and b[2] < 0.8
            ok2 = (late[3] >= 2.0) if not np.isnan(late[3]) else False
            cell_ok += ok
            cell_late += ok2
            print(f"  {f} {int(r * 100):2d}% (n={len(A):6d}): transfer {b[1]:.2f} wait {b[2]:.2f} {'[b>1.1, c<0.8]' if ok else '':16s} "
                  f"lateness by transfer <2/2-5/5-10/>10 s: " + " ".join(f"{x:+5.1f}" for x in late) + f"  {'[>=+2 s at >10 s]' if ok2 else ''}")
    print(f"\n  cells with b > 1.1 and c < 0.8: {cell_ok} of 6 (needs 4); cells with lateness >= +2 s at transfers over 10 s: {cell_late} of 6 (needs 4)")
    print(f"  mean rmse reduction over the two case splits: {np.mean(gains) * 100:.1f}% (needs 5%)")
    rep = np.mean(gains) >= 0.05 and cell_ok >= 4
    print("verdict M5 (re-weighted estimate):", "REPLICATES -> Gate 1 with pooled coefficients" if rep else "does NOT replicate -> dropped")
    print("verdict M2 (transit-aware):", "alive (lateness pattern holds)" if cell_late >= 4 else "dropped (lateness pattern does not hold)")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "run":
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 8)
    elif cmd == "check":
        check()
    else:
        rung_report()
        error_report()
