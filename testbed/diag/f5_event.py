"""Event-driven re-layout for F5 (pre-registered 16 Nov 2026, knowledge/synthesis/workflow-aware-decision-rules.md, "F5 + trigger-based grow and shrink
between re-layouts" and its amendment 1). Simulator twin, CAP-W2 weights, Azure arrivals, 10 nodes, development seeds 1-3 only.

    ~/venv-dfps/bin/python testbed/diag/f5_event.py run [workers]   |   report

Arms: frozen5_e0 (first re-layout at 10 s), frozen5_ev (event-driven re-layout + slow shrink), frozen5_ts (the 6 Nov trigger on top of F5, reference).
Cells: G1 the live cell (load 0.5, peak cap 300 tasks/s), G2 load 0.5 no cap (ML, MapReduce), G3 load 0.7 no cap, G4 load 0.9 no cap; 42 per arm.
F5 reference: the stored simulator runs for G2-G4 (~/testbed-results/sim-load-capw2), G1 re-run here with the current code.
Results: ~/testbed-results/sim-event/<group>/<app>.s<seed>.<arm>.json; a cell with a file is never run again. Readings E1-E5 (and T1-T5 for frozen5_ts) as registered.
"""
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
RES = Path.home() / "testbed-results"
OUT = RES / "sim-event"
APPS = ["690.ml", "660.map-reduce", "650.vid", "680.excamera"]
NAMES = {"690.ml": "ML", "660.map-reduce": "MapReduce", "650.vid": "Video", "680.excamera": "ExCamera"}
SEEDS = (1, 2, 3)
ARMS = ("frozen5_e0", "frozen5_ev", "frozen5_ts")
GROUPS = {"G1": (None, 300.0, APPS), "G2": (0.5, None, APPS[:2]), "G3": (0.7, None, APPS), "G4": (0.9, None, APPS)}     # (rho, peak cap, apps)
F5_STORED = {"G2": "sim-load-capw2/rho0.5-uncapped", "G3": "sim-load-capw2/rho0.7", "G4": "sim-load-capw2/rho0.9"}


def cells():
    return [(g, app, s) for g, (_, _, apps) in GROUPS.items() for app in apps for s in SEEDS]


def path(g, app, s, arm):
    if arm == "frozen5" and g in F5_STORED:
        return RES / F5_STORED[g] / f"{app}.s{s}.frozen5.json"
    return OUT / g / f"{app}.s{s}.{arm}.json"


def one(job):
    g, app, s, arm = job
    out = path(g, app, s, arm)
    if out.exists():
        return str(out), 0.0
    from testbed import sim_sweep as SW
    rho, cap, _ = GROUPS[g]
    t0 = time.time()
    r = SW.one((arm, app, s, 10, "memory", rho, cap, None))
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".part")
    tmp.write_text(json.dumps(r, default=float))
    tmp.replace(out)
    return str(out), time.time() - t0


def cost(job):
    """Expected run time, from F5's stored wall times (heavy cells first, so the long ones do not end up last)."""
    g, app, s, arm = job
    ref = path(g, app, s, "frozen5")
    try:
        return json.loads(ref.read_text())["wall_s"]
    except Exception:
        return 60.0 if app in ("690.ml", "660.map-reduce") else 5.0


