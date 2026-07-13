#!/bin/bash
# mems26_preflight.sh — "האם כל המערכות מחוברות כמו שצריך?" (מייקל 07-13).
# בדיקה מקיפה מקצה-לקצה, READ-ONLY, PASS/GAP לכל תת-מערכת + verdict. עובד בשתי
# המכונות (מזהה-עצמית). תופס בדיוק את החוסרים שנשכנו בהם: חימוש, בינארי-DLL ישן,
# פנטום/divergence, פידים תקועים, מערכות שלא מקבלות. משלים את mems26_verify.sh.
set -uo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$REPO" || exit 1
V9="$HOME/SierraChart_Data/v9_export"
BASE="http://localhost:8000"
TOK=$(grep '^BRIDGE_TOKEN=' .env 2>/dev/null | cut -d= -f2)
G="\033[1;32m"; R="\033[1;31m"; Y="\033[1;33m"; B="\033[1;36m"; N="\033[0m"
gap=0; warn=0
ok(){ echo -e "  ${G}✅ $1${N}"; }
gp(){ echo -e "  ${R}🔴 GAP: $1${N}"; gap=$((gap+1)); }
wn(){ echo -e "  ${Y}⚠️  $1${N}"; warn=$((warn+1)); }
age(){ [ -f "$1" ] && echo $(( $(date +%s) - $(stat -f %m "$1" 2>/dev/null || echo 0) )) || echo 99999; }
jget(){ python3 -c "import json,sys;print(json.load(open('$1')).get('$2',''))" 2>/dev/null; }

echo -e "${B}══════ MEMS26 PREFLIGHT ($(hostname -s) · $(date '+%H:%M')) ══════${N}"

echo -e "${B}── 1. שירותים + API ──${N}"
for s in com.mems26.backend com.mems26.bridge com.mems26.export_promoter; do
  launchctl print "gui/$(id -u)/$s" 2>/dev/null | grep -q "state = running" && ok "$s רץ" || gp "$s לא-רץ"
done
curl -sf -m3 "$BASE/api/v9/health" >/dev/null 2>&1 && ok "backend API עונה" || gp "backend API לא-עונה (:8000)"
curl -sf -m3 "http://localhost:3000" >/dev/null 2>&1 && ok "frontend :3000 עונה" || wn "frontend :3000 לא-עונה"

echo -e "${B}── 2. פידים טריים (כל קבצי-ה-export) ──${N}"
# בשעות-מסחר כולם צריכים <15s; בשוק-סגור חלקם קופאים (מקובל → WARN)
for f in woodies_5min 5min tpo cumulative_delta live_price sierra_state; do
  a=$(age "$V9/$f.json")
  if [ "$a" -lt 15 ]; then ok "$f.json טרי (${a}s)"
  elif [ "$a" -lt 99999 ]; then wn "$f.json ${a}s (OK אם שוק-סגור; אחרת בדוק promoter/סטאדי)"
  else gp "$f.json חסר/לא-נכתב"; fi
done

echo -e "${B}── 3. חיבור-סיירה + חימוש-מסחר (הלקח של היום) ──${N}"
SS="$V9/sierra_state.json"
if [ -f "$SS" ] && [ "$(age "$SS")" -lt 15 ]; then
  ok "עין-סיירה טרייה"
  ARM=$(jget "$SS" order_placement_armed); SIM=$(jget "$SS" is_sim)
  SND=$(jget "$SS" send_orders_to_trade_service); QTY=$(jget "$SS" position_qty)
  [ "$ARM" = "1" ] && ok "חימוש: Enable Order Placement (In:22)=1" \
    || gp "לא-מחומש (armed=$ARM) — חמש Input 'Enable Order Placement'=1, אחרת אין ירי"
  [ "$SIM" = "1" ] && ok "is_sim=1 (יום-סים)" || wn "is_sim=$SIM (לא-סים! ודא שזו כוונה)"
  # בסים send_orders צריך 0; בלייב 1
  if [ "$SIM" = "1" ] && [ "$SND" = "0" ]; then ok "send_orders_to_trade_service=0 (תואם-סים)"
  elif [ "$SIM" = "0" ] && [ "$SND" = "1" ]; then ok "send_orders=1 (תואם-לייב)"
  else wn "send_orders=$SND vs is_sim=$SIM — אי-התאמה (toggle אמצע-סשן?)"; fi
  [ -z "$ARM" ] && wn "אין שדה order_placement_armed → בינארי-DLL ישן! Remote Build"
else gp "sierra_state.json חסר/ישן — סיירה לא מחוברת/DLL לא-מייצא"; fi

