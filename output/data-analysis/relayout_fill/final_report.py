"""Oracle headroom on the 42 cases, and the scale test."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import sim_pl5 as S
import scale_run as SR

MET = ("p99_makespan", "p95_makespan", "p50_makespan", "avg_makespan", "cold_starts", "n_moved", "mean_containers")


def val(c, arm, s, m):
    return (S.base(c, s) if arm == "frozen3i" else S.new(c, arm, s))[m]


print("===== ORACLE: every server can always fit one more largest container, same container budget, one-at-a-time fill, no leftover stage")
for lab, cs in (("all 42", S.cases("dev") + S.cases("heldout")), ("heldout 24", S.cases("heldout")), ("dev 18", S.cases("dev"))):
    print(f" -- {lab}")
    for a, b, t in (("oracle1", "ratio1", "oracle / one-at-a-time (remaining headroom)"), ("oracle1", "frozen3i", "oracle / PL-4")):
        print(f"  {t}")
        for m in MET:
            r = np.array([np.exp(np.mean(np.log([(val(c, a, s, m) + 1e-9) / (val(c, b, s, m) + 1e-9) for s in S.CLOCK]))) for c in cs])
            g, lo, hi = S.gm_ci(r)
            print(f"    {m:18s} {g:.3f} [{lo:.3f}, {hi:.3f}]  median case {np.median(r):.3f}  better/worse {int((r < 1).sum())}/{int((r > 1).sum())}")

print("\n===== SCALE: ratio to PL-4, per seed, geometric mean over seeds")
for budget, name in (("", "on-demand"), ("fixed", "fixed-budget")):
    print(f" -- {name}")
    pool = {"5": {m: [] for m in ("p99_makespan", "avg_makespan", "cold_starts")}, "6": {m: [] for m in ("p99_makespan", "avg_makespan", "cold_starts")}}
    for n, f, w in SR.SIZES:
        for fast, lab in (("5", "PL-5 one-at-a-time"), ("6", "PL-5p 8-pass")):
            R = {m: [] for m in ("p99_makespan", "avg_makespan", "cold_starts")}
            comp, tl, tm, tf, seeds = [], [], [], [], 0
            for seed in range(1, 6):
                pa, pb = SR.path("4", budget, n, f, w, seed), SR.path(fast, budget, n, f, w, seed)
                if not (pa.exists() and pb.exists()):
                    continue
                a, b = json.loads(pa.read_text()), json.loads(pb.read_text())
                if not (a.get("done") and b.get("done")):
                    continue
                seeds += 1
                for m in R:
                    R[m].append(b[m] / a[m]); pool[fast][m].append(b[m] / a[m])
                comp.append(b["n_completed"] / a["n_completed"]); tl.append(b["relayout_later"]["median"]); tm.append(b["move"]["p99"]); tf.append(b["relayout"]["max"])
            if seeds:
                print(f"  N{n} F{f} {lab:20s} seeds {seeds} | P99 {np.exp(np.mean(np.log(R['p99_makespan']))):.3f} (better in {sum(x < 1 for x in R['p99_makespan'])}/{seeds})  mean {np.exp(np.mean(np.log(R['avg_makespan']))):.3f} (better in {sum(x < 1 for x in R['avg_makespan'])}/{seeds})  cold {np.exp(np.mean(np.log(R['cold_starts']))):.3f} | completed ratio {np.mean(comp):.3f} | re-layout later median {np.median(tl):7.0f} ms, max incl. first {max(tf):7.0f} ms, move p99 {np.median(tm):6.0f} ms")
    for fast, lab in (("5", "PL-5 one-at-a-time"), ("6", "PL-5p 8-pass")):
        for m, v in pool[fast].items():
            if v:
                g, lo, hi = S.gm_ci(v)
                print(f"  ALL sizes {lab:20s} {m:14s} {g:.3f} [{lo:.3f}, {hi:.3f}]  n={len(v)}  better/worse {sum(x < 1 for x in v)}/{sum(x > 1 for x in v)}")
