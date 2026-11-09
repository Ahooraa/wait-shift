"""Where does the gain come from? 2 x 2 of fill order (best gain / furthest below target) by leftover rule (best gain / furthest below target), plus the passes.
Every contrast is paired clock by clock; geometric mean over cases, 95% case bootstrap."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import sim_pl5 as S

MET = ("p99_makespan", "p95_makespan", "p50_makespan", "avg_makespan", "cold_starts", "n_moved", "mb_relocated", "mean_containers", "slo_ok")


def val(c, arm, s, m):
    return (S.base(c, s) if arm == "frozen3i" else S.new(c, arm, s))[m]


def ratio(cs, a, b, m):
    return np.array([np.exp(np.mean(np.log([(val(c, a, s, m) + 1e-9) / (val(c, b, s, m) + 1e-9) for s in S.CLOCK]))) for c in cs])


CON = [("order only (order changed, PL-4 leftover)         ", "orderonly", "frozen3i"),
       ("leftover only (PL-4 order, new leftover)          ", "leftonly", "frozen3i"),
       ("both = one-at-a-time                              ", "ratio1", "frozen3i"),
       ("8 passes, PL-4 leftover                           ", "pass8gl", "frozen3i"),
       ("8 passes, new leftover = 8-pass fill              ", "ratio8", "frozen3i"),
       ("order effect, given new leftover (both / left)    ", "ratio1", "leftonly"),
       ("leftover effect, given new order (both / order)   ", "ratio1", "orderonly"),
       ("leftover effect inside 8-pass                     ", "ratio8", "pass8gl"),
       ("passes effect, PL-4 leftover (8-pass / order only)", "pass8gl", "orderonly")]
for lab, cs in (("all 42", S.cases("dev") + S.cases("heldout")), ("heldout 24", S.cases("heldout")), ("dev 18", S.cases("dev"))):
    print(f"\n===== {lab} cases")
    for m in MET:
        print(f" {m}")
        for t, a, b in CON:
            r = ratio(cs, a, b, m)
            g, lo, hi = S.gm_ci(r)
            print(f"   {t} {g:.3f} [{lo:.3f}, {hi:.3f}]  median case {np.median(r):.3f}  better/worse {int((r < 1).sum())}/{int((r > 1).sum())}")
