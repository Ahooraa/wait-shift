"""Rebuild the chart block of slide 2 (deck output/presentation/dfps-controller-talk.html) from CAP-W1 results:
FROZEN-4 (ours, filled and on-demand), B*, RL; 18 development cases (F1/F2 x rho 0.5/0.7/0.85 x seeds 1-3). RL_CAL and Heu are not shown.
  python slide2_capw1.py            # print numbers
  python slide2_capw1.py write      # patch the deck
"""
import json, math, re, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import capw1_rows as C
DECK = C.ROOT / "output" / "presentation" / "dfps-controller-talk.html"
ARMS = [("FROZEN-4", "Ours", ""), ("FROZEN-4 on-demand", "Ours on-demand", " od"), ("B*", "B*", " m"), ("RL", "RL", " w")]   # textbook stack removed 6 Nov 2026 (user: a mix of our own parts, not a baseline to show)
RHOS = (0.5, 0.7, 0.85)
cs = C.dev()
R = {c: C.rows(c) for c in cs}
OD = C.ROOT / "results" / "capW1_ondemand"          # FROZEN-4 on-demand (6 Nov 2026): container counts = the sizing rule's, no leftover memory filled
OD_J = {c: json.loads((OD / f"{c}.frozen4_od.json").read_text()) for c in cs}
for c in cs:
    R[c]["FROZEN-4 on-demand"] = OD_J[c]["result"]
    R[c]["FROZEN-4"] = json.loads((C.OUT / f"{c}.fill1.json").read_text())["result"]   # arm fill1 = FROZEN-4, filled
def cases(rho): return [c for c in cs if f"_r{rho}_" in c]
def val(c, a, metric):
    r = R[c][a]
    return {"avg": r["avg_makespan"], "p99": r["p99_makespan"], "cold": r["cold_starts"],
            "mv": 100 * r["n_moved"] / r["n_completed"]}[metric]
def mean(rho, a, m): return float(np.mean([val(c, a, m) for c in cases(rho)]))
fmt = {"avg": lambda v: f"{v:.1f}", "p99": lambda v: f"{v:,.0f}", "cold": lambda v: f"{v:,.0f}", "mv": lambda v: f"{v:,.0f}"}

def bars(metric, title, note=""):
    M = {(rho, a): mean(rho, a, metric) for rho in RHOS for a, _, _ in ARMS}
    top = max(M.values())
    out = f'<div class="vrow"><span class="vtitle">{title}</span><div class="vgrid">'
    for rho in RHOS:
        out += f'<div class="vchart"><span class="vh">{int(rho*100)}% load</span><div class="vbars">'
        for a, _, cl in ARMS:
            v = M[(rho, a)]
            out += f'<div class="vcol"><span class="vval">{fmt[metric](v)}</span><div class="vbar{cl}" style="height:{max(2, round(53*v/top))}px"></div></div>'
        out += '</div><div class="vnames">' + "".join(f"<span>{n}</span>" for _, n, _ in ARMS) + '</div></div>'
    return out + '</div></div>' + note

def dots():
    allv = [val(c, a, "p99") for c in cs for a in ("FROZEN-4", "B*")]
    lo, hi = math.log10(min(allv)) - 0.06, math.log10(max(allv)) + 0.06
    X = lambda v: 8 + 284 * (math.log10(v) - lo) / (hi - lo)
    ticks = [t for t in (100, 300, 1000, 3000) if lo < math.log10(t) < hi]
    out = '<div class="vrow"><span class="vtitle">Per-case P99 makespan (s, log scale): <span class="lg-o">●</span> Ours <span class="lg-b">●</span> B*</span><div class="vgrid">'
    for rho in RHOS:
        ks = sorted(cases(rho), key=lambda c: val(c, "FROZEN-4", "p99"))
        s = f'<div class="vchart"><span class="vh">{int(rho*100)}% load</span><svg class="dots" viewBox="0 0 300 150" role="img" aria-label="{int(rho*100)}% load: P99 makespan per case, ours and B*">'
        for t in ticks:
            s += f'<line class="dgrid" x1="{X(t):.1f}" x2="{X(t):.1f}" y1="6" y2="130"/><text class="dtick" x="{X(t):.1f}" y="144">{t:,}</text>'
        for i, c in enumerate(ks):
            y = 16.3 + i * (119.7 - 16.3) / (len(ks) - 1)
            xo, xb = X(val(c, "FROZEN-4", "p99")), X(val(c, "B*", "p99"))
            s += f'<line class="dlink" x1="{xo:.1f}" x2="{xb:.1f}" y1="{y:.1f}" y2="{y:.1f}"/><circle class="dot-o" cx="{xo:.1f}" cy="{y:.1f}" r="3.5"/><circle class="dot-b" cx="{xb:.1f}" cy="{y:.1f}" r="3.5"/>'
        out += s + '</svg></div>'
    return out + '</div></div>'

def block():
    cold = ('<div class="coldnote">RL starts with no initial placement (every slot empty); in an earlier 18-case test (CAP-U) giving RL and Heu the same NSGA-II '
            'start as ours/B*, cold starts changed by −1.6% on average (range −11% to +13%) and P99 by −1.3% — the empty start is not the explanation for RL\'s high count.</div>')
    return ('<div class="vcharts">' + bars("avg", "Average makespan (s)") + bars("p99", "P99 makespan (s)") + dots()
            + bars("cold", "Cold starts per run", cold) + bars("mv", "Request moves per 100 requests") + '</div>')

if __name__ == "__main__":
    print("memory share on-demand", {rho: round(float(np.mean([OD_J[c]["info"]["prov_mean"] / OD_J[c]["info"]["capacity_total"] for c in cases(rho)])), 2) for rho in RHOS})
    for m in ("avg", "p99", "cold", "mv"):
        print(m, {rho: {a: fmt[m](mean(rho, a, m)) for a, _, _ in ARMS} for rho in RHOS})
    if len(sys.argv) > 1 and sys.argv[1] == "write":
        t = DECK.read_text(encoding="utf-8")
        i = t.index('<div class="vcharts">'); j = t.index('<p class="metric">', i)
        t = t[:i] + block() + "\n  " + t[j:]
        DECK.write_text(t, encoding="utf-8")
        print("deck patched")
