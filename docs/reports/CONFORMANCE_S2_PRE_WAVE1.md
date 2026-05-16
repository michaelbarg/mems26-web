# CONFORMANCE S2 · Pre-Wave 1
Date: 2026-05-16 · Branch: feature/v9_architecture_rebuild

## §A · File Locations

| Pattern | Path | LOC |
|---|---|---|
| Reactive Long | five_min_system.py:265-304 `_detect_reactive()` | ~40 |
| Reactive Short | five_min_system.py:306-315 (mirror block) | ~10 |
| Initiative Long | five_min_system.py:319-353 `_detect_initiative()` | ~35 |
| Initiative Short | five_min_system.py:355-362 (mirror block) | ~8 |
| Belly | five_min_system.py:196-211 `_get_belly_from_footprint()` | ~16 |
| Tests | tests/atomic/test_five_min_patterns.py | 9 tests |
| Tests | tests/atomic/test_five_min_sizing.py | 5 tests |
| Tests | tests/test_five_min_system.py | 10 tests |

## §B · Reactive_Long Conformance (10 checks)

| Check | Status | Code Quote |
|---|---|---|
| C-RL-1 | :green_circle: | `b1, b2, b3, b4 = bars_5m[-4], bars_5m[-3], bars_5m[-2], bars_5m[-1]` (line 281) |
| C-RL-2 | :green_circle: | `b1_sellers = b1["c"] < b1["o"] and b1_vol > 0` (line 294) |
| C-RL-3 | :red_circle: MISSING | No check for price proximity to support (PDL/VAL/IBL/SL). Pattern fires regardless of location. |
| C-RL-4 | :green_circle: | `b2_drop = b2_vol <= b1_vol * 0.10 if b1_vol > 0 else False  # 90% drop` (line 295) |
| C-RL-5 | :yellow_circle: PARTIAL | `b3_belly = belly is not False  # True or None (unavailable) both pass` (line 297). Belly read from Footprint HTTP, but None passes (not strict). |
| C-RL-6 | :green_circle: | `poc_rising = self._poc_vol_rising(bars_5m[-3:])` (line 300). Full check: each POC >= previous over 3 bars. |
| C-RL-7 | :green_circle: | `b4_confirm = b4["c"] > b4["o"]` (line 298). Simple bullish close. |
| C-RL-8 | :green_circle: | `cot_above_amt = cur_cot > cur_amt` (line 299). Enforced in final condition (line 302). |
| C-RL-9 | :green_circle: | Returns `("LONG", 0.80 if poc_rising else 0.75, {...})` (line 303-304) |
| C-RL-10 | :red_circle: MISSING | Returns (direction, confidence, info_dict). Does NOT include entry_price, stop_price, t1, t2, time_stop per D-041. |

**Verdict: YELLOW (PARTIAL).** 7/10 conform. Missing: S/R proximity (C-RL-3) + D-041 output (C-RL-10). Belly gate too permissive (None passes).

## §C · Reactive_Short Conformance (10 checks)

| Check | Status | Code Quote |
|---|---|---|
| C-RS-1 | :green_circle: | Same 4-bar read as LONG (line 281) |
| C-RS-2 | :green_circle: | `b1_buyers = b1["c"] > b1["o"] and b1_vol > 0` (line 307) |
| C-RS-3 | :red_circle: MISSING | No check for price proximity to resistance (PDH/VAH/IBH) |
| C-RS-4 | :green_circle: | Same `b2_drop` check reused (line 295, computed above) |
| C-RS-5 | :yellow_circle: PARTIAL | Same belly gate (None passes) |
| C-RS-6 | :green_circle: | `poc_falling = self._poc_vol_falling(bars_5m[-3:])` (line 311) |
| C-RS-7 | :green_circle: | `b4_confirm_s = b4["c"] < b4["o"]` (line 309) |
| C-RS-8 | :green_circle: | `cot_below_amt = cur_cot < cur_amt` (line 310). Enforced in condition (line 313). |
| C-RS-9 | :green_circle: | Returns `("SHORT", 0.80 if poc_falling else 0.75, {...})` (line 314) |
| C-RS-10 | :red_circle: MISSING | Same as C-RL-10 — no D-041 fields |

