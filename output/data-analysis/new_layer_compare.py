"""Compare the no-B* controller variants (new_layer_sweep.py) with the reference (rebal = request moves cap 300) and with B* / the
best existing method. Paired differences are (variant - reference) / reference on P99: negative = the variant is better."""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from d1_rlla import BASE, D1, D3S, boot  # noqa: E402

M = "p99_makespan"
EX = ("B_STAR", "RL", "RL_CAL", "HEU")
NAMES = [("rebal", "REFERENCE: busiest-first + request moves (cap 300), no B*"),
         ("nl_rm100", "request moves capped at 100 / round"), ("nl_rm1000", "request moves capped at 1000 / round"),
         ("nl_rmall", "request moves unlimited"),
         ("nl_hpa", "HPA-style rule"), ("nl_fifer", "Fifer-style rule"), ("nl_kraken", "Kraken-style rule"),
         ("nl_cap100", "re-layout capped at 100 containers"), ("nl_cap200", "re-layout capped at 200 containers"),
         ("nl_u0.7", "utilisation target 0.7"), ("nl_u0.9", "utilisation target 0.9"),
         ("nl_c60", "backlog cleared in 60 s"), ("nl_c240", "backlog cleared in 240 s"), ("nl_randplace", "random placement (no data affinity)"),
         ("nl_jsq", "BASELINE: join-shortest-queue moves instead of finish-time moves"),
         ("nl_steal", "BASELINE: work-stealing moves instead of finish-time moves"),
         ("nl_stack", "TEXTBOOK STACK: HPA-style sizing + join-shortest-queue moves"),
         ("nl_km", "PLACEMENT: incremental k-median + improvement pass"),
         ("nl_km_noimp", "PLACEMENT: incremental k-median, no improvement pass"),
         ("nl_km_scratch", "PLACEMENT: k-median from scratch"),
         ("nl_km_noorig", "PLACEMENT: incremental k-median, origins not counted"),
         ("nl_km_rmall", "PLACEMENT: incremental k-median + unlimited request moves"),
         ("nl_qa", "PLACEMENT: queue-aware, tau 1 (unlimited moves)"), ("nl_qa_tau2", "PLACEMENT: queue-aware, tau 2"),
         ("nl_qa_noqueue", "PLACEMENT: queue-aware without the waiting term")]
base = {}
for d_ in (D1, BASE):
    for f in d_.glob("*.json"):
        x = json.loads(f.read_text())
        if x.get("ctrl") in EX:
            base.setdefault((x["family"], x["rho"], x["seed"]), {})[x["ctrl"]] = x["result"]
runs = {}
for n, _ in NAMES:
    for f in D3S.glob(f"*.O3S_h120_blind_nosim_{n}.json"):
        x = json.loads(f.read_text())
        runs.setdefault(n, {})[(x["family"], x["rho"], x["seed"])] = x["result"]
p = lambda b: f"{b['mean'] * 100:+6.1f}% ({b['lo'] * 100:+.0f} to {b['hi'] * 100:+.0f})"  # noqa: E731
out = {}
for rhos, rl in (((0.5,), "50% load"), ((0.7, 0.85), "70-85% load"), ((0.5, 0.7, 0.85), "all loads")):
    print(f"=== {rl} ===")
    for n, lab in NAMES:
        if n not in runs:
            continue
        ks = [k for k in runs[n] if k[1] in rhos and k[2] <= 3 and k in runs["rebal"] and k in base and "B_STAR" in base[k]]
        if not ks:
            continue
        vb = [(base[k]["B_STAR"][M] - runs[n][k][M]) / base[k]["B_STAR"][M] for k in ks]
        be = [min(base[k][m][M] for m in EX if m in base[k]) for k in ks]
        ve = [(b - runs[n][k][M]) / b for b, k in zip(be, ks)]
        pr = [(runs[n][k][M] - runs["rebal"][k][M]) / runs["rebal"][k][M] for k in ks]
        row = dict(n=len(ks), vs_bstar=boot(vb), vs_best=boot(ve), wins=int(sum(x > 0 for x in ve)), paired=boot(pr),
                   cold=float(np.mean([runs[n][k]["cold_starts"] for k in ks])))
        out[f"{n}|{rl}"] = row
        extra = "" if n == "rebal" else f" | vs reference {p(row['paired'])}"
        print(f"{lab:56s} n={len(ks):2d} vs B* {p(row['vs_bstar'])} | vs best {p(row['vs_best'])} wins {row['wins']:2d}"
              f" | cold {row['cold']:6.0f}{extra}")
(ROOT / "output" / "data-analysis" / "results" / "new_layer_compare.json").write_text(json.dumps(out, indent=1))
