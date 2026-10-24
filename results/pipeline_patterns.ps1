$env:OMP_NUM_THREADS = "1"
$env:PATH = "C:\Users\ahoor\anaconda3;C:\Users\ahoor\anaconda3\Library\mingw-w64\bin;C:\Users\ahoor\anaconda3\Library\usr\bin;C:\Users\ahoor\anaconda3\Library\bin;C:\Users\ahoor\anaconda3\Scripts;" + $env:PATH
Set-Location "D:\DFPS implementation"
$PY = 'C:\Users\ahoor\anaconda3\python.exe'
while (-not (Test-Path results\qaware.done)) { Start-Sleep -Seconds 120 }
& $PY output\data-analysis\pattern_scenarios.py run 11 *> results\patterns.log
& $PY output\data-analysis\pattern_scenarios.py analyze *> results\patterns.txt
"done $(Get-Date)" | Out-File results\patterns.done
