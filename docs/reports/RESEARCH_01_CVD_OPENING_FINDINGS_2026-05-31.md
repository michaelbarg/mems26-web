# RESEARCH 01 — ממצאים: CVD + סיווג סוג פתיחה (ES/MES)

> סקירת ספרות ופרקטיקה — בסיס לעדכון `detect_opening_type`.
> **מעודכן/מחליף** את `OPENING_CVD_RESEARCH_2026-05-31.md` (מספרים מדויקים יותר,
> דגימת ES גדולה). סטטוס: RECOMMENDATION ONLY — אין שינוי קוד.

---

## 1 · נוסחת CVD — הבסיס

### 1.1 delta לבר
```
delta_i = ask_vol_i - bid_vol_i
```
`ask_vol` = נפח עסקאות ב-ask (אגרסיבי buy). `bid_vol` = נפח עסקאות ב-bid
(אגרסיבי sell). delta>0 → קונים אגרסיביים; delta<0 → מוכרים אגרסיביים.

### 1.2 CVD מצטבר
```
CVD_t = CVD_{t-1} + delta_t
```
אפס בפתיחת הסשן, מצטבר ברציפות. מדדים על חלון הפתיחה (N ברים):

| סימן | הגדרה | ערך |
|---|---|---|
| `net_CVD` | CVD_N − CVD_0 | סכום כל ה-delta בחלון |
| `total_vol` | Σ(ask_vol_i + bid_vol_i) | כל הנפח בחלון |
| `abs_delta_sum` | Σ\|delta_i\| | סכום ה-\|delta\| לכל בר |

