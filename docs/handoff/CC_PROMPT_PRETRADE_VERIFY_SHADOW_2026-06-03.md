# CC Prompt — Pre-Trade Verify (SHADOW readiness, #3) | 2026-06-03

פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md` (Rule 5 ראיה-גולמית · anti-tautological · NOT-DONE חובה · B6 נאמנות-היקף).

## מטרה אחת
לאמת end-to-end שהמערכת **מוכנה לאסוף יום SHADOW נקי** — לרוץ את הפרוטוקול הקבוע `docs/runbooks/PRE_TRADE_PROTOCOL.md` (Phase 0–6) עם **ראיה גולמית לכל סעיף**, פלוס דלתות-היום למטה. זהו **gate** לפני #4 (הרצה+ניטור). **אבחון-בלבד — אל תשנה קוד.** אם סעיף נכשל → תקן/דווח לפי הפרוטוקול, אל תמשיך כאילו עבר.

## הקשר היום (אל תניח — אמת)
- feed חזר ב-~10:30 ET אחרי reload של study (frozen-tail). אומת בלתי-תלוי (Cowork 10:42 ET): `MAX(ts) v9_bars_5min=09:40 ET מתקדם`, ברי-RTH 09:30/35/40 syn=0 שפוי.
- B4 חי (`0ece0fa`): גייט RTH על `/5min`+`/cumulative_delta`; `MAX(vol) is_synthetic=0=71832`; 19 synthetic.
- DB root-fix חי (`9255bfa`): safe_writer-only; `get_db` לא נועל (אל תחזיר). footprint+tick_reversal מושבתים.
- backend עלה (health=ok). mode חייב = shadow.

## אסור לגעת (risk surface)
`sc_study/`, bridge routes, `bars.py` ingestion, trading-logic. אל תפעיל footprint/tick_reversal. אל תשנה את ה-polling floors (CLAUDE.md). שינוי-קוד=מחוץ-להיקף → עצור ודווח.

## Phases — רוץ את הפרוטוקול + הדלתות

### P0–P3 (שירותים · streams · חיבור · סנכרון מול Sierra)
רוץ `PRE_TRADE_PROTOCOL.md` Phase 0–3 כלשונו, ראיה גולמית לכל סעיף. **דגשי-היום:**
- **Frozen-tail watch (קריטי):** הוכח שהברים ממשיכים לזרום — קרא `MAX(ts) v9_bars_5min` **פעמיים בהפרש ≥5 דק'** וודא התקדמות (`python3 -c "import sqlite3;c=sqlite3.connect('file:data/mems26_local.db?mode=ro',uri=True);print(c.execute('SELECT MAX(ts) FROM v9_bars_5min').fetchone())"`). הצלב מול mtime+ts של `~/SierraChart_Data/v9_export/5min.json` (mtime טרי **וגם** מערך-הברים מתקדם, לא רק live_price). אם הברים נתקעים שוב → frozen-tail רגרסיה ב-v9.4.5 → **עצור ודווח** (לא reload-בלולאה).
- בריא-גשר local-only (אין `push FAILED to https://`).

### P4 (6 המערכות מקבלות+מסווגות) — הליבה ל-SHADOW
רוץ Phase 4 + הוסף:
- **readiness verdict:** `curl -s localhost:8000/<build_status endpoint> | python3 -m json.tool` → `readiness == "READY"` (לא DEGRADED/BLOCKED). הדבק את ה-4 checks (bridge/day_type/trend/RTH) הגולמיים. אם DEGRADED/BLOCKED → איזה check נכשל ולמה.
- **S1 bar_count עולה** (raw, פעמיים) · day_type מתקדם ומסווג · IB נועל ~10:30 ET.
- **S2 can-fire בשני הנתיבים** (אימות ה-B1 both-sites, `825972f`): הוכח ש-`_detect_reactive` **וגם** הנתיב השני אינם חסומים מתמטית כעת — או fire אמיתי ב-DB (`v9_five_min_setups`/`v9_trades firing_system=2`), או can-fire diagnostic שמראה שהגייטים פוגשים על ברי-RTH אמיתיים. (אל תשכפל לוגיקה — assert על הפלט/DB. *if reverted bypass → RED because lookback_quiet חוסם שוב*.)
- S3/S4 — לפחות אחת ARMED/יורה; trend_state לא תקוע GRAY (אחרת A1 חוסם הכל).

### P5 (דגלים + בטיחות)
רוץ Phase 5: 5 דגלי-כיול ON **ב-runtime** (לא רק .env — plist), `mode=shadow`, demo/live=null, 5 שערי-סיכון ירוקים, overnight=0 fires, frozen-tail: CCI משתנה על ברים שונים ב-RTH.

### P6 (עסקאות + DB)
רוץ Phase 6: עסקאות נרשמות (fires=rows, 0 drops), synthetic מסומן "TEST", DB אין future-ts/flat-stale/@5900.
- **caveat לבדיקה (מ-Cowork):** בר 03:15 ET יחיד (07:15Z) נכתב-מחדש post-cleanup ל-syn=0/vol=879 → ה-re-push/backfill של reload **כנראה עוקף את גייט ה-RTH** (רק live-tail מגויט). אַמֵּת: כמה ברי **non-RTH** נכתבו היום אחרי ה-reload? (`SELECT COUNT(*) ... WHERE ts NOT in RTH AND <נכתב היום>`). אם >1 → הגייט לא מכסה hydration; דווח (low-risk, מחוץ-RTH, אך לתיעוד).

## Integrity (הקשר, לא עכשיו)
**אל תריץ** `integrity_check` עכשיו (backend חי = false-positive, CLAUDE.md). הוא רץ **בסוף הסשן backend-כבוי** (#5). רק ציין שהוא pending.

## דוח (חלק C)
טבלת Phase · Status(PASS/FAIL/PARTIAL) · Evidence(command+raw output) · Deviation. שורת "if reverted→RED" ל-S2 can-fire. **NOT DONE/DEVIATIONS** (גם "none"). **Verdict בשורה אחת: SHADOW GO / NO-GO + הסיבה.** Open.
