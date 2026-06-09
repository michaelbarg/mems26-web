# Decision Brief — סף Volume-Exhaustion ל-Reactive (S2) · 2026-06-01

**סטטוס:** 🟡 **ממתין להחלטת Michael** — שינוי trading-logic / priors-change. **אפס קוד שונה.**
**מחבר:** Cowork agent · **מקור מחקר:** מחקר חיצוני שסיפק Michael (2026-06-01)
**רקע:** `DAY1_DEEP_ANALYSIS_2026-06-01.md` §3 (פריט A) · `AGENT_FIRE_AUDIT_VISIBLE_WINDOW_2026-06-01.md` §3a · `PATTERN_AUDIT_DAY1_2026-06-01.md`

> ⚠️ זהו פריט שמשנה **קצב ירי** של Reactive ולכן **את ה-priors של ה-SHADOW stats**. לפי CLAUDE.md (§Pre-LIVE: "strategic stop ... before any change that affects trading logic or risk surface") — דרוש אישור מפורש לפני מימוש. המסמך מציג מסקנה + הצעה + תוכנית אימות; ההחלטה שלך.

---

## 1 · ההחלטה הנדרשת

האם להחליף את סף ה-volume-exhaustion של Reactive מ-**"ירידת 90% בר-מול-בר"** (הבלתי-אפשרי) לסף **יחסי מבוסס-ממוצע (RVOL)** — ואם כן, באיזה stage להתחיל.

## 2 · מצב נוכחי בקוד (מעוגן, לא מהזיכרון)

`backend/v9/systems/five_min/five_min_system.py`:
- שורה 30: `DROP_THRESHOLD_PCT = 0.10` → בר 2 חייב ≤ 10% מ-volume של בר 1 (ירידת 90%).
- שורה 36: `LOOKBACK_MAX_VOL_RATIO = 0.6` → 3 הברים **לפני** בר 1 חייבים להיות שקטים (< 0.6× בר 1).
- `_detect_reactive` (≈שורה 499): הגייט בפועל הוא `b2_drop = b2_vol <= b1_vol * DROP_THRESHOLD_PCT`.

**עובדה אמפירית (מ-DAY1):** מתוך 54 זוגות ברים ב-2026-06-01, **0** עברו את 0.10; הקרוב ביותר 0.12 (ירידת 88%). → Reactive **לעולם לא יורה** בסף הנוכחי.

**מה כבר קיים שרלוונטי:** (א) `LOOKBACK_MAX_VOL_RATIO=0.6` — כבר מושג של volume יחסי, אך מוחל על ה-lookback ולא על בר 2. (ב) `_current_atr_5m` — ATR-14 מתגלגל כבר מחושב (תומך ב-overlay "narrow spread" ללא תשתית חדשה). (ג) **אין** ממוצע-volume מתגלגל ו**אין** RVOL-by-time-of-day — יידרשו לבנייה ב-Stage 2.

## 3 · מסקנת המחקר (תמצית)

1. **ירידת 90% בר-מול-בר ב-5-דק' RTH היא בלתי-אפשרית מבחינה מבנית.** ה-90% כנראה הגיע מ-**ברים יומיים** (או מקריאה שגויה של "no demand") והוחל בטעות על intraday.
2. **אף מתודולוגיה מוכרת לא משתמשת בסף אחוז קבוע בר-מול-בר:**
   - **VSA** (Williams / Coulling): "no demand/supply" = volume **נמוך מ-2 הברים הקודמים** + narrow spread (יחסי/אורדינלי, לרוב ירידה 10–40%), או "מתחת לממוצע 20".
   - **Wyckoff** (Secondary Test): מבחן low-volume = **40–60% מ-volume ה-climax** (לא 90%).
   - **Bulkowski:** **מגמת** volume רב-ברית, לא ירידת בר בודד.
   - **Order Flow:** "ייבוש" אגרסיבי איכותי (delta divergence / absorption), לא אחוז.
3. **volume ב-5-דק' אוטו-קורלטיבי חזק** (Bińkowski & Lehalle 2018; Admati & Pfleiderer 1988 — עקומת U). הירידה המבנית peak→midday היא ~50–65% **פרוסה על ~8 ברים**, לא צוק בודד.
4. **סף RVOL "נמוך" מתכנס סביב 0.5** (0.5–0.7 band; 0.75–1.25 = נורמלי). לאינדקסים יציב יותר (0.7–1.5).
5. **צריך נרמול time-of-day** (RVOL-TOD) כי עקומת ה-U מטה כל סף קבוע (over-fire בבוקר, under-fire באמצע היום).

## 4 · הצלבה: המחקר מול ה-spec שלנו

- המבנה ה-4-ברי שלנו (בר 2 = "תשישות מוכר/קונה") **מתורגם נכון** ל-"בר 2 = low-volume narrow-range יחסית" — בדיוק מה ש-RVOL/VSA תופסים ו-90% בר-מול-בר לא.
- VSA דורש **אישור**: no-demand → הבר הבא סוגר דובי; no-supply → הבר הבא סוגר שורי. זה כבר ממופה ל-ברים 3–4 שלנו (`b3_buyers`/`b4_confirm`). אין צורך בשינוי שם.
- ה-overlay של "narrow spread" יכול להשתמש ב-`_current_atr_5m` הקיים — אין תשתית חדשה ל-Stage 1.

