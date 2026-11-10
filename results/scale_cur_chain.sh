# exact default (MV-3 + PL-1) on current code, same scenarios as the lazy sweeps, one process at a time
cd "D:/DFPS implementation/output/data-analysis"
for c in "80 30 15" "160 30 15" "320 30 15" "640 30 15" "160 60 30" "320 120 60" "640 240 120"; do
  set -- $c
  echo start $c $(date +%H:%M:%S)
  TAG=_cur timeout 1500 python capw1_scale.py one $1 $2 $3
done
echo done
