"""Does B* annealing drift the layout toward heavy functions under CAP-W1? (2 Nov 2026)
Re-runs B* F1_r0.5_s1 (annealing on, seed offset 0) under CAP-U and CAP-W1 and stores the start layout X0 and the final layout
sim.cnt. The event hash of each re-run is compared with the stored result, so the layouts belong to the reported runs.
  python bstar_layout_drift.py run <CAP-U|CAP-W1>   |   python bstar_layout_drift.py report"""
import json, pickle, sys, time
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT))
OUT = ROOT / "results" / "bstar_diag"; W1 = ROOT / "results" / "capW1_light"; D1 = ROOT / "results" / "d1_headroom"
TG = "F1_r0.5_s1"

def run(model):
    import yaml
    from dfps.sim import Sim
    from dfps.variants import make_adjuster, sim_kwargs
    A = yaml.safe_load((ROOT / "config" / "assumptions.yaml").read_text(encoding="utf-8"))
    if model == "CAP-U":
        sc, X0 = pickle.load(open(D1 / f"{TG}.pkl", "rb")), pickle.load(open(D1 / f"{TG}.prep.pkl", "rb"))["X0"]
    else:
        P = pickle.load(open(W1 / f"{TG}.sc.pkl", "rb")); sc, X0 = P["sc"], P["X0"]
    kw = sim_kwargs("B_STAR", A)
    kw.update(warmup=60.0, duration=900.0, retry_min_interval=1.0, retry_max_attempts=10)
    kw["interval"] = float(json.loads((D1 / f"{TG}.B_STAR.json").read_text())["period"])
    sim = Sim(sc, X0.copy(), adjuster=make_adjuster("B_STAR", A, seed=1 + 300), seed=1 + 400, **kw)
    r = sim.run()
    pickle.dump(dict(model=model, X0=np.array(X0), cnt=sim.cnt.T.copy(), fw=np.asarray(sc.fw), ecc=np.asarray(sc.ecc),
                     hash=r["event_hash"], p99=r["p99_makespan"]), open(OUT / f"layout_{model}.pkl", "wb"))
    print(model, "done", r["p99_makespan"], flush=True)

def report():
    stored = {"CAP-U": json.loads((D1 / f"{TG}.B_STAR.json").read_text())["result"]["event_hash"],
              "CAP-W1": json.loads((W1 / f"{TG}.B_STAR.json").read_text())["result"]["event_hash"]}
    for m in ("CAP-U", "CAP-W1"):
        d = pickle.load(open(OUT / f"layout_{m}.pkl", "rb"))
        X0, X1, fw, ecc = d["X0"], d["cnt"], d["fw"], d["ecc"]
        print(f"=== {m}: P99 {d['p99']:.0f}, hash same as stored: {d['hash'] == stored[m]}")
        print(f"  containers {X0.sum()} -> {X1.sum()}; weighted load {(X0@fw).sum():.1f} -> {(X1@fw).sum():.1f} of {ecc.sum():.1f}")
        print(f"  functions with 0 containers: {(X0.sum(0)==0).sum()} -> {(X1.sum(0)==0).sum()}; moved containers (L1/2): {np.abs(X1-X0).sum()/2:.0f}")
        order = np.argsort(fw); lo, hi = order[:len(fw)//3], order[-(len(fw)//3):]
        print(f"  light third (w<={fw[lo].max():.2f}): {X0[:,lo].sum()} -> {X1[:,lo].sum()} containers;  heavy third (w>={fw[hi].min():.2f}): {X0[:,hi].sum()} -> {X1[:,hi].sum()}")
        print(f"  correlation of change with weight: {np.corrcoef(fw, X1.sum(0)-X0.sum(0))[0,1]:.2f}")
if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    run(sys.argv[2]) if sys.argv[1] == "run" else report()
