# S1 — טבלאות-זיהוי (as-built מהקוד) · סוג-יום + סוג-פתיחה
*`opening_detector_v2.py` + `daytype_classifier.py`, 2026-06-20. עמודת "✏️ נכון?" למילוי שלך.*

## א׳ · זיהוי סוג-פתיחה (5 סוגים — לפי סדר, ראשון שמתאים)
*חלון = 6 הברים הראשונים · tol = buf = 1 טיק · crossings = מס׳ היפוכי-סימן של (close−open).*

| # | סוג | הטריגר בקוד | ביטחון | ✏️ נכון? |
|---|---|---|---|---|
| 1 | OPEN_DRIVE | כל ה-lows ≥ open (לא חוזר דרך הפתיחה) + closes מונוטוני + סוגר מעבר ל-open±buf | 0.85 | |
| 2 | OPEN_TEST_DRIVE | poke 2–6 טיק מעבר ל-PDH/PDL/VAH/VAL שנכשל (סוגר בחזרה) + \|תנועה\| > buf | 0.75 | |
| 3 | OPEN_REJECTION_REVERSE | תנועה ראשונית + היפוך מלא דרך open + \|last\| ≥ 0.5×\|init\| + crossings ≤ 1 | 0.5–0.6 | |
| 4 | OPEN_AUCTION_OUT | אחרת + open מחוץ ל-PDH/PDL | 0.5 | |
| 5 | OPEN_AUCTION_IN | אחרת (רוטציה; open בתוך VA/טווח אתמול) | 0.4 | |

**open_location:** in_value (בתוך VA אתמול) · out_value_in_range (בתוך PDH–PDL) · out_of_range (מעבר ל-PDH/PDL).

## ב׳ · זיהוי סוג-יום (7 סוגים — דיסקרימינטור ראשי = sides)

| # | תנאי (לפי הסדר, ראשון שמתאים) | → סוג | ✏️ נכון? |
|---|---|---|---|
| 0 | `returned_through_open` | דגל-זמני opening_invalidated (לא טרמינלי) | |
| 1 | `n_bars < 6` (30 דק׳) | FORMING | |
| 2 | sides=2 · `rib < 1.3` | Neutral · FORMING | |
| 3 | sides=2 · `close_pos ≥0.85 / ≤0.15` | Neutral_Extreme | |
| 4 | sides=2 · `close_pos 0.33–0.67` | Neutral_Center | |
| 5 | sides=1 · `dd_second_dist=True` | Trend_DD | |
| 6 | sides=1 · open∈{Drive,TestDrive} + one_tf + `rib≥2.5` + CVD-כיווני | Trend_Normal | |
| 7 | sides=1 · `1.3 ≤ rib < 2.5` ⚠️(צ"ל <2.0) | Variation | |
| 8 | sides=0 · `vol_ratio ≤ 0.5` + `rib ≤ 1.5` | Nontrend | |
| 9 | sides=0 · `IB ≤ 7 נק'` + `rib ≤ 1.15` | Nontrend | |
| 10 | sides=0 · `rib ≤ 1.3` + ווליום-רגיל + IB-לא-צר | Normal | |
| 11 | אחרת | FORMING | |

**מדידת הקלטים:** sides = קצוות-IB עם ≥2 ברים רצופים שסוגרים ≥0.3×IB מעבר · rib = טווח÷IB · one_tf = תקופות 30-דק׳ HL/ללא-LL · CVD-כיווני = cvd_pos ≥0.75/≤0.25 · vol_ratio = ווליום-סשן ÷ חציון-ימים · IB = 60 הדק׳ הראשונות (מוחלט).

## ה-flaws המהותיים (שאני רואה בטבלאות)
1. **OPEN_DRIVE כמעט בלתי-נגיש** — דורש שאף בר מ-6 לא יחזור דרך הפתיחה. בסריקה **0 ימים** יצאו Drive → הפתיחה כמעט תמיד Auction → **Trend_Normal כמעט בלתי-נגיש**. זה כנראה ה-flaw המרכזי.
2. **Trend_DD נדלק-יתר** (proxy של קפיצת-POC).
3. **Variation** חוסם-עליון 2.5 במקום 2.0.
4. **vol_ratio + IB מזוהמים** לימים פרה-גלגול → סיווג garbage-in.
