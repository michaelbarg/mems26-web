# CC — Missed-Trade Analysis + Status-Board "Should-Have-Fired" Detector · 2026-06-05

חוזה + `CC_VERIFICATION_PROTOCOL`. **Sierra=SoT** ל-CCI/study. VERIFY file בסיום.
מקור: `docs/reports/MISSED_TRADES_ANALYSIS_2026-06-05.md` (קריאת-Cowork ראשונית).

**הקשר (אומת):** 2026-06-05 יום-מגמה-יורד. המערכת **זיהתה** signals אבל **0 ירו**.

## 🎯 BENCHMARK — 5 העסקאות שמיכאל ציפה (ground-truth, CT). לכל אחת חייבים תשובה:
| # | שעה (CT) | סוג | מערכת | חייב להסביר |
|---|----------|-----|-------|-------------|
| 1 | **8:35** | **REVERSAL** | S2 | ⚠️ בר 1-2 → FHB ב-**ACCUMULATING** (ברים 1-3 = אין תבניות, `first_hour_buffer.py:70`). האם זו הסיבה? האם להתיר reversal מוקדם? |
| 2 | **9:00–9:05** | **LONG טקטי** | S2 | FIRST_HOUR_TACTICAL (~בר 6-7). איזו תבנית-LONG? איזה gate חסם (choppiness?) |
| 3 | **9:20** | **SHORT** | S2/S4 | תבנית + gate שחסם |
| 4 | **9:35** | **SHORT** | S2/S4 | סביב מעבר FIRST_HOUR→DAY_TYPE (~9:30 CT) — האם המעבר השפיע? |
| 5 | **10:00** | **SHORT** | S2/S4 | DAY_TYPE_MODE — gate שחסם (choppiness/sizing/day_type) |

**לכל אחת מ-5 אלה:** איזו תבנית-שלנו תואמת · זוהתה?(panel flag) · entry/stop/T1 · **ה-gate המדויק
שחסם** (decision_tree reject + gateway blocked_by) · מה היה חסר · ה-I-# · והאם תוקן כבר (eve).

═══════════════════════════════════════
## חלק 1 · ניתוח רטרואקטיבי של היום (טבלה)
═══════════════════════════════════════
הרץ **כל detector** (S2: REACTIVE/INITIATIVE L/S, INV_HNS, HNS_TOP, DOUBLE_BOTTOM_EE,
DOUBLE_TOP_AA, BULL/BEAR_FLAG · S4: ZLR/TLB/TT/GB100/HFE/HTLB/FAMIR) **רטרואקטיבית על
ברי-RTH של היום** (`v9_bars_5min` + woodies CCI). לכל candidate הפק שורה:
`זמן(CT) · תבנית · מערכת · זוהה?(panel flag) · entry · stop(per-pattern ATR) · T1/T2 · R ·
gate-שחסם(decision_tree reject_reason + gateway blocked_by) · I-#`.
הצלב מול 7 ה-shorts של Michael. **Sierra cross-check** ל-CCI לכל שורה.

═══════════════════════════════════════
## חלק 2 · 🆕 גלאי "Should-Have-Fired" בסטטוס-בורד (חי, לומד)
═══════════════════════════════════════
**אפיון Michael:** lookback מתגלגל של **6 נרות מרגע פתיחת RTH** (08:30 CT) — בכל בר, בדוק את
6 הברים האחרונים וזהה האם נוצר **setup-איכותי שהיה צריך לירות אבל לא ירה**.

לבנות (OBSERVABILITY — **לא** משנה לוגיקת-ירי):
1. **detector חדש** `should_have_fired` — חלון מתגלגל 6-ברים מהפתיחה. setup-מועמד =
   (א) signal מ-detector קיים שנחסם ב-gate, **או** (ב) תנועה-נקייה-בכיוון-מגמה בחלון
   (למשל ≥X נק' בכיוון trend_state) שאף תבנית לא תפסה.
2. לכל מועמד: שמור `time · pattern/type · why-not (gate או "not-detected") · hypothetical R`
   (replay קדימה → hit T1/stop/timeout).
3. **חשיפה בסטטוס-בורד** — סקשן "⚠️ Missed / Should-Have-Fired": שורה פר-מועמד.
4. **persist יומי** (`v9_missed_trades` או JSON) → אוסף/לומד את הפער מדי-יום (לכיול).
- ערכי-סף (X נק' תנועה, חלון) — **הצע, אישור Michael** (זה מגדיר "עסקה-איכותית").
- אל תיגע ב-firing/risk; זה גלאי-תצפית בלבד.

═══════════════════════════════════════
## חלק 3 · 🆕 סימון מחזור-עסקה מלא על הצ'ארט (אפיון Michael — "פשוט מאוד")
═══════════════════════════════════════
לכל candidate, הגלאי מוציא **5 שדות** ומציג אותם כ-**markers על הצ'ארט** (השתמש/הרחב את
`TradeMarkerOverlay.tsx` הקיים):
1. **🔵 זיהוי (detection)** — ts+price של הבר שבו התבנית זוהתה (zlr/hfe/reactive…).
2. **🟢 כניסה (entry)** — מחיר-הטריגר (שבירת low/high של בר-הזיהוי בכיוון).
3. **🔴 סטופ ראשוני** — מעל/מתחת ל-high/low של התבנית (ATR per-pattern).
4. **🎯 יעדים** — T1/T2 לפי רמות-Sierra הקרובות (TPO POC/VAH/VAL מ-`_load_sierra_tpo`).
5. **⤴️ הזזת-סטופ (trail)** — לוגיקה: אחרי T1→BE, ואז trail מתחת ל-lower-high/VA-edge (long: הפוך).
שמור את כל 5 ב-`v9_missed_trades` ובתגובת `/api/v9/missed-trades`. בצ'ארט: קו מקווקו זיהוי→כניסה→סטופ→יעד.
**זה תצפית בלבד** (מה שהיה צריך לקרות) — לא ירי אמיתי.

═══════════════════════════════════════
## VERIFY (raw output)
- חלק 1: הדבק את הטבלה המלאה (כל candidate + gate שחסם) + צילום.
- חלק 2: `curl /api/v9/build_status/...` שמראה את סקשן ה-Missed · DB/JSON שנשמר · צילום-בורד.
- regression: setup ידוע (ZLR@13:35 / HFE@13:50) מופיע ב-Missed עם ה-gate הנכון.
- NOT-DONE: ערכי-סף שממתינים ל-Michael; פערי Sierra↔backend.
