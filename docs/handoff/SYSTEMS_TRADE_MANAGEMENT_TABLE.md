# MEMS26 — טבלת מערכות, כניסה, סטופ, יעדים, ניהול עסקה

> ⚠️ **DRAFT — לא מאומת.** הנתונים נלקחו מהקוד בלבד. Michael יאשר את הנתונים לפני שמשתמשים בטבלה זו לכל שינוי קוד או הוראה לסוכן.

**מטרה:** מסמך יחיד לסוכן הבא — כל מה שצריך לדעת על 6 המערכות, תבניות, כניסות, סטופים, יציאות.

---

## א. סקירת 6 המערכות

| # | שם | תפקיד | מקור נתונים | Stream |
|---|-----|--------|-------------|--------|
| S1 | Day Type | OBSERVER — מסווג יום מסחר | `volume_profile.json` | `volume_profile` |
| **S2** | Five Min | **FIRING T1** | `5min.json` | `5min` |
| **S3** | Footprint | **FIRING T3** | `footprint.json`, `tick_reversal_12/15.json` | `footprint`, `tick_reversal` |
| **S4** | Woodies CCI | **FIRING T2** | `woodies_5min.json` | `woodies_5min` |
| S5 | TPO / VP | OBSERVER — POC, VA, location | `tpo.json`, `volume_profile.json` | `tpo`, `volume_profile` |
| S6 | Killzone | GATE — חוסם כניסות מחוץ לזונות | poll ~5s | — |

**הערה:** S3 כרגע **Observer בפועל** (D-082/D-086 LOCKED — `if mode == 'LIVE': return` מונע ירי SHADOW). תוקן יהיה ב-post-SHADOW.

---

## ב. תבניות שכל מערכת מזהה

### S4 — Woodies CCI (9 תבניות)

| Pattern | קבוצה | כיוון | min bars | Tier | סטופ בדיטקטור | T1 | T2 | T3 |
|---------|--------|--------|----------|------|----------------|-----|-----|-----|
| **ZLR** | CONTINUATION | L/S | 3 | HIGH | per pattern | 1×risk | 2×risk | — |
| **TLB** | CONTINUATION | L/S | 3 | LOW | per pattern | 1×risk | 2×risk | — |
| **TT** | CONTINUATION | L/S | 3 | HIGH | per pattern | targets[] | targets[] | — |
| **GB100** | CONTINUATION | L/S | 3 | HIGH | per pattern | targets[] | targets[] | — |
| **VEGAS** | REVERSAL | L/S | **≥20** | MEDIUM | entry ±12 ticks (3 pts) | 16 ticks | 32 ticks | — |
| **GHOST** | REVERSAL | L/S | 3 | MEDIUM | per pattern | targets[] | targets[] | — |
| **FAMIR** | REVERSAL | L/S | 3 | MEDIUM | per pattern | targets[] | targets[] | — |
| **HTLB** | REVERSAL | L/S | 3 | MEDIUM | per pattern | targets[] | targets[] | — |
| **HFE** | REVERSAL | L/S | 3 | **⚠️ חסר** | per pattern | targets[] | targets[] | — |

> **HFE — שאלה פתוחה:** לא הוגדר ב-`PATTERN_TIER` → default 'low' → `sizing=reject` → לא נכנס. Michael צריך לאשר: `'high'` / `'medium'` / `'low'` / `'reject'`.

### S2 — Five Min (patterns)

| Pattern | סוג | כיוון | תנאי כניסה |
|---------|-----|--------|------------|
| REACTIVE | 4-bar seller/buyer weakness | L/S | b2_drop 90% + belly + COT > AMT |
| INITIATIVE | 4-bar expansion-test-join | L/S | b1_expansion 1.5-1.75 pts + COT < AMT |

**COT/AMT מקור (לאחר תיקון):** Sierra `cumulative_delta.json` → `cot_amt.py`

### S3 — Footprint (מצבים)

| סיווג | תנאי | ירי |
|--------|------|-----|
| T3_CLUSTER | sweep_return + volume confluence | כן (D-086 דחוי ל-post-SHADOW) |
| NO_SETUP | אין confluences | לא |

---

## ג. שערי כניסה אוטונומית

### עץ ל-S4 (A1–A7)

```
A1 Trend Gate      → GRAY/BLUE/RED/YELLOW (לא חוסם GRAY)
A2 Study Validity  → 11 studies קיימים
A3 Pattern Detect  → active_patterns לא ריק
A4 Touchpoints     → advisory only (חוסם רק אם FAIL + patterns)
A5 Sizing          → calculate_size != 'reject'
A6 Entry Class     → TACTICAL→REACTIVE / STRATEGIC→INITIATIVE
A7 Universal       → pre_fire_validator (רק אם fire_setup מוגדר)

ready_to_route = A1–A7 לא FAIL ולא PENDING + patterns + sizing != reject
```

### Gateway — שערי risk (בסדר הבדיקה)

