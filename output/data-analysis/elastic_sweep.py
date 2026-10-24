"""Elastic capacity (2026-10-23): can the controller serve the same traffic with fewer containers?

Structural limit being lifted: DFPS fixes the container count at the slot budget (D-7: every slot always holds an instance) and can
only convert one function into another. The sizing rule here could never say "use fewer", which is the claim Fifer and Kraken
make (76-80% fewer containers). With Sim(elastic=True) slots may stay empty: the controller adds an instance into a free slot (cold
start) and removes one (at once if idle or cold, after its run if busy). Cost is the number of provisioned containers integrated over
the measured window (result key provisioned_slot_s; mean_containers = that divided by the window length).

Controller: the frozen one (busiest-first sizing, incremental k-median placement, finish-time request moves with no cap, no B*),
differing only in that the sizing rule's own count is used instead of spreading the leftover slots by demand. The utilisation target
sets how much slack is kept: containers = ceil(load / target), so a lower target keeps more containers.

  full      the reference (nl_km_rmall): all 1,235 slots always provisioned
  el80      elastic, target 0.8 (the rule as designed)
  el65      elastic, target 0.65
  el50      elastic, target 0.5
  hpa_el, fifer_el, kraken_el   the published rules, each used with its own container count (Fifer and Kraken's own terms)
18 development cases (F1/F2 x 50/70/85% x seeds 1-3). Files <case>.O3S_h120_blind_nosim_nl_<variant>.json

  python output/data-analysis/elastic_sweep.py run [workers] [variants]   |   analyze
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(ROOT))
import d3s_headroom as d  # noqa: E402
from new_layer_sweep import BASE  # noqa: E402

EL = dict(BASE, placement="qaware", origin_weight=1.0, rebal_max=10 ** 9, tau=1.0, queue_term=False, elastic=True)   # FROZEN-1 placement
VARIANTS = {  # name -> (cand mode, churn)
    "el80": ("nosim", dict(EL, util_cap=0.8)), "el65": ("nosim", dict(EL, util_cap=0.65)), "el50": ("nosim", dict(EL, util_cap=0.5)),
    "hpa_el": ("hpa", dict(EL)), "fifer_el": ("fifer", dict(EL)), "kraken_el": ("kraken", dict(EL)),
}
M = "p99_makespan"


def run(workers, only):
    T = json.loads((d.OUT / "g2_tstar.json").read_text())
    T = {f: float(T["families"][f]["T_star"]) for f in ("F1", "F2")}
    jobs = []
    for name in only:
        cand, churn = VARIANTS[name]
        part = []
        for f in ("F1", "F2"):
            for r in d.RHOS:
                for s in (1, 2, 3):
                    tg = d.tag(f, r, s)
                    part.append((tg, str(d.RUNS / f"{tg}.O3S_h120_blind_nosim_nl_{name}.json"), s, T[f], d.DURATION, 60.0, 120.0, 5,
                                 True, None, cand, dict(churn)))
        part.sort(key=lambda j: -float(j[0].split("_r")[1].split("_")[0]))
        jobs += part
    with ProcessPoolExecutor(workers) as ex:
        for done in ex.map(d.job, jobs):
            print("done", done, flush=True)


def analyze():
    from d1_rlla import BASE as B1, D1, boot
    base = {}
    for d_ in (D1, B1):
        for f in d_.glob("*.json"):
            x = json.loads(f.read_text())
            if x.get("ctrl") in ("B_STAR", "RL"):
                base.setdefault((x["family"], x["rho"], x["seed"]), {})[x["ctrl"]] = x["result"]
    def load(s):
        o = {}
        for f in d.RUNS.glob(f"*.O3S_h120_blind_nosim_{s}.json"):
            x = json.loads(f.read_text())
            if x["seed"] <= 3:
                o[(x["family"], x["rho"], x["seed"])] = x["result"]
        return o
    rows = [("full", "nl_km_rmall", "ours, all slots (reference)")] + [(n, f"nl_{n}", n) for n in VARIANTS]
    runs = {n: load(s) for n, s, _ in rows}
    import pickle
    SL = {}                                                       # the slot total differs between scenarios (ecc is drawn per seed)
    def slots_of(k):
        if k not in SL:
            SL[k] = float(pickle.load(open(D1 / f"{k[0]}_r{k[1]}_s{k[2]}.pkl", "rb")).ecc.sum())
        return SL[k]
    slots = 1235.0
    p = lambda b: f"{b['mean'] * 100:+6.1f}% ({b['lo'] * 100:+.0f} to {b['hi'] * 100:+.0f})"  # noqa: E731
    out = {}
    for rhos, rl in (((0.5,), "50% load"), ((0.7,), "70% load"), ((0.85,), "85% load"), ((0.5, 0.7, 0.85), "all loads")):
        ks0 = [k for k in runs["full"] if k[1] in rhos and k in base]
        print(f"=== {rl} ===")
        print("%-28s %3s | %9s %9s | %9s %7s | %8s %9s" % ("controller", "n", "containers", "% of slots", "P99 s", "vs B*", "cold", "goodput"))
        b_p99 = np.mean([base[k]["B_STAR"][M] for k in ks0])
        print("%-28s %3d | %9.0f %9s | %9.1f %7s | %8.0f %9.2f" % ("B* (all slots)", len(ks0), np.mean([slots_of(k) for k in ks0]), "100%", b_p99, "—",
              np.mean([base[k]["B_STAR"]["cold_starts"] for k in ks0]), np.mean([base[k]["B_STAR"]["slo_goodput"] for k in ks0])))
        for n, _, lab in rows:
            ks = [k for k in ks0 if k in runs[n]]
            if not ks:
                continue
            r = runs[n]
            cont = np.mean([r[k].get("mean_containers", slots_of(k)) for k in ks])
            share = np.mean([r[k].get("mean_containers", slots_of(k)) / slots_of(k) for k in ks])
            g = [(base[k]["B_STAR"][M] - r[k][M]) / base[k]["B_STAR"][M] for k in ks]
            out[f"{n}|{rl}"] = dict(n=len(ks), containers=float(cont), share_of_slots=float(share), p99=float(np.mean([r[k][M] for k in ks])), vs_bstar=boot(g),
                                    cold=float(np.mean([r[k]["cold_starts"] for k in ks])))
            print("%-28s %3d | %9.0f %8.0f%% | %9.1f %7s | %8.0f %9.2f" % (lab, len(ks), cont, 100 * share,
                  np.mean([r[k][M] for k in ks]), "%+.0f%%" % (100 * np.mean(g)), np.mean([r[k]["cold_starts"] for k in ks]),
                  np.mean([r[k]["slo_goodput"] for k in ks])))
    (d.OUT / "elastic_sweep.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 11, sys.argv[3].split(",") if len(sys.argv) > 3 else list(VARIANTS))
    else:
        analyze()
