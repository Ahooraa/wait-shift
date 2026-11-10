"""Clean timing, one process at a time: MV-3 (FASTPATH 5) and MV-4 (FASTPATH 7), alternating, FROZEN-4, on-demand, seeds 1-2."""
import os, sys, json, subprocess, numpy as np
from pathlib import Path
ROOT = next(p for p in (Path("D:/DFPS implementation"), Path.home() / "DFPS-implementation") if p.exists())
S = ROOT / "output/data-analysis/capw1_scale.py"
SIZES = [(160, 30, 15), (320, 30, 15), (640, 30, 15), (1280, 30, 15), (2560, 30, 15), (320, 120, 60), (640, 240, 120), (1280, 480, 240)]
DIR = {"5": "capW1_scale_fill1_clean", "7": "capW1_scale_mv4_clean"}


def path(fast, n, f, w, seed):
    return ROOT / "results" / DIR[fast] / f"N{n}_F{f}_W{w}_s{seed}.json"


if sys.argv[1] == "run":
    for seed in (1, 2):
        for n, f, w in SIZES:
            for fast in ("7", "5"):
                if n == 2560 and fast == "5" and seed == 2:
                    continue
                p = path(fast, n, f, w, seed)
                if p.exists() and json.loads(p.read_text()).get("done"):
                    continue
                try:
                    r = subprocess.run([sys.executable, str(S), "one", str(n), str(f), str(w), str(seed)], env=dict(os.environ, FASTPATH=fast, TAG="_clean"), capture_output=True, text=True, timeout=3000)
                    print(("done" if r.returncode == 0 else "FAILED " + r.stderr[-500:]), fast, n, f, seed, flush=True)
                except subprocess.TimeoutExpired:
                    print("timeout", fast, n, f, seed, flush=True)
print(f"{'N':>5s} {'F':>4s} s | {'MV-3 med':>9s} {'p99':>7s} | {'MV-4 med':>9s} {'p99':>7s} {'max':>7s} | ratio med | same hash | queued moves | evals reused priced/avail blocked")
for seed in (1, 2):
    for n, f, w in SIZES:
        a, b = path("5", n, f, w, seed), path("7", n, f, w, seed)
        A = json.loads(a.read_text()) if a.exists() else None
        B = json.loads(b.read_text()) if b.exists() else None
        if not B:
            continue
        m, st = B["move"], B["mv4_stats"]
        am = A["move"] if A else dict(median=float("nan"), p99=float("nan"))
        print(f"{n:5d} {f:4d} {seed} | {am['median']:9.1f} {am['p99']:7.1f} | {m['median']:9.1f} {m['p99']:7.1f} {m['max']:7.1f} | {am['median'] / m['median']:9.1f} | {(A or {}).get('event_hash') == B.get('event_hash') if A and A.get('done') and B.get('done') else None} | {B['queued_mean']:.0f} {B['moves_per_pass']:.0f} | {st[0]} {st[1]} {st[2] / max(1, st[3]):.4f} ({st[2] / max(1, st[0]):.1f} per eval) {st[4]}")
