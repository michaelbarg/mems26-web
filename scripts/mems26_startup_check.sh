#!/usr/bin/env bash
# ============================================================================
# mems26_startup_check.sh — the "turn the machine on → it connects and checks
# everything" self-check. Runs at login (via com.mems26.startup_check
# LaunchAgent) and can be run by hand any time.
#
# Waits for the services to come up, verifies the whole chain
# (backend ↔ Postgres ↔ bridge ↔ Sierra feed ↔ frontend), writes a readable
# report to /tmp/mems26_startup_report.txt, and pops a macOS notification:
#   ✅ all systems go   /   ⚠️ partial   /   ❌ something is down
#
# Read-only: never starts/stops a trade, never edits code/flags/.env.
# ============================================================================
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO" 2>/dev/null || true
[ -f .env ] && { set -a; . ./.env; set +a; }
EXPORT_DIR="${V9_EXPORT_DIR:-$HOME/SierraChart_Data/v9_export}"
REPORT=/tmp/mems26_startup_report.txt
PSQL="$(ls /Applications/Postgres.app/Contents/Versions/*/bin/psql 2>/dev/null | tail -1 || command -v psql || true)"

pass=0; warn=0; fail=0
lines=()
ok()   { lines+=("  ✅ $*"); pass=$((pass+1)); }
wn()   { lines+=("  ⚠️  $*"); warn=$((warn+1)); }
bad()  { lines+=("  ❌ $*"); fail=$((fail+1)); }

# ── within RTH? (08:30–15:00 America/Chicago) — feed is legitimately stale outside it
now_ct_min=$(TZ=America/Chicago date +"%H %M" | awk '{print $1*60+$2}')
dow=$(TZ=America/Chicago date +%u)   # 1=Mon..7=Sun
in_rth=0
if [ "$dow" -le 5 ] && [ "$now_ct_min" -ge 510 ] && [ "$now_ct_min" -lt 900 ]; then in_rth=1; fi

# ── 1. wait for backend (up to 60s) ──
backend_ok=0
for _ in $(seq 1 30); do
  if curl -s -m 3 http://localhost:8000/api/v9/health 2>/dev/null | grep -q '"status":"ok"'; then backend_ok=1; break; fi
  sleep 2
done
[ "$backend_ok" = 1 ] && ok "Backend :8000 — health OK" || bad "Backend :8000 — NOT responding (check /tmp/backend.err.log)"

# ── 2. Postgres reachable ──
if [ -n "$PSQL" ] && "$PSQL" -tA postgresql://localhost/mems26 -c "SELECT 1" >/dev/null 2>&1; then
  ok "Postgres — reachable (mems26)"
else
  bad "Postgres — unreachable (is Postgres.app running?)"
fi

# ── 3. bridge process ──
if pgrep -f "json_bridge.py" >/dev/null 2>&1; then ok "Bridge — running"; else bad "Bridge — not running (LaunchAgent com.mems26.bridge)"; fi

# ── 4. export promoter ──
if pgrep -f "v9_export_promoter.py" >/dev/null 2>&1; then ok "Export promoter — running"; else wn "Export promoter — not running (feed .tmp→.json may freeze)"; fi

# ── 5. Sierra feed freshness ──
newest=0
if [ -d "$EXPORT_DIR" ]; then
  for f in "$EXPORT_DIR"/*.json; do
    [ -e "$f" ] || continue
    m=$(stat -f %m "$f" 2>/dev/null || echo 0); [ "$m" -gt "$newest" ] && newest=$m
  done
fi
if [ "$newest" = 0 ]; then
  bad "Sierra feed — no JSON exports in $EXPORT_DIR (is Sierra running with the study + Input-4?)"
else
  age=$(( $(date +%s) - newest ))
  if [ "$in_rth" = 1 ]; then
    [ "$age" -le 10 ] && ok "Sierra feed — fresh (${age}s, RTH)" || bad "Sierra feed — STALE ${age}s during RTH (check Sierra/promoter)"
  else
    ok "Sierra feed — last update ${age}s ago (outside RTH — stale is normal)"
  fi
fi

# ── 6. frontend :3000 ──
if curl -s -m 3 -o /dev/null -w '%{http_code}' http://localhost:3000 2>/dev/null | grep -qE '200|3..'; then
  ok "Frontend :3000 — serving"
else
  wn "Frontend :3000 — not serving (dashboard only; not required for trading)"
fi

# ── 7. bridge actually pushing (log tail, RTH only) ──
if [ "$in_rth" = 1 ]; then
  if tail -50 /tmp/bridge.err.log 2>/dev/null | grep -q "push"; then ok "Bridge → backend — pushing"; else wn "Bridge → backend — no recent push in log (RTH)"; fi
fi

# ── verdict ──
if   [ "$fail" -gt 0 ]; then icon="❌"; verdict="בעיה — יש רכיב שלא עלה"; title="MEMS26 ❌ בעיה בהפעלה"
elif [ "$warn" -gt 0 ]; then icon="⚠️"; verdict="עלה עם אזהרות"; title="MEMS26 ⚠️ עלה עם אזהרות"
else                        icon="✅"; verdict="כל המערכות תקינות"; title="MEMS26 ✅ הכל מחובר ותקין"; fi

{
  echo "MEMS26 — בדיקת-הפעלה $(date '+%Y-%m-%d %H:%M:%S %Z')"
  echo "מצב: $icon $verdict   (עבר:$pass  אזהרות:$warn  נכשל:$fail)   RTH=$([ "$in_rth" = 1 ] && echo כן || echo לא)"
  echo "---------------------------------------------------------------"
  printf '%s\n' "${lines[@]}"
  echo "---------------------------------------------------------------"
  echo "דשבורד: http://localhost:3000   ·   בקאנד: http://localhost:8000"
  [ "$fail" -gt 0 ] && echo "טיפ: לוגים ב-/tmp/backend.err.log · /tmp/bridge.err.log · ריסטארט: launchctl kickstart -k gui/\$(id -u)/com.mems26.backend"
} | tee "$REPORT"

# macOS notification (best-effort)
osascript -e "display notification \"עבר:$pass אזהרות:$warn נכשל:$fail\" with title \"$title\"" >/dev/null 2>&1 || true

exit 0
