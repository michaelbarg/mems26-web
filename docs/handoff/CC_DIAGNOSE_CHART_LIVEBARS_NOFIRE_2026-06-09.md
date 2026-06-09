# CC — אבחון בלבד (לא לתקן): טבלה פגומה · נרות לא-חיים · תבניות לא יורות · 2026-06-09

> **⛔ אבחון בלבד.** אל תיגע בקוד. התוצר = חבילת-ראיות גולמיות (file:line · SQL+פלט · לוג · ts)
> שתימסר ל-Cowork. כל טענה = אסמכתא גולמית, לא הסקה. עבוד דרך ה-index. אל תאבחן מ-inspector
> בלבד — הצלב מול ה-engine/fire-path (לקח חוזר: inspector≠engine). אל תדליק דגל default-off.

תוצר: `docs/reports/DIAGNOSE_CHART_LIVEBARS_NOFIRE_2026-06-09.txt` — סעיף לכל ציר, raw מודבק.

═══════════════════════════════════════════════
## ציר A · למה הטבלה/צ'art פגומה (CVD blow-out + בר מנותק)
═══════════════════════════════════════════════
תצפית-Cowork מצילום Michael: ציר-המחיר מתנפץ (7370 → ‎-89,870); ב-Sierra ה-CVD נע ‎-55..1844 בלבד.
+ בר-בודד מנותק ב-7440 מהסדרה הראשית ב-~7413.
1. **CVD:** מאיפה מגיע הערך שמוצג? עקוב `bars.py:710 post_cumulative_delta` → `v9_bars_cumulative_delta`/
   `v9_bars_5min.cumulative_delta`. הדבק: `SELECT ts,delta,cumulative_delta FROM v9_bars_5min WHERE ts::date=CURRENT_DATE ORDER BY ts DESC LIMIT 20;`
   האם יש ערך ~‎-89,870? האם ה-CVD **מתאפס per-session** או רץ/מצטבר על פני סשנים/כפילויות?
2. **ציר-תצוגה:** ה-CVD מוצג על אותו ציר-Y כמו המחיר? (frontend) — file:line של הרכיב.
3. **בר מנותק:** `bars_5min_history.py` ממזג `v9_bars_5min` ⊕ `v9_bars_5min_woodies`. הדבק את שורות-המיזוג
   סביב 14:30 משתי הטבלאות — האם ה-dedup מפספס (אותו ts/מחיר שונה → בר כפול)?
**אל תתקן — רק הצג שורש + raw.**

═══════════════════════════════════════════════
## ציר B · למה הנרות לא נבנים באופן חי
═══════════════════════════════════════════════
ב-G3 `bars_5min` היה stale 14h ("יתרענן ב-RTH"). אם RTH נפתח והנרות עדיין לא נבנים חי:
1. **Sierra מייצאת?** mtime + הבר האחרון בקובץ `~/SierraChart_Data/v9_export/5min*.json` — טרי? קופא?
2. **הגשר דוחף 5min?** `/tmp/bridge.err.log` / לוג-הגשר — push לערוץ `bars_5min`/`5min`? כמה לאחרונה? (לעומת woodies/tick שדווחו FRESH).
3. **ה-ingest כותב?** `SELECT max(ts),count(*) FROM v9_bars_5min WHERE ts::date=CURRENT_DATE;` — `max(ts)` מתקדם בזמן-אמת? אם לא — איפה נעצר (export/bridge/ingest)?
4. **TZ:** ה-ts שנכתב ב-UTC? (I-18/I-20 — `fresh=true` על lag שגוי). הצלב ts-מנוע מול שעון-קיר.
זה מחלקת I-21 (session-non-start) / frozen-tail. **בודד את החוליה: export → bridge → ingest → DB.** raw לכל חוליה.

═══════════════════════════════════════════════
## ציר C · למה התבניות לא יורות
═══════════════════════════════════════════════
1. **detection בכלל רץ?** לוג ה-engine (`[FiveMin]`/`[Woodies]`) — האם `process_bar` רץ על ברים חדשים?
   כמה ברים בבאפר? (`_bar_buffer` — צריך ≥8 ל-`_det_buf`). אם הבאפר ריק/קטן ← קשור לציר B (אין נרות חיים).
