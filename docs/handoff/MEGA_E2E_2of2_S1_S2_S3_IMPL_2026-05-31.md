# מגה‑פרומפט E2E 2/2 — מימוש סיווג S1/S2/S3 (relative + CVD) מאחורי flags

> פרומפט **מימוש** להדבקה בסוכן קוד עם גישה ל‑repo `mems26_web_git`.
> **קרא קודם `CLAUDE.md` + `.cursor/rules/...mdc`.** **מחליף** את
> `IMPL_PROMPT_1of2/2of2` הישנים (מאחד אותם).
>
> ⚠️ **שער כניסה:** מתחילים רק אחרי שפרומפט E2E 1/2 ירוק (צינור מאומת + טריידס
> תקין). SHADOW בלבד · כל שינוי **מאחורי feature flag default OFF** · **בסיס
> רגרסיה (golden) לפני כל שינוי** · ATR/CVD ממקור‑אמת (`None` כשחסר) · אסור
> להפעיל flag / לנתב ל‑playbook/order/risk/sizing בלי אישור Michael.

---

## 0 · רצף עבודה
**שלב 0 (כיול offline, ללא קוד חי):** חשב מהברים (`v9_bars_5min`,
`v9_bars_footprint`) את ה‑k‑values האמיתיים שיחליפו את ה‑priors — היסטוגרמות
range/ATR, פרסנטילים, double‑break בפועל. תוצר: `docs/reports/CALIBRATION_FINDINGS`.
אם לא רץ עדיין — מממשים עם priors כברירת מחדל בקונפיג (flag off ממילא).

**שלבי מימוש:** S2 → S3 → S1‑opening → S1‑daytype, אחד בכל פעם, רגרסיה ירוקה +
report בין שלב לשלב.

## 1 · MANIFEST — מה משנים (priors; ATR 5‑דק' אלא אם צוין יומי)

### S2 — `systems/five_min/` (flag `S2_ATR_RELATIVE=False`)
| קובץ | נוכחי | → |
|---|---|---|
| `five_min_system.py:31-32` | EXPANSION 1.5/1.75 נק' | `bar_range ≥ 1.5–2×ATR5m` |
| `:33` | POC_RETURN_TOLERANCE 0.5 נק' | `~0.1–0.25×ATR5m` |
| `quality_tier.py:22` | PROXIMITY_PT 2.0 | `1–1.5×ATR5m` |
| `sr_proximity.py:17` | 5 טיק | `1–1.5×ATR5m` |
| `adaptive_stop.py:20` | FLOOR_TICKS 4 | `1.5–2×ATR5m` + רצפת מינ' מוחלטת backstop |
| `patterns/flags.py` | POLE 16 טיק | pole `≥5.5×ATR`; flag `≤2.5×ATR` |
| `patterns/head_shoulders.py` | HEAD 2 טיק | פרופורציונלי לגובה |
| `patterns/double_bt.py:87` | tol 0.5 נק' | `0.5–1×ATR5m` |
| **להשאיר** | SYM/RETRACE %, DROP/LOOKBACK/BELLY ratios | ✅ |

### S3 — `systems/footprint/` (flag `S3_RELATIVE=False`)
| קובץ | נוכחי | → |
|---|---|---|
| `signals/stacked_imbalance.py:21` | MIN_LEVEL_VOL 10 | **נפח‑יחסי** `k×median_level_vol` (לא ATR) |
| `detectors.py:102` | range_ticks 15.0 | `~1×ATR5m` |
| **להשאיר** | STACK_N/TREND_BARS/min_acc/IMB%/POC% | ✅ |

### S1‑opening — `day_type/detector.py` + `state_machine.py` (flag `S1_CVD_OPENING=False`)
- `detect_opening_type`: הוסף `PE=net_CVD/Σ|delta|` + DE + divergence על חלון
  הפתיחה (מ‑`v9_bars_footprint.delta`/`cumulative_delta`, **reset‑aware בתוך session**).
  מודל דו‑שלבי label_15(09:45,bias)→label_30(10:00,מחייב). priors: DRIVE
  `PE_30>0.65 & range_exp>1.0 & ¬div`; AUCTION `|net_CVD|/total_vol<0.15 & PE<0.25`;
  REJECTION_REVERSE `CVD_sign_flip & divergence בקצה`. חתימה tick‑rule/aggressor.
- gap (`_stage_a1` ~408): `gap/ATR14_**daily**`, 4 קטגוריות Tiny/Small/Medium/Large (ממד נפרד).

### S1‑daytype — `day_type/` (flag `S1_DAYTYPE_STAGING=False`, `S1_IB_WIDTH_ATR=False`)
- IB width (`classify_ib_width`+`schemas.py`): `IB_range/ATR14_**daily**` ב‑4 tiers
  צר<0.5 · נורמלי 0.5–1.0 · רחב 1.0–1.5 · קיצוני>1.5. הוסף `EXTREME` ל‑IBWidth enum
  ומפה ב‑`DECISION_MATRIX`.
- מודל מדורג: 30דק'=ראשוני(≤60%) · 60דק'(10:30)=נעילת IB+חיזוק · ולידציה מתמשכת
  (הרחב `_check_reeval`: C‑period 10:30–11:00 + עומק נסיגה <25%→החזק / ≥50%→re‑diagnose).
  **אין צ'קפוינט 90 נפרד.**
