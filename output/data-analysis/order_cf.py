"""Mover pass order and early stop: counterfactual Gate 0 (CAP-W1, MV-2; pre-registered 4 Nov 2026 in
knowledge/synthesis/workflow-aware-decision-rules.md, "Mover pass order and early stop"). Logging only: on every 4th pass
O3SimAdjuster._order_cf replays the pass on copies under V0 (current), V1 (no early stop), V2 (wait order), V3 (gain order);
the real pass runs unchanged. 18 development cases, FROZEN-2 + transfer_only dispatcher; each run must equal the stored
results/capW1_align_transfer_only run field by field (probe inert), and V0 must reproduce the real pass's moves.
  python order_cf.py run [workers] | report
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
OUT = ROOT / "results" / "order_cf"
W1 = ROOT / "results" / "capW1_light"
REF = ROOT / "results" / "capW1_align_transfer_only"
DURATION, WARMUP = 900.0, 60.0
SKIP = ("wall_s", "mover_impl")


def cases():
    return [f"{f}_r{r}_s{s}" for f in ("F1", "F2") for r in (0.5, 0.7, 0.85) for s in (1, 2, 3)]


def run_job(tg):
    out = OUT / f"{tg}.json"
    if out.exists():
        return str(out)
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        import numpy as _np
        assert _np.__version__.startswith("1."), "run with the Anaconda interpreter (numpy 1.26)"
        import yaml
        from dfps import dispatchers as D
        from dfps.dispatch_priority import QueuePriority
        from dfps.o3s import O3SimAdjuster
        from dfps.sim import Sim
        from dfps.variants import make_adjuster, sim_kwargs
        from frozen2 import FROZEN2, MOVE_PERIOD_S
        A = yaml.safe_load((ROOT / "config" / "assumptions.yaml").read_text(encoding="utf-8"))
        P = pickle.load(open(W1 / f"{tg}.sc.pkl", "rb"))
        sc, X0 = P["sc"], P["X0"]
        seed, fam = int(tg.split("_s")[1]), tg.split("_r")[0]
        kw = sim_kwargs("B_STAR", A)
        kw.update(warmup=WARMUP, duration=DURATION, retry_min_interval=1.0, retry_max_attempts=10, dispatcher=D.DISPATCHERS["transfer_only"])
        kw["queue_priority"] = QueuePriority("full", aging=2.0)
        adj = O3SimAdjuster(make_adjuster("B_STAR", A, seed=seed + 300), MOVE_PERIOD_S[fam], epoch=60.0, horizon=30.0, K=8,
                            seed=seed + 800, warmup=WARMUP, blind=True, cand_mode="nosim",
                            churn=dict(FROZEN2, lam=0.5, log_order_cf=True, order_cf_every=4))
        kw["interval"] = adj.next_interval
        t0 = time.time()
        sim = Sim(sc, X0.copy(), adjuster=adj, seed=seed + 400, **kw)
        r = sim.run()
        sim.check_invariants()
        r["wall_s"] = time.time() - t0
        ref = json.loads((REF / f"{tg}.json").read_text())["result"]
        diff = [k for k in ref if k not in SKIP and "_ms" not in k and r.get(k) != ref[k]]
        out.write_text(json.dumps(dict(capacity_model="CAP-W1", case=tg, mover_impl=r.get("mover_impl"), identical_to_ref=not diff,
                                       diff_fields=diff, log=getattr(adj, "order_cf_log", []), wall_s=r["wall_s"])))
    except Exception:
        import traceback
        out.with_suffix(".err").write_text(traceback.format_exc())
        return str(out) + " FAILED"
    return str(out)


def run(workers):
    todo = [c for c in cases() if not (OUT / f"{c}.json").exists()]
    todo.sort(key=lambda c: -float(c.split("_r")[1].split("_")[0]))
    print(len(todo), "runs", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        for r in ex.map(run_job, todo):
            print("done", r, flush=True)


def report():
    cells, ok_all, match = {}, True, [0, 0]
    for tg in cases():
        p = OUT / f"{tg}.json"
        if not p.exists():
            continue
        x = json.loads(p.read_text())
        ok_all &= x["identical_to_ref"]
        if not x["identical_to_ref"]:
            print(tg, "NOT identical to reference:", x["diff_fields"][:6])
        cell = tg.rsplit("_s", 1)[0]
        c = cells.setdefault(cell, dict(n=0, st=np.zeros(3), V={m: np.zeros(4) for m in ("V0", "V1", "V2", "V3")}, diffden={m: 0 for m in ("V1", "V2", "V3")}))
        for e in x["log"]:
            if not (WARMUP <= e["t"] < DURATION):                    # measured window only (the drain after DURATION is not measured)
                continue
            match[0] += e["real_match"]
            match[1] += 1
            c["n"] += 1
            c["st"] += [e["storage"]["evals"], e["storage"]["blocked_any"], e["storage"]["blocked_changed"]]
            for m in c["V"]:
                c["V"][m] += e[m]                                   # moves, gain, common with V0, distinct moves
            for m in c["diffden"]:
                c["diffden"][m] += max(e["V0"][3], e[m][3])
    print(f"probe inert (all runs identical to reference): {ok_all}; V0 reproduces the real pass: {match[0]}/{match[1]} sampled passes")
    passes = {m: 0 for m in ("V1", "V2", "V3")}
    for cell, c in cells.items():
        v0 = c["V"]["V0"]
        ev, ba, bc = c["st"]
        print(f"\n{cell}: {c['n']} sampled passes, V0 {v0[0] / max(c['n'], 1):.1f} moves/pass; storage: some host blocked {ba / max(ev, 1) * 100:.2f}% of "
              f"evaluations, storage changed the decision {bc / max(ev, 1) * 100:.3f}%")
        for m in ("V1", "V2", "V3"):
            v = c["V"][m]
            dshare = 1 - v[2] / max(c["diffden"][m], 1)
            mr, gr = v[0] / max(v0[0], 1), v[1] / max(v0[1], 1e-9)
            go = dshare >= 0.05 and gr >= 1.05
            passes[m] += go
            print(f"  {m}: moves differ {dshare * 100:5.1f}%  moves ratio {mr:.3f}  est. gain ratio {gr:.3f}  {'PASS' if go else ''}")
    print("\ncells passing (need >= 4 of 6):", {m: f"{n}/{len(cells)}" for m, n in passes.items()},
          "->", {m: ("to online run" if n >= 4 else "dead") for m, n in passes.items()},
          "" if len(cells) == 6 and sum(1 for c in cases() if (OUT / f"{c}.json").exists()) == 18 else "(partial)")


if __name__ == "__main__":
    {"run": lambda: run(int(sys.argv[2]) if len(sys.argv) > 2 else 6), "report": report}[sys.argv[1]]()
