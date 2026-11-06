import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
ROOT = Path("D:/DFPS implementation"); sys.path.insert(0, str(ROOT / "output" / "data-analysis")); sys.path.insert(0, str(ROOT))
import capw1_ondemand as O, capw1_rows as C
if __name__ == "__main__":
    jobs = [(c, a, O.DURATION, str(O.OUT)) for a in ("frozen3_od_e30_u65", "frozen3_od_e30_u50") for c in C.dev()]
    print(len(jobs), "runs", flush=True)
    with ProcessPoolExecutor(4, initializer=O.H.I._low_priority) as ex:
        for r in ex.map(O.run_job, jobs):
            print("done", r, flush=True)
