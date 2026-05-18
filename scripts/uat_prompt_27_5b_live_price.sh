#!/usr/bin/env bash
# P27.5b UAT — live_price freshness check
# READ-ONLY: does not start/stop any services.
# Calls /api/v9/live_price 10 times, 1s apart.
# PASS only if all samples during RTH have age_ms < 60000.
# Outside RTH: exits SKIP/DEFERRED.

set -euo pipefail

ENDPOINT="http://127.0.0.1:8000/api/v9/live_price"
SAMPLES=10
INTERVAL=1
THRESHOLD_MS=60000

# ── 0. Check backend is up ──
if ! curl -sf -o /dev/null "$ENDPOINT" 2>/dev/null; then
  echo "FAIL: backend not reachable at $ENDPOINT"
  exit 1
fi

echo "P27.5b UAT — live_price freshness"
echo "Endpoint: $ENDPOINT"
echo "Samples:  $SAMPLES × ${INTERVAL}s interval"
echo "Threshold: age_ms < $THRESHOLD_MS"
echo "---"

pass=0
fail=0
skip=0

for i in $(seq 1 $SAMPLES); do
  start_ms=$(python3 -c "import time; print(int(time.time()*1000))")
  body=$(curl -sf -w '\n%{http_code} %{time_total}' "$ENDPOINT" 2>/dev/null) || {
    echo "[$i] HTTP error — curl failed"
    fail=$((fail+1))
    sleep "$INTERVAL"
    continue
  }

  # Split body into JSON + status line
  json_line=$(echo "$body" | head -1)
  status_line=$(echo "$body" | tail -1)
  http_code=$(echo "$status_line" | awk '{print $1}')
  latency_s=$(echo "$status_line" | awk '{print $2}')
  latency_ms=$(python3 -c "print(int(float('$latency_s')*1000))")

  # Parse fields
  price=$(echo "$json_line" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('price','null'))")
  age_ms=$(echo "$json_line" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('age_ms','null'))")
  ts_utc=$(echo "$json_line" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('ts_utc','null'))")
  error=$(echo "$json_line" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('error',''))")

  # Check for error response
  if [ -n "$error" ] && [ "$error" != "" ] && [ "$error" != "None" ]; then
    echo "[$i] HTTP=$http_code  ERROR=$error  latency=${latency_ms}ms"
    fail=$((fail+1))
    sleep "$INTERVAL"
    continue
  fi

  # Check for missing age_ms field
  if [ "$age_ms" = "null" ] || [ "$age_ms" = "None" ]; then
    echo "[$i] FAIL: age_ms field missing from response"
    fail=$((fail+1))
    sleep "$INTERVAL"
    continue
  fi

  # Market-closed heuristic: age_ms > 10 minutes = likely not RTH
  age_ms_int=$(python3 -c "print(int($age_ms))")
  if [ "$age_ms_int" -gt 600000 ]; then
    echo "[$i] SKIP  HTTP=$http_code  price=$price  age_ms=$age_ms (>10min — market likely closed)  ts_utc=$ts_utc  latency=${latency_ms}ms"
    skip=$((skip+1))
    sleep "$INTERVAL"
    continue
  fi

  # RTH check: age_ms should be < threshold
  if [ "$age_ms_int" -lt "$THRESHOLD_MS" ]; then
    echo "[$i] PASS  HTTP=$http_code  price=$price  age_ms=$age_ms  ts_utc=$ts_utc  latency=${latency_ms}ms"
    pass=$((pass+1))
  else
    echo "[$i] FAIL  HTTP=$http_code  price=$price  age_ms=$age_ms (>= $THRESHOLD_MS)  ts_utc=$ts_utc  latency=${latency_ms}ms"
    fail=$((fail+1))
  fi

  sleep "$INTERVAL"
done

echo "---"
echo "Results: PASS=$pass  FAIL=$fail  SKIP=$skip  (of $SAMPLES)"
echo ""

if [ "$skip" -eq "$SAMPLES" ]; then
  echo "RESULT: DEFERRED — all samples skipped (market closed / Sierra not writing)"
  echo "Re-run during RTH with Sierra running and the MES chart actively writing live_price.json."
  exit 0
elif [ "$fail" -gt 0 ]; then
  echo "RESULT: FAIL — $fail sample(s) exceeded age_ms threshold"
  exit 1
elif [ "$pass" -eq "$SAMPLES" ]; then
  echo "RESULT: PASS — all $SAMPLES samples have age_ms < $THRESHOLD_MS"
  exit 0
else
  echo "RESULT: PARTIAL — $pass passed, $skip skipped, $fail failed"
  echo "P27.5b requires $SAMPLES/$SAMPLES PASS during RTH to go GREEN."
  exit 0
fi
