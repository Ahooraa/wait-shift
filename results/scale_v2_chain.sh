# clean, one process at a time: lazy + exact speed-ups, then with M = 32; then 3 seeds at 320 and 640 servers for quality
FASTPATH=2 TAG=_v2 python capw1_scale.py sweep 1500 > ../../results/capw1_scale_v2_run.log 2>&1
FASTPATH=2 THIN=32 TAG=_v2 python capw1_scale.py sweep 1500 > ../../results/capw1_scale_v2t32_run.log 2>&1
for s in 2 3; do for n in 320 640; do
  FASTPATH=2 TAG=_v2 python capw1_scale.py one $n 30 15 $s >> ../../results/capw1_scale_v2_run.log 2>&1
  FASTPATH=2 THIN=32 TAG=_v2 python capw1_scale.py one $n 30 15 $s >> ../../results/capw1_scale_v2t32_run.log 2>&1
done; done
