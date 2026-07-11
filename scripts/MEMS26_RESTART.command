#!/bin/bash
# MEMS26 — הפעלה-מחדש בלחיצה (מייקל) — 2026-07-10
# עושה: snapshot → ריסטארט backend → ודא bridge/feeder/frontend חיים → flag_guard + fire_drill → סיכום GO/NO-GO.
# בטיחות: לא נוגע בסיירה, לא בדגלים; רק מרים מחדש את השירותים המקומיים ומאמת.

cd "$(dirname "$0")/.." || exit 1
REPO="$(pwd)"
G="\033[1;32m"; R="\033[1;31m"; Y="\033[1;33m"; N="\033[0m"
echo "══════════ MEMS26 RESTART — $(date '+%H:%M:%S') ══════════"

# 0) עסקה פתוחה? (מזהירים אבל לא עוצרים — סיירה מחזיקה את הברקטים)
PSQL=/Applications/Postgres.app/Contents/Versions/latest/bin/psql
OPEN=$($PSQL postgresql://localhost/mems26 -t -A -c "SELECT count(*) FROM v9_trades WHERE mode!='shadow' AND state NOT IN ('CLOSED','CANCELLED');" 2>/dev/null)
if [ "${OPEN:-0}" != "0" ]; then
  echo -e "${Y}⚠ יש ${OPEN} עסקה/ות פתוחות — הברקטים בסיירה ממשיכים להגן; ההידרציה תאמץ אותן בבוט.${N}"
fi

# 1) snapshot מהיר
bash scripts/mems26_snapshot.sh "click-restart" >/dev/null 2>&1 && echo "✓ snapshot נלקח"

# 2) ריסטארט backend
launchctl kickstart -k "gui/$(id -u)/com.mems26.backend" && echo "✓ backend kickstart"
sleep 15

# 3) bridge חי? (LaunchAgent אמור להחזיק; אם מת — kickstart)
pgrep -f "bridge" >/dev/null || launchctl kickstart "gui/$(id -u)/com.mems26.bridge" 2>/dev/null

# 4) פידר-activity — אחד בדיוק (שניים = הרעלת-offset!)
NFEED=$(pgrep -f "trade_activity_feed" | wc -l | tr -d ' ')
if [ "$NFEED" = "0" ]; then
  screen -dmS mems26_activity_feed bash -c "cd $REPO && python3 scripts/trade_activity_feed.py >> /tmp/activity_feed.log 2>&1"
  echo "✓ פידר-activity הופעל (חשבון-אמת ברירת-מחדל)"
elif [ "$NFEED" != "3" ] && [ "$NFEED" -gt "4" ]; then
  echo -e "${Y}⚠ יותר מפידר אחד ($NFEED תהליכים) — סכנת אירועים-כפולים; סגור ידנית או שאל את הסוכן${N}"
fi

# 5) פרונטאנד מגיב?
curl -s -o /dev/null -w "" http://127.0.0.1:3000 --max-time 3 && echo "✓ frontend :3000 חי" || echo -e "${Y}⚠ frontend לא מגיב — screen -dmS mems26_frontend + npm run dev (ראה start_all.sh)${N}"

# 6) אימות
echo "── אימות ──"
grep "env_loader" /tmp/backend.err.log | tail -1 | grep -o "applied [0-9]* vars" || echo -e "${R}✗ אין שורת-boot — הבקאנד לא עלה!${N}"
python3 scripts/flag_guard.py 2>&1 | tail -1
python3 scripts/fire_drill.py 2>&1 | tail -2

# 7) הידרציה — העסקאות/מצב-היום נטענו מההיסטוריה (BOOT_HYDRATION_V1)
grep -iE "HYDRATION|hydrat" /tmp/backend.err.log | tail -3

echo "══════════ סיום — חלון זה אפשר לסגור ══════════"
read -n 1 -s -r -p "(מקש כלשהו לסגירה)"
