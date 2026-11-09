"""Profile the request-move pass inside the full simulator (FROZEN-4, on-demand scale scenario). python mv_prof.py N F W [seed]"""
import os, sys, cProfile, pstats, io, json
from pathlib import Path
os.environ["FASTPATH"] = "5"
HERE = Path(__file__).resolve().parent
sys.path[:0] = ["D:/DFPS implementation/output/data-analysis", "D:/DFPS implementation"]
N, F, W = map(int, sys.argv[1:4]); seed = int(sys.argv[4]) if len(sys.argv) > 4 else 1
sys.argv = sys.argv[:1]
import numpy as np
import capw1_scale as S
import dfps.o3s as O3
S.OUT = HERE / "mv_prof_out"
pr = cProfile.Profile()
orig = O3.O3SimAdjuster.rebalance_step
shape = []


def wrapped(self, s, max_moves=None):
    q = [[len(s.queue[k][f]) for f in range(s.F)] for k in range(s.N)]
    q = np.array(q)
    cnt = np.asarray(s.cnt)
    cnt = cnt if cnt.shape[0] == s.F else cnt.T
    m0 = getattr(self, "rebal_moves", 0)
    pr.enable()
    x = orig(self, s, max_moves)
    pr.disable()
    fq = np.flatnonzero(q.sum(axis=0))
    shape.append((int(q.sum()), int((q > 0).sum()), float((cnt[fq] > 0).sum(axis=1).mean()) if fq.size else 0.0, int(q.max()), getattr(self, "rebal_moves", 0) - m0))
    return x


O3.O3SimAdjuster.rebalance_step = wrapped
S.one(N, F, W, seed)
a = np.array(shape, float)
st = io.StringIO()
p = pstats.Stats(pr, stream=st).sort_stats("tottime")
p.print_stats(28)
out = HERE / f"mv_prof_{N}_{F}.txt"
out.write_text(f"passes {len(a)}  per pass (mean): queued {a[:,0].mean():.0f}, non-empty queues {a[:,1].mean():.0f}, hosts per queued function {a[:,2].mean():.1f}, longest queue {a[:,3].mean():.0f}, moves {a[:,4].mean():.0f}\n" + st.getvalue())
print("wrote", out)
