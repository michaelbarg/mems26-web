#!/bin/bash
# ═══════════ MEMS26 — מסך הפעלה ═══════════
# לחיצה-כפולה או: MEMS26_CONTROL.command [status|start|restart|stop|check|update]
# עובד בשתי המכונות (מזהה-עצמית את הריפו). פרוטוקול: docs/runbooks/SECOND_MAC_SETUP.md §12.
set -uo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BRANCH="stabilize/mems26-local-truth-2026-05-16"
PSQL=$(ls /Applications/Postgres.app/Contents/Versions/*/bin/psql 2>/dev/null | head -1)
UID_=$(id -u)
G="\033[1;32m"; R="\033[1;31m"; Y="\033[1;33m"; B="\033[1;36m"; N="\033[0m"
cd "$REPO" || exit 1

open_trades() {
  [ -n "$PSQL" ] && "$PSQL" postgresql://localhost/mems26 -t -A -c \
    "SELECT count(*) FROM v9_trades WHERE mode!='shadow' AND state NOT IN ('CLOSED','CANCELLED');" 2>/dev/null || echo "?"
}

guard_trades() {  # לפני פעולה מסוכנת: עסקה פתוחה → אישור מפורש
  local n; n=$(open_trades)
  if [ "$n" != "0" ] && [ "$n" != "?" ]; then
    echo -e "${R}⚠ יש $n עסקה/ות פתוחות! הברקטים בסיירה ממשיכים להגן, אבל עדיף לחכות ל-flat.${N}"
    read -r -p "להמשיך בכל זאת? (כן/לא) " a; [ "$a" = "כן" ] || return 1
  fi
  return 0
}

svc_state() {  # $1=label
  if launchctl print "gui/$UID_/$1" 2>/dev/null | grep -q "state = running"; then echo -e "${G}● רץ${N}";
  elif launchctl list 2>/dev/null | grep -q "$1"; then echo -e "${Y}● טעון (לא רץ)${N}";
  else echo -e "${R}○ כבוי${N}"; fi
}

do_status() {
  echo -e "${B}── סטטוס שירותים ──${N}"
  for s in com.mems26.backend com.mems26.bridge com.mems26.export_promoter com.mems26.activity_feed; do
    printf "  %-28s %b\n" "$s" "$(svc_state $s)"
  done
  printf "  %-28s " "frontend :3000"
  curl -s -o /dev/null -m 3 http://127.0.0.1:3000 && echo -e "${G}● עונה${N}" || echo -e "${R}○ לא עונה${N}"
  printf "  %-28s " "backend health"
  H=$(curl -s -m 3 http://localhost:8000/api/v9/health 2>/dev/null)
  [ -n "$H" ] && echo -e "${G}● $H${N}" || echo -e "${R}○ אין תשובה${N}"
  echo -e "  עסקאות פתוחות: $(open_trades)"
  echo -e "${B}── גרסה ──${N}"
  echo "  מקומי:  $(git log -1 --format='%h %ci %s' | cut -c1-80)"
  git fetch -q origin "$BRANCH" 2>/dev/null
  BEHIND=$(git rev-list --count HEAD..origin/"$BRANCH" 2>/dev/null || echo "?")
  if [ "$BEHIND" = "0" ]; then echo -e "  ${G}✓ מעודכן לגרסה האחרונה${N}"; else echo -e "  ${Y}⬇ מפגר ב-$BEHIND קומיטים — הרץ 'בדיקת עדכונים'${N}"; fi
  # DLL drift — מקור מול ריפו, וגם בינארי מול מקור (GATE#1: מקור עודכן אך לא קומפל!)
  if [ -f ~/SierraChart/ACS_Source/MES_AI_DataExport.cpp ]; then
    diff -q sc_study/MES_AI_DataExport_merged.cpp ~/SierraChart/ACS_Source/MES_AI_DataExport.cpp >/dev/null 2>&1 \
      && echo -e "  ${G}✓ DLL-מקור פרוס == ריפו${N}" || echo -e "  ${Y}⚠ DLL-מקור פרוס ≠ ריפו (הרץ עדכון/בילד)${N}"
    DLLBIN=$(ls -t ~/SierraChart/Data/MES_AI_DataExport*.dll 2>/dev/null | head -1)
    if [ -n "$DLLBIN" ]; then
      if [ ~/SierraChart/ACS_Source/MES_AI_DataExport.cpp -nt "$DLLBIN" ]; then
        echo -e "  ${R}🔴 הבינארי ישן מהמקור ($(stat -f '%Sm' -t '%d.%m %H:%M' "$DLLBIN")) — סיירה מריצה קוד ישן! נדרש: Remote Build + reload${N}"
      else
        echo -e "  ${G}✓ בינארי-DLL טרי מהמקור ($(stat -f '%Sm' -t '%d.%m %H:%M' "$DLLBIN"))${N}"
      fi
    fi
  fi
}

classify_changes() {  # $1=range → מדפיס הנחיות אחרי-התקנה
  local range="$1" files
  files=$(git diff --name-only "$range" 2>/dev/null)
  echo -e "${B}── מה כלול ומה נדרש אחרי העדכון ──${N}"
  [ -z "$files" ] && { echo "  (אין שינויים)"; return; }
  echo "$files" | grep -q "^sc_study/"            && echo -e "  🔧 ${Y}sc_study השתנה → יופעל build אוטומטי, ואז בסיירה: Remote Build + reload לסטאדי${N}"
  echo "$files" | grep -q "config/RULED_FLAGS"    && echo -e "  🚩 ${Y}דגלים פסוקים השתנו → ייתכן עדכון .env (flag_guard יגיד בדיוק מה)${N}"
  echo "$files" | grep -q "^bridge/"              && echo -e "  🌉 bridge השתנה → ריסטארט bridge אוטומטי"
  echo "$files" | grep -q "^backend/"             && echo -e "  ♻️  backend השתנה → ריסטארט backend אוטומטי"
  echo "$files" | grep -q "^frontend/"            && echo -e "  🖥  frontend השתנה → ריסטארט frontend אוטומטי"
  echo "$files" | grep -q "^scripts/launchagents/" && echo -e "  🚀 LaunchAgents השתנו → השווה מול ~/Library/LaunchAgents (ידני+snapshot)"
  echo "  סה\"כ קבצים: $(echo "$files" | wc -l | tr -d ' ')"
}

do_check() {
  git fetch -q origin "$BRANCH"
  BEHIND=$(git rev-list --count HEAD..origin/"$BRANCH")
  if [ "$BEHIND" = "0" ]; then echo -e "${G}✓ אתה על הגרסה האחרונה ($(git log -1 --format=%h))${N}"; return; fi
  echo -e "${Y}⬇ זמינים $BEHIND קומיטים חדשים:${N}"
  git log --oneline HEAD..origin/"$BRANCH" | head -12 | sed 's/^/    /'
  classify_changes "HEAD..origin/$BRANCH"
  echo -e "  להתקנה: בחר 'עדכן לגרסה האחרונה' (או: $0 update)"
}

do_start() {
  for s in com.mems26.backend com.mems26.bridge com.mems26.export_promoter com.mems26.activity_feed; do
    [ -f ~/Library/LaunchAgents/$s.plist ] && launchctl bootstrap "gui/$UID_" ~/Library/LaunchAgents/$s.plist 2>/dev/null
    launchctl kickstart "gui/$UID_/$s" 2>/dev/null
  done
  curl -s -o /dev/null -m 2 http://127.0.0.1:3000 || screen -dmS mems26_frontend bash -c \
    "cd $REPO/frontend/v9 && ulimit -n 10240; export WATCHPACK_POLLING=true CHOKIDAR_USEPOLLING=true CHOKIDAR_INTERVAL=1000; exec npm run dev >> /tmp/frontend_screen.log 2>&1"
  sleep 12; do_status
}

do_restart() {
  guard_trades || return
  bash scripts/mems26_snapshot.sh "control-restart" >/dev/null 2>&1 && echo "✓ snapshot"
  launchctl kickstart -k "gui/$UID_/com.mems26.backend" 2>/dev/null
  launchctl kickstart -k "gui/$UID_/com.mems26.bridge" 2>/dev/null
  pkill -f "npm run dev" 2>/dev/null; sleep 1
  screen -dmS mems26_frontend bash -c "cd $REPO/frontend/v9 && ulimit -n 10240; export WATCHPACK_POLLING=true CHOKIDAR_USEPOLLING=true CHOKIDAR_INTERVAL=1000; exec npm run dev >> /tmp/frontend_screen.log 2>&1"
  sleep 15; do_status
  python3 scripts/flag_guard.py 2>&1 | tail -1
  python3 scripts/fire_drill.py 2>&1 | tail -2
}

do_stop() {
  guard_trades || return
  for s in com.mems26.backend com.mems26.bridge com.mems26.activity_feed; do
    launchctl bootout "gui/$UID_/$s" 2>/dev/null && echo "✓ $s כובה"
  done
  pkill -f "npm run dev" 2>/dev/null && echo "✓ frontend כובה"
  echo -e "${Y}הערה: export_promoter נשאר (לא מזיק). הפעלה מחדש: מסך זה → הפעלה.${N}"
}

do_update() {
  guard_trades || return
  echo "1/6 snapshot…";  bash scripts/mems26_snapshot.sh "pre-update-$(date +%m%d-%H%M)" >/dev/null 2>&1 && echo "  ✓"
  git fetch -q origin "$BRANCH"
  RANGE="HEAD..origin/$BRANCH"
  BEHIND=$(git rev-list --count $RANGE)
  [ "$BEHIND" = "0" ] && { echo -e "${G}✓ כבר על הגרסה האחרונה${N}"; return; }
  CHANGED=$(git diff --name-only $RANGE)
  echo "2/6 משיכה ($BEHIND קומיטים)…"
  git pull --ff-only origin "$BRANCH" || { echo -e "${R}✗ pull נכשל (לא FF?) — עצור ודווח לסוכן${N}"; return; }
  echo "3/6 סנכרון .env לפסיקות + בדיקת דגלים…"
  # RULED_FLAGS.yaml הגיע עם ה-pull; .env פר-מכונה לא. מסנכרן אוטומטית את
  # הדגלים-הפסוקים בלבד (זו החלת פסיקות-מייקל שכבר כתובות, לא החלטה חדשה),
  # snapshot כבר נלקח בצעד 1. שאר .env לא נוגעים.
  python3 scripts/sync_env_from_ruled.py --apply 2>&1 | sed 's/^/    /'
  if ! python3 scripts/flag_guard.py 2>&1 | tail -1 | grep -q PASS; then
    echo -e "${R}🚩 flag_guard עדיין נכשל אחרי הסנכרון — דגל לא-מוכר או קונפליקט:${N}"
    python3 scripts/flag_guard.py 2>&1 | tail -12
    echo -e "${Y}עצור ודווח לסוכן (snapshot כבר נלקח).${N}"; return
  fi; echo "  ✓ PASS"
  if echo "$CHANGED" | grep -q "^sc_study/"; then
    echo "4/6 בילד DLL (sc_study השתנה)…"
    bash scripts/build_monolithic_cpp.sh --deploy 2>&1 | tail -2
    NEED_REMOTE_BUILD=1
  else NEED_REMOTE_BUILD=0; echo "4/6 (אין שינוי DLL)"; fi
  echo "5/6 ריסטארטים…"
  echo "$CHANGED" | grep -q "^backend/"  && launchctl kickstart -k "gui/$UID_/com.mems26.backend" && sleep 12 && echo "  ✓ backend"
  echo "$CHANGED" | grep -q "^bridge/"   && launchctl kickstart -k "gui/$UID_/com.mems26.bridge" && echo "  ✓ bridge"
  if echo "$CHANGED" | grep -q "^frontend/"; then pkill -f "npm run dev" 2>/dev/null; sleep 1
    screen -dmS mems26_frontend bash -c "cd $REPO/frontend/v9 && export WATCHPACK_POLLING=true; exec npm run dev >> /tmp/frontend_screen.log 2>&1"; echo "  ✓ frontend"; fi
  echo "6/6 אימות…"
  python3 scripts/fire_drill.py 2>&1 | tail -2
  echo -e "${B}══ הנחיות אחרי-התקנה ══${N}"
  [ "$NEED_REMOTE_BUILD" = "1" ] && echo -e "  🔧 ${Y}בסיירה עכשיו: Analysis → Build Custom Studies DLL → Remote Build → reload לסטאדי.${N}\n     אחרי reload: ודא ש-sierra_state.json מתעדכן (ls -la ~/SierraChart_Data/v9_export/)."
  classify_changes "$(git log -1 --format=%h)~$BEHIND..HEAD" 2>/dev/null | tail -n +2
  echo -e "${G}✓ עדכון הושלם: $(git log -1 --format='%h %s' | cut -c1-70)${N}"
}

menu() {
  while true; do
    echo -e "\n${B}══════ MEMS26 — מסך הפעלה ($(hostname -s)) ══════${N}"
    echo "  1) סטטוס מערכת          4) בדיקת עדכונים"
    echo "  2) הפעלה                 5) עדכן לגרסה האחרונה"
    echo "  3) הפעלה מחדש            6) כיבוי"
    echo "  0) יציאה"
    read -r -p "בחירה: " c
    case "$c" in
      1) do_status;; 2) do_start;; 3) do_restart;; 4) do_check;; 5) do_update;; 6) do_stop;;
      0) exit 0;; *) echo "?";;
    esac
  done
}

case "${1:-menu}" in
  status) do_status;; start) do_start;; restart) do_restart;;
  stop) do_stop;; check) do_check;; update) do_update;; menu) menu;;
  *) echo "usage: $0 [status|start|restart|stop|check|update]";;
esac
