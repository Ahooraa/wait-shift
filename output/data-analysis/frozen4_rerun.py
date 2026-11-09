"""FROZEN-4 re-run (9 Nov 2026): the FROZEN-3 result sets repeated with FROZEN-4, each matched to the cases its reference has.
Already available, not re-run: filled 42 cases x 3 clocks (arms fill1 / fill1_p1 / fill1_p2 in capW1_rows) and the scale runs (capW1_scale_fill1[_fb]).
Re-run here: on-demand (frozen4_od, frozen4_od_e30_u70), two-loop grid cells with a re-layout (Cf4, Df4, Cqf4, Cf4_L4, Df4_L4), FaaSPR's setting (f4_fixed, f4_elastic).
Baselines and grid cells without a re-layout (A, B) do not use the controller's re-layout and are not repeated.
  python frozen4_rerun.py run [workers] | report
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
R = ROOT / "results"
OD, GRID, FS, ROWS, LIGHT = R / "capW1_ondemand", R / "capW1_grid", R / "capW1_faaspr_setting", R / "capW1_rows", R / "capW1_light"
IND = R / "capW1_independent"
DEV = [f"{f}_r{r}_s{s}" for f in ("F1", "F2") for r in (0.5, 0.7, 0.85) for s in (1, 2, 3)]
HELD = [f"{f}_r{r}_s{s}" for f in ("F1", "F2") for r in (0.5, 0.7, 0.85) for s in (7, 8, 9, 10)]
OD_PAIRS = (("frozen4_od", "frozen3_od"), ("frozen4_od_e30_u70", "frozen3_od_e30_u70"))
GRID_PAIRS = (("Cf4", "C"), ("Df4", "D"), ("Cqf4", "Cq"), ("Cf4_L4", "C_L4"), ("Df4_L4", "D_L4"))
FS_PAIRS = (("f4_fixed", "f3_fixed"), ("f4_elastic", "f3_elastic"))


def stem(p, ref):
    return p.name[: -len(f".{ref}.json")]


def todo():
    out = []
    for a, b in OD_PAIRS:
        out += [("od", stem(p, b), a) for p in OD.glob(f"*.{b}.json") if not (OD / f"{stem(p, b)}.{a}.json").exists()]
    for a, b in GRID_PAIRS:
        out += [("grid", stem(p, b), a) for p in GRID.glob(f"*.{b}.json") if not (GRID / f"{stem(p, b)}.{a}.json").exists()]
    for a, b in FS_PAIRS:
        out += [("fs", stem(p, b), a) for p in FS.glob(f"*.{b}.json") if not (FS / f"{stem(p, b)}.{a}.json").exists()]
    return out


def job(j):
    kind, tg, arm = j
    if kind == "od":
        import capw1_ondemand as O
        return O.run_job((tg, arm, O.DURATION, str(O.OUT)))
    if kind == "grid":
        import capw1_grid as G
        return G.run_job((tg, arm))
    import faaspr_paper_setting as F
    return F.run_job((tg, arm, F.DURATION, str(F.OUT)))


def res(d, c, a):
    p = d / f"{c}.{a}.json"
    return json.loads(p.read_text())["result"] if p.exists() else None


def gm(x, seed=0, B=4000):
    x = np.log(np.asarray(x, float))
    b = x[np.random.default_rng(seed).integers(0, x.size, (B, x.size))].mean(axis=1)
    return np.exp(x.mean()), np.exp(np.percentile(b, 2.5)), np.exp(np.percentile(b, 97.5))


def line(lab, pairs, mets=(("p99_makespan", "P99"), ("avg_makespan", "mean"), ("cold_starts", "cold"))):
    pairs = [(a, b) for a, b in pairs if a and b]
    if not pairs:
        print(f"  {lab:46s} no data")
        return
    s = []
    for m, n in mets:
        g, lo, hi = gm([(a[m] + 1e-9) / (b[m] + 1e-9) for a, b in pairs])
        s.append(f"{n} {g:.3f} [{lo:.3f}, {hi:.3f}]")
    r = [a["p99_makespan"] / b["p99_makespan"] for a, b in pairs]
    print(f"  {lab:46s} n={len(pairs):2d}  " + "  ".join(s) + f"  P99 lower/higher {sum(x < 1 for x in r)}/{sum(x > 1 for x in r)}, median {np.median(r):.3f}")


def report():
    print("Ratio FROZEN-4 / FROZEN-3 (below 1 = FROZEN-4 lower), geometric mean over cases [95% case bootstrap]")
    for lab, cs in (("development", DEV), ("held-out", HELD)):
        print(f"-- filled, {lab}, three clocks, reference PL-4 (frozen3i)")
        for s in ("", "_p1", "_p2"):
            line(f"clock {s or 'base'}", [(res(ROWS, c, "fill1" + s), res(ROWS, c, "frozen3i" + s)) for c in cs])
    print("-- on-demand")
    for a, b in OD_PAIRS:
        for lab, cs in (("development", DEV), ("held-out", HELD)):
            line(f"{a} / {b}, {lab}", [(res(OD, c, a), res(OD, c, b)) for c in cs])
    print("-- two-loop grid")
    for a, b in GRID_PAIRS:
        for lab, cs in (("development", DEV), ("held-out", HELD)):
            line(f"{a} / {b}, {lab}", [(res(GRID, c, a), res(GRID, c, b)) for c in cs])
    print("-- two-loop grid with FROZEN-4: effect of each loop")
    for lab, cs in (("development", DEV), ("held-out", HELD)):
        for a, b in (("Cf4", "A"), ("B", "A"), ("Df4", "B"), ("Df4", "Cf4"), ("Df4", "A")):
            line(f"{a} / {b}, {lab}", [(res(GRID, c, a), res(GRID, c, b)) for c in cs])
    tags = sorted({p.name[: -len(".faaspr.json")] for p in FS.glob("*.faaspr.json")})
    print("-- FaaSPR's own setting")
    for a, b in FS_PAIRS + (("f4_fixed", "faaspr"), ("f4_elastic", "faaspr"), ("f3_fixed", "faaspr"), ("f3_elastic", "faaspr")):
        line(f"{a} / {b}", [(res(FS, c, a), res(FS, c, b)) for c in tags])
    print("-- held-out, system / FROZEN-4 (above 1 = FROZEN-4 lower), filled; in brackets of the next row the same against FROZEN-3 (frozen3i)")
    for arm, d in (("B_STAR", LIGHT), ("RL", LIGHT), ("faaspr", IND), ("faaspr_rs", IND), ("ga_p2", IND), ("heft_p2", IND), ("ga_s2", IND), ("heft_s2", IND)):
        line(f"{arm} / FROZEN-4", [(res(d, c, arm), res(ROWS, c, "fill1")) for c in HELD])
        line(f"{arm} / FROZEN-3", [(res(d, c, arm), res(ROWS, c, "frozen3i")) for c in HELD])
    print("-- held-out, on-demand, system / FROZEN-4")
    for arm in ("faaspr_od", "ga_p2_od", "heft_p2_od"):
        line(f"{arm} / FROZEN-4", [(res(OD, c, arm), res(OD, c, "frozen4_od")) for c in HELD])
        line(f"{arm} / FROZEN-3", [(res(OD, c, arm), res(OD, c, "frozen3_od")) for c in HELD])


if __name__ == "__main__":
    if sys.argv[1] == "run":
        t = todo()
        t.sort(key=lambda j: "_L4" in j[2])
        print(len(t), "runs", flush=True)
        with ProcessPoolExecutor(int(sys.argv[2]) if len(sys.argv) > 2 else 10) as ex:
            for r in ex.map(job, t):
                print("FAILED " + r if "FAILED" in r else "done " + r, flush=True)
    else:
        report()