### 1.3 חתימת עסקאות — tick rule מול BVC
- **tick rule (ברירת מחדל לפיוצ'רז):** uptick→buy; downtick→sell; unchanged→carry.
  דיוק ~83–93% (Odders-White 2000, Finucane 2000).
- **Lee-Ready:** Quote Rule + Tick Test ל-midpoint. ~85–95%.
- **BVC** (Easley-LdP-O'Hara): `V_buy = V·Φ[(P_i−P_{i-1})/σ_ΔP]`, Φ=normal CDF
  (RFS 2012) או t(0.25 d.f.) (JFE 2016). **אל תשתמש ב-BVC כשיש נתוני tick**
  (Andersen & Bondarenko 2015 — נחות על E-mini). BVC רק כשיש OHLCV בלבד.

## 2 · מדדי חד-כיווניות

### 2.1 Delta Efficiency (DE)
`DE = net_CVD / total_vol` — bounded [−1,+1]. שבר הנפח שהיה net directional.
מגבלה: גבוה גם בטייפ צ'ופי אם צד אחד מובהק לאורך.

### 2.2 Path / Persistence Efficiency (PE) ← **המדד המומלץ**
`PE = net_CVD / abs_delta_sum` — bounded [−1,+1].
PE≈1.0 → כל בר תרם delta באותו סימן (drive אמיתי). PE≈0.0 → התחלפות (auction).
PE שלילי → CVD התהפך. זהו מדד *monotonicity* של ה-delta.

### 2.3 Delta Divergence (DD)
bullish: מחיר low חדש אך CVD עולה → seller exhaustion. bearish: מחיר high חדש
אך CVD יורד → buyer exhaustion. משמש כ-**suppress**: divergence בקצה הקיצוני =
חתימת REJECTION_REVERSE, לא DRIVE.

### 2.4 Effort vs Result
`EVR = net_CVD / (high − low)`. DRIVE: delta גדול + range גדול. ABSORPTION:
delta גדול + range קטן (limit orders בולעים).

## 3 · חתימות כמותיות לפי סוג פתיחה (Dalton + ספרות)

| סוג | PE | net_CVD | divergence? | range exp | CVD flip? | ביטחון |
|---|---|---|---|---|---|---|
| **OPEN_DRIVE** | גבוה ≈0.7–1.0 | גדול+מונוטוני | לא | חזקה ≥ATR15 | לא | הגבוה |
| **OPEN_TEST_DRIVE** | גבוה אחרי טסט | גדול אחרי reversal מוקדם | לא | מתרחב אחרי טסט | brief flip→back | שני |
| **OPEN_REJECTION_REVERSE** | נמוך/שלילי | flip בסימן | **כן**, בקצה | ראשוני, נסוג | **כן** | נמוך (<50%) |
| **OPEN_AUCTION** | נמוך ≈0.0–0.2 | ~אפס | לא | קטנה | לא | הנמוך |

### פרוטוקול זיהוי
1. **DRIVE:** PE גבוה AND |net_CVD| גדול AND range_exp ≥1×ATR15 AND אין divergence.
2. **TEST_DRIVE:** PE מוקדם נמוך/שלילי (טסט), אז PE חזרה לגבוה AND net_CVD בכיוון סופי.
3. **REJECTION_REVERSE:** divergence בקצה AND net_CVD flip AND range ראשוני שנסוג.
4. **AUCTION:** PE נמוך AND |net_CVD| z-score נמוך AND range contained.

## 4 · חלון זמן: 15 מול 30 דק'

נתונים (6,142 ימי ES+NQ — tradingstats.net):

| חלון | double-break ES | double-break NQ |
|---|---|---|
| 5 דק' | **74.3%** | 69.2% |
| 15 דק' | **61.0%** | 52.6% |
| 30 דק' | **47.9%** | 39.4% |

- 15 דק': 61% מהימים שוברים שני צדדים → DRIVE שסווג ב-15 דק' מתבטל לעיתים קרובות.
  **label_15 לא אמין לבד.**
- 30 דק': double-break 47.9% — שיפור מהותי.
- Dalton: שיא/שפל יום בתוך 30 דק' ~50%, בתוך 60 דק' ~75%. DRIVE ניתן לזיהוי
  ב-5–15 דק'; שאר הסוגים — 30 דק' לנעילה.

המלצה: **label_15** = bias מוקדם low-confidence; **label_30** = נעילה בפועל
(משפיע על first_hour_matrix). DRIVE ב-label_15 actionable רק כש-PE + range_exp +
היעדר divergence כולם מסכימים.

## 5 · נורמליזציית Gap ל-ATR

±2 נק' מוחלט = 0.03–0.05×ATR14 (ATR יומי ES 40–60 נק') — "Tiny" בכל משטר, לא
מתרחב עם תנודתיות, לא גורם.

```python
gap_ratio   = (open - prev_close) / ATR14_daily
range_ratio = (OR_high - OR_low) / ATR15_intraday
```

סיווג gap (Gap Fill Indicator, 2,646 ימי ES):

| קטגוריה | טווח | פרשנות |
|---|---|---|
| Tiny | <0.3×ATR14 | זניח |
| Small | 0.3–0.7 | ניטרלי |
| Medium | 0.7–1.2 | מהותי, ↑AUCTION_OUT |
| Large | >1.2 | גדול, ↑DRIVE |

החלף `if abs(gap)>2.0` ב-`gap_ratio` עם 4 קטגוריות, כממד נפרד (לא סף בינארי).

## 6 · מסווג דו-שלבי (RECOMMENDATION ONLY)

```
T=09:30  open
T=09:45  label_15 (provisional, low-conf) → bias: DRIVE_BIAS/AUCTION_BIAS/UNCLEAR
            PE_15, DE_15, range_exp_15, gap_ratio, divergence_flag_15
T=10:00  label_30 (confirmed, decision-binding) → OPEN_DRIVE / TEST_DRIVE /
            REJECTION_REVERSE / AUCTION_IN / AUCTION_OUT
            PE_30, DE_30, range_exp_30, divergence_flag_30, CVD_sign_flip
```

```python
if PE_30 > 0.65 and range_exp_30 > 1.0 and not divergence:
    return OPEN_DRIVE
elif CVD_sign_flip and divergence_at_early_extreme:
    return OPEN_REJECTION_REVERSE
elif early_brief_opposite_delta and PE_30_final > 0.5:
    return OPEN_TEST_DRIVE
elif abs(net_CVD)/total_vol < 0.15 and PE_30 < 0.25:
    return OPEN_AUCTION_OUT if gap_ratio > 0.7 else OPEN_AUCTION_IN
else:
    return INDETERMINATE
```

**הספים = priors בלבד.** לנעול ספים רק אחרי soak SHADOW ≥~60 ימי מסחר.

## 7 · סיכום — מה להכניס ל-detect_opening_type

| כעת | מומלץ |
|---|---|
| `net_move/total_range` על 3 ברים | + PE, DE, divergence_flag על 6 ברים |
| CVD בלוג בלבד | CVD כקלט ממשי בהחלטה |
| gap ±2 נק' מוחלט | `gap_ratio = gap/ATR14_daily` עם 4 קטגוריות |
| label אחד ב-15 דק' | דו-שלבי: provisional (15) + confirmed (30) |
| אין divergence check | suppress DRIVE אם divergence בקצה |

## 8 · מקורות
Odders-White (2000); Finucane (2000); Easley-LdP-O'Hara (RFS 2012, JFE 2016);
Andersen & Bondarenko (2015); Cont-Kukanov-Stoikov (JFE 2014); Dalton "Mind Over
Markets"; tradingstats.net (6,142 ימי ES/NQ double-break; 2,646 ימי ES gap-fill).

---

> **STATUS: RECOMMENDATION ONLY — NO CODE CHANGES.** מימוש = מגה-פרומפט נפרד
> לאחר אישור Michael + soak SHADOW לכיול ספים.