## 5 · הצעה מדורגת (ממופה לקוד)

| Stage | שינוי | מיקום | תשתית חדשה? |
|-------|-------|-------|--------------|
| **1 (drop-in)** | החלף `b2_drop` ב-VSA-faithful: `b2_vol < b1_vol AND b2_vol < b0_vol` **וגם** `b2_vol ≤ 0.7 × rolling_avg_20(vol)` | `_detect_reactive` + const | ממוצע vol מתגלגל-20 (קל) |
| **2 (production)** | החלף ממוצע-20 ב-**RVOL-TOD**: בר מול ממוצע אותה שעת-שעון על 10–20 sessions; ירי כש-`RVOL_TOD < 0.5–0.7` | helper + שאילתת `v9_bars_5min` לפי clock-time | baseline TOD (בינוני) |
| **3 (tuning)** | כיול המכפיל ל-~5–10 setups/יום: התחל 0.7, הדק ל-0.5 אם רועש; gate-alone pass-rate יעד 5–18% | const + backtest | — |
| **overlay (אופ')** | "narrow spread": דרוש גם `b2_range < 0.7 × ATR` (משתמש ב-`_current_atr_5m` הקיים) | `_detect_reactive` | אין |

**הערה מהמחקר:** אל תהפוך את גייט ה-**volume** ל-ATR-relative — ATR מודד טווח-מחיר, לא volume. שמור אותם כשני גייטים משלימים.

## 6 · סיכון ו-priors-change

- **השפעה ישירה:** Reactive יעבור מ-0 fires ל-~5–10/יום → ה-SHADOW stats של S2 ישתנו. כל השוואה ל-baseline קודם נשברת מנקודת השינוי.
- **סיכון סף:** נמוך מדי → false positives; גבוה מדי → 0 (המצב הנוכחי). 3 התנאים האחרים (COT>AMT, belly, lookback) מסננים הלאה.
- **תאימות מקור-אמת:** השינוי הוא בלוגיקת trading על ברים ingested — **מותר** לפי CLAUDE.md (§Sierra: "trading logic on ingested bars" מותר). לא ממציא נתון.

## 7 · תוכנית אימות (לפני שמסמנים "done")

1. **אמת את הנחת ה-persistence על הנתונים שלנו:** חשב lag-1 autocorrelation של volume 5-דק' RTH מ-`v9_bars_5min` (המחקר מעריך ~0.7–0.9 אך לא אומת על MES שלנו).
2. **distribution של RVOL** על 20 sessions: כמה ברים עוברים 0.5 / 0.6 / 0.7? (כיול Stage 3).
3. **קצב signals:** הרץ את הלוגיקה המוצעת על ההיסטוריה → ספור setups/יום. יעד ~5–10.
4. **4 צירי UAT** (CLAUDE.md) על כל endpoint שמשתנה: Quality / Recency / Cardinality / Latency.
5. **Rule 5:** הדבק command + raw output לכל מספר לעיל.
6. **edge-cases:** הוצא/טפל בנפרד ב-2 הברים הראשונים אחרי 09:30, בבר 15:55–16:00 (closing auction), וב-roll/half-days — שם ירידות בר-בודד גדולות קורות טבעית ומעוותות baseline.

## 8 · אופציות החלטה (Michael)

- **A — אשר Stage 1 עכשיו** (drop-in, סף 0.7 + lower-than-prior-2), והרץ אימות §7 ב-SHADOW. מהיר, defensible, הופך Reactive לחי.
- **B — המתן ל-backtest** (§7.1–7.3) לפני נגיעה בקוד; החלט מכפיל מתוך הנתונים.
- **C — קפוץ ישר ל-Stage 2 (RVOL-TOD)** — נכון יותר אך יותר עבודה ו-baseline TOD לבנות.
- **D — דחה / השאר 0.10** (Reactive נשאר מושבת בפועל).

**המלצתי:** **A + §7 במקביל** — Stage 1 ב-SHADOW נותן אותות לאיסוף נתונים מיד, והאימות רץ במקביל לכיול לקראת Stage 2. זה תואם את "SHADOW = איסוף נתונים" בלי לסכן risk surface (עדיין shadow).

## 9 · Caveats (מהמחקר — להעביר כמו שהם)

- ספי RVOL (0.5="נמוך") מקורם בעיקר בתוכן trading-education (Plus500/Tradewink/StockTitan/StockCharts) — convention מקובל, **לא** קבוע אקדמי. לעומת זאת ה-autocorrelation/עקומת-U נשענים על ספרות peer-reviewed (Admati & Pfleiderer 1988; Bińkowski & Lehalle 2018).
- פילוחי ה-volume התוך-יומיים של ES (25% שעה ראשונה, ~8–10% אמצע) הם הערכות תעשייה, לא מדידות peer-reviewed — לאמת מול היסטוריית ה-MES שלנו.
- lag-1 autocorrelation המדויק של volume 5-דק' ES RTH לא פורסם במקור מאומת — חשב מהנתונים שלנו לפני סופיות.
- כל הספים לbacktest על נתוני MES שלנו; המכפיל הנכון תלוי ב-3 התנאים האחרים ובטולרנס frequency/quality.

---

*אפס שינוי קוד. מסמך החלטה בלבד. עם אישור → CC ממש לפי Stage שנבחר, עם raw verification (Rule 5) ועדכון roadmap/STATUS_BOARD.*
