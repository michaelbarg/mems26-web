# HANDOFF — צ'אט Cowork הבא (ממשיך את הסשן) · 2026-06-09 ערב

אתה (Cowork הבא) = **orchestrator + verifier בלתי-תלוי**. CC מבצע על ה-Mac; אתה כותב פרומפטים,
מצליב (**Rule 5: פקודה+פלט גולמי**), מאשר לפני fire-path. **עבוד דרך ה-index.**

## קרא קודם
1. `CLAUDE.md` (§Pre-LIVE · §Standing Decisions · §Index · §Frontend Polling Floors) · `SYSTEM_INDEX.md`.
2. **הרשימה המלאה:** `docs/reports/OPEN_ISSUES_REGISTER_2026-06-09.md`.
3. **המגה ש-CC מריץ עכשיו:** `docs/handoff/CC_MEGA_RUN_AND_CLOSE_2026-06-09.md`.
4. הזיכרון של Cowork.

## מצב מאומת (ע"י Cowork, כולל הרצת-pytest אמיתית בסנדבוקס)
**5 תיקונים — קוד תקין + committed:** #1 (`0bc1d20`) · #3 (`2aef154`) · #2/#4 (`23163d9`) ·
#5 inspector (`0efe9e0`) · S2⟂S3 (`638e664`). **טסטים (`e1f2edc`):** אימתתי אמפירית — #1+#5
RED-on-revert **אמיתי**; **#3 עדיין מזויף** (החזרת `_det_buf[:-1]` לא הפילה אותו) → ב-B1 למגה.

## החלטות שאושרו ע"י Michael היום (לא לפתוח מחדש)
- **A2 Double-Top dedup = אופציה 1** (dedup ב-engine `last_fire_pattern_id+ts`, N=lookback). אושר.
- **B3 CCI = מ-Sierra export** (source-of-truth) + fallback ביושר (`source="derived"`). אושר.
- **S3/footprint = post-LIVE** — לא נוגעים/משתמשים עד LIVE. I-11 לא חוסם. scope=S2+S4. (נשמר בזיכרון.)
- **סטופ+targets** מוגדרים per-pattern×day-type (טבלה) — ה-backtester/הקוד **צורך** אותם, לא ממציא.
- **E2 dashboard:** detection בולט בראש · TARGETS/STOP → accordion מקופל (בקשת-צילום Michael).

## מה CC מריץ עכשיו (המגה) — מה להצליב כשיחזיר
שער-קדם-פתיחה G1-G5 (שירותים · 7 דגלים ON · streams S2+S4 · **ירי→`v9_trades`→תצוגת Trades** · סטופים-מהטבלה)
→ סשן (A2·B3·B1·B2·E2/E1) → Completion (בורדים + `MEGA_RUN_2026-06-09.txt`).
**הצלבה (Rule 5):** דרוש פלט גולמי לכל G; אל תאשר "עובד" בלי שורה ב-`v9_trades` **ובתצוגה**;
ודא #3-test מוכח RED-on-revert; ודא אף דגל default-off לא הודלק ו-S3 לא נגעו.

## פתוח/נדחה אחרי המגה
- backtester "driver-דק" (אפיון: `HANDOFF_NEXT_CHAT_2026-06-09_BACKTESTER.md`) + סוכן-יומי — תנאי-קדם A2.
- C4 אינדקס לדוחות (`_INDEX.md` ל-docs/reports+handoff, ~400 קבצים).
- בעיה 7 Initiative calibration (החלטת-Michael) · בעיה 4 ensure_iso_ts · בעיה 2 on_bar_close.
- **C2 git:** הענף 26 לפני origin — push מה-Mac לפני clone/מעבר-מחשב (Cowork חסום מ-push).

## הדרך ל-DEMO (post-today) — רצף-הפאזות (מהרוד-מאפ)
- **פאזה 1 · SHADOW soak (אחרי היום):** המערכת יורה ומתעדת, observe-only, **אין הזמנות**.
  מטרה: להוכיח ירי **נכון+עקבי** לאורך תקופה. כניסה: שער-קדם-פתיחה GO + הבאג של אתמול סגור.
- **פאזה 2 · DEMO = Pipeline 5 (רכיב 5):** נתיב-הזמנה אמיתי לסיארה (DLL DEMO order) · soak ≥7 ימים.
  כניסה: SHADOW soak עבר **+** פתוחים שמשפיעים על אמון סגורים (`pnl_r` ×50 · Double-Top dedup · CCI).
  רכיב 5 = משטח-הסיכון הגבוה (order execution) → **STRATEGIC-STOP + Michael**; פעולות-כסף = Michael בלבד.
  אפשר **להכין/לבנות** את רכיב 5 כבר במהלך SHADOW (במקביל); **המעבר** ל-DEMO מותנה ב-SHADOW-pass.
- **פאזה 3 · LIVE:** pre-flight → micro → production.

## הצעד הראשון בצ'אט הבא
1. בדוק אם CC סיים את המגה → הצלב G1-G5 (Rule 5) → דווח GO/NO-GO ל-Michael.
2. אם trading פתוח — אמת שירי-חי נכתב ומוצג.
3. אחר כך: SHADOW soak · backtester (driver-דק) → סוכן-יומי · הכנת רכיב 5 (Pipeline 5) במקביל · C4 · frontend שנותר.
