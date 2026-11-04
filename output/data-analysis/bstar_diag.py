"""Why did B* get worse under CAP-W1? Two diagnostic checks (2 Nov 2026, user request after the CAP-W1 light test).

Context: on 5 development cases ours is flat between CAP-U (one slot per container) and CAP-W1 (sized containers) while B*'s P99
rose in 4 of 5 (e.g. F1 50% s1: 191 -> 491 s). A count of annealing proposals (bstar_nofit_count.py) showed none rejected for
not fitting (21.7% redrawn), so the proposal rule does not explain it. Two candidates remain.

CHECK 2  start layout.  B* with annealing OFF (the NSGA-II start layout only, nothing adapts), under CAP-U and CAP-W1, on the two
         cases with the largest rise: F1 50% s1 and F1 70% s1.
         Reading, fixed now: if static P99 under CAP-W1 / under CAP-U is >= 1.5 on BOTH cases, the start layout is a main
         cause; if < 1.2 on both, it is not; otherwise inconclusive.
CHECK 3  noise.  B* with annealing, F1 50% s1, four runs per capacity model (the original and three other seeds that change
         the annealing draws and the execution-time draws; arrivals are fixed by the scenario), CAP-U and CAP-W1.
         Reading, fixed now: "within noise" if the CAP-U and CAP-W1 P99 ranges overlap; "beyond noise" if the smallest CAP-W1 P99
         exceeds the largest CAP-U P99.
Harness check: the CAP-U original-seed run must reproduce the stored d1_headroom B* event hash.

  python bstar_diag.py run [workers]   |   python bstar_diag.py report
"""
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
OUT = ROOT / "results" / "bstar_diag"
W1 = ROOT / "results" / "capW1_light"
D1 = ROOT / "results" / "d1_headroom"
DURATION, WARMUP = 900.0, 60.0
STATIC_CASES = ("F1_r0.5_s1", "F1_r0.7_s1")
NOISE_CASE, NOISE_OFFSETS = "F1_r0.5_s1", (0, 1000, 2000, 3000)


def jobs():
    out = []
    for tg in STATIC_CASES:
        for model in ("CAP-U", "CAP-W1"):
            out.append((model, tg, "static", 0))
    for off in NOISE_OFFSETS:
        for model in ("CAP-U", "CAP-W1"):
            if model == "CAP-W1" and off == 0:
                continue                                     # the stored light-test run is the original-seed CAP-W1 run
            out.append((model, NOISE_CASE, "sa", off))
    return out


def path(j):
    model, tg, mode, off = j
    return OUT / f"{model}_{tg}.{mode}.s{off}.json"


def run_job(j):
    model, tg, mode, off = j
    out = path(j)
    if out.exists():
        return str(out)
    try:
        import numpy as _np
        assert _np.__version__.startswith("1."), "run with the Anaconda interpreter (numpy 1.26)"
        import yaml
        from dfps.sim import Sim
        from dfps.variants import make_adjuster, sim_kwargs
        ASSUME = yaml.safe_load((ROOT / "config" / "assumptions.yaml").read_text(encoding="utf-8"))
        seed = int(tg.split("_s")[1])
        if model == "CAP-U":
            sc, X0 = pickle.load(open(D1 / f"{tg}.pkl", "rb")), pickle.load(open(D1 / f"{tg}.prep.pkl", "rb"))["X0"]
        else:
            P = pickle.load(open(W1 / f"{tg}.sc.pkl", "rb"))
            sc, X0 = P["sc"], P["X0"]
        kw = sim_kwargs("B_STAR", ASSUME)
        kw.update(warmup=WARMUP, duration=DURATION, retry_min_interval=1.0, retry_max_attempts=10)
        adj = None
        if mode == "sa":
            adj = make_adjuster("B_STAR", ASSUME, seed=seed + 300 + off)
            kw["interval"] = float(json.loads((D1 / f"{tg}.B_STAR.json").read_text())["period"])
        t0 = time.time()
        sim = Sim(sc, X0.copy(), adjuster=adj, seed=seed + 400 + off, **kw)
        r = sim.run()
        sim.check_invariants()
        r["wall_s"] = time.time() - t0
        OUT.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(dict(capacity_model=model, case=tg, mode=mode, seed_offset=off, result=r)))
    except Exception:
        import traceback
        OUT.mkdir(parents=True, exist_ok=True)
        out.with_suffix(".err").write_text(traceback.format_exc())
        return str(out) + " FAILED"
    return str(out)


def run(workers):
    todo = [j for j in jobs() if not path(j).exists()]
    print(f"{len(todo)} runs, {workers} workers", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        for r in ex.map(run_job, sorted(todo, key=lambda j: j[2] != "sa")):       # annealing runs first (they are the long ones)
            print("done", r, flush=True)


def load(j):
    p = path(j)
    if j[0] == "CAP-W1" and j[2] == "sa" and j[3] == 0:
        p = W1 / f"{j[1]}.B_STAR.json"
    elif j[0] == "CAP-U" and j[2] == "sa" and j[3] == 0 and not p.exists():
        return None
    return json.loads(p.read_text())["result"] if p.exists() else None


def report():
    print("=== check 2: static layout (annealing off), P99 s ===")
    ok2 = []
    for tg in STATIC_CASES:
        u, w = load(("CAP-U", tg, "static", 0)), load(("CAP-W1", tg, "static", 0))
        if u and w:
            ratio = w["p99_makespan"] / u["p99_makespan"]
            ok2.append(ratio)
            print(f"  {tg}: CAP-U {u['p99_makespan']:.0f}  CAP-W1 {w['p99_makespan']:.0f}  ratio {ratio:.2f}   (avg {u['avg_makespan']:.0f} -> {w['avg_makespan']:.0f})")
    if len(ok2) == len(STATIC_CASES):
        print("  reading:", "start layout is a main cause" if min(ok2) >= 1.5 else ("not the start layout" if max(ok2) < 1.2 else "inconclusive"))
    print("\n=== check 3: B* with annealing, " + NOISE_CASE + ", P99 s by seed offset ===")
    rows = {m: [] for m in ("CAP-U", "CAP-W1")}
    for m in rows:
        for off in NOISE_OFFSETS:
            r = load((m, NOISE_CASE, "sa", off))
            if r:
                rows[m].append(r["p99_makespan"])
                print(f"  {m:7s} offset {off:4d}: P99 {r['p99_makespan']:.0f}  avg {r['avg_makespan']:.0f}  cold {r['cold_starts']}")
    stored = json.loads((D1 / f"{NOISE_CASE}.B_STAR.json").read_text())["result"]
    u0 = load(("CAP-U", NOISE_CASE, "sa", 0))
    if u0:
        print(f"  harness check, CAP-U original seed vs stored d1_headroom run: event hash same = {u0['event_hash'] == stored['event_hash']}")
    if len(rows["CAP-U"]) == len(NOISE_OFFSETS) and len(rows["CAP-W1"]) == len(NOISE_OFFSETS):
        lo_w, hi_u = min(rows["CAP-W1"]), max(rows["CAP-U"])
        print(f"  CAP-U range {min(rows['CAP-U']):.0f}-{hi_u:.0f}; CAP-W1 range {lo_w:.0f}-{max(rows['CAP-W1']):.0f}")
        print("  reading:", "beyond noise" if lo_w > hi_u else ("within noise (ranges overlap)"))


if __name__ == "__main__":
    {"run": lambda: run(int(sys.argv[2]) if len(sys.argv) > 2 else 3), "report": report}[sys.argv[1]]()
