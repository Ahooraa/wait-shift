"""Re-extract the Alibaba DAGs together with each task's resource request (plan_cpu, plan_mem), 2026-11-02.

The original extraction (extract_alibaba.py) kept only the DAG shape. The container-size model needs the task profiles, so
this writes a second file with the same jobs in the same order plus `plan_cpu` / `plan_mem` per task, and refuses to finish
unless (job, n, edges) match the existing file exactly -- an index into one file must be an index into the other.

  python -m experiments.extract_alibaba_profiles data/alibaba_raw/batch_task.csv data/alibaba_dags_lt60s.json \
      data/alibaba_dags_lt60s_profiles.json
"""
import json
import sys

import numpy as np

from dfps.workload import load_alibaba_batch_task

if __name__ == "__main__":
    raw, old_path, out_path = sys.argv[1:4]
    dags = load_alibaba_batch_task(raw, min_tasks=2, with_profile=True)
    old = json.load(open(old_path))
    assert len(dags) == len(old), f"job count differs: {len(dags)} vs {len(old)}"
    for i, (a, b) in enumerate(zip(dags, old)):
        assert a["job"] == b["job"] and a["n"] == b["n"] and [list(e) for e in a["edges"]] == [list(e) for e in b["edges"]], \
            f"job {i} differs from the existing extraction"
    json.dump(dags, open(out_path, "w"))
    mem = np.array([m for d in dags for m in d["plan_mem"] if m is not None], dtype=float)
    cpu = np.array([c for d in dags for c in d["plan_cpu"] if c is not None], dtype=float)
    miss_m = sum(m is None for d in dags for m in d["plan_mem"])
    miss_c = sum(c is None for d in dags for c in d["plan_cpu"])
    print(f"{len(dags)} jobs identical to {old_path}; tasks {mem.size + miss_m}, missing plan_mem {miss_m}, missing plan_cpu {miss_c}")
    print("plan_mem  quantiles 5/25/50/75/95/99:", np.round(np.percentile(mem, [5, 25, 50, 75, 95, 99]), 3), "max", mem.max())
    print("plan_cpu  quantiles 5/25/50/75/95/99:", np.round(np.percentile(cpu, [5, 25, 50, 75, 95, 99]), 1), "max", cpu.max())
