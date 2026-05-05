# MEMS26 — Day-Type Adaptive Logic Spec V3.1

**Version:** V3.1 — supersedes V2.0 from 1/5/2026
**Date locked:** 5 May 2026 EOD
**Status:** 📋 Spec ready → Phase 3.3 implementation (8-10 May)
**Includes:** 3 critique patches integrated (hysteresis bypass / rollover / timeout)
**LIVE target:** 21 May 2026

---

## 📑 Table of Contents

1. [Vision & Strategic Context](#1-vision)
2. [Architectural Changes vs V2](#2-changes)
3. [The 6 Day Types — Full Spec](#3-types)
4. [Detection Pseudocode](#4-detection)
5. [Hysteresis State Machine](#5-hysteresis)
6. [Time Phase Filter](#6-phase)
7. [News Filter 3-Tier](#7-news)
8. [Special Days Protocol](#8-special)
9. [Smart Entry Mechanism](#9-entry)
10. [Backend Mapping (Phase 3.3)](#10-backend)
11. [Acceptance Criteria](#11-acceptance)
12. [Open Questions for Day 3-5](#12-open)

---

<a name="1-vision"></a>
## 1. Vision & Strategic Context

> **"מערכת שמצליחה למקסם יום מסחר ולהגיע להום ראן /
>  לזהות סוג יום ולמצות אותו עד תום"**

The system must:
1. Identify the kind of trading day in real time
2. Adapt its strategy (entry, sizing, targets, BE timing) per day type
3. Filter out periods/days where no edge exists
4. Maximize good days, protect capital on bad days

V2 had 5 day types but no playbook differentiation in production code.
V3.1 has 6 day types, each with its own playbook (see `MEMS26_PLAYBOOKS_V1.md`).

---

<a name="2-changes"></a>
## 2. Architectural Changes vs V2

| # | Change | Reason |
|---|--------|--------|
| 1 | DEVELOPING removed from Day Types → Time Phase Filter | Day 2 finding: -11.2pp WR is a **time** effect, not type-specific |
| 2 | NORMAL renamed → BROAD_CHANNEL with new playbook | Differentiated mid-volatility days from default fallback |
| 3 | GAP_FILL min size: 5pt → 20pt MES | 5pt gaps are noise; real institutional gaps are ≥20pt |
| 4 | REVERSAL_DAY added as 6th type | V-shape days are highly lucrative but missed by V2 |
| 5 | News Filter system (3 tiers) | Granular blocking: high-impact ±15min vs medium ±5min vs low log-only |
| 6 | Special Days protocol (Friday PM, holidays, rollover) | LIVE 21/5 + June rollover 11-18 = 2-3 days post-LIVE |
| 7 | Smart Entry: POC of footprint + imbalance | Better fills than fixed limit at signal price |
| 8 | Hysteresis state machine | Prevent flip-flopping between types within same day |
| 9 | Patch 1: REVERSAL bypass | Standard +15 conf rule blocks legitimate TREND→REVERSAL |
| 10 | Patch 2: Rollover periods | June 11-18 rollover = 2-3 days after LIVE |
| 11 | Patch 3: Smart Entry timeout enforcement | Never market-chase after limit timeout |

---

<a name="3-types"></a>
## 3. The 6 Day Types — Full Spec

### 3.1 Quick Reference Table

| Day Type | Detection Core | Sizing | T1 | T2 | T3 | BE | Stop |
|----------|---------------|--------|-----|-----|-----|-----|------|
| 🟢 TREND_DAY | flips≤2, IB held, range>0.7×ATR | 3 | +1R | max(3R, TPO_VAH) | Vegas trail | After T2 | 5pt |
| 🔵 BROAD_CHANNEL | IB 0.5-1.0×ATR, flips≤3 | 2 | +1R | VWAP/POC cap 2.5R | OFF | After T1 | 5pt |
| 🟦 RANGE | flips≥4, IB>1.2×ATR | 2 | +1R | VWAP/VPOC cap 2R | OFF | After T1 | 5pt |
| 🟣 GAP_FILL | gap>20pt + reverting to PDC | 3 | +1R | PDC cap 6R | Vegas trail | After T2 | 5pt |
| 🟡 REVERSAL_DAY | V-shape + range>1.0×ATR + vol burst | 2 | +1R | open_price level | Vegas trail | After T2 | 7pt |
| 🟠 NEUTRAL | IB failed both sides + flips≥6 | 0/1 | +1R | — | OFF | n/a | 5pt |

### 3.2 🟢 TREND_DAY

**Detection:**
```
vegas_flips_today <= 2
AND ib_break_held = true                  (broke and held 5+ min)
AND day_range > atr_baseline * 0.7
```
**Confidence:** `min(1.0, day_range / atr_baseline)`
**Tie-break priority:** 3rd (after GAP_FILL, REVERSAL_DAY)

**Why this works (Hebrew):**
> 🇮🇱 יום מגמתי = הזדמנות החודש. IB צר ונשבר → המוסדיים מחויבים לכיוון. אסור לחתוך את הrunner; T3 trail על Vegas EMA169 עד הסוף.

### 3.3 🔵 BROAD_CHANNEL (renamed from V2 NORMAL)

**Detection:**
```
atr_baseline * 0.5 <= ib_range <= atr_baseline * 1.0
AND vegas_flips_today <= 3
AND day_range / atr_baseline between 0.7 and 1.2
```
**Confidence:** `0.4 + 0.1 * vegas_flips_today` (clamped 0..1)
**Tie-break priority:** 4th

**Why renamed?**
- V2 NORMAL was a catch-all bucket with no differentiated play
- BROAD_CHANNEL has a specific playbook: fade only at edges, no runner
- Mid-channel volatility is real and tradeable when you stay disciplined

**Why this works (Hebrew):**
> 🇮🇱 ערוץ רחב = שוק שלא יודע לאן ללכת. אסור לחפש "המהלך הגדול" — הוא לא בא. רק מהקצוות, חצי גודל, אין runner. 4-5 trades של 1R+2.5R = $350-$430 ביום bread-and-butter.

### 3.4 🟦 RANGE (V2 unchanged)

**Detection:**
```
vegas_flips_today >= 4
AND ib_range > atr_baseline * 1.2
AND no_range_extension_held = true
```
**Confidence:** `min(1.0, vegas_flips / 6.0)`
**Tie-break priority:** 5th

**Why this works (Hebrew):**
> 🇮🇱 RANGE = כל breakout נכשל. סוחרים רק קצוות, רק לכיוון VWAP, חצי גודל, T2 הדוק (2R cap), אין T3.

### 3.5 🟣 GAP_FILL (V3 patch — min 20pt)

**Detection:**
```
abs(open_price - prior_day_close) > 20pt MES   ← was 5pt in V2
AND moving_to_pdc = true                        (price reverting toward gap)
```
**Confidence:** `min(1.0, gap_size / 30.0)`
**Tie-break priority:** 1st (highest — structural morning event)

**Why min 20pt?**
- Gaps under 20pt MES are typically overnight noise
- Real institutional gap-and-go (or gap-and-fill) requires >20pt commitment
- Tighter threshold reduces false positives in pre-market drift

**Why this works (Hebrew):**
> 🇮🇱 Gap מעל 20pt = אירוע מוסדי. PDC הוא target ידוע — הסיכוי ש-fill קורה תוך 90 דקות גבוה. T2 רחב (6R cap) כי PDC רחוק. T3 trail לdouble-fill ימים.

### 3.6 🟡 REVERSAL_DAY (NEW — V-shape detection)

**Detection:**
```
first_90min_direction != current_direction
AND day_range > atr_baseline * 1.0
AND price has crossed back through open_price (V or inverted-V)
AND volume_burst_at_reversal_ratio >= 1.5
```
**Confidence:** `pct_reversed_from_extreme` (0..100, normalized 0..1)
**Tie-break priority:** 2nd (after GAP_FILL — afternoon structural event)
**Special:** Patch 1 hysteresis bypass (TREND→REVERSAL allowed at conf ≥ 60)

**Why include this?**
- V-shape days are 5-10% of trading days but produce 8R+ moves
- V2 mis-classified them as TREND, then C3 trail killed the runner
- Catching reversal early = 2× the daily PnL

**Why this works (Hebrew):**
> 🇮🇱 REVERSAL_DAY = יום שבו ה-trend הראשוני התעייף. כל מי שב-trend morning תפוס. אנחנו לא מנסים לתפוס לפני — אנחנו מחכים שהמחיר חוצה את open_price ונכנסים בכיוון החדש. סטופ רחב יותר (7pt) כי תנודתיות גבוהה.

### 3.7 🟠 NEUTRAL (V2 unchanged)

**Detection:**
```
ib_break_direction != NONE
AND ib_break_failed_count >= 2     (failed BOTH sides)
AND vegas_flips_today >= 6
AND abs(close_to_mid_ratio) < 0.2
```
**Confidence:** `min(1.0, ib_break_failed_count / 2.0)`
**Tie-break priority:** 6th (last resort)

**Why skip in LIVE?**
- NEUTRAL = no edge. Whipsaw maximum. Score Delta < 5pp between LONG/SHORT
- Capital preservation > clever trading
- Shadow mode (1 ctr, T1 only) keeps data flowing without risk

---

<a name="4-detection"></a>
## 4. Detection Pseudocode

```python
from dataclasses import dataclass
from enum import Enum
from typing import Tuple

class DayType(Enum):
    TREND_DAY = "TREND_DAY"
    BROAD_CHANNEL = "BROAD_CHANNEL"
    RANGE = "RANGE"
    GAP_FILL = "GAP_FILL"
    REVERSAL_DAY = "REVERSAL_DAY"
    NEUTRAL = "NEUTRAL"
    UNKNOWN = "UNKNOWN"

@dataclass
class MarketSnapshot:
    timestamp: datetime
    open_price: float
    prior_day_close: float
    current_price: float
    day_high: float
    day_low: float
    ib_high: float
    ib_low: float
    ib_break_direction: str          # "UP" / "DOWN" / "NONE"
    ib_break_held: bool
    ib_break_failed_count: int
    vegas_flips_today: int
    atr_baseline: float
    first_90min_direction: str       # "UP" / "DOWN" / "NONE"
    volume_burst_ratio: float        # vs avg

class DayClassifier:
    def __init__(self):
        self.current_type: DayType = DayType.UNKNOWN
        self.current_confidence: float = 0.0
        self.last_switch_ts = None
        self.cooldown_seconds = 30 * 60  # 30 min
    
    def update(self, snapshot: MarketSnapshot) -> Tuple[DayType, float]:
        # Run all detectors, get candidates
        candidates = []
        for detector in [
            self._detect_gap_fill,    # priority 1
            self._detect_reversal,     # priority 2 (with Patch 1 bypass)
            self._detect_trend,        # priority 3
            self._detect_broad_channel,# priority 4
            self._detect_range,        # priority 5
            self._detect_neutral,      # priority 6
        ]:
            is_match, conf = detector(snapshot)
            if is_match:
                candidates.append((detector.__name__, conf))
        
        if not candidates:
            return (DayType.UNKNOWN, 0.0)
        
        # Pick highest confidence (priority order is detector list order)
        best_name, best_conf = max(candidates, key=lambda x: x[1])
        new_type = self._name_to_type(best_name)
        
        # Apply Patch 1: REVERSAL bypass
        if (self.current_type == DayType.TREND_DAY 
            and new_type == DayType.REVERSAL_DAY 
            and best_conf >= 0.60):
            self.current_type = DayType.REVERSAL_DAY
            self.current_confidence = best_conf
            self.last_switch_ts = snapshot.timestamp
            return (DayType.REVERSAL_DAY, best_conf)
        
        # Standard hysteresis
        return self._apply_hysteresis(new_type, best_conf, snapshot.timestamp)
    
    def _detect_trend(self, s: MarketSnapshot) -> Tuple[bool, float]:
        if (s.vegas_flips_today <= 2
            and s.ib_break_held
            and (s.day_high - s.day_low) > s.atr_baseline * 0.7):
            conf = min(1.0, (s.day_high - s.day_low) / s.atr_baseline)
            return (True, conf)
        return (False, 0.0)
    
    def _detect_broad_channel(self, s: MarketSnapshot) -> Tuple[bool, float]:
        ib_range = s.ib_high - s.ib_low
        day_range = s.day_high - s.day_low
        if (s.atr_baseline * 0.5 <= ib_range <= s.atr_baseline * 1.0
            and s.vegas_flips_today <= 3
            and 0.7 <= day_range / s.atr_baseline <= 1.2):
            conf = 0.4 + 0.1 * s.vegas_flips_today
            return (True, min(1.0, conf))
        return (False, 0.0)
    
    def _detect_range(self, s: MarketSnapshot) -> Tuple[bool, float]:
        ib_range = s.ib_high - s.ib_low
        if (s.vegas_flips_today >= 4
            and ib_range > s.atr_baseline * 1.2):
            conf = min(1.0, s.vegas_flips_today / 6.0)
            return (True, conf)
        return (False, 0.0)
    
    def _detect_gap_fill(self, s: MarketSnapshot) -> Tuple[bool, float]:
        gap = abs(s.open_price - s.prior_day_close)
        moving_to_pdc = (
            (s.open_price > s.prior_day_close and s.current_price < s.open_price)
            or
            (s.open_price < s.prior_day_close and s.current_price > s.open_price)
        )
        if gap > 20.0 and moving_to_pdc:
            conf = min(1.0, gap / 30.0)
            return (True, conf)
        return (False, 0.0)
    
    def _detect_reversal(self, s: MarketSnapshot) -> Tuple[bool, float]:
        # Determine current direction (last 30min net)
        current_direction = "UP" if s.current_price > s.open_price else "DOWN"
        crossed_open = (
            (s.first_90min_direction == "UP" and s.current_price < s.open_price)
            or
            (s.first_90min_direction == "DOWN" and s.current_price > s.open_price)
        )
        if (s.first_90min_direction != current_direction
            and (s.day_high - s.day_low) > s.atr_baseline * 1.0
            and crossed_open
            and s.volume_burst_ratio >= 1.5):
            # Confidence = % reversal from extreme
            extreme_distance = max(
                abs(s.day_high - s.open_price),
                abs(s.day_low - s.open_price)
            )
            current_distance = abs(s.current_price - s.open_price)
            conf = min(1.0, current_distance / extreme_distance) if extreme_distance > 0 else 0.5
            return (True, conf)
        return (False, 0.0)
    
    def _detect_neutral(self, s: MarketSnapshot) -> Tuple[bool, float]:
        mid = (s.day_high + s.day_low) / 2
        close_to_mid_ratio = (s.current_price - mid) / (s.day_high - s.day_low + 0.001)
        if (s.ib_break_direction != "NONE"
            and s.ib_break_failed_count >= 2
            and s.vegas_flips_today >= 6
            and abs(close_to_mid_ratio) < 0.2):
            conf = min(1.0, s.ib_break_failed_count / 2.0)
            return (True, conf)
        return (False, 0.0)
    
    def _apply_hysteresis(self, new_type: DayType, new_conf: float, now) -> Tuple[DayType, float]:
        if self.current_type == DayType.UNKNOWN:
            self.current_type = new_type
            self.current_confidence = new_conf
            self.last_switch_ts = now
            return (new_type, new_conf)
        
        if new_type == self.current_type:
            self.current_confidence = max(self.current_confidence, new_conf)
            return (self.current_type, self.current_confidence)
        
        # Different type — check hysteresis
        elapsed = (now - self.last_switch_ts).total_seconds() if self.last_switch_ts else 999999
        if elapsed < self.cooldown_seconds:
            return (self.current_type, self.current_confidence)
        
        if new_conf >= self.current_confidence + 0.15:  # +15pp
            self.current_type = new_type
            self.current_confidence = new_conf
            self.last_switch_ts = now
            return (new_type, new_conf)
        
        return (self.current_type, self.current_confidence)
    
    def _name_to_type(self, name: str) -> DayType:
        mapping = {
            '_detect_trend': DayType.TREND_DAY,
            '_detect_broad_channel': DayType.BROAD_CHANNEL,
            '_detect_range': DayType.RANGE,
            '_detect_gap_fill': DayType.GAP_FILL,
            '_detect_reversal': DayType.REVERSAL_DAY,
            '_detect_neutral': DayType.NEUTRAL,
        }
        return mapping.get(name, DayType.UNKNOWN)
```

---

<a name="5-hysteresis"></a>
## 5. Hysteresis State Machine

### 5.1 Standard Rule

Switch from `current_type` to `new_type` ONLY if:
1. `new_confidence >= current_confidence + 0.15` (15 percentage points), AND
2. At least 30 minutes elapsed since last switch (cooldown)

### 5.2 Patch 1 — REVERSAL_DAY Bypass

```python
if (current_type == TREND_DAY 
    and new_type == REVERSAL_DAY 
    and new_confidence >= 0.60):
    # Natural transition — no +15 requirement, no cooldown
    switch_immediately()
```

**Why:** A genuine V-shape reversal cannot wait for cooldown. By the time +15 confidence builds, the runner is dead.

### 5.3 Mermaid State Diagram

```
                ┌──────────┐
                │ UNKNOWN  │
                └─────┬────┘
                      │ first detection
                      ↓
        ┌─────────────────────────────┐
        │    Active classification    │
        │  (any of 6 types)           │
        └─────┬───────────────────────┘
              │
              ├─► same type, higher conf → update conf
              │
              ├─► different type, +15 conf, cooldown done → switch
              │
              └─► TREND→REVERSAL @ ≥60% → BYPASS, switch immediately
```

---

<a name="6-phase"></a>
## 6. Time Phase Filter (replaces V2 DEVELOPING)

V2 had DEVELOPING as a day type. V3 promotes it to a separate **time phase filter** because Day 2 data validated:
- DEVELOPING (09:30-11:00 ET) phase WR = 37.1%
- All other phases = 48.3%
- Edge = -11.2pp regardless of day type

### 6.1 Phase Definitions

| Phase | Time (ET) | Status |
|-------|-----------|--------|
| PREMARKET | before 09:30 | log-only (no LIVE trades) |
| **DEVELOPING** | 09:30 - 11:00 | **SKIP in LIVE** (universal filter) |
| RTH | 11:00 - 14:30 | normal trading |
| LATE_DAY | 14:30 - 16:00 | half size (Friday) or normal |
| OFF_HOURS | after 16:00 | log-only (no LIVE trades) |

### 6.2 CFG-α Recommendation

CFG-α (LIVE candidate) should skip BOTH:
- OFF_HOURS (current spec)
- DEVELOPING (Day 2 finding)

**Net trade count impact:** ~25% reduction in setups.
**Net WR impact:** estimated +5-7pp improvement (need Day 3-5 to validate).

### 6.3 Future Work

Per-phase modifiers per day type:
- TREND_DAY in LATE_DAY: maybe tighter T2 cap?
- RANGE in DEVELOPING: skip universally (already covered)
- REVERSAL_DAY: most happen in LATE_DAY phase — boost confidence?

These are open questions for Phase 3.4+.

---

<a name="7-news"></a>
## 7. News Filter 3-Tier

### 7.1 Tier Definitions

| Tier | Events | Block Window | Action |
|------|--------|--------------|--------|
| **Tier 1 — HIGH** | FOMC, NFP, CPI | ±15 min | hard skip |
| **Tier 2 — MEDIUM** | GDP, PPI, Retail Sales | ±5 min | hard skip |
| **Tier 3 — LOW** | Housing, Sentiment, Consumer Conf | — | log only |

### 7.2 Data Source

ForexFactory calendar JSON cached daily at 00:00 IDT to:
```
data/news_calendar_<YYYY-MM-DD>.json
```

### 7.3 Backend Integration

```python
def is_news_blackout(timestamp, calendar) -> Tuple[bool, int]:
    """Returns (is_blocked, tier_int)"""
    for event in calendar.get('events', []):
        delta_min = abs((timestamp - event['time']).total_seconds()) / 60
        if event['tier'] == 1 and delta_min <= 15:
            return (True, 1)
        if event['tier'] == 2 and delta_min <= 5:
            return (True, 2)
        if event['tier'] == 3:
            return (False, 3)  # log only
    return (False, 0)
```

### 7.4 Setup Field

Add `news_tier_v3` to setup record (int 0/1/2/3, default 0).

---

<a name="8-special"></a>
## 8. Special Days Protocol

### 8.1 Friday Late (After 14:00 ET)

**Behavior:** Half size (`Tier-H` 2 contracts) regardless of score
**Reason:** Weekend risk — institutional flows wind down, gap risk over weekend
**Override:** None — if score ≥ 80, still half size

### 8.2 Pre-Holiday Early Close

**Behavior:** SKIP entirely (no trading)
**Reason:** Half-day sessions have unreliable volume profile, distorted TPO
**Source:** CME early-close calendar (cached daily)

### 8.3 Year-End Window (22 Dec - 2 Jan)

**Behavior:** SKIP entirely
**Reason:** Tax-related flows distort price action, low volume regime
**Configurable:** Set in `SPECIAL_DAYS_2026` constant

### 8.4 Patch 2 — MES Rollover Periods

```python
ROLLOVER_PERIODS_2026 = [
    {"start": "2026-03-12", "end": "2026-03-19"},  # March
    {"start": "2026-06-11", "end": "2026-06-18"},  # June ⚠️ 2-3d AFTER LIVE!
    {"start": "2026-09-10", "end": "2026-09-17"},  # September
    {"start": "2026-12-10", "end": "2026-12-17"},  # December
]
```

**Behavior:** SKIP entirely during rollover windows
**Reason:** Liquidity migrating from old to new contract, distorted depth
**Critical:** June rollover starts **2-3 days after LIVE 21/5** — this WILL affect us in week 1

### 8.5 Implementation

```python
def is_special_day_block(today: date) -> Tuple[bool, str]:
    """Returns (is_blocked, reason_string)"""
    
    # Friday late
    if today.weekday() == 4:  # Friday
        return (True, "friday_late")  # half size, not full block — handle in sizing
    
    # Year-end
    if (today.month == 12 and today.day >= 22) or (today.month == 1 and today.day <= 2):
        return (True, "year_end")
    
    # Rollover periods
    for window in ROLLOVER_PERIODS_2026:
        start = date.fromisoformat(window['start'])
        end = date.fromisoformat(window['end'])
        if start <= today <= end:
            return (True, "rollover")
    
    # Holiday early-close (placeholder — implement with CME calendar)
    # if today in CME_EARLY_CLOSE_2026:
    #     return (True, "early_close")
    
    return (False, "")
```

---

<a name="9-entry"></a>
## 9. Smart Entry Mechanism

V2 used fixed limit at signal price. V3 introduces Smart Entry: enter at the POC (Point of Control) of the last footprint bar at signal trigger, with imbalance check.

### 9.1 Entry Price Calculation

```
1. At signal trigger, identify last completed footprint bar (1m or 3m TF)
2. Find POC = price level with highest volume in that bar
3. Set entry_price = POC (LONG) or POC (SHORT, same — direction doesn't change POC)
4. Check imbalance: bid/ask ratio at entry_price ≥ 200% in setup direction
5. If imbalance check fails → REJECT setup (don't place order)
6. Place limit order at entry_price
```

### 9.2 Patch 3 — Timeout Enforcement

```python
def on_order_timeout(order):
    if order.elapsed_seconds >= order.timeout_seconds:
        order.status = "MISSED_TIMEOUT"  # NOT "CHASED"
        log_setup_status(order.setup_id, "MISSED_TIMEOUT")
        # Setup is dead. Wait for next opportunity.
        # NEVER convert to market order.
```

**Per-day-type timeout:**
- TREND_DAY, GAP_FILL, REVERSAL_DAY: 90 seconds (Smart Entry)
- BROAD_CHANNEL, RANGE: 60 seconds (Limit at edge)
- NEUTRAL: N/A (no entries in LIVE)

### 9.3 Why POC over fixed limit?

- Fixed limit at signal price often misses fills (price moves while order resting)
- POC is the price where most volume traded — strong magnet
- Imbalance check filters out fake signals (no institutional flow)
- Day 1 estimate: 80% fill rate vs 60% with fixed limit

---

<a name="10-backend"></a>
## 10. Backend Mapping (Phase 3.3)

### 10.1 day_config.py rewrite

```python
DAY_CONFIGS = {
    "TREND_DAY": {
        "sizing": {"score_70_plus": 3, "score_50_69": 0, "below_50": 0},
        "entry_filter": "trend_continuation_only",
        "entry_method": "smart_poc",
        "entry_timeout_sec": 90,
        "stop_pts": 5.0,
        "targets": {
            "t1_mode": "fixed_R", "t1_R": 1.0,
            "t2_mode": "max_R_or_TPO_VAH", "t2_R_min": 3.0, "t2_cap_R": 4.0,
            "t3_mode": "vegas_trail",
        },
        "be": {"trigger": "on_t2_fill"},
        "weights": {"vegas": 35, "tpo": 20, "fvg": 25, "footprint": 20},
    },
    "BROAD_CHANNEL": {
        "sizing": {"score_70_plus": 2, "score_50_69": 0, "below_50": 0},
        "entry_filter": "fade_extremes_only",
        "entry_method": "limit_at_edge",
        "entry_timeout_sec": 60,
        "stop_pts": 5.0,
        "targets": {
            "t1_mode": "fixed_R", "t1_R": 1.0,
            "t2_mode": "vwap_or_poc", "t2_cap_R": 2.5,
            "t3_mode": "off",
        },
        "be": {"trigger": "on_t1_fill"},
        "weights": {"vegas": 25, "tpo": 30, "fvg": 25, "footprint": 20},
    },
    "RANGE": {
        "sizing": {"score_70_plus": 2, "score_50_69": 0, "below_50": 0},
        "entry_filter": "fade_extremes_only",
        "entry_method": "limit_at_edge",
        "entry_timeout_sec": 60,
        "stop_pts": 5.0,
        "targets": {
            "t1_mode": "fixed_R", "t1_R": 1.0,
            "t2_mode": "vwap_or_vpoc", "t2_cap_R": 2.0,
            "t3_mode": "off",
        },
        "be": {"trigger": "on_t1_fill"},
        "weights": {"vegas": 15, "tpo": 35, "fvg": 25, "footprint": 25},
    },
    "GAP_FILL": {
        "sizing": {"score_70_plus": 3, "score_50_69": 0, "below_50": 0},
        "entry_filter": "reversal_to_pdc_only",
        "entry_method": "smart_poc",
        "entry_timeout_sec": 90,
        "stop_pts": 5.0,
        "targets": {
            "t1_mode": "fixed_R", "t1_R": 1.0,
            "t2_mode": "pdc_price", "t2_cap_R": 6.0,
            "t3_mode": "vegas_trail",
        },
        "be": {"trigger": "on_t2_fill"},
        "weights": {"vegas": 20, "tpo": 30, "fvg": 30, "footprint": 20},
    },
    "REVERSAL_DAY": {
        "sizing": {"score_70_plus": 2, "score_50_69": 0, "below_50": 0},
        "entry_filter": "reversal_direction_only",
        "entry_method": "smart_poc",
        "entry_timeout_sec": 90,
        "stop_pts": 7.0,                          # WIDER
        "targets": {
            "t1_mode": "fixed_R", "t1_R": 1.0,
            "t2_mode": "open_price_level", "t2_cap_R": 4.0,
            "t3_mode": "vegas_trail",
        },
        "be": {"trigger": "on_t2_fill"},
        "weights": {"vegas": 25, "tpo": 25, "fvg": 25, "footprint": 25},
    },
    "NEUTRAL": {
        "sizing": {"score_70_plus": 0, "score_50_69": 0, "below_50": 0},
        "shadow_only": {"min_score": 80, "qty": 1},
        "entry_filter": "skip_all",
        "entry_method": "n/a",
        "stop_pts": 5.0,
        "targets": {"t1_mode": "fixed_R", "t1_R": 1.0},
        "be": {"trigger": "n/a"},
        "weights": {"vegas": 25, "tpo": 25, "fvg": 25, "footprint": 25},
    },
}
```

### 10.2 New Functions Required

```python
def apply_universal_filters(setup, market_data) -> Tuple[bool, str]:
    """Returns (allow, reject_reason)"""
    if setup.score < 70:
        return (False, "score_below_70")
    if is_off_hours(setup.timestamp):
        return (False, "off_hours")
    if is_developing_phase(setup.timestamp):
        return (False, "developing_phase")
    is_blocked, reason = is_special_day_block(setup.timestamp.date())
    if is_blocked and reason != "friday_late":
        return (False, reason)
    is_news, tier = is_news_blackout(setup.timestamp, calendar)
    if is_news:
        return (False, f"news_tier_{tier}")
    return (True, "")

def apply_entry_filter(setup, day_type, market_data) -> bool:
    """Day-type-specific entry filter"""
    config = DAY_CONFIGS[day_type]
    filter_name = config["entry_filter"]
    # Implement per filter_name (trend_continuation_only, fade_extremes_only, etc.)
    ...

def compute_targets(entry, stop, day_type, tpo_data, vwap, pdc, open_price) -> dict:
    """Compute T1/T2/T3 per playbook"""
    config = DAY_CONFIGS[day_type]["targets"]
    R = abs(entry - stop)
    t1 = entry + (R * config["t1_R"]) if direction == "LONG" else entry - (R * config["t1_R"])
    # ... compute t2, t3 per t2_mode/t3_mode
    return {"t1": t1, "t2": t2, "t3": t3}
```

---

<a name="11-acceptance"></a>
## 11. Acceptance Criteria

For Phase 3.3 deployment to be considered successful:

- [ ] V3 Day Type Classifier deployed in production
- [ ] All 6 day types observed in 30 days of demo (REVERSAL may be 0-3)
- [ ] BROAD_CHANNEL playbook beats V2 NORMAL on V3-classified backtests
- [ ] Hysteresis switches: ≤ 4 per day average
- [ ] News tier blocks correctly applied (sample audit)
- [ ] Special day blocks fire correctly during rollover (test with synthetic date)
- [ ] Patch 1 hysteresis bypass tested with synthetic V-shape
- [ ] Patch 2 rollover blocking June 11-18, 2026 active
- [ ] Patch 3 timeout enforcement validated (no market chases logged)
- [ ] Smart Entry POC + imbalance fill rate ≥ 70% in demo

---

<a name="12-open"></a>
## 12. Open Questions for Day 3-5

1. **REVERSAL_DAY threshold tuning** — `range_multiplier 1.0 vs 1.2 vs 1.5`?
2. **BROAD_CHANNEL T2 cap** — `2.0R vs 2.5R vs 3.0R`?
3. **Patch 1 confidence floor** — `60 vs 70`?
4. **Cooldown override on Patch 1** — when bypassing, do we still want cooldown reset for next switch?
5. **Smart Entry timeout** — is 90s too long for fast markets?
6. **Imbalance threshold** — `200% vs 250% vs 150%`?
7. **Per-phase modifiers** — should LATE_DAY have its own size adjustments?
8. **DEVELOPING phase exception** — are there setups in DEVELOPING that should override the skip?

---

## Document History

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 1 May 2026 | V2.0 — initial 5 day types |
| 3.0 | 5 May 2026 PM | V3.0 — restructure to 6 types, new playbooks |
| 3.1 | 5 May 2026 EOD | V3.1 — 3 patches integrated, full pseudocode |

---

**Maintained by:** Michael (with Claude assistance)
**Status:** LOCKED — input to Phase 3.3 implementation
**Next review:** After Phase 3.2 Day 5 (8/5)
