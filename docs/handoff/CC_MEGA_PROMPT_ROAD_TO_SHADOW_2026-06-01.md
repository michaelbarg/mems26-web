# CC MEGA PROMPT — מסלול ל-SHADOW (הכל · פאזות עם שערים)

**תאריך:** 2026-06-01 · **מקור:** Cowork (Michael) · **מצב:** SHADOW בלבד
**מטרה:** להביא את המערכת למצב שבו אפשר לפתוח SHADOW ולאסוף נתוני כיול **נקיים**, עם כל 6 המערכות מקבלות ומציגות מידע (כולל פרונטאנד).
**משמעת:** diagnose-first · Rule 5 (פלט גולמי לכל קביעה) · flag-OFF=golden · **אפס שינוי order/risk/sizing/polling** · **שער בין פאזות: דווח וקבל ירוק לפני שממשיכים** (one-thread-at-a-time בתוך הרצף).

## רקע מצב (1/6, מאומת)
backend חי + LaunchAgent ✅ · D-094 מומש (flag OFF) ✅ · חיבור/OOH/hydration תוקן (`0bc2d0f`) ✅. **פתוח:** calibration-wiring מנופח (רק S2 חי; S3+S1 מתים) · מחיר-חי תקוע + נרות לא רציפים (בתיקון) · אימות פרונטאנד לכל המערכות. RTH נפתח ~16:30 IL.

> **סדר חובה:** Phase 1+2 (wiring+רציפות) **לפני** איסוף — אחרת נאסוף על לוגיקה ישנה / מחיר תקוע.

---

## Phase 1 · Calibration wiring סבב-2  (ספק מלא: `CC_PROMPT_CALIBRATION_WIRING_ROUND2_2026-06-01.md`)
השלם את מה שסבב-1 פספס (אומת `f3caa89`):
- **S3_RELATIVE:** העבר `median_level_vol` ל-`detect_stacked_imbalance` (`footprint_system.py:369`) + חבר `get_range_ticks`.
- **3 דגלי S1** (IB_WIDTH_ATR / CVD_OPENING / DAYTYPE_STAGING): אבחן אתר-מוות לכל אחד ותקן wiring.
- **Part B:** scaffolding לרישום מטריקות-כיול.
- **עיקרון:** דגל "מחווט" רק אם הוכח **שינוי-התנהגות** flag-ON (לא רק קריאה). flag-OFF=golden. אפס שינוי priors.
**שער 1:** טבלת flag→אתר-מוות→fix→טסט flag-ON (פלט)→golden. דווח לפני Phase 2.

## Phase 2 · רציפות נרות + מחיר זמן-אמת — ✅ **בוצע (אימות בלבד)**
**כבר תוקן** ב-`BAR_CONTINUITY_2026-06-01.md`: מחיר-חי = bid/ask midpoint כשסטייה >2pt (`price_routes.py:35` `_best_price`, 7590.50→7612.12) · WoodiesSystem persist dedup (`woodies_system.py:502` str(ts)+INSERT OR REPLACE) · chart ממזג שתי טבלאות (`bars_5min_history.py`) · flat-stale bars נוקו · פערים אמיתיים (weekend/overnight-down/maintenance) נשארים ללא סינתוז.
**אל תבצע מחדש — רק אמת שמחזיק:** (a) `/api/v9/live_price` מחזיר מחיר חי שזז (לא 7590.50); (b) `/api/v9/chart/bars5min` רציף בתוך חלונות עם נתון, 0 flat-stale; (c) v9_bars_5min_woodies 0 כפילויות. הדבק פלט. אם משהו רגרס — דווח (strategic-stop), אל תתקן מעבר ל-wiring.
⚠️ **הערה ל-Michael:** המחיר החי נלקח מ-**bid/ask midpoint** (לא מ-close של Woodies כפי שנוסח) — התוצאה חיה ונכונה (~7612), אך אם רצית דווקא את ערך ה-Woodies bar, זה tweak קטן.

