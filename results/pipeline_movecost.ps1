$env:OMP_NUM_THREADS = "1"
$env:PATH = "C:\Users\ahoor\anaconda3;C:\Users\ahoor\anaconda3\Library\mingw-w64\bin;C:\Users\ahoor\anaconda3\Library\usr\bin;C:\Users\ahoor\anaconda3\Library\bin;C:\Users\ahoor\anaconda3\Scripts;" + $env:PATH
Set-Location "D:\DFPS implementation"
$PY = 'C:\Users\ahoor\anaconda3\python.exe'
while (-not (Test-Path results\km_scratch.done)) { Start-Sleep -Seconds 60 }
& $PY output\data-analysis\move_cost_sweep.py run 11 *> results\move_cost.log
& $PY output\data-analysis\move_cost_sweep.py analyze *> results\move_cost.txt
"done $(Get-Date)" | Out-File results\move_cost.done
