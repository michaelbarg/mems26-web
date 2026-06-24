# מערכת 2 (5‑דקות) — תנאי הירי של כל תבנית (מהקוד החי, 2026‑06‑24)

_בדיקה READ‑ONLY מהקוד. מקור: `backend/v9/systems/five_min/`. ציטוט file:line ליד כל תבנית. לא שונה כלום._

## סדר הבדיקה (`five_min_system.process_bar`, ~שורות 1020‑1052)
הגלאים רצים **בשרשרת — הראשון שתופס מנצח**, על **ברים סגורים בלבד** (`_det_buf = buffer[:-1]`):

1. **Reactive** (כל בר) → 2. **Initiative** (אם Reactive ריק) → 3. **H&S + Double** (רק ב‑DAY_TYPE_MODE + סוג‑יום מורשה) → 4. **Flags** (אותו תנאי).

---

## א. תבניות הליבה — רצות בכל בר (Reactive / Initiative)

### 1. REACTIVE LONG / SHORT — תבנית 4 ברים (`five_min_system.py:580‑720`)
היגיון: חולשת מוכרים (LONG) / חולשת קונים (SHORT). **LONG:**

- **בר 1** — מוכרים שולטים: `b1.close < b1.open` ו‑`vol>0`.
- **בר 2** — צניחת ווליום: `b2.vol ≤ 10% × b1.vol` (צניחה 90%, `DROP_THRESHOLD_PCT=0.10`).
- **בר 3** — קונים: `b3.close > b3.open` + **belly** קונה (footprint) + **POC עולה**.
- **בר 4** — אישור: `b4.close > b4.open` **וגם** `b4.close > b3.high` (סגירה מעל כל הטווח של בר 3).
- **lookback** — 3 הברים שלפני בר 1 שקטים: `max(vol) < 0.6 × b1.vol` (`LOOKBACK_MAX_VOL_RATIO=0.6`).
- **COT > AMT** — ⚠️ **מבוטל כברירת‑מחדל** (S2⟂S3, ראה למטה). belly_ratio≥1.5 או None.
- ביטחון: 0.80 אם POC עולה, אחרת 0.75.

**SHORT** = מראה (בר1 קונים, בר3 מוכרים, `b4.close < b3.low`).
דרישת מינימום: `MIN_BARS_REQUIRED=7` (4 תבנית + 3 lookback).

### 2. INITIATIVE LONG / SHORT — תבנית 4 ברים (`five_min_system.py:722‑819`)
היגיון: התרחבות יוזמת + טסט + הצטרפות. **LONG:**

- **בר 1** — התרחבות שורית: `b1.close>b1.open` ו‑`1.3×avg ≤ b1.range ≤ 2.5×avg` (ממוצע טווח 14 ברים; לא ATR).
- **בר 2** — טסט: `b2.low > b1.low` (Higher‑Low) **או** חזרה ל‑POC (`|b2.close − POC| ≤ 0.2×avg`).
- **בר 3** — הצטרפות: `b3.range > b1.range`.
- **בר 4** — טסט שני + כניסה: `b4.low ≥ b2.low` **וגם** `b4.close > b1.high`.
- **COT < AMT** — ⚠️ **מבוטל כברירת‑מחדל**. lookback שקט כמו ב‑Reactive.
- ביטחון: 0.80.

**SHORT** = מראה (בר1 דובי, בר2 Lower‑High/POC, `b4.high ≤ b2.high`, `b4.close < b1.low`).

---

## ב. תבניות גיאומטריות — רק ב‑DAY_TYPE_MODE **ובסוג‑יום מורשה**

> שער: `chart_patterns_allowed(day_type, pkg)` (`:98`). **None / UNKNOWN / Nontrend → לעולם לא יורה.** ⇒ באג סוג‑היום משתיק אותן בשקט.

