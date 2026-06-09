> ⚠️ **הוחלף ע"י `MEGA_E2E_1of2_PIPELINE_TRADES` + `MEGA_E2E_2of2_S1_S2_S3_IMPL`**
> (גרסת ה‑e2e המתוקנת 31/5 — מוסיפה אימות צינור + תיקון עמוד הטריידס לפני הסיווג).
> השתמש בגרסאות ה‑E2E.

# מגה‑פרומפט מימוש 1/2 — S2 + S3: ספים מוחלטים → יחסיים (ATR / נפח)

> פרומפט **מימוש** (משנה קוד) — להדבקה בסוכן קוד (Claude Code / Cursor) עם גישה
> ל‑repo `mems26_web_git`. מאושר עקרונית ע"י Michael 31/5. **קרא קודם `CLAUDE.md`
> ו‑`.cursor/rules/mems26-pre-live-protocol.mdc`.**
>
> ⚠️ כללי ברזל: SHADOW בלבד · אסור לגעת ב‑order routing / risk surface · כל שינוי
> **מאחורי feature flag שברירת המחדל שלו כבויה** (כבוי = התנהגות נוכחית מדויקת) ·
> **בסיס רגרסיה נלכד לפני כל שינוי** · אסור להפעיל את הדגל בלי אישור Michael.

---

## 0 · מה אנחנו מתקנים (MANIFEST — קרא לפני שמתחילים)

ממירים ספי **מחיר/טיק מוחלטים** ל**יחסיים** (ATR 5‑דק' / נפח). **לא** משנים אחוזים
וספירות מבניות. כל ערך חדש = **prior** (ברירת מחדל בקונפיג), ננעל אחרי soak.

### S2 — `backend/v9/systems/five_min/`
| קובץ | פרמטר נוכחי | משתנה ל (prior) |
|---|---|---|
| `five_min_system.py:31-32` | `EXPANSION_MIN_PT=1.5`/`MAX_PT=1.75` | `bar_range ≥ k_exp×ATR5m`, k_exp=1.5–2.0 |
| `five_min_system.py:33` | `POC_RETURN_TOLERANCE_PT=0.5` | `k_poc×ATR5m`, k_poc≈0.1–0.25 |
| `quality_tier.py:22` | `PROXIMITY_PT=2.0` | `k_prox×ATR5m`, k_prox=1.0–1.5 |
| `sr_proximity.py:17` | `DEFAULT_PROXIMITY_TICKS=5` | `k_sr×ATR5m`, k_sr=1.0–1.5 |
| `adaptive_stop.py:20` | `FLOOR_TICKS=4` | `k_stop×ATR5m` (1.5–2.0) **+ רצפת מינ' מוחלטת נשארת backstop** |
| `patterns/flags.py:11,36` | `POLE_MIN_HEIGHT_TICKS=16` | pole `≥5.5×ATR5m`; flag `≤2.5×ATR5m` (Katsanos) |
| `patterns/head_shoulders.py:11,30` | `HEAD_MIN_EXT_TICKS=2` | פרופורציונלי לגובה הדפוס (לא טיקים) |
| `patterns/double_bt.py:87,104` | `tolerance=TICK_SIZE*2` (0.5pt) | `k_db×ATR5m`, k_db=0.5–1.0 |

**להשאיר כפי שהוא (אחוזים/יחסים — לא לגעת):** `SHOULDER_SYM_PCT`,
`TROUGH_SYM_PCT`, `NECKLINE_MIN_RISE_PCT`, `POLE_DIRECTIONAL_PCT`,
`FLAG_MAX_RETRACE_PCT`, `DROP_THRESHOLD_PCT`, `LOOKBACK_MAX_VOL_RATIO`,
`BELLY_DOMINANCE_RATIO`.

### S3 — `backend/v9/systems/footprint/`
| קובץ | פרמטר נוכחי | משתנה ל (prior) |
|---|---|---|
| `signals/stacked_imbalance.py:21` | `MIN_LEVEL_VOL=10` | **נפח‑יחסי**: `k_vol×median_level_vol` של הבר (לא ATR) |
| `detectors.py:102` | `analyze_context(range_ticks=15.0)` | `k_rng×ATR5m`, k_rng≈1.0 |

**להשאיר:** `STACK_N=3`, `TREND_BARS=4`, `min_acc_bars=5`, `IMB_THRESHOLD=2.5`,
`poc_threshold_pct=30`, `empty 5`, `EXHAUSTION_FACTOR`, `DIRECTIONAL_BODY_PCT`.

### תשתית משותפת — ATR (חדש)
אין עמודת ATR ב‑DB. צור helper `atr_5min(bars, period=14)` שמחשב ATR מ‑True Range
על ברי 5‑דק' שכבר נקלטו (`v9_bars_5min`). **מקור‑אמת:** אם <period ברים →
מחזיר `None`, וה‑caller **נופל חזרה לסף המוחלט הישן** (לא מסנתז). תעד period.

---

## 1 · מנגנון הבקרה (חובה)

1. **Feature flags, default OFF** — הוסף ל‑config: `S2_ATR_RELATIVE=False`,
   `S3_RELATIVE=False`. כשכבוי → **בדיוק** הקוד המוחלט הקיים (אפס שינוי התנהגות).
   כשדולק → הנתיב היחסי. אל **תפעיל** אותם.
2. **בסיס רגרסיה לפני כל שינוי (גיבוי):**
   - לפני נגיעה בקוד: כתוב `tests/v9/regression/test_s2_s3_baseline_golden.py`
     שמריץ את ה‑detectors הקיימים על ~30–50 ברים מייצגים (fixtures) ושומר את
     הפלט כ‑**golden snapshot** (`tests/v9/regression/golden/s2_s3_*.json`).
   - אחרי השינוי: הטסט מוודא ש‑**flag OFF ⇒ פלט זהה ל‑golden** (אפס רגרסיה),
     ו‑**flag ON ⇒ ההבדל הצפוי בלבד** (assertions ממוקדות).
   - commit ה‑golden + הטסט **לפני** שינוי הלוגיקה. זהו הגיבוי.
3. **שינוי אחד בכל פעם** — סדר: EXPANSION (1.16) → POC → PROXIMITY/SR → STOP →
   patterns(flags/H&S/double_bt) → S3. אחרי כל אחד: רגרסיה ירוקה + report.
4. **4 צירי UAT** לכל שינוי שנוגע ל‑endpoint/דאטה: Quality · Recency ·
   Cardinality · Latency (<100ms).
5. **smallest correct change** — בלי refactor "תוך כדי". בלי לגעת ב‑order routing,
   gateway, risk, sizing (sizing מבוסס‑תנודתיות = **לא מאושר**, לא לממש).

## 2 · תוצרים + שערים
- קומיט נפרד לכל פרמטר, עם הרגרסיה הירוקה ב‑diff.
- דוח `docs/reports/S2_S3_RELATIVE_IMPL_<date>.md`: מה הומר, golden coverage,
  פלט רגרסיה גולמי (flag off=identical, flag on=expected diff).
- **שער:** הדגלים נשארים כבויים. הפעלה ב‑SHADOW + נעילת k‑values = אחרי soak
  ואישור Michael נפרד.

## 3 · אסור
- להפעיל flags · לגעת ב‑order/gateway/risk/sizing · לשנות אחוזים/ספירות מבניות ·
  לסנתז ATR · refactor רחב · להחליף ערך מוחלט בלי fallback כש‑ATR=None.

> STATUS: מימוש מאחורי flags בלבד. ערכי k = priors. נעילה אחרי soak + אישור.
