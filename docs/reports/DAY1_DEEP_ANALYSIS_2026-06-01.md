ווד# Day 1 SHADOW — ניתוח מעמיק + הנחיות למחקר · 2026-06-01

**תאריך:** 2026-06-01 RTH (09:30-16:00 ET) · **מצב:** SHADOW Day 1
**נתונים:** 55 ברים 5-דק', 146 עסקאות (S2=0, S3=142, S4=4)

---

## 1 · תמונת יום המסחר (מהצילומים + DB)

```
09:30  Open 7587 · IB forming
10:00  IB Low 7576 · selling pressure
10:30  IB locked: H=7596.5 L=7576.0 Width=20.5pt (MEDIUM)
       Opening type: OPEN_AUCTION_IN (inside prior range)
       Day type classified: Normal (p=0.68)

10:30-12:00  Range-bound 7581-7602 · POC ~7590
             CCI: RED → GRAY → RED → GRAY (choppy)
             
12:00-12:30  Breakout above IB High (7596.5) → 7602
             CCI crosses ZL upward → enters BLUE territory

12:30-13:00  Extension to VAH (7606.75) → 7613
             CCI reaches +267 → strong BLUE
             ★ ZLR opportunities (DLL detected 8×)
             ★ HFE DOWN opportunities (DLL detected 17×)

13:00-13:30  Spike to 7632.75 (session high)
             Then pullback to 7607-7625 range
             
13:30-16:00  Trading above VAH · CCI BLUE with pullbacks
             Multiple ZLR/HFE setups flagged by DLL
```

**סיכום:** יום שהתחיל Normal rotation, הפך ל-**IB extension up** ואז ל-**trend day** (מחיר מעל VAH, CVD חיובי, CCI BLUE). המערכת לא זיהתה את המעבר.

---

## 2 · S1 Day Type — לא זיהה שינוי behavior

### מה קרה
- 10:30: סיווג **Normal** (p=0.68) עם IB=MEDIUM ו-opening=AUCTION_IN
- 10:30→16:00: הסיווג **נשאר Normal** למרות:
  - מחיר פרץ מעל IB High ב-12:00 (extension up)
  - מחיר פרץ מעל VAH (7606.75) ב-12:30
  - מחיר הגיע ל-7632 (36pt מעל IB Low, 1.75× IB range)
  - CCI הגיע ל-+267 (extreme momentum)

### מה היה צריך לקרות
לפי Dalton (Mind Over Markets) ו-D-091:
- **IB extension** (מחיר מעל IB High ב-2+ IB widths) → מעבר מ-Normal ל-**Normal Variation** (NV)
- מחיר 7632 = 36pt מעל IB Low, IB width=20.5 → extension = 1.75× IB → NV territory
- אם ההתנהגות ממשיכה → **Trend Normal** (TN)
- NV/TN מאפשרים Initiative patterns (שהיו חסומים ב-Normal Auth Table SKIP)

### שורש הבעיה
1. **S1 state machine at Stage B2** — מסווג פעם אחת ונעצר. אין re-evaluation mechanism שבודק IB extension / VA breakout ומעדכן.
2. **`_stage_b1`/`_stage_c2` voting** — ה-voting מבוסס על ברים בודדים, לא על behavior patterns (extension, breakout, return-to-VA).
3. **אין IB extension tracker** — הקוד לא עוקב אחרי כמה ה-IB "extended" מעבר ל-IB High/Low.

### הנחיות למחקר
- **מקור:** Dalton "Mind Over Markets" Chapter 5 (Day Type Development), D-091 §Coverage Matrix
- **שאלת מפתח:** מהם הקריטריונים **המדויקים** למעבר Normal → NV ו-NV → TN?
  - כמה IB widths extension = NV?
  - האם breakout מעל VAH = TN?
  - האם CVD alignment (directional volume) מאשר?
  - מתי (session_min) הכי סביר שהמעבר מתרחש?
- **בדוק:** `state_machine.py` `_rescore_from_behavior()` (line 535) — האם הוא אמור לעשות re-eval? האם הוא כלל רץ?
- **Risk:** שינוי day type mid-session משנה את Auth Table gating (Normal SKIP → NV FULL), אז זה משפיע ישירות על אילו patterns יורים.

---

## 3 · S2 Reactive — סף volume בלתי אפשרי

### מה קרה
- `DROP_THRESHOLD_PCT = 0.10` — דורש שבר 2 יהיה ≤ 10% מ-volume של בר 1
- מתוך 54 זוגות ברים היום: **אפס** עברו את הסף
- הכי קרוב: ratio=0.12 (88% ירידה — עדיין לא 90%)

### ניתוח volume distribution ב-MES 5-דק'
```
Min ratio today:  0.12 (88% drop — almost but fails)
Pairs ≤ 10%:      0/54  (threshold = 0.10)
Pairs ≤ 30%:      3/54
Pairs ≤ 50%:     11/54
Pairs ≤ 70%:     21/54
```

