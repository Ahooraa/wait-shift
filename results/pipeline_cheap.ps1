Set-Location "D:\DFPS implementation"
$env:OMP_NUM_THREADS = "1"
$env:PATH = "C:\Users\ahoor\anaconda3;C:\Users\ahoor\anaconda3\Library\mingw-w64\bin;C:\Users\ahoor\anaconda3\Library\usr\bin;C:\Users\ahoor\anaconda3\Library\bin;C:\Users\ahoor\anaconda3\Scripts;" + $env:PATH
$PY = 'C:\Users\ahoor\anaconda3\python.exe'
# Cheap stages run in parallel on the 2 spare cores so they finish overnight; the main pipeline skips cases already done here.
$common = @('output/data-analysis/d3s_headroom.py','run','--long','--seeds','1-3','--families','F1,F2','--workers','2')
& $PY @common --blind --cand nosim *> results\cheap_2a_nosim.log
& $PY output/data-analysis/d3s_variants_compare.py *> results\d3s_variants_compare.log
& $PY @common --blind --cand keep_bottleneck --horizon 30 *> results\cheap_3c_keep_bottleneck_H30.log
& $PY output/data-analysis/d3s_variants_compare.py *> results\d3s_variants_compare.log
"done $(Get-Date)" | Out-File results\pipeline_cheap.done
