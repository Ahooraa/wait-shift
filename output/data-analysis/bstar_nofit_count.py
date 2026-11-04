"""B* misfit count (CAP-W1 diagnostic, 2 Nov 2026): how often does the annealing step propose a replacement that does not fit?

Re-runs B* exactly as capw1_light.py does (same scenario, start layout, seeds) on ONE case and reads the annealing counters
(dfps/sa.py stats: fit_checked, nofit, nofit_none) after the run. Counting only; no behaviour change. Output is checked
against the stored run (event hash, P99) so a count from a different trajectory cannot slip through.

  python bstar_nofit_count.py F1_r0.5_s1
"""
import json
import pickle
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
import yaml  # noqa: E402
from dfps.sim import Sim  # noqa: E402
from dfps.variants import make_adjuster, sim_kwargs  # noqa: E402

OUT, D1 = ROOT / "results" / "capW1_light", ROOT / "results" / "d1_headroom"
DURATION, WARMUP = 900.0, 60.0
tg = sys.argv[1]
ASSUME = yaml.safe_load((ROOT / "config" / "assumptions.yaml").read_text(encoding="utf-8"))
P = pickle.load(open(OUT / f"{tg}.sc.pkl", "rb"))
sc, X0 = P["sc"], P["X0"]
seed = int(tg.split("_s")[1])
kw = sim_kwargs("B_STAR", ASSUME)
kw.update(warmup=WARMUP, duration=DURATION, retry_min_interval=1.0, retry_max_attempts=10)
adj = make_adjuster("B_STAR", ASSUME, seed=seed + 300)
kw["interval"] = float(json.loads((D1 / f"{tg}.B_STAR.json").read_text())["period"])
t0 = time.time()
sim = Sim(sc, X0.copy(), adjuster=adj, seed=seed + 400, **kw)
r = sim.run()
sim.check_invariants()
st = dict(adj.stats)
ref = json.loads((OUT / f"{tg}.B_STAR.json").read_text())["result"]
print(f"{tg} wall {time.time() - t0:.0f}s | P99 {r['p99_makespan']:.1f} (stored {ref['p99_makespan']:.1f}) | event hash same as stored: {r['event_hash'] == ref['event_hash']}")
print("annealing counters:", json.dumps(st))
n, c = st["iterations"], st["fit_checked"]
print(f"proposals {n}; reached the fit test {c}; first draw did not fit {st['nofit']} ({100 * st['nofit'] / max(1, c):.1f}% of tested); "
      f"no function fit at all {st.get('nofit_none', 0)}; redrawn to a heavier function than the one removed {st.get('redraw_up', 0)}")
Path(OUT / f"{tg}.B_STAR.nofit.json").write_text(json.dumps(dict(capacity_model="CAP-W1", case=tg, stats=st, p99=r["p99_makespan"],
                                                                event_hash_same=r["event_hash"] == ref["event_hash"])))
