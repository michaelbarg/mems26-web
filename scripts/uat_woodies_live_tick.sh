#!/usr/bin/env bash
# P30.10 — verify building-bar tick: current_bar merges into tail (close/CCI move between polls).
set -euo pipefail
API="${API:-http://127.0.0.1:8000}"
LIMIT="${1:-5}"
SLEEP="${2:-3}"

echo "=== Woodies live tick UAT (sleep ${SLEEP}s) ==="
snap() {
  curl -sf "${API}/api/v9/woodies/chart?limit=${LIMIT}" | python3 -c "
import sys, json, time
d = json.load(sys.stdin)
c = d.get('current_bar') or {}
b = (d.get('bars') or [])[-1] if d.get('bars') else {}
print(json.dumps({
  't': time.time(),
  'age_s': d.get('age_s'),
  'stale': d.get('stale'),
  'study_caption': d.get('study_caption'),
  'cardinality': d.get('cardinality'),
  'latest_ts_unix': d.get('latest_ts_unix'),
  'tail_ts': b.get('ts'),
  'tail_close': b.get('close'),
  'tail_cci': b.get('cci_14'),
  'cur_close': c.get('close'),
  'cur_cci': c.get('cci_14'),
  'same_ts': b.get('ts_unix') == c.get('ts_unix'),
  'tail_eq_cur_close': b.get('close') == c.get('close'),
}, indent=2))
"
}
echo "--- poll 1 ---"
A=$(snap)
echo "$A"
sleep "$SLEEP"
echo "--- poll 2 ---"
B=$(snap)
echo "$B"

TMP1=$(mktemp) TMP2=$(mktemp)
echo "$A" > "$TMP1"
echo "$B" > "$TMP2"
python3 - "$TMP1" "$TMP2" "$SLEEP" <<'PY'
import json, sys
a = json.load(open(sys.argv[1]))
b = json.load(open(sys.argv[2]))
sleep_s = float(sys.argv[3])
ok = True
if a.get("stale") or b.get("stale"):
    print("WARN: stale export — tick test may be inconclusive")
if not a.get("tail_eq_cur_close") or not b.get("tail_eq_cur_close"):
    print("FAIL: tail close != current_bar (merge bug)")
    ok = False
if a.get("latest_ts_unix") != b.get("latest_ts_unix"):
    print("INFO: new bar appeared between polls (ts advanced)")
elif a.get("tail_close") == b.get("tail_close") and a.get("tail_cci") == b.get("tail_cci"):
    print(f"WARN: building bar unchanged in {sleep_s}s — market quiet or export frozen?")
else:
    print("PASS: building bar tick updated (close or cci changed, same ts)")
if a.get("study_caption"):
    print("PASS: study_caption present")
else:
    print("WARN: study_caption missing — restart backend for route change")
raise SystemExit(0 if ok else 1)
PY
rm -f "$TMP1" "$TMP2"
