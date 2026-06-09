# Pattern Arming Audit — 2026-06-08 15:14 UTC

**Session:** RTH active, 286 min to close  
**Day Type:** Variation (S1 classified, IB locked)  
**Opening Type:** OPEN_DRIVE  
**S2 Mode:** DAY_TYPE_MODE (post-IB, FHB=COMPLETE bar=13)  
**S4 Trend:** BLUE (uptrend)  
**CCI-14:** 110.67 | TCCI: 68.15

---

## Bridge Stream Health

| Stream | Status | Lag | Note |
|--------|--------|-----|------|
| woodies_5min | FRESH | 0s | OK |
| footprint | FRESH | 0s | OK (bridge pushing, S3 muted via S3_MUTE=1) |
| cumulative_delta | FRESH | 276s | OK |
| volume_profile | FRESH | 1s | OK |
| tick_reversal_15 | **DEAD** | **4283 min** | Last push 2026-06-05 15:51 ET |
| imbalance | FRESH | 0s | OK |
| tpo | **DEAD** | **1.3M min** | Last push 2023-11-25 (!) |
| bars_5min | FRESH | 0s | OK |

---

## S2 -- Five-Minute Patterns (10 patterns)

### Master Table

| # | Pattern | Direction | Status | Blocked Reason (primary) | Classification | Auth Cell |
|---|---------|-----------|--------|--------------------------|----------------|-----------|
| 1 | Reactive | LONG | Blocked | choppiness_ok (chop=93, need <70) | :yellow_circle: choppiness_ok | FULL 3/2/2 |
| 2 | Reactive | SHORT | Blocked | choppiness_ok (chop=93, need <70) | :yellow_circle: choppiness_ok | FULL 3/2/2 |
| 3 | Initiative | LONG | Blocked | choppiness_ok + b1_expansion (6.25pt, need [4.5,6.0]) | :yellow_circle: choppiness_ok | FULL 3/2/1 |
| 4 | Initiative | SHORT | Blocked | choppiness_ok + b1_expansion | :yellow_circle: choppiness_ok | FULL 3/2/1 |
| 5 | Inverse H&S | LONG | Blocked | choppiness_ok + swing_lows (2 found, need 3) | :yellow_circle: choppiness_ok | REDUCED 2/1/0 |
| 6 | H&S Top | SHORT | Blocked | choppiness_ok + swing_highs (2 found, need 3) | :yellow_circle: choppiness_ok | REDUCED 2/1/0 |
| 7 | Double Bottom EE | LONG | Blocked | choppiness_ok + eve_variant (trough widths too narrow) | :yellow_circle: choppiness_ok | FULL 3/2/2 |
| 8 | Double Top AA | SHORT | Blocked | choppiness_ok + neckline_breakout (close 30.75pts above neckline) | :yellow_circle: choppiness_ok | FULL 3/2/2 |
| 9 | Bull Flag | LONG | Blocked | choppiness_ok + breakout (close 4.50pts below trigger) | :yellow_circle: choppiness_ok | FULL 3/2/2 |
| 10 | Bear Flag | SHORT | Blocked | choppiness_ok + pole_found (no valid bear pole) | :yellow_circle: choppiness_ok | FULL 3/2/1 |

### S2 Global Gate

- `nt_day_type`: PASS (Variation != Nontrend)

### S2 Per-Pattern Gate Analysis

All 10 S2 patterns share these gates (all passing):

| Gate | Status | Value |
|------|--------|-------|
| five_min_bar_recency | PASS | lag=275s <= 360s |
| cci_14_history | PASS | buffer=20 >= 14 |
| day_type_known | PASS | Variation |
| auth_table_cell | PASS | != SKIP for all patterns on Variation |
| nt_skip | PASS | Variation != Nontrend |
| mode_context | PASS | DAY_TYPE_MODE |
| fhb_eligible | PASS | COMPLETE @ bar 13 |

The **universal blocker** is `choppiness_ok`:
- **Current:** chop=93
- **Required:** < 70
- **Source:** `compute_choppiness()` in `backend/v9/systems/five_min/choppiness.py`

Each pattern also has a **secondary detection blocker** (no pattern geometry detected on the current bar buffer), but these are normal -- they change bar-by-bar.

---

## Choppiness Deep Dive

