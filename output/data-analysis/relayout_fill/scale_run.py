"""Full-simulator scale test through the repo code: PL-4, PL-5, PL-5p x on-demand and fixed-budget x 4 sizes x seeds 1-5. python scale_run.py <workers>"""
import os, sys, json, subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
ROOT = Path("D:/DFPS implementation")
S = ROOT / "output" / "data-analysis" / "capw1_scale.py"
SIZES = [(640, 30, 15), (640, 240, 120), (1280, 30, 15), (1280, 480, 240)]
DIRS = {"4": "capW1_scale_incr", "5": "capW1_scale_fill1", "6": "capW1_scale_fill8"}


def path(fast, budget, n, f, w, seed):
    return ROOT / "results" / (DIRS[fast] + ("_fb" if budget == "fixed" else "")) / f"N{n}_F{f}_W{w}_s{seed}.json"


def job(a):
    fast, budget, n, f, w, seed = a
    env = dict(os.environ, FASTPATH=fast, BUDGET=budget)
    r = subprocess.run([sys.executable, str(S), "one", str(n), str(f), str(w), str(seed)], env=env, capture_output=True, text=True, timeout=5400)
    print("done" if r.returncode == 0 else "FAILED " + r.stderr[-400:], a, flush=True)


if __name__ == "__main__":
    todo = []
    for budget in ("", "fixed"):
        for fast in DIRS:
            for n, f, w in SIZES:
                for seed in range(1, 6):
                    p = path(fast, budget, n, f, w, seed)
                    if not (p.exists() and json.loads(p.read_text()).get("done")):
                        todo.append((fast, budget, n, f, w, seed))
    print(len(todo), "runs", flush=True)
    with ThreadPoolExecutor(int(sys.argv[1])) as ex:
        list(ex.map(job, todo))
