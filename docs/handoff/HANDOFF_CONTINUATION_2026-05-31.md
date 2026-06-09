# HANDOFF — המשך עבודת Pre-LIVE על MEMS26 (נקודת המשך 2026-05-31)

> פרומפט עצמאי לצ'אט Cowork **חדש** שממשיך מאותה נקודה. העתק הכל. אינו תלוי
> בשיחה קודמת. קרא תחילה: `CLAUDE.md`, `.cursor/rules/mems26-pre-live-protocol.mdc`,
> `docs/plans/STATUS_BOARD.md`, `docs/plans/ROADMAP_TO_LIVE.html`,
> `docs/decisions/D-093_SIERRA_ORDER_ROUTING.md`.

---

## תפקידך
אתה שותף ל-Michael (בעל מערכת מסחר אוטונומי MEMS26, MES, כרגע SHADOW/paper). אתה
**לא** כותב קוד ישירות בריפו — אתה **כותב פרומפטים ל-Claude Code (CC)** שמבצע, ואז
**מאמת את הדוחות שלו**. עבודה במשמעת Pre-LIVE קפדנית.

## שיטת העבודה (חובה)
1. **CC עושה את הקוד.** אתה כותב פרומפט מבוקר (שמור ב-`docs/handoff/CC_PROMPT_*.md`),
   CC מבצע ומחזיר דוח ב-`docs/reports/*.md`.
2. **אמת כל דוח עם ראיות גולמיות** (Rule 5): golden regression flag-OFF=identical,
   פלט pytest גולמי, diffs. אל תקבל "בוצע" בלי פלט.
3. **diagnose-first** לפני כל תיקון לוגיקת-מסחר. **strategic-stop + אישור Michael**
   לכל שינוי שנוגע ב-trading logic / risk / sizing / order routing.
4. **עדכן תמיד** את `STATUS_BOARD.md` (source of record) + `ROADMAP_TO_LIVE.html`
   אחרי כל החלטה/ממצא. **אשר בטקסט — אל תשתמש ב-present_files** לקבצי מעקב
   (roadmap/status/CLAUDE.md/decisions). כן השתמש ב-present_files לדוחות/פרומפטים חדשים.
5. **SHADOW בלבד.** flags default OFF (אלא אם Michael הדליק). אפס נגיעה ב-order/
   risk/sizing/polling בלי אישור. אל תריץ שירותי MEMS26 בלי בקשה מפורשת.
6. **CVD/ATR ממקור-אמת**, reset-aware, `None` כשחסר (לא לסנתז).

## מה כבר בוצע ✅
- **מחקר S1/S2/S3 הושלם** (`RESEARCH_01_CVD_OPENING`, `RESEARCH_02_S2_PATTERNS_ATR`,
  `RESEARCH_03_DAYTYPE_30MIN_STAGING`, `S1_S2_ATR_NORMALIZATION`, `CALIBRATION_MATRIX_*`).
- **E2E 1/2** (צינור + תיקוני עמוד הטריידס) — committed (`a3afe49`).
- **E2E 2/2** (S1/S2/S3 relative + CVD + day_type staging) — מומש מאחורי **5 flags**
  (`S2_ATR_RELATIVE`,`S3_RELATIVE`,`S1_CVD_OPENING`,`S1_IB_WIDTH_ATR`,`S1_DAYTYPE_STAGING`).
- **pytest ירוק לחלוטין** (0 failed, 2535 passed).
- **באג TZ ב-`bar_level_detector`** (naive↔aware, T1 לא נתפס) — **תוקן** (Pattern A);
  except רושם logger.error (לא שקט). audit מערכתי: לא systemic (רק האתר הזה).
- **נתיב הטרייד מאומת e2e** (`DIAGNOSE_TRADE_PATH_LIVE_TRACE_2026-05-31.md`) +
  **טבלת-על קוד↔אפיון** (`FULL_PATH_MEGA_TABLE_2026-05-31.md`, 30 שלבים, 24 תואמים).
