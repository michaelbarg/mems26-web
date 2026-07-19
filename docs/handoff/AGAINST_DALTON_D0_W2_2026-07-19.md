# W2 · against-Dalton האמיתי לפי מפת-D0

**תאריך:** 2026-07-19 · cursor-agent · API read-only (`/trades` + `/chart/replay` + `/classify_replay`)

## למה T1 הישן ניפח
`PATTERN_INTEL_NUMBERS` ספר CONT בצד-VA "הלא-נכון" כ-against-Dalton סטטי.  
במפת-D0: יום שסווג `Normal_Variation` = **Variation** → CONT **עם-הרחבת-IB מותר**, גם מתחת/מעל POC.  
דוגמה: 07-15 #379 GB100 SHORT near_val — T1=AGAINST, D0=**WITH** (exp=DOWN).

## שיטת-D0 (כנה)
| סוג (מנורמל) | CONT | REV |
|---|---|---|
| Variation (`Normal_Variation`→Variation) | עם הרחבת IB בלבד | מותר (דוקטרינה) |
| Normal | צד-POC נכון · **mig=UNKNOWN** → צד-POC בלבד | קצוות VA |
| Neutral_* | חסום | קצוות |
| Trend_* | מותר (POC לא-שער) | חסום |
| Nontrend/Nonconviction | SKIP | SKIP |

**מגבלת-כנות:** `poc_migration` לא ב-`chart/replay.levels` → כל השורות `mig=UNKNOWN`.  
Normal CONT לא נבחן על mig-UP/DOWN (רק POC-side).

## פלט גולמי

```
live+demo scored: n=25  WITH=21  AGAINST=4 (16%)
  Variation: W=19 A=0
  Neutral_Extreme: W=2 A=3
  Normal: W=0 A=1

live+demo CONT-only (ליבת-D1): n=9  WITH=5  AGAINST=4 (44%)
  AGAINST:
    #257 06-29 INITIATIVE_SHORT Normal below_poc (wrong POC side) pnl=-123.75
    #310 07-08 ZLR LONG Neutral_Extreme (CONT blocked) pnl=+22.5
    #350 07-10 ZLR LONG Neutral_Extreme CONT blocked pnl=+52.5
    #344 07-10 ZLR LONG Neutral_Extreme CONT blocked pnl=+52.5

07-15..17 CONT: n=2 WITH=2 AGAINST=0  (+3 CONT UNSCORED = inside-IB)
  (מול T1 הישן: 10 AGAINST על 21 — ניפוח Variation)

shadow CONT+all: against≈42% (הרבה Neutral CONT / REV-mid)
```

JSON: `/tmp/w2_against_dalton_d0.json`

## מסקנה לערך-D1
1. **על Variation (רוב ימי-הלייב האחרונים):** D0 כבר "מיישר" CONT-with-expansion — הניפוח הסטטי נעלם.  
2. **ה-against האמיתי בלייב+דמו CONT:** בעיקר **Neutral×CONT** (3) + **Normal wrong-POC** (1) = **4**.  
3. D1/`DAYTYPE_POSITION_GATE` + family-aware יחסום את Neutral×CONT ו-Normal wrong-POC — זה הבסיס הכמותי (לא 48%).  
4. חסר לכיול מלא: **סדרת POC-migration** במקור-replay (כרגע UNKNOWN).

אין שינוי-שער כאן — מספרים לפסיקת-הדלקת D1 אחרי סים.
