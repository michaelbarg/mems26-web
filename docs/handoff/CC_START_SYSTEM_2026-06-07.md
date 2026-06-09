# CC — הפעלת המערכת המלאה + אימות (2026-06-07 ערב, לקראת RTH מחר)

Michael ביקש להפעיל את המערכת. בצע לפי הסדר, הדבק פלט גולמי לכל שלב (Rule 5),
וכתוב הכל ל-`docs/reports/SYSTEM_START_2026-06-07.txt`.

## 1 — מצב נוכחי (לפני)
```bash
lsof -i :8000 | grep -i listen
lsof -i :3000 | grep -i listen
ps eww $(pgrep -f "uvicorn backend.main" | head -1) 2>/dev/null | tr ' ' '\n' | grep '^DATABASE_URL=' || echo "DATABASE_URL MISSING in running backend"
```

## 2 — אם ה-backend הרץ בלי DATABASE_URL של Postgres → להפיל אותו
(החשד הפתוח: restart קודם עלה בלי DATABASE_URL ונפל ל-SQLite המושחת. `.env` כבר תוקן.)
```bash
pkill -f "uvicorn backend.main:app"; sleep 3
```

## 3 — הפעלה מלאה בנתיב המבורך
```bash
cd /Users/michael/Downloads/mems26_web_git
bash scripts/start_all.sh
sleep 10
bash scripts/check_status.sh 2>/dev/null || true
```

## 4 — אימות (החלק החשוב)
```bash
{
echo "=== health ==="; curl -s localhost:8000/health; echo
echo "=== DATABASE_URL בתהליך הרץ (חייב postgresql://localhost/mems26) ==="
ps eww $(pgrep -f "uvicorn backend.main" | head -1) | tr ' ' '\n' | grep '^DATABASE_URL='
echo "=== 7 הדגלים (חייבים ON) ==="
ps eww $(pgrep -f "uvicorn backend.main" | head -1) | tr ' ' '\n' | grep -E "S2_ATR_RELATIVE|S3_RELATIVE|S1_CVD_OPENING|S1_IB_WIDTH_ATR|S1_DAYTYPE_STAGING|S2_VSA_VOLUME|S3_MUTE" | sort
echo "=== bridge ==="; tail -20 /tmp/bridge.err.log 2>/dev/null | grep -vE "^$" | tail -8
curl -s localhost:8000/api/v9/status | python3 -c "import sys,json; d=json.load(sys.stdin); print('bridge:',d.get('bridge')); print('sierra:',d.get('sierra')); print('session:',d.get('session',{}).get('current'))"
echo "=== sqlite errors? (חייב נקי) ==="; tail -40 /tmp/backend.log | grep -iE "sqlite|malformed" || echo "clean"
echo "=== frontend ==="; curl -s -o /dev/null -w "%{http_code}" http://localhost:3000; echo
} >> docs/reports/SYSTEM_START_2026-06-07.txt 2>&1
cat docs/reports/SYSTEM_START_2026-06-07.txt
```

## קריטריוני-GO (דווח PASS/FAIL לכל אחד)
1. backend: uvicorn יחיד · health ok
2. **DATABASE_URL = postgresql://localhost/mems26 בתהליך הרץ** (סוגר את חשד-ה-SQLite)
3. כל 7 הדגלים ON
4. אין שגיאות sqlite/malformed בלוג
5. bridge רץ ודוחף ל-localhost (אין push FAILED to https)
6. frontend עונה על :3000
הערה: שוק נפתח רק ב-Globex הלילה — sierra עשויה להיות idle עד אז; זה תקין.
אם קריטריון 2 או 4 נכשלים — עצור ודווח, אל תמשיך.
