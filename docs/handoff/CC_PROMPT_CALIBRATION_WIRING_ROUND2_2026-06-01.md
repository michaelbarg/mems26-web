# CC PROMPT — Calibration Wiring · סבב-2 (S3 + 3 דגלי S1 + Part B)

**תאריך:** 2026-06-01 · **מקור:** Cowork (Michael אישר) · **מצב:** SHADOW
**רקע:** אימות Rule 5 (`f3caa89`) + הצלבת Cowork קבעו שסבב-1 היה **מנופח** — רק `S2_ATR_RELATIVE` מחווט באמת. סבב זה משלים את היתר **לפני איסוף SHADOW** (אחרת S3+S1 נאספים על לוגיקה ישנה → כיול מזוהם).
**משמעת:** diagnose-first לכל דגל · **wiring + observability בלבד — אסור לשנות ספים/priors/k-values** · מאחורי הדגל הקיים (flag-OFF = golden identical) · regression לכל דגל · Rule 5 (פלט גולמי).

> **עיקרון מנחה (חובה):** דגל נחשב "מחווט" רק אם הענף **באמת מתנהג אחרת** כשהוא ON — לא מספיק שה-helper *נקרא*. תפסנו בסבב-1 ש-`get_min_level_vol` נקרא אך עם `median_level_vol=0` → תמיד החזיר את הקבוע. לכל דגל: הוכח שינוי-התנהגות עם פלט.

---

## משימה A · S3_RELATIVE (מת — לתקן)
**דיאגנוזה מאומתת:** `footprint_system.py:369` קורא `detect_stacked_imbalance(footprint_levels, bar)` **בלי `median_level_vol`** → default 0.0 → `get_min_level_vol` מחזיר תמיד 10. בנוסף `detectors.py::get_range_ticks` מוגדר אך לא נקרא (analyze_context משתמש ב-range_ticks=15 קבוע).
**תקן:**
1. חשב `median_level_vol` מ-`footprint_levels` והעבר ל-`detect_stacked_imbalance` (ולכל גלאי שצריך אותו).
2. חבר את `get_range_ticks` לנתיב הזיהוי (analyze_context) כשהדגל ON.
**הוכח:** flag ON + median>0 → `_min_vol = 0.3×median` (≠10); flag OFF → 10 (golden). הדבק טסט + פלט.

## משימה B · 3 דגלי S1 (מתים — diagnose-first ואז לתקן)
לכל דגל: (a) **אבחן את אתר-המוות המדויק** (grep + הקריאה שלא מעבירה קלט / לא מתייעצת בדגל), (b) תקן wiring, (c) הוכח שינוי-התנהגות flag-ON מול golden flag-OFF.
1. **S1_IB_WIDTH_ATR** (`detector.py:65`) — האם `atr_daily` באמת מועבר ל-`classify_ib_width_atr` בנתיב החי? אם לא — להעביר. הוכח: ON + atr → EXTREME/ATR-tiers; OFF → 15/25pt.
2. **S1_CVD_OPENING** (`detector.py:255`) — האם ה-CVD label **מחליף את הסיווג החי** מקצה-לקצה (→matrix→day_type), או רק נכתב ל-`reasoning_notes` (כפי שדווח קודם)? אם רק reasoning — לחבר להחלטה. הוכח: ON + footprint → label מ-CVD; OFF → price-based.
3. **S1_DAYTYPE_STAGING** (`detector.py:78-114`) — האם ה-staging (cap 60% לפני 60min + C-period re-eval) באמת מופעל בנתיב החי? הוכח: ON → conf מוגבל לפני IB lock; OFF → ללא cap.

## משימה C · Part B — scaffolding לכיול (observability)
ודא ש-SHADOW **רושם את המטריקות שעליהן מכיילים** (ב-`cross_context`/quality או טבלת audit קיימת — לא ליצור כפילות):
- S2: range של B1 ÷ ATR5m (ratio), גם כשלא ירה.
- S1: `PE_30`, `net_CVD/total`, `range_exp`, label שנבחר (CVD מול price).
- S1 day_type: החלטת כל checkpoint (30/60/90) + confidence.
- S3: strength + aux_count + confluence + `median_level_vol` בפועל.
**אל תרשום** סודות/מחירים מיותרים; רק מטריקות-כיול. שדה חדש = מתועד + נבדק.

---

## פלט מצופה
`docs/reports/CALIBRATION_WIRING_ROUND2_2026-06-01.md` — **טבלה לכל דגל:** flag → אתר-המוות (grep) → diff התיקון → **טסט flag-ON שמוכיח שינוי-התנהגות (פלט גולמי)** → golden flag-OFF identical. + רשימת מטריקות Part B והיכן נרשמות. commits נפרדים. עדכון `STATUS_BOARD.md` (Rule 5).

**שערים:** wiring+observability בלבד — **אפס שינוי priors/ספים/k** (strategic-stop אם נדרש). flag-OFF חייב להישאר זהה (golden). דגל "מחווט" = הוכחת שינוי-התנהגות, לא רק קריאה. אל תיגע ב-order/risk/sizing. תאם עם פרומפט הרציפות (`BAR_CONTINUITY`) — שניהם נוגעים ב-footprint/detection.
