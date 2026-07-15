#!/usr/bin/env bash
# post_restart_verify.sh — liveness gate after every restart/kickstart.
# "No green, no trading." Wire into the morning protocol and after each
# `launchctl kickstart` of the backend/bridge.
#
# 5 checks (Michael CC_NIGHT_PROMPT P4, 2026-07-16):
#   (a) bridge subscribe lines present in the log
#   (b) new bar in DB within 7 min          (v9_bars_5min)
#   (c) v9_day_type_state advancing         (< 15 min)
#   (d) decisions-feed responds             (HTTP 200, non-empty)
#   (e) woodies history fresh               (v9_bars_5min_woodies < 7 min)
#
# Freshness checks (b,c,e) are ENFORCED only during RTH (09:30-16:00 ET); outside
# RTH they are informational (bars are legitimately idle). Structural checks
# (a,d) always enforced. TZ-safe: freshness reads the DB (corrected ts), NOT the
# export files (whose ts is ET-as-UTC).
#
# Exit 0 = GREEN (ok to trade). Exit 1 = RED (do NOT trade) + phone alert in RTH.

set -uo pipefail
cd "$(dirname "$0")/.." || exit 2

API="${MEMS26_API:-http://localhost:8000}"
DB="${DATABASE_URL:-postgresql://localhost/mems26}"
PSQL="$(ls /Applications/Postgres.app/Contents/Versions/*/bin/psql 2>/dev/null | head -1)"
[ -z "$PSQL" ] && PSQL="psql"
BRIDGE_LOG="${BRIDGE_LOG:-/tmp/bridge.err.log}"
BAR_MAX_AGE=420      # 7 min
DAYTYPE_MAX_AGE=900  # 15 min

RED=0
say()  { printf '%s\n' "$*"; }
pass() { say "  ✅ $*"; }
fail() { say "  🔴 $*"; RED=1; }
info() { say "  ▫️  $*"; }

# ── RTH gate (ET) ── FORCE_RTH=1/0 overrides (testing / manual gate).
if [ -n "${FORCE_RTH:-}" ]; then
  IS_RTH="$FORCE_RTH"
else
  IS_RTH=$(python3 - <<'PY'
from datetime import datetime
from zoneinfo import ZoneInfo
n=datetime.now(ZoneInfo("America/New_York")); t=n.hour*60+n.minute
print("1" if (n.weekday()<5 and 570<=t<960) else "0")
PY
)
fi
[ "$IS_RTH" = "1" ] && say "═ post_restart_verify — RTH ACTIVE (freshness enforced) ═" \
                    || say "═ post_restart_verify — outside RTH (freshness = info) ═"

_db_age() { "$PSQL" "$DB" -tA -c "SELECT COALESCE(extract(epoch from (now()-max(ts)))::int, -1) FROM $1;" 2>/dev/null; }

check_fresh() { # name table max_age
  local name="$1" tbl="$2" max="$3" age; age="$(_db_age "$tbl")"
  if [ -z "$age" ] || [ "$age" -lt 0 ] 2>/dev/null; then fail "$name: no rows / DB unreachable"; return; fi
  local mins=$(( age/60 ))
  if [ "$IS_RTH" = "1" ]; then
    [ "$age" -le "$max" ] && pass "$name: ${mins}min old (≤ $((max/60))min)" || fail "$name: ${mins}min old (> $((max/60))min) — STALE"
  else
    info "$name: ${mins}min old (outside RTH — not enforced)"
  fi
}

say "(a) bridge subscribe/stream lines"
# grep -c (not -q) into a var: under `pipefail`, grep -q closes the pipe early →
# tail gets SIGPIPE → pipeline returns non-zero → false negative.
A_HITS=0
[ -f "$BRIDGE_LOG" ] && A_HITS=$(tail -400 "$BRIDGE_LOG" 2>/dev/null | grep -ciE "subscrib|heartbeat|pushes=|stream")
if [ "${A_HITS:-0}" -gt 0 ]; then
  pass "bridge streaming (${A_HITS} heartbeat/push lines in $(basename "$BRIDGE_LOG"))"
else
  fail "no bridge stream/heartbeat lines in $(basename "$BRIDGE_LOG") (bridge down?)"
fi

say "(b) new bar in DB (v9_bars_5min)";       check_fresh "bars_5min"   "v9_bars_5min"          "$BAR_MAX_AGE"
say "(c) day_type advancing";                 check_fresh "day_type"    "v9_day_type_state"     "$DAYTYPE_MAX_AGE"
say "(e) woodies history fresh";              check_fresh "woodies"     "v9_bars_5min_woodies"  "$BAR_MAX_AGE"

say "(d) decisions-feed responds"
DEC_CODE=$(curl -s -o /tmp/_prv_dec.json -w '%{http_code}' -m 8 "$API/api/v9/gateway/decisions?limit=5" 2>/dev/null)
if [ "$DEC_CODE" = "200" ] && [ -s /tmp/_prv_dec.json ]; then
  pass "decisions endpoint HTTP 200 ($(wc -c </tmp/_prv_dec.json | tr -d ' ') bytes)"
else
  fail "decisions endpoint HTTP ${DEC_CODE:-timeout}"
fi

say ""
if [ "$RED" -eq 0 ]; then
  say "🟢 GREEN — liveness verified, OK to trade."
  exit 0
fi
say "🔴 RED — DO NOT TRADE. One or more liveness checks failed."
if [ "$IS_RTH" = "1" ]; then
  python3 - <<'PY' 2>/dev/null || true
try:
    from backend.v9.services.phone_alert import push
    push("post_restart_verify", "🔴 MEMS26: liveness RED",
         "post_restart_verify failed during RTH — do NOT trade until green.", priority=2)
except Exception:
    pass
PY
fi
exit 1
