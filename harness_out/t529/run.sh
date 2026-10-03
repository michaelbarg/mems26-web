#!/bin/bash
# T-529 (03.10, Saturday) — the edge question before the location skip on the responsive (Normal/Neutral) rows.
# Michael 03.10 ~09:1x: "יכול לתקן?" after "למה אין תיקט". Three runs on 66 sessions (t523 list + 02.10), read-only DB,
# same-night reference (= live config), ≤2 parallel, outside RTH:
#   t529ref  live config (tree 3.1.0 · T1 floor 1.5R · ib-return `returning`)
#   t529a    + DECISION_TREE_V3_PATH=config/decision_tree_v3.t529.yaml   (edge asked on the responsive rows; edge = CEILING_FLIP only, as today)
#   t529b    + TREE_EDGE_FAMILIES=CEILING_FLIP,DOUBLE_TOP,DOUBLE_BOTTOM  (the edge also carried by double tops/bottoms — the 02.10 17:55 case)
cd /Users/michael/Downloads/mems26_web_git || exit 1
H=$(TZ=Asia/Jerusalem date +%H%M); D=$(TZ=Asia/Jerusalem date +%u)
if [ "$D" -le 5 ] && [ "$H" -ge 1630 ] && [ "$H" -lt 2300 ]; then echo "REFUSED: $H IL is inside RTH"; exit 2; fi
S=harness_out/t529/sessions.txt
OUT=harness_out/t529/run.out
echo "START $(date) · $(wc -l < "$S") sessions" > "$OUT"
LIVE="DECISION_TREE_V3=1 T1_REALISM_FLOOR_R_V1=1.5 IB_RETURN_HINT_RELEASE_V1=returning"
TREE="DECISION_TREE_V3_PATH=/Users/michael/Downloads/mems26_web_git/config/decision_tree_v3.t529.yaml"
run() { bash harness_out/t466/run_variant.sh "$1" "$2" "$S" > "harness_out/t529/run_$1.out" 2>&1; echo "$1 done $(date) · json=$(ls harness_out/t466/$1_*.json 2>/dev/null | wc -l)" >> "$OUT"; }
run t529ref "$LIVE"
run t529a   "$LIVE $TREE"
run t529b   "$LIVE $TREE TREE_EDGE_FAMILIES=CEILING_FLIP,DOUBLE_TOP,DOUBLE_BOTTOM"
{
  echo "== vs the same-night reference t529ref (= live config)"
  PYTHONIOENCODING=utf-8 python3 harness_out/t515/report.py --ref t529ref t529a t529b
  for t in t529a t529b; do PYTHONIOENCODING=utf-8 python3 harness_out/t515/diff_dir.py "$t" t529ref; done
  for t in t529a t529b; do PYTHONIOENCODING=utf-8 python3 harness_out/t494/cmp_vs_live.py "$t" t529ref | sed -n 1,2p; done
  echo "== drift check: t529ref vs t523ref (same config, common sessions)"
  PYTHONIOENCODING=utf-8 python3 harness_out/t494/cmp_vs_live.py t529ref t523ref | head -2
} >> "$OUT" 2>&1
echo "ALL DONE $(date)" >> "$OUT"
