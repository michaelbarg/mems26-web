# שאלת ספק · Zohar · Pkg 2bc S2 OFA Configuration

**תאריך:** 2026-05-23 19:55 IL
**מ:** Michael (דרך Cursor agent)
**ל:** זוהר (מחבר ה-spec ב-S2 Master Summary)
**נושא:** הבהרת spec ב-Sheet 7 שורה 6 לפני מימוש Pkg 2bc

---

## רקע קצר

אנחנו מממשים את **Pipeline 1 (S2 D-091) Pkg 2bc** — בעצם המשך של תיקוני ה-OFA לאחר Pkg 2a שכבר עבר G3 (close-through-level entry signal). Pkg 2bc אמור להוסיף 2 קונפיגים שמופיעים ב-Master Summary Sheet 7 שורה 6 אבל הסמנטיקה לא ברורה.

הקוד הנוכחי של S2 Reactive LONG (`backend/v9/systems/five_min/five_min_system.py`) ב-4 ברים:
```
bar 1: sellers dominate (bearish close + high volume)
bar 2: 90% volume drop vs bar 1   ← רק בר אחד נבדק כרגע
bar 3: buyers belly (bullish close) + POC_VOL rising
bar 4: confirmation (close above bar 3 high · אחרי Pkg 2a)
+ COT > AMT
```

ה-Pkg 2bc אמור לפי Sheet 7 שורה 6:

> חשיפת `belly_dominance_ratio` (default 1.5×) · `min_bars_for_drop` (default 3) · config-driven

---

## שאלה 1 · `belly_dominance_ratio = 1.5×`

הקוד היום קורא boolean מ-Footprint System (System 3):
```python
belly = self._get_belly_from_footprint()  # מחזיר True / False / None
```

ה-detector של ה-belly נמצא ב-`backend/v9/systems/footprint/detectors.py` שם הוא מחושב כ-flag בשם `belly_ratio_dominant` (boolean).

**Michael בחר interpretation:** "להעביר את ה-ratio מ-Footprint" — כלומר ה-threshold 1.5× שייך ל-`footprint/detectors.py` ולא ל-`five_min/`.

**שאלה לזוהר:**
1. האם ה-1.5× threshold הוא של buyers volume / sellers volume **על bar 3 spesifically** (ה-belly bar)?
2. או של ratio אחר (e.g. ask_volume / bid_volume אצל ה-POC במהלך אותו bar)?
3. האם זה אמור להחליף את ה-boolean signal שמגיע מ-Footprint, או להיות תוספת מעליו?
4. **האם ה-implementation שייך ל-S2 (`five_min/`) או ל-S3 (`footprint/`)** ?

---

## שאלה 2 · `min_bars_for_drop = 3`

זו השאלה החשובה — הקוד היום בודק בדיקה אחת מול bar 1 (3 שורות):
```python
b2_drop = b2_vol <= b1_vol * 0.10   # 90% drop · בר אחד
```

ה-spec רוצה `min_bars_for_drop = 3` — אבל מה זה אומר בפועל?

### 4 פירושים אפשריים שעלו אצלנו:

**A · הרחבת ה-pattern מ-4 ל-6 ברים**
מבנה חדש:
```
bar 1: sellers dominate (HIGH volume)
bar 2: drop (low volume)   ┐
bar 3: drop (low volume)   ├─ 3 ברי drop רצופים
bar 4: drop (low volume)   ┘
bar 5: buyers belly
bar 6: confirmation
```
**תוצאה:** pattern יותר ארוך · יותר נדיר · יותר איכותי.

**B · lookback לפני bar 1**
ה-pattern נשאר 4 ברים. אבל לפני שbar 1 (sellers spike) מתחיל, צריך לבדוק ש-3 הברים שלפניו (`bar -3, -2, -1`) הראו תנודה רגילה / נמוכה (לא drop גדול).
**תוצאה:** מסנן sellers spike שמתרחש אחרי גרירות · רוצים sellers דרמטיים אחרי תקופה שקטה.

**C · warm-up trivial**
פשוט: צריך לפחות 3 ברים ב-buffer לפני שה-detector מתחיל לעבוד. זה כבר קיים (`if len(bars_5m) < 4`).
**תוצאה:** שינוי קוסמטי בלבד · `min_bars_for_drop=3` רק עוצר טריוויאלי.

**D · ממוצע 3 ברים סביב bar 2**
במקום לבדוק רק `bar2_volume vs bar1_volume` · נבדוק את הממוצע של b1+b2+b3 לעומת b1 או לעומת ממוצע היסטורי.
**תוצאה:** smoothing מתימטי על ה-drop check.

### השאלות לזוהר:

1. **איזה משבע (A/B/C/D) זה הכוונה?** או משהו חמישי?
2. אם זה A (הרחבה ל-6 ברים) — האם ה-threshold (10% drop · default) זהה לכל 3 ברי ה-drop, או שונה?
3. אם זה B (lookback) — מה ה-threshold לתנודה הרגילה לפני bar 1?
4. אם זה D (ממוצע) — איזה ממוצע? simple average? rolling? משוקלל?
5. **האם min_bars_for_drop=3 משפיע על TimedoutAt? כלומר האם pattern יוצא הציר אם 3 ברי ה-drop לא קורים בתוך X זמן?**

---

## חזית CC

אנחנו רוצים שCC ימממש את Pkg 2bc בהקדם · 3 פירושים אפשריים אבל בלי תשובה מדויקת אנחנו מסתכנים בפיצול ההתנהגות מ-Master Summary. Michael ביקש להעלות את ה-ambiguity ולא לבחור מטעם הקוד.

**אם אין תשובה בהקדם** — Michael יחליט להתחיל עם **C (warm-up trivial)** כברירת מחדל בטוחה ולתעד את הdecision כ-D-091-followup. זה לא ייצור regression אבל גם לא ימצה את ה-spec.

תודה!
Michael Barg + Cursor agent

---

*אם נוח לך לענות ב-WhatsApp / מייל · מספיק לציין את ה-letter (A/B/C/D) ל-Q2 ו-yes/no ל-Q1 sub-parts. נמשיך מכאן.*
