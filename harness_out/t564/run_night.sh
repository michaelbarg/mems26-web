#!/bin/bash
# T-564 night run (fix-agent 07.10 23:5x IL) — BRIEF §2.2 #1: ONE allow (INITIATIVE_SHORT · Variation · 18-19h) vs the
# SAME-NIGHT reference (= live config), on the t529 list + the sessions added since (2026-10-05, 2026-10-06 = 68).
# Sequential (run_variant.sh already runs 2 sessions in parallel); outputs harness_out/t466/<tag>_*.json.
# Then, window permitting, cowork's queued T-561 second-slot variant vs the same reference (harness_out/t564/run.sh).
cd /Users/michael/Downloads/mems26_web_git || exit 1
REF='DECISION_TREE_V3=1 T1_REALISM_FLOOR_R_V1=1.5 IB_RETURN_HINT_RELEASE_V1=returning TREE_EDGE_FAMILIES=CEILING_FLIP,DOUBLE_TOP,DOUBLE_BOTTOM'
SESS=harness_out/t564/sessions.txt
VAR=/Users/michael/Downloads/mems26_web_git/config/decision_tree_v3.t564_allow.yaml
OUT=harness_out/t564/run_night.out
echo "START $(date) · $(wc -l < "$SESS") sessions" > "$OUT"
bash harness_out/t466/run_variant.sh t564ref "$REF" "$SESS" > harness_out/t564/run_t564ref.out 2>&1
echo "t564ref done $(date) · json=$(ls harness_out/t466/t564ref_*.json 2>/dev/null | wc -l)" >> "$OUT"
bash harness_out/t466/run_variant.sh t564a "$REF DECISION_TREE_V3_PATH=$VAR" "$SESS" > harness_out/t564/run_t564a.out 2>&1
echo "t564a done $(date) · json=$(ls harness_out/t466/t564a_*.json 2>/dev/null | wc -l)" >> "$OUT"
{
  echo "== T-564 allow vs same-night reference t564ref (= live config)"
  PYTHONIOENCODING=utf-8 python3 harness_out/t515/report.py --ref t564ref t564a
  PYTHONIOENCODING=utf-8 python3 harness_out/t494/cmp_vs_live.py t564a t564ref
  echo "== drift check: t564ref vs t529b (same config, common sessions)"
  PYTHONIOENCODING=utf-8 python3 harness_out/t494/cmp_vs_live.py t564ref t529b | head -3
} >> "$OUT" 2>&1
echo "PRIMARY DONE $(date)" >> "$OUT"
if [ "${RUN_T561:-1}" = "1" ]; then
  bash harness_out/t466/run_variant.sh t561s2 "$REF HARNESS_SECOND_SLOT_PATHS=opening_type=OPEN_DRIVE/phase=C/day_type=Trend_Normal/rel_bias=with" "$SESS" > harness_out/t564/run_t561s2.out 2>&1
  echo "t561s2 done $(date) · json=$(ls harness_out/t466/t561s2_*.json 2>/dev/null | wc -l)" >> "$OUT"
  { echo "== T-561 second slot vs t564ref"; PYTHONIOENCODING=utf-8 python3 harness_out/t494/cmp_vs_live.py t561s2 t564ref; } >> "$OUT" 2>&1
fi
echo "ALL DONE $(date)" >> "$OUT"
