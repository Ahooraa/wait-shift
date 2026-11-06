"""Held-out independent comparison under CAP-W1 (protocol frozen in knowledge/synthesis/independent-baselines-capw1.md, section 6, 5 Nov 2026).
F1/F2 x rho 0.5/0.7/0.85 x seeds 7-10 = 24 cases, nine arms:
  frozen3, stack (capw1_rows), B_STAR, RL (capw1_light), faaspr (1,500 paths), faaspr_rs, ga_p, heft_p, ga_s, heft_s (capw1_independent).
Results: frozen3/stack in results/capW1_rows, B_STAR/RL in results/capW1_light, the rest in results/capW1_independent. Resumable: unreadable
(half-written) result files are removed first.   python capw1_heldout.py run [workers] | status | report
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import capw1_independent as I  # noqa: E402

SEEDS = (7, 8, 9, 10)
ROWS, LIGHT = I.ROOT / "results" / "capW1_rows", I.ROOT / "results" / "capW1_light"
ORDER = ("faaspr", "faaspr_rs", "frozen3", "stack", "B_STAR", "RL", "ga_p", "heft_p", "ga_s", "heft_s",
         "ga_p2", "heft_p2", "ga_s2", "heft_s2")      # the last four: v2 tie-break (added 5 Nov 2026 after the audit); v1 results are kept
FP_PATHS = 1500


def path_of(tg, arm):
    d = ROWS if arm in ("frozen3", "stack") else LIGHT if arm in ("B_STAR", "RL") else I.OUT
    return d / f"{tg}.{arm}.json"


def job(spec):
    tg, arm = spec
    if arm in ("frozen3", "stack"):
        import capw1_rows as R
        return R.run_job((tg, arm))
    if arm in ("B_STAR", "RL"):
        import capw1_light as L
        return L.run_job((tg, arm, L.DURATION))
    return I.run_job((tg, arm, I.DURATION, str(I.OUT), FP_PATHS))


def clean():
    n = 0
    for arm in ORDER:
        for tg in I.tags(SEEDS):
            p = path_of(tg, arm)
            if p.exists():
                try:
                    json.loads(p.read_text())
                except Exception:
                    p.unlink()
                    n += 1
    return n


def todo():
    return [(tg, arm) for arm in ORDER for tg in I.tags(SEEDS) if not path_of(tg, arm).exists()]


def run(workers):
    print("removed unreadable results:", clean(), flush=True)
    t = todo()
    print(len(t), "runs to do of", len(ORDER) * 24, flush=True)
    with ProcessPoolExecutor(workers, initializer=I._low_priority) as ex:
        for r in ex.map(job, t):
            print("done", r, flush=True)


def status():
    for arm in ORDER:
        n = sum(path_of(tg, arm).exists() for tg in I.tags(SEEDS))
        e = sum(path_of(tg, arm).with_suffix(".err").exists() for tg in I.tags(SEEDS))
        print(f"{arm:10s} {n:2d}/24 done, {e} errors")


def result(tg, arm):
    p = path_of(tg, arm)
    return json.loads(p.read_text())["result"] if p.exists() else None


def gm_ci(x, seed=0):
    x = np.log(np.asarray(x, float))
    rng = np.random.default_rng(seed)
    bs = [x[rng.integers(0, len(x), len(x))].mean() for _ in range(10000)]
    lo, hi = np.exp(np.percentile(bs, [2.5, 97.5]))
    return float(np.exp(x.mean())), float(lo), float(hi)


def report():
    cs = I.tags(SEEDS)
    print("Held-out CAP-W1, seeds 7-10. P99 makespan ratio system / FROZEN-3 (geometric mean [95% bootstrap CI over case log-ratios], wins of FROZEN-3)")
    print(f"{'system':10s} {'cases':>5s} {'all':>26s} {'rho 0.5':>8s} {'rho 0.7':>8s} {'rho 0.85':>8s}   mean P99 (s)")
    for arm in ORDER:
        if arm == "frozen3":
            continue
        rows = [(c, result(c, arm), result(c, "frozen3")) for c in cs]
        rows = [(c, a, f) for c, a, f in rows if a and f]
        if not rows:
            continue
        r = [a["p99_makespan"] / f["p99_makespan"] for _, a, f in rows]
        g = gm_ci(r)
        per = []
        for rho in ("0.5", "0.7", "0.85"):
            q = [x for (c, _, _), x in zip(rows, r) if f"_r{rho}_" in c]
            per.append(f"{np.exp(np.mean(np.log(q))):8.2f}" if q else f"{'-':>8s}")
        print(f"{arm:10s} {len(rows):5d} {g[0]:8.2f} [{g[1]:6.2f}, {g[2]:6.2f}] {sum(x > 1 for x in r):2d}/{len(r)} " + " ".join(per) + f"   {np.mean([a['p99_makespan'] for _, a, _ in rows]):8.1f}")
    f3 = [result(c, "frozen3") for c in cs]
    f3 = [x for x in f3 if x]
    if f3:
        print(f"{'frozen3':10s} {len(f3):5d} {'':26s} {'':8s} {'':8s} {'':8s}   {np.mean([x['p99_makespan'] for x in f3]):8.1f}")
    print("\nFaaSPR health (in-run counters; printed with every table): LP slack share, repaired requests, unplannable requests, parked")
    for arm in ("faaspr", "faaspr_rs"):
        h = []
        for c in cs:
            p = path_of(c, arm)
            if p.exists():
                j = json.loads(p.read_text()); i = j["info"]; w = i["window"]
                lg = [x for x in i["solve_log"] if x[0] < I.DURATION]
                h.append((sum(x[2] for x in lg) / max(1, sum(x[1] for x in lg)), w["rep_req"] / max(1, w["pure"] + w["rep_req"]),
                          w["unplanned"] / max(1, w["arrived"]), j["result"]["n_parked"] / max(1, j["result"]["n_arrived"])))
        if h:
            m = np.mean(h, axis=0)
            print(f"{arm:10s} {len(h)} cases: slack LPs {m[0]:.2f}, repaired requests {m[1]:.2f}, unplannable {m[2]:.2f}, parked/arrived {m[3]:.2f}")


if __name__ == "__main__":
    {"run": lambda: run(int(sys.argv[2]) if len(sys.argv) > 2 else 4), "status": status, "report": report}[sys.argv[1]]()
