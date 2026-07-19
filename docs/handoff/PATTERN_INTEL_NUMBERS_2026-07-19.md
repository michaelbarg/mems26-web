# PATTERN INTEL NUMBERS — against-Dalton baseline (T1) · 2026-07-19

**משימה:** `CURSOR_TASKLIST` T1 · סוגר Bible-U2 / G-11 (מספרים מ-DB via API).  
**מבצע: cursor-agent** · מאמת: cowork-dev (חוק-5).

## שיטה + מגבלות
- `scripts/audit_pattern_miss.py --relax all` **נכשל** על חיבור-PG חדש:
  `Postgres.app failed to verify "trust" authentication` (dialog לא נפתח מתהליך-הסוכן).
- הבקאנד החי (`:8000`) כבר מחובר ל-PG → מקור-ראיה:  
  `GET /api/v9/chart/replay?date=` (trades+levels) + `GET /api/v9/day_type/classify_replay?date=`.
- הגדרת **against-Dalton** (כפי במפרט): משפחת-CONT +  
  `(LONG ∧ zone∈{near_vah,above_value}) ∨ (SHORT ∧ zone∈{near_val,below_value})`.  
  אזור כמו `location_gate.zone_of` (tol=0.25×IBW, floor1/cap4).
- **הערת-Variation:** שני הימים עם VA היו `Normal_Variation` ב-classify_replay — CONT short ליד-VAL
  יכול להיות *עם-הרחבה* לפי D0; נספר כאן כ-against לפי הגדרת-המפרט (קצה-VA הפוך לפייד),
  לא כפסק-D0 הסופי ל-Variation.
- `is_sim`: API `sierra.is_sim=null` / mode=live; **אין op=PLACE** — קריאה בלבד.

## פלט-גולמי (סיכום)

| date | classify_replay.final | n_trades | VA | against |
|---|---|---|---|---|
| 2026-07-15 | Normal_Variation CLASSIFIED | 11 | VAH=7619 VAL=7593.25 | **5** |
| 2026-07-16 | Trend_Normal CLASSIFIED | 0 | **חסר** (אין poc/vah/val ב-replay) | n/a |
| 2026-07-17 | Normal_Variation CLASSIFIED | 10 | VAH=7536.5 VAL=7506.25 | **5** |

**TOTAL scored rows with VA: 21 · AGAINST: 10 (48%)**

### Against list (raw)
```
2026-07-15 AGAINST 378 GB100 SHORT near_val dist=24.25 WIN +97.5
2026-07-15 AGAINST 379 GB100 SHORT near_val dist=24.25 WIN +77.5
2026-07-15 AGAINST 384 ZLR LONG near_vah dist=24.75 LOSS -41.25
2026-07-15 AGAINST 385 ZLR LONG near_vah dist=24.75 LOSS -37.5
2026-07-15 AGAINST 386 ZLR LONG near_vah dist=24.50 LOSS -37.5
2026-07-17 AGAINST 399 BEAR_FLAG_SHORT SHORT near_val dist=28.25 WIN +56.25
2026-07-17 AGAINST 400 BEAR_FLAG_SHORT SHORT near_val dist=28.25 WIN +20.0
2026-07-17 AGAINST 401 ZLR SHORT below_value dist=34.75 WIN +28.75
2026-07-17 AGAINST 402 ZLR SHORT below_value dist=36.25 WIN +26.25
2026-07-17 AGAINST 404 ZLR SHORT below_value dist=37.25 WIN +93.75
```

### By pattern

| pattern | n | against | against% | avg_dist_to_edge | win% | pnl_usd |
|---|---:|---:|---:|---:|---:|---:|
| ZLR | 9 | 6 | 67% | 26.92 | 44% | −26.25 |
| GB100 | 2 | 2 | 100% | 24.25 | 100% | +175.00 |
| BEAR_FLAG_SHORT | 2 | 2 | 100% | 28.25 | 100% | +76.25 |
| HTLB | 2 | 0 | 0% | 6.75 | 0% | −112.50 |
| INITIATIVE_SHORT | 2 | 0 | 0% | 17.00 | 50% | −26.25 |
| REACTIVE_LONG | 3 | 0* | 0% | 16.92 | 0% | −142.50 |
| SIM_TEST | 1 | 0 | 0% | 104.25 | 0% | 0 |

\* REACTIVE_LONG #382/#383 היו `near_vah` (REV long בתקרה) — **לא** במונה-CONT; דוקטרינת-פייד הייתה חוסמת אותם גם כן.

### C1/C2/C3 hit-rate
מ-`exit_price` מול `t1/t2/t3` על 18 שורות עם יעד+יציאה: **c1=0 c2=0 c3=0 (0%/0%/0%)**.  
כלומר בנתוני-ה-replay האלה היציאה לא נגעה ביעדים (רוב STOP/BE/LOSS לפני T1, או יעדים לא-תואמים) —
**לא** להשתמש כ-hit-rate אמין עד שדה-outcome עשיר יותר / audit_pattern_miss עם PG תקין.

## פקודות (שיחזור)
```bash
# נכשל אצל הסוכן (Postgres.app trust):
BRIDGE_TOKEN=… python3 scripts/audit_pattern_miss.py --date 2026-07-15 --relax all

# ראיה בפועל:
curl -sS 'http://127.0.0.1:8000/api/v9/chart/replay?date=2026-07-15'
curl -sS 'http://127.0.0.1:8000/api/v9/day_type/classify_replay?date=2026-07-15'
# + סקריפט zone/against כמפורט ב-LIVE_CHANNEL
```

## Follow-up ל-cowork
1. ריסטארט Postgres.app (trust dialog) → להריץ `audit_pattern_miss --relax all` על 15/16/17 ולהחליף את הבסיס אם שונה.  
2. 07-16: למה replay בלי VA + 0 trades — פער-נתונים נפרד.
