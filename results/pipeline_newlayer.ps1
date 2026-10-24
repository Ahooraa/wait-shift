$env:OMP_NUM_THREADS = "1"
$env:PATH = "C:\Users\ahoor\anaconda3;C:\Users\ahoor\anaconda3\Library\mingw-w64\bin;C:\Users\ahoor\anaconda3\Library\usr\bin;C:\Users\ahoor\anaconda3\Library\bin;C:\Users\ahoor\anaconda3\Scripts;" + $env:PATH
Set-Location "D:\DFPS implementation"
$PY = 'C:\Users\ahoor\anaconda3\python.exe'
& $PY output\data-analysis\new_layer_sweep.py 11 *> results\new_layer_sweep.log
& $PY output\data-analysis\new_layer_compare.py *> results\new_layer_compare.txt
"done $(Get-Date)" | Out-File results\new_layer.done
