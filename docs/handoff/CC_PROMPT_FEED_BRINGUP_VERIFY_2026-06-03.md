# CC Prompt — Feed Bring-Up + Mac-Side Verification (#10) | 2026-06-03

פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md` (anti-tautological · Rule 5 ראיה-גולמית · סעיף NOT-DONE חובה · נאמנות-היקף B6: phase שחושף צורך → עצור ודווח).

## מטרה אחת
לסגור את **חוסם #10 — feed תקוע** ולהביא את הצינור Sierra → bridge → backend → DB למצב שבו ברי-RTH חדשים נכתבים ל-`v9_bars_5min` ועוברים את גייט ה-RTH של B4. זהו **תנאי מקדים ליום SHADOW**.

## רקע (אבחון Cowork בלתי-תלוי, DB-side, 2026-06-03 ~13:50 UTC)
- `MAX(ts) v9_bars_5min = 2026-06-03T07:15:00Z` (03:15 ET) · `cumulative_delta=06:55Z` · `woodies_signals=08:16:53Z` · `day_type_state=08:08Z`.
- מסקנה: ה-backend היה **חי עד ~08:16** (המשיך לחשב woodies/day_type) אך **לא קיבל ברים חדשים אחרי 07:15** → השבר **upstream ל-ingestion** (Sierra export או bridge push), **לא** ב-backend-ingestion.
- כרגע ה-backend **מושבת** (דוח B4: "Backend restart | Michael — currently stopped").
- B4 (`0ece0fa`) חי: גייט RTH על `/5min` + `/cumulative_delta` → ברים מחוץ 09:30–16:00 ET נדחים (`rth_skipped`). RTH פתוח עכשיו.

## אסור לגעת (risk surface)
- `sc_study/`, bridge market-data routes, או `bars.py` ingestion — **אבחון-בלבד** (CLAUDE.md §7a anti-regression). אל תשנה קוד בפרומפט הזה.
- `CLOUD_URL` חייב להישאר `http://localhost:8000` (CLAUDE.md §Bridge Local-Only). אם תראה push ל-render/remote → **עצור ודווח**.
- אל תחזיר lock ל-`get_db` (deadlock). אל תפעיל מחדש footprint/tick_reversal.

## Phases (אטומיים — כל אחד עם Acceptance בינארי + פקודת-אימות)

### Phase 1 — מצב נוכחי (לפני restart)
- A1. backend חי? `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health` → צפוי `000`/refused (מושבת).
- A2. מי מאזין על הפורטים? `lsof -nP -iTCP:8000 -sTCP:LISTEN; lsof -nP -iTCP:3000 -sTCP:LISTEN` (CLAUDE.md §Service Bring-Up — לוודא אין כפילויות לפני העלאה).
- A3. **רעננות export של Sierra** (השורש החשוד): `ls -la --time-style=full-iso ~/SierraChart_Data/v9_export/*.json | sort -k6` — האם `5min.json` / `cumulative_delta.json` mtime **מתקדם עכשיו** (השווה 2 קריאות בהפרש 60 ש')? אם תקוע ~07:15Z → Sierra עצמו לא מייצא (מנותק מהפיד / סטאדי לא רץ / צ'ארט סגור).
- A4. תוכן ה-export הטרי: `python3 -c "import json,glob,os; p=os.path.expanduser('~/SierraChart_Data/v9_export/5min.json'); d=json.load(open(p)); print('mtime',os.path.getmtime(p)); print('last bar ts', d[-1].get('ts') if isinstance(d,list) else d)"` — מה ה-ts של הבר האחרון בקובץ עצמו (לפני bridge)?
- **Acceptance:** קובע איפה הקצה הקדמי תקוע — אם export-mtime תקוע → Sierra (Mac-UI); אם export טרי אבל DB תקוע → bridge/backend.

### Phase 2 — bridge
- B1. bridge רץ? `ps aux | grep -i "v9_streams\|base_stream\|bridge" | grep -v grep`.
- B2. לוג שגיאות: `tail -40 /tmp/bridge.err.log` — חפש `API push FAILED`. אם היעד **לא** `localhost`/`127.0.0.1` → **עצור ודווח** (config drift, CLAUDE.md). אם FAILED ל-localhost → ה-backend היה למטה (צפוי).
- B3. `CLOUD_URL` בפועל: `grep -i CLOUD_URL ~/Library/LaunchAgents/com.mems26.bridge.plist scripts/start_all.sh` → חייב `http://localhost:8000`.
- **Acceptance:** bridge רץ + מכוון ל-localhost + הסיבה האחרונה ל-FAILED מובנת.

### Phase 3 — restart backend + אימות זרימה ב-RTH (השער האמיתי)
- C1. העלה backend (Michael אישר העלאה לצורך SHADOW). תעד את הפקודה (`scripts/start_all.sh` או launchctl) + יציאתה.
- C2. `curl -s http://localhost:8000/health` → `200` + body.
- C3. **השער:** המתן 2 מחזורי-בר (≥10 דק' RTH) וקרא **פעמיים** בהפרש 5 דק':
  `python3 -c "import sqlite3; c=sqlite3.connect('file:data/mems26_local.db?mode=ro',uri=True); print(c.execute('SELECT MAX(ts),COUNT(*) FROM v9_bars_5min').fetchone())"`
  → `MAX(ts)` חייב **להתקדם** בין שתי הקריאות ולהיות בתוך 09:30–16:00 ET (עבר גייט B4).
- C4. אימות אנטי-טאוטולוגי לגייט (לא להעתיק את הלוגיקה): שלח בר-בדיקה **מחוץ** ל-RTH דרך ה-endpoint האמיתי וודא שהוא נדחה ב-`rth_skipped`, ובר **בתוך** RTH נכתב — *if reverted (הסרת הגייט) → RED because בר 03:15 ET היה נכתב ומזהם rolling_avg*. (אם B4 כבר כיסה — הפנה לטסט הקיים, אל תשכפל.)
- **Acceptance בינארי:** `MAX(ts)` התקדם ב-2 קריאות רצופות **AND** הבר האחרון בתוך RTH. אם לא התקדם → השבר עדיין upstream (חזור ל-Phase 1, אל "תתקן" את ה-backend באשליה — P27.5d).

### Phase 4 — integrity (אחרי שהוכח שהפיד זורם)
- D1. אם נדרש להשבית את ה-backend בשלב כלשהו לבדיקה — `PRAGMA integrity_check` **רק backend-כבוי** (CLAUDE.md: live-soak "ok" פספס corruption 3×). אם ה-backend נשאר חי לאיסוף — **דווח שלא בוצע integrity** (NOT-DONE), אל תטען "ok" על בדיקה חיה.

## דוח (חלק C של החוזה)
טבלת phases (Status · Evidence=command+raw output · Deviation) · שורת "if reverted → RED" לגייט · **NOT DONE / DEVIATIONS** (גם אם "none") · Open.
**שאלת-מפתח לתשובה מפורשת:** השבר היה ב-Sierra-export, ב-bridge, או ב-backend? (ראיה: איזה mtime/ts היה תקוע ואיפה).
