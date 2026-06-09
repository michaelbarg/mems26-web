# CC AUTONOMOUS MEGA PROMPT — Desktop Worklist Fixes · Phases 0–3 + Frontend Candles

**פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`** (טסטים אנטי-טאוטולוגיים · Rule 5 ראיה-לא-טענה · NOT-DONE חובה · single-source · נאמנות-להיקף).

## 🤖 מנדט אוטונומי (אישור Michael, 2026-06-02)
- **בצע את כל Phases 0–3 + תיקון הנרות ב-frontend, ברצף, אוטונומית. אל תשאל שאלות. אל תחכה לאישור. סיים הכל והפק דוח יחיד בסוף.**
- **שער ה-strategic-stop של B5 (אישור Michael לפני live) — מבוטל לריצה הזו בלבד.** כל שאר חוקי החוזה + ה-Invariants הקשיחים למטה **בתוקף מלא**.
- **הקשר סיכון:** הריצה כולה בתוך **SHADOW** — אין נתיב הזמנה אמיתי לברוקר (Pipeline 5 לא נבנה). לכן סיכון האוטונומיה חסום ל-data/display/stability, לא לכסף אמיתי. עדיין: כל שינוי flag-gated + הפיך.

## פרוטוקול שער אוטונומי (במקום "לעצור ולשאול את Michael")
לכל שער: CC מאמת בעצמו. אם עובר → ממשיך. אם **נכשל**:
1. **אל תדחוף קדימה לתוך מצב לא-בטוח.** השאר את הרכיב הבעייתי **מושבת/flag-OFF**, את ה-backend במצב קריאה בטוח, ו-DB ללא כתיבות מושחתות. **data מושחת גרוע מאין** (CLAUDE.md).
2. תעד את הכשל (פלט גולמי) ב-NOT-DONE, **דלג רק על השלבים התלויים בו**, והמשך לשלבים **העצמאיים** (למשל frontend לא תלוי ב-DB rebuild).
3. אל תמציא ערך כדי "לעבור" שער (honest failure > synthetic value).

## 🚫 INVARIANTS קשיחים — לעולם לא להפר, גם אוטונומית
- **אל תחזיר lock ל-`get_db()`** (`session.py:71-81` — בוטל בכוונה, deadlock ב-uvicorn).
- **`integrity_check` = רק עם backend כבוי.** בדיקה חיה/מעל-mount = false-positive (קרה ×3 ב-2/6). זה השער היחיד התקף ל-DB.
- **אל תשחזר מ-`.corrupt.bak`.** backfill רק מ-Sierra export.
- **Sierra = source-of-truth.** אל תסנתז OHLC/CVD/proj_*. אל תמחק שורות נתונים אמיתיות — אם צריך לפסול, סמן `is_synthetic`.
- **B2/B3 ללא שינוי** (הכרעת Michael): אל תיגע ב-`_EXPANSION_MIN_ATR_K` (=1.5, `five_min_system.py:44`) ולא ב-`b4_close_above_b3_high` (543).
- **אל תיגע:** `sc_study/` · bridge market-data routes · `safe_writer.py` · polling intervals · LaunchAgent `KeepAlive`/`CLOUD_URL` · `get_tick_reversal` (קריאה).
- בדוק listeners קיימים על `127.0.0.1:3000`/`:8000` לפני הפעלת שירות — אל תיצור instance כפול.

---

## ⚠️ ממצא קוד (אומת Cowork) — בסיס ל-A1
`get_db()` (`session.py:71-81`) **אינו** לוקח `_write_lock` — גישת `_LockedSession` בוטלה (deadlock). כתיבות ORM (כולל `bars.py:375` tick_reversal `db.commit()`) **לא מסורלות** — רק raw sqlite3 עובר ב-`safe_writer`. זה השורש ל-corruption החוזר. **CLAUDE.md §DB Write-Safety מיושן** (מתאר lock שכבר אינו קיים) — תקן אותו (ראה Phase 0/דוח). השבתת tick_reversal = הסרת הכותב-ORM הכבד; residual root (כותבי-ORM אחרים) = Open, **לא** נפתר ע"י lock.

---

# PHASE 0 — DB + דגלים + S2 (ערב 2/6)

## A1 · השבתת tick_reversal + rebuild נקי
1. אבחון: הצג `session.py:71-81` + `bars.py:354-384`; `integrity_check` (backend כבוי) לפני התיקון → הדבק איזו טבלה מושחתת.
2. `atr.py` (~91): הוסף `TICK_REVERSAL_DISABLED` **call-time** (ראה A3).
3. `bars.py` `post_tick_reversal` (354): early-return אם הדגל ON (שמור קוד, עצור כתיבה). אל תיגע ב-`get_tick_reversal`.
4. grep `tick_reversal` ב-`systems/` → אשר S1/S2/S4 לא תלויים. הדבק.
5. plist: `export TICK_REVERSAL_DISABLED=true`.
6. rebuild: `DROP TABLE` למושחתת + `VACUUM`. לא מ-`.corrupt.bak`.
- **שער:** `integrity_check` backend-כבוי = `ok` (פקודה+פלט). אם ≠ ok → השאר tick_reversal OFF, backend לא עולה לאיסוף, תעד, המשך לשלבים עצמאיים.

## A2 · CCI=32628 → נופל מ-reload נקי + hydration. אמת CCI שפוי אחרי reload (ערך גולמי).

## A3 + D1 · כל הדגלים → call-time
`atr.py:83-93` קורא `os.environ.get` ב-import-time; `trend_relabel.py:12` import קשיח → ערך קפוא. הוסף `def flag(name): return os.environ.get(name,"").lower() in ("1","true","yes")` ב-`atr.py` והמר את **כל** הצרכנים. דגלים cached: `S4_EXTREME_TREND_RELABEL, S2_ATR_RELATIVE, S3_RELATIVE, S1_CVD_OPENING, S1_DAYTYPE_STAGING, S1_IB_WIDTH_ATR, S3_MUTE, FOOTPRINT_DISABLED`. תקן `trend_relabel.py:12,20,23`.
- **שער:** grep → 0 ייבואי-דגל module-level ב-`systems/`. טסט: set env אחרי import → call-time רואה ערך חדש; *"if reverted → RED because cached import value ignores late export"*.

## B1 · bypass lookback_quiet כש-VSA ON (trading-logic, flag-gated)
`five_min_system.py` — `lookback_quiet` ב-**531-533** ו-**622-624**. מיד אחרי כל חישוב:
```python
if flag("S2_VSA_VOLUME"):
    lookback_quiet = True  # VSA gate sufficient — Michael approved 2026-06-02
