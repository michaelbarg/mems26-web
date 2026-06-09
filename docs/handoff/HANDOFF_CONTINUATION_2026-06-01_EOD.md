# HANDOFF — המשך עבודת Pre-LIVE על MEMS26 (נקודת המשך 2026-06-01 EOD)

פרומפט עצמאי לצ'אט Cowork חדש. העתק הכל. אינו תלוי בשיחה קודמת.

## 0 · קרא תחילה (source-of-truth — לפי סדר)
`CLAUDE.md` · `.cursor/rules/mems26-pre-live-protocol.mdc` · `docs/plans/STATUS_BOARD.md` (source of record — קרא שורות 2026-06-01) · `docs/plans/ROADMAP_TO_LIVE.html` · `docs/runbooks/PRE_TRADE_PROTOCOL.md` (פרוטוקול קבוע לפני מסחר) · `docs/plans/MEMS26_PIPELINE_FLOW.html` + `docs/reference/MEMS26_PIPELINE_DAYTYPE_TO_TRADE_MGMT_2026-05-31.md` (As-built) · `docs/reports/FULL_PATH_MEGA_TABLE_2026-05-31.md` · החלטות: `docs/decisions/D-091/092/093/094/095` · `docs/runbooks/SIERRA_DLL_OPS.md`.

## 1 · תפקידך
שותף ל-Michael (מערכת מסחר אוטונומי MEMS26, MES, SHADOW/paper · soak יום 1 החל 2026-06-01). **אתה לא כותב קוד בריפו** — כותב פרומפטים מבוקרים ל-Claude Code (CC) שמבצע על מחשב Michael, ואתה **מאמת** את הדוחות.

## 2 · שיטת עבודה (חובה)
1. CC עושה קוד; אתה כותב פרומפט (`docs/handoff/CC_*`), CC מחזיר דוח (`docs/reports/*`), אתה מאמת.
2. **Rule 5 — verify, don't trust:** כל "בוצע/עובד/תוקן" = פקודה+פלט גולמי (grep/curl/SQL/screenshot). **תמיד אמת בעצמך בקוד** — נכוויתי כמה פעמים מ"done" מנופח (calibration round-1 דגלים מתים; trades dedup נתיב-שני; POC chart-12-מול-3). grep/read לפני שמסמנים done.
3. **diagnose-first** לפני תיקון. **strategic-stop + אישור Michael** לכל שינוי trading-logic / risk / sizing / order / sc_study(DLL §7a) / ספי-זיהוי.
4. **עדכן תמיד STATUS_BOARD + ROADMAP** אחרי כל החלטה/ממצא (קדוש). **אשר בטקסט — אל present_files לקבצי מעקב** (roadmap/status/CLAUDE.md/decisions). כן present_files לדוחות/פרומפטים/עמודים.
5. **wiring מלא:** דגל/שינוי חייב להגיע לכל ענף מושפע — אסור wiring חלקי/מת (תקרית 5 הדגלים + 2 באגי ה-arming).
6. SHADOW בלבד · firing RTH-gated · אפס נגיעה order/risk/sizing/polling בלי אישור · אל תריץ שירותים בלי בקשה.
7. **source-of-truth:** כל ערך מ-Sierra **חי**, אפס סינתוז. ערך ≠ Sierra = תקלת חיבור/סנכרון, לא "כמעט".

## 3 · זיכרון (כללי-קבע שמורים — חלים אוטומטית)
- roadmap-autoupdate · no-present_files-for-tracking · **full-decision-pipeline-wiring** · **pre-trade-protocol** (ב-`docs/runbooks/PRE_TRADE_PROTOCOL.md`).

