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
