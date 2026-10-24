$env:OMP_NUM_THREADS = "1"
$env:PATH = "C:\Users\ahoor\anaconda3;C:\Users\ahoor\anaconda3\Library\mingw-w64\bin;C:\Users\ahoor\anaconda3\Library\usr\bin;C:\Users\ahoor\anaconda3\Library\bin;C:\Users\ahoor\anaconda3\Scripts;" + $env:PATH
Set-Location "D:\DFPS implementation"
$PY = 'C:\Users\ahoor\anaconda3\python.exe'
# last missing case of ablation 2b (F2 85% seed 2), one worker, in parallel with the sweep
$p2b = Start-Process -FilePath $PY -ArgumentList 'output/data-analysis/d3s_headroom.py','run','--long','--seeds','1-3','--families','F1,F2','--workers','1','--blind','--cand','local_sim' -RedirectStandardOutput results\mech_2b_resume.log -RedirectStandardError results\mech_2b_resume.err.log -WindowStyle Hidden -PassThru
& $PY output\data-analysis\churn_sweep.py 10 *> results\churn_sweep_resume.log
"done $(Get-Date)" | Out-File results\churn_sweep.done