**File:** `/Users/michael/Downloads/mems26_web_git/backend/v9/systems/five_min/choppiness.py`

`compute_choppiness(bars)` scores 0-100 from a 3-6 bar window:
- **Component 1 (0-40):** Direction flips -- alternating bullish/bearish candles
- **Component 2 (0-35):** Overlap ratio -- bars overlapping each other's range
- **Component 3 (0-25):** Body size variance -- coefficient of variation of body sizes

**Critical finding:** The function uses `bars[:max_bars]` (first 6 bars), meaning it reads the **FIRST bars in the buffer**, not the most recent. In `five_min_system.py` line 868:
```python
_chop_bars = self._bar_buffer[-14:] if len(self._bar_buffer) >= 5 else self._bar_buffer
```
So it feeds the last 14 bars from the buffer, but `compute_choppiness` slices `[:6]`, reading the **oldest 6 of the 14**. This means the choppiness gate is locked to whatever the opening bars looked like and barely changes as the session progresses.

**choppiness_ok does NOT depend on:**
- tick_reversal_15 (DEAD stream -- not used)
- tpo (DEAD stream -- not used)
- footprint / S3_MUTE (not used)

It depends purely on the 5-min OHLC bars in the buffer. The score of 93 is legitimate -- the opening bars were genuinely choppy (alternating direction, overlapping ranges). But the fact that it reads `bars[:6]` (the oldest 6 of the window, which are roughly bars 7-12 of the session, i.e., roughly 09:40-10:10 ET) means it is nearly frozen for the rest of the day.

---

## S4 -- Woodies CCI Patterns (9 patterns)

### Master Table

| # | Pattern | Direction | Status | Blocked Reason | Classification |
|---|---------|-----------|--------|----------------|----------------|
| 1 | ZLR (Zero Line Reject) | with-trend | Armed | No CCI pattern detected yet | :yellow_circle: Waiting setup |
| 2 | TLB (Trend Line Break) | with-trend | Armed | No CCI pattern detected yet | :yellow_circle: Waiting setup |
| 3 | TT (Tony Trade) | with-trend | Armed | No CCI pattern detected yet | :yellow_circle: Waiting setup |
| 4 | GB100 (Ghost Bar +/-100) | with-trend | Armed | No CCI pattern detected yet | :yellow_circle: Waiting setup |
| 5 | Vegas (Divergence) | with-trend | Armed | No CCI pattern detected yet | :yellow_circle: Waiting setup |
| 6 | Ghost (CCI H&S) | with-trend | Armed | No CCI pattern detected yet | :yellow_circle: Waiting setup |
| 7 | FaMir (Failed ZLR +/-200) | with-trend | Armed | No CCI pattern detected yet | :yellow_circle: Waiting setup |
| 8 | HTLB (Horizontal TLB) | with-trend | Armed | No CCI pattern detected yet | :yellow_circle: Waiting setup |
| 9 | HFE (Hook From Extreme) | with-trend | Armed | No CCI pattern detected yet | :yellow_circle: Waiting setup |

### S4 Gate Analysis

All 9 S4 patterns share these gates (all passing):

| Gate | Status | Value |
|------|--------|-------|
| cci_14_present | PASS | 110.67 |
| tcci_present | PASS | 68.15 |
| 5min_bar_recency | PASS | lag=275s <= 360s |
| strategic_gate (trend) | PASS | BLUE |
| rth_gate | PASS | in RTH |
| day_type_gate | PASS | Variation |

All S4 patterns are **ARMED** -- data gates satisfied, trend established (BLUE). They simply have not detected a CCI pattern on the current bar. Blockers listed (`detection.pattern_specific`, `targets_stop.*`, `exit_rules.ready_to_route`) are all downstream of detection -- they will populate automatically when a pattern triggers.

**S4 is healthy. No fixes needed.**

---

## Classification Summary

| Classification | Count | Patterns |
|----------------|-------|----------|
| :red_circle: Data blocker (dead stream) | 0 | -- |
| :green_circle: Auth Table SKIP (doctrine) | 0 | -- (all patterns allowed on Variation) |
| :yellow_circle: Choppiness gate (computed, not stream) | 10 | All S2 patterns |
| :yellow_circle: Waiting setup (no CCI pattern detected) | 9 | All S4 patterns |