```
החל על **שני** האתרים (לא חלקי). אל תיגע ב-44/543 (B2/B3).
- **שער:** golden flag-OFF זהה ל-baseline; flag-ON → bypass בשני האתרים; טסט קורא ל-`five_min_system` האמיתי, *"if reverted → RED because ___"*.

## שער Phase 0
commit per-change · regression **≥87/87, 0 failed** (פלט גולמי) · reload backend נקי (port-check קודם).

---

# PHASE 1 — אימות חי (בוקר 3/6, < 16:30 IL)
אוטונומי, פלט גולמי לכל בדיקה: `integrity_check` backend-כבוי=ok · `readiness=READY` · S4 trend=BLUE/RED (לא GRAY) · S2 armed עם VSA · נרות/מחיר זורמים אין frozen-tail. כשל בבדיקה → תעד + המשך.

---

# PHASE 2 — אחרי RTH

## B4 · נפחים מנופחים (אוטונומי, source-of-truth)
ברי 15:15–16:15 (vol 540K–980K, `is_synthetic=0`). הצלב מול `~/SierraChart_Data/v9_export/5min.json`:
- אם **artifact של ingestion** (לא תואם DLL) → תקן אוטונומית **בצורה הפיכה**: סמן `is_synthetic=1` לשורות החשודות **ו/או** סנן מ-`rolling_avg` של VSA מעל סף (`bars.py` ingest + `five_min_system.py`). **אל תמחק** שורות. הוסף regression.
- אם **תואם DLL** (נתון אמיתי) → אל תיגע, תעד "real per Sierra".
- אם **לא חד-משמעי** → אל תיגע, תעד ב-NOT-DONE עם הראיה.

## B5 · `s2_pattern_probe.py` (`systems/build_status/`) — ודא שאין `90% drop`/`[1.5,1.75]` ישנים. תצוגה בלבד.

## D2 · Backfill `v9_bars_30min_woodies`, `v9_bars_cumulative_delta` (חלקי) מ-`history_loader.run_gap_fill("startup")`. דלג על footprint/tick_reversal (מושבתים). לא מ-`.corrupt.bak`.

---

# PHASE 3 — תיקון הנרות ב-Frontend (C1+C2, אוטונומי)
**קובץ אמיתי:** `frontend/v9/src/v9/components/chart/v5b/ChartV5b.tsx`. fetch+render: שורות **495-561** (`bars5min`, `sortedFull` ב-521, render ב-553); CVD כבר מתוכנן 1:1 על אותו timeScale (314, `barsForCvdRef`).

## C1 · session filter (הבעיה: נרות מסשן קודם מעורבים עם היום)
אחרי המיון (`sortedFull`, ~521) סנן לברים מ-**תחילת הסשן הנוכחי** בלבד: overnight = 18:00 ET אתמול, RTH = 09:30 ET היום. החל את אותו סינון על `cData`, `cvdBars`, `barsForCvd`, `barsForOverlay` (~538-549) כדי לשמור יישור 1:1.
- אם המקור הנכון הוא ה-endpoint (`/api/v9/chart/bars5min`, backend בריפו) ולא הפרונט — תקן שם והעדף את ה-SoT, אבל אל תסנתז ברים.

## C2 · CVD alignment
ודא ש-CVD מתבסס על אותו set ברים מסונן (C1) → היישור נשמר. אם יש drift שארי ב-timeScale (ראה הערות TZ 84-100) — ודא ש-CVD `t` ב-epoch תואם ל-bar `t` המסונן.

## אימות Phase 3 (חובה ראייתי)
- `npm run build` ב-`frontend/v9/` עובר (TypeScript נקי) — פלט גולמי.
- ויזואלי: port-check :3000; אם אין instance — הפעל dev server, **צלם screenshot** של הצ'ארט שמראה: נרות רק מהסשן הנוכחי + CVD מיושר מתחת. צרף את ה-screenshot/תיאור. אל תשאיר instance כפול.

---

## דוח חובה סופי (חלק C, ללא צורך באישור)
1. טבלת phases: `Phase · Status · Evidence (command+output) · Deviation/why`.
2. לכל טסט *"if reverted → RED because ___"*.
3. **NOT DONE / DEVIATIONS** (כולל: עדכון CLAUDE.md §DB Write-Safety + residual ORM-write root + כל שער שנכשל).
4. **Open / מה נשאר** + מצב סופי של backend/frontend (רץ? port?).
5. commit אחד או יותר עם labels ברורים; אל תשאיר uncommitted.

**אחרי הדוח — Cowork יאמת בלתי-תלוי (חלק D) ויעדכן STATUS_BOARD/ROADMAP. אתה (CC) אל תעדכן אותם.**
