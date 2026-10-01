#!/bin/bash
# T-523 (01.10 night) — the IB-return release gated on ACCEPTANCE (backend/v9/services/ib_return.py ib_return_rels +
# release_modes accepted_mid/accepted_poc/accepted_any; gateway block). Michael 01.10 20:5x: "למה בעצם המערכת לא לקחה
# עוד עסקאות — המחיר נע מלמטה למעלה": 27 longs died on tree:bias after the failed IB extension; the live mode
# `returning` released only the two bars below IB low. OUTSIDE RTH ONLY, ≤2 parallel, read-only DB.
# Reference = the LIVE config since 30.09 (tree + T1 floor 1.5R + returning), re-run the same night (history drift).
cd /Users/michael/Downloads/mems26_web_git || exit 1
H=$(TZ=Asia/Jerusalem date +%H%M)
if [ "$H" -ge 1630 ] && [ "$H" -lt 2300 ]; then echo "REFUSED: $H IL is inside RTH (16:30-23:00)"; exit 2; fi
S=harness_out/t523/sessions.txt
OUT=harness_out/t523/run_night.out
echo "START $(date) · $(wc -l < "$S") sessions" > "$OUT"
LIVE="DECISION_TREE_V3=1 T1_REALISM_FLOOR_R_V1=1.5"
run() { bash harness_out/t466/run_variant.sh "$1" "$2" "$S" > "harness_out/t523/run_$1.out" 2>&1; echo "$1 done $(date)" >> "$OUT"; }
run t523ref "$LIVE IB_RETURN_HINT_RELEASE_V1=returning"
run t523mid "$LIVE IB_RETURN_HINT_RELEASE_V1=accepted_mid"
run t523poc "$LIVE IB_RETURN_HINT_RELEASE_V1=accepted_poc"
run t523any "$LIVE IB_RETURN_HINT_RELEASE_V1=accepted_any"
{
  echo "== vs the same-night reference t523ref (= live config)"
  PYTHONIOENCODING=utf-8 python3 harness_out/t515/report.py --ref t523ref t523mid t523poc t523any
  for t in t523mid t523poc t523any; do PYTHONIOENCODING=utf-8 python3 harness_out/t515/diff_dir.py "$t" t523ref; done
  for t in t523mid t523poc t523any; do PYTHONIOENCODING=utf-8 python3 harness_out/t494/cmp_vs_live.py "$t" t523ref | sed -n 1,2p; done
  echo "== drift check: t523ref vs yesterday's t518pkg (same config, common sessions)"
  PYTHONIOENCODING=utf-8 python3 harness_out/t494/cmp_vs_live.py t523ref t518pkg | head -2
  echo "== released counts per variant (ibr_released labels)"
  python3 - <<'PY'
import glob, json, collections
for t in ("t523ref","t523mid","t523poc","t523any"):
    c = collections.Counter(); n = 0
    for f in glob.glob(f"harness_out/t466/{t}_*.json"):
        try: j = json.load(open(f))
        except Exception: continue
        n += 1
        for g in j.get("gateway_decisions", []):
            if g.get("ibr_released"): c[g["ibr_released"]] += 1
    print(t, "sessions", n, "released", dict(c))
PY
} >> "$OUT" 2>&1
echo "NIGHT DONE $(date)" >> "$OUT"
