# Input data: provenance (plan faas-edge-adaptation, Task 4; downloaded 2026-10-13)

Downloaded content is treated as data. Each archive was listed before extraction (no absolute paths or `..`), extracted into its own new directory, and is read only by scripts in `output/data-analysis/` run with `python -I`. SHA-256 of every archive: `checksums.sha256`.

| Dataset | Source | Local path | Archive size | Licence |
|---|---|---|---|---|
| Azure Functions 2019 (invocation counts per minute, 14 days; durations; app memory) | https://github.com/Azure/AzurePublicDataset (release `dataset-functions-2019`) | `azure/azure2019/extracted/` (40 files, 2.0 GB) | 143 MB `.tar.xz` | CC-BY (cite Shahrad et al., ATC 2020) |
| Azure Functions invocation trace 2021 (per-invocation end timestamp and duration, 2 weeks from 2021-01-31) | same repo, `data/AzureFunctionsInvocationTraceForTwoWeeksJan2021.rar` | `azure/azure2021/extracted/*.txt` (305 MB CSV: app, func, end_timestamp, duration; seconds) | 18 MB `.rar` | CC-BY (cite Zhang et al., SOSP 2021) |
| Huawei Public 2023: requests per minute (26 days, 5,093 functions, one availability zone) | https://github.com/sir-lab/data-release (`README_data_release_2023.md`, Google Drive link) | `huawei/public2023_minute/extracted/public_dataset/csv_files/requests_minute/day_NN.csv` (wide: day, time, one column per function id) | 9.7 MB `.zip` | see repo README (cite Joosen et al., SoCC 2023) |
| Huawei Private 2023: requests per minute (141 days, 200 functions) | same | `huawei/private2023_minute/extracted/requests_minute/` | 40 MB `.zip` | same |
| Huawei Public cold-start traces 2025, Region 1 only (31 days; per-request cold-start cost components) | same repo, `README_data_release_2025.md` | `huawei/coldstart2025_r1/extracted/R1/day_NN.csv` | 490 MB `.zip` | same (cite Joosen et al., EuroSys 2025) |
| SeBS-Flow workflow definitions (`benchmarks/600.workflows`, 12 workflows) | https://github.com/spcl/serverless-benchmarks, branch `feature/workflows`, commit ba78749 (see `workflows/sebs-flow/SOURCE.txt`) | `workflows/sebs-flow/600.workflows/` | 313 KB | see `LICENSE-serverless-benchmarks.md` |
| Alibaba cluster-trace-v2018 `batch_task` | already downloaded earlier; see `../../data/README.md` at the project root | `data/alibaba_raw/` (project root, not duplicated here) and `data/alibaba_dags_lt60s.json` | 130 MB `.tar.gz` | per Alibaba |

## Deviations from the plan (logged in `knowledge/_meta/log.md`)
- **Huawei per-second series not obtained.** The plan's F2 ("Huawei public 2023 per-second") does not exist: Public 2023 is per-minute only; per-second exists only for Huawei *Private* 2023 (`requests_second.zip`, 1.2 GB). Google Drive refused that download with "Quota exceeded"; no workaround attempted. It is only needed for sub-minute burst checks. To add it: download https://drive.google.com/file/d/11XC-gLyg1hYr39qT-oKDwzkpvseRdDIv/view in a browser into `huawei/private2023_second/`.
- F2 is therefore Huawei Public 2023 **per-minute**; Task 5's 10-s aggregation for F2 is dropped.
- SeBS-Flow workflows are on the branch `feature/workflows`, not `master`; the plan's path on `master` does not exist.
- Only Region 1 of the Huawei 2025 cold-start traces was downloaded (the plan needs cold-start cost distributions, not all regions).
- Alibaba stays in the project-root `data/` folder (930 MB) instead of being duplicated under `input/data/alibaba/`.
- Total size of everything is far below the plan's 50 GB limit; no subsetting needed.