### מה היה צריך לקרות (עם סף 50%)
7 Reactive setups היו מתקבלים:
```
14:20  REACTIVE_SHORT  vol_drop=0.49  @POC (7590)
14:45  REACTIVE_SHORT  vol_drop=0.30  @IB_H (7596.5)  ★ + ZLR
15:15  REACTIVE_SHORT  vol_drop=0.35  @POC
15:30  REACTIVE_LONG   vol_drop=0.46  breakout above IB
15:45  REACTIVE_SHORT  vol_drop=0.40  @IB_H  ★ + HFE
16:45  REACTIVE_LONG   vol_drop=0.42  breakout to 7625+
17:45  REACTIVE_LONG   vol_drop=0.40  continuation at 7625
```

### הנחיות למחקר
- **מקור:** Auth Table V1 §T1 Reactive definition, Master Sheet 7 (OFA configuration)
- **שאלת מפתח:** מהו ה-volume drop threshold הנכון ל-MES 5-דק'?
  - **D-091 אומר:** `bar 2 vol ≤ 10% of bar 1 vol (90% drop)` — אבל זה מנוסח על daily bars?
  - **Bulkowski:** volume drop patterns מוגדרים בדרך כלל כ-50-60% (לא 90%)
  - **MES reality:** average bar volume 5-דק' ~5000-50000 contracts. ירידה של 90% = בר של 500 contracts — כמעט ריק. זה לא קורה ב-RTH.
- **בדוק:** 
  1. מה ה-distribution של volume ratios ב-MES 5-דק' על 20 ימי מסחר (DB history)
  2. האם 50% drop (0.50) נותן ~5-10 setups ליום (סביר) או 50+ (רועש)
  3. האם הסף צריך להיות **ATR-relative** (כמו שאר הספים)?
- **Risk:** סף נמוך מדי = יותר מדי false positives. סף גבוה מדי (0.10) = אפס fires.

---

## 4 · S4 Woodies — DLL זיהה, המערכת לא ירתה

### מה קרה
**DLL (Sierra) זיהה 25 הזדמנויות** שהמערכת פספסה:
- **8× ZLR** — CCI was above +100, pulled back toward ZL, bouncing
- **17× HFE** — Hook from extreme, CCI reversing from +200+ zone

### שורשי הבעיה (3 שכבות)
1. **DLL flags לא הועברו** — `last_flat` dict חסר `zlr_detected`/`hfe_detected`
   - **תוקן:** commit `730f913`

2. **Python detector שונה מ-DLL** — Python ZLR דורש `current > prev` (bounce), DLL לא
   - **תוקן:** commit `58d6538` (DLL trusted as primary)

3. **Stage A1 blocks in GRAY** — HFE detected by DLL in GRAY trend, but P-W5 blocks ALL 9
   - **11 ברים GRAY** מתוך 50 → 55 דקות שכל 9 התבניות חסומות
   - HFE הוא **REV pattern** — לפי D-092 §4 P-W5 חוסם REV ב-GRAY
   - **אבל:** HFE הוא community pattern (לא Wood original) — ייתכן שהכלל צריך להיות גמיש יותר

### ZLR timeline (8 missed fires)
```
14:45  CCI=-98   trend=RED   ★ZLR DOWN — CCI pulling back from -137 extreme
14:50  CCI=-106  trend=RED   ★ZLR DOWN — continuation
15:55  CCI=55    trend=BLUE  ★ZLR UP   — CCI bouncing from ZL after +267 extreme
16:25  CCI=63    trend=BLUE  ★ZLR UP   — breakout bar, CCI above ZL
16:30  CCI=64    trend=BLUE  ★ZLR UP   — continuation
16:35  CCI=64    trend=BLUE  ★ZLR UP   — continuation
17:15  CCI=76    trend=BLUE  ★ZLR UP   — new ZLR after pullback from +230
17:20  CCI=176   trend=BLUE  ★ZLR UP   — strong bounce confirmed
```

### HFE timeline (17 missed fires)
```
15:35-15:50  CCI 172→107→80→49  trend=BLUE  ★HFE DOWN (4 bars)
             Price at 7599-7606 (near VAH) — reversal from +267 extreme
16:00-16:10  CCI 30→-13→-57     trend=GRAY  ★HFE DOWN (3 bars)
             → Blocked by GRAY trend (P-W5)
17:00-17:10  CCI 42→40→37       trend=BLUE  ★HFE DOWN (3 bars)
             Price at 7624-7626 — reversal after spike to 7632
17:25-17:30  CCI 142→133        trend=BLUE  ★HFE DOWN (2 bars)
17:45-18:05  CCI 156→117→91→79→73 trend=BLUE ★HFE DOWN (5 bars)
             Price at 7624-7628 — extended reversal zone
```

### הנחיות למחקר
- **מקור:** D-092 §ZLR (Section 5 A1), D-092 §HFE (Section 5 B5), P-W5 (YELLOW/GRAY gate)
- **שאלות מפתח:**
  1. **ZLR:** האם DLL logic או Python logic נכון? DLL מזהה ב-pullback, Python דורש bounce. מה Woodies methodology אומר? (Gannon, Rensink, Liran)
  2. **HFE in GRAY:** D-092 says "BLOCK ALL 9 in GRAY" but HFE is MEMS26-internal (not Wood doctrine). האם HFE צריך exemption מ-P-W5? Wood WSI ("Wait, Sit, Inspect") אומר לחכות — אבל HFE הוא by definition reversal from extreme, שקורה ב-transition zones.
  3. **GRAY duration:** 55 דקות GRAY מתוך 4.5 שעות RTH = 20% של היום. האם הסף ל-trend persistence (6 bars) נכון, או צריך 4-5?
