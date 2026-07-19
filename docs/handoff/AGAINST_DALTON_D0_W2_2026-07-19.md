# W2 · against-Dalton לפי מפת-D0 (ריצה חוזרת 2026-07-19)

**בעלים:** cursor-agent · API `/trades`+`/chart/replay`+`/classify_replay`  
**`audit_pattern_miss`:** נכשל — Postgres.app trust-dialog (`FATAL: failed to verify "trust"`). עקף ב-API.

## שיטת-D0
Variation CONT = רק עם הרחבת-IB · Normal CONT = צד-POC (`mig=UNKNOWN`) · Neutral CONT=חסום · Trend REV=חסום · Nontrend=SKIP.

## פלט גולמי
```
total RTH=328 live+demo=30 shadow=298

live+demo ALL: scored=25 WITH=21 AGAINST=4 (16%)
  Variation: W=19 A=0
  Neutral_Extreme: W=2 A=3
  Normal: W=0 A=1
  AGAINST:
    #350 07-10 ZLR CONT Neutral_Extreme (CONT blocked) pnl=+52.5
    #344 07-10 ZLR CONT Neutral_Extreme (CONT blocked) pnl=+52.5
    #310 07-08 ZLR CONT Neutral_Extreme (CONT blocked) pnl=+22.5
    #257 06-29 INITIATIVE_SHORT CONT Normal SHORT below POC pnl=-123.75

live+demo CONT-only: n=9 WITH=5 AGAINST=4 (44%)
07-15.. CONT: n=2 WITH=2 AGAINST=0
shadow ALL: scored=252 WITH=167 AGAINST=85 (34%) — בעיקר Neutral×CONT + Trend×REV
```
JSON: `/tmp/w2_against_dalton_rerun.json`

## מסקנה לערך-D1
1. ניפוח T1 הסטטי (Variation as fade) **נעלם** תחת D0 (Variation A=0 בלייב+דמו).  
2. against אמיתי לייב+דמו = **4** (3×Neutral CONT + 1×Normal wrong-POC).  
3. D1/position+family יחסום בדיוק את אלה — בסיס כמותי להדלקה אחרי סים.  
4. חסר: סדרת `poc_migration` ב-replay (עדיין UNKNOWN).
