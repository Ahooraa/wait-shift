"""The two-loop 2x2 under CAP-W1 with the current controller (plan: knowledge/synthesis/independent-baselines-capw1.md, section 9, 7 Nov 2026).
Router transfer_only, gain-ordered moves (MV-3, event hashes equal MV-2), filled budget, FIFO queues; 900 s, warm-up 60 s.
  A fixed layout, no moves | B fixed layout, moves | C re-layout every 60 s, no moves | D re-layout + moves (FROZEN-3 without the criticality queue order)
  Aq, Cq  the two no-move cells with a queue-aware router (greedy_eft: input transfer + queue estimate), development cases
  X_L4    cell X with the 900 s trace repeated 4 times (3,600 s, same load), 6 development cases (seed 1)
Development cases seeds 1-3; held-out cases seeds 7-10 (cells A-D). New runs also record the mechanism (see mech()); the trace and the sampling do not change the dynamics.
  python capw1_grid.py run [workers] | status | report
Results: results/capW1_grid/{tag}.{cell}.json
"""
import copy
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
import capw1_rows as C  # noqa: E402

OUT = ROOT / "results" / "capW1_grid"
W1 = ROOT / "results" / "capW1_light"
DURATION, WARMUP = 900.0, 60.0
CELLS = {"A": dict(no_relayout=True, rebal=False), "B": dict(no_relayout=True, fast_order=True), "C": dict(rebal=False), "D": dict(fast_order=True),
         "Aq": dict(no_relayout=True, rebal=False), "Cq": dict(rebal=False)}
HELD = [f"{f}_r{r}_s{s}" for f in ("F1", "F2") for r in (0.5, 0.7, 0.85) for s in (7, 8, 9, 10)]
LONG = [c for c in C.dev() if c.endswith("_s1")]


