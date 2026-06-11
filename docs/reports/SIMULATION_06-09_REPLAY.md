ב# MEMS26 Simulation Replay Report: 2026-06-09 (MES)

Generated: 2026-06-11
Session: RTH 09:30-16:00 ET (16:30-23:00 Israel)

---

## 1. Session Summary

| Metric | Value |
|--------|-------|
| RTH Open | 7458.50 (16:30 IL / 09:30 ET) |
| Session High | 7491.00 at 16:45 IL (09:45 ET) |
| Session Low | 7247.00 at 19:40 IL (13:40 ET) |
| RTH Close | ~7399 |
| Range | 244 pts (7491 - 7247) |
| S1 Classification | OPEN_DRIVE -> Trend_Normal (from 14:30 IL / 11:00 ET), reclassified Variation at 15:31 IL (12:31 ET) |
| IB Width Class | EXTREME -> later WIDE |
| Character | Massive trend day down with late session bounce |

### Price Action Narrative (5-min bars, Israel time)

- **16:30-16:45**: Opening drive up. 7458 -> 7491 high on 4th bar (aggressive buying).
- **16:50-17:05**: Rollover from 7491 to 7461. 4 consecutive bearish bars.
- **17:10-17:15**: CRASH BARS. 17:10 bar: 7461->7437 (-24.5pt, vol 44k). 17:15 bar: 7437->7422 (low 7415, vol 52k).
- **17:15-17:35**: Brief consolidation 7422-7441. Dead cat bounce.
- **17:40-17:45**: Second waterfall. 17:40: 7430->7407 (vol 31k). 17:45: 7407->7374 (low 7371, vol 65k!).
- **17:50-18:10**: Bounce attempt 7374->7400. 3 bars recovering 26pts.
- **18:15-18:55**: Second leg down. 7384->7312 (low 7311). Vol heavy.
- **19:00-19:40**: Third waterfall to session low. 7317->7247 (low at 19:40).
- **19:45-20:00**: V-bottom reversal begins. 7268->7305.
- **20:00-22:00**: Recovery rally. 7305->7395 (+90pts off low).
- **22:00-23:00**: Late session chop/fade then close squeeze to 7399.

---

## 2. S2 (FiveMinSystem) Patterns That DID Fire

Source: `v9_five_min_setups` table.

| # | Time (IL) | Pattern | Dir | Entry | Stop | Conf | Variant | Assessment |
|---|-----------|---------|-----|-------|------|------|---------|------------|
| 1 | 16:45 | INITIATIVE_LONG | LONG | 7489.0 | 7474.5 | 0.80 | - | **BAD** -- fired at session high, immediately reversed 244pts |
| 2 | 16:55 | REACTIVE_SHORT | SHORT | 7465.5 | 7490.75 | 0.80 | A_VSA,B_RVOL | **GOOD** -- excellent short entry, 25pt stop, market fell 218pts |
| 3 | 17:50 | INITIATIVE_SHORT | SHORT | 7387.25 | 7388.25 | 0.80 | - | **QUESTIONABLE** -- 1pt stop is absurdly tight; entry after already -104pt drop |
| 4 | 17:55 | REACTIVE_LONG | LONG | 7398.5 | 7367.0 | 0.75 | A_VSA,B_RVOL | **BAD** -- caught the dead cat bounce, market went to 7247 |
| 5 | 18:05 | REACTIVE_LONG | LONG | 7400.75 | 7383.5 | 0.75 | A_VSA,B_RVOL | **BAD** -- second attempt to catch the bounce, also stopped out |
| 6 | 18:55 | BEAR_FLAG_SHORT | SHORT | 7313.5 | 7349.75 | 0.92 | - | **MIXED** -- good direction but entry at 7313 with more downside; stop 36pt wide |
| 7 | 18:55 | REACTIVE_SHORT | SHORT | 7312.75 | 7349.75 | 0.80 | A_VSA,C_STRICT | **MIXED** -- same bar as Bear Flag; near the lows (7247 only 66pt away) |
| 8 | 20:30 | BULL_FLAG_LONG | LONG | 7337.75 | 7336.75 | 0.91 | - | **QUESTIONABLE** -- 1pt stop; correctly identified bounce direction |
| 9 | 21:30 | BULL_FLAG_LONG | LONG | 7377.75 | 7376.75 | 0.87 | - | **QUESTIONABLE** -- 1pt stop; rally correct but stop impossibly tight |
| 10 | 22:00 | DOUBLE_BOTTOM_EE_LONG | LONG | 7394.75 | 7330.25 | 0.77 | - | **GOOD** -- correctly detected double bottom (troughs ~7247 + ~7347); rally to 7399 |
| 11 | 22:05 | DOUBLE_BOTTOM_EE_LONG | LONG | 7393.25 | 7330.25 | 0.77 | - | Dedup failure -- same pattern 5 min later (30-bar cooldown not reached) |
| 12 | 22:50 | DOUBLE_BOTTOM_EE_LONG | LONG | 7384.0 | 7346.75 | 0.89 | - | **OK** -- second double bottom pair; close session near high |