### 3. INVERSE H&S (LONG) / H&S TOP (SHORT) (`patterns/head_shoulders.py`)
- **מינ' 12 ברים**, 3 נקודות‑סווינג (LS, ראש, RS; pivot lookback 2).
- ראש קיצוני: LONG ⇒ הראש הנמוך מבין השלושה; SHORT ⇒ הגבוה.
- **סימטריית כתפיים** ≤ 5% מהמרחק ראש‑לכתף ממוצעת.
- **הראש חורג ≥ 2 טיקים** מעבר לכתף הממוצעת.
- צוואר = max השיאים (LONG) / min השפלים (SHORT) שבין הכתפיים.
- **ירי:** `close > neckline + טיק` (LONG) / `close < neckline − טיק` (SHORT).
- **סוגי‑יום מורשים (Pkg 5a):** Neutral_Extreme · Neutral_Center · Normal · Variation.

### 4. DOUBLE BOTTOM Eve&Eve (LONG) / DOUBLE TOP Adam&Adam (SHORT) (`patterns/double_bt.py`)
- **מינ' 10 ברים**, 2 שפלים/שיאים סימטריים ≤ 3%.
- **וריאנט:** Double‑Bottom — שני שפלים **רחבים ≥ 3 ברים** (Eve); Double‑Top — שני שיאים **חדים ≤ 2 ברים** (Adam).
- צוואר = max שיאים‑ביניים (DB) / min שפלים‑ביניים (DT); חייב לעלות ≥ סף מעל השפל.
- **ירי:** `close > neckline + טיק` (DB) / `close < neckline − טיק` (DT).
- **סוגי‑יום מורשים (Pkg 5a):** כמו H&S.

### 5. BULL FLAG (LONG) / BEAR FLAG (SHORT) (`patterns/flags.py`)
- **מינ' 10 ברים**. **מוט (pole):** 5–15 ברים, גובה ≥ 16 טיק (4 נק' MES), ≥ 60% מהברים סוגרים בכיוון.
- **דגל (flag):** 3–8 ברים, ריטרייס ≤ 50% מהמוט, אף בר‑דגל לא סוגר מעבר לקצה‑המוט.
- **ירי:** `close > flag_high + טיק` (Bull) / `close < flag_low − טיק` (Bear).
- **סוגי‑יום מורשים (Pkg 5c):** Trend_Normal · Trend_DD · Variation · Neutral_Extreme · Normal.

---

## ג. שערים משותפים (מעבר לתנאי‑הצורה של כל תבנית)

1. **סוג‑יום (גיאומטריות + דגלים):** None/UNKNOWN/Nontrend → לא יורה. דגל `S2_CHART_ALL_DAYTYPES=1` פותח לכל סוג מלבד Nontrend.
2. **COT/AMT מבוטל (S2⟂S3, Michael 2026‑06‑08):** Reactive/Initiative יורות על גאומטריית‑מחיר + ווליום בלבד; הסף חוזר רק עם `S2_REQUIRE_COT_AMT=1` + אישורך.
3. **belly / POC / belly_ratio "graceful":** כש‑footprint מושתק (None) — התנאים האלה **עוברים אוטומטית**. כלומר התבנית יורה **בלי** אישור ה‑order‑flow שהאפיון דורש.
4. **NO_TRADE / Nontrend early‑skip** (D‑091.Q2) — חוזר עוד לפני הגלאים.
5. **dedup cooldown** + **First‑Hour‑Buffer eligibility** — חוסמים ירי חוזר של אותה תבנית.
6. **שערי gateway במורד הזרם** (לא חלק מהתבנית): DIRECTION_CONTEXT, reactive_location_gate, daytype_playbook.

---

## ד. קשר לנקודה 6 שלך ("היורות לא תואמות לאפיון")
- **Reactive/Initiative** יורות בלי COT/AMT ובלי belly/POC (graceful None) → **חסר אישור ה‑order‑flow** שבאפיון המקורי. זה מקל את התנאי לעומת הספֵק.
- **הגיאומטריות (H&S/Double/Flags)** תלויות סוג‑יום — ועם באג סוג‑היום (None/Trend_Normal שגוי) הן או נדלגות בשקט או יורות בסוג‑יום הלא‑נכון.
- **`MIN_BARS` שונה בין תבניות** (7 ליבה / 10 דגל+double / 12 H&S) — לא אחיד.

_מקור הקוד: `backend/v9/systems/five_min/five_min_system.py` (Reactive/Initiative + שער סוג‑יום) · `patterns/flags.py` · `patterns/double_bt.py` · `patterns/head_shoulders.py` · `compliance_manifest.yaml`._
