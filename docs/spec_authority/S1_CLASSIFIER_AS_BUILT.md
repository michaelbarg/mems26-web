# S1 מסווג — איך הוגדר בפועל (as-built, מהקוד)
*`backend/v9/systems/day_type/daytype_classifier.py` + `config/daytype_trading_plan.yaml`. 2026-06-20.*

## סדר-העדיפות (עוברים מלמעלה; הראשון שמתאים — מנצח)

| # | תנאי | תוצאה |
|---|---|---|
| 0 | `returned_through_open` | דגל-זמני `opening_invalidated` (חוסם Trend-מ-פתיחה למטה; **לא** טרמינלי) |
| 1 | `n_bars < 6` (30 הדק׳ הראשונות) | **FORMING** |
| 2 | `sides == 2` | משפחת **Neutral** (ר' למטה) |
| 3 | `sides == 1` | **Variation / Trend** (ר' למטה) |
| 4 | `sides == 0` | **Nontrend / Normal** (ר' למטה) |

## הכללים המדויקים

**sides == 2 (Neutral):**
| תנאי | תוצאה |
|---|---|
| `rib < 1.3` | Neutral · FORMING ("פוקסים שוליים") |
| `close_pos ≥ 0.85` או `≤ 0.15` | **Neutral_Extreme** |
| `close_pos 0.33–0.67` | **Neutral_Center** |
| אחרת | Neutral · FORMING |

**sides == 1 (Variation/Trend):**
| תנאי | תוצאה |
|---|---|
| `dd_second_dist == True` | **Trend_DD** |
| `open∈{Drive,TestDrive}` + `one_tf` + `rib ≥ 2.5` + CVD-כיווני + `not oi` | **Trend_Normal** |
| `1.3 ≤ rib < 2.5` ⚠️ | **Variation** *(צ"ל < 2.0 לפי המטריצה — באג)* |
| אחרת | Variation · FORMING |

**sides == 0 (Nontrend/Normal):**
| תנאי | תוצאה |
|---|---|
| `vol_ratio ≤ 0.5` + `rib ≤ 1.5` | **Nontrend** (השתתפות-נמוכה) |
| `IB ≤ 7 נק'` + `rib ≤ 1.15` | **Nontrend** (בסיס-צר קלאסי) |
| `rib ≤ 1.3` + לא-נמוך-ווליום + IB-לא-צר | **Normal** |
| אחרת | FORMING |

## איך כל קלט נמדד
| קלט | הגדרה |
|---|---|
| `sides` | מספר קצוות-IB עם **≥2 ברים רצופים** שסוגרים **≥0.3×IB** מעבר (0/1/2) |
| `rib` | (RTH_high − RTH_low) ÷ IB_width |
| `one_tf` | תקופות 30-דק׳: UP אם אין Lower-Low / DOWN אם אין Higher-High |
| `CVD-כיווני` | `cvd_pos ≥ 0.75` או `≤ 0.25` (cvd_pos מנורמל בטווח-הסשן) |
| `vol_ratio` | ווליום-הסשן ÷ **חציון-ימים-קודמים** ⚠️ (הבסיס מזוהם — ר' למטה) |
| `IB_width` | (max−min) של 12 הברים הראשונים (60 דק׳), מוחלט |
| `opening_type` | גלאי 5-הסוגים על 6 הברים הראשונים |
| `dd_second_dist` | **proxy**: קפיצת-POC ≥0.8×IB שמחזיקה — **לא** single-print אמיתי ⚠️ |

## באגים/פערים שהסריקה חשפה (לתיקון)
1. **`vol_ratio` מזוהם** — בסיס-החציון כולל ימים-מוקדמים-זבל → יחסים של 20–632×. **לתקן:** בסיס יציב (חציון-עמיד / רק ימים נקיים).
2. **IB מזוהם** לימים 06-05→06-12 (גלגול-חוזה) → 45–75 נק'. **garbage-in** — אי-אפשר לכייל על הימים האלה.
3. **Trend_DD proxy נדלק-יתר** (06-05/08/15/16). **לתקן:** להחמיר/לכבות עד single-print אמיתי (P4).
4. **Variation חוסם-עליון** = 2.5 במקום **2.0** (לא השתמשתי ב-`rib_variation[1]`). **לתקן:** `1.3 ≤ rib < 2.0`.

> מסקנה: **רק ימים נקיים (06-15 ואילך, פוסט-גלגול) ניתנים לאימות.** הימים המוקדמים צריכים דאטה-נקי קודם. 06-18=Normal · 06-19=Nontrend — נכונים.
