$env:OMP_NUM_THREADS = "1"
$env:PATH = "C:\Users\ahoor\anaconda3;C:\Users\ahoor\anaconda3\Library\mingw-w64\bin;C:\Users\ahoor\anaconda3\Library\usr\bin;C:\Users\ahoor\anaconda3\Library\bin;C:\Users\ahoor\anaconda3\Scripts;" + $env:PATH
Set-Location "D:\DFPS implementation"
$PY = 'C:\Users\ahoor\anaconda3\python.exe'
while (-not (Test-Path results\km_rmall.done)) { Start-Sleep -Seconds 120 }
& $PY output\data-analysis\placement_sweep.py 11 km_scratch *> results\km_scratch.log
& $PY output\data-analysis\new_layer_compare.py *> results\placement_compare_final.txt
"done $(Get-Date)" | Out-File results\km_scratch.done