**Verdict: YELLOW (PARTIAL).** Same gaps as LONG: no S/R proximity, no D-041 output.

## §D · Initiative_Long Conformance (8 checks)

| Check | Status | Code Quote |
|---|---|---|
| C-IL-1 | :green_circle: | `b1, b2, b3, b4 = bars_5m[-4], bars_5m[-3], bars_5m[-2], bars_5m[-1]` (line 335) |
| C-IL-2 | :green_circle: | `b1_expansion = 1.5 <= b1_range <= 1.75  # 6-7 ticks MES` (line 342) |
| C-IL-3 | :yellow_circle: PARTIAL | `b2_higher_low = b2["l"] > b1["l"]` (line 348). Checks HL but NOT "return to POC_VOL" alternative. |
| C-IL-4 | :green_circle: | `b3_joining = b3_range > b1_range` (line 344) |
| C-IL-5 | :yellow_circle: PARTIAL | `b4_test = b4["l"] >= b2["l"]` (line 349). Checks floor hold but not explicit "2nd test = entry signal" with entry price. |
| C-IL-6 | :green_circle: | `cot_below_amt = cur_cot < cur_amt` (line 350). Enforced in condition (line 352). |
| C-IL-7 | :green_circle: | Returns `("LONG", 0.80, {"kind": "INITIATIVE", "stage": 4})` (line 353) |
| C-IL-8 | :red_circle: MISSING | Same — no D-041 fields (entry/stop/t1/t2/time_stop) |

**Verdict: YELLOW (PARTIAL).** 5/8 conform fully. Missing: POC_VOL return alternative in Bar -2, explicit entry logic, D-041 output.

## §E · Initiative_Short Conformance (8 checks)

| Check | Status | Code Quote |
|---|---|---|
| C-IS-1 | :green_circle: | Same 4-bar read (line 335) |
| C-IS-2 | :green_circle: | Same `b1_expansion` check (line 342) |
| C-IS-3 | :yellow_circle: PARTIAL | `b2_lower_high = b2["h"] < b1["h"]` (line 357). LH but no POC_VOL alternative. |
| C-IS-4 | :green_circle: | Same `b3_joining` check (line 344) |
| C-IS-5 | :yellow_circle: PARTIAL | `b4_test_s = b4["h"] <= b2["h"]` (line 358). Ceiling hold only. |
| C-IS-6 | :green_circle: | `cot_above_amt = cur_cot > cur_amt` (line 359). NOTE: spec says COT > AMT for Initiative SHORT = "no counter pressure from sellers". Code matches. |
| C-IS-7 | :green_circle: | Returns `("SHORT", 0.80, {"kind": "INITIATIVE", "stage": 4})` (line 362) |
| C-IS-8 | :red_circle: MISSING | No D-041 fields |

**Verdict: YELLOW (PARTIAL).** Same gaps as LONG mirror.

## §F · Belly Conformance (4 checks)

| Check | Status | Code Quote |
|---|---|---|
| C-B-1 | :yellow_circle: PARTIAL | `_get_belly_from_footprint()` returns bool from Footprint `/current` endpoint `belly_ratio_dominant`. Does not distinguish buyer vs seller belly explicitly in S2 — relies on Footprint's computation. |
| C-B-2 | :red_circle: MISSING | No "thin neck" condition anywhere in five_min code. Footprint `detectors.py:138` has `belly_ratio_dominant` but no thin_neck check visible. |
| C-B-3 | :red_circle: MISSING | POC_VOL position within bar not checked by belly function. `_poc_vol_rising()` is separate from belly gate. |
| C-B-4 | :green_circle: | Belly consumed by Reactive pattern at line 291-297: `belly = self._get_belly_from_footprint()` then used in `b3_belly` condition. |

**Verdict: YELLOW (PARTIAL).** Belly exists as boolean gate but lacks Zohar OFA depth (thin neck, POC position within bar).

## §G · Tests Conformance

