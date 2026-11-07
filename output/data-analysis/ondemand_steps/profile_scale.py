"""Where does the controller's time go? cProfile of one on-demand FROZEN-3 run at N servers (seed 2, so the sweep's seed-1 files are untouched)."""
import os
for v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ[v] = "1"
import cProfile, pstats, sys
from pathlib import Path
ROOT = Path("D:/DFPS implementation"); sys.path.insert(0, str(ROOT / "output" / "data-analysis")); sys.path.insert(0, str(ROOT))
import capw1_scale as S
N = int(sys.argv[1])
pr = cProfile.Profile()
pr.enable()
S.one(N, int(sys.argv[2]) if len(sys.argv) > 2 else 30, int(sys.argv[3]) if len(sys.argv) > 3 else 15, 2)
pr.disable()
st = pstats.Stats(pr)
total = st.total_tt
print(f"total {total:.1f} s at N={N}")
rows = []
for (fn, line, name), (cc, nc, tt, ct, _) in st.stats.items():
    rows.append((ct, tt, nc, Path(fn).name, line, name))
keep = ("queue_aware_placement", "costs", "share", "demand_points", "bottleneck_first_placement", "rebalance_step", "_order_cf", "engine", "evaluate", "hosts_of", "svc", "service_estimate",
        "apply_placement", "decide", "candidates", "__init__", "backlog_per_function", "workflow_rates", "forecast", "matmul", "fst_vec", "transfer_only", "route", "reb", "bfp")
print(f"{'cumulative s':>12s} {'own s':>8s} {'calls':>10s}  function")
for ct, tt, nc, f, line, name in sorted(rows, reverse=True)[:70]:
    print(f"{ct:12.2f} {tt:8.2f} {nc:10d}  {f}:{line} {name}")
