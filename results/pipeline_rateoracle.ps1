Set-Location "D:\DFPS implementation"
$env:OMP_NUM_THREADS = "1"
py -3 output/data-analysis/d3s_headroom.py run --long --future rate --seeds 1-3 --families F1,F2 --workers 10 *> results\d3s_rateoracle_run.log
py -3 output/data-analysis/d3s_rateoracle_compare.py *> results\d3s_rateoracle_compare.log
