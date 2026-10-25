"""Offline ceilings for slack-aware ordering (A) and for fixing fracture / co-location (B1, B2) on traced full-length runs of our controller.
Six scenarios; results in results/wfstress/bounds/.   python bounds_run.py run [workers] | show"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import workflow_stress as w  # noqa: E402

OUT = w.RUNS / "bounds"
JOBS = [(("chain12", "F1", 0.85, 1), 10), (("wide16", "F1", 0.85, 1), 10), (("layered12", "F1", 0.85, 1), 10),
        (("mix", "F1", 0.85, 1), 10), (("mix", "F1", 0.85, 1), 1), (("mix", "F2", 0.85, 1), 10)]


def go(j):
    scen, k = j
    return w.one((scen, k, "ours", w.tstars()[scen[1]]), out=OUT / f"{w.tag(scen, k)}.json", with_bounds=True)


def show():
    print("%-24s | base P99 | A_unmoved        A_all            | B1 co-location   | B2 fracture      | replay error" % "scenario")
    for f in sorted(OUT.glob("*.json")):
        x = json.loads(f.read_text())
        b = x.get("bounds") or {}
        if "base_p99" not in b:
            print(f.stem, str(b.get("error", ""))[-200:])
            continue
        s = lambda k: "%6.0f (%+5.1f%%)" % (b[k + "_p99"], 100 * (b[k + "_p99"] / b["base_p99"] - 1))
        print("%-24s | %7.0f | %s %s | %s | %s | %.1e" % (f.stem, b["base_p99"], s("A_unmoved"), s("A_all"), s("B1_colocation"), s("B2_fracture"), b["replay_error"]))


if __name__ == "__main__":
    if sys.argv[1] == "run":
        OUT.mkdir(parents=True, exist_ok=True)
        with ProcessPoolExecutor(int(sys.argv[2]) if len(sys.argv) > 2 else 4) as ex:
            for r in ex.map(go, JOBS):
                print("done", r, flush=True)
    else:
        show()
