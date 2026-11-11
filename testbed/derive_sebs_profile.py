#!/usr/bin/env python3
"""Derive the per-function profile table of the testbed workload from the SeBS-Flow replication package (testbed/DESIGN.md, DEV-T2).

    ~/venv-dfps/bin/python -I testbed/derive_sebs_profile.py PATH/TO/ReplicationPackage-SeBS-Flow  [--out testbed/sebs_profiles.json]

Reads sebs-flow-artifact/perf-cost/<benchmark>/aws/2024/ (one row per measured function invocation) and writes a small JSON table: per
function the quantiles of the provider-measured execution duration, the cold-start initialisation time, the median blob bytes uploaded
and downloaded, and the memory used. The dataset itself stays outside the repository (1.1 GB); this table is a derived summary.

Data: Schmid, Copik, Calotoiu, Brandner, Koziolek, Hoefler, "Replication Package for 'SeBS-Flow: Benchmarking Serverless Cloud Function
Workflows'", Zenodo, doi 10.5281/zenodo.14907321, licence CC BY 4.0 (attribution in testbed/SEBS_DATA_NOTICE.md).

Choices (all stated in the output file): platform AWS, year 2024; durations from the warm run (steady state) and, for 1000Genome, which has
no warm run, from the burst run; durations are provider.execution_duration (microseconds, without the initialisation), taken from
invocations that were not cold when there are at least 30 of them; cold-start time is provider.init_duration of the cold invocations of the
burst run. A function that has no measured row (Trip Booking's failing `confirm`) is listed with `stand_in` naming the functions whose pooled
data stand in for it.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

WORKFLOWS = {  # benchmark: (warm or burst file used for durations, burst file used for cold starts)
    "650.vid": ("warm_2048", "burst_2048"),
    "6200.trip-booking": ("warm_128", "burst_128"),
    "660.map-reduce": ("warm_256", "burst_256"),
    "680.excamera": ("warm_256", "burst_256"),
    "690.ml": ("warm_1024", "burst_1024"),
    "6100.1000-genome": ("burst_2048", "burst_2048"),
}
STAND_IN = {"6200.trip-booking": {"confirm": ["reserve_flight", "reserve_hotel", "reserve_rental"]}}
QUANTILES = np.linspace(0.0, 1.0, 101)


def profile(root: Path):
    base = root / "sebs-flow-artifact" / "perf-cost"
    out = {"source": {"title": "Replication Package for 'SeBS-Flow: Benchmarking Serverless Cloud Function Workflows'",
                      "authors": "Schmid, Copik, Calotoiu, Brandner, Koziolek, Hoefler", "doi": "10.5281/zenodo.14907321", "license": "CC BY 4.0",
                      "platform": "aws", "year": 2024}, "workflows": {}}
    for bench, (dur_mode, cold_mode) in WORKFLOWS.items():
        dur = pd.read_csv(base / bench / "aws" / "2024" / f"{dur_mode}_processed.csv")
        cold = pd.read_csv(base / bench / "aws" / "2024" / f"{cold_mode}_processed.csv")
        fns = {}
        for name, g in dur.groupby("func"):
            warm = g[g["is_cold"] == False]                                     # noqa: E712
            use = warm if len(warm) >= 30 else g
            q = (use["provider.execution_duration"] / 1e6).quantile(QUANTILES).to_numpy()
            c = cold[(cold["func"] == name) & (cold["is_cold"] == True)]        # noqa: E712
            fns[name] = {"n_duration": int(len(use)), "duration_s_q": [round(float(x), 6) for x in q],
                         "duration_s_mean": round(float((use["provider.execution_duration"] / 1e6).mean()), 6),
                         "cold_init_s_median": round(float(c["provider.init_duration"].median() / 1e6), 4) if len(c) else None,
                         "cold_init_s_n": int(len(c)),
                         "blob_upload_bytes_median": float(g["blob.upload"].median()), "blob_download_bytes_median": float(g["blob.download"].median()),
                         "mem_used_mb_median": float(g["max_mem_used"].median()), "mem_used_mb_p95": float(g["max_mem_used"].quantile(0.95))}
        for name, srcs in STAND_IN.get(bench, {}).items():
            if name not in fns:
                pooled = pd.concat([dur[dur["func"] == s] for s in srcs])
                q = (pooled["provider.execution_duration"] / 1e6).quantile(QUANTILES).to_numpy()
                fns[name] = {"stand_in": srcs, "n_duration": int(len(pooled)), "duration_s_q": [round(float(x), 6) for x in q],
                             "duration_s_mean": round(float((pooled["provider.execution_duration"] / 1e6).mean()), 6),
                             "cold_init_s_median": float(np.median([fns[s]["cold_init_s_median"] for s in srcs])), "cold_init_s_n": 0,
                             "blob_upload_bytes_median": 0.0, "blob_download_bytes_median": 0.0,
                             "mem_used_mb_median": float(np.median([fns[s]["mem_used_mb_median"] for s in srcs])),
                             "mem_used_mb_p95": float(np.median([fns[s]["mem_used_mb_p95"] for s in srcs]))}
        out["workflows"][bench] = {"duration_run": f"aws/2024/{dur_mode}", "cold_run": f"aws/2024/{cold_mode}",
                                   "requests_in_duration_run": int(dur["request_id"].nunique()), "functions": fns}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("package", help="folder ReplicationPackage-SeBS-Flow")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "sebs_profiles.json"))
    a = ap.parse_args(argv)
    prof = profile(Path(a.package))
    Path(a.out).write_text(json.dumps(prof, indent=1) + "\n")
    n = sum(len(w["functions"]) for w in prof["workflows"].values())
    print(f"wrote {a.out}: {len(prof['workflows'])} workflows, {n} functions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
