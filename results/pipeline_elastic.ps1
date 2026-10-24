$env:OMP_NUM_THREADS = "1"
$env:PATH = "C:\Users\ahoor\anaconda3;C:\Users\ahoor\anaconda3\Library\mingw-w64\bin;C:\Users\ahoor\anaconda3\Library\usr\bin;C:\Users\ahoor\anaconda3\Library\bin;C:\Users\ahoor\anaconda3\Scripts;" + $env:PATH
Set-Location "D:\DFPS implementation"
$PY = 'C:\Users\ahoor\anaconda3\python.exe'
# gate: run the sweep only if every correctness test passed; stop (and say so) if any failed
while ($true) {
    $t = if (Test-Path results\elastic_test.out) { Get-Content results\elastic_test.out -Raw } else { "" }
    if ($t -match "all passed") { break }
    if ($t -match "Traceback|AssertionError|Error") { "tests FAILED $(Get-Date)" | Out-File results\elastic_blocked.txt; exit 1 }
    Start-Sleep -Seconds 60
}
& $PY output\data-analysis\elastic_sweep.py run 11 *> results\elastic_sweep.log
& $PY output\data-analysis\elastic_sweep.py analyze *> results\elastic_sweep.txt
"done $(Get-Date)" | Out-File results\elastic.done
