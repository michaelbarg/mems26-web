# CC-MACBOOK — סופ"ש 07-25/26: הכל-מוכן-לשני (מנדט-מייקל 07-25)

**דדליין: ראשון 20:00 IL** (מרווח-אימות לפני פתיחת-שני 16:30). פעל לפי
`CC_HANDOFF_CONTRACT.md` (Rule-5 · anti-tautological · NOT-DONE מפורש). **הכל flag-OFF /
לא-מחווט-חי עד אימות-cowork + פסיקה.** עבוד לפי האינדקס — הנתיבים למטה מדויקים.
תוכנית-האם: `docs/plans/WORKPLAN_TO_MONDAY_2026-07-27.md`. עדכן LIVE_CHANNEL אחרי כל Phase.

## סדר: W2 → W3 → W4 → W1 → W1b → W6 → W5

### W2 — exit-tracking: המערכת סגרה עסקה ולא רשמה (מייקל ראה חי, 513 אתמול)
עסקת-לייב 513 (ZLR LONG 18:55) יצאה בסיירה אך **לא נרשמה סגורה** — הרשומה נשארה פתוחה וה-slot
השתחרר רק מאוחר. שורש-משוער: fill_poller לא ממפה exit-fills של ברקטים (ראה גם
`[FillPoller] ORDER_SUBMITTED parent_id=… but no PENDING demo/live trade to map … I-58 fallback`).
**אבחן-לפני-תיקון** (משוך את ה-fills-journal של 513 מול v9_trades), תקן את מיפוי-היציאה +
עדכון state/exit_ts/exit_price/pnl, טסט-רגרסיה עם רצף-fills אמיתי מ-513. revert→RED.

### W3 — NAKED_STOP_SUSPECT: בפוזיציה בלי סטופ-מאושר (CRITICAL אתמול)
`[Reconcile-live] NAKED_STOP_SUSPECT — in position but stop not confirmed
(last_result='MODIFY_STOP_NONE', age עד 837s)` — חלונות-אמת אתמול. אבחן: למה MODIFY_STOP החזיר
NONE (סטופ לא-קיים? id-mismatch? DLL?), ותקן כך שיש אישור-סטופ אחרי כל כניסה/BE-move, או
אסקלציה מיידית (לא רק לוג) אם אין. flag-gated אם משנה-התנהגות. טסט + revert→RED.

### W4 — Variation with-trend (הספק המלא כבר כתוב — בצע אותו)
`docs/handoff/CC_PROMPT_VARIATION_WITH_TREND_CONT_2026-07-24.md` — דגל
`VARIATION_WITH_TREND_CONT_V1` (OFF), fixture 18:15 מאתמול. כמפורט שם.

### W1 — הרחבת-DLL: שדות מסך-Trade-Positions → sierra_state.json
מייקל רוצה את הנתונים שהמסך מציג. הכותב: `sc_study/MES_AI_DataExport.cpp:~1998` (כבר כותב
`position_qty`+`avg_price` מ-`PosData`). הוסף מאותו struct (`s_SCPositionData`):
`open_pnl` (OpenProfitLoss) · `daily_pnl` (DailyProfitLoss) · `high_during_pos`
(PriceHighDuringPosition) · `low_during_pos` (PriceLowDuringPosition) · `trade_account` ·
`symbol` · `daily_total_qty_filled` אם קיים. שמור פורמט/סדר קיים (position_qty נשאר — הקוראים
תלויים בו). בילד: `./scripts/build_monolithic_cpp.sh --deploy` (auto-snapshot) — **Remote Build
= מייקל שני-בוקר**; ציין ב-LOG כשמוכן-לבילד. עד אז השדות פשוט לא-יופיעו (הקוראים חייבים
graceful-None — ודא).

### W1b — עמוד-חשבון-אמת (המערכת-איסוף + העמוד שמייקל ביקש)
Endpoint חדש `GET /api/v9/account/state` (קרא `docs/SOURCE_OF_TRUTH.md` — המקור = sierra_state.json
דרך ה-bridge, לא DB-synthesis): מחזיר את כל שדות-sierra_state כולל החדשים + עסקת-המערכת הפתוחה
(מ-TM) + ‏reconciler-verdict (manual/system/flat). פרונט: עמוד/פאנל "חשבון" — פוזיציה, avg,
Open P/L, Daily P/L, High/Low-During, פקודות-עובדות, is_sim, armed — polling **15000ms**
(רצפות-P30, אסור מהר-יותר). Rule-1: שדה-חסר = "—", לא המצאה. טסטים ל-endpoint.

