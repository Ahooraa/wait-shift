"""FROZEN-1 on held-out seeds, at 60 s and 30 s re-layout cadence (2026-10-23).

Configuration (results/frozen_config.json, decided by the user): busiest-first sizing + incremental soft-routing placement
(tau 1, origin weight 1, NO waiting term) + finish-time request moves with no cap; B* annealing off; fixed slot budget; no foresight.
Nothing is changed after the held-out results are seen. Two cadences are run, and they are the only configurations run on the
held-out seeds: fz60 (the design) and fz30 (the 30 s variant the user asked to test).

  held-out     seeds 4-10 x Azure/Huawei x 50/70/85% load = 42 cases per cadence (never used while developing anything)
  development  seeds 1-3 x the same = 18 cases; fz60 is the existing nl_qa_noqueue result (copied), fz30 is new

Files <case>.O3S_h120_blind_nosim_nl_fz60 / fz30 .json. Reference methods (B*, RL, RL_CAL) exist for every case.

  python output/data-analysis/frozen_sweep.py run [workers]   |   analyze
"""
import json
import shutil
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(ROOT))
import d3s_headroom as d  # noqa: E402
from new_layer_sweep import BASE  # noqa: E402

FROZEN = dict(BASE, placement="qaware", origin_weight=1.0, rebal_max=10 ** 9, tau=1.0, queue_term=False)
EX = ("B_STAR", "RL", "RL_CAL")
M = "p99_makespan"
HELD, DEV = tuple(range(4, 11)), (1, 2, 3)


def cases(seeds):
    return [(f, r, s) for f in ("F1", "F2") for r in d.RHOS for s in seeds]


def path(case, e):
    f, r, s = case
    return d.RUNS / f"{d.tag(f, r, s)}.O3S_h120_blind_nosim_nl_fz{e}.json"


def run(workers, reverse=False):
    T = json.loads((d.OUT / "g2_tstar.json").read_text())
    T = {f: float(T["families"][f]["T_star"]) for f in ("F1", "F2")}
    for c in cases(DEV):                                              # development 60 s = the existing nl_qa_noqueue run
        src = d.RUNS / f"{d.tag(c[0], c[1], c[2])}.O3S_h120_blind_nosim_nl_qa_noqueue.json"
        if src.exists() and not path(c, 60).exists():
            shutil.copyfile(src, path(c, 60))
    order = [(e, cases(HELD)) for e in (60, 30)] + [(30, cases(DEV))]       # held-out first, then the development 30 s
    jobs = []
    for e, cs in order:
        part = [(d.tag(f, r, s), str(path((f, r, s), e)), s, T[f], d.DURATION, float(e), 120.0, 5, True, None, "nosim", dict(FROZEN))
                for f, r, s in cs]
        part.sort(key=lambda j: -float(j[0].split("_r")[1].split("_")[0]))
        jobs += [j for j in part if not Path(j[1]).exists()]
    if reverse:                                  # a second pool that works from the other end of the list (the lightest cases first)
        jobs = jobs[::-1]
    print(f"{len(jobs)} runs to do" + (" (reverse order)" if reverse else ""), flush=True)
    with ProcessPoolExecutor(workers) as ex:
        for done in ex.map(d.job, jobs):
            print("done", done, flush=True)


def analyze():
    from d1_rlla import BASE as B1, D1, boot
    base = {}
    for d_ in (D1, B1):
        for f in d_.glob("*.json"):
            x = json.loads(f.read_text())
            if x.get("ctrl") in EX:
                base.setdefault((x["family"], x["rho"], x["seed"]), {})[x["ctrl"]] = x["result"]
    p = lambda b: f"{b['mean'] * 100:+6.1f}% ({b['lo'] * 100:+.0f} to {b['hi'] * 100:+.0f})"  # noqa: E731
    out = {}
    for tag_, seeds in (("HELD-OUT seeds 4-10", HELD), ("development seeds 1-3", DEV)):
        r = {e: {c: json.loads(path(c, e).read_text())["result"] for c in cases(seeds) if path(c, e).exists()} for e in (60, 30)}
        print(f"\n##### {tag_}")
        for e in (60, 30):
            print(f"  cadence {e} s: {len(r[e])} of {len(cases(seeds))} cases done")
        for lab, rh in (("50% load", (0.5,)), ("70-85% load", (0.7, 0.85)), ("all loads", (0.5, 0.7, 0.85))):
            print(f"  -- {lab}")
            for e in (60, 30):
                ks = [c for c in r[e] if c[1] in rh and all(m in base.get((c[0], c[1], c[2]), {}) for m in EX)]
                if not ks:
                    continue
                key = lambda c: (c[0], c[1], c[2])  # noqa: E731
                vb = [(base[key(c)]["B_STAR"][M] - r[e][c][M]) / base[key(c)]["B_STAR"][M] for c in ks]
                be = [min(base[key(c)][m][M] for m in EX) for c in ks]
                ve = [(b - r[e][c][M]) / b for b, c in zip(be, ks)]
                vr = [(base[key(c)]["RL"][M] - r[e][c][M]) / base[key(c)]["RL"][M] for c in ks]
                row = dict(n=len(ks), vs_bstar=boot(vb), vs_rl=boot(vr), vs_best=boot(ve), wins=int(sum(x > 0 for x in ve)),
                           p99=float(np.mean([r[e][c][M] for c in ks])), cold=float(np.mean([r[e][c]["cold_starts"] for c in ks])))
                out[f"{tag_}|{e}|{lab}"] = row
                print("     %2d s  n=%2d  P99 %6.1f s | vs B* %s | vs RL %s | vs best %s wins %2d/%d | cold %5.0f" % (
                    e, len(ks), row["p99"], p(row["vs_bstar"]), p(row["vs_rl"]), p(row["vs_best"]), row["wins"], len(ks), row["cold"]))
            ks = [c for c in r[60] if c in r[30] and c[1] in rh]
            if ks:
                g = [(r[60][c][M] - r[30][c][M]) / r[60][c][M] for c in ks]
                b = boot(g)
                out[f"{tag_}|30vs60|{lab}"] = dict(n=len(ks), gain=b, wins=int(sum(x > 0 for x in g)))
                print("     30 s vs 60 s: P99 %s, better in %d/%d | cold starts %.0f vs %.0f" % (
                    p(b), sum(x > 0 for x in g), len(ks), np.mean([r[30][c]["cold_starts"] for c in ks]), np.mean([r[60][c]["cold_starts"] for c in ks])))
        ks = [c for c in r[60] if c in r[30]]
        for fam in ("F1", "F2"):
            kk = [c for c in ks if c[0] == fam]
            if kk:
                g = [(r[60][c][M] - r[30][c][M]) / r[60][c][M] for c in kk]
                print(f"     {'Azure' if fam == 'F1' else 'Huawei'} 30 s vs 60 s: {p(boot(g))}, better in {sum(x > 0 for x in g)}/{len(kk)}")
    (d.OUT / "frozen_sweep.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 8, reverse=len(sys.argv) > 3 and sys.argv[3] == "reverse")
    else:
        analyze()
