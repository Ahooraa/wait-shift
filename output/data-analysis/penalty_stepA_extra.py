"""Step A add-on (2026-10-28): margin x kind, harm concentration, mu spread, and the join-gating signal's relevance."""
import runpy
import sys

import numpy as np

sys.argv = [sys.argv[0], sys.argv[1]]
import io, contextlib  # noqa: E401,E402
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    G = runpy.run_path(str(__import__("pathlib").Path(__file__).parent / "penalty_stepA_analyze.py"), run_name="__main__")
g, EX, R, W, stt = G["g"], G["EX"], G["R"], G["W"], G["stt"]

mu = np.array([EX[k["f"]] for k in g])
print("service time mu_f over moves: p10/p50/p90 =", np.percentile(mu, [10, 50, 90]).round(2), " distinct functions moved:", len({k['f'] for k in g}))
x = np.array([k["pred_gain_wait"] for k in g]) / mu
real = np.array([k["real_gain_wait"] for k in g])
net = real - np.array([k["out_delta"] for k in g])
kind = np.array([k["kind"] for k in g])
neg_total = -net[net < 0].sum()
print(f"\nmargin x kind (net of first-hop fracture; 'harm' = share of all net-negative seconds):")
for lo, hi in ((0, 0.25), (0.25, 0.5), (0.5, 1e9)):
    for kd in ("first", "return", "onward"):
        m = (x >= lo) & (x < hi) & (kind == kd)
        if m.sum():
            print(f"  gain/mu {lo:>4}-{hi:<5} {kd:7s} n={m.sum():6d} real {real[m].mean():+6.2f}s net {net[m].mean():+6.2f}s "
                  f"harmful {(net[m] < 0).mean():.1%}  share of total harm {-net[m][net[m] < 0].sum() / neg_total:.1%}")
pg = np.array([k["pred_gain_wait"] for k in g])
for lo, hi in ((0, 1), (1, 2), (2, 1e9)):
    m = (pg >= lo) & (pg < hi)
    print(f"  absolute predicted gain {lo}-{hi}s: n={m.sum()} real {real[m].mean():+.2f}s")

# join gating: a task whose child join j already has every other parent's input delivered when the task starts
print("\njoin-gating signal:")
rows = {"all": [], "tail": []}
for rid, r in R.items():
    w, T = W[r["wid"]], r["T"]
    for t in T:
        js = [c for c in w["ch"][t] if len(w["par"][c]) > 1]
        if not js:
            continue
        gate_t = None
        for j in js:
            others = [r["arr_in"][(u, j)] for u in w["par"][j] if u != t]
            tg = max(others)
            if tg <= T[t][6]:
                gate_t = tg if gate_t is None else min(gate_t, tg)
        gating = gate_t is not None
        gated_wait = max(0.0, T[t][6] - max(gate_t, T[t][5])) if gating else 0.0
        rec = (gating, t in r["chain"], gated_wait, T[t][8], w["flt"][t] <= 1e-9)
        rows["all"].append(rec)
        if r["tail"]:
            rows["tail"].append(rec)
for grp, rs in rows.items():
    a = np.array(rs, dtype=float)
    gt, on, gw, nm, zf = a[:, 0] > 0, a[:, 1] > 0, a[:, 2], a[:, 3], a[:, 4] > 0
    nreq = len(R) if grp == "all" else sum(1 for r in R.values() if r["tail"])
    print(f"[{grp}] join-feeding tasks {len(a)}: gating at start {gt.mean():.1%};  P(on critical path | gating) {on[gt].mean():.3f} "
          f"vs | not gating {on[~gt].mean():.3f}  (zero-float structural: {on[zf].mean():.3f})")
    print(f"       wait accrued AFTER becoming gating: {gw.sum() / nreq:.2f}s per request; gating tasks moved: {(nm[gt] > 0).mean():.1%}")
