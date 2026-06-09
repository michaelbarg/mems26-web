# Cowork Handoff — Next Chat (2026-06-05 night) — SHADOW רץ, יום-0 ירה 0, התמה: ספים יחסיים + כיול-לעין

**אתה (Cowork הבא):** orchestrator + verifier בלתי-תלוי של MEMS26. CC מבצע על ה-Mac;
אתה כותב פרומפטים, מצליב (**Rule 5: פקודה+פלט גולמי**), מעדכן בורדים, מריץ agents,
ומתקן frontend ישירות כשמהיר (Next dev עושה hot-reload).

## 0 · מקור-אמת + פרוטוקולים
`CLAUDE.md` — כולל **§Codebase Index Protocol** (אינדקס קודם! `backend/main.py`≠`backend/v9/main.py`).
`CC_HANDOFF_CONTRACT.md` · `CC_VERIFICATION_PROTOCOL.md`. בורדים: `STATUS_BOARD.md` (source-of-record) ·
`ROADMAP_TO_LIVE.html` (צ'קליסט) · **`docs/reports/MEMS26_ISSUES_REGISTER.md` (I-1…I-17, הרשימה העיקרית)**.
ניתוח-עסקאות: `docs/reports/MISSED_TRADES_ANALYSIS_2026-06-05.md` (כולל ה-benchmark + 8:36).

## 1 · מצב חי (eve) — מה תוקן ואומת
- **SHADOW רץ מ-0**, committed. day_type=**Normal** (S1 תקין ב-`backend/main.py:405`, IB מ-Sierra TPO).
- **תוקן ואומת חי (Cowork):** choppiness (I-16, 0 חוסמים) · trend_state/GRAY (I-15) · day_type endpoint (I-1) ·
  B-11 (הלוח לא משקר). **frontend:** Build Status P0 + Trades Phase 1 + visual-1:1 + **scroll** (2 העמודים) +
  **chart-crash** (`tpoLevels.ts` null-guard) — חלקם uncommitted, CC מבצע commit בפרומפט הנוכחי.

## 2 · 🎯 התובנה המרכזית של היום: **0 עסקאות ירו** — והשורש
ה-setups היו אמיתיים ואף **זוהו** (ZLR-DOWN, HFE, RED) — אבל **שרשרת חוסמים** הרגה כל נתיב-ירי:
choppiness (תוקן) · sizing=reject aux<2 (I-13) · FHB ACCUMULATING (8:35 reversal חסום מבנית) ·
Auth-Table SKIP×Normal · ZLR firing-detector מחמיר מהפאנל (I-3) · double-bottom לא-מזוהה (I-17).
**התמה המאחדת (אישור Michael):** **כל הספים צריכים להיות יחסיים-לתנודתיות, וה-detectors/entries
מכוילים לעין של Michael.** המצב-היחסי כבר בנוי (`S2_ATR_RELATIVE`) אבל היה כבוי.

## 3 · בתהליך עכשיו (פרומפט נשלח ל-CC)
`CC_PROMPT_ENABLE_RELATIVE_PLUS_FRONTEND_2026-06-05.md`:
(A) `S2_ATR_RELATIVE` → **default-ON** + `export=1` ב-SHADOW + תיקון-חיווט `double_bt.py:98,115`→`get_trough_tolerance`.
(B) commit כל תיקוני-ה-frontend. **כש-CC יחזיר — הצלב:** flag=True · double-bottom tolerance=ATR-יחסי ·
scroll · console נקי. (ה-K-ים לא כוילו — toggle נשאר עד soak.)

## 4 · Ground-truth של Michael (לכיול הגלאי)
5 עסקאות-benchmark (CT): **8:35 reversal-S2** (חסום FHB) · 9:00-9:05 LONG · 9:20/9:35/10:00 SHORT.
**8:36 מפורט:** SHORT כניסה **7544** · סטופ **7553.75** (מעל swing-3דק') · **2 חוזים** · T1 7529 · T2 7515 ·
R:R 1.54/2.97. **לקח-מפתח:** Michael נכנס **מוקדם (anticipation, בדחייה)** לא בשבירה → R:R כפול; כניסה-מאוחרת
(break) נכשלת ב-`r_t1` gate. + סטופ נקבע ב-**3-דק'** (multi-TF) לדיוק.

## 5 · Agents פעילים (Cowork)
`pattern-diag-30min` (deep, כל 30דק' RTH) · `mems26-eod-issues-designs` (23:10, שער CT≥15:00) ·
`mems26-missed-trades-investigator` (23:15, lookback-6-נרות + benchmark). **+ `missed_trade_detector`**
(backend חי, `main.py:426`, 6-bar-from-open, `MOVE_THRESHOLD_PTS=15` — ⏳ אישור-כיול Michael) →
endpoint `/api/v9/missed-trades`. **חלק-3 (סימון-צ'ארט detection/entry/stop/target/trail)** עוד לא נבנה.

## 6 · רשימת-כיול פתוחה (דורש החלטות Michael + soak)
I-3 ZLR strict · I-13 sizing aux<2 · **I-17 double-bottom** (tolerance→יחסי, נסגר בפרומפט הנוכחי חלקית) ·
FHB reversal-מוקדם · entry-timing (anticipation) · multi-TF stop (3דק') · MOVE_THRESHOLD=15 ·
כיול-K אחרי soak. **+ טבלת-EOD פר-תבנית** (כמה הזדמנויות/למה לא ירו) — הסוכן מפיק 23:15.

## 7 · לקחים מחייבים
1. **אינדקס קודם** (CLAUDE.md §Index). `backend/main.py` הוא ה-entry.
2. **אל תאבחן מ-endpoint יחיד** — `/day_type/state` קרא instance-מת → טעות "S1 dark" (תוקן).
3. **הצלב כל טענת-CC** (Rule 5). 4. **visual = 1:1 להמחשה**, לא רק פונקציונליות.
5. **כשמשהו מאושר — אל תעכב אותו** (טעות: עיכבתי את S2_ATR_RELATIVE שכבר אושר).

## 8 · הצעד הראשון בצ'אט הבא
1. הצלב את ה-VERIFY של פרומפט-המצב-היחסי (flag=True · double-bottom יחסי · scroll · console).
2. דוחות-ה-agents מהלילה (EOD + missed-trades) — סקור את **טבלת-EOD פר-תבנית** ואשר/כייל מול Michael.
3. אשר MOVE_THRESHOLD + K-ים; בנה חלק-3 (סימון-צ'ארט). סנכרן בורדים.
