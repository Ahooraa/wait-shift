$env:OMP_NUM_THREADS = "1"
$env:PATH = "C:\Users\ahoor\anaconda3;C:\Users\ahoor\anaconda3\Library\mingw-w64\bin;C:\Users\ahoor\anaconda3\Library\usr\bin;C:\Users\ahoor\anaconda3\Library\bin;C:\Users\ahoor\anaconda3\Scripts;" + $env:PATH
Set-Location "D:\DFPS implementation"
& 'C:\Users\ahoor\anaconda3\python.exe' output\data-analysis\churn_sweep.py 11 *> results\churn_sweep.log
"done $(Get-Date)" | Out-File results\churn_sweep.done
