# CC הוראת עבודה — Near-Miss + הקלות אפשריות (S1 · S2 · S4)

**תאריך:** 2026-05-29 · **שעת בדיקה:** ~11:05 ET · **כותב:** Cowork (DB+קוד; אין גישה ל-API/לוגים)
**מטרה:** מה התנאים הכי קרובים לירי בכל מערכת היום, ומה אפשר *להקל* (המלצה בלבד —
**אסור לשנות קוד-מסחר ללא אישור Michael**, CLAUDE.md § Strategic stop).

> **הקשר חשוב:** הניתוח מהיום בלבד. רוב המסקנות מבוססות על ה-DB; חלק (near-miss של S2,
> אישור wiring) דורש לוגים חיים על ה-Mac — מסומן [CC-MAC].
> **באג רקע ידוע** (ראה `CC_DIAGNOSE_5MIN_AND_FRONTEND_LATENCY_2026-05-29.md`):
> שורות ts עתידיות (+1h) ב-`v9_bars_5min` מזהמות את buffer ה-S2 — ייתכן שזה תורם לאפס
> הירי של S2. לתקן אותו לפני שמסיקים ש"הטקטיקות צריכות הקלה".

---

## 0. תמונת מצב — ירי היום לפי מערכת (מ-DB)

| מערכת | ירה היום? | ראיה |
|-------|-----------|------|
| **S1** Day Type | ❌ לא ננעל | `lock_state=PENDING`, day_type=`Normal` (ברירת מחדל), conf 0.68, stage תקוע ב-B2 |
| **S2** 5-min | ❌ 0 setups | `v9_five_min_setups` ריק היום |
| **S4** Woodies | ✅ פעיל מאוד | 142 signals, **62 trades FILLED** + 12 PARTIAL + 1 OPEN |

**מסקנה:** S4 עובד. S1 לא ננעל (וזה משפיע על S2). S2 לא יורה כלום — צריך לאמת אם זו
החלטה נכונה (אין pattern) או חסימה (buffer מזוהם / שער לוגי).

---

## 1. S1 — DAY TYPE: זמנים מדויקים + מה חסר

### 1.1 ציר הזמן המדויק (מהקוד · `state_machine.py`)