def mech(sim, sc, ticks, tail_q=99.0):
    """Mechanism. Per tick: queued tasks split into stranded (an idle container of the SAME function exists on another node: what moves fix), wrong function (no idle container
    of that function, but idle containers of OTHER functions exist: what re-layout fixes; sizes ignored), and true shortage. Per request: time along its critical path split into
    wait in queue, execution, and the rest (mainly state transfer), for all requests and the slowest 1%."""
    a = np.array(ticks, dtype=float) if ticks else np.zeros((1, 5))
    q = max(1.0, float(a[:, 1].sum()))
    n = len(a)
    out = dict(queued_mean=float(a[:, 1].mean()), stranded=float(a[:, 2].sum() / q), wrong_function=float(a[:, 3].sum() / q), shortage=float(a[:, 4].sum() / q),
               queued_first_half=float(a[: n // 2, 1].mean()) if n > 1 else 0.0, queued_second_half=float(a[n // 2:, 1].mean()) if n > 1 else 0.0)
    wfs = {w.id: w for w in sc.workflows}
    by = {}
    for rid, wid, t, _p, _k, t_first, t_start, t_done, _m in sim.trace["tasks"]:
        by.setdefault(rid, (wid, {}))[1][t] = (t_first, t_start, t_done)
    arr = {rid: (wid, t0, t1) for rid, wid, t0, t1 in sim.trace["reqs"]}
    rows = []
    for rid, (wid, t0, t1) in arr.items():
        tasks, wf = by.get(rid, (wid, {}))[1], wfs[wid]
        if len(tasks) != wf.n:
            continue
        t = max(tasks, key=lambda x: tasks[x][2])
        w = e = 0.0
        while True:
            f, s, d = tasks[t]
            w += s - f
            e += d - s
            if not wf.parents[t]:
                break
            t = max(wf.parents[t], key=lambda p: tasks[p][2])
        rows.append((t1 - t0, w, e))
    if rows:
        r = np.array(rows)
        tail = r[r[:, 0] >= np.percentile(r[:, 0], tail_q)]
        for lab, x in (("all", r), ("tail", tail)):
            out[f"{lab}_makespan"], out[f"{lab}_wait"], out[f"{lab}_exec"] = float(x[:, 0].mean()), float(x[:, 1].mean()), float(x[:, 2].mean())
    return out


def run_job(args):
    tg, cell = args[0], args[1]
    out_dir = Path(args[2]) if len(args) > 2 else OUT
    out = out_dir / f"{tg}.{cell}.json"
    if out.exists():
        return str(out)
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        import yaml
        from dfps import dispatchers as D
        from dfps.o3s import O3SimAdjuster, backlog_per_function
        from dfps.sim import Sim
        from dfps.solution import IDLE
        from dfps.variants import make_adjuster, sim_kwargs
        from frozen2 import FROZEN3, FROZEN3_DISPATCHER, MOVE_PERIOD_S
        base, loop = (cell.split("_L")[0], int(cell.split("_L")[1])) if "_L" in cell else (cell, 1)
        A = yaml.safe_load((ROOT / "config" / "assumptions.yaml").read_text(encoding="utf-8"))
        P = pickle.load(open(W1 / f"{tg}.sc.pkl", "rb"))
        sc, X0 = P["sc"], P["X0"]
        assert sc.meta.get("capacity_model") == "CAP-W1"
        duration = DURATION * loop
        if loop > 1:
            sc = copy.copy(sc)
            sc.arrivals = [(t + i * DURATION, w, o) for i in range(loop) for t, w, o in P["sc"].arrivals]
        seed, fam = int(tg.split("_s")[1]), tg.split("_r")[0]
        kw = sim_kwargs("B_STAR", A)
        router = "greedy_eft" if base.endswith("q") else FROZEN3_DISPATCHER
        kw.update(warmup=WARMUP, duration=duration, retry_min_interval=1.0, retry_max_attempts=10, dispatcher=D.DISPATCHERS[router], trace=True)
        adj = O3SimAdjuster(make_adjuster("B_STAR", A, seed=seed + 300), MOVE_PERIOD_S[fam], epoch=60.0, horizon=30.0, K=8, seed=seed + 800,
                            warmup=WARMUP, blind=True, cand_mode="nosim", churn=dict(FROZEN3, lam=0.5, **CELLS[base]))
        kw["interval"] = adj.next_interval
        sim = Sim(sc, X0.copy(), adjuster=adj, seed=seed + 400, **kw)
        ticks, orig = [], adj.run

        def tracked(s, _o=orig):
            if WARMUP <= s.now < duration:
                Q = backlog_per_function(s)
                I = np.array([sum(1 for k in range(s.N) for i in s.inst[k][f] if i.state == IDLE and i.swap_to is None) for f in range(s.F)], dtype=float)
                st = np.minimum(Q, I)
                rest = float(Q.sum() - st.sum())
                wrong = min(rest, float((I - st).sum()))
                ticks.append((s.now, float(Q.sum()), float(st.sum()), wrong, rest - wrong))
            return _o(s)
        adj.run = tracked
        t0 = time.time()
        r = sim.run()
        sim.check_invariants()
        r["wall_s"] = time.time() - t0
        out.write_text(json.dumps(dict(capacity_model="CAP-W1", case=tg, cell=cell, router=router, queue="FIFO", duration=duration, mech=mech(sim, sc, ticks), result=r)))
    except Exception:
        import traceback
        out.with_suffix(".err").write_text(traceback.format_exc())
        return str(out) + " FAILED"
    return str(out)


def all_jobs():
    dev = C.dev()
    return ([(c, k) for k in ("Aq", "Cq") for c in dev] + [(c, f"{k}_L4") for k in "DCBA" for c in LONG] + [(c, k) for k in "DCBA" for c in HELD])


def run(workers):
    from capw1_independent import _low_priority
    jobs = [j for j in all_jobs() + [(c, k) for k in "DCBA" for c in C.dev()] if not (OUT / f"{j[0]}.{j[1]}.json").exists()]
    print(len(jobs), "runs", flush=True)
    with ProcessPoolExecutor(workers, initializer=_low_priority) as ex:
        for r in ex.map(run_job, jobs):
            print("done", r, flush=True)


def load(c, k):
    p = OUT / f"{c}.{k}.json"
    return json.loads(p.read_text()) if p.exists() else None


def res(c, k):
    j = load(c, k)
    return j["result"] if j else None


def ci(x, seed=0):
    x = np.asarray(x, float)
    rng = np.random.default_rng(seed)
    b = [x[rng.integers(0, len(x), len(x))].mean() for _ in range(10000)]
    return float(x.mean()), float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))


def f3_of(c):
    if int(c.split("_s")[1]) >= 7:
        p = C.OUT / f"{c}.frozen3.json"
        return json.loads(p.read_text())["result"] if p.exists() else None
    return C.frozen3(c)


def grid(cs, label):
    ok = [c for c in cs if all(res(c, k) for k in "ABCD")]
    print(f"\n=== {label}: {len(ok)} of {len(cs)} cases complete")
    if not ok:
        return
    L = {k: np.log([res(c, k)["p99_makespan"] for c in ok]) for k in "ABCD"}
    gm = {k: float(np.exp(L[k].mean())) for k in "ABCD"}
    print("P99 geometric mean (s): A fixed %.0f | B fixed+moves %.0f | C re-layout %.0f | D both %.0f" % (gm["A"], gm["B"], gm["C"], gm["D"]))

    def eff(a, b, lab):
        m, lo, hi = ci(L[a] - L[b])
        print(f"  {lab}: x{np.exp(m):.2f} [{np.exp(lo):.2f}, {np.exp(hi):.2f}], better in {int((L[a] > L[b]).sum())}/{len(ok)}")
    eff("A", "B", "moves on a fixed layout")
    eff("C", "D", "moves with re-layout")
    eff("A", "C", "re-layout without moves")
    eff("B", "D", "re-layout with moves")
    eff("A", "D", "both together")
    m, lo, hi = ci(L["A"] - L["B"] - L["C"] + L["D"])
    print(f"  log interaction {m:.2f} [{lo:.2f}, {hi:.2f}]; both together over the product of the separate effects: x{np.exp(-m):.2f}")
    for rho in ("0.5", "0.7", "0.85"):
        q = [i for i, c in enumerate(ok) if f"_r{rho}_" in c]
        print("  rho", rho, "P99 A %.0f B %.0f C %.0f D %.0f" % tuple(np.exp(L[k][q].mean()) for k in "ABCD"))
    f3 = {c: f3_of(c) for c in ok}
    if all(f3.values()):
        r = np.log([res(c, "D")["p99_makespan"] / f3[c]["p99_makespan"] for c in ok])
        a = np.log([res(c, "D")["avg_makespan"] / f3[c]["avg_makespan"] for c in ok])
        m, lo, hi = ci(r)
        print(f"Queue order: FIFO (D) over FROZEN-3 (criticality): P99 {np.exp(m):.3f} [{np.exp(lo):.3f}, {np.exp(hi):.3f}], FIFO lower in {int((r < 0).sum())}/{len(ok)}; mean makespan {np.exp(a.mean()):.3f}")
        for rho in ("0.5", "0.7", "0.85"):
            q = [i for i, c in enumerate(ok) if f"_r{rho}_" in c]
            print("  rho", rho, "FIFO / criticality P99 %.3f" % np.exp(r[q].mean()))
    mechs = {k: [load(c, k).get("mech") for c in ok] for k in "ABCD"}
    if all(all(v) for v in mechs.values()):
        print("Mechanism (mean over cases). Share of queued work per tick; critical-path time of the slowest 1% of requests (s):")
        for k in "ABCD":
            v = mechs[k]
            g = lambda n: float(np.mean([x[n] for x in v]))
            print(f"  {k}: queued {g('queued_mean'):8.0f} (first half {g('queued_first_half'):8.0f}, second {g('queued_second_half'):8.0f}) | stranded {g('stranded'):.2f} wrong-function {g('wrong_function'):.2f} shortage {g('shortage'):.2f} | tail makespan {g('tail_makespan'):7.0f} wait {g('tail_wait'):7.0f} exec {g('tail_exec'):5.0f} | all makespan {g('all_makespan'):6.0f} wait {g('all_wait'):6.0f} exec {g('all_exec'):5.0f}")


def report():
    print("errors:", len(list(OUT.glob("*.err"))))
    grid(C.dev(), "Development cases, seeds 1-3")
    grid(HELD, "Held-out cases, seeds 7-10")
    dev = C.dev()
    ok = [c for c in dev if res(c, "Aq") and res(c, "Cq") and res(c, "D")]
    if ok:
        print(f"\n=== Queue-aware router (greedy_eft) in the no-move cells, {len(ok)} development cases")
        for q, b in (("Aq", "A"), ("Cq", "C")):
            x = np.log([res(c, q)["p99_makespan"] for c in ok])
            d = np.log([res(c, b)["p99_makespan"] for c in ok])
            m, lo, hi = ci(d - x)
            m2, lo2, hi2 = ci(x - np.log([res(c, "D")["p99_makespan"] for c in ok]))
            print(f"  {q}: P99 {np.exp(x.mean()):.0f} s; better than transfer_only ({b}) by x{np.exp(m):.2f} [{np.exp(lo):.2f}, {np.exp(hi):.2f}]; still worse than D (both loops) by x{np.exp(m2):.2f} [{np.exp(lo2):.2f}, {np.exp(hi2):.2f}], D lower in {int((x > np.log([res(c, 'D')['p99_makespan'] for c in ok])).sum())}/{len(ok)}")
        for rho in ("0.5", "0.7", "0.85"):
            q = [c for c in ok if f"_r{rho}_" in c]
            print("  rho", rho, "P99 Aq %.0f Cq %.0f D %.0f" % tuple(np.exp(np.mean(np.log([res(c, k)["p99_makespan"] for c in q]))) for k in ("Aq", "Cq", "D")))
        L = {k: np.log([res(c, k)["p99_makespan"] for c in ok]) for k in ("Aq", "B", "Cq", "D")}
        m, lo, hi = ci(L["Aq"] - L["B"] - L["Cq"] + L["D"])
        print(f"  interaction with the queue-aware no-move cells: {m:.2f} [{lo:.2f}, {hi:.2f}]")
    ok = [c for c in LONG if all(res(c, f"{k}_L4") for k in "ABCD")]
    if ok:
        print(f"\n=== Run length, trace repeated to 3,600 s, {len(ok)} development cases (seed 1), same cases at 900 s beside it")
        L9 = {k: np.log([res(c, k)["p99_makespan"] for c in ok]) for k in "ABCD"}
        L4 = {k: np.log([res(c, f"{k}_L4")["p99_makespan"] for c in ok]) for k in "ABCD"}
        for k in "ABCD":
            print(f"  {k}: P99 900 s run {np.exp(L9[k].mean()):7.0f} s | 3,600 s run {np.exp(L4[k].mean()):7.0f} s | growth x{np.exp((L4[k] - L9[k]).mean()):.2f}")
        for lab, L in (("900 s", L9), ("3,600 s", L4)):
            m, lo, hi = ci(L["A"] - L["B"] - L["C"] + L["D"])
            print(f"  {lab}: both together x{np.exp((L['A'] - L['D']).mean()):.1f}; moves with re-layout x{np.exp((L['C'] - L['D']).mean()):.1f}; re-layout with moves x{np.exp((L['B'] - L['D']).mean()):.1f}; interaction {m:.2f} [{lo:.2f}, {hi:.2f}]")


if __name__ == "__main__":
    c = sys.argv[1]
    if c == "run":
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 4)
    elif c == "status":
        print({k: sum(res(x, k) is not None for x in HELD) for k in "ABCD"}, "held-out;", {k: sum(res(x, k) is not None for x in C.dev()) for k in ("Aq", "Cq")}, "dev;",
              {k: sum(res(x, f"{k}_L4") is not None for x in LONG) for k in "ABCD"}, "long; errors", len(list(OUT.glob("*.err"))))
    else:
        report()