| Test File | Scenarios | Spec Match? | Pass |
|---|---|---|---|
| test_five_min_patterns.py::test_reactive_long | 4-bar sellers→drop→buyers→confirm with COT>AMT mock | :green_circle: Matches V3 T1 Reactive LONG | PASS |
| test_five_min_patterns.py::test_reactive_short | Mirror of above | :green_circle: | PASS |
| test_five_min_patterns.py::test_reactive_rejected_when_belly_false | Belly=False → no pattern | :green_circle: Edge case | PASS |
| test_five_min_patterns.py::test_reactive_needs_4_bars | <4 bars → None | :green_circle: Guard | PASS |
| test_five_min_patterns.py::test_initiative_long | Expansion→HL→joining→test with COT<AMT | :green_circle: Matches V3 T1 Initiative LONG | PASS |
| test_five_min_patterns.py::TestPocVolRising (3 tests) | POC rising/falling/insufficient | :green_circle: Utility | PASS |
| test_five_min_patterns.py::test_poc_falling_true | Mirror | :green_circle: | PASS |
| test_five_min_sizing.py (5 tests) | full/half/reject sizing decisions | :yellow_circle: Tests sizing logic, not 4-bar pattern | PASS |
| test_five_min_system.py (10 tests) | Hydration, process, mode transition | :yellow_circle: Infrastructure tests, not pattern logic | PASS |

**Verdict: GREEN for pattern tests (9 tests cover 4-bar logic). Tests use mocked COT/AMT/Belly — realistic for unit tests.**

## §H · Cross-Cutting

| Item | Status | Details |
|---|---|---|
| COT/AMT integration | :green_circle: | Both Reactive and Initiative CONSUME COT/AMT via `_get_cot_from_footprint()` / `_get_amt_from_footprint()`. Constraint enforced in all 4 patterns. |
| S/R proximity | :red_circle: MISSING | No grep hits for pdh/pdl/vah/val/ibh/ibl/support/resistance in pattern logic. Reactive patterns fire regardless of price location vs S/R levels. |
| D-041 output | :red_circle: MISSING | All patterns return `(direction_str, confidence_float, info_dict)`. Missing: entry_price, stop_price, t1_price, t2_price, time_stop_minutes. |

## §I · OVERALL VERDICT (CRITICAL)

| Pattern | Verdict | Required Action |
|---|---|---|
| Reactive_Long | :yellow_circle: YELLOW | Needs: S/R proximity check (Bar -3 at support) + D-041 output wrapper. Core 4-bar logic is CORRECT. |
| Reactive_Short | :yellow_circle: YELLOW | Same: S/R proximity (resistance) + D-041 output. |
| Initiative_Long | :yellow_circle: YELLOW | Needs: POC_VOL return alternative in Bar -2 + D-041 output. Core expansion/joining logic CORRECT. |
| Initiative_Short | :yellow_circle: YELLOW | Same as IL mirror. |
| Belly | :yellow_circle: YELLOW | Needs: thin neck condition + POC position within bar. Current boolean gate is too coarse. |
| Tests | :green_circle: GREEN | 9/9 pass. Cover 4-bar logic with mocked dependencies. Add S/R + output tests in Wave 1. |

**OVERALL: ALL YELLOW — patterns detect correctly but output is incomplete (no price levels) and S/R proximity not enforced. No RED = no rebuild needed.**

## §J · CC's Wave 1 Scope Recommendation

**Option (b): Original 3 commits + 2 alignment commits.**

Wave 1 scope (5 commits):

1. **C1: `pre_fire_validator.py`** — new shared module (original)
2. **C2: `T1Setup` output schema** — new file (original)
3. **C3: `cot_amt.py` standalone** — direct Sierra read (original)
4. **C4: Output wrapper** — wrap existing `_detect_reactive` / `_detect_initiative` output into `T1Setup` with computed entry/stop/t1/t2/time_stop based on bar data
5. **C5: S/R proximity gate** — add support/resistance proximity check to Reactive patterns using TPO data (VAH/VAL/IB levels from `/api/v9/tpo/current`)

**DEFER (Wave 2+):**
- Thin neck belly condition (requires Footprint OFA enhancement, not S2-local)
- POC_VOL "return" alternative for Initiative Bar -2 (minor — HL check is sufficient for V1)
- First Hour Buffer/Matrix (separate prompt)

**NOT needed (skip):**
- Pattern rebuild (all 4 are structurally CORRECT per Zohar 4-bar)
- COT/AMT in patterns (already wired and enforced)

Estimated Wave 1: 5 commits, ~1.5 hours CC.