- **להשאיר:** directional_ratio, delta/width rules, הצבעות מבניות.

## 2 · תשתית ATR (חדש)
`atr_5min(period=14)` ו‑`atr_daily(period=14)` מהברים שנקלטו, מקור‑אמת. <period
ברים → `None` → fallback לסף המוחלט הישן. תעד period/timeframe/מקור.

## 2B · סדרת בדיקות — ראיית משתמש בכל מקום + טריות

### B1 · מטריצת נראות (כל מקום שהסיווג מופיע למשתמש)
`grep` לכל הצרכנים של `day_type`/`opening_type`/`ib_width`/setup, ואז אמת בכל
אחד שהערך מוצג, מרונדר, ו**זהה** בין כולם ומול ה‑DB:

| מקום (UI) | רכיב | מה לאמת |
|---|---|---|
| דאשבורד — S1 | `System1Panel` | day_type · opening_type · ib_width/class · lock_state · confidence · stage |
| דאשבורד — S2/S4 | `System2Panel`/`System4Panel` | setups + ספים יחסיים (כשהדגל on‑shadow) |
| Side panel | `DayTypePlan`/`Lens` | playbook/סוג היום תואם |
| Sidebar | `PredictionsTab`/`PredActualTab`/`StatsTab` | חיזוי מול בפועל |
| צ'ארט — S4 | `WoodiesCciPanel` | cci/swi (אנטי‑frozen‑tail §7a) |
| Layer0 | `Layer0Strip` | chop score |
| API | `/api/v9/status` (`_check_day_type`), `cockpit/systems-snapshot` | אותו lock_state/day_type חי |

**עקביות:** `day_type` ב‑`System1Panel` == `DayTypePlan` == endpoint status == שורת
`v9_day_type_history` ב‑DB — כולם זהים.

### B2 · נראות shadow‑scoring
כשהדגל ב‑shadow: ה‑label החדש נרשם **לצד** הישן (לוג/עמודת shadow) וניתן להשוות
old vs new vs EOD — **בלי** שה‑UI/playbook מושפע מהחדש. אמת ששני הערכים נראים
לצורך ההשוואה, ושההחלטה החיה עדיין על הישן.

### B3 · טריות (Recency — אסור stale)
- `latest classification ts == MAX(ts) FROM v9_day_type_history` (Quality+Recency).
- `System1Panel` מתעדכן על בר 5‑דק' (`useSystemStatePolling` 5s); רוחב IB/gap
  מתעדכנים ב‑checkpoints (30/60 דק').
- **אנטי‑frozen‑tail** (§7a): על פני ברים 5‑דק' **שונים** cci_14/swi משתנים — לא
  ערך קפוא. אסור לשנות polling intervals.
- אחרי restart‑seed: lock_state/day_type נטענים נכון (לא PENDING תקוע) — מכוסה 1.15.

### B4 · אוטומציה
`tests/v9/e2e/test_classification_visibility_freshness.py`: seed שורת day_type
ידועה → endpoint status + systems‑snapshot מחזירים אותו ערך; latest_ts==MAX(ts);
flag OFF ⇒ הסיווג זהה ל‑golden. הדבק פלט גולמי.

## 3 · מנגנון הבקרה (חובה)
1. **flags default OFF** — כבוי = הקוד הקיים בדיוק (אפס שינוי התנהגות).
2. **golden regression לפני כל שינוי:** snapshot של הפלט הנוכחי
   (`tests/v9/regression/golden/`); אחרי: flag OFF⇒זהה, flag ON⇒הבדל צפוי בלבד.
   commit golden+טסט לפני שינוי הלוגיקה. **זהו הגיבוי.**
3. **shadow‑scoring:** flag‑on במצב shadow מחשב את הסיווג החדש ו**רושם לצד הישן**
   (לוג/עמודה), **בלי לנתב להחלטה**. השוואה ל‑EOD truth לאורך soak.
4. **שינוי אחד בכל פעם** + 4 צירי UAT + report בין שלבים.
5. ATR/CVD מקור‑אמת בלבד, reset‑aware, `None` כשחסר.

## 4 · תוצרים + שערים
דוח `docs/reports/S1_S2_S3_IMPL_<date>.md`: manifest שבוצע, golden coverage,
פלט רגרסיה גולמי (off=identical / on=expected), דוגמת shadow (old vs new vs EOD).
**שער:** דגלים כבויים. הפעלה ב‑SHADOW + נעילת k = אחרי soak ~60 ימים ואישור
Michael. day_type מזין playbook → אישור מפורש לפני הפעלה.

## 5 · אסור
להתחיל לפני שפרומפט 1/2 ירוק · להפעיל flags · לנתב סיווג חדש ל‑playbook/order/risk/
sizing · לסנתז ATR/CVD · CVD חוצה session reset · לשנות %/ספירות מבניות · refactor רחב ·
sizing מבוסס‑תנודתיות/מפסק $250 (לא מאושר).

> STATUS: מימוש מאחורי flags + shadow. priors. נעילה+הפעלה אחרי soak ואישור Michael.
