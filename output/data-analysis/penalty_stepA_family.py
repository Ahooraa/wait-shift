"""Step A, family-partitioned (2026-10-28): are the P99 bottlenecks family-specific, and do the move/urgency findings survive
when the diagnostic tail is taken WITHIN each family (its own worst 10%) instead of the pooled P99 (which is all large workflows)?

Families are derived from the DAG structure of the 15 F3 workflow types, not assumed:
  chain     no forks, no joins                 fan-in    joins, no forks (several roots merge)
  fan-out   forks, no joins                    fork-join forks and joins
Per family and per workflow type: worst 10% (sojourn >= that family's / type's own P90) vs the rest, per-request means of the
critical-path decomposition and of each problem. Moves are scored two ways: ex-ante (every move of the family -- no outcome
conditioning) and outcome-conditioned on the family's worst 10% (P90; still conditioned on outcome, so the gap between the
two rows measures the remaining selection bias).
  python output/data-analysis/penalty_stepA_family.py results/penalty_stepA/stepA.pkl"""
import contextlib
import io
import json
import runpy
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
PKL = sys.argv[1] if len(sys.argv) > 1 else str(HERE / "results" / "penalty_stepA" / "stepA.pkl")
sys.argv = [sys.argv[0], PKL]
with contextlib.redirect_stdout(io.StringIO()):
    G = runpy.run_path(str(HERE / "penalty_stepA_analyze.py"), run_name="__main__")
R, W, g, K, EX, stt, auc, H = G["R"], G["W"], G["g"], G["K"], G["EX"], G["stt"], G["auc"], G["H"]
U = G["U"]


def family(w):
    forks = any(len(c) > 1 for c in w["ch"])
    joins = bool(w["joins"])
    return {(False, False): "chain", (False, True): "fan-in", (True, False): "fan-out", (True, True): "fork-join"}[(forks, joins)]


FAM = {wid: family(w) for wid, w in W.items()}

# ------------------------------------------------------------------ per-request records
kinds_of = defaultdict(Counter)
for k in K:
    kinds_of[(k["rid"], k["task"])][k["kind"]] += 1
REC = {}
for rid, r in R.items():
    w, T, t_arr = W[r["wid"]], r["T"], r["t_arr"]
    ex_p = wu = wm = tr = 0.0
    for t in r["chain"]:
        row = T[t]
        ex_p += row[7] - row[6]
        if row[8] > 0:
            wm += row[6] - row[5]
        else:
            wu += row[6] - row[5]
        if not w["par"][t]:
            tr += row[5] - t_arr
    for (u, t) in r["crit_edges"]:
        tr += T[t][5] - T[u][7]
    extra_on = extra_all = 0.0
    for (u, v), size in w["ss"].items():
        e = stt(size, T[u][4], T[v][3]) - stt(size, T[u][3], T[v][3])
        extra_all += e
        if (u, v) in r["crit_edges"]:
            extra_on += e
    desync_on = 0.0
    for x in w["joins"]:
        if x not in r["chain"]:
            continue
        ps = w["par"][x]
        arr = {u: r["arr_in"][(u, x)] for u in ps}
        nom = {u: w["est"][u] + w["ex"][u] for u in ps}
        dly = {u: arr[u] - t_arr - nom[u] for u in ps}
        desync_on += max(arr.values()) - (t_arr + min(dly.values()) + max(nom.values()))
    n = w["n"]
    kc = Counter()
    for t in T:
        kc.update(kinds_of.get((rid, t), {}))
    REC[rid] = dict(soj=r["soj"], cp=w["cp"], exec=ex_p, wait_unmoved=wu, wait_moved=wm, transfer=tr, extra_hop_on_path=extra_on,
                    extra_hop_all=extra_all, join_desync_on_path=desync_on, moved_share=sum(1 for t in T if T[t][8] > 0) / n,
                    moves_per_task=sum(T[t][8] for t in T) / n, returns_per_task=kc["return"] / n, onward_per_task=kc["onward"] / n)
COLS = ["soj", "exec", "wait_unmoved", "wait_moved", "transfer", "extra_hop_on_path", "join_desync_on_path", "moves_per_task",
        "returns_per_task", "onward_per_task"]


def worst10(rids):
    s = np.array([REC[x]["soj"] for x in rids])
    p90 = np.percentile(s, 90)
    return {x for x in rids if REC[x]["soj"] >= p90}, float(p90), float(np.percentile(s, 99))


OUT = {}
groups = defaultdict(list)
types = defaultdict(list)
for rid, r in R.items():
    groups[FAM[r["wid"]]].append(rid)
    types[r["wid"]].append(rid)
