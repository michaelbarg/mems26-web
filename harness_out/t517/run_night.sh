#!/bin/bash
# T-517 (29.09) night replay — the IB-return hint release (backend/v9/services/ib_return.py + the gateway block, both
# inert unless the env flags below are set). OUTSIDE RTH ONLY (refuses 16:30-23:00 IL), ≤2 sessions in parallel
# (run_variant.sh), read-only DB. Same-night reference first (history tables drift between days), sessions = the 62 of
# T-515 + 2026-09-29 (today's live day).
cd /Users/michael/Downloads/mems26_web_git || exit 1
H=$(TZ=Asia/Jerusalem date +%H%M)
if [ "$H" -ge 1630 ] && [ "$H" -lt 2300 ]; then echo "REFUSED: $H IL is inside RTH (16:30-23:00)"; exit 2; fi
S=harness_out/t517/sessions.txt
{ cat harness_out/t515/sessions.txt; echo 2026-09-29; } | sort -u > "$S"
OUT=harness_out/t517/run_night.out
echo "START $(date) · $(wc -l < "$S") sessions" > "$OUT"
# 0. smoke: one session with the full block on (flow query included) — the log must not say "unavailable"
bash harness_out/t466/run_variant.sh t517smoke "DECISION_TREE_V3=1 IB_RETURN_HINT_RELEASE_V1=both IB_RETURN_RELEASE_FLOW=1" \
  <(echo 2026-09-28) > harness_out/t517/run_t517smoke.out 2>&1
if grep -q "IB-return state unavailable" harness_out/t466/t517smoke_2026-09-28.log; then
  echo "SMOKE FAILED — IB-return block raised; see harness_out/t466/t517smoke_2026-09-28.log" >> "$OUT"; exit 3
fi
python3 - >> "$OUT" 2>&1 <<'EOF'
import json
j = json.load(open("harness_out/t466/t517smoke_2026-09-28.json"))
rel = [g for g in j["gateway_decisions"] if g.get("ibr_released")]
print(f"SMOKE OK · 28.09 · released {len(rel)} · states:",
      sorted({(g.get('tree_v3') or {}).get('ibr', {}).get('state') for g in j['gateway_decisions']} - {None}))
EOF
run() { bash harness_out/t466/run_variant.sh "$1" "$2" "$S" > "harness_out/t517/run_$1.out" 2>&1; echo "$1 done $(date)" >> "$OUT"; }
run t517ref   "DECISION_TREE_V3=1"
run t517ret   "DECISION_TREE_V3=1 IB_RETURN_HINT_RELEASE_V1=returning"
run t517retf  "DECISION_TREE_V3=1 IB_RETURN_HINT_RELEASE_V1=returning IB_RETURN_RELEASE_FLOW=1"
run t517fail  "DECISION_TREE_V3=1 IB_RETURN_HINT_RELEASE_V1=failed"
run t517bothf "DECISION_TREE_V3=1 IB_RETURN_HINT_RELEASE_V1=both IB_RETURN_RELEASE_FLOW=1"
{
  echo "== vs the same-night reference t517ref"
  PYTHONIOENCODING=utf-8 python3 harness_out/t515/report.py --ref t517ref t517ret t517retf t517fail t517bothf
  for t in t517ret t517retf t517fail t517bothf; do PYTHONIOENCODING=utf-8 python3 harness_out/t515/diff_dir.py "$t" t517ref; done
  for t in t517ret t517retf t517fail t517bothf; do PYTHONIOENCODING=utf-8 python3 harness_out/t494/cmp_vs_live.py "$t" t517ref | sed -n 2p; done
  echo "== drift check: t517ref vs this morning's t515ref (common sessions)"
  PYTHONIOENCODING=utf-8 python3 harness_out/t494/cmp_vs_live.py t517ref t515ref | head -1
} >> "$OUT" 2>&1
echo "NIGHT DONE $(date)" >> "$OUT"
