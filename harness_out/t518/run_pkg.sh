#!/bin/bash
cd /Users/michael/Downloads/mems26_web_git || exit 1
H=$(TZ=Asia/Jerusalem date +%H%M); if [ "$H" -ge 1630 ] && [ "$H" -lt 2300 ]; then echo REFUSED; exit 2; fi
S=harness_out/t517/sessions.txt; OUT=harness_out/t518/run_pkg.out
echo "START $(date)" > "$OUT"
bash harness_out/t466/run_variant.sh t518pkg "DECISION_TREE_V3=1 T1_REALISM_FLOOR_R_V1=1.5 IB_RETURN_HINT_RELEASE_V1=returning" "$S" > harness_out/t518/run_t518pkg.out 2>&1
echo "t518pkg done $(date)" >> "$OUT"
{ PYTHONIOENCODING=utf-8 python3 harness_out/t494/cmp_vs_live.py t518pkg t517ref | sed -n 1,3p
  PYTHONIOENCODING=utf-8 python3 harness_out/t515/report.py --ref t517ref t518pkg t518f15 t517ret; } >> "$OUT" 2>&1
echo "PKG DONE $(date)" >> "$OUT"
