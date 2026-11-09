"""Does the repo switch reproduce the scratch prototype? (1) layouts on recorded inputs, direct and factorised pricing; (2) default PL-4 path unchanged."""
import sys, os, pickle, time
argv, sys.argv = sys.argv, sys.argv[:1]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pl5
K = pl5.R10.K
ORIG = pl5.R10.ORIG
RD = "D:/DFPS implementation/results/relayout_prof/"


def run(sc, r, f, **extra):
    K._place_incremental = f
    i = r["inp"]; kw = dict(i["kw"]); kw["incr"] = True; kw["fast_cost"] = False; kw["lazy"] = False; kw["thin"] = 0
    kw.update(extra)
    t = time.perf_counter(); X = K.queue_aware_placement(sc, rates=i["rates"], counts=i["counts"], cur=i["cur"], busy=i["busy"], **kw)
    return X, time.perf_counter() - t


for name in ("F1_r0.85_s7.frozen3m", "F2_r0.85_s7.frozen3m", "N80_F30_W15_s1", "N320_F30_W15_s1", "N640_F30_W15_s1", "N640_F240_W120_s1", "N1280_F480_W240_s1_fp4"):
    P = pickle.load(open(RD + name + ".pkl", "rb")); sc, rec = P["sc"], P["rec"]
    pl5.R10.ST["s"] = None
    for lab, var, passes in (("one-at-a-time", "ratio1", 0), ("8-pass", "ratio8", 8)):
        C = pl5.make(**pl5.VARIANTS[var])
        d, ta, tb = 0, [], []
        for r in rec:
            a, t1 = run(sc, r, C)
            b, t2 = run(sc, r, ORIG, fill="shortfall", fill_passes=passes)
            d += int(np.abs(a - b).sum()); ta.append(t1); tb.append(t2)
        print(f"{name:26s} {lab:14s} calls {len(rec):3d}  containers differing prototype vs repo {d:4d}  median ms prototype {np.median(ta[1:])*1e3:7.1f} repo {np.median(tb[1:])*1e3:7.1f}", flush=True)
K._place_incremental = ORIG
