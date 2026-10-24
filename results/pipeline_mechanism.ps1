Set-Location "D:\DFPS implementation"
$env:OMP_NUM_THREADS = "1"
$env:PATH = "C:\Users\ahoor\anaconda3;C:\Users\ahoor\anaconda3\Library\mingw-w64\bin;C:\Users\ahoor\anaconda3\Library\usr\bin;C:\Users\ahoor\anaconda3\Library\bin;C:\Users\ahoor\anaconda3\Scripts;" + $env:PATH   # detached (WMI) launch has no conda PATH: workers crashed loading numpy DLLs
$PY = 'C:\Users\ahoor\anaconda3\python.exe'   # the interpreter all earlier results used (numpy 1.26.4)
$common = @('output/data-analysis/d3s_headroom.py','run','--long','--seeds','1-3','--families','F1,F2','--workers','10')
# 0. rate oracle (fresh Poisson draw of the true rates)
& $PY @common --future rate *> results\mech_0_rateoracle.log
& $PY output/data-analysis/d3s_rateoracle_compare.py *> results\d3s_rateoracle_compare.log
& $PY output/data-analysis/d3s_variants_compare.py *> results\d3s_variants_compare.log
# 1. no-foresight O3S (copies the last 2 min)
& $PY @common --blind *> results\mech_1_blind.log
& $PY output/data-analysis/d3s_variants_compare.py *> results\d3s_variants_compare.log
# 2. ablations (no foresight)
& $PY @common --blind --cand nosim *> results\mech_2a_nosim.log
& $PY @common --blind --cand local_sim *> results\mech_2b_local_sim.log
& $PY output/data-analysis/d3s_variants_compare.py *> results\d3s_variants_compare.log
# 3. speed study (no foresight; backlog clearing time fixed at 120 s in all variants)
& $PY @common --blind --cand keep_bottleneck *> results\mech_3a_keep_bottleneck.log
& $PY @common --blind --horizon 60 *> results\mech_3b_H60.log
& $PY @common --blind --cand keep_bottleneck --horizon 30 *> results\mech_3c_keep_bottleneck_H30.log
& $PY output/data-analysis/d3s_variants_compare.py *> results\d3s_variants_compare.log
"done $(Get-Date)" | Out-File results\pipeline_mechanism.done