### S2 Fire Quality Summary

- **Correct direction fires**: 2 SHORT (#2 Reactive, #6 Bear Flag), 2 LONG (#10, #12 Double Bottom) = **4/12 quality fires**
- **Wrong direction fires**: 3 LONG (#1 Initiative at top, #4, #5 Reactive longs into selloff)
- **Questionable**: 3 (absurdly tight 1pt stops: #3, #8, #9)
- **Day type was UNKNOWN for all fires** -- `day_type_at_fire` column is blank for every row. This means the Pkg 5a/5b/5c chart pattern gates (which require `current_day_type in (...)`) were NOT active during most of the session.

---

## 3. S4 (WoodiesSystem) Patterns That DID Fire

Source: `v9_woodies_patterns` and `v9_woodies_signals` tables.

**ZERO S4 patterns fired.** Both tables are empty for 2026-06-09.

This is the critical finding: S4 was completely silent on a 244-point trend day.

---

## 4. S4 CCI Analysis -- What SHOULD Have Fired

### 4.1 CCI-14 Timeline (key bars, Israel time)

| Time (IL) | CCI-14 | TCCI (CCI-6) | Trend | Price Close | Event |
|-----------|--------|--------------|-------|-------------|-------|
| 16:30 | +143.9 | +102.9 | BLUE | 7458 | RTH open |
| 16:35 | +217.0 | +141.2 | BLUE | 7466 | CCI above +200 |
| 16:40 | +232.8 | +138.1 | BLUE | 7475 | Peak CCI ~+256 next bar |
| 16:45 | **+256.6** | +150.5 | BLUE | 7490 | **CCI EXTREME: Session high** |
| 16:50 | +146.8 | +70.5 | BLUE | 7474 | CCI hook down from +256 |
| 16:55 | +57.3 | -22.8 | BLUE | 7466 | CCI crashing |
| 17:00 | +21.6 | -75.4 | BLUE | 7463 | CCI approaching zero |
| 17:05 | +6.9 | -85.6 | BLUE | 7461 | CCI near zero |
| 17:10 | **-130.4** | -154.6 | GRAY | 7437 | CCI CRASH below -100, trend flip GRAY |
| 17:15 | **-202.3** | -141.0 | GRAY | 7423 | CCI hits -200 EXTREME |
| 17:20 | -136.7 | -74.9 | GRAY | 7441 | Bounce |
| 17:25 | -106.3 | -47.0 | GRAY | 7433 | |
| 17:30 | -101.5 | -45.3 | GRAY | 7434 | |
| 17:35 | -87.5 | -40.9 | RED | 7431 | Trend flip to RED |
| 17:40 | -118.6 | -167.6 | RED | 7408 | Second sell wave |
| 17:45 | **-175.8** | -170.5 | RED | 7374 | Deep negative |
| 17:50 | -158.2 | -107.5 | RED | 7387 | Hook from -175 |
| 17:55 | -114.5 | -45.6 | RED | 7399 | CCI recovering |
| 18:00 | -90.5 | -22.4 | RED | 7391 | ZLR zone! |
| 18:05 | -74.0 | +11.0 | RED | 7401 | CCI approaching zero |
| 18:10 | -58.4 | +77.9 | RED | 7397 | CCI pullback to zero... |
| 18:15 | -73.3 | -42.4 | RED | 7384 | CCI hooks back DOWN! |
| 18:20 | -115.9 | -187.2 | RED | 7363 | CCI accelerates short |
| 18:25 | -182.3 | -158.8 | RED | 7332 | Deep selling again |
| 19:35 | -147.7 | -166.1 | RED | 7255 | Third wave down |
| 19:40 | -147.6 | -123.5 | RED | 7268 | Session low area |
| 19:55 | -56.3 | +31.6 | RED | 7287 | CCI hooking up strongly |
| 20:00 | **+38.7** | +175.9 | GRAY | 7306 | CCI crosses zero! |
| 20:15 | +119.7 | +88.8 | GRAY | 7321 | CCI above +100 |
| 20:20 | +153.3 | +135.7 | GRAY | 7326 | Strong momentum |
| 20:25 | +131.5 | +100.8 | BLUE | 7329 | Trend flip to BLUE |

### 4.2 Patterns That SHOULD Have Fired

#### 4.2.1 HFE DOWN (Hook From Extreme) -- ~16:55-17:05 IL

**Setup**: CCI hit +256.6 at 16:45 (above +200 threshold). By 16:55, CCI dropped to +57.3 (hook distance = 199 points > 50 threshold). CCI was declining (57.3 < 146.8).

**Why it should have detected**:
- Extreme reached: +256.6 >= +200 at 16:45
- Hook: CCI at 16:55 = +57.3, hook_distance = 199 > 50
- CCI declining: 57.3 < 146.8 (prev bar)
- Bars since extreme: 2 bars (within 2-12 range)

**Why it did NOT fire**: HFE uses DLL-primary detection (W-4 protocol). The `hfe_detected` column is 0 for all bars. The DLL did not flag this HFE. The Python fallback computes it but NEVER produces a trade decision (audit only). **This is a DLL detection gap.**

**Hypothetical trade**: Entry 7465.5 (16:55 close), Stop 7491.75 (above session high + 3T), Direction SHORT. Target: 7465.5 - 12 ticks = 7462.5 (T1), then trail. Result: **massive winner** (market fell to 7247).

#### 4.2.2 ZLR DOWN (Zero Line Reject) -- ~18:10-18:15 IL

**Setup**: CCI was below -100 earlier (hit -202.3 at 17:15). Pulled back toward zero: CCI at 18:05 = -74.0, at 18:10 = -58.4 (within -100 to +100 zone, pulled back). Then at 18:15: CCI = -73.3, dropping again (current < prev: -73.3 < -58.4). CCI is in -200 to 0 range.

**Detection logic check** (`zlr.py`):
- Stage 1: CCI <= -100 found at multiple bars (17:10-17:15 at -130/-202)
- Stage 2: Pullback above -100 but below +100: bars 18:00 (-90.5), 18:05 (-74.0), 18:10 (-58.4) all qualify
- Stage 3: Current CCI (-73.3) < prev (-58.4) AND -200 < -73.3 < 0: YES

**Why it SHOULD have fired**: All three ZLR stages are met. Trend was RED. This was a textbook ZLR short -- CCI bounced to zero from the -200 extreme, then rejected back down.

**Why it did NOT fire**: S4 pattern engine was completely silent (0 rows in `v9_woodies_patterns`). Either the WoodiesSystem was not running, not subscribed, or not processing bars on this day.

**Hypothetical trade**: Entry ~7384 (18:15 close), Stop ~7405.5 (recent swing high + ATR), Direction SHORT. Market went from 7384 to 7247 = **137pt winner**.

#### 4.2.3 ZLR DOWN (Second) -- ~19:25-19:35 IL

**Setup**: After the bounce to -56.3 (19:55) from the second CCI extreme around -182 (18:25), CCI pulled back toward zero at 19:25 (-93.5), then dropped again at 19:35 (-147.7). But this is a re-acceleration, not a classic pullback-and-reject.

**More precisely**: CCI was at -84.6 (19:30), then crashed to -147.7 (19:35). Prior extreme was around -182 at 18:25. Pullback bars: 19:20 (-128), 19:25 (-93.5), 19:30 (-84.6) -- all in the -100 to 0 zone... actually -93.5 and -84.6 are above -100 technically. Then drop: -147.7 < -84.6 and -200 < -147.7 < 0.

This could qualify as a ZLR DOWN but the pullback was shallow (only to -84.6, not really near zero). The ZLR code checks `-100 < cci < 100` for pullback bars -- -84.6 IS above -100. So it qualifies.

**Hypothetical trade**: Entry ~7255 (19:35 close), Stop ~7307 (recent high), Direction SHORT. Market hit 7247 then bounced -- tight but valid 8pt capture.

#### 4.2.4 TLB DOWN (Trend Line Break) -- ~17:10 IL

**Setup**: CCI had been rising/elevated (above +200 at 16:35-16:45). The 10-bar CCI window ending at 17:10 would show: a strong positive slope (from the +256 peak) that is now breaking down. Linear regression slope over the 10-bar window [16:25 to 17:10] would be NEGATIVE (CCI went from ~+117 to -130).

**Detection logic check** (`tlb.py`): slope < -2, current > predicted + 10, current > prev? Actually this is TLB UP (breaking upward through downtrend). For TLB DOWN: slope > 2, current < predicted - 10, current < prev. The slope from the 10-bar window ending at 17:10 would be steeply negative (not positive). So TLB DOWN does not apply here as coded.

Actually, if we look at the 10-bar window ending at ~17:55 (when CCI was rising from -175 to -114): the slope would be positive (CCI going from deep negative toward zero). TLB DOWN requires slope > 2 and current breaking below. This doesn't fit.

**Conclusion**: TLB detection geometry may not trigger on this day's CCI behavior because the moves were too one-directional. The CCI didn't form a trendline-then-break pattern; it crashed straight down. **TLB is designed for gradual trend exhaustion, not waterfalls.** Not a miss.

#### 4.2.5 TT SHORT (Turbo Trend) -- ~17:40-17:45 IL

**Setup**: Trend was RED from 17:35. CCI-14 < 0. TCCI needs to touch CCI-14 from below, then bounce back down.

- 17:35: CCI-14=-87.5, TCCI=-40.9 (TCCI above CCI-14: was_above check fails for SHORT)
- 17:40: CCI-14=-118.6, TCCI=-167.6 (TCCI < CCI-14-5: touched? Yes (-167.6 <= -118.6-5=-123.6). But need "was_below" at prev2...)

Actually for TT SHORT the logic is:
- was_below: cci6_prev2 < cci14_prev2 - 10 (2 bars ago TCCI was well below CCI-14)
- touched: cci6_prev >= cci14_prev - 5 (1 bar ago TCCI approached CCI-14 from below)
- bounced: cci6 < cci14 - 5 AND cci6 < cci6_prev (current bar TCCI drops below CCI-14 again)

At 17:40 (RED, CCI-14=-118.6): prev = 17:35 (CCI-14=-87.5, TCCI=-40.9). TCCI(-40.9) >= CCI-14(-87.5)-5 = -92.5. Yes, touched. prev2 = 17:30 (CCI-14=-101.5, TCCI=-45.3). was_below: -45.3 < -101.5-10 = -111.5? NO (-45.3 > -111.5). **Fails was_below.** TCCI was actually ABOVE CCI-14 at prev2, not below. So TT SHORT doesn't fire here.

**Verdict**: TT logic requires a prior period where TCCI was well BELOW CCI-14 (for SHORT), then TCCI approached CCI-14, then dropped away. On this day, TCCI and CCI-14 moved somewhat together during the selloff. **Not a clear miss** -- the TCCI/CCI-14 relationship didn't form the classic TT touch-and-go.

#### 4.2.6 GHOST SHORT (Bearish Ghost) -- ~17:05-18:20 IL

**Setup**: Ghost SHORT requires three CCI peaks where middle > both sides and current CCI is below the third (right) peak. Looking at the CCI-14 series from 16:25 to 18:20:

CCI peaks in the window:
- Peak 1: 16:45 at +256.6
- No valid "three peaks with middle highest" because +256 IS the absolute high

The GHOST pattern needs three CCI swings forming H&S. On this day CCI had ONE massive peak then crashed. There's no three-peak structure on the short side.

During the recovery (20:00-22:00), the CCI on the bullish side:
- Trough 1: ~17:15 at -202.3
- Trough 2: ~18:25 at -182.3
- Trough 3: ~19:40 at -147.6

This is an ASCENDING trough pattern (each trough higher) -- but GHOST LONG requires middle trough LOWER than both sides. -202.3, -182.3, -147.6 is ascending, not a head pattern. **No GHOST match.**

#### 4.2.7 VEGAS SHORT (Bearish Divergence) -- No valid setup

VEGAS SHORT requires: price makes Higher High but CCI makes Lower High. The session had ONE price high at 7491. There was no second price high that exceeded 7491. **No VEGAS setup possible.**

VEGAS LONG could theoretically apply at session end (price made lower lows but CCI made higher lows): price low 7247 (19:40) vs price low ~7347 (22:40), but CCI lows were -147.6 vs -123.9. Price LL + CCI HL would need the second price low BELOW the first, which 7347 > 7247 -- so no. **No VEGAS setup.**

#### 4.2.8 FAMIR SHORT -- ~17:05-17:10 IL

**Setup**: CCI approached +200 (reached +256.6 at 16:45, exceeding +200). FAMIR requires CCI to approach but NOT reach +200 (NEAR_THRESHOLD=170, max < THRESHOLD+10=210). CCI hit +256.6, which is > 210. **FAMIR filter: `max_recent < THRESHOLD + 10 = 210`... 256.6 >= 210. FAILS.** FAMIR is for FAILED attempts at 200; this CCI blew through 200. Correct non-detection.

FAMIR LONG after the selloff: CCI hit -202.3 at 17:15 (below -200). FAMIR LONG requires `min_recent > -(THRESHOLD + 10) = -210`. -202.3 > -210, so it passes. But `min_recent <= -NEAR_THRESHOLD = -170` also needed. -202.3 <= -170: YES. Then: current > prev and current > min_recent + 20.

At 17:20: CCI = -136.7 > -202.3 + 20 = -182.3? YES. And -136.7 > prev(-202.3)? YES. **FAMIR LONG should have fired at 17:20!**

**Why it did NOT fire**: Same reason as all S4 -- the Woodies pattern engine was not running.

**Hypothetical trade**: Entry 7441 (17:20 close), Stop above recent high ~7461, Direction LONG. Market bounced to 7441 then fell to 7247. **Would have been stopped out** -- the FAMIR long was a counter-trend trade into a crash. Correct non-fire in hindsight, but the code should have detected it.

---

## 5. S2 Patterns That SHOULD Have Fired (But Didn't)

### 5.1 H&S Top -- ~17:00-17:10 IL

**Setup**: Price formed a potential H&S top:
- Left Shoulder: 7470.75 high at 16:35
- Head: 7491.00 high at 16:45
- Right Shoulder: 7472.50 high at 17:00

Neckline: min of lows between LS and RS -- roughly 7464-7473 area.

**Why it likely didn't detect**: The detection runs on bars with PIVOT_LOOKBACK=2. By the time bars[-1] close was below neckline (17:10 close = 7437), the pattern geometry requires the pivots to be swing highs. The 7491 peak at 16:45 surrounded by 7475 and 7490 makes it a valid swing high (7491 > 7475.5 AND 7491 > 7490). But the right shoulder at 17:00 (7472.5 high) needs both neighbors to be lower -- 17:05 high is 7469.5 (lower) and 16:55 high is 7476.75 (HIGHER). So 7472.5 is NOT a swing high per PIVOT_LOOKBACK=2.

**Root cause**: The H&S detection requires formal swing pivots. The right shoulder at 17:00 doesn't qualify because 16:55 has a higher high. With PIVOT_LOOKBACK=1 it might have worked, but the constant is 2. **This is a legitimate geometric miss** -- the pattern was there visually but the pivot detection is strict.

### 5.2 Bear Flag -- Earlier fires (18:55 was caught)

The Bear Flag at 18:55 DID fire (entry 7313.5). There was potentially an earlier Bear Flag setup after the first leg down (17:10-17:45: pole from 7461 to 7374, then flag 7374-7399 consolidation, breakdown at 18:15-18:20). Let's check:
- Pole: 17:10-17:45, from ~7461 high to 7371.75 low = 89.25pt height, 8 bars, mostly bearish
- Flag: 17:50-18:10, range 7367-7405 = 38pt, 5 bars
- Retrace: (7405 - 7371.75) / 89.25 = 37% < 50%: passes
- Breakout bar at 18:20: close 7362.5 < flag_low (7367.75)... yes!

This should have detected as a BEAR_FLAG around 18:20 but:
- The detection requires `day_type_mode` and `current_day_type in ("Trend_Normal", "Trend_DD", "Variation", ...)`.
- Day type was UNKNOWN in `five_min_setups` for the fired patterns, suggesting the day_type was not properly propagated to S2.
- However, the 18:55 Bear Flag DID fire. So the gate was eventually met.

The 18:20 Bear Flag may have been missed because S2's `current_day_type` was still `None` at that time despite DB showing Trend_Normal from 14:30. The hydration issue where `current_day_type is None` causes chart patterns to be silently skipped (the code has an explicit warning for this).

**Impact**: Missing the Bear Flag at 18:20 (entry ~7362) cost a potential 115pt winner to the session low.

### 5.3 Double Top -- Not applicable

The session had one major peak (7491 at 16:45). No second peak at a similar level formed. The Double Top (Adam&Adam) detector requires two sharp peaks at similar highs with `TROUGH_SYM_PCT = 0.03` (0.2% tolerance). No such structure existed. **Correct non-detection.**

---

## 6. Root Cause Analysis: S4 Complete Silence

**Finding**: Zero rows in `v9_woodies_patterns` and `v9_woodies_signals` for 2026-06-09, despite:
- 109 CCI bars computed in `v9_bars_5min_woodies`
- CCI reaching extreme values (+256.6, -202.3)
- Multiple textbook ZLR/HFE setups
- RED trend state active for most of the session

**Possible root causes** (investigation needed):
1. **WoodiesSystem.process_bar not wired**: The pattern engine may not be receiving bar events from BarRouter
2. **Pattern dispatcher not calling detect()**: The `pattern_engine.py` or `pattern_dispatcher.py` may have a gate preventing pattern evaluation
3. **Strategic gate (a1_strategic_gate.py)**: May be blocking all S4 fires based on some condition
4. **Day type gate (day_type_gate.py)**: May require a day type that wasn't available
5. **Anti-pattern (AP8 CCI flat)**: Unlikely given CCI had extreme values, but the check runs on all patterns

**This is a P0 issue for LIVE readiness.** A 244-point trend day with CCI extremes should produce multiple ZLR and HFE signals from S4.

---

## 7. Key Issues Summary

### CRITICAL

| # | Issue | Impact | Priority |
|---|-------|--------|----------|
| C1 | **S4 completely silent** -- 0 patterns detected on 244pt trend day | Lost all S4 trade signals | P0 |
| C2 | **S2 day_type_at_fire is blank** for all 12 fires | Chart patterns (H&S, Flag, Double) gated inconsistently | P1 |
| C3 | **1-point stops** on 3 fires (#3, #8, #9) -- non-tradeable | Sizing/stop logic failure on Initiative/Flag patterns | P1 |

### MODERATE

| # | Issue | Impact | Priority |
|---|-------|--------|----------|
| M1 | HFE DOWN at 16:55 missed (DLL did not flag it) | Missed 218pt short from session high | P2 |
| M2 | ZLR DOWN at 18:15 missed (S4 engine not running) | Missed 137pt short continuation | P2 |
| M3 | Bear Flag at 18:20 missed (likely day_type=None gate) | Missed 115pt short continuation | P2 |
| M4 | S2 fired INITIATIVE_LONG at session high (7489) | Worst possible entry of the day | P3 (inherent risk) |
| M5 | S2 fired 2 REACTIVE_LONG counter-trend into crash | Counter-trend detection in strong selloff | P3 |
| M6 | Dedup failure: DOUBLE_BOTTOM_EE fired at 22:00 AND 22:05 (only 1 bar apart, cooldown=30) | Same setup fired twice | P2 |

### Score Card

| Metric | Value |
|--------|-------|
| S2 fires (total) | 12 |
| S2 fires (correct direction, quality entry) | 4 (33%) |
| S2 fires (wrong direction or bad stop) | 8 (67%) |
| S4 fires (total) | **0** |
| S4 expected fires (ZLR, HFE) | 3-5 |
| Missed HIGH-VALUE trades | 3 (HFE, ZLR, early Bear Flag) |
| Total unrealized edge from misses | ~400+ pts |

---

## 8. Recommendations

1. **Investigate S4 engine wiring** -- priority P0. Check `WoodiesSystem.process_bar`, `pattern_engine.py`, `pattern_dispatcher.py`, and whether BarRouter delivers `bar.5min` events to S4. The CCI bars are computed (in the DB), so the bridge + CCI calculator works; it's the pattern detection stage that's broken.

2. **Fix day_type propagation to S2** -- the `day_type_at_fire` column being blank means S2's `current_day_type` is `None`, which silently blocks all chart patterns (H&S, Double, Flag) during FIRST_HOUR_TACTICAL mode and early DAY_TYPE_MODE. The hydration path loads from DB but may be stale.

3. **Audit 1-point stops** -- Initiative SHORT at 17:50 had stop=7388.25 vs entry=7387.25 (1pt). Bull Flags at 20:30 and 21:30 also had 1pt stops. This is the adaptive stop engine returning degenerate values. The `compute_stop_v2` or `compute_stop` is likely receiving bad structural anchors.

4. **Consider adding counter-trend filter for S2 Reactive** -- on a Trend_Normal/EXTREME IB day, REACTIVE_LONG fires are suicide trades. S2 could consult the day type classification to suppress counter-trend Reactive fires when the day type is strongly directional.

5. **Re-evaluate HFE DLL detection** -- the Python fallback correctly detected the HFE DOWN at 16:55 but was suppressed by W-4 protocol (DLL-primary). If the DLL consistently misses HFEs, consider promoting Python fallback to co-primary or adding a hybrid mode.