2. **detection מול blocked מול no-setup:** הצלב את ה-engine (לא רק inspector) — לכל תבנית: זוהתה ונחסמה (איזה gate),
   או לא זוהתה כלל? הדבק `build/pattern-status` **+** לוג-ה-engine על אותו חלון (לאמת שהם מסכימים).
3. **mode/gates:** `mode` (OVERNIGHT/FIRST_HOUR/DAY_TYPE)? `day_type` סוּוַּג? גייטים default-off באמת off
   (`S2_CHOPPINESS_GATE`/`LAYER0_CHOP_GATE`/`S2_REQUIRE_COT_AMT`)? auth-table חוסם?
4. **שרשרת-הירי:** אם תבנית כן זוהתה — האם הגיעה ל-setup_emitter→gateway→`v9_trades`? (קשור G4).
   `SELECT count(*) FROM v9_five_min_setups WHERE ts::date=CURRENT_DATE;` + לוג emitted/approved/vetoed.
**הבחן בין שלוש האפשרויות: (א) אין נרות חיים → אין detection · (ב) detection רץ אך נחסם · (ג) אין setup אמיתי.**

═══════════════════════════════════════════════
## ציר D · S1 — למה לא זיהתה opening-type ולמה day_type לא דינמי
═══════════════════════════════════════════════
S1 הייתה אמורה (א) לסווג את **סוג-הפתיחה** היום, ו-(ב) לעדכן את **סוג-היום דינמית** אחרי ~30 דק'.
**אבחן מהנתיב האמיתי, לא מה-endpoint המת:** `backend/main.py` → `_day_type_on_bar` → `app.state.day_type_machine`
+ טבלת `v9_day_type_state`. **אל** תאבחן מ-`/api/v9/day_type/state` (wrapper מת → UNKNOWN מטעה, לקח 2026-06-05).
1. **opening-type:** `SELECT ts,opening_type,day_type,session_min FROM v9_day_type_state ORDER BY ts DESC LIMIT 10;`
   מה `opening_type`? אם UNKNOWN/`session_min=0` ← זה I-1 (instance-split) — הצג את השורש (איזה instance נכתב, האם פוצל).
2. **דינמיות:** האם `day_type` התעדכן לאורך הסשן (יותר מערך אחד / ts מתקדם)? אם תקוע ← האם המכונה מקבלת ברים?
   `S1_DAYTYPE_STAGING`=ON? המכונה (30-min staging) מוזנת ברים חדשים ומחושבת-מחדש, או קפואה?
3. **שרשרת-סיבה:** אם ציר B נכון (אין נרות חיים) → S1 לא יכולה לסווג/להתעדכן דינמית. אמר מפורש אם D נגרם מ-B.

═══════════════════════════════════════════════
## ציר E · S2 — למה חסומה
═══════════════════════════════════════════════
לכל תבנית-S2: מה ה-blocker בפועל (הצלב build/pattern-status **+** engine, לא inspector בלבד)?
1. **mode:** עדיין `OVERNIGHT_MODE`? (אם RTH פתוח וזה עדיין overnight ← קשור B/ציר-הזמן).
2. **gate של day_type:** S2 נחסם אם `day_type`∈{Nontrend} או UNKNOWN. **אם S1 (ציר D) לא סיווגה → S2 נחסם** —
   זו ככל-הנראה שרשרת D→E. אמת זאת: מה ה-day_type שה-S2-gate רואה?
3. **גייטים אחרים:** FHB (first-hour) · choppiness (אמור OFF default) · auth-table · `S2_REQUIRE_COT_AMT` (אמור OFF).
   ודא שהגייטים ה-default-off באמת off ולא חוסמים.
4. הבחן: S2 חסומה כי (א) overnight/אין נרות · (ב) day_type לא סווג (D) · (ג) gate ספציפי אחר.

## פורמט
לכל ציר (A-E): שורש (file:line/SQL/לוג) · raw מודבק · **בלי תיקון**. **מפה את שרשרת-הסיבתיות:**
B (אין נרות חיים) → D (S1 לא מסווגת דינמית) → E (S2 נחסם על day_type) → C (אין ירי). אם זו השרשרת — הוכח אותה ב-raw.
Cowork יצליב לפני שנשלח פרומפט-תיקון.