**Totals: 0 green (doctrine), 0 red (data), 19 yellow (waiting/gate)**

---

## Dead Streams (noted but not blocking S2/S4)

| Stream | Last Push | Impact |
|--------|-----------|--------|
| `tick_reversal_15` | 2026-06-05 15:51 ET (3 days ago) | Not used by choppiness or any S2/S4 gate. Sierra study may have stopped exporting. |
| `tpo` | 2023-11-25 (2.5 years ago) | Sierra TPO JSON loaded directly by `_load_sierra_tpo()` for POC/VAH/VAL refs -- not via this bridge stream. S1 day-type uses it separately. Not a blocker. |

---

## Top 3 Fixes to Unblock the Most Patterns

### Fix 1: Choppiness window bug -- use LATEST bars, not oldest (unblocks all 10 S2)

**File:** `backend/v9/systems/five_min/choppiness.py` line 33  
**Current:** `window = bars[:max_bars]` -- reads the first 6 bars  
**Should be:** `window = bars[-max_bars:]` -- reads the last 6 bars  

This single change would give a rolling choppiness score that reflects current market structure rather than the opening period. The market may have transitioned from choppy to trending by now, but the score is frozen at 93 because it reads old bars.

**Impact:** Unblocks all 10 S2 patterns (when score drops below 70)

### Fix 2: Consider raising the choppiness threshold to 80 (tuning, not bug)

If the opening was genuinely choppy and the score is correct, a threshold of 70 may be too aggressive. A Variation day with an OPEN_DRIVE opening could legitimately have choppy initial bars while still being tradeable intraday. Consider raising to 80 as a soak experiment.

**Impact:** Unblocks all 10 S2 patterns (if score falls between 70-80 range after fix 1)

### Fix 3: Restart tick_reversal_15 export from Sierra (non-blocking, hygiene)

The tick_reversal_15 stream has been dead since June 5. While it does not currently block any arming gate, it may be needed for future features. Check the Sierra DLL study for export failures.

**Impact:** Hygiene only, no immediate pattern unblock.

---

## Appendix: S2 Pattern Gate Dependency Map

### Reactive LONG/SHORT
- **Data gates:** bar_recency, cci_14_history, choppiness_ok, mode_context, fhb_eligible
- **Day type gates:** day_type_known, auth_table_cell, nt_skip
- **Detection:** min_bars (7), b1_sellers/buyers, b2_volume_drop, b3_buyers/sellers, b4_confirm
- **Streams:** 5-min bars (in-memory buffer), COT/AMT (Sierra CDV), Footprint belly (S3 injection)

### Initiative LONG/SHORT
- **Data gates:** (same as Reactive)
- **Detection:** min_bars (7), b1_expansion (ATR-relative range check), b2_test, b3_joining, b4_test
- **Streams:** 5-min bars, COT/AMT

### Inverse H&S LONG / H&S Top SHORT
- **Data gates:** (same as Reactive)
- **Detection:** min_bars (12), swing_lows/highs (need 3), shoulder_symmetry, head_extension, neckline_breakout
- **Streams:** 5-min bars only (no footprint/COT dependency)

### Double Bottom EE LONG / Double Top AA SHORT
- **Data gates:** (same as Reactive)
- **Detection:** min_bars (10), swing_lows/highs (need 2), trough_pair/peak_pair, eve_variant/adam_variant, neckline_breakout
- **Streams:** 5-min bars only

### Bull Flag LONG / Bear Flag SHORT
- **Data gates:** (same as Reactive)
- **Detection:** min_bars (10), pole_found (5+ bars, 16T height), flag_length (3-8 bars), flag_retrace (<50%), breakout
- **Streams:** 5-min bars only

### S4 All Patterns (ZLR, TLB, TT, GB100, Vegas, Ghost, FaMir, HTLB, HFE)
- **Data gates:** cci_14_present, tcci_present, 5min_bar_recency
- **Stage A1:** strategic_gate (trend_state in BLUE/RED), rth_gate, day_type_gate
- **Detection:** pattern-specific CCI geometry (each pattern has unique CCI shape rules)
- **Streams:** Woodies 5-min bars + CCI-14/TCCI/SWI/CZI study values from Sierra

---

*Generated by Claude Code audit at 2026-06-08T15:14 UTC*
