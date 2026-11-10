cd "D:/DFPS implementation/output/data-analysis"
for s in 2 3; do for n in 320 640; do
  echo start $n $s $(date +%H:%M:%S)
  TAG=_cur timeout 1500 python capw1_scale.py one $n 30 15 $s
done; done
echo done
