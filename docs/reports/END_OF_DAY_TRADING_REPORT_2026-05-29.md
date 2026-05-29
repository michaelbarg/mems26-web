# End of Day Trading Report · 2026-05-29

---

## 1. סיכום עסקאות

| קטגוריה | כמות | PnL |
|---------|------|-----|
| **Real S4 (Woodies)** | 12 | **+$137.50** |
| **Real S2 (5-Min)** | 1 | open |
| Noise (footprint bursts) | 550 | N/A |
| Fake entries (@5900) | 12 PARTIAL | N/A |
| **Total** | 575 | **+$137.50 net** |

### S4 Woodies Detail

| # | Mode | Dir | Entry | Stop | T1 | Exit | Reason | PnL | R |
|---|------|-----|-------|------|----|------|--------|-----|---|
| 15 | demo | SHORT | 7529.75 | 7531.00 ✅ | 7526.25 | 7531.00 | STOP_HIT | -$18.75 | -1.00 |
| 155 | shadow | LONG | 7579.00 | 7577.75 ✅ | 7582.00 | — | TIME_STOP | $0.00 | 0.00 |
| 156 | demo | LONG | 7579.00 | 7579.25 (BE+1T) | 7582.00 | 7579.25 | STOP_HIT (post T1) | +$17.50 | 0.93 |
| 536 | shadow | LONG | 7606.25 | 7604.75 ✅ | 7609.25 | 7604.75 | STOP_HIT | -$22.50 | -1.00 |
| 537 | demo | LONG | 7606.25 | 7604.75 ✅ | 7609.25 | 7604.75 | STOP_HIT | -$22.50 | -1.00 |
| 603 | shadow | LONG | 7592.25 | 7590.25 ✅ | 7595.75 | 7600.00 | TIME_STOP | **+$116.25** | **3.88** |
| 652 | shadow | LONG | 7602.75 | 7600.75 ✅ | 7605.75 | 7607.25 | TIME_STOP | **+$67.50** | **2.25** |

Shadow: +$161.25 · Demo: -$23.75

---

## 2. Stop Analysis