```
1. Cooldown        → 2 הפסדות רצופות → block ~30 דק'
2. SSV             → D-049 suffering-side veto
3. Chop gate       → Layer0 chop_state == 'SEARCHING' → block
4. Cluster guard   → D-088: חוסם DEMO/LIVE (לא SHADOW!)
   ↓
   SHADOW תמיד נרשם (unlimited slots)
   DEMO — slot יחיד
   LIVE — slot יחיד + strict risk
```

**מצב נוכחי:**
- `cluster_guard: True` → DEMO/LIVE חסומים, SHADOW פעיל
- `chop_state: EXPANDING` → כניסות פתוחות
- `cooldown: False` → ירוק

---

## ד. סטופ ראשוני לפי מערכת

| מערכת | איך נקבע סטופ | דוגמה MES |
|--------|--------------|-----------|
| S4 Woodies | `PatternResult.stop` מהדיטקטור | VEGAS LONG: entry - 12 ticks (−3 pts) |
| S2 Five Min | `bar.low - 2.0` (LONG) / `bar.high + 2.0` (SHORT) | 🟡 סף לכיול ב-SHADOW |
| S3 Footprint | `min(low, entry - tick)` / `max(high, entry + tick)` | dynamic |

---

## ה. ניהול עסקה פעילה — אוטונומי

### BarLevelDetector — סדר בדיקה על כל בר 5min

```
1. STOP HIT (ראשון!)
   LONG:  bar.low  <= trade.stop → STOP_HIT → סגור
   SHORT: bar.high >= trade.stop → STOP_HIT → סגור

2. T1 HIT
   LONG:  bar.high >= trade.t1 → T1_HIT → PARTIAL + Smart-BE
   SHORT: bar.low  <= trade.t1 → T1_HIT → PARTIAL + Smart-BE

3. T2 HIT (רק אחרי T1)
   LONG:  bar.high >= trade.t2 → T2_HIT
   SHORT: bar.low  <= trade.t2 → T2_HIT

4. T3 HIT (רק אחרי T2)
   → T3_HIT → CLOSED

5. Time Stop (לפי Day Type)
6. EOD Flatten
```

### Smart Break-Even אחרי T1

```python
# TradeManager._apply_smart_be_after_t1
if T1 hit:
    quality["initial_stop"] = trade.stop  # שמור סטופ מקורי לחישוב P&L
    trade.stop = trade.entry_price         # הזז סטופ ל-entry
```

> **P&L:** `pnl_usd` מחושב על ה-entry price ו-exit price. `initial_stop` שמור ב-quality לחישוב R.

### Time Stop לפי Day Type

| Day Type | Time Stop (דקות) |
|----------|-----------------|
| TREND_NORMAL | ∞ (אין) |
| TREND_DD | 90 |
| VARIATION | 60 |
| NEUTRAL | 45 |
| NORMAL | 30 |
| NONTREND | 20 |

---

## ו. sizing — גודל פוזיציה לפי מערכת

### S4 Woodies (calculate_size)

| Tier | aux_count | trend_ok | sizing |
|------|-----------|---------|--------|
| HIGH | ≥3 | כן | full (3 contracts) |
| HIGH/MEDIUM | ≥2 | — | half (2 contracts) |
| LOW | ≥2 | — | half |
| LOW | <2 | — | **reject** |
| כל tier | <2 (HIGH/MED) | — | **reject** |

**aux_count** = SWI aligned + CZI aligned + TCCI leading (מקסימום 3)

### S2 Five Min (calculate_size)

```
full (3): 4-bar pattern + COT_AMT strong (1.2×) + location='at'
half (2): pattern + COT_AMT ok + location='near'
reject:   pattern אבל COT_AMT לא עומד
```

---

## ז. שאלות פתוחות לסוכן הבא

| # | שאלה | מי מחליט | דחיפות |
|---|------|----------|--------|
| 1 | HFE tier: high/medium/low/reject? | Michael | 🔴 לפני ירי HFE |
| 2 | S2 stop = `bar.low - 2.0` — האם 2 נקודות (8 ticks) נכון? | Michael | 🟡 לכיול ב-SHADOW |
| 3 | S3 — מתי מפעילים ירי Footprint (post-D086)? | Michael | 🟡 post-SHADOW |
| 4 | VEGAS T2=32 ticks — האם זה נכון? | Michael | 🟡 לוודא vs spec |
| 5 | S2 REACTIVE/INITIATIVE — `cot_below_amt` ל-LONG (INITIATIVE)? | Cursor | 🟡 לוודא הגיון |

---

## ח. מצב עכשיו (2026-05-22 17:00 IL)

| מערכת | מצב | last pattern | fires? |
|--------|-----|-------------|--------|
| S1 Day Type | unknown | — | לא |
| S2 Five Min | FIRST_HOUR_TACTICAL | None (buf=133) | מוכן |
| S3 Footprint | BALANCED | NO_SETUP | D-086 block |
| **S4 Woodies** | **ZLR LONG 0.9** | ZLR+GB100 | **✅ SHADOW פעיל** |
| S5 TPO | active | — | לא |
| S6 Killzone | — | — | gate בלבד |

**Trades היום:** S4 fired TM 2861/2862/2863 (VEGAS SHORT) + 2857/2858 (LONG)

---

*נוצר: 2026-05-22 17:00 IL | Cursor Agent*
