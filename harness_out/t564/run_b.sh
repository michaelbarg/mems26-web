#!/bin/bash
# T-564b (fix-agent 08.10 01:2x IL) — the permit ALONE (against-the-hint INITIATIVE_SHORT · Variation · 18-19h → TAKE,
# default exit; see make_variant_b.py) vs the same-night reference t564ref, on the same 68 sessions. Waits for the
# night script (t561s2) to finish so no more than one run_variant (2 sessions) is active at a time.
cd /Users/michael/Downloads/mems26_web_git || exit 1
until grep -q "ALL DONE" harness_out/t564/run_night.out 2>/dev/null; do sleep 30; done
REF='DECISION_TREE_V3=1 T1_REALISM_FLOOR_R_V1=1.5 IB_RETURN_HINT_RELEASE_V1=returning TREE_EDGE_FAMILIES=CEILING_FLIP,DOUBLE_TOP,DOUBLE_BOTTOM'
SESS=harness_out/t564/sessions.txt
VAR=/Users/michael/Downloads/mems26_web_git/config/decision_tree_v3.t564b_allow.yaml
OUT=harness_out/t564/run_b.out
echo "START $(date) · $(wc -l < "$SESS") sessions" > "$OUT"
bash harness_out/t466/run_variant.sh t564b "$REF DECISION_TREE_V3_PATH=$VAR" "$SESS" > harness_out/t564/run_t564b.out 2>&1
echo "t564b done $(date) · json=$(ls harness_out/t466/t564b_*.json 2>/dev/null | wc -l)" >> "$OUT"
{
  echo "== T-564b permit-alone vs same-night reference t564ref (= live config)"
  PYTHONIOENCODING=utf-8 python3 harness_out/t515/report.py --ref t564ref t564b
  PYTHONIOENCODING=utf-8 python3 harness_out/t494/cmp_vs_live.py t564b t564ref --days --trades
} >> "$OUT" 2>&1
echo "ALL DONE $(date)" >> "$OUT"
