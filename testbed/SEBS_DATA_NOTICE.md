# Attribution for `sebs_profiles.json`

`testbed/sebs_profiles.json` is a summary derived from measurement data published in:

Larissa Schmid, Marcin Copik, Alexandru Calotoiu, Laurin Brandner, Anne Koziolek, Torsten Hoefler.
*Replication Package for "SeBS-Flow: Benchmarking Serverless Cloud Function Workflows"*. Zenodo, 2025.
DOI: [10.5281/zenodo.14907321](https://doi.org/10.5281/zenodo.14907321). Licence: Creative Commons Attribution 4.0 (CC BY 4.0).

**What was changed:** the original data (one row per measured function invocation, 622 MB) is not included. The table keeps, for each of
the 25 functions of the six applications used here, the quantiles of the provider-measured execution duration, the median cold-start
initialisation time, the median bytes read from and written to storage, and the memory used, taken from the AWS 2024 measurements.
One function (Trip Booking's failing `confirm`) has no measured row and is filled in from other functions of the same application;
the table marks it. Produced by `testbed/derive_sebs_profile.py`.
