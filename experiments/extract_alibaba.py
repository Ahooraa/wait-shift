"""Extract the DAGs the paper uses (jobs under one minute) from the raw Alibaba batch_task.csv into a small JSON file,
so the 800 MB CSV is no longer needed. python -m experiments.extract_alibaba data/alibaba_raw/batch_task.csv data/alibaba_dags_lt60s.json"""
import json
import sys
from collections import Counter

import numpy as np

from dfps.workload import load_alibaba_batch_task

if __name__ == "__main__":
    dags = load_alibaba_batch_task(sys.argv[1], min_tasks=2)
    json.dump(dags, open(sys.argv[2], "w"))
    n = np.array([d["n"] for d in dags])
    depth = []
    for d in dags:
        lv = [0] * d["n"]
        for u, v in d["edges"]:
            lv[v] = max(lv[v], lv[u] + 1)
        depth.append(max(lv) + 1)
    print("qualifying DAG jobs (>=2 tasks, all Terminated, span < 60 s):", len(dags))
    print("tasks per job: mean %.2f median %d p90 %d max %d" % (n.mean(), np.median(n), np.percentile(n, 90), n.max()))
    print("size histogram:", dict(sorted(Counter(n.tolist()).items())[:12]))
    print("depth (critical-path length in tasks): mean %.2f" % np.mean(depth), dict(sorted(Counter(depth).items())[:8]))
    print("edges per job mean %.2f" % np.mean([len(d["edges"]) for d in dags]))