- **Risk:** 
  - הרחבת P-W5 (HFE in GRAY) → יותר fires אבל ב-low-conviction zone
  - שינוי ZLR logic → alignment עם DLL אבל חוסר bounce = earlier entry (more risk)

---

## 5 · S2 Initiative — Auth Table SKIP ליום Normal

### מה קרה
Initiative LONG/SHORT חסומים ע"י Auth Table:
```
INITIATIVE_LONG  × Normal = SKIP
INITIATIVE_SHORT × Normal = SKIP
```

### מה היה צריך לקרות
- מחיר עלה 7576 → 7632 (56pt) ביום שסווג Normal
- Bar at 16:40: range=20.75pt, close=7623.5 (bull) — initiative breakout bar
- **אם Day Type היה NV/TN** → Initiative היה authorized ← תלוי בתיקון S1

### הנחיות למחקר
- **מקור:** D-091 §Coverage Matrix, Auth Table V1
- **שאלה:** האם Initiative צריך לירות גם ב-Normal אם יש IB extension + VA breakout? או שזה תמיד דורש NV/TN classification?
- **Risk:** Initiative on Normal = more fires, potentially lower quality

---

## 6 · S2 Chart Patterns (H&S, Double, Flag)

### מה קרה
- **H&S:** 7 swing highs, 5 lows — **אבל** אין triplet סימטרי. ✅ לגיטימי
- **Double Top:** peaks at 7632/7629 (0% diff), neckline=7599 — price ABOVE neckline by 25pt. ✅ לגיטימי (no breakout SHORT)
- **Bull Flag:** longest bull run = 4 bars (need 5). ✅ לגיטימי (bar at 16:40 range=20.75 broke the run)
- **Bear Flag:** no 5-bar bearish pole. ✅ לגיטימי

### הנחיות למחקר
- אלה **לא באגים** — המבנים לא התגבשו היום
- **שאלה אופציונלית:** האם ה-swing detection algorithm (5-bar lookback) מתאים ל-MES 5-דק'? יום trend עם ברים גדולים יוצר swing points רחוקים שלא יוצרים H&S קלאסי.

---

## 7 · סיכום: מה עובד, מה שבור, מה צריך החלטה

### ✅ עובד
| רכיב | ראיה |
|-------|------|
| S3 Footprint | 142 trades — pipeline שלם |
| S4 HTLB | 4 trades — detection + fire + trade management |
| S4 DLL flags | ZLR/HFE flags pass-through (תוקן היום) |
| Day Type classification | Normal p=0.68 (correct for IB data) |
| IB from Sierra | H=7596.5 L=7576.0 (matches Sierra) |
| POC/VAH/VAL | Live from tpo.json (matches Sierra) |
| Live price | Bid/ask midpoint (accurate) |
| Woodies CCI | Live from chart 12 (matches Sierra) |
| Build Status | Per-pattern armed/blocked with live data |

### ❌ שבור (באגים מאומתים)
| # | באג | השפעה | תוקן? |
|---|-----|-------|-------|
| 1 | DROP_THRESHOLD=0.10 (90%) | Reactive NEVER fires | ❌ **צריך אישור** |
| 2 | DLL flags not passed | ZLR/HFE missed | ✅ תוקן (730f913) |
| 3 | DLL detection not trusted | Python disagrees with DLL | ✅ תוקן (58d6538) |

### ❓ צריך החלטת Michael (research first)
| # | נושא | מחקר נדרש | risk |
|---|------|----------|------|
| A | DROP_THRESHOLD: 0.10 → ? | Volume distribution on 20 days | Wrong threshold = too many/few fires |
| B | S1 re-classification (Normal→NV/TN) | Dalton IB extension rules | Changes Auth Table gating mid-day |
| C | P-W5: HFE in GRAY? | Wood WSI vs HFE community pattern | Low-conviction fires |
| D | S3 mute until S1+S2+S4 work | Michael request | Lost data collection |

---

## 8 · לו"ז מומלץ

1. **מחקר (1-2 שעות):** 
   - Volume distribution analysis → קבע DROP_THRESHOLD
   - Dalton IB extension → קריטריונים ל-S1 re-classification
   - P-W5 HFE exemption → כן/לא

2. **אישור Michael:** על A/B/C/D

3. **מימוש (אחרי אישור):**
   - A: שורה אחת (`five_min_system.py:30`)
   - B: הוספת `_check_ib_extension()` ל-state machine (mid-complexity)
   - C: exemption list ב-`woodies_system.py` RTH gate
   - D: flag `S3_MUTE=1` ב-plist

---

*הדוח פתוח ב-TextEdit. אפס שינויים בוצעו — research + אישור לפני מימוש.*