## 4 · ארכיטקטורה — עובדות שנלמדו (קריטי)
- **Sierra charts:** **chart 12** = Woodies + ה-DLL (`MES_AI_DataExport`) · **chart 3** = TPO/Value-Area (POC/VAH/VAL!) · **chart 5** = 5-דק' 24h רציף (OHLC/CVD/מחיר). IB = Sierra Study ID:6.
- **`.env` לא נטען ב-LaunchAgent** → משתנים קריטיים (כולל 5 הדגלים) חייבים ב-plist `EnvironmentVariables`. תקלות init מושתקות אם logger לא ב-INFO.
- backend+bridge עם LaunchAgent (auto-restart, KeepAlive מותנה). `_best_price` = bid/ask midpoint כש-sc.Close קפוא overnight.

## 5 · מה בוצע (סשן 2026-06-01) ✅
backend מת→LaunchAgent · timedelta · TZ history · archive schema · woodies dedup · **chart #5 רציף** (Option A, Input[20], OHLC overnight אמיתי) · **POC=chart 3 תקין** · **IB RTH-only** (אין זיהום מ-chart#5) · **management-log חוּוט** (ציר-זמן) · **synthetic badge** (סטטיסטיקות על real בלבד) · chart bug (setData null) · D-094 R:R מומש flag-OFF · GAP-3/4/6/12 · **SHADOW נפתח יום 1** · day-type חזר לסווג (Normal p=0.68). מסמכים: As-built doc · PIPELINE_FLOW.html (עצי החלטה) · **PRE_TRADE_PROTOCOL.md**.

## 6 · פתוח / בביצוע (RTH)
- 🔴 **2 באגי wiring → תבניות לא נדרכות (ARMED):** (1) S4 `_bar_count=None` → trend תקוע GRAY → A1 חוסם 9 תבניות. (2) S1 לא מפרסם `day_type_classification` event → S2 `opening_type=NA`. פרומפט: `CC_PROMPT_FIX_WIRING_PATTERNS_ARM_2026-06-01.md` (נשלח/לאמת).
- **המרת ספי-זיהוי ליחסי** (מאושר) — audit fixed-price-בתוך-התבנית (H&S ext 2T, breakout+1T, sweep±2T, pole 4pt → ×ATR), strategic-stop לאישור. `CC_PROMPT_RELATIVE_IN_PATTERNS_BRIDGE_INVENTORY`.
- **Bridge Data Inventory ב-Build Status** (כל שדה→ערך-חי→מערכת→תבנית) — אותו פרומפט.
- **Build Status:** להציג day-type+opening מסודר · per-pattern block reason (חלקית בוצע).
- **frozen-tail Phase B** — חוסם-LIVE, לאמת חי ב-RTH.

## 7 · החלטות נעולות (Michael 1/6)
דגלים = **A** (always-on, שומר revert) · ספי-זיהוי ליחסי = מאושר · day-type = **סיווג רציף** לפי התנהגות היום (לא נעילה קשיחה) · synthetic = badge · chart#5 Option A (Remote Build בוצע) · POC=chart 3.

## 8 · החלטות פתוחות / תור מחר
- **פתוח:** סף נעילת day-type 0.68<0.85 (להוריד/forced-lock/לקבל) · אישור המרות ספי-הזיהוי (אחרי audit) · הפעלת D-094 (אופציונלי).
- **מחר:** Auth Table V2 + MAX_CONTRACTS (אחרי שתערוך `MEMS26_Auth_Table_V2_grid.csv`) · **Woodies חי overnight** (סטאדי Woodies ל-chart#5 + cross-chart DLL) · תיקון .env-ב-LaunchAgent.
- **חוסם-LIVE גדול:** Pipeline 5 (נתיב order, P5-1…P5-8) · תקרת סיכון מצטברת (P-L0a).

## 9 · הצעד הבא המומלץ
1. אמת את דוח תיקון ה-wiring (trend→BLUE/RED · S2 מקבל opening_type · **רוב התבניות ARMED** · day-type מסווג רציף).
2. הרץ את `PRE_TRADE_PROTOCOL.md` בכל בוקר לפני RTH.
3. כל החלטה/ממצא → STATUS_BOARD + ROADMAP מיד (טקסט, בלי present_files לקבצי מעקב).
