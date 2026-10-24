$env:OMP_NUM_THREADS = "1"
$env:PATH = "C:\Users\ahoor\anaconda3;C:\Users\ahoor\anaconda3\Library\mingw-w64\bin;C:\Users\ahoor\anaconda3\Library\usr\bin;C:\Users\ahoor\anaconda3\Library\bin;C:\Users\ahoor\anaconda3\Scripts;" + $env:PATH
Set-Location "D:\DFPS implementation"
$PY = 'C:\Users\ahoor\anaconda3\python.exe'
# start only after the experiments that are already running or queued have finished
while (-not ((Test-Path results\frozen2dev.done) -and (Test-Path results\timing.done) -and (Test-Path results\period2.done))) { Start-Sleep -Seconds 120 }
& $PY output\data-analysis\admission_sweep.py run 11 *> results\adm2.log
& $PY output\data-analysis\admission_sweep.py analyze *> results\adm2.txt
"done $(Get-Date)" | Out-File results\adm2.done
