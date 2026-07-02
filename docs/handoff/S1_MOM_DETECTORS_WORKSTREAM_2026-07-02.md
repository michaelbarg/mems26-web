# S1 — MoM Detectors Workstream (סדר מאושר-Michael, 2026-07-02 ~18:40)

_נגזר מ: `docs/spec_authority/MOM_SUPPLEMENT_DETECTORS_2026-07-02.md` (המסמך של מיכאל) + `MOM_GAP_ANALYSIS_2026-07-02.md` (מיפוי קיים/חסר). מצטרף ל-workstream הרה-כיול של S1 (memory: `project_s1_daytype_recalibration` — inputs-first). כל פריט: research→spec→flag-gated build→SHADOW→פסק-Michael. **לא חלק מחבילת-הערב** (שם רק פריט-13 P/b)._

## הסדר המאושר
1. **✅ P/b-filter** — בחבילת-CC (פריט-13). הזול: הנתון קיים.
2. **Double-Print Transition Detector** — "הגלאי שחסר": 4 קטגוריות-מעבר (ללא / 1TF→2TF / 2TF→1TF / 1TF→הפוך=Neutral) על תקופות-30-דק' (מקבץ 6×5m). double-prints מעבר לקיצון נגד ה-1TF = אישור-מעבר. **משרת ישירות:** (א) reclass של S1 (המקרה החי מ-07-02: שבירת-IB-L — נקירה-בלי-אישור נשארה Normal, בצדק; הגלאי הופך את זה למכני) (ב) invalidation ל-trailing/C3 ביום-Trend (טבלה-9). Inputs: ברי-woodies בלבד — קיימים.
3. **Value-Area Rule** — פתיחה מחוץ-ל-VA-אתמול + acceptance (double-prints) בפנים ⇒ (א) חסם-fade על הקצה הקרוב (ב) target = הקצה הנגדי. 3 המסננים מהספר: מרחק-מה-value · רוחב-VA (קיים: va_width) · כיוון-auction-ארוך. Inputs קיימים (prior_vah/val/open_location) — חסר רק גלאי-ה-acceptance (double-prints) — משותף עם פריט-2.
4. **NONCONVICTION (הסוג השמיני)** — override חוסם-הכל: Open-Auction-בתוך-value + אפס-tails + אפס-RE עד שעה X. נבנה בתוך הרה-כיול של S1 (questionnaire) — משנה את מרחב-הסוגים ⇒ פסק-ספק של Michael לפני קוד. + **calendar/news flag** (input חיצוני — feed לוח-שנה; גם ימי-ערב-נתון).

## אחר-כך (שכבות B/C מה-gap-analysis, לפי תור)
Time-at-Extreme warning → דירוג-איכות-קיצון (TAIL_STRONG/TIME_WEAK — צריכה ב-stop/target trust) → One-TF-integrity בוליאני→יציאת-C3 → TPO-count מעל/מתחת-POC (+נטרול-בטרנד) → Spike-memory → תגיות-EOD (3-1/2I-1R/NeuExt-close — **לאמת על MES לפני משקולות**, נתוני-הספר=אג"ח 86-87) → HVN/LVN-proxy ליעדים → gap-timer שעה-ראשונה.

## חוקי-ביטול (טבלה-9) — נכנסים עם הגלאים התומכים שלהם
מחיקת-gap כסטופ · double-prints-בתוך-spike · DD-singles-מתמלאים=יציאה · balance-rock (כשל-פריצה→דריכה-נגדית).

**Contract:** כרגיל — `CC_HANDOFF_CONTRACT.md`, אנטי-טאוטולוגי, פלט גולמי, NOT-DONE.