### W6 — תבנית-חדשה: HIGHER_LOW_SECOND_TEST_V1 (flag-OFF; ההגדרה לאישור-מייקל)
מנדט-מייקל: "שיזהה את הירידה בפעם השנייה ונבצע רכישה בחלק הגבוה יותר". הגדרה מוצעת (S2, לונג;
סימטרי-שורט): (1) דחף-כיווני ≥X נק'; (2) פולבק-ראשון → שפל-L1; (3) התאוששות ≥33%; (4) **ירידה-שנייה
שנעצרת מעל L1 (higher-low L2 > L1 + מרווח)**; (5) בר-דחייה בסגירה מעל L2 → **LONG בסגירת-הדחייה**
("החלק הגבוה" — לא מחכים ל-L1, כי אז זה הולך-לאיבוד); סטופ מאחורי L2 − 16T; T1=1.5R; חלון RTH,
עסקה-אחת-פר-מבנה. flag `HIGHER_LOW_SECOND_TEST_V1` (OFF). fixtures משני ימים אמיתיים מ-woodies
(מצא מבנה כזה ב-07-21/07-24) + revert→RED + OFF=byte-identical. **אל תדליק — ההגדרה עצמה ממתינה
לאישור-מייקל** (מסומן ב-WORKPLAN §מה-על-מייקל).

### W5 — השמשת מערכת-6 (stretch — NOT-DONE מפורש אם לא נכנס)
החוסם האמיתי: op=EXIT שבור (אין יציאה-חלקית עצמאית) → S6 תקוע ב-protective בלבד. הספק הקיים:
`docs/handoff/CC_PROMPT_2026-07-14_EXIT_OP_REBUILD.md` (EXIT-v2: per-contract exit דרך מנגנון חדש,
C++ + backend). התחל: אבחון-עדכני קצר (מה השתנה מאז 07-14) → בנה כמה שנכנס flag-OFF. אם לא מספיק —
NOT-DONE עם מפת-המשך מדויקת. אימות-סים = אחרי שמייקל מדליק Sim בשני.

## חובה בסיום
דוח חלק-C (`docs/reports/CC_WEEKEND_REPORT_2026-07-26.md`): טבלת-phases + פקודה+פלט-גולמי פר-אימות +
revert→RED פר-טסט + NOT-DONE. flag_guard ירוק. רגרסיה ≤ baseline (141). commit+push + שורת-LOG
ב-LIVE_CHANNEL. cowork מאמת ראשון-ערב.