### כיוון Stop — ✅ תקין
11/12 trades עם stop בכיוון הנכון. ה-❌ (#156) הוא Smart BE תקין — stop זז מ-7577.75 ל-7579.25 (entry+1T) אחרי T1 hit.

### Smart BE (Breakeven + 1 Tick)
- #156: T1 hit → stop moved to 7579.25 (entry+0.25) → stop hit → PnL +$17.50
- כל שאר ה-trades: T1 **לא נרשם** → Smart BE **לא הופעל**

### Stop Risk Size
| Trades | Stop Distance | Ticks |
|--------|--------------|-------|
| #155, #15, #561, #658 | 1.25 pts | 5 ticks |
| #536, #537 | 1.50 pts | 6 ticks |
| #603, #604, #652 | 2.00 pts | 8 ticks |
| #544, #545 | 3.50 pts | 14 ticks |

ממוצע: ~1.7 pts (7 ticks). ב-MES עם ATR ~50, זה **צפוף**.

---

## 3. TIME_STOP — באגים

### Spec vs Reality

| Trade | Duration | Expected (spec=90min) | Status |
|-------|----------|----------------------|--------|
| #155 | **0.9 min** | 90 min | ❌ Bug A (push counting — fixed in code) |
| #603 | **31.9 min** | 90 min | ❌ **Still broken** |
| #652 | **59.9 min** | 90 min | ❌ **Still broken** |

### Root Cause
ה-Woodies `_bar_count` dedup (`_last_bar_ts_for_count`) משתמש ב-`bar.get("ts")`.
אבל ה-Woodies bars מגיעים עם **ts ייחודי לכל push** (ISO timestamp עם milliseconds,
e.g. `2026-05-29T15:05:33.214428+00:00`). כל push = ts חדש = bar_count +1.

954 pushes ב-32 דקות → bar_count 18 הגיע אחרי ~36 pushes ≈ ~72 שניות.

**ה-dedup ב-Woodies לא עובד** כי ה-ts של כל push שונה (milliseconds).
צריך dedup על **rounded 5-minute bar boundary** (floor to 5min), לא על ts מדויק.

### T1 Hit Not Detected
Trades #603 ו-#652 עברו את T1 (exit price > T1) אבל `t1_hit_ts` ריק.
ה-BarLevelDetector subscribes ל-`5min` (לא `woodies_5min`) — ייתכן שהוא לא
רואה את ה-bars הרלוונטיים, או שה-TZ issue גורם לו לפספס.

---

## 4. S2 (5-Min) — למה לא ירתה

### Reactive
- **b2_volume_drop**: ratio=0.727–1.37 (need ≤0.10). אף bar היום לא הראה 90% drop.
- **COT vs AMT**: COT=-4650, AMT=-5932. Reactive SHORT דורש COT<AMT — COT גבוה מ-AMT.
- Best near-miss: Reactive SHORT 5/7 conditions.

### Initiative  
- **b1_expansion**: כל bars היום range 3-18 pts. Spec דורש 1.5-1.75 pts. **0/44 bars passed**.
- Bar range ממוצע: 6.12 pts — פי 4 מהנדרש.

### Chart Patterns (H&S, Flags, Double Top)
- DOUBLE_TOP_AA_SHORT **זוהה!** (conf=0.89-0.98)
- נדחה ע"י `pre_fire_validator`: R:R < 1.0 (risk=14.38, reward=11.38)
- **המערכת עבדה נכון** — זיהתה pattern ודחתה כי הסיכון > תגמול.

---

## 5. Market Data — IB + TPO

### IB Today
| Source | High | Low | Width | Class |
|--------|------|-----|-------|-------|
| Sierra Study (during RTH) | 7611.75 | 7586.75 | 25.0 | MEDIUM |

### TPO Today (end of session)
| Metric | Value |
|--------|-------|
| **POC** | 7586.25 |
| **VAH** | 7590.25 |
| **VAL** | 7582.50 |

---

## 6. S1 (Day Type) — סיכום

- **Classification**: Normal (via INDETERMINATE opening → Decision Matrix fallback)
- **IB**: 7611.75 / 7586.75, class=MEDIUM
- **Opening type**: INDETERMINATE (backend restarted after 09:40 ET → missed detection window)
- **Confidence**: 0.68 < lock threshold 0.70 → **לא ננעל כל היום** (stage B2)

---

## 6. רעש — מה צריך לנקות לפני LIVE

| # | בעיה | כמות | עדיפות |
|---|------|------|--------|
| 1 | Footprint burst (30× trades/minute) | 550 | 🔴 CRITICAL |
| 2 | Fake PARTIAL @5900 | 12 | 🔴 מחיקה + מקור |
| 3 | TIME_STOP fires early (push counting) | 3 trades | 🔴 dedup fix |
| 4 | T1 not detected by BarLevelDetector | 2 trades | 🟡 lifecycle |
| 5 | S2 Initiative expansion threshold too narrow | 0/44 bars | 🟡 review threshold |

---

---

## 7. צ'קליסט תיקונים ושיפורים (לביצוע)

### 🔴 קריטי — לפני LIVE

| # | נושא | מערכת | תיאור | קובץ |
|---|------|-------|-------|------|
| 1 | **TIME_STOP Woodies dedup שבור** | S4 | `_last_bar_ts_for_count` משווה ts מדויק (milliseconds), כל push = ts חדש → bar_count מנופח → TIME_STOP fires ב-32 דקות במקום 90 | `woodies_system.py:207` |
| 2 | **T1 hit לא נתפס** | Trade Manager | BarLevelDetector subscribes ל-`5min` לא `woodies_5min` → לא רואה bars של S4 → T1/T2 לא נרשמים → Smart BE לא מופעל | `bar_level_detector.py:38` |
| 3 | **Footprint burst — 550 trades/יום** | S3 | אין dedup לפי (price-level + bar_ts). כל update = trade חדש. 30× באותה דקה | `footprint_system.py:426` |
| 4 | **12 fake PARTIAL @5900** | Trades | entry=5900, stop=5900.25, t1=5910 — מחירי seed/test. מקור לא מזוהה | `v9_trades` |
| 5 | **Bars 5min — פערים אחרי restart** | S2 | Bridge שולח רק latest bar. Restart מאבד history. צריך backfill מ-Sierra export | `bars_5min_stream.py:41` |
| 6 | **S1 restart מאפס state** | S1 | Restart תוך RTH = IB/opening/classification הולכים לאיבוד. seed logic לא מספיק | `state_machine.py reset()` |

### 🟡 גבוה — משפיע על דיוק

| # | נושא | מערכת | תיאור |
|---|------|-------|-------|
| 7 | **S1 confidence 0.68 < 0.70** | S1 | לא ננעל כל היום. שקול הורדת threshold ל-0.65 או forced lock מוקדם יותר |
| 8 | **Opening type = INDETERMINATE** | S1 | A2 קיבל 3 pushes ב-4 שניות (לא 3 bars אמיתיים). dedup per-system בA2 |
| 9 | **v9_five_min_state ריקה** | S2 | המערכת קוראת אבל לא כותבת. Frontend/status רואה ריק |
| 10 | **Stop risk 5-8 ticks** | S4 | צפוף ל-MES עם ATR ~50. שקול ATR-based stop |

### 🟢 שיפורים — איכות חיים

| # | נושא | תיאור |
|---|------|-------|
| 11 | **S2 Initiative threshold [1.5-1.75]** | 0/44 bars עברו. Average range=6.12. צריך התאמה ל-MES |
| 12 | **S2 Reactive 90% vol drop** | קורה 2% מהזמן. שקול 80% |

---

## 7b. מחקר Thresholds קבועים → יחסיים (לפני Shadow הבא)

### שלושה thresholds ב-S2 שבנויים על מספרים קבועים (נקודות) במקום יחסיים:

#### 1. `EXPANSION_MIN_PT = 1.5` / `EXPANSION_MAX_PT = 1.75` (Initiative)
- **מה זה:** טווח range של Bar 1 ב-Initiative pattern (6-7 ticks MES)
- **למה בעייתי:** קבוע — לא מתאים ליום volatile (ATR 80) או שקט (ATR 30)
- **היום:** 0/44 bars עברו. ממוצע range=6.12 pts, פי 4 מהנדרש
- **🔬 מחקר נדרש:** 
  - חישוב ATR-5min היומי על 30 ימות מסחר אחרונים
  - מציאת ratio: `expansion_range / ATR_5min` שנותן ~1.5 pts ב-ATR רגיל
  - המרה: `EXPANSION_MIN = ATR_5min × 0.25` / `MAX = ATR_5min × 0.30` (לדוגמה)
  - בדיקה: כמה bars/יום היו עוברים עם threshold יחסי vs קבוע

#### 2. `POC_RETURN_TOLERANCE_PT = 0.5` (Initiative b2 POC return)
- **מה זה:** מרחק מקסימלי מ-POC שנחשב "חזרה ל-POC" (2 ticks)
- **למה בעייתי:** ביום volatile, 0.5 pts הוא כלום. ביום שקט — הרבה
- **🔬 מחקר נדרש:**
  - חישוב average bar range של 5-min bars
  - המרה: `POC_TOLERANCE = avg_bar_range × 0.15` (לדוגמה)
  - בדיקה: כמה Initiative setups היו מזוהים עם tolerance יחסי

#### 3. `DROP_THRESHOLD_PCT = 0.10` (Reactive 90% vol drop)
- **מה זה:** Bar 2 volume ≤ 10% של Bar 1 — **כבר יחסי** אבל אולי **קיצוני מדי**
- **היום:** 2% מהבarים עוברים. Closest ratio=0.15 (85% drop)
- **🔬 מחקר נדרש:**
  - סטטיסטיקה על 30 יום: כמה bars עוברים ב-10%, 15%, 20%, 25%
  - בכמה מהם ה-pattern המלא (b1→b4) היה מתקיים
  - מציאת sweet spot בין סלקטיביות (פחות false positives) לבין יכולת ירי

### דרך ביצוע המחקר (מחר)
```bash
# 1. ATR-5min על 30 יום
sqlite3 data/mems26_local.db "
  SELECT date(ts) as day, 
         AVG(high-low) as avg_range,
         COUNT(*) as bars
  FROM v9_bars_5min 
  WHERE symbol='MES' AND ts > datetime('now','-30 days')
  GROUP BY date(ts) ORDER BY day DESC LIMIT 30
"

# 2. Volume drop distribution (30 יום)
# כמה bars עם drop ≤10%, ≤15%, ≤20%, ≤25%?

# 3. Backtest Initiative עם threshold יחסי
# כמה setups היו מזוהים עם expansion = ATR×0.25-0.30?
```
| 13 | **Frontend polling 15s → 5s** | `WoodiesCciPanel.tsx:1107` — CLAUDE.md floor הוא 5s |
| 14 | **pnl_r חישוב UI** | DB=1.5R, UI=60R — באג תצוגה |
| 15 | **Demo trades open לא נסגרים** | #604 עדיין OPEN — BarLevelDetector לא מנהל demo |

---

## 8. נתוני טרום מסחר (Pre-Market) — מה חסר

### מה Sierra מספקת pre-RTH (Globex)
| נתון | זמין? | מקור | שימוש |
|------|-------|------|-------|
| Globex High/Low | ✅ | `tpo.json` session block | S1 A1 pre-open context |
| Previous Day POC/VAH/VAL | ✅ | `tpo.json` prior_day block | S1 A1 + key_levels |
| Previous Day High/Low/Close | ✅ | `prev_day.py` | S1 opening detection |
| Overnight volume profile | ✅ | `volume_profile.json` | לא מנוצל |
| **Globex CCI** | ❌ | Woodies chart = RTH only | CCI לא מחושב pre-RTH |
| **Pre-market imbalances** | ✅ | `imbalance_flags.json` | S3 footprint — אבל לא מסונן ל-RTH |
| **Yesterday IB** | ⚠️ | DLL Input 19 (לא מחובר) | key_levels prev_day |

### מה צריך לבנות
1. **Pre-RTH dashboard strip** — Globex H/L + PD POC/VAH/VAL + overnight range
2. **Gap analysis** — Open vs PD close, Open vs PD POC
3. **Overnight activity bias** — volume profile shape pre-RTH
4. **Session context for S1** — feed A1 stage with pre-open data (כבר חלקית מחובר)

---

## 9. מערכת 3 (Footprint/Imbalance) — מה חסר

### מה קיים
- `footprint_system.py` — מזהה imbalance levels, fires ל-gateway
- Bridge streams: `footprint.json`, `tick_reversal_12/15.json`, `imbalance_flags.json`, `stacked_imbalances.json`
- DB: `v9_bars_footprint` (615K rows), `v9_bars_tick_reversal` (16M rows)
- COT/AMT provider — מזין S2

### מה חסר (אין "עץ החלטות")
| # | חוסר | השפעה | עדיפות |
|---|------|-------|--------|
| 1 | **אין Decision Tree** | S3 fires כל imbalance ללא filtering → 550 trades רעש/יום | 🔴 |
| 2 | **אין dedup per-level** | אותה רמה fires 30× בדקה | 🔴 |
| 3 | **אין RTH gate** | fires גם ב-overnight (06:xx, 18:xx) | 🔴 |
| 4 | **אין sizing logic** | כל fire = אותו size, בלי alignment check | 🟡 |
| 5 | **אין anti-patterns** | S4 יש AP1-AP9, S3 אין שום AP | 🟡 |
| 6 | **אין pattern spec** | אין מסמך שמגדיר מתי imbalance = setup אמיתי vs רעש | 🔴 |
| 7 | **COT/AMT quality** | S3 מספק COT/AMT ל-S2, אבל הערכים random-like (footprint_system.py:41-43) | 🔴 |
| 8 | **`v9_footprint_signals` לא קיים** | אין טבלת signals נפרדת — fires ישירות ל-gateway | 🟡 |
| 9 | **tick_reversal TZ shift +6h** | ts עתידי ב-DB (bridge TZ fix לא applied on this stream) | 🟡 |
| 10 | **אין tests** | `tests/v9/systems/footprint/` לא קיים | 🟡 |

### מה צריך לבנות (עץ S3)
1. **Pattern spec** — מתי stacked imbalance = actionable setup
2. **Decision tree stages** — A1 (market context) → A2 (level detection) → A3 (confirmation) → fire
3. **Dedup** — per (price_level, bar_ts, direction)
4. **RTH gate** — F17-style כמו ב-Woodies
5. **COT/AMT provider fix** — ערכים אמיתיים מ-cumulative_delta, לא random
6. **Regression tests**

---

## 10. Open Issues for Tomorrow

1. **TIME_STOP Woodies dedup** — needs 5min-boundary rounding, not exact ts
2. **BarLevelDetector T1 detection** — subscribes to 5min, not woodies_5min
3. **Footprint dedup** — add per-level per-bar gate
4. **S2 thresholds** — Initiative expansion [1.5-1.75] unreachable with current MES ATR
5. **S1 confidence** — 0.68 < 0.70 → never locks. Consider lowering threshold or forcing earlier lock
