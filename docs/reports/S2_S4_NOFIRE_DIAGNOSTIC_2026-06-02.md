# דוח אבחון מלא — למה S2 ו-S4 לא ירו (2026-06-02)

**מאת:** Cowork diagnostic (read-only) · **מצב:** SHADOW · **Backend בזמן הריצה:** כבוי (:8000)
**מתודולוגיה:** קריאה-בלבד מול `data/mems26_local.db` (`mode=ro`) + קריאת קוד-ייצור. אפס שינוי קוד/DB/שירות.
כל מספר בדוח **אומת בלתי-תלוי** ע"י Cowork (פקודה + פלט גולמי), לפי CLAUDE.md Rule 5.
ההמלצות הן **המלצות בלבד** — כל שינוי trading-logic הוא strategic-stop הממתין לאישור Michael.

---

## 0 · תקציר מנהלים

- **S4 (Woodies) — תקין, ירה 3×** (TLB, TT, HTLB ב-`v9_trades` firing_system=4). מתוך 9 התבניות:
  3 ירו, 3 זוהו אך לא נותבו (ZLR/VEGAS/GHOST — לפי תכנון "מנצח-אחד-לבר"), 3 לא חומשו כלל
  (GB100/FaMir/HFE — ה-CCI לא הגיע לאזורים הנדרשים). **אין באג ב-S4.**
- **S2 (Five-Min REACTIVE) — 0 ירי כל-הזמן.** שורש יחיד מאומת: גייט `b2_drop`
  (`DROP_THRESHOLD_PCT=0.10`) דורש קריסת נפח של 90% בין שני ברי 5-דקות — מצב שכמעט לא קיים
  בנתונים. הגייט `lookback_quiet` (שחשדנו בו תחילה) **מעולם לא הורץ** — ה-chain נחסם הרבה לפניו.
- **ממצא data-quality חדש:** נפחי חלון-הסגירה (15:15–16:15) מנופחים פי ~50–100 (980001…310000,
  round-thousand). ה-pass היחיד של `b2_drop` בכל ההיסטוריה (16:00→16:05) **נגרם מבר מנופח כזה** —
  כלומר הנתונים הפגומים *מייצרים* pass מזויף. **חובה לאמת את מקור הנפחים לפני כל כיול.**
- **3 השערות קודמות הופרכו** ב-verify-before-trust (פירוט §5).

---

## 1 · S4 Woodies — 9 תבניות

