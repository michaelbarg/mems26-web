#!/bin/bash
# T-564 (fix-agent 08.10 02:1x IL) — the live tree changed at 00:22 IL (3.4.0 → 3.4.1, uncommitted, hot-reloaded 00:26:12,
# "phase C Neutral_Extreme follows the session hint") while the night's runs were in flight: t564ref/t564a ran on 3.4.0,
# t561s2/t564b on 3.4.1. This run = the live config AS IT IS NOW (frozen copy of 3.4.1) on the same 68 sessions, so that
# (a) t564b (3.4.1 + permit) has its true same-night reference and (b) 3.4.1 itself gets the whole-day number vs 3.4.0.
cd /Users/michael/Downloads/mems26_web_git || exit 1
REF='DECISION_TREE_V3=1 T1_REALISM_FLOOR_R_V1=1.5 IB_RETURN_HINT_RELEASE_V1=returning TREE_EDGE_FAMILIES=CEILING_FLIP,DOUBLE_TOP,DOUBLE_BOTTOM'
SESS=harness_out/t564/sessions.txt
LIVE341=/Users/michael/Downloads/mems26_web_git/config/decision_tree_v3.t564live341.yaml
OUT=harness_out/t564/run_ref2.out
echo "START $(date) · $(wc -l < "$SESS") sessions" > "$OUT"
bash harness_out/t466/run_variant.sh t564ref2 "$REF DECISION_TREE_V3_PATH=$LIVE341" "$SESS" > harness_out/t564/run_t564ref2.out 2>&1
echo "t564ref2 done $(date) · json=$(ls harness_out/t466/t564ref2_*.json 2>/dev/null | wc -l)" >> "$OUT"
{
  echo "== 3.4.1 (live now) vs 3.4.0 (t564ref): the whole-day number of the 00:22 tree change"
  PYTHONIOENCODING=utf-8 python3 harness_out/t494/cmp_vs_live.py t564ref2 t564ref --days --trades
  echo "== T-564b permit-alone vs its true same-night reference (3.4.1)"
  PYTHONIOENCODING=utf-8 python3 harness_out/t494/cmp_vs_live.py t564b t564ref2 --days --trades
  echo "== T-561 second slot vs 3.4.1"
  PYTHONIOENCODING=utf-8 python3 harness_out/t494/cmp_vs_live.py t561s2 t564ref2 --days --trades
} >> "$OUT" 2>&1
echo "ALL DONE $(date)" >> "$OUT"
