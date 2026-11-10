"""Full-simulator test of the candidates: FROZEN-3 (frozen3i configuration), only the re-layout function replaced, repo code untouched.
Same cases, seeds and +-1 ms clock shifts as frozen3i / _p1 / _p2.   python sim_pl5.py run <workers> <set> <variant...> | report <set> <variant...>      set = dev | heldout"""
import json, pickle, sys, time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in (Path("D:/DFPS implementation"), Path.home() / "DFPS-implementation") if p.exists())
DA = ROOT / "output" / "data-analysis"
for p in (str(ROOT), str(DA), str(HERE)):
    if p not in sys.path:
        sys.path.insert(0, p)
OUT = ROOT / "results" / "relayout_fill"
W1, ROWS = ROOT / "results" / "capW1_light", ROOT / "results" / "capW1_rows"
DURATION, WARMUP = 900.0, 60.0
CLOCK = {"": 0.0, "_p1": 0.001, "_p2": -0.001}


class _Ecc(np.ndarray):
    """Per-server capacity with slack; a plain .sum() still reports the original budget, so the container targets do not grow."""
    def sum(self, *a, **k):
        if not a and not k and getattr(self, "_S", None) is not None:
            return self._S
        return super().sum(*a, **k)


def cases(which):
    seeds = (1, 2, 3) if which == "dev" else (7, 8, 9, 10)
    return [f"{f}_r{r}_s{s}" for f in ("F1", "F2") for r in (0.5, 0.7, 0.85) for s in seeds]


def run_job(a):
    tg, var, suf = a
    out = OUT / f"{tg}.{var}{suf}.json"
    if out.exists():
        return str(out)
    OUT.mkdir(exist_ok=True)
    try:
        assert np.__version__.startswith("1."), "use the Anaconda interpreter"
        import yaml
        import dfps.controllers as K
        _argv, sys.argv = sys.argv, sys.argv[:1]
        import pl5
        sys.argv = _argv
        K._place_incremental = pl5.make(**pl5.VARIANTS[var])
        A = yaml.safe_load((ROOT / "config" / "assumptions.yaml").read_text(encoding="utf-8"))
        P = pickle.load(open(W1 / f"{tg}.sc.pkl", "rb"))
        sc, X0 = P["sc"], P["X0"]
        assert sc.meta.get("capacity_model") == "CAP-W1"
        if var.startswith("oracle"):                                     # fragmentation oracle: every server gets room for one more largest container, the budget (ecc.sum()) stays the original
            e = (sc.ecc + int(np.ceil(np.max(sc.fw)))).view(_Ecc)
            e._S = sc.ecc.sum()
            sc.ecc = e
        seed, fam = int(tg.split("_s")[1]), tg.split("_r")[0]
        t0 = time.time()
        from dfps import dispatchers as D
        from dfps.dispatch_priority import QueuePriority
        from dfps.o3s import O3SimAdjuster
        from dfps.sim import Sim
        from dfps.variants import make_adjuster, sim_kwargs
        from frozen2 import FROZEN3_INCR, FROZEN3_DISPATCHER, MOVE_PERIOD_S
        kw = sim_kwargs("B_STAR", A)
        kw.update(warmup=WARMUP, duration=DURATION, retry_min_interval=1.0, retry_max_attempts=10)
        kw["dispatcher"] = D.DISPATCHERS[FROZEN3_DISPATCHER]
        kw["queue_priority"] = QueuePriority("full", aging=2.0)
        adj = O3SimAdjuster(make_adjuster("B_STAR", A, seed=seed + 300), MOVE_PERIOD_S[fam] + CLOCK[suf], epoch=60.0, horizon=30.0, K=8,
                            seed=seed + 800, warmup=WARMUP, blind=True, cand_mode="nosim", churn=dict(FROZEN3_INCR, lam=0.5))
        kw["interval"] = adj.next_interval
        sim = Sim(sc, X0.copy(), adjuster=adj, seed=seed + 400, **kw)
        r = sim.run()
        sim.check_invariants()
        r["wall_s"] = time.time() - t0
        out.write_text(json.dumps(dict(capacity_model="CAP-W1", case=tg, ctrl=var + suf, result=r)))
    except Exception:
        import traceback
        out.with_suffix(".err").write_text(traceback.format_exc())
        return str(out) + " FAILED"
    return str(out)


def base(tg, suf):
    return json.loads((ROWS / f"{tg}.frozen3i{suf}.json").read_text())["result"]


def new(tg, var, suf):
    p = OUT / f"{tg}.{var}{suf}.json"
    return json.loads(p.read_text())["result"] if p.exists() else None


def gm_ci(x, seed=0, B=4000):
    x = np.log(np.asarray(x)); rng = np.random.default_rng(seed)
    b = x[rng.integers(0, x.size, (B, x.size))].mean(axis=1)
    return np.exp(x.mean()), np.exp(np.percentile(b, 2.5)), np.exp(np.percentile(b, 97.5))


METRICS = ("p99_makespan", "p95_makespan", "p50_makespan", "avg_makespan", "n_moved", "cold_starts", "mb_relocated", "n_placements_applied")


def report(which, variants):
    cs = cases(which)
    for var in variants:
        have = [c for c in cs if all(new(c, var, s) is not None for s in CLOCK)]
        print(f"== {var}: {len(have)} of {len(cs)} cases complete ({which}); ratio to frozen3i, paired clock by clock, mean over the three clocks per case, geometric mean over cases [95% case bootstrap]")
        if not have:
            continue
        for m in METRICS:
            r = []
            for c in have:
                v = [(new(c, var, s)[m] + 1e-9) / (base(c, s)[m] + 1e-9) for s in CLOCK]
                r.append(np.exp(np.mean(np.log(v))))
            g, lo, hi = gm_ci(r)
            print(f"   {m:22s} {g:.3f} [{lo:.3f}, {hi:.3f}]   cases better/worse {sum(x < 1 for x in r)}/{sum(x > 1 for x in r)}")
        for fam in ("F1", "F2"):
            for rho in (0.5, 0.7, 0.85):
                sub = [c for c in have if c.startswith(f"{fam}_r{rho}_")]
                if sub:
                    r = [np.exp(np.mean(np.log([new(c, var, s)["p99_makespan"] / base(c, s)["p99_makespan"] for s in CLOCK]))) for c in sub]
                    print(f"      P99 {fam} rho {rho}: {np.exp(np.mean(np.log(r))):.3f}  ({len(sub)} cases)")
        noise = [np.exp(np.mean(np.abs(np.log([base(c, a)["p99_makespan"] / base(c, b)["p99_makespan"] for a, b in (("", "_p1"), ("", "_p2"), ("_p1", "_p2"))])))) for c in have]
        print(f"   noise floor: frozen3i against its own clock shifts, typical |P99 ratio| {np.exp(np.mean(np.log(noise))):.3f}")


if __name__ == "__main__":
    if sys.argv[1] == "run":
        w, which, vs = int(sys.argv[2]), sys.argv[3], sys.argv[4:]
        todo = [(c, v, s) for v in vs for c in cases(which) for s in CLOCK if not (OUT / f"{c}.{v}{s}.json").exists()]
        print(len(todo), "runs", flush=True)
        with ProcessPoolExecutor(w) as ex:
            for r in ex.map(run_job, todo):
                print("done", r, flush=True)
    else:
        report(sys.argv[2], sys.argv[3:])
