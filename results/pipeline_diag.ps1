$env:OMP_NUM_THREADS = "1"
$env:PATH = "C:\Users\ahoor\anaconda3;C:\Users\ahoor\anaconda3\Library\mingw-w64\bin;C:\Users\ahoor\anaconda3\Library\usr\bin;C:\Users\ahoor\anaconda3\Library\bin;C:\Users\ahoor\anaconda3\Scripts;" + $env:PATH
Set-Location "D:\DFPS implementation"
$PY = 'C:\Users\ahoor\anaconda3\python.exe'
& $PY output\data-analysis\bstar_role_diag.py run 11 *> results\bstar_role_diag.log
& $PY output\data-analysis\bstar_role_diag.py analyze *> results\bstar_role_diag.txt
"done $(Get-Date)" | Out-File results\bstar_role_diag.done
