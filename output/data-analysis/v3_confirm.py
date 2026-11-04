"""V3 confirmation on fresh seeds 4-6 (CAP-W1; pre-registered 4 Nov 2026, workflow-aware-decision-rules.md, "V3 confirmation on fresh seeds 4-6").
Gain-ordered mover vs current mover (stored results/capW1_confirm transfer_only), F1/F2 x rho 0.7/0.85 x seeds 4-6.
CONFIRMED = moves/req CI upper <= 0.95 AND median CI upper < 1.00 (fresh 12) AND P99 CI upper <= 1.02 (pooled 24 with v3_online).
  python v3_confirm.py run [workers] | report
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import v3_online as V  # noqa: E402

ROOT = V.ROOT
V.OUT = OUT = ROOT / "results" / "v3_confirm"
REF = ROOT / "results" / "capW1_confirm"
OLD, OLDREF = ROOT / "results" / "v3_online", ROOT / "results" / "capW1_align_transfer_only"


def cases(seeds=(4, 5, 6)):
    return [f"{f}_r{r}_s{s}" for f in ("F1", "F2") for r in (0.7, 0.85) for s in seeds]


def run_job(tg):
    V.OUT = OUT                       # set in the worker process too (spawned workers re-import v3_online with its own OUT)
    return V.run_job(tg)


def run(workers):
    todo = [c for c in cases() if not (OUT / f"{c}.json").exists()]
    print(len(todo), "runs", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        for r in ex.map(run_job, todo):
            print("done", r, flush=True)


def load(out, ref, cs, refname):
    rows = []
    for c in cs:
        a, b = out / f"{c}.json", ref / refname(c)
        if a.exists() and b.exists():
            rows.append((c, json.loads(b.read_text())["result"], json.loads(a.read_text())["result"]))
    return rows


def report():
    new = load(OUT, REF, cases(), lambda c: f"{c}.transfer_only.json")
    old = load(OLD, OLDREF, cases((1, 2, 3)), lambda c: f"{c}.json")
    print(f"fresh {len(new)} of 12, follow-up {len(old)} of 12")
    mv = lambda x: x["n_moved"] / x["n_completed"]
    for c, b, a in new:
        print(f"{c:12s} P99 {b['p99_makespan']:6.1f} -> {a['p99_makespan']:6.1f} ({(a['p99_makespan'] / b['p99_makespan'] - 1) * 100:+5.1f}%)"
              f"  P50 {b['p50_makespan']:5.1f} -> {a['p50_makespan']:5.1f} ({(a['p50_makespan'] / b['p50_makespan'] - 1) * 100:+5.1f}%)"
              f"  moves/req {mv(b):.2f} -> {mv(a):.2f} ({(mv(a) / mv(b) - 1) * 100:+5.1f}%)  cold {b['cold_starts']} -> {a['cold_starts']}")
    if len(new) < 6:
        return
    r = lambda rows, f: V.gm_ci([f(a) / f(b) for _, b, a in rows])
    m = r(new, mv)
    p50 = r(new, lambda x: x["p50_makespan"])
    p99n = r(new, lambda x: x["p99_makespan"])
    p99p = r(new + old, lambda x: x["p99_makespan"])
    for nm, k in (("mean", "avg_makespan"), ("P95", "p95_makespan")):
        x = r(new, lambda z: z[k])
        print(f"   {nm:5s} fresh {x[0]:.3f} [{x[1]:.3f}, {x[2]:.3f}]")
    print(f"1 moves/req fresh   {m[0]:.3f} [{m[1]:.3f}, {m[2]:.3f}], lower in {sum(mv(a) < mv(b) for _, b, a in new)}/{len(new)}")
    print(f"2 median fresh      {p50[0]:.3f} [{p50[1]:.3f}, {p50[2]:.3f}], better in {sum(a['p50_makespan'] < b['p50_makespan'] for _, b, a in new)}/{len(new)}")
    print(f"3 P99 pooled {len(new) + len(old):2d}     {p99p[0]:.3f} [{p99p[1]:.3f}, {p99p[2]:.3f}]   (fresh alone {p99n[0]:.3f} [{p99n[1]:.3f}, {p99n[2]:.3f}])")
    for rho in ("0.7", "0.85"):
        kk = [(b, a) for c, b, a in new if f"_r{rho}_" in c]
        print(f"   rho {rho} fresh: P99 {np.exp(np.mean([np.log(a['p99_makespan'] / b['p99_makespan']) for b, a in kk])):.3f}"
              f"  P50 {np.exp(np.mean([np.log(a['p50_makespan'] / b['p50_makespan']) for b, a in kk])):.3f}"
              f"  moves {np.exp(np.mean([np.log(mv(a) / mv(b)) for b, a in kk])):.3f}")
    c1, c2, c3 = m[2] <= 0.95, p50[2] < 1.00, p99p[2] <= 1.02
    print(f"\ncriterion 1 {'met' if c1 else 'NOT met'}, 2 {'met' if c2 else 'NOT met'}, 3 {'met' if c3 else 'NOT met'} -> "
          f"{'CONFIRMED' if c1 and c2 and c3 else 'NOT CONFIRMED'}{'' if len(new) == 12 and len(old) == 12 else ' (partial)'}")


if __name__ == "__main__":
    {"run": lambda: run(int(sys.argv[2]) if len(sys.argv) > 2 else 6), "report": report}[sys.argv[1]]()