WORST = {}                                                     # rid -> True if in its OWN family's worst 10%
WORST_T = {}                                                   # ... in its own workflow type's worst 10%
print("=== A. per family: worst 10% (>= family P90) vs the rest -- mean per request (s) ===")
hdr = "".join(f"{c[:14]:>15s}" for c in COLS)
for fam in ("chain", "fan-in", "fan-out", "fork-join"):
    rids = groups[fam]
    wst, p90, p99 = worst10(rids)
    for x in rids:
        WORST[x] = x in wst
    rest = [x for x in rids if x not in wst]
    wt = sorted({R[x]["wid"] for x in rids})
    print(f"\n[{fam}] types {wt}  requests {len(rids)}  P90 {p90:.1f}s  P99 {p99:.1f}s  share of pooled-P99 tail "
          f"{sum(R[x]['tail'] for x in rids) / max(1, sum(r['tail'] for r in R.values())):.1%}")
    print(f"  {'':10s}{hdr}")
    a = {c: np.mean([REC[x][c] for x in wst]) for c in COLS}
    b = {c: np.mean([REC[x][c] for x in rest]) for c in COLS}
    print(f"  {'worst10':10s}" + "".join(f"{a[c]:15.2f}" for c in COLS))
    print(f"  {'rest':10s}" + "".join(f"{b[c]:15.2f}" for c in COLS))
    print(f"  {'delta':10s}" + "".join(f"{a[c] - b[c]:15.2f}" for c in COLS))
    secs = ["exec", "wait_unmoved", "wait_moved", "transfer"]
    d_soj = a["soj"] - b["soj"]
    share = {c: (a[c] - b[c]) / d_soj for c in secs}
    print("  where the extra sojourn of the worst 10% comes from (shares of delta-sojourn): "
          + ", ".join(f"{c} {share[c]:.0%}" for c in secs)
          + f";  of which fracture extra-hop {(a['extra_hop_on_path'] - b['extra_hop_on_path']) / d_soj:.0%}, "
            f"join desync (overlaps waits/transfer) {(a['join_desync_on_path'] - b['join_desync_on_path']) / d_soj:.0%}")
    OUT[fam] = dict(types=wt, n=len(rids), p90=p90, p99=p99, worst=a, rest=b, delta_share=share)

print("\n=== B. per workflow type: what grows most in the type's own worst 10% (delta vs rest, s) ===")
print(f"  {'wid':>4s} {'family':10s} {'n':>3s} {'CP':>5s} {'MB':>5s} {'P90':>6s} {'dSoj':>6s} {'dWaitU':>7s} {'dWaitM':>7s} {'dTrans':>7s} "
      f"{'dExHop':>7s} {'dDesync':>8s} {'dMoves':>7s} {'dRet':>6s}")
OUT["types"] = {}
for wid in sorted(types, key=lambda x: (FAM[x], W[x]["cp"])):
    rids = types[wid]
    wst, p90, _ = worst10(rids)
    for x in rids:
        WORST_T[x] = x in wst
    rest = [x for x in rids if x not in wst]
    d = {c: np.mean([REC[x][c] for x in wst]) - np.mean([REC[x][c] for x in rest]) for c in COLS}
    OUT["types"][wid] = dict(family=FAM[wid], p90=p90, delta=d)
    w = W[wid]
    print(f"  {wid:>4d} {FAM[wid]:10s} {w['n']:>3d} {w['cp']:5.1f} {w['mb']:5.0f} {p90:6.1f} {d['soj']:6.1f} {d['wait_unmoved']:7.1f} "
          f"{d['wait_moved']:7.1f} {d['transfer']:7.1f} {d['extra_hop_on_path']:7.1f} {d['join_desync_on_path']:8.1f} "
          f"{d['moves_per_task']:7.2f} {d['returns_per_task']:6.2f}")


# ------------------------------------------------------------------ moves: ex-ante vs P90-conditioned, per family
def score(sel):
    if not sel:
        return None
    rg = np.array([k["real_gain_wait"] for k in sel])
    net = rg - np.array([k["out_delta"] for k in sel])
    return dict(n=len(sel), real=round(float(rg.mean()), 2), net=round(float(net.mean()), 2), harmful=round(float((net < 0).mean()), 3))


def line(label, s):
    if s:
        print(f"    {label:52s} n={s['n']:6d} real {s['real']:+6.2f}s  net {s['net']:+6.2f}s  harmful {s['harmful']:.1%}")


