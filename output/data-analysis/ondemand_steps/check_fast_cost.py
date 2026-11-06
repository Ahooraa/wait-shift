"""Is the fast re-layout scoring the same arithmetic up to rounding, and do layouts differ only at near-ties? One real scenario, real call to queue_aware_placement in both modes."""
import pickle, sys
from pathlib import Path
import numpy as np
ROOT = Path("D:/DFPS implementation"); sys.path.insert(0, str(ROOT))
import dfps.controllers as C
P = pickle.load(open(ROOT / "results/capW1_light/F1_r0.5_s1.sc.pkl", "rb"))
sc, X0 = P["sc"], P["X0"]
fw = np.asarray(sc.fw, float)
mu = np.array([f.exec_time for f in sc.functions])
rates = C.expected_workflow_rates(sc)
lam = np.zeros(len(mu))
for w, r in zip(sc.workflows, rates):
    for t in range(w.n):
        lam[w.ft[t]] += r
load = lam * mu
need = np.maximum(1, np.ceil(load / 0.7)).astype(int)
print("weighted need", float(need @ fw), "capacity", float(sc.ecc.sum()))
kw = dict(rates=rates, counts=need, cur=X0, busy=load, origin_weight=1.0, tau=1.0, queue_term=False, fill_leftover=False)
A = C.queue_aware_placement(sc, **kw)
B = C.queue_aware_placement(sc, fast_cost=True, **kw)
print("same counts per function:", bool((A.sum(axis=0) == B.sum(axis=0)).all()), "| cells that differ:", int((A != B).sum()), "of", A.size, "| containers placed:", int(A.sum()))
# the formula on random inputs: dense product against the shared-base form
rng = np.random.default_rng(0)
N, D = 80, 60
h = rng.integers(0, 6, (D, N)).astype(float)
W, Bm = np.exp(-h), np.exp(-h) * h
ra, c = rng.random(D), rng.integers(0, 4, N).astype(float)
c[0] = 1.0
idx = np.arange(N)
delta = np.eye(N)
cc = c[None, :] + delta
dense = ((cc @ Bm.T) / np.maximum(cc @ W.T, 1e-12) * ra[None, :]).sum(axis=1)
fast = ((Bm @ c)[None, :] + Bm[:, idx].T) / np.maximum((W @ c)[None, :] + W[:, idx].T, 1e-12)
fast = (fast * ra[None, :]).sum(axis=1)
print("largest relative difference of the two forms: %.2e" % float(np.max(np.abs(dense - fast) / np.abs(dense))))