| שלב | שעה ET | מה קורה | קובץ |
|-----|--------|---------|------|
| A1 | 09:30 | Pre-open context (gap, PD, overnight) | `state_machine.py:357` |
| **A2** | **~09:45** | זיהוי Opening Type — דורש **≥3 ברים RTH (15 דק')** | `:444-458` |
| A3 | 09:30–10:30 | IB Tracking — **רק מ-Sierra Study** (אין fallback מברים) | `:460-478` |
| **A4** | **10:30** | **IB Lock** + סיווג רוחב | `:480-518` |
| B1 | 10:30 | Vote ראשון דרך Decision Matrix `(opening_type × ib_width)` | `:522-540` |
| B2–B6 | 10:30+ | מעקב התפתחות, re-score | `:542-627` |
| **C1** | — | **נעילה** | `:680-703` |

**תנאי הנעילה (C1, `state_machine.py:684-687`):**
- `confidence ≥ 0.70`, **או**
- אותו vote פעמיים ברצף, **או**
- `session_min ≥ 210` → **נעילה כפויה ב-13:00 ET**.

### 1.2 מה קרה היום (מ-DB)

- IB נוצר תקין: `ib_high=7611.75`, `ib_low=7586.75`, רוחב **MEDIUM** (25 נק').
- `opening_type = INDETERMINATE` (state: `NA`).
- Decision Matrix: `(INDETERMINATE, *) → Normal` (`decision_matrix.py:59-62`) — כלומר
  **day_type=Normal הוא ברירת מחדל, לא קריאה אמיתית של השוק.**
- `confidence = 0.68` → **מתחת ל-0.70**, אז אין נעילה על ביטחון. תינעל רק ב-13:00 ET
  (fallback) או ב-2× vote.
- **אנומליה:** stage תקוע ב-**B2** כל היום (69 שורות 10:30–11:00 ET); לא התקדם ל-C1/C2/C3.
  ב-`process_bar` רצף B2→B6 אמור להעביר ל-C1 באותה קריאה (`:627`). חשד:
  `_stage_b6` חוזר מוקדם אם `vote_history` ריק (`:591`), או שה-engine נבנה מחדש כל בר.
  **[CC-MAC] לאמת בלוג** למה לא מתקדם מ-B2.

### 1.3 מה ה"חוסר" (תשובה ישירה לשאלה שלך)

1. **Opening Type לא סווג** → קיבלת `INDETERMINATE` → day_type נפל לברירת מחדל `Normal`.
   זה הליבה. השוק היה רוטציוני/לא-מובהק בפתיחה, אז ה-detector לא נתן OD/OTD/ORR.
2. **לא ננעל** כי conf 0.68 < 0.70. עד 13:00 ET ה-day_type "רך" (PENDING).
3. **שני detectors ל-opening קיימים** ולא ברור מי חי:
   - `detector.py:detect_opening_type` (משמש את A2, `:452`) — מחזיר OD/OTD/ORR/AUCTION,
     **לעולם לא INDETERMINATE**.
   - `open_type.py:classify_open_type` — חדש יותר (30-min range/VA), conf 0.7–0.85.
   **[CC-MAC] לאמת איזה מהם מזין את ה-state בפועל**, ומאיפה בדיוק נכתב `INDETERMINATE`.

### 1.4 ספי ה-opening (הלברים להקלה · `detector.py`)

| Opening Type | תנאי | conf |
|--------------|------|------|
| OPEN_DRIVE | `directional_ratio ≥ 0.7` + כל הברים באותו כיוון | 0.95 |
| OPEN_TEST_DRIVE | pullback ratio 0.2–0.6 | 0.70 |
| OPEN_REJECTION_REVERSE | `|last_move| ≥ |first_move|×0.5` | 0.65 |
| OPEN_AUCTION_OUT | פתיחה מחוץ ל-PD range | 0.50 |
| OPEN_AUCTION_IN | אחרת (רוטציוני בתוך טווח) | 0.40 |

---

## 2. S4 — WOODIES: ירה 62 פעמים. מה כן נחסם (near-miss)

S4 בריא. ה-near-miss כאן = signals שזוהו אך לא הפכו לעסקה.

### 2.1 שער הירי (`woodies_system.py`)

| שער | תנאי | קובץ |
|-----|------|------|
| RTH gate (F17) | רק ברי RTH | `:260` |
| YELLOW lock (P-W5) | מצב YELLOW **חוסם את כל 9 הפטרנים** | `:303-307` |
| בחירת pattern | best confidence (W-8 R_t1 dispatch) | `:311-318` |
| sizing | חייב `!= "reject"` כדי לירות | `:328` |
| dedup | אותו bar_ts+pattern+direction = לא יורה שוב | `:401` |

**`sizing="reject"` נקבע ע"י (`five_min_system.py:594-606`, משותף):**
- pattern לא בָּשֵׁל (stage), **או**
- COT/AMT לא חזק: long דורש `cot > amt×1.2`, short דורש `cot < amt×0.8`.

### 2.2 התפלגות signals היום (near-miss)

```
HTLB SHORT 62 (conf 0.65) · TLB LONG 40 (0.55–0.85) · HTLB LONG 16 (0.65)
GB100 LONG 8 (0.50–0.85) · ZLR LONG 4 (0.80–0.90) · VEGAS L/S 3+3 (0.75)
ZLR SHORT 3 (0.66–0.69) · TLB SHORT 2 (0.49–0.85) · TT LONG 1 (0.70)
```
ה-signals הכי "קרובים אך חלשים": **TLB SHORT 0.49, GB100 0.50, TLB LONG 0.55**.
אם אלו לא הפכו לעסקה — סביר שנחסמו ב-COT/AMT (1.2×/0.8×) או ב-YELLOW.

### 2.3 לברים להקלה ב-S4 (המלצה בלבד)
- מפתח COT/AMT: `1.2×` (long) / `0.8×` (short) → הורדה ל-1.1×/0.9× תגדיל ירי **ותגדיל רעש**.
- YELLOW lock: כרגע חוסם הכל. אפשר לאפשר פטרנים בעדיפות-גבוהה ב-YELLOW — **שינוי risk**.

---

## 3. S2 — 5-MIN: 0 ירי. שרשרת השערים + מה הכי קרוב

### 3.1 שרשרת השערים (`five_min_system.py:665-785`)

1. **Mode:** OVERNIGHT/MAINT/WEEKEND → רק buffer, אין ירי (`:699`). פתיחה → FIRST_HOUR_TACTICAL → אחרי שעה DAY_TYPE_MODE.
2. **Nontrend:** `current_day_type=="Nontrend"` → דילוג NO_TRADE (`:723`). *(היום Normal, אז לא חוסם.)*
3. **Detectors:** Reactive → Initiative (תמיד רצים).
4. **Chart patterns** (H&S/Double · Pkg 5a/5b) — רק ב-DAY_TYPE_MODE + `current_day_type ∈ {Neutral_Extreme, Neutral_Center, Normal, Variation}` (`:752`). *(Normal עובר!)*
5. **Flags** (Pkg 5c) — `∈ {Trend_Normal, Trend_DD, Variation, Neutral_Extreme, Normal}` (`:766`). *(Normal עובר!)*
6. **FHB eligibility** (ב-FIRST_HOUR בלבד): `is_pattern_eligible` (`:778`).
7. **sizing != reject** (COT/AMT 1.2×/0.8× · `:594-606`).

### 3.2 ספי ה-detectors (`five_min_system.py`)

| Pattern | תנאים עיקריים | conf | קובץ |
|---------|----------------|------|------|
| Reactive | belly dominance `≥1.5` + bar4 confirm + close מעבר ל-bar3 + COT vs AMT | — | `:437-510`, `BELLY_DOMINANCE_RATIO=1.5 :37` |
| Initiative | מבנה stage-4 ספציפי | 0.80 | `:513-576` |

### 3.3 מה חוסם את S2 היום — היפותזות לפי סבירות
1. **day_type לא היה זמין מוקדם:** עד 10:30 ET `current_day_type=None` → כל פטרני
   chart/flag דולגו בשקט + לוג `[FiveMin] current_day_type is None` (`:746`). מ-10:30
   day_type=Normal זמין → אמורים להיפתח. **[CC-MAC] לבדוק בלוג מתי current_day_type התעדכן.**
2. **buffer מזוהם מ-ts עתידי** (+1h) → סדר/בָּשלוּת הברים שגויים → detectors לא מתכנסים.
   **לתקן את באג ה-ts קודם.**
3. **אין pattern אמיתי** — ייתכן שזו התנהגות נכונה (שוק רוטציוני, אין setup).
4. **v9_five_min_state ריק** → אם הפרונטאנד/סטטוס מציגים S2 מהטבלה, נראה "מת" גם אם הליבה רצה.

### 3.4 לברים להקלה ב-S2 (המלצה בלבד)
- `BELLY_DOMINANCE_RATIO` 1.5 → 1.3 (reactive קליל יותר).
- COT/AMT 1.2×/0.8× → 1.1×/0.9×.
- דרישת בָּשלוּת (stage) של פטרנים.
- הרחבת gate סוג-היום (כבר רחב; Normal נכלל).
> כל אלו מגדילים ירי **ומגדילים false-positives** לפני LIVE. לא לפני שבאג ה-ts תוקן
> ואומת ש-0 הירי אינו תוצר חסימה טכנית.

---

## 4. [CC-MAC] בדיקות לאישור על ה-Mac (לוגים + API)

```bash
cd /Users/michael/Downloads/mems26_web_git

# 4.1 — S2: למה אין ירי? חפש את שלשת הלוגים הקריטיים
grep -E "current_day_type is None|FHB gate|NT NO_TRADE|FIRE:" /tmp/mems26_backend.log | tail -40
#   "current_day_type is None"  → day_type לא הגיע ל-S2 (בעיית event delivery)
#   "FHB gate ... blocked"       → First-Hour buffer חסם pattern שכן זוהה (near-miss אמיתי!)
#   אין שום שורה                  → שום pattern לא זוהה (אין setup, לא חסימה)

# 4.2 — S1: למה stage תקוע ב-B2 ולמה opening=INDETERMINATE
grep -E "\[DayType\]|opening_type|stage=|lock_state|B2|C1" /tmp/mems26_backend.log | tail -40

# 4.3 — אמת מי מזין opening_type (detector.py vs open_type.py)
grep -rn "detect_opening_type\|classify_open_type" backend/v9 --include=*.py | grep -v __pycache__ | grep -v "def "

# 4.4 — S4: כמה signals נחסמו ב-sizing=reject / YELLOW (near-miss אמיתי)
grep -E "YELLOW state|reject|FIRE" /tmp/mems26_backend.log | grep -i woodies | tail -30

# 4.5 — API חי: מצב 3 המערכות עכשיו
curl -s http://localhost:8000/api/v9/build/pattern-status | python3 -m json.tool | head -80
```

---

## 5. סיכום המלצות הקלה (לפי עדיפות · אישור Michael חובה)

| # | מערכת | הקלה | סיכון | קדימות |
|---|-------|------|-------|--------|
| 1 | — | **תקן באג ts עתידי** (לא הקלה — באג) | אין; מבטל חסימה טכנית | **קודם כל** |
| 2 | S1 | בדוק/תקן wiring של opening detector (INDETERMINATE → סיווג אמיתי) | בינוני (לוגיקת-מסחר) | גבוה |
| 3 | S1 | הקדם forced-lock מ-13:00 ET, או הורד conf 0.70→0.65 | נועל ניחוש חלש מוקדם | בינוני |
| 4 | S2 | `BELLY_DOMINANCE_RATIO` 1.5→1.3 + COT/AMT 1.2/0.8→1.1/0.9 | יותר false-positives | נמוך (אחרי #1) |
| 5 | S4 | אפשר high-priority patterns ב-YELLOW; COT/AMT 1.1/0.9 | יותר רעש | נמוך |

**עקרון:** קודם לוודא ש-0 הירי של S2 אינו תקלה טכנית (#1+#4.1). רק אם הליבה רצה נכון
ועדיין לא יורה — לשקול הקלת ספים. כל שינוי סף = +regression test +אימות 4 צירי +דיווח.

**קבצים:** `state_machine.py` (680 lock, 444 A2), `detector.py:36` (opening), `decision_matrix.py:59`
(INDETERMINATE→Normal), `schemas.py:96-100` (config), `woodies_system.py` (260/303/328 gates),
`five_min_system.py` (37 belly, 594-606 sizing, 665-785 process_bar).