## Phase 3 · חיבור end-to-end + "המערכות יורות" — NEW · עדיפות (בעיה מאומתת)
**ממצא Cowork (צילום 1/6):** הדאשבורד LIVE והפס העליון תוקן (7611.12 טרי), **אבל פאנל Woodies CCI עדיין תקוע על 7590.50** — הוא קורא ממקור נפרד (study/`sc.Close` קפוא) שתיקון `_best_price` לא נגע בו. כנראה אותו דבר בטבלה/footprint. זה backend-fixed-frontend-not-wired.

### 3a · מחיר חי בכל משטח (diagnose-first)
לכל משטח: מאיפה הוא קורא את המחיר? האם זה המקור המתוקן (`_best_price`/`/live_price`) או הקפוא?
| משטח | מצב ידוע | לתקן |
|------|----------|------|
| פס עליון | ✅ 7611.12 טרי | — |
| **פאנל Woodies CCI** | ❌ תקוע 7590.50 | חבר למקור המתוקן |
| טבלת trades / active | ❓ לאמת | אם תקוע — לתקן |
| Build Status | ❓ לאמת | — |
| chart 5-דק' | רציפות? | לאמת 0 פערים בחלון עם נתון |
לכל "❌/❓": grep מאיפה הקומפוננטה קוראת מחיר → חבר למקור הטרי. הדבק before/after (צילום/JSON: המחיר זז).

### 3b · 6 המערכות מקבלות+מציגות
| מערכת | בק (מקבל?) | פרונט (מאוכלס?) |
|-------|------------|------------------|
| S1 Day Type · S2 Five-Min · S3 Footprint · **S4 Woodies** · S5 TPO · S6 Killzone | endpoint/stream | פאנל לא "—"/"Disconnected" |
- 4 צירי UAT על `/api/v9/cockpit/systems-snapshot` (Quality·Recency·Cardinality·Latency<100ms). FRESH/STALE/DEAD בבק + rendered Y/N בפרונט. תקן כל פאנל ריק שאינו מוסבר ע"י pre-RTH.

### 3c · "המערכות יורות" — אימות נתיב ירי end-to-end
מאחר ש-overnight אף מערכת לא יורה (גייטינג RTH), **אמת את הנתיב בבדיקה מבוקרת:** הזרם setup סינתטי תקף בסביבת-טסט דרך `route_setup` → 5 שערי סיכון → TradeManager → DB `v9_trades` → API `/trades` → UI. הוכח שהשרשרת שלמה (לא חוסם/dead-wire) ושב-RTH יירה. **אסור** לזייף ירי על נתון חי/overnight — בדיקה בסביבת-טסט בלבד.
**שער 3:** מחיר חי זז בכל המשטחים · 6 מערכות בק+פרונט · נתיב ירי מאומת e2e. דווח לפני Phase 4. בסיס: `CC_MEGA_PROMPT_SYSTEM_READINESS_CHECK_2026-05-29.md`.

## Phase 4 · שער SHADOW (P-S0) — מוכנות
- אמת `mode=shadow` (demo/live=null).
- 60 דק' ריצה ירוקה · אפס warnings פתוחים · אפס push errors.
- **DLL frozen-tail חי:** 0 ערכי (cci_14,swi) זהים על ברים שונים ב-RTH (LIVE blocker פתוח).
- הפק דוח מוכנות ל-**sign-off של Michael** (לא לפתוח SHADOW בלי אישורו).
**שער 4:** דוח מוכנות → Michael.

---

## פלט מצופה
דוח לכל פאזה תחת `docs/reports/` + עדכון `STATUS_BOARD.md` אחרי כל שער (finding→fix→evidence, Rule 5). commits נפרדים per-phase.

**שערים כלליים:** עצור ודווח בסוף כל פאזה. flag-OFF=golden. אפס שינוי order/risk/sizing/polling. נרות היסטוריים/overnight = תצוגה בלבד, לא מזינים ירי (אמת D-091/D-092 RTH gates). **לא בסקופ של הרצף הזה:** Auth Table V2 + MAX_CONTRACTS (Michael מעדכן את הטבלה שוב), הפעלת D-094, הרחבת עמוד trades — threads נפרדים.
