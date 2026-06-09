# Pattern Firing — EOD מאוחד · 2026-06-05

> **⚠ אזהרת-זמן (ממצא I-9, מאומת):** הסוכן רץ אוטומטית ב-**09:25 CT** (17:25 ישראל),
> לא אחרי סגירת RTH (15:00 CT). RTH נפתח 08:30 CT — כך שהדוח מכסה רק את ה**שעה הראשונה**
> (08:30–09:25 CT, 11 ברי-5דק'), לא יום-מסחר מלא. ה-cron עדיין מכוון ל-TZ הלא-נכון
> (ראה I-9). **כל המספרים למטה הם חלון-בוקר, לא יום שלם.** יש להריץ שוב אחרי 23:00 ישראל
> ליום מלא.

**מקור:** API חי דרך Chrome → `http://localhost:8000`. קריאה/תיעוד בלבד.
`/api/v9/trades/recent` (max limit=100) · `/api/v9/chart/bars5min` · `/woodies|footprint|five_min|gateway/current`.
**Sierra cross-checks** (CCI/study/OHLC) מסומנים ל-CC — לא אומתו כאן (read-only, אין גישת-export).

---

## טבלת EOD מאוחדת (חלון 08:30–09:25 CT)

| מערכת | תבנית | נדרכה # | נורתה # | לא-נדרכה # (סיבות) | לא-נורתה # (פירוק סיבות-דחייה) | תחזית-נגד: W/L, ΣR |
|-------|-------|---------|---------|--------------------|-------------------------------|---------------------|
| **S4 woodies** | HFE | **1** | 0 | 0 | **1 — A5 `calculate_size=reject`** (sizing: HFE LONG, CCI=−192.9, trend=RED, group=REVERSAL → reversal-long לתוך RED שמרני) | **0W/1L, ΣR = −1.0R** (ראה §תחזית-נגד; חוסך הפסד) |
| S4 woodies | ZLR | 0 | 0 | 1 — לא ב-`active_patterns` (signal=HFE בלבד) | — | — |
| S4 woodies | TLB | 0 | 0 | 1 — לא ב-`active_patterns` | — | — |
| S4 woodies | TT | 0 | 0 | 1 — לא ב-`active_patterns` | — | — |
| S4 woodies | GB100 | 0 | 0 | 1 — לא ב-`active_patterns` | — | — |
| S4 woodies | HTLB | 0 | 0 | 1 — לא ב-`active_patterns` | — | — |
| S4 woodies | FAMIR | 0 | 0 | 1 — לא ב-`active_patterns` | — | — |
| **S3 footprint** | ABSORPTION | 0 | 0 | 1 — **0 ברי-footprint עובדו היום** (buffer=0, כל flow=null) | — | — (לא יכלה לדרוך) |
| S3 footprint | STACKED_IMBALANCE | 0 | 0 | 1 — אותו דבר (אין ברי-footprint) | — | — |
| S3 footprint | SWEEP_RETURN | 0 | 0 | 1 — אותו דבר | — | — |
| S3 footprint | EXHAUSTION | 0 | 0 | 1 — אותו דבר | — | — |
| **S2 five_min** | REACTIVE_LONG | 0 | 0 | — (detector רץ על 166 ברים) | 1 — `patterns_detected=0`, אין match בחלון | — |
| S2 five_min | REACTIVE_SHORT | 0 | 0 | — | 1 — `patterns_detected=0` | — |
| S2 five_min | INITIATIVE_LONG | 0 | 0 | — | 1 — `patterns_detected=0` | — |
| S2 five_min | INITIATIVE_SHORT | 0 | 0 | — | 1 — `patterns_detected=0` | — |
| S2 five_min | INV_HNS | 0 | 0 | — | 1 — `patterns_detected=0` | — |
| S2 five_min | HNS_TOP | 0 | 0 | — | 1 — `patterns_detected=0` | — |
| S2 five_min | DOUBLE_BOTTOM_EE | 0 | 0 | — | 1 — `patterns_detected=0` | — |
| S2 five_min | DOUBLE_TOP_AA | 0 | 0 | — | 1 — `patterns_detected=0` | — |
| S2 five_min | BULL_FLAG | 0 | 0 | — | 1 — `patterns_detected=0` | — |
| S2 five_min | BEAR_FLAG | 0 | 0 | — | 1 — `patterns_detected=0` | — |

**סך-הכל בחלון:** נדרכה=1 (S4 HFE) · נורתה=0 · trades_today=0 · daily_pnl=0.

---

## תחזית-נגד (counterfactual) — S4 HFE LONG @ 09:12 CT

**ספק-התבנית (מ-`active_patterns`):** entry=**7519.25**, stop=**7516.75**, T1=**7522.25**, T2=**7525.25**.
R = entry−stop = **2.5 נק'** · T1 = +3.0 = **1.2R** · T2 = +6.0 = **2.4R** · direction=LONG (limit-entry מתחת למחיר ~7525 בזמן-האיתות).

**שחזור הברים שאחרי האיתות** (5דק', מ-`bars5min`, ישראל TZ):

| בר (IL / CT) | O | H | L | C | אירוע מול ההגדרה |
|--------------|---|---|---|---|------------------|
| 17:15 / 09:15 | 7525 | 7533.5 | 7524.75 | 7533.25 | low 7524.75 > entry 7519.25 → **לא מולא** |
| 17:20 / 09:20 | 7533.25 | 7533.25 | 7521 | 7521.7 | low 7521 > entry → **לא מולא** |
| 17:25 / 09:25 | — | 7522 | **7516** | — | low 7516 ≤ entry 7519.25 → **מולא** ; low 7516 < stop 7516.75 → **STOP HIT**; high 7522 < T1 7522.25 → T1 לא נגע |

**תוצאה:** אם ההגדרה נשארה חיה ~13 דק' עד בר 17:25 — הכניסה מולאה ב-7519.25 ונעצרה
באותו בר ב-7516.75 → **−1.0R** (T1 פספס ב-0.25 נק'). אם חל **fill-timeout** קצר יותר
(ההגדרה פגה אחרי 2–3 ברים בלי מילוי) → **0R, אין-עסקה**. בשני התרחישים — **חסימת A5 לא
עלתה על עסקה רווחית**; בתרחיש המילוי היא **חסכה הפסד של 1R**.

ΣR-נגד פר-תבנית בחלון: **HFE = −1.0R (0W/1L)**. כל שאר התבניות לא-נדרכו → אין תחזית-נגד.

**הסתייגויות (חובה):**
- בר 17:25 (09:25 CT) הוא **הבר-החי המתהווה** ברגע-הריצה — low/high עדיין יכולים לזוז.
  התוצאה −1R **provisional**.
- חלון של **3 ברים בלבד** אחרי האיתות (כי הסוכן רץ 5.5ש' מוקדם) — מדגם n=1, לא מובהק.
- ordering תוך-ברי בבר-המילוי לא חד-משמעי, אבל התוצאה (entry מולא · stop נגע · T1 לא) זהה
  בכל סדר כי high 7522 < T1 7522.25.
- **Sierra SoT:** CCI=−192.9 / TCCI=−99.7 / OHLC של בר-ה-HFE טרם הוצלבו מול `~/SierraChart_Data/v9_export/` → **CC**.

---

## לקחים

**תבניות שנדרכו-הרבה ולא-ירו (ולמה):** רק **S4 HFE** נדרכה (פעם אחת) ולא ירתה — נחסמה
ב-**A5 sizing** כי זו reversal-long לתוך trend=RED עם CCI מתוח (−192.9). הערת-המנוע:
`"HFE LONG size=reject: CCI=-192.9, trend=RED, conf=0.70, group=REVERSAL"`. התחזית-נגד
מראה שהחסימה הזו **מוצדקת** (חסכה ≈1R, או לכל הפחות ניטרלית) — לא שמרנית-מדי בחלון הזה.

**תבניות שלא-נדרכו (ולמה):**
- **S3 (כל ה-4): אנומליה אמיתית** — `bars_processed_today=0` גם ב-09:24 CT (≈54 דק' לתוך
  RTH), המערכת `running+hydrated` אבל אפס ברי-footprint נכנסו. שום תבנית-S3 לא יכולה לדרוך.
  זו **לא דחייה-מוצדקת אלא תקלת-הזנה** (ראה I-10 חדש ב-Issues Register).
- **S2 (כל ה-10):** ה-detector רץ חי על 166 ברים אבל `patterns_detected=0` — **לגיטימי**,
  פשוט לא היה setup בחלון-הבוקר. אין כאן חסם, רק היעדר-תבנית.
- **S4 (6 התבניות האחרות):** לא ב-`active_patterns` — המנוע בחר HFE כאיתות-היחיד. לגיטימי.

**דחיות מוצדקות מול שמרניות-מדי:** הדחייה היחידה (A5 על HFE) נראית **מוצדקת** לפי
התחזית-נגד. אין ראיה לשמרנות-יתר בחלון הזה. **אבל** — A4 דיווח `context degraded`
(day_type/tpo/killzone/layer0 כולם `missing`), כך שה-sizing פעל **בלי קונטקסט-יום מלא**;
ייתכן שה-reject "צדק במקרה". יש לאמת מול I-1 (day_type=UNKNOWN) לפני שמסיקים שה-A5 מכויל נכון.

---

## NOT-DONE / פערים
- **חלון חלקי בלבד** (שעה ראשונה) עקב ריצה מוקדמת — I-9. צריך ריצה חוזרת אחרי-סגירה ליום מלא.
- **A5 `details{}` ריק** — סיבת-ה-reject המדויקת (account equity / risk-per-trade / contract)
  לא נחשפת ב-endpoint; ההסבר נלקח מ-`last_reasoning_notes`. צריך DB/log read ע"י CC.
- **S2 FHB state** לא נחשף ב-`/five_min/current` — `armed` פר-תבנית נמדד דרך detector-running
  כ-proxy, לא דרך ACCUMULATING/EARLY כפי שמבקש §2.
- **S3 zero-bars שורש** לא אובחן (read-only) — נתיב footprint export→bridge→DB ל-CC.
- **Sierra cross-checks** (CCI/TCCI/OHLC) טרם הוצלבו — read-only, אין גישת-export. ל-CC.
