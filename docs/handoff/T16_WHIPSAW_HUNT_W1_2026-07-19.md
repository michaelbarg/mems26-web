# W1 · ציד whipsaw ל-T16 — הרחבה + מסקנה (ריצה חוזרת 2026-07-19 22:40 IL)

**בעלים:** cursor-agent · קריאה-בלבד · מרחיב `T16_REVERSAL_BACKTEST_2026-07-19.md`  
**JSON:** `/tmp/t16_w1_rerun.json`

## יקום
```
FETCH trades=353 (auth) · mode∈{live,demo} · RTH 09:30–16:00 ET · t1_hit
n_t1=15
DAYS_GE3_T1: 2026-07-02(3), 2026-07-10(3)
ALL_T1_DAYS: 07-01:1 07-02:3 07-03:1 07-07:2 07-09:1 07-10:3 07-13:2 07-15:1 07-17:1
```

## מתודולוגיה
- אחרי T1 · ≥2 סגירות עוקבות נגד הפוזיציה · **לפני exit_ts**
- שמרני: גם `cum_delta` / CVD.d עוין על בר-הטריגר
- CF: רגלי HIT נשארות · OPEN נמשכות ב-close±0.5pt
- **HURT_WHIPSAW:** δ&lt;−$5 **וגם** fav_after≥5pt בכיוון-העסקה **וגם** actual&gt;cf

## פלט גולמי
```
=== CVD+price (conservative): trig=1 helped=1 hurt=0 whipsaw_hurt=0 net_delta=+$175.00
  #282 07-02 HELPED Δ+175.00 fav=17.75 ge3=True clip_opp=True

=== price-only: trig=3 helped=2 hurt=0 whipsaw_hurt=0 net_delta=+$181.25
  #282 07-02 HELPED Δ+175.00
  #344 07-10 HELPED Δ+6.25 fav=7.75 ge3=True clip_opp=True
  #261 07-01 NEUT Δ+0.00 fav=30.25

GE3 07-10: אין טריגר CVD-שמרני לפני יציאה; price-only תופס #344 כ-HELPED (לא HURT)
```

(ריצה קודמת W1 בערב: CVD trig=3 helped=3 hurt=0 whipsaw=0 net=+$207.5 — אותה מסקנה; הבדלי-CVD נובעים ממיפוי cum_delta vs נקודות CVD.)

## המקרה-הגרוע במדגם
אין HURT. הכי "יקר" כהזדמנות-שיא (clip-opp, לא hurt): **#282** fav_after=17.75pt אחרי טריגר — אבל היציאה בפועל הייתה גרועה מה-pull → δ חיובי.

## שורת-מסקנה (מכריעה T16)

| | |
|---|---|
| **T16 כן/לא** | **כן לבנות** דגל `SYSTEM6_REVERSAL_TIGHTEN_V1` default-OFF · **לא AUTO** עד סים |
| **באיזה trigger** | **CVD-adverse + ≥2 סגירות-עוינות אחרי T1 ולפני יציאה** (שמרני). price-only רופף מדי ל-AUTO |
| **ראיה** | whipsaw_hurt=**0** על N=15 כולל שני ימי ≥3×T1 · net חיובי על טריגרים |
| **פסיקת-מייקל** | כבר **א'** ב-LIVE_CHANNEL — תואם למסקנה זו |

אין מימוש מסחר כאן.