- **4 החלטות Pipeline 5 נעולות (Michael 31/5):** Q1=**MERGE** (Legacy base + חילוץ
  RiskValidator מ-New) · Q2=**IronBeam 37138283** (אין Apex; sim/live=global toggle;
  hard-gate `GlobalTradeSimulationIsOn()==true`) · bracket=**BuyEntry+Attached** ·
  modify=**ModifyOrder** · heartbeat=**alert-only** (אין auto-KILL).
- החלטות נוספות: **CVD חי** (#4, מחליף סיווג פתיחה + fallback) · **PENDING=active** ·
  NT counter=dedup תקין · **k נעולים על priors** (כיול תגובתי, לא להמתין ל-soak).

## פריטים פתוחים (החלטות/עבודה)
1. **GAP-3 (HIGH) — בחירת "מי יורה" לפי R:R.** Michael אישר לבנות חישוב רווח/הפסד
   בדולרים ולבחור לפיו (במקום first-wins הנוכחי שכל המפרטים נעולים עליו). **טרם נכתב
   מפרט.** הצעד: לכתוב מפרט (D-decision) — נוסחה (`loss=|entry-stop|×חוזים×$5`,
   `profit` משוקלל לפי contract split, `R:R`) + כלל בחירה + **חלון buffering** (לאסוף
   setups מתחרים) + tie-breaking → אישור Michael → מימוש. **שינוי trading logic.**
2. **MAX_CONTRACTS=5** (Michael החליט) — לאמת בקוד מה הוא שולט עליו (per-trade מול
   מצטבר/מקבילי) + **לאכוף** (GAP-4: כרגע מוגדר ולא נאכף ב-`risk_checks.py`) +
   ליישב מול Auth Table (מקס' 3/setup → עסקה לא תעבור 3 אלא אם משנים גם אותו).
3. **תקרת סיכון — אין כרגע.** ⚠️ שער חובה לפני LIVE (P-L0a). לא דחוף ב-SHADOW.
4. **DB ריק (0 trades), השרת לא רץ** → לא נאספים נתוני SHADOW. כיול הדגלים מחייב
   הרצת SHADOW. לאשר אם ה-DB אופס מכוון (`mems26_pre_shadow_reset_*`).
5. **הדלקת 5 הדגלים ב-SHADOW** — Michael אישר; פרומפט מוכן
   (`CC_PROMPT_ENABLE_FLAGS_SHADOW_2026-05-31.md`) — אך משמעותי רק כשהשרת רץ.

## מוכן/בתור (פרומפטים קיימים ב-`docs/handoff/`)
- `CC_PROMPT_ENABLE_FLAGS_SHADOW` — הדלקת דגלים + מעקב + revert per-flag.
- `MEGA_E2E_2of2_S1_S2_S3_IMPL` — בוצע (לעיון).
- `PIPELINE5_ACTION_PLAN` (`docs/plans/`) — תוכנית 3 שלבים (audit→decisions→impl);
  שלב 1+2 בוצעו/נעולו; **P5-1 implementation טרם נכתב** (gated: SHADOW ירוק + action plan).

## אימותים שאולי ממתינים מ-CC
- אם CC מחזיר דוח על backlog/except/ZLR — אמת מול הראיות הגולמיות.
- GAP-6 ציין 39 ZLR failures, אבל PYTEST_GREEN_FINAL=0 failed → לאמת שה-ZLR אכן
  ירוקים/דולגו (לא להניח).

## הצעד הבא המומלץ
1. כתוב מפרט GAP-3 (R:R) → הצג ל-Michael לאישור → ואז פרומפט מימוש.
2. במקביל: פרומפט קצר ל-CC לאמת MAX_CONTRACTS (מה שולט + אכיפה + Auth Table).
3. כשמחליטים להריץ SHADOW: להדליק דגלים → להעלות שרת → לצפות (קצב ירי, התפלגויות).

> כל החלטה/ממצא → עדכן STATUS_BOARD + ROADMAP מיד (אשר בטקסט, בלי present_files לקבצי מעקב).
