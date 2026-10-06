#!/bin/bash
# T-538 alternatives (06.10 morning, market closed): cutoff at 19:00 / 21:00 / 22:00 vs the existing same-config reference t543ref (3.3.0 = 20:00).
cd /Users/michael/Downloads/mems26_web_git || exit 1
H=$(TZ=Asia/Jerusalem date +%H%M); D=$(TZ=Asia/Jerusalem date +%u)
if [ "$D" -le 5 ] && [ "$H" -ge 1600 ] && [ "$H" -lt 2305 ]; then echo "REFUSED: $H IL is inside RTH"; exit 2; fi
set -a; source .env; set +a
S=harness_out/t529/sessions.txt; OUT=harness_out/t543/run_cutoffs.out
echo "START $(date) · $(wc -l < "$S") sessions" > "$OUT"
LIVE="DECISION_TREE_V3=1 T1_REALISM_FLOOR_R_V1=1.5 IB_RETURN_HINT_RELEASE_V1=returning TREE_EDGE_FAMILIES=${TREE_EDGE_FAMILIES:-CEILING_FLIP,DOUBLE_TOP,DOUBLE_BOTTOM}"
for t in t543c19 t543c21 t543c22; do
  bash harness_out/t466/run_variant.sh "$t" "$LIVE DECISION_TREE_V3_PATH=/Users/michael/Downloads/mems26_web_git/config/decision_tree_v3.$t.yaml" "$S" > "harness_out/t543/run_$t.out" 2>&1
  echo "$t done $(date) · json=$(ls harness_out/t466/${t}_*.json 2>/dev/null | wc -l)" >> "$OUT"
done
{
  echo "== cutoff alternatives vs t543ref (3.3.0, cutoff 20:00) and vs t529b (3.2.0, no cutoff)"
  for t in t543c19 t543c21 t543c22; do PYTHONIOENCODING=utf-8 python3 harness_out/t494/cmp_vs_live.py "$t" t543ref; done
  for t in t543c19 t543c21 t543c22; do PYTHONIOENCODING=utf-8 python3 harness_out/t494/cmp_vs_live.py "$t" t529b; done
  echo "== (reference) t543ref vs t529b"; PYTHONIOENCODING=utf-8 python3 harness_out/t494/cmp_vs_live.py t543ref t529b
} >> "$OUT" 2>&1
echo "ALL DONE $(date)" >> "$OUT"