`SELECT MIN/MAX(cci_14)` היום: **min -257.55 · max +157.14** (CCI נע בכל הטווח, כולל קיצונים).
ספירת signals היום: TLB 19–21, HTLB 11, VEGAS 7, ZLR 3–4, GHOST 3, TT 1.
ניתוב trade = `v9_trades` firing_system=4 (לא כל signal → trade; הדיספצ'ר בוחר מנצח אחד/בר).

ארכיטקטורה (קוד): `detect_all_patterns` → אם trend=YELLOW נחסם הכל → `pattern_dispatcher.select_winner`
בוחר **מנצח אחד** (מעדיף משפחת CONT על REV, ובתוכה max R_t1) → `calculate_size`; אם `reject` →
`ready_to_route=False` → לא נכתב trade.

| Pattern | signals | סטטוס | נדרש (קוד) | live | למה לא ירה |
|---|---|---|---|---|---|
| **TLB** | 19–21 | ✅ fired | — | trade @15:06 | ירה |
| **HTLB** | 11 | ✅ fired | — | trade @06:46 | ירה |
| **TT** | 1 | ✅ fired | — | trade @07:46 | ירה |
| **ZLR** | 3–4 | armed | CONT, tier=high דורש aux_count≥2 | CCI 12.9–77.2, czi=CZI (חלש) | `calculate_size→reject` (aux חלש) / הפסיד בדיספצ'ר |
| **VEGAS** | 7 | armed | REV | CCI 127–157 | family-preference: REV הפסיד ל-CONT באותו bar_ts |
| **GHOST** | 3 | armed | REV (H&S על CCI) | זוהה | family-preference: הפסיד ל-CONT |
| **GB100** | 0 | blocked | חצייה טרייה ±100 (`prev≤100<current`) | CCI חיובי טיפס 116→157 ברצף, ללא חצייה טרייה | **cross gate** |
| **FaMir** | 0 | blocked | max_recent ∈ [170,210) (או mirror) | max חיובי 157.14<170; min -257.55<-210 | **near-threshold gate** (לא נכנס לחלון) |
| **HFE** | 0 | blocked | \|CCI\|≥200 ואז hook≥50 בחלון 2–12 ברים | קיצון התקיים, hook שלם לא נצפה | **hook gate** |

**מסקנת S4:** התנהגות תקינה. אין אף כשל; 6 ה"לא-ירו" מתחלקים ל-arming-לא-הושג (CCI לא בקיצון
הנדרש) ול-routing-לא-נבחר (מנצח-אחד-לבר). הערה: הבחנת armed/blocked ל-ZLR/VEGAS/GHOST נגזרה
מהקוד+counts כי ה-backend היה כבוי (אין מצב in-memory חי).

---

## 2 · S2 Five-Min REACTIVE — שורש 0-ירי

`v9_five_min_setups` = **0 rows all-time**. שרשרת REACTIVE LONG ב-
`backend/v9/systems/five_min/five_min_system.py` `_detect_reactive` (~469–575):
`MIN_BARS=7` → COT/AMT≠None → b1_sellers → **b2_drop (b2_vol ≤ b1_vol×0.10)** → b3_buyers →
belly → b4_confirm → b4_close>b3_high → cot>amt → **lookback_quiet (max(prev3) < b1_vol×0.6)** → belly_ratio.

### 2.1 · Funnel היסטורי (מאומת Cowork — כל ההיסטוריה)
מקור: `v9_bars_5min`, 1306 ברים distinct-ts, 2026-05-04 11:30 → 2026-06-02 16:35.
```
pairs: 1305 | b1 directional-down: 612 | of those b2_drop(≤0.10) pass: 1
ratio(b2/b1) median=0.944  p5=0.427  | pairs ≤0.10 (any direction): 5 / 1305
```
- **`b2_drop` עבר פעם אחת בלבד בכל ההיסטוריה** (עם תנאי b1-מוכר) — וזו האנומליה של היום (§3).
- קריסת נפח של 90% בין ברי 5-דקות עוקבים כמעט לא קיימת: p5 של היחס הוא 0.427.
- **`lookback_quiet` מעולם לא הורץ** — 0 חלונות הגיעו אליו (הם נחסמו ב-b2_drop קודם).

### 2.2 · 3 הוריאציות (A_VSA / B_RVOL / C_STRICT) = 0 by construction
התגית (`_variant`) מוקצית **רק בתוך** הבלוק שמתקיים אחרי שכל השרשרת עברה (כולל b2_drop).
מאחר שהשרשרת לא הושלמה אף פעם → אין direction → אין כתיבת setup → 3 הוריאציות 0. שורש משותף יחיד.

### 2.3 · הפרכת השערת lookback_quiet
חלון "מועמד" 2026-06-02 14:40 (raw DB): b1(14:40) v=6606, b2(14:45) v=**6155** → יחס **0.93**
(נדרש ≤0.10). החלון מת ב-**b2_drop**, מעולם לא הגיע ל-lookback_quiet. (פירוט הפרכה §5.)

---

## 3 · Data-quality — נפחי close מנופחים (ממצא חדש, מאומת)

נפחי RTH נורמליים ~4K–13K. בחלון 15:15–16:15 של 2026-06-02 (`is_synthetic=0`):
```
15:20  980001    15:25  960000    16:00  950000    15:55  880000
16:15  750024    15:45  710000    16:10  580000    15:15  540000
all-time MAX(volume)=980001 | count(volume≥500000 today)=8
```
**הוכחת ההשפעה (רגישות funnel, מאומת):** ה-pass היחיד של `b2_drop` היום הוא
**16:00 (v=950000, down) → 16:05 (v=40000)**, יחס 0.042 ≤ 0.10. כלומר ה-pass נוצר מנפח b1 מנופח,
לא מקריסת-נפח אמיתית. **הנתונים הפגומים מייצרים את ה-pass המזויף היחיד בכל ההיסטוריה.**

**רמז מקור (קוד):** `bar_aggregator_5min.py:155` חוסם תרומת tick ל-`min(raw_vol, 10000)` —
כלומר נתיב ה-tick_reversal **לא** יכול לייצר round-thousand של ~1M. הערכים האלה מגיעים, ככל הנראה,
מנתיב **ingest 5min ישיר מ-Sierra export** ולא מה-aggregator. **טרם אומת מול המקור** (§6).

---

## 4 · המלצות (המלצות בלבד — לא מומשו; כולן strategic-stop לאישור Michael)

1. **🛑 לאמת ולתקן את מקור הנפחים (15:15–16:15) — קודם לכל השאר.** הצלבה מול
   `~/SierraChart_Data/v9_export/` על ה-host: האם 980001/950000… אמיתיים מה-DLL או תוצר
   אגרגציה/תקרה/ingestion? אם סינתזה → CLAUDE.md §Source-of-Truth (לדווח, לא לסנתז). **אסור לכייל
   threshold לפני שמקור הנפחים נקי**, אחרת מכיילים על נתונים מורעלים.
2. **🛑 כיול `b2_drop` (`DROP_THRESHOLD_PCT=0.10`) — השורש האמיתי ל-0 ירי.** חוסם ~95% מהחלונות;
   על נתונים נקיים עבר 0–1 פעמים ב-29 ימים. אופציה מועדפת (כבר מתוכננת ב-`CC_PROMPT_S2_REACTIVE_CANFIRE`):
   להוציא את גייט בר-2 ל-callable מוזרק (default זהה-בייט) + 3 וריאציות **יחסיות** צופות
   (VSA / RVOL-TOD / Strict שמשוות ל-rolling-avg ולא לקריסה מוחלטת). flag-gated, observational, ללא נגיעה ב-live fire.
3. **🟡 `lookback_quiet` — תיקון נכון אך לא דחוף.** הגייט מובס-עצמית כש-b1 נמוך-נפח (משווה ל-b1
   במקום ל-rolling-avg / לא דורש b1 RVOL spike), אבל ה-chain לא מגיע אליו עד שמתקנים את b2_drop.
   לתעדף **אחרי** #2.
4. **🟢 observability:** להוסיף ל-build-status של S2 שדות per-variant (`armed`, `blocked_reason`,
   `last_eval_ts`, `fired_today`) — כדי שב-RTH הבא נראה את הגייט החוסם בזמן אמת בלי לכבות backend.
   (כבר מפורט ב-Phase 3 של `CC_PROMPT_S2_REACTIVE_CANFIRE`.)

---

## 5 · תיקונים (verify-before-trust — מה שנתפס)

1. **"S2 נתקע ב-lookback_quiet"** — **שגוי.** הסתמך על מספרים שגויים (b2=441, b3=970003) שאינם
   קיימים ב-DB. raw אמיתי: b2(14:45)=6155, יחס 0.93 → מת ב-b2_drop. lookback_quiet מעולם לא הורץ.
2. **"CCI נשאר 36–77 היום"** — **שגוי.** raw: min -257.55 / max +157.14.
3. **"footprint מושבת בנתונים ולכן חוסם את S2"** — לא רלוונטי לשורש: S2 נחסם ב-b2_drop, הרבה
   לפני גייטי ה-footprint.
4. **"b2_drop עבר 3× בהיסטוריה"** (סוכן) מול **"1× עם תנאי b1-מוכר, והוא artifact"** (אימות Cowork) —
   הפער מתודולוגי (תנאי directional / windows מול pairs); העובדה התקפה: על נתונים נקיים b2_drop
   כמעט לא עובר, וה-pass היחיד שכן — נגרם מנפח מנופח.

---

## 6 · NOT DONE / OPEN

- **אימות מקור הנפחים מול Sierra export — לא בוצע מ-Cowork.** הסיבה: `~/SierraChart_Data/v9_export/`
  **אינו נגיש מסביבת ה-sandbox** (לא mounted). דרוש: הרצה על ה-host (CC או Michael) להצליב את
  נפחי 15:15–16:15 מול ה-JSON export של ה-DLL. זו המלצה #1 ו-strategic-stop.
- **הבחנת armed/blocked חיה ל-S4** דורשת backend פעיל (endpoint `build/pattern-status`). הדוח הזה
  נגזר מ-DB+קוד בלבד.
- **כל ההמלצות (#1–#4) ממתינות לאישור Michael** — לא מומש שום שינוי.

---
*read-only · אפס שינוי · כל מספר מגובה ב-raw. פרומפט מימוש קיים: `docs/handoff/CC_PROMPT_S2_REACTIVE_CANFIRE_2026-06-02.md` (כולל §D2 — חוסם הנפחים).*
