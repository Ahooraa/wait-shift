$env:OMP_NUM_THREADS = "1"
$env:PATH = "C:\Users\ahoor\anaconda3;C:\Users\ahoor\anaconda3\Library\mingw-w64\bin;C:\Users\ahoor\anaconda3\Library\usr\bin;C:\Users\ahoor\anaconda3\Library\bin;C:\Users\ahoor\anaconda3\Scripts;" + $env:PATH
Set-Location "D:\DFPS implementation"
$PY = 'C:\Users\ahoor\anaconda3\python.exe'
& $PY output\data-analysis\cadence_sweep.py run 6 *> results\cadence.log
& $PY output\data-analysis\cadence_sweep.py analyze *> results\cadence.txt
"done $(Get-Date)" | Out-File results\cadence.done
