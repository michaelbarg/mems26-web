#!/bin/bash
# ═══════════ MEMS26 — גיבוי מוצפן ל-Google Drive ═══════════
# לחיצה-כפולה. יוצר גיבוי מלא ומוצפן-בסיסמה של המערכת ומניח אותו ב-Google Drive.
# מגבה: קוד+היסטוריית-גיט מלאה · .env (סודות) · מסד-הנתונים (בלי נתוני-שוק כבדים
# שמשוחזרים לבד) · LaunchAgents · snapshots. הסיסמה נשארת אצלך — הסקריפט מבקש
# אותה אינטראקטיבית ואף אחד אחר לא רואה אותה.  שחזור: ראה RESTORE.txt בתוך הגיבוי.
set -uo pipefail
G="\033[1;32m"; R="\033[1;31m"; Y="\033[1;33m"; B="\033[1;36m"; N="\033[0m"

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[ -d "$REPO/.git" ] || REPO="$HOME/mems26/mems26_web_git"
[ -d "$REPO/.git" ] || REPO="$HOME/Downloads/mems26_web_git"
DRIVE="$HOME/Library/CloudStorage/GoogleDrive-michael@passparto.com/My Drive/MEMS26_Backups"
[ -d "$HOME/Library/CloudStorage/GoogleDrive-michael@passparto.com/My Drive" ] || DRIVE="$HOME/Google Drive/My Drive/MEMS26_Backups"
PGDUMP=$(ls /Applications/Postgres.app/Contents/Versions/*/bin/pg_dump 2>/dev/null | head -1)
STAMP=$(date +%Y%m%d_%H%M)
STAGE=$(mktemp -d /tmp/mems26_bk.XXXXXX)
trap 'rm -rf "$STAGE"' EXIT   # לעולם לא להשאיר סודות בפליינטקסט

# טבלאות-שוק כבדות שמשוחזרות לבד מסיירה — שומרים מבנה, מדלגים על הנתונים:
SKIP=(--exclude-table-data=public.v9_bars_footprint
      --exclude-table-data=public.v9_bars_tick_reversal
      --exclude-table-data=public.v9_bars_30min_woodies)

echo -e "${B}══ MEMS26 גיבוי מוצפן ($STAMP) ══${N}"
mkdir -p "$DRIVE"

echo "1/6 קוד + היסטוריית-גיט…"
git -C "$REPO" bundle create "$STAGE/mems26_repo.bundle" --all >/dev/null 2>&1 && echo -e "  ${G}✓${N}"

echo "2/6 סודות + הגדרות…"
cp "$REPO/.env" "$STAGE/env.txt" 2>/dev/null && echo -e "  ${G}✓ .env${N}" || echo -e "  ${Y}⚠ אין .env${N}"
mkdir -p "$STAGE/LaunchAgents"; cp ~/Library/LaunchAgents/com.mems26.* "$STAGE/LaunchAgents/" 2>/dev/null && echo -e "  ${G}✓ LaunchAgents${N}"

echo "3/6 מסד-נתונים (בלי נתוני-שוק כבדים)…"
if [ -n "$PGDUMP" ]; then
  "$PGDUMP" -Fc "${SKIP[@]}" mems26 -f "$STAGE/mems26_db.dump" 2>/dev/null \
    && echo -e "  ${G}✓ $(du -h "$STAGE/mems26_db.dump" | awk '{print $1}')${N}" \
    || echo -e "  ${Y}⚠ pg_dump נכשל${N}"
fi

echo "4/6 snapshots…"
[ -d ~/mems26_snapshots ] && cp -R ~/mems26_snapshots "$STAGE/snapshots" 2>/dev/null && echo -e "  ${G}✓${N}"

cat > "$STAGE/RESTORE.txt" << 'RST'
MEMS26 — שחזור מהגיבוי הזה
==========================
0. פענוח:  openssl enc -d -aes-256-cbc -pbkdf2 -in <קובץ>.enc -out mems26_backup.tar.gz
           (מזין את הסיסמה שבחרת)   ואז:   tar -xzf mems26_backup.tar.gz
1. קוד:    git clone mems26_repo.bundle mems26_web_git   (ריפו מלא עם כל ההיסטוריה)
           או:  git -C <repo קיים> pull mems26_repo.bundle
2. סודות:  cp env.txt <repo>/.env
3. DB:     createdb mems26 ; pg_restore -d mems26 mems26_db.dump
           (טבלאות-השוק הכבדות ריקות — הן ממלאות-עצמן מסיירה בהרצה)
4. שירותים: cp LaunchAgents/com.mems26.* ~/Library/LaunchAgents/ ; launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.mems26.backend.plist
5. אימות:  python3 scripts/flag_guard.py  →  PASS 47/47
RST

echo "5/6 אורז…"
tar -czf "$STAGE/backup.tar.gz" -C "$STAGE" $(cd "$STAGE" && ls | grep -v backup.tar.gz)
echo -e "  ${G}✓ $(du -h "$STAGE/backup.tar.gz" | awk '{print $1}')${N}"

echo -e "6/6 ${B}הצפנה — הזן סיסמה (פעמיים). זכור אותה! בלעדיה אין שחזור.${N}"
OUT="$DRIVE/mems26_backup_$STAMP.tar.gz.enc"
if openssl enc -aes-256-cbc -pbkdf2 -salt -in "$STAGE/backup.tar.gz" -out "$OUT"; then
  echo -e "${G}✓ גיבוי מוצפן נשמר: $OUT${N}"
  echo -e "  גודל: $(du -h "$OUT" | awk '{print $1}')  ·  Google Drive יסנכרן אותו הביתה."
else
  echo -e "${R}✗ ההצפנה בוטלה — לא נשמר גיבוי.${N}"
fi
echo -e "${Y}(קבצי-הביניים נמחקו אוטומטית — הסודות לא נשארים בפליינטקסט.)${N}"
read -n 1 -s -r -p "(מקש כלשהו לסגירה)"
