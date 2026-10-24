$env:OMP_NUM_THREADS = "1"
$env:PATH = "C:\Users\ahoor\anaconda3;C:\Users\ahoor\anaconda3\Library\mingw-w64\bin;C:\Users\ahoor\anaconda3\Library\usr\bin;C:\Users\ahoor\anaconda3\Library\bin;C:\Users\ahoor\anaconda3\Scripts;" + $env:PATH
Set-Location "D:\DFPS implementation"
$PY = 'C:\Users\ahoor\anaconda3\python.exe'
# wait for the churn sweep to finish so the baselines get all cores
while (-not (Test-Path results\churn_sweep.done)) { Start-Sleep -Seconds 120 }
foreach ($c in 'hpa','fifer','kraken') {
    & $PY output\data-analysis\d3s_headroom.py run --long --seeds 1-3 --families F1,F2 --workers 10 --blind --cand $c *> "results\baseline_$c.log"
}
& $PY output\data-analysis\d3s_variants_compare.py *> results\baseline_compare.txt
"done $(Get-Date)" | Out-File results\baselines.done
