$env:OMP_NUM_THREADS = "1"
$env:PATH = "C:\Users\ahoor\anaconda3;C:\Users\ahoor\anaconda3\Library\mingw-w64\bin;C:\Users\ahoor\anaconda3\Library\usr\bin;C:\Users\ahoor\anaconda3\Library\bin;C:\Users\ahoor\anaconda3\Scripts;" + $env:PATH
Set-Location "D:\DFPS implementation"
$PY = 'C:\Users\ahoor\anaconda3\python.exe'
while (-not (Test-Path results\placement.done)) { Start-Sleep -Seconds 120 }
& $PY output\data-analysis\placement_sweep.py 11 km_rmall *> results\km_rmall.log
& $PY output\data-analysis\new_layer_compare.py *> results\km_rmall_compare.txt
"done $(Get-Date)" | Out-File results\km_rmall.done
