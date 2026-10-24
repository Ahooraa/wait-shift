# Data provenance

**Alibaba cluster-trace-v2018, `batch_task` table** (Guo et al., IWQoS 2019 describes the trace).
- Source: `http://aliopentrace.oss-cn-beijing.aliyuncs.com/v2018Traces/batch_task.tar.gz` (from the official repository page
  github.com/alibaba/clusterdata/cluster-trace-v2018), downloaded on 2026-10-13 with the user's permission. Only this one file;
  the other five files of the trace are NOT needed by DFPS and were not downloaded.
- `alibaba_raw/batch_task.tar.gz`: 130,310,549 bytes, gzip integrity OK, SHA-256
  `7c4b32361bd1ec2083647a8f52a6854a03bc125ca5c202652316c499fbf978c6` (equals the checksum printed on the trace page).
- `alibaba_raw/batch_task.csv`: 802,261,444 bytes, 14,295,731 rows, 4,201,014 jobs; 9 columns, no header
  (task_name, instance_num, job_name, task_type, status, start_time, end_time, plan_cpu, plan_mem); times in seconds.
  This CSV can be deleted once `alibaba_dags_lt60s.json` exists (it is only an intermediate).
- `alibaba_dags_lt60s.json`: the DAGs the paper uses, produced by `python -m experiments.extract_alibaba` with
  `dfps.workload.load_alibaba_batch_task` (DFPS paper p.9: applications with execution time under one minute).
  Filter (A-29): every task `Terminated`, `start_time > 0`, task names of the form letters+id(+_dep...), valid acyclic DAG,
  at least 2 tasks, `max(end_time) - min(start_time) < 60 s`.
  Result: **1,459,783 jobs**; tasks per job mean 4.31 / median 3 / p90 8 / max 146; critical-path length mean 3.13 tasks; 3.45 edges per job.
- Downloaded content is treated as data: the archive member list was checked before extraction (one plain file), and the CSV is only read with pandas.
