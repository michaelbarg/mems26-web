# P30 Woodies CCI Panel — Designer Brief (Hebrew, authoritative)

**Audience:** Designer / frontend implementing Sierra fidelity  
**Reference:** Sierra Chart screenshots (original), `docs/design/WOODY_PANEL_DESIGNER_SPEC_v1.md`, baseline `v14_data_right_aligned.html` (when available)  
**Date:** 2026-05-19 (Michael)

---

## חלק א׳: עמודת הנתונים הימנית — מה כל שדה אומר ולמה חשוב שיהיה חי

המעצב צריך להבין שזה **לא טקסט קישוטי** — זה ה-HUD (Heads-Up Display) שמייקל מסתכל עליו תוך כדי החלטת מסחר בזמן אמת. כל מספר כאן צריך להתעדכן עם כל tick של השוק (בערך כל שנייה במהלך שעות מסחר).

### 10 השדות לפי הסדר מלמעלה למטה

| # | שדה | דוגמה | מה זה אומר | קצב עדכון |
|---|---|---|---|---|
| 1 | **CCIDiff H** (ירוק) | `55.19 CCIDiff H` | ההפרש בין CCI-14 ל-TCCI (CCI-6) בנקודת ה-**High** של הבר הנוכחי. סימן שהמומנטום מתחזק כלפי מעלה. | חי — כל tick |
| 2 | **CCIDiff** (לבן) | `55.19 CCIDiff` | ההפרש הנוכחי בין CCI-14 (קו שחור) ל-TCCI (קו צהוב). זה הערך **המרכזי** של ה-divergence. | חי — כל tick |
| 3 | **CCIDiff L** (מג'נטה) | `55.19 CCIDiff L` | ההפרש באותו בר בנקודת ה-**Low**. סימן שהמומנטום מתחזק כלפי מטה. | חי — כל tick |
| 4 | **High Prev/Cur** (ירוק) | `7371.00 7375.00 High Prev/Cur` | שני High של 2 הברים האחרונים. השוואה מיידית האם הבר הנוכחי שובר את ההיי של הקודם. | חי — כל tick |
| 5 | **Last Price** (שחור, 22px) | `7374.00 Last Price` | **המחיר הנסחר כרגע**. זה השדה הכי גדול וחשוב. מייקל קורא אותו בלי להזיז את הראש. | חי — **כל tick** |
| 6 | **Low Prev/Cur** (שחור) | `7356.75 7366.75 Low Prev/Cur` | שני Low של 2 הברים האחרונים. מקביל לשורה 4 אבל בלואים. | חי — כל tick |
| 7 | **ProjHigh** (ציאן) | `7667.00 ProjHigh` | חיזוי High של היום מבוסס Initial Balance + range. **קלוט מ-DLL**. | מתעדכן כל ~5 דקות (פעם בבר) |
| 8 | **ProjLow** (מג'נטה) | `7074.75 ProjLow` | חיזוי Low של היום. מקביל ל-ProjHigh. | מתעדכן כל ~5 דקות (פעם בבר) |
| 9 | **CCI Pred. H/L** (שחור) | `18.1  18.1 CCI Pred. H/L` | חיזוי ערכי CCI-14 לבר הבא — High ו-Low תיאורטיים. בשימוש לזיהוי הצטלבויות עתידיות. | חי — כל tick |
| 10 | **Low Prev/Cur (זווית)** (שחור) | `-67.7° Low Prev/Cur` | **הזווית הגאומטרית** של ה-trend line של ה-Lows ב-2 הברים האחרונים. שלילי = יורד, חיובי = עולה. מודד תלילות. | חי — כל tick |

### כללי תצוגה לכל השדות

- **יישור:** כולם right-aligned ל-x=447 (ראה סעיף 5.12 במפרט).
- **רקע:** **שקוף לחלוטין** מעל הגרף — בלי תיבה כהה. הטקסט "צף" מעל ה-`#2D5555`. ב-Sierra הוא חלק מאותו canvas של הגרף, לא widget נפרד.
- **פונט:** כל השורות 11px bold **חוץ מ-Last Price** שהוא 22px bold.
- **צבעי הצמדה:** הצבעים נושאים מידע סמנטי — אסור לשנות:
  - ירוק = ערכי High / מומנטום עולה
  - שחור = ערכי Low / מידע ניטרלי
  - מג'נטה = ProjLow / מומנטום יורד
  - ציאן = ProjHigh

---

## חלק ב׳: איך השדות עוזרים לקרוא את הגרף

### חיבור 1: CCIDiff (שורות 1–3) ↔ המרחק בין הקו השחור לקו הצהוב

```
בגרף:     קו שחור (CCI-14)  ─────╮
                                  │ ← המרחק
               קו צהוב (TCCI) ───╯

בעמודה:   55.19 CCIDiff
```

- CCIDiff חיובי וגדל → שחור מעל צהוב → divergence bullish.
- CCIDiff שלילי → שחור מתחת לצהוב → bearish.
- CCIDiff → 0 → סף ZLR פוטנציאלי.

### חיבור 2: CCI Pred. H/L (שורה 9) ↔ איפה ה-X הלבן יהיה ברגע הבא

- X לבן = CCI-14 על הבר הנוכחי.
- שורה 9 מנבאת טווח CCI בבר הבא בתוך ±240.
- `200+` בחיזוי → התכוננות ל-extreme / אקזיט.

### חיבור 3: זווית (שורה 10) ↔ שיפוע קו Lows

- `-67.7°` = ירידה תלולה; קיצון → מומנטום יורד מאבד אוויר.

### חיבור 4: ProjHigh / ProjLow (7–8) ↔ הקשר יומי

- הגרף ≈ 30 ברים (~2.5h); Proj = תקרה/תחתית יום צפויות שלא נראות בגרף.

---

## חלק ג׳: גלילת זמן — שתי שכבות

### שכבה 1: רצועת זמן (Zone 2)

גרירה אופקית → **ברים + קווים + ZLR + X (אם בטווח) + תוויות זמן** נגללים יחד.

**לא זז עם גלילת זמן:** קווים מקווקווים ±200/±100/0, ציר Y, **עמודת הנתונים**, מסגרת, Title Bar.

**חוק:** בר #N תמיד מעל חותמת הזמן שלו — סנכרון 1:1.

**Live:** בר ימני = building; כל 5m ננעל, הכל זז שמאלה.

**Historical (§6.8):** גרף קפוא; X נעלם; כפתור "back to NOW"; **Last Price בעמודה ממשיך חי**; שאר עמודה לפי בר מוצג / Sierra behavior.

### שכבה 2: ציר Y (Zone 4)

נפרד מגלילת זמן. גרירה אנכית על ציר Y משנה scale (ברירת מחדל ±240).

---

## חלק ד׳: כותרת — מה חסר במוקאפ

Sierra מציגה בכותרת (בנוסף ל-CCI ו-Trend):

```
(6, 5, 14, 100, HLC Avg)  Commodity Channel Index  CCI: …  Line 1: …  Line 2: …
```

מפרט §5.2: **מינימום 6 אלמנטי טקסט** + `(6…` לפרמטרי study. המוקאפ הנוכחי קיצץ — זה באג מול Sierra.

---

## חלק ה׳: סיכום מבצעי למעצב

> המוקאפ הנוכחי הוא קריקטורה — לא רפלקציה. מייקל צריך **את Sierra בתוך הדשבורד**. פיקסל, צבע, מיקום, טקסט כמו בתמונת הרפרנס.
>
> הבדל מותר: רקע `#2D5555` במקום `#1F4848` לקוהרנטיות דשבורד.
>
> **3 משימות מיידיות:**
> 1. עמודת נתונים — 10 שורות, right @ x=447, Last Price 22px שחור, **רקע שקוף**.
> 2. ציר Y — ±240 קבוע (13 ערכים, כל 40); אדום רק ±200.
> 3. Baseline `v14_data_right_aligned.html` — השוואה side-by-side.
>
> **בדיקה:** כל אלמנט במוקאפ חייב להופיע ב-Sierra; אחרת — באג.

---

## Implementation note (for dev agents)

Current code (`buildDataTexts`) does **not** yet implement Michael's semantics:

| Field | Required | Current code gap |
|-------|----------|------------------|
| CCIDiff H/L | CCI-14 − TCCI at bar High/Low | Single `cci_14 - cci_14_prev` copied ×3 |
| High/Low Prev/Cur | Previous bar + current bar OHLC highs/lows | Wrong `prevRef` from CCI math |
| ProjHi/Lo | From Sierra DLL export | API `max(high)+2` approximation |
| Angle | Geometric slope of lows (2 bars) | `atan2(cci_prev - cci_3ago)` — wrong domain |
| Data column bg | Transparent | `rgba(18,42,42,0.72)` box — **remove** |
| Time strip | Scroll history, sync bars | Partial: bar zoom on strip — **reconcile with Michael** |

See English mirror: `P30_WOODIES_DESIGNER_BRIEF_EN.md`
