"""Request-move mechanism, gap diagnosis step 3: logging for M1 (tail-aware comparison) and M4 (gain-ordered pass).
18 development cases, config D of grid2x2_v2.py, logging only (event hash must equal the stored D run). churn["log_move_ctx"] logs, for
every decision of every 4th rebalance pass: the request's function, mean run time, position in its queue and containers at the current
node, the estimate's parts (input transfer, service estimate, downstream transfer) at the current node and at every evaluated
candidate with that candidate's queue length and container count, and the accepted destination.

  python move_ctx_probe.py run [workers]    18 logging runs (resumable)
  python move_ctx_probe.py check            logging runs identical to the stored D runs?
  python move_ctx_probe.py report           Gate 0 for M1 and M4 (pre-registered in workflow-aware-decision-rules.md)
"""
import gzip
import json
import pickle
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
import move_gap_probe as mg  # noqa: E402

CTX = ROOT / "results" / "move_ctx"
LAM = 0.5


def job(args):
    tg, seed, family = args
    out = CTX / f"{tg}.pkl.gz"
    if out.exists():
        return str(out)
    CTX.mkdir(parents=True, exist_ok=True)
    try:
        import yaml
        assert np.__version__.startswith("1."), "run with the Anaconda interpreter (numpy 1.26)"
        import d3s_headroom as d
        from frozen2 import FROZEN2, MOVE_PERIOD_S
        from dfps.dispatch_priority import QueuePriority
        from dfps.o3s import O3SimAdjuster
        from dfps.sim import Sim
        from dfps.variants import make_adjuster, sim_kwargs
        ASSUME = yaml.safe_load((ROOT / "config" / "assumptions.yaml").read_text(encoding="utf-8"))
        sc = pickle.load(open(d.D1 / f"{tg}.pkl", "rb"))
        P = pickle.load(open(d.D1 / f"{tg}.prep.pkl", "rb"))
        kw = sim_kwargs("B_STAR", ASSUME)
        kw.update(warmup=d.WARMUP, duration=d.DURATION, retry_min_interval=1.0, retry_max_attempts=10)
        kw["queue_priority"] = QueuePriority("full", aging=2.0)
        churn = dict(FROZEN2, lam=LAM, log_move_ctx=True)
        adj = O3SimAdjuster(make_adjuster("B_STAR", ASSUME, seed=seed + 300), MOVE_PERIOD_S[family], epoch=60.0, horizon=30.0, K=8,
                            seed=seed + 800, warmup=d.WARMUP, blind=True, cand_mode="nosim", churn=churn)
        kw["interval"] = adj.next_interval
        sim = Sim(sc, P["X0"].copy(), adjuster=adj, seed=seed + 400, **kw)
        t0 = time.time()
        res = sim.run()
        sim.check_invariants()
        with gzip.open(out, "wb") as fh:
            pickle.dump(dict(case=tg, event_hash=res["event_hash"], p99=res["p99_makespan"], log=adj.ctx_log, wall_s=time.time() - t0), fh)
    except Exception:
        import traceback
        out.with_suffix(".err").write_text(traceback.format_exc())
        return str(out) + " FAILED"
    return str(out)