### W7 — cooldown אחרי STOP_HIT (cursor פער-4 🔴, ~$600 ראיית-צל בשבועיים) — flag-OFF
`PATTERN_STOP_COOLDOWN_V1` (default OFF): אחרי STOP_HIT על תבנית×כיוון — חסום ירי-זהה (אותה
תבנית+כיוון) ל-N ברים (default 6 = 30 דק', env `PATTERN_STOP_COOLDOWN_BARS`), אלא אם רמת-הכניסה
החדשה רחוקה ≥X נק' מהכניסה-שנעצרה (מידע-חדש). מיקום: gateway, ליד שאר השערים (נקודת-חנק יחידה).
fixtures מהאשכולות האמיתיים: 07-21 6×ZLR-SHORT 20:56→21:55 (−$206) · 07-20 3×LONG (−$310) ·
07-22 3×SHORT (−$150) → עם-דגל: הראשון עובר, הבאים נחסמים. revert→RED · OFF=byte-identical.
הדלקה = פסיקת-מייקל (שינוי-משטח-סיכון).

### W8 — PROTECT-על-אישור: סטופ+נקודות-מימוש לפוזיציה-ידנית (פסיקת-מייקל 07-25 ליל-שבת)
**הפסיקה:** "אפשר שבאישור של ההתראה תציב סטופ ונקודות מימוש" — אישור-פר-מקרה מהפלאפון על
התראת-ה-NAKED (MANUAL_POSITION_GUARD_V1 שכבר חי) → המערכת מציבה הגנה מלאה על הפוזיציה-הידנית.
אישור-פר-מקרה = רוח פסיקת-12:20 נשמרת (המערכת נוגעת רק בלחיצת-מייקל).

**מה קיים (אומת):** מנגנון-אישור-פלאפון מוכח — `mobile_monitor.py:200` POST /flatten עם
`{"confirm":"FLATTEN"}` + MOBILE_ACCESS_KEY (שכפל את התבנית) · מחיר-סטופ-מבני —
`recommend_orphan_stop()` (reconciler:190) · יעדים — `target_zones.py` / סולם 1.5R.
**מה חסר:** ל-DLL אין op להצבת סטופ/לימיט על פוזיציה קיימת (ב-merged יש רק FLATTEN+MODIFY;
בדוק את המונולית — עבודת-PLACE_STOP-הישנה של 1ב אולי שם, עדיין לא-סים-מאומתת A1.6).

**בנייה:**
1. **DLL:** op `PLACE_STOP` (סטופ-מגן qty-מלא) + op `PLACE_LIMIT` (יעד) באזור-הדיספץ' של
   FLATTEN/MODIFY. acks: `PLACE_STOP_OK/FAIL`, `PLACE_LIMIT_OK/FAIL` (‏reconcile.py:42 כבר
   מכיר PLACE_STOP_OK). **רוכב על ה-Remote-Build של שני יחד עם W1** — אותו בילד.
2. **Backend:** `POST /api/v9/mobile/protect` (תבנית-flatten: אישור-כפול `{"confirm":"PROTECT"}`
   + מפתח): קורא פוזיציה-ידנית מ-sierra_state → סטופ=recommend_orphan_stop (מבני, לא-מסונתז) →
   יעדים=1.5R+3R מ-avg (או target_zones אם זמין-נקי) → כותב PLACE_STOP+2×PLACE_LIMIT → מאשר-acks.
   כשל-חלקי = דיווח-כן (מה הוצב ומה לא). flag `MANUAL_GUARD_PROTECT_V1` (OFF).
3. **פלאפון:** בעמוד-המובייל — כשה-guard מזהה naked-manual: כפתור "🛡️ הצב הגנה" (אישור-כפול)
   שקורא ל-/protect. ההתראה-פוש מפנה לעמוד.
4. **טסטים:** חישוב-סטופ/יעדים לפוזיציה long/short אמיתית (avg 07-24) · אישור-כפול-חסר=דחייה ·
   flag-OFF=endpoint-מחזיר-כבוי · acks-חלקיים=דיווח-כן. **הדלקה: אחרי סים-שני** (מציב פקודות-אמת!)
   — פסיקת-ההפעלה כבר נתונה (07-25), נשאר sim-verify בלבד לפי הנוהל.

### W9 — 🔴 dead-wiring: יומן-הלמידה של S6 ריק (0 שורות) — אין hit-rates, אפס למידה
**ממצא (cowork 07-25, אומת ב-DB+קוד):** `SYSTEM6_EXIT_JOURNAL=1` דלוק מאז 07-13, אבל
`select count(*) from v9_exit_decisions` = **0**. שורש: השרשרת מחווטת **חצי-דרך** —
- ✍️ **כתיבת-שורות** קיימת רק ב-`api/v9/system6_routes.py:145` (`/s6/diagnose`) → נכתב **רק כשמישהו
  פותח את פאנל-S6 בדשבורד**. אין שום לופ-רקע שמעריך `evaluate_exit()` על עסקה חיה פר-בר.
- ✅ **חתימת-התוצאה** כן קיימת (`trading_gateway.py:2390` `fill_outcome` בשחרור-slot) — אבל אין לה
  שורות לחתום עליהן.
⇒ 8 אותות-היציאה/החזקה (price_stall, opposite_patterns, failed_reaction_volume, counter_flow_wins,
cvd_divergence, pattern_intact, trend_continues, hold_confirmation) **מחושבים על-פי-דרישה בלבד
ואף פעם לא נצברים** → אין דאטה להחליט אילו אותות לחבר ל-EXIT-v2. זה חוסם את ההחלטה על S6-המלאה.

**הבנייה (flag-gated, ‏advisory-בלבד — לא נוגע במסחר):**
1. **לופ-רקע:** בכל בר-5-דק' סגור, לכל עסקה **פתוחה** (live/demo) — לקרוא `evaluate_exit()` +
   `pattern_intact/trend_continues/hold_confirmation` ולרשום שורה ל-`v9_exit_decisions` פר-אות
   (‏`build_record` הקיים; `decision='OBSERVED'`, `decided_by='auto_loop'`). נקודת-חיבור טבעית:
   ה-hook של `bar_level_detector`/‏TM שכבר רץ פר-בר על עסקאות-פתוחות (אותו מקום שבו S6-supervisor
   רץ) — **לא** ליצור פולר חדש. דגל `SYSTEM6_JOURNAL_AUTOLOOP_V1` (OFF).
2. **דה-דופ:** שורה אחת פר (trade_id, signal_kind, bar_ts) — לא להציף.
3. **hit-rates:** לוודא ש-`compute_hit_rates` עובד על הדאטה החדשה + לחשוף ב-`/s6/hit_rates`
   (הפונקציה קיימת, ‏system6_routes:160).
4. **טסטים:** לופ רושם פר-בר-פר-אות · דה-דופ · `fill_outcome` חותם על השורות אחרי סגירה ·
   flag-OFF = 0 כתיבות (byte-identical) · advisory-בלבד (אפס קריאות ל-write_exit/MODIFY).
**מטרה:** להתחיל לצבור דאטת-אמת מיום-שני → תוך שבוע יש hit-rates אמיתיים → **אז** מחליטים אילו
אותות מחברים ל-EXIT-v2 (‏W5) במקום לנחש. הדלקה: אחרי אימות — advisory, סיכון-אפס.