echo -e "${B}── 4. DLL: מקור↔בינארי (מלכוד הבינארי-הישן) ──${N}"
DEPLOYED=~/SierraChart/ACS_Source/MES_AI_DataExport.cpp
if [ -f "$DEPLOYED" ]; then
  diff -q sc_study/MES_AI_DataExport_merged.cpp "$DEPLOYED" >/dev/null 2>&1 \
    && ok "DLL-מקור פרוס == ריפו" || gp "DLL-מקור פרוס ≠ ריפו → build_monolithic_cpp.sh --deploy"
  DLLBIN=$(ls -t ~/SierraChart/Data/MES_AI_DataExport*.dll 2>/dev/null | head -1)
  if [ -n "$DLLBIN" ]; then
    [ "$DEPLOYED" -nt "$DLLBIN" ] \
      && gp "בינארי-DLL ($(stat -f '%Sm' -t '%H:%M' "$DLLBIN")) ישן מהמקור → Remote Build + reload!" \
      || ok "בינארי-DLL טרי מהמקור"
  fi
else wn "אין ACS_Source (מכונה בלי סיירה?)"; fi

echo -e "${B}── 5. DB + עסקאות תקועות (פנטום) ──${N}"
python3 - <<'PY' 2>/dev/null && ok "DB נגיש" || gp "DB לא-נגיש (postgresql://localhost/mems26)"
from sqlalchemy import create_engine, text
create_engine("postgresql://localhost/mems26").connect().execute(text("SELECT 1"))
PY
STUCK=$(python3 -c "
from sqlalchemy import create_engine, text
c=create_engine('postgresql://localhost/mems26').connect()
print(c.execute(text(\"SELECT count(*) FROM v9_trades WHERE mode!='shadow' AND state NOT IN ('CLOSED','CANCELLED')\")).scalar())" 2>/dev/null)
if [ "$STUCK" = "0" ]; then ok "אין עסקאות פתוחות תקועות"
elif [ -n "$STUCK" ]; then wn "$STUCK עסקאות פתוחות — ודא שמגובות בפוזיציית-סיירה (אחרת פנטום; PHANTOM_HEAL ירפא)"; fi
BARLAG=$(python3 -c "
from sqlalchemy import create_engine, text
c=create_engine('postgresql://localhost/mems26').connect()
r=c.execute(text('SELECT EXTRACT(EPOCH FROM (now()-max(ts))) FROM v9_bars_5min_woodies')).scalar()
print(int(r) if r else 99999)" 2>/dev/null)
[ -n "$BARLAG" ] && { [ "$BARLAG" -lt 400 ] && ok "בר-אחרון ב-DB לפני ${BARLAG}s" || wn "בר-אחרון ${BARLAG}s (OK אם שוק-סגור)"; }

echo -e "${B}── 6. 6 המערכות מקבלות + מסווגות ──${N}"
DT=$(curl -sf -m4 "$BASE/api/v9/day_type/state" 2>/dev/null | python3 -c "import json,sys;d=json.load(sys.stdin);print(d.get('day_type','?'),d.get('bar_count','?'))" 2>/dev/null)
[ -n "$DT" ] && ok "S1 day_type: $DT" || wn "S1 day_type endpoint לא-ענה (בדוק אם RTH)"
curl -sf -m4 "$BASE/api/v9/status" >/dev/null 2>&1 && ok "status endpoint (S2/S4 slots) חי" || wn "status endpoint לא-ענה"

echo -e "${B}── 7. שערי-החלטה: flags + fire_drill ──${N}"
python3 scripts/flag_guard.py 2>/dev/null | tail -1 | grep -q PASS && ok "flag_guard PASS" || gp "flag_guard NO-GO → python3 scripts/flag_guard.py"
python3 scripts/fire_drill.py 2>/dev/null | tail -1 | grep -q "GO" && ok "fire_drill GO" || wn "fire_drill לא-GO (בדוק — ייתכן מחוץ-לשעות)"

echo -e "${B}── 8. HEAD מסונכרן ל-origin ──${N}"
git fetch -q origin 2>/dev/null
BEHIND=$(git rev-list --count HEAD..origin/stabilize/mems26-local-truth-2026-05-16 2>/dev/null || echo "?")
[ "$BEHIND" = "0" ] && ok "על הגרסה האחרונה ($(git rev-parse --short HEAD))" \
  || wn "מפגר ב-$BEHIND קומיטים → כפתור-עדכון"

echo ""
if [ $gap -eq 0 ]; then echo -e "${G}════ ✅ הכל מחובר — 0 חוסרים · $warn אזהרות ════${N}"
else echo -e "${R}════ 🔴 $gap חוסרים · $warn אזהרות — תקן לפני מסחר ════${N}"; fi
exit $gap