def run(workers):
    todo = [(pe.tag(f, r, s), s, f) for f, r, s in mg.cases() if not (CTX / f"{pe.tag(f, r, s)}.pkl.gz").exists()]
    print(f"{len(todo)} runs, {workers} workers", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        for r in ex.map(job, todo):
            print("done", r, flush=True)


def load():
    out = {}
    for f in sorted(CTX.glob("*.pkl.gz")):
        with gzip.open(f, "rb") as fh:
            x = pickle.load(fh)
        out[x["case"]] = x
    return out


def check():
    ref = {}
    for f in pe.T1_REF.glob("*.D.json"):
        x = json.loads(f.read_text())
        ref[(x["family"], x["rho"], x["seed"])] = x["result"]
    same = tot = 0
    for tg, x in load().items():
        fam, rho, seed = tg.split("_r")[0], float(tg.split("_r")[1].split("_s")[0]), int(tg.split("_s")[1])
        r = ref[(fam, rho, seed)]
        tot += 1
        ok = x["event_hash"] == r["event_hash"] and x["p99"] == r["p99_makespan"]
        same += ok
        if not ok:
            print("DIFFERENT:", tg)
    print(f"logging runs identical to the stored D runs (event hash and P99): {same} of {tot}")


def score(parts, lam=LAM):
    inp, svc, out = parts
    return inp + svc + lam * out


def sd_model(mu, ahead, cnt, c):
    """Std of the wait for a request with `ahead` requests in front of it served by `cnt` containers: each container serves about
    ahead/cnt requests before it, run times with coefficient of variation c -> c * mu * sqrt(ahead / cnt). Plus one own run time."""
    return c * mu * np.sqrt(np.maximum(ahead, 0) / np.maximum(cnt, 1) + 1.0)


def flips(logs, z, c):
    """Fraction of decisions whose chosen action changes if each location is scored by mean + z * sd of its start time."""
    n = ch = ch_move = n_move = 0
    for x in logs:
        for (_, _, f, mu, a0, c0, p0, cands, best) in x["log"]:
            if not cands:
                continue
            s0 = score(p0) + z * sd_model(mu, a0, c0, c)
            sc = [(score(p) + z * sd_model(mu, a2, c2, c), k2) for k2, p, a2, c2 in cands]
            m = min(sc)
            new = m[1] if m[0] < s0 else None
            n += 1
            ch += new != best
            if best is not None:
                n_move += 1
                ch_move += new != best
    return n, ch / max(n, 1), n_move, ch_move / max(n_move, 1)


def report():
    logs = list(load().values())
    print(f"=== {len(logs)} cases, {sum(len(x['log']) for x in logs)} logged decisions ===")
    # sd calibration from the step-2 logs: residual of the realised time to start around the predicted (inp + wait), by ahead/cnt
    rows = mg.rows_by_case()
    A = np.vstack(list(rows.values()))   # transfer, wait, mu, ql, cn, realised, t
    pred = A[:, 0] + A[:, 1]
    res = A[:, 5] - pred
    ratio = A[:, 3] / np.maximum(A[:, 4], 1)
    print("\ncalibration of the wait spread (step-2 moved requests): sd of (realised - predicted) / mu by queue length per container")
    print(f"{'ql/cn':>10s} {'n':>8s} {'sd/mu':>7s} {'model sqrt(r+1)':>16s}")
    edges = [0, 0.5, 1, 2, 4, 8, 1e9]
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (ratio >= lo) & (ratio < hi)
        if m.sum() > 50:
            print(f"{lo:4.1f}-{min(hi, 99):4.1f} {m.sum():8d} {np.std(res[m] / A[m, 2]):7.2f} {np.sqrt(ratio[m].mean() + 1):16.2f}")
    # coefficient c = sd of (res/mu) over sqrt(r+1) pooled
    c = float(np.std(res / A[:, 2] / np.sqrt(ratio + 1)))
    print(f"pooled c (sd/mu per sqrt(ql/cn + 1)) = {c:.2f}")
    print("\n=== M1 Gate 0: flip rate of the chosen action if locations are scored by mean + z * sd (all decisions / decisions that moved) ===")
    for z in (0.5, 1.0):
        n, f1, nm, f2 = flips(logs, z, c)
        print(f"z={z}: {n} decisions, flip {f1 * 100:.1f}% overall, {f2 * 100:.1f}% of the {nm} moves")
    # M4: pass structure
    print("\n=== M4 Gate 0: structure of a pass (sampled passes) ===")
    npass = nmov_tot = multi = same_dest = 0
    gains_order = []
    for x in logs:
        by = {}
        for (p, t, f, mu, a0, c0, p0, cands, best) in x["log"]:
            if best is None:
                continue
            g = score(p0) - min(score(pp) for k2, pp, _, _ in cands if k2 == best)
            by.setdefault(p, []).append((f, best, g))
        for p, mv in by.items():
            npass += 1
            nmov_tot += len(mv)
            if len(mv) >= 2:
                multi += 1
                same_dest += len({(f, k2) for f, k2, _ in mv}) < len(mv)
                g = np.array([m[2] for m in mv])
                if np.std(g) > 0:
                    gains_order.append(np.corrcoef(np.arange(len(g)), g)[0, 1])
    print(f"passes with moves: {npass}; moves per such pass {nmov_tot / max(npass, 1):.1f}; passes with >=2 moves {multi / max(npass, 1) * 100:.0f}%; "
          f"of those, with two moves into the same (function, node) queue {same_dest / max(multi, 1) * 100:.0f}%")
    if gains_order:
        print(f"correlation between processing order and gain within a pass: mean {np.mean(gains_order):+.2f} "
              f"(negative = earlier moves in a pass have the larger gain, i.e. the order is already roughly gain-descending)")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "run":
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 10)
    elif cmd == "check":
        check()
    else:
        report()
