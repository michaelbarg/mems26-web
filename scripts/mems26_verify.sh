#!/usr/bin/env bash
# mems26_verify.sh — one-shot "is everything consistent + up to date?" check.
# Read-only. Prints PASS / WARN / FAIL per surface + an overall verdict. Starts nothing.
set -uo pipefail
REPO="${MEMS26_REPO:-$HOME/Downloads/mems26_web_git}"
EXPORT_DIR="${MEMS26_SIGNALS_DIR:-$HOME/SierraChart_Data/v9_export}"
PSQL=$(ls /Applications/Postgres.app/Contents/Versions/*/bin/psql 2>/dev/null | head -1)
fail=0; warn=0
ok(){ echo "  ✅ $1"; }
wn(){ echo "  ⚠️  $1"; warn=$((warn+1)); }
er(){ echo "  🔴 $1"; fail=$((fail+1)); }

echo "════ MEMS26 consistency verify · $(date '+%Y-%m-%d %H:%M:%S %Z') ════"

echo "── 1. services ──"
code=$(curl -s -m4 -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null || echo 000)
[ "$code" = "200" ] && ok "backend :8000 → HTTP 200" || er "backend :8000 → HTTP $code"
pgrep -f json_bridge.py >/dev/null && ok "bridge running" || er "bridge NOT running"
pgrep -f v9_export_promoter >/dev/null && ok "export promoter running" || er "export promoter NOT running"

echo "── 2. LaunchAgents loaded ──"
for la in com.mems26.backend com.mems26.bridge com.mems26.export_promoter; do
  launchctl list 2>/dev/null | grep -q "$la" && ok "$la loaded" || wn "$la NOT loaded"
done

echo "── 3. DLL deployed ↔ repo monolith ──"
DEP="$HOME/SierraChart/ACS_Source/MES_AI_DataExport.cpp"
MONO="$REPO/sc_study/MES_AI_DataExport_merged.cpp"
if [ -f "$DEP" ] && [ -f "$MONO" ]; then
  dh=$(shasum -a256 "$DEP"|awk '{print $1}'); mh=$(shasum -a256 "$MONO"|awk '{print $1}')
  if [ "$dh" = "$mh" ]; then ok "deployed DLL == committed monolith"
  else wn "deployed DLL ≠ committed monolith (rebuild+redeploy pending, or merged.cpp stale — run build_monolithic_cpp.sh then diff)"; fi
else wn "cannot compare (missing deployed or monolith file)"; fi
if [ -d "$REPO/.git" ]; then
  dirty=$(git -C "$REPO" status --short sc_study/ 2>/dev/null)
  [ -z "$dirty" ] && ok "sc_study/ clean in git" || wn "sc_study/ has uncommitted changes (deployed may lag repo):
$(echo "$dirty"|sed 's/^/      /')"
fi

echo "── 4. indexes current (no drift) ──"
if [ -f "$REPO/scripts/gen_flag_index.py" ]; then
  if (cd "$REPO" && python3 scripts/gen_flag_index.py --check >/dev/null 2>&1); then ok "FLAG_INDEX current"; else wn "FLAG_INDEX drift → run: python3 scripts/gen_flag_index.py"; fi
fi
[ -f "$REPO/SYSTEM_INDEX.md" ] && ok "SYSTEM_INDEX.md present" || wn "SYSTEM_INDEX.md missing → run scripts/gen_index.py"

echo "── 5. data feed fresh (promoter doing its job) ──"
if [ -f "$EXPORT_DIR/woodies_5min.json" ]; then
  age=$(( $(date +%s) - $(stat -f %m "$EXPORT_DIR/woodies_5min.json") ))
  if [ "$age" -le 120 ]; then ok "woodies_5min.json fresh (${age}s)"
  else wn "woodies_5min.json ${age}s old (OK if market closed / CME break; else check promoter)"; fi
fi

echo "── 6. DB reachable + recent ──"
if [ -n "$PSQL" ]; then
  lag=$("$PSQL" "postgresql://localhost/mems26" -tA -c "SELECT now()-MAX(ts) FROM v9_bars_5min_woodies;" 2>/dev/null)
  [ -n "$lag" ] && ok "v9_bars_5min_woodies last bar lag: $lag" || wn "could not query v9_bars_5min_woodies"
else wn "psql not found (Postgres.app)"; fi

echo "════ verdict: $([ $fail -eq 0 ] && echo "OK" || echo "$fail FAIL") · $warn warn ════"
[ $fail -eq 0 ]
