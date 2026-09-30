#!/bin/bash
# T-518 (30.09) day-total replays vs the same-night reference t517ref (63 sessions incl. 29.09). ≤2 parallel, read-only DB.
# Refuses to START inside RTH (16:30-23:00 IL); if still running at 16:10 the day run must stop it (T-284: load = trigger).
cd /Users/michael/Downloads/mems26_web_git || exit 1
H=$(TZ=Asia/Jerusalem date +%H%M)
if [ "$H" -ge 1630 ] && [ "$H" -lt 2300 ]; then echo "REFUSED: $H IL is inside RTH"; exit 2; fi
S=harness_out/t517/sessions.txt
OUT=harness_out/t518/run_queue.out
echo "START $(date) · $(wc -l < "$S") sessions · ref=t517ref" > "$OUT"
run() { bash harness_out/t466/run_variant.sh "$1" "$2" "$S" > "harness_out/t518/run_$1.out" 2>&1; echo "$1 done $(date)" >> "$OUT"; }
run t518f10 "DECISION_TREE_V3=1 T1_REALISM_FLOOR_R_V1=1.0"
run t518f15 "DECISION_TREE_V3=1 T1_REALISM_FLOOR_R_V1=1.5"
run t518cft "DECISION_TREE_V3=1 DECISION_TREE_V3_PATH=harness_out/t518/tree_cft.yaml"
run t518dt  "DECISION_TREE_V3=1 DECISION_TREE_V3_PATH=harness_out/t518/tree_dt.yaml"
run t518is  "DECISION_TREE_V3=1 DECISION_TREE_V3_PATH=harness_out/t518/tree_is.yaml"
{
  echo "== day-total vs t517ref"
  for t in t518f10 t518f15 t518cft t518dt t518is; do PYTHONIOENCODING=utf-8 python3 harness_out/t494/cmp_vs_live.py "$t" t517ref | sed -n 1,3p; done
  echo "== detail (t515 report)"
  PYTHONIOENCODING=utf-8 python3 harness_out/t515/report.py --ref t517ref t518f10 t518f15 t518cft t518dt t518is
} >> "$OUT" 2>&1
echo "QUEUE DONE $(date)" >> "$OUT"