def run(workers):
    jobs = [(g, app, s, arm) for (g, app, s) in cells() for arm in ARMS] + [(g, app, s, "frozen5") for (g, app, s) in cells() if g == "G1"]
    todo = sorted((j for j in jobs if not path(*j).exists()), key=cost, reverse=True)
    print(f"{len(todo)} runs to do of {len(jobs)}, {workers} workers", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        futs = {ex.submit(one, j): j for j in todo}
        for i, fu in enumerate(as_completed(futs), 1):
            j = futs[fu]
            try:
                p, w = fu.result()
                print(f"{time.strftime('%H:%M:%S')} done {i}/{len(todo)} {'.'.join(map(str, j))} in {w:.0f} s", flush=True)
            except Exception as e:
                print(f"{time.strftime('%H:%M:%S')} FAILED {'.'.join(map(str, j))}: {e!r}", flush=True)
    print("ALL-DONE", flush=True)


def load(g, app, s, arm):
    return json.loads(path(g, app, s, arm).read_text())


def gm_ci(x, rng):
    lx = np.log(x)
    bs = np.array([rng.choice(lx, len(lx)).mean() for _ in range(10000)])
    return float(np.exp(lx.mean())), float(np.exp(np.percentile(bs, 2.5))), float(np.exp(np.percentile(bs, 97.5)))


def report():
    rng = np.random.default_rng(0)
    summary = {}
    for arm in ARMS:
        rows = []
        for (g, app, s) in cells():
            a, b = load(g, app, s, "frozen5"), load(g, app, s, arm)
            rel = b.get("relayout") or {}
            trig = b.get("trigger") or {}
            ctrl_s = float(rel.get("decide_total_s", 0.0)) + (float(trig.get("time_total_s", 0.0)) if arm == "frozen5_ts" else 0.0)
            rows.append(dict(g=g, app=app, s=s, r99=b["p99_makespan"] / a["p99_makespan"], r50=b["p50_makespan"] / a["p50_makespan"],
                             ravg=b["avg_makespan"] / a["avg_makespan"], cold_f5=a["cold_starts"], cold=b["cold_starts"], p99_f5=a["p99_makespan"], p99=b["p99_makespan"],
                             event=rel.get("event"), scheduled=rel.get("scheduled"), check_p99_ms=rel.get("check_p99_ms"), trig_p99_ms=trig.get("time_p99_ms"),
                             share=ctrl_s / max(b["wall_s"], 1e-9), unf=b["n_unfinished"]))
        print(f"\n===== {arm} against F5 =====")
        print(f"{'cell':26}{'F5 P99':>9}{'P99':>9}{'ratio':>7}{'P50 r':>7}{'avg r':>7}{'cold F5':>8}{'cold':>7}{'events':>7}{'ctrl %':>7}")
        for r in rows:
            print(f"{r['g'] + ' ' + NAMES[r['app']] + ' s' + str(r['s']):26}{r['p99_f5']:9.2f}{r['p99']:9.2f}{r['r99']:7.3f}{r['r50']:7.3f}{r['ravg']:7.3f}"
                  f"{r['cold_f5']:8d}{r['cold']:7d}{str(r['event'] if r['event'] is not None else '-'):>7}{100 * r['share']:7.2f}")
        e1 = gm_ci(np.array([r["r99"] for r in rows if r["g"] != "G1"]), rng)
        e2 = gm_ci(np.array([r["r99"] for r in rows if r["g"] == "G1"]), rng)
        e1v = "BETTER" if e1[2] <= 0.97 else "WORSE" if e1[1] >= 1.03 else "NO DETECTABLE CHANGE"
        per_app = {}
        for app in APPS:
            x = [r for r in rows if r["app"] == app]
            g_app = float(np.exp(np.mean(np.log([r["r99"] for r in x]))))
            c5, c = np.mean([r["cold_f5"] for r in x]), np.mean([r["cold"] for r in x])
            per_app[NAMES[app]] = dict(gm=g_app, cold_f5=float(c5), cold=float(c), ok=bool(g_app <= 1.03 and (c <= 1.25 * c5 or c <= c5 + 50)))
        e3 = all(v["ok"] for v in per_app.values())
        chk = [r["check_p99_ms"] for r in rows if r["check_p99_ms"] is not None]
        e5_check = (max(chk) if chk else 0.0)
        e5_share = max(r["share"] for r in rows)
        cold_all = (sum(r["cold"] for r in rows), sum(r["cold_f5"] for r in rows))
        if arm == "frozen5_ts":
            tp = max(r["trig_p99_ms"] or 0.0 for r in rows)
            e5 = bool(tp <= 10.0 and e5_share <= 0.02 and cold_all[0] <= 1.25 * cold_all[1])
            cost_txt = f"trigger check p99 max {tp:.2f} ms (limit 10), control time share max {100 * e5_share:.2f}% (limit 2%), cold starts {cold_all[0]} vs F5 {cold_all[1]} (limit x1.25)"
        else:
            e5 = bool(e5_check <= 1.0 and e5_share <= 0.02)
            cost_txt = f"event check p99 max over cells {e5_check:.3f} ms (limit 1), control time share max {100 * e5_share:.2f}% (limit 2%)"
        verdict = e1v == "BETTER" and e2[2] <= 1.02 and e3 and e5
        print(f"E1 (G2-G4, 30 cells): GM {e1[0]:.3f} [{e1[1]:.3f}, {e1[2]:.3f}] -> {e1v}; median cell {np.median([r['r99'] for r in rows if r['g'] != 'G1']):.3f}")
        for g in ("G2", "G3", "G4"):
            x = np.array([r["r99"] for r in rows if r["g"] == g])
            print(f"     {g}: GM {np.exp(np.log(x).mean()):.3f}, better in {(x < 1).sum()}/{len(x)}")
        for key, lab in (("ravg", "average"), ("r50", "P50")):              # reported, not part of the rule (as registered)
            x, y = np.array([r[key] for r in rows if r["g"] != "G1"]), np.array([r[key] for r in rows if r["g"] == "G1"])
            print(f"     {lab} makespan (reported): G2-G4 GM {np.exp(np.log(x).mean()):.3f}, better in {(x < 1).sum()}/{len(x)}; G1 GM {np.exp(np.log(y).mean()):.3f}")
        print(f"E2 (G1, live cell, 12 cells): GM {e2[0]:.3f} [{e2[1]:.3f}, {e2[2]:.3f}] -> {'met' if e2[2] <= 1.02 else 'NOT met'} (CI upper <= 1.02)")
        print("E3 per application: " + "; ".join(f"{k} GM {v['gm']:.3f}, cold {v['cold_f5']:.0f} -> {v['cold']:.0f} {'ok' if v['ok'] else 'NOT ok'}" for k, v in per_app.items()))
        print(f"E5 cost: {cost_txt} -> {'met' if e5 else 'NOT met'}")
        print(f"VERDICT {arm}: {'CANDIDATE' if verdict else 'not a candidate'}")
        summary[arm] = dict(e1=e1, e1v=e1v, e2=e2, per_app=per_app, e5=e5, verdict=verdict, rows=rows)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "report.json").write_text(json.dumps(summary, default=float, indent=1))


if __name__ == "__main__":
    if sys.argv[1] == "one":                                              # one cell, for the laptops: one G APP SEED ARM
        print(one((sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5])))
    elif sys.argv[1] == "run":
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 9)
    else:
        report()