print("\n=== C. moves per family: ex-ante vs conditioned on the family's worst 10% (P90) ===")
OUT["moves"] = {}
for fam in ("chain", "fan-in", "fan-out", "fork-join"):
    mv = [k for k in g if FAM[k["wid"]] == fam]
    inw = [k for k in mv if k["rid"] in R]
    print(f"  [{fam}]")
    o = {}
    for kd in ("first", "return", "onward"):
        o[f"exante_{kd}"] = score([k for k in mv if k["kind"] == kd])
        line(f"ex-ante, {kd}", o[f"exante_{kd}"])
    o["p90_all"] = score([k for k in inw if WORST.get(k["rid"])])
    o["p90_crit"] = score([k for k in inw if WORST.get(k["rid"]) and k["crit"]])
    o["rest_crit"] = score([k for k in inw if not WORST.get(k["rid"]) and k["crit"]])
    line("P90-conditioned: tasks of worst-10% requests", o["p90_all"])
    line("P90-conditioned: ... on their critical path", o["p90_crit"])
    line("contrast: critical-path tasks of the other 90%", o["rest_crit"])
    mu = np.array([EX[k["f"]] for k in mv])
    x = np.array([k["pred_gain_wait"] for k in mv]) / mu
    for lo, hi in ((0, 0.25), (0.25, 0.5), (0.5, 1e9)):
        sel = [k for k, xi in zip(mv, x) if lo <= xi < hi]
        o[f"margin_{lo}"] = score(sel)
        line(f"ex-ante, predicted gain/mu in [{lo}, {hi})", o[f"margin_{lo}"])
    OUT["moves"][fam] = o

# ------------------------------------------------------------------ urgency with a within-family target
print("\n=== D. urgency candidates vs being on the critical path of a request in its OWN family's worst 10% ===")
tgt, fam_of_task = [], []
for rid, r in R.items():
    for t in r["T"]:
        tgt.append(bool(WORST.get(rid)) and t in r["chain"])
        fam_of_task.append(FAM[r["wid"]])
tgt, fam_of_task = np.array(tgt), np.array(fam_of_task)
OUT["urgency"] = {}
cands = ("req_slack", "local_slack", "local_slack_over_cp", "lag", "lag_over_cp", "neg_projected_soj")
print(f"  {'candidate':22s}" + "".join(f"{f:>11s}" for f in ("pooled", "chain", "fan-in", "fan-out", "fork-join")))
for c in cands:
    v = np.array(U[c])
    row = [auc(-v, tgt)] + [auc(-v[fam_of_task == f], tgt[fam_of_task == f]) for f in ("chain", "fan-in", "fan-out", "fork-join")]
    OUT["urgency"][c] = [round(a, 3) for a in row]
    print(f"  {c:22s}" + "".join(f"{a:11.3f}" for a in row))

# ------------------------------------------------------------------ E. length-bias check: per-TYPE target, type-normalised candidate
# Within one workflow type every slack candidate above is the same quantity shifted by a constant, so they differ only in how they
# rank tasks of DIFFERENT types that compete for the same pool. The per-type target asks: which candidate finds the tasks that will
# end in their OWN type's worst 10%? The normalised candidate divides projected sojourn by the type's median sojourn (online: a
# running median per workflow type; here taken from the run).
med = {wid: float(np.median([REC[x]["soj"] for x in rids])) for wid, rids in types.items()}
tgt_t, fam_t, normv = [], [], []
proj = np.array(U["neg_projected_soj"])
i = 0
for rid, r in R.items():
    for t in r["T"]:
        tgt_t.append(bool(WORST_T.get(rid)) and t in r["chain"])
        fam_t.append(FAM[r["wid"]])
        normv.append(proj[i] / med[r["wid"]])
        i += 1
tgt_t, fam_t, normv = np.array(tgt_t), np.array(fam_t), np.array(normv)
print("\n=== E. length-bias check: target = on the critical path of a request in its own WORKFLOW TYPE's worst 10% ===")
print(f"  {'candidate':34s}" + "".join(f"{f:>11s}" for f in ("pooled", "chain", "fan-in", "fan-out", "fork-join")))
OUT["urgency_type_target"] = {}
for name, v in (("req_slack", -np.array(U["req_slack"])), ("neg_projected_soj (absolute s)", -proj),
                ("projected_soj / type median", -normv), ("local_slack_over_cp", -np.array(U["local_slack_over_cp"]))):
    row = [auc(v, tgt_t)] + [auc(v[fam_t == f], tgt_t[fam_t == f]) for f in ("chain", "fan-in", "fan-out", "fork-join")]
    OUT["urgency_type_target"][name] = [round(a, 3) for a in row]
    print(f"  {name:34s}" + "".join(f"{a:11.3f}" for a in row))
json.dump(OUT, open(Path(PKL).with_name("family_result.json"), "w"), indent=1, default=float)
print("\nwritten", Path(PKL).with_name("family_result.json"))
