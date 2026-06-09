# טבלה מאוחדת — מצב קיים מול המלצה (S1/S2/S3 + CVD/ATR)

**נוצר:** 2026‑05‑31 (Cowork) · **עודכן:** 2026‑05‑31 (שולב 3 דוחות מחקר חיצוני)
· **סטטוס:** סיכום מחקר — הכל המלצה הממתינה לכיול פנימי + אישור Michael. **שום
פריט אינו מבוצע.** מקורות:
`RESEARCH_01_CVD_OPENING_FINDINGS` (פתיחה+CVD) ·
`RESEARCH_02_S2_PATTERNS_ATR` (תבניות S2 + stops) ·
`RESEARCH_03_DAYTYPE_30MIN_STAGING` (day‑type 30 דק') ·
`S1_S2_ATR_NORMALIZATION_RESEARCH` (חוצה‑מערכות).

מקרא סטטוס: 🔄 להמיר ליחסי · ✅ כבר תקין (להשאיר) · 🔬 דורש כיול פנימי ·
❓ לאמת זמינות נתונים · ❌ לא מאושר / לא לביצוע · ✔️ אומת, אין שינוי.

---

## 0 · חוצה‑מערכות

| נושא | מצב קיים | המלצה | סטטוס |
|------|----------|--------|--------|
| Reference ATR | אין נרמול — ספים מוחלטים | ATR **5‑דק'** len ~10–14 לאות, ~14–20 ל‑sizing; **לעולם לא יומי** | 🔄 |
| כיול מכפיל k | מספרים עגולים ידניים | פרסנטיל היסטורי (~70–90 ל‑expansion) + walk‑forward + plateau | 🔬 |
| עונתיות תוך‑יומית (U‑shape) | סף אחיד כל היום | מכפיל time‑of‑day / 1–3 ברים ראשונים כמשטר נפרד | 🔄🔬 |
| position sizing | לא מבוסס‑תנודתיות (capped 2) | vol‑based: `Contracts = Risk$ ÷ (ATR×k×$5)` | ❌ לא מאושר |
| מפסק יומי + רצפת stop | תקרת $250 (P‑L0a) | מפסק קשיח $250 + רצפת stop מוחלטת | ❌ לא מאושר |

## 1 · S1 — Day Type

| פרמטר | מצב קיים | המלצה (priors מהמחקר) | סטטוס |
|--------|----------|--------|--------|
| רוחב IB | NARROW <15 · MED 15–25 · WIDE >25 נק' מוחלט | `IB_range / ATR14_**daily**` ב‑4 tiers: **צר <0.5 · נורמלי 0.5–1.0 · רחב 1.0–1.5 · קיצוני >1.5** (R03: 5,519 ימים — צר 98.7% שבירה, קיצוני 66.7%). שים לב: IB=מבנה session → ATR **יומי** | 🔄🔬 |
| אי‑התאמה רוחב IB | קוד מריץ 25, הערה אומרת 20 (`schemas.py:43`) | ליישר הערה ל‑25 (תיעוד) | 🔄 (בטוח) |
| gap | ±2.0 נק' מוחלט (`state_machine.py:408`) | `gap/ATR14_daily`, 4 קטגוריות: Tiny<0.3 · Small 0.3–0.7 · Medium 0.7–1.2 · Large>1.2 (ממד נפרד) | 🔄🔬 |
| תקופת IB / staging | 60 דק' נקודה יחידה, נעילה 13:00 | **מודל 4 שלבים** (R03): 30דק'=השערה ≤60% · 10:30=רוחב IB · C‑period 10:30–11:00=אישור · עומק נסיגה=הכרעה. מכייל את 30/60/90 | 🔄🔬 |
| חלון סיווג פתיחה | 3 ברים (15 דק') יחיד | provisional label_15 (09:45) → confirmed label_30 (10:00). double-break ES 15-דק' 61%/30-דק' 47.9% | 🔄🔬 |
| קלט סיווג פתיחה | מחיר בלבד `net_move/range≥0.7` | + `PE` + DE + range/ATR + divergence | 🔄 |
| CVD בהחלטה | מוזרם אך לא משפיע (רק `reasoning_notes`) | קלט מרכזי (`PE=net_CVD/Σ|delta|`) | 🔄✅(נתונים) |
| directional_ratio | 0.7 (כבר יחסי) | יחסי — לכייל סף בלבד | ✅🔬 |
| delta rule (Neutral) | extensions שני צדדים `>0` (שלם) | ספירה מבנית — להשאיר שלם | ✅ |
| width rule (TPO) | `>5` אותיות (שלם) | מבני — להשאיר | ✅ |
| הצבעות רצופות לנעילה | `≥2` (שלם) | מבני — להשאיר | ✅ |
| סף ביטחון לנעילה | 0.85 | סף הסתברות — לבחון מול gates של R03 | 🔬 |
| נעילה כפויה | `session_min≥210` (13:00 ET) | להחליף ב‑gates: C‑period + עומק נסיגה | 🔬 |
| 1.14 Status enum | `_check_day_type` מחזיר `lock_state` חי | המיפוי קיים — אין באג | ✔️ |

## 2 · S2 — five_min (תבניות/setups)

> ATR ל‑S2 = **5‑דק'** (len 14, או 6–10 לזמן החזקה <שעה). אזהרת Davey: לבדוק
> dollar vs ATR ב‑backtest, לא להניח.

| פרמטר | מצב קיים | המלצה (priors מ‑R02) | סטטוס |
|--------|----------|--------|--------|
| EXPANSION_MIN/MAX | 1.5 / 1.75 נק' (`five_min_system.py:31`) | בר ≥ **1.5–2×ATR(5min)** או ATR Δ≥5% | 🔄🔬 (=1.16) |
| POC_RETURN_TOLERANCE | 0.5 נק' (`:33`) | ATR fraction (~0.25–0.5×) | 🔄🔬 |
| PROXIMITY_PT | 2.0 נק' (`quality_tier.py:22`) | buffer **1–1.5×ATR** | 🔄🔬 |
| SR proximity | 5 טיק =1.25 נק' (`sr_proximity.py:17`) | **1–1.5×ATR** מעבר לאזור | 🔄🔬 |
| STOP floor | 4 טיק (`adaptive_stop.py:20`) | **1.5–2×ATR** + רצפת מינ' (ATR‑min/%) | 🔄🔬 (sizing ❌) |
| POLE_MIN_HEIGHT | 16 טיק =4 נק' (`flags.py`) | **≥5.5×ATR**; flag ≤2.5×ATR (Katsanos) | 🔄🔬 |
| HEAD_MIN_EXT | 2 טיק (`head_shoulders.py`) | פרופורציונלי; כתפיים ביחס **0.80–1.20** | 🔄🔬 |
| double_bt tolerance | 0.5 נק' (`double_bt.py:87`) | **0.5–1×ATR(5min)** (LMW 1.5% רחב מדי לאינטראדיי) | 🔄🔬 |
| symmetry % (shoulder/trough) | 5% / 3% | להשאיר % (LMW 1.5%) | ✅ |
| retrace / neckline % | 50% / 10% / 60% | להשאיר % | ✅ |
| DROP/LOOKBACK/BELLY ratios | 0.10 / 0.6 / 1.5 | יחסי נפח — להשאיר | ✅ |

## 3 · S3 — footprint

| פרמטר | מצב קיים | המלצה | סטטוס |
|--------|----------|--------|--------|
| MIN_LEVEL_VOL | 10 חוזים מוחלט (`stacked_imbalance.py:21`) | נרמל ל**נפח** (בר/חציוני), לא ATR | 🔄🔬 |
| range_ticks (accumulation) | 15.0 טיק (`detectors.py:102`) | `ATR×k` | 🔄🔬 |
| STACK_N / TREND_BARS / min_acc | 3 / 4 / 5 (שלם) | ספירות מבניות — להשאיר | ✅ |
| jumps_count / confluence | ≥3 / ≥4/6 (שלם) | מבני — להשאיר | ✅ |
| IMB_THRESHOLD | 2.5 (ask/bid) | יחס — להשאיר | ✅ |
| poc% / empty% / imbalance% | 30% / 5% / ≥250% | יחסי — להשאיר | ✅ |
| EXHAUSTION_FACTOR / BODY% | 0.6 / 0.5 | יחסי — להשאיר | ✅ |

## 4 · CVD / סיווג פתיחה (נוסחאות)

| היבט | מצב קיים | המלצה | סטטוס |
|------|----------|--------|--------|
| מטריקת חד‑כיווניות | אין | **`path_eff = net_CVD / Σ|delta_i|`** (ראשית) | 🔄 |
| מטריקות תומכות | אין | `delta_eff = net/total` · z‑score(60) | 🔄 |
| מטריקות תומכות | אין | `DE = net_CVD/total_vol` · `EVR = net_CVD/range` · z‑score | 🔄 |
| range expansion | אין | `range_exp = OR/ATR15`, drive `>1.0` | 🔄🔬 |
| חתימת delta | Sierra CDV (COT/AMT) — לאמת | `delta = ask_vol − bid_vol`; tick rule/aggressor (**לא BVC**) | ❓ |
| divergence guard | היפוך מחיר בלבד | דכא DRIVE על divergence בקצה (=REJECTION_REVERSE) | 🔄 |
| ספי סיווג (priors) | קבוע 0.7 | DRIVE: `PE_30>0.65 & range_exp>1.0 & ¬div` · AUCTION: `net/total<0.15 & PE<0.25` | 🔬 (נעילה אחרי soak ~60 ימי SHADOW) |
| חלון (מעודכן RESEARCH 01) | 3 ברים (15 דק') | provisional 09:45 → lock 10:00. double-break ES: 15-דק' **61%**, 30-דק' **47.9%** | 🔄 |
| זמינות CVD per‑bar | `cumulative_delta` 200/200 · footprint `delta`+`levels` 200/200 (אומת 31/5) | קיים ומאוכלס | ✅ **חוסם נסגר** |

---

## חוסמים לפני כיול פנימי
1. ✅ **זמינות CVD per‑bar — נסגר (31/5).** `cumulative_delta` 200/200,
   footprint `delta`+`levels` 200/200. נותרת נואנסה: `cumulative_delta` מתאפס
   בגבול session → לחשב PE בתוך חלון session (לא חוצה reset).
2. ⚠️ **ATR לא שמור** — אין עמודה ולא טבלת daily‑ATR. לגזור: 5‑דק' ATR
   מ‑`v9_bars_5min`, daily ATR מטבלת ברים יומית (לאתר/לבנות).
3. 🔬 **היסטוריה** — footprint רק מ‑2026‑05‑12 (~13 ימי RTH). soak ל‑~60 ימים
   לנעילת ספים עדיין נדרש.

## אישורי Michael (31/5 — עקרוני, ממתין לכיול+backtest)
- ✅ **S2** המרת כל ספי הנקודות → ATR יחסי (priors R02).
- ✅ **S3** MIN_LEVEL_VOL→נפח, range_ticks→ATR.
- ✅ **סיווג הרצת פתיחה** PE/CVD + gap קטגוריות + 15→30.
- ⏳ **סוג היום** — מודל מוצע (30=ראשוני · 60=חיזוק+נעילת IB · re-diagnosis מתמשך).
  ממתין לאישור סופי; הערת Cowork: שמר את חלון C-period (≈90 דק') כשלב ולידציה.

## מה כבר הוכרע (אין צורך בכיול)
- ✅ ספי % (סימטריה/ריטרייס) נשארים יחסיים.
- ✅ ספירות מבניות (STACK_N/TREND_BARS/votes/confluence) נשארות שלמות.
- ✔️ 1.14 Status enum — אין באג.
- ❌ sizing מבוסס‑תנודתיות + מפסק $250 + רצפת stop — לא מאושר, לא לביצוע.

## השלב הבא המוצע
אימות זמינות נתונים (חוסמים 1–2) → ואז כיול פנימי על `v9_bars_5min` שהופך את כל
ה‑priors למספרים מכוילים. שום מימוש בלי אישור Michael.
