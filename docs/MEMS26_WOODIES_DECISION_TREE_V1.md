# MEMS26 — Woodies CCI Decision Tree V1

**Version:** V1.0
**Date:** May 9, 2026
**Status:** STANDALONE — Woodies operates independently
**Architecture:** MODULAR — every stage is editable and re-orderable
**Touch-points with Multi-System:** 6 total — ADVISORY ONLY, NO VETO

---

## 📑 Table of Contents

1. [Core Principles](#1-core-principles)
2. [Configuration Block — Edit Order Here](#2-configuration-block)
3. [Touch-Points Reference](#3-touch-points-reference)
4. [Entry Phase — Stages A1 through A7](#4-entry-phase)
5. [Active Phase — Stages B1 through B14](#5-active-phase)
6. [Terminal States Catalog](#6-terminal-states-catalog)
7. [Editing Guide](#7-editing-guide)

---

<a name="1-core-principles"></a>
## 1. Core Principles

```
═══════════════════════════════════════════════════════════════════════
  
  STANDALONE PRINCIPLE
  ─────────────────────
  Woodies CCI = self-contained decision system.
  Can operate without any other system being online.
  
  TOUCH-POINTS = ADVISORY ONLY
  ────────────────────────────
  6 touch-points query the Multi-System for facts.
  These facts INFORM Woodies' decisions but NEVER OVERRIDE them.
  Multi-System cannot block, force, or vote on Woodies actions.
  
  DEGRADED MODE
  ─────────────
  If Multi-System is unavailable:
    • Day Type query fails → assume NORMAL day
    • POC location query fails → skip Suffering Side check
    • OTF Clarity query fails → skip clarity check
    • Market State query fails → skip partial close logic
  Woodies continues operating with reduced precision.
  
  NO SCORING
  ──────────
  All decisions are BINARY (Yes/No).
  No weighted sums, no thresholds, no 0-100 scores.
  Each check returns: PASS / FAIL / SKIP.
  
  PRIORITY HIERARCHY (in Active Phase)
  ─────────────────────────────────────
  1. Absolute Exits (Stop, EOD)
  2. Strategic Exits (Color flip)
  3. Touch-point Advisories (Suffering, OTF, Market State)
  4. Time Stops
  5. Target Milestones (T1/T2/T3)
  6. Tightening (Counter-patterns, Color shifts)
  7. Hold
  
═══════════════════════════════════════════════════════════════════════
```

---

<a name="2-configuration-block"></a>
## 2. Configuration Block — Edit Order Here

To re-order stages, edit this YAML block. The engine reads stage order from here.
To disable a stage, set `enabled: false`. To add a new stage, append it here.

```yaml
woodies_tree_v1:
  
  entry_phase:
    - id: A1_strategic_gate
      type: woodies_core
      enabled: true
      reorder_priority: 1
    
    - id: A2_day_type_query
      type: touch_point
      enabled: true
      reorder_priority: 2
      target_system: multi_system
      query: day_type
      blocking: false  # advisory only
    
    - id: A3_pattern_detection
      type: woodies_core
      enabled: true
      reorder_priority: 3
    
    - id: A4_poc_suffering_query
      type: touch_point
      enabled: true
      reorder_priority: 4
      target_system: multi_system
      query: [poc_location, suffering_side]
      blocking: false  # advisory only
    
    - id: A5_otf_clarity_query
      type: touch_point
      enabled: true
      reorder_priority: 5
      target_system: multi_system
      query: otf_clarity_state
      blocking: false  # advisory only
    
    - id: A6_entry_classification
      type: woodies_core
      enabled: true
      reorder_priority: 6
    
    - id: A7_universal_checks
      type: woodies_core
      enabled: true
      reorder_priority: 7
  
  active_phase:
    - id: B1_stop_check
      type: woodies_core
      enabled: true
      priority_class: ABSOLUTE_EXIT
    
    - id: B2_eod_check
      type: woodies_core
      enabled: true
      priority_class: ABSOLUTE_EXIT
    
    - id: B3_color_flip
      type: woodies_core
      enabled: true
      priority_class: STRATEGIC_EXIT
    
    - id: B4_poc_migration_query
      type: touch_point
      enabled: true
      target_system: multi_system
      query: poc_migration
      blocking: false  # advisory
      priority_class: ADVISORY_EXIT
    
    - id: B5_otf_mid_trade_query
      type: touch_point
      enabled: true
      target_system: multi_system
      query: otf_clarity_state
      blocking: false  # advisory
      priority_class: ADVISORY_EXIT
    
    - id: B6_news_window
      type: woodies_core
      enabled: true
      priority_class: ABSOLUTE_EXIT
    
    - id: B7_time_stop
      type: woodies_core
      enabled: true
      priority_class: TIME_EXIT
    
    - id: B8_counter_pattern
      type: woodies_core
      enabled: true
      priority_class: TIGHTEN
    
    - id: B9_market_state_query
      type: touch_point
      enabled: true
      target_system: multi_system
      query: market_state
      blocking: false  # advisory
      priority_class: PARTIAL
    
    - id: B10_t1_milestone
      type: woodies_core
      enabled: true
      priority_class: TARGET
    
    - id: B11_t2_milestone
      type: woodies_core
      enabled: true
      priority_class: TARGET
    
    - id: B12_t3_milestone
      type: woodies_core
      enabled: true
      priority_class: TARGET
    
    - id: B13_trail_check
      type: woodies_core
      enabled: true
      priority_class: TRAIL
    
    - id: B14_hold
      type: woodies_core
      enabled: true
      priority_class: NO_ACTION
      always_last: true
```

---

<a name="3-touch-points-reference"></a>
## 3. Touch-Points Reference (6 Total — All Advisory)

```
╔═════╦══════════╦═════════════════════════╦══════════════════════════════╗
║ ID  ║ Phase    ║ Queries from M-S         ║ How Woodies uses it           ║
╠═════╬══════════╬═════════════════════════╬══════════════════════════════╣
║ A2  ║ Entry    ║ Day Type                 ║ Filter pattern relevance      ║
║     ║          ║                          ║ (TREND→Trend-Confirm prefer.) ║
║     ║          ║                          ║ NEVER blocks entry             ║
╠═════╬══════════╬═════════════════════════╬══════════════════════════════╣
║ A4  ║ Entry    ║ POC location +           ║ Classify Reactive vs Init.    ║
║     ║          ║ Suffering Side           ║ + warn if suffering side       ║
║     ║          ║                          ║ NEVER blocks entry             ║
╠═════╬══════════╬═════════════════════════╬══════════════════════════════╣
║ A5  ║ Entry    ║ OTF Clarity State        ║ Warn if State 4                ║
║     ║          ║                          ║ NEVER blocks entry             ║
╠═════╬══════════╬═════════════════════════╬══════════════════════════════╣
║ B4  ║ Active   ║ POC migration            ║ Warn if POC crossed against   ║
║     ║          ║                          ║ NEVER auto-exits               ║
╠═════╬══════════╬═════════════════════════╬══════════════════════════════╣
║ B5  ║ Active   ║ OTF Clarity State        ║ Warn if State 4 mid-trade     ║
║     ║          ║                          ║ NEVER auto-exits               ║
╠═════╬══════════╬═════════════════════════╬══════════════════════════════╣
║ B9  ║ Active   ║ Market State             ║ Suggest partial close          ║
║     ║          ║                          ║ NEVER auto-exits               ║
╚═════╩══════════╩═════════════════════════╩══════════════════════════════╝
```

**Key:** "Advisory" means the touch-point produces a warning/suggestion that Woodies' core logic can choose to act on or ignore based on its own rules. Multi-System never directly closes a trade or blocks an entry.

---

<a name="4-entry-phase"></a>
## 4. Entry Phase — Stages A1 through A7

### Stage A1 — Strategic Gate

```
ID:           A1_strategic_gate
Type:         🎨 Woodies Core (independent decision)
Editable:     ✅ YES
Reorderable:  ✅ YES (typically first in Entry Phase)
Touch-point:  ❌ NO
```

**Purpose:** Determine which trade direction is allowed today based on CCI 14 vs Zero Line behavior over 6+ bars.

**Inputs:**
- `cci_14_value` (float, current bar)
- `cci_14_history` (last 10 bars)
- `zero_line` (constant: 0)

**Logic:**
```
IF cci_14 > 0 for 6+ consecutive bars → color = BLUE → LONG allowed, SHORT blocked
IF cci_14 < 0 for 6+ consecutive bars → color = RED → SHORT allowed, LONG blocked
IF cci_14 crosses 0 frequently in last 10 bars → color = GREY → wait
IF cci_14 changes from sustained trend to opposite → color = YELLOW → stand aside
ELSE → color = INDETERMINATE → wait
```

**Outputs:**
- `direction_allowed`: LONG | SHORT | NONE
- `color`: BLUE | RED | GREY | YELLOW | INDETERMINATE

**Terminal States from this stage:**
- 🟡 SKIP — color veto (GREY/YELLOW/INDETERMINATE)

**Edit notes:**
- To change persistence threshold (currently 6 bars), edit `bars_persistence_required` parameter.
- To remove YELLOW state and merge into GREY, edit `yellow_detection: false`.

---

### Stage A2 — Day Type Query (Touch-Point)

```
ID:           A2_day_type_query
Type:         🔗 Touch-Point (advisory only)
Editable:     ✅ YES
Reorderable:  ✅ YES
Blocking:     ❌ NO (NEVER vetoes)
Target:       Multi-System
```

**Purpose:** Query Multi-System for today's Day Type to filter which Woodies patterns are most relevant.

**Inputs:**
- Query to Multi-System endpoint: `/day-type/current`

**Logic:**
```
day_type = query(multi_system, "day_type")

IF day_type == TREND_DAY:
  → prefer Trend-Confirming patterns (ZLR, TT, TLB, GB100)
  → assume color stable, set color_volatility_expectation = LOW

IF day_type == RANGE_DAY:
  → prefer Reactive patterns (HFE, FAMIR at extremes)
  → assume color may flip, set color_volatility_expectation = HIGH

IF day_type == REVERSAL_DAY:
  → prefer New-Trend patterns (VEGAS, GHOST, FAMIR)
  → expect color shifts

IF day_type == GAP_FILL:
  → bias toward Initiative (target = PDC)

IF day_type == BROAD_CHANNEL:
  → prefer Reactive at channel extremes

IF day_type == NEUTRAL or unavailable:
  → no preference (use degraded mode)
```

**Outputs:**
- `pattern_preference`: list of preferred pattern IDs
- `color_volatility_expectation`: LOW | MEDIUM | HIGH

**Degraded mode (if M-S unavailable):**
- Default to no preference (all patterns equally weighted)
- Continue to A3 with no filter applied

**Terminal States from this stage:** None (advisory only)

**Edit notes:**
- To change pattern preferences per day type, edit `pattern_preferences` map.
- To disable this touch-point entirely, set `enabled: false` in config block.

---

### Stage A3 — Pattern Detection

```
ID:           A3_pattern_detection
Type:         🎨 Woodies Core (independent decision)
Editable:     ✅ YES
Reorderable:  ✅ YES
Touch-point:  ❌ NO
```

**Purpose:** Detect if any of the 9 Woodies patterns is currently triggered.

**Inputs:**
- `cci_14_history` (last 30 bars)
- `cci_zero_line_distance`
- `cci_extremes` (touches of ±100, ±200)
- `cci_trend_lines` (calculated from history)
- `ema_13_34_89_state` (for VEGAS detection)

**Logic — 9 patterns scanned in parallel:**

```
TREND-CONFIRMING patterns (require BLUE or RED color from A1):
  ZLR (Zero Line Reject):
    CCI approaches ZL from trend side, rejected, returns
  
  TT (Tony Trade):
    CCI crosses ±100, returns past it within N bars
  
  TLB (Trend Line Break):
    CCI breaks trend line drawn on CCI itself (in trend direction)
  
  GB100 (Ghost Bar at ±100):
    CCI consolidates at ±100 for 1-2 bars, then breaks in trend dir.

NEW-TREND patterns (require color transition):
  VEGAS:
    EMAs 13/34/89 converge then spread in new direction
  
  GHOST:
    Color changes (BLUE→RED or RED→BLUE), CCI clusters around ZL,
    then continues in new direction
  
  FAMIR (False Move + Immediate Reversal):
    False breakout one direction, sudden entry opposite
  
  HTLB (Horizontal Trend Line Break):
    Horizontal line at ±100 broken, signaling new trend start
  
  HFE (Hook From Extreme):
    CCI reaches ±200, hooks back — strong reversal signal
```

**Outputs:**
- `pattern_matched`: pattern ID or NONE
- `pattern_category`: TREND_CONFIRMING | NEW_TREND | NONE
- `pattern_direction`: LONG | SHORT | NONE

**Terminal States from this stage:**
- 🟡 WAIT — no pattern matched

**Edit notes:**
- Each of the 9 patterns is an independent sub-module. Disable individually with `pattern_enabled: false`.
- To add a new pattern, append to `patterns_list` with detection logic.
- To change pattern categories (Trend-Confirming vs New-Trend), edit `pattern_category_map`.

---

### Stage A4 — POC + Suffering Side Query (Touch-Point)

```
ID:           A4_poc_suffering_query
Type:         🔗 Touch-Point (advisory only)
Editable:     ✅ YES
Reorderable:  ✅ YES
Blocking:     ❌ NO (NEVER vetoes — only informs)
Target:       Multi-System
```

**Purpose:** Get POC location and Suffering Side info to classify entry type and warn on thesis risk.

**Inputs:**
- Query to Multi-System: `/poc/current`, `/suffering-side/check`
- `entry_direction` (from A3)
- `current_price`

**Logic:**
```
poc_location = query(multi_system, "poc_current")
suffering_check = query(multi_system, "suffering_side", direction=entry_direction)

# Classification — input to A6
IF current_price within 3pt of IB/VA edge:
  → entry_classification_hint = REACTIVE

IF current_price near middle + POC migrating in entry_direction:
  → entry_classification_hint = INITIATIVE

# Warning — does NOT block
IF suffering_check == TRUE and not (in UFL or UFH):
  → warning_flag = SUFFERING_SIDE
  → Woodies core decides whether to skip (per its rules)

IF in UFL/UFH zone:
  → warning_flag = NONE (bypass active)
```

**Outputs:**
- `entry_classification_hint`: REACTIVE | INITIATIVE | UNCLEAR
- `suffering_warning`: SUFFERING_SIDE | NONE
- `bypass_active`: UFL | UFH | NONE

**Degraded mode (if M-S unavailable):**
- `entry_classification_hint` = INITIATIVE (default safe assumption)
- Skip suffering side warning entirely

**Terminal States from this stage:** None (advisory only)

**Note on advisory nature:** Even if `suffering_warning = SUFFERING_SIDE`, Woodies' core logic may still proceed if other conditions strongly justify. The warning is logged but does not auto-skip. If user wants strict suffering-side blocking, configure A4 with `convert_warning_to_skip: true` (currently `false`).

**Edit notes:**
- To make suffering side a hard block, set `convert_warning_to_skip: true`.
- To change UFL/UFH bypass logic, edit `bypass_zones` parameter.

---

### Stage A5 — OTF Clarity Query (Touch-Point)

```
ID:           A5_otf_clarity_query
Type:         🔗 Touch-Point (advisory only)
Editable:     ✅ YES
Reorderable:  ✅ YES
Blocking:     ❌ NO (NEVER vetoes — only warns)
Target:       Multi-System
```

**Purpose:** Get OTF Clarity State to warn on chaotic market conditions.

**Inputs:**
- Query to Multi-System: `/otf-clarity/state`

**Logic:**
```
otf_state = query(multi_system, "otf_clarity")

IF otf_state == 1 (BOTH_CLEAR):
  → clarity_warning = NONE → safe to proceed

IF otf_state == 2 (SELLERS_CLEAR) and entry_direction == LONG:
  → clarity_warning = NONE → safe (suffering = sellers)

IF otf_state == 3 (BUYERS_CLEAR) and entry_direction == SHORT:
  → clarity_warning = NONE → safe

IF otf_state == 4 (UNCLEAR):
  → clarity_warning = NO_CLARITY
  → Woodies core decides (typically skips, but configurable)

IF otf_state mismatched with direction:
  → clarity_warning = DIRECTION_MISMATCH
```

**Outputs:**
- `clarity_warning`: NONE | NO_CLARITY | DIRECTION_MISMATCH
- `otf_state_value`: 1 | 2 | 3 | 4 | UNAVAILABLE

**Degraded mode (if M-S unavailable):**
- Skip clarity check entirely, proceed to A6

**Terminal States from this stage:** None (advisory only)

**Note:** Even with `clarity_warning = NO_CLARITY`, Woodies can still trade if pattern is exceptionally strong (e.g., HFE from ±200 with FAMIR confirmation). The advisory is logged.

**Edit notes:**
- To make State 4 a hard block, set `state_4_hard_block: true`.
- To change which directions are allowed per state, edit `direction_state_map`.

---

### Stage A6 — Entry Classification

```
ID:           A6_entry_classification
Type:         🎨 Woodies Core (independent decision)
Editable:     ✅ YES
Reorderable:  ✅ YES
Touch-point:  ❌ NO (uses A4 hint as input but decides independently)
```

**Purpose:** Final classification of entry as REACTIVE or INITIATIVE, which determines management style.

**Inputs:**
- `pattern_matched` (from A3)
- `entry_classification_hint` (from A4, optional)
- `direction`

**Logic:**
```
# Pattern-based classification (Woodies' own rules)
IF pattern in [HFE, FAMIR, TT_at_extreme]:
  → classification = REACTIVE

IF pattern in [VEGAS, GHOST, TLB, HTLB, ZLR_mid_trend]:
  → classification = INITIATIVE

# A4 hint can confirm but not override
IF A4_hint == REACTIVE and pattern allows both:
  → classification = REACTIVE

IF A4_hint == INITIATIVE and pattern allows both:
  → classification = INITIATIVE

IF conflict between pattern and A4_hint:
  → use pattern-based decision (Woodies wins)
```

**Outputs:**
- `entry_classification`: REACTIVE | INITIATIVE
- `position_size`: 2 (Reactive) | 3 (Initiative) — based on classification
- `management_profile`: TIGHT (Reactive) | WIDE (Initiative)

**Terminal States from this stage:** None (continues to A7)

**Edit notes:**
- To change which patterns map to which classification, edit `pattern_classification_map`.
- To allow A4 hint to override pattern decision, set `a4_hint_overrides_pattern: true`.

---

### Stage A7 — Universal Pre-Entry Checks

```
ID:           A7_universal_checks
Type:         🎨 Woodies Core (independent decision)
Editable:     ✅ YES
Reorderable:  ✅ YES (but typically last in Entry Phase)
Touch-point:  ❌ NO
```

**Purpose:** Final non-Woodies-specific safety checks before entry execution.

**Inputs:**
- `news_calendar`
- `cool_down_state`
- `daily_pnl`
- `proposed_stop_pts`
- `bridge_health`
- `time_to_eod`

**Logic:**
```
checks_to_run:
  - news_window_check (±5min)
  - cool_down_active
  - daily_loss_cap_hit ($200)
  - stop_within_3_to_8_pts (D-001 cap)
  - bridge_status == healthy
  - eod_distance > 60min (don't start late)

IF any check fails → SKIP with reason
IF all pass → execute entry
```

**Outputs:**
- `entry_approved`: TRUE | FALSE
- `skip_reason`: enum (if FALSE)

**Terminal States from this stage:**
- 🟡 SKIP — universal block (with reason)
- 🟢 BUY (LONG) — if direction == LONG
- 🔴 SELL (SHORT) — if direction == SHORT

**Edit notes:**
- Each check is independent and can be enabled/disabled.
- To add new universal check, append to `checks_to_run` list.
- To change daily loss cap, edit `daily_loss_cap_usd`.
- To change stop range (3-8pt), edit `stop_min_pt` and `stop_max_pt`.

---

<a name="5-active-phase"></a>
## 5. Active Phase — Stages B1 through B14

> **Priority hierarchy:** Each stage runs in priority class order. Higher priority class wins. Within same class, order matters (earliest in config wins).

### Stage B1 — Stop Check

```
ID:               B1_stop_check
Type:             🎨 Woodies Core
Priority Class:   ABSOLUTE_EXIT (highest)
Editable:         ✅ YES (logic), ❌ NO (priority class)
```

**Purpose:** Check if stop has been hit.

**Inputs:** `current_price`, `stop_price`, `direction`

**Logic:**
```
IF direction == LONG and current_price <= stop_price → STOP_HIT
IF direction == SHORT and current_price >= stop_price → STOP_HIT
```

**Terminal:** 🔴 CLOSE ALL + cool-down 30min

---

### Stage B2 — EOD Check

```
ID:               B2_eod_check
Type:             🎨 Woodies Core
Priority Class:   ABSOLUTE_EXIT
Editable:         ✅ YES (time threshold)
```

**Purpose:** Force flatten before market close.

**Inputs:** `current_time_et`

**Logic:**
```
IF current_time_et >= "15:59" → EOD_FORCE
```

**Terminal:** 🔴 CLOSE ALL — EOD force (no overnight, D-002)

**Edit notes:**
- To change EOD time, edit `eod_force_time`.

---

### Stage B3 — Color Flip Check

```
ID:               B3_color_flip
Type:             🎨 Woodies Core (Strategic Gate broken)
Priority Class:   STRATEGIC_EXIT
Editable:         ✅ YES
```

**Purpose:** Detect if Strategic Gate (color) flipped against position.

**Inputs:** `current_color`, `entry_color`, `direction`

**Logic:**
```
IF direction == LONG and entry_color == BLUE and current_color == RED → FLIP
IF direction == SHORT and entry_color == RED and current_color == BLUE → FLIP
IF current_color in [YELLOW, GREY] for N bars → DEGRADATION (configurable)
```

**Terminal:** 🔴 CLOSE ALL — Strategic Exit

**Edit notes:**
- YELLOW/GREY response is configurable: `degradation_action: TIGHTEN | EXIT`
- To require N consecutive bars before flip exit, edit `flip_confirmation_bars`.

---

### Stage B4 — POC Migration Query (Touch-Point)

```
ID:               B4_poc_migration_query
Type:             🔗 Touch-Point (advisory only)
Priority Class:   ADVISORY_EXIT
Editable:         ✅ YES
Blocking:         ❌ NO (NEVER auto-exits — only warns)
```

**Purpose:** Check if POC has crossed against the position (Suffering Side flip).

**Inputs:** Query Multi-System: `/poc/migration`, `direction`, `entry_price`, `current_price`

**Logic:**
```
poc_location = query(multi_system, "poc_current")

IF direction == LONG and current_price < poc_location and not in UFL:
  → suffering_warning = SUFFERING_FLIP
  → Woodies core decides exit (default: YES if pattern weakening, else HOLD)

IF direction == SHORT and current_price > poc_location and not in UFH:
  → suffering_warning = SUFFERING_FLIP

IF in UFL/UFH bypass zone:
  → suffering_warning = NONE
```

**Outputs:** `suffering_flip_warning`: SUFFERING_FLIP | NONE

**Default action when warning fires:** Tighten stop to entry. NOT auto-exit.

**To make this auto-exit:** set `auto_exit_on_suffering_flip: true` in config.

**Degraded mode:** Skip entirely if M-S unavailable.

---

### Stage B5 — OTF Clarity Mid-Trade (Touch-Point)

```
ID:               B5_otf_mid_trade_query
Type:             🔗 Touch-Point (advisory only)
Priority Class:   ADVISORY_EXIT
Editable:         ✅ YES
Blocking:         ❌ NO (NEVER auto-exits — only warns)
```

**Purpose:** Check if OTF state degraded to State 4 mid-trade.

**Inputs:** Query Multi-System: `/otf-clarity/state`

**Logic:**
```
otf_state = query(multi_system, "otf_clarity")

IF otf_state == 4:
  → clarity_warning = NO_CLARITY_MID_TRADE
  → Woodies core decides (default: tighten, not exit)
```

**Default action:** Tighten stop. NOT auto-exit.

**Degraded mode:** Skip entirely.

---

### Stage B6 — News Window

```
ID:               B6_news_window
Type:             🎨 Woodies Core
Priority Class:   ABSOLUTE_EXIT
Editable:         ✅ YES
```

**Purpose:** Force exit before high-impact news event.

**Inputs:** `news_calendar`, `current_time`

**Logic:**
```
IF Tier 1 news within ±5min → CLOSE ALL
IF Tier 2 news within ±5min and position size > 1 → reduce to 1 contract
```

**Terminal:** 🔴 CLOSE ALL — News emergency

---

### Stage B7 — Time Stop

```
ID:               B7_time_stop
Type:             🎨 Woodies Core
Priority Class:   TIME_EXIT
Editable:         ✅ YES (duration)
```

**Purpose:** Exit if no T1 hit within time threshold (no momentum).

**Inputs:** `entry_timestamp`, `current_timestamp`, `t1_hit`

**Logic:**
```
elapsed_minutes = (current_time - entry_time) / 60
IF elapsed_minutes >= 60 and not t1_hit → TIME_STOP
```

**Terminal:** 🔴 CLOSE ALL — Time stop

**Edit notes:**
- To change duration (currently 60min), edit `time_stop_minutes`.

---

### Stage B8 — Counter-Pattern Detection

```
ID:               B8_counter_pattern
Type:             🎨 Woodies Core
Priority Class:   TIGHTEN
Editable:         ✅ YES
```

**Purpose:** Detect counter-patterns that warn of reversal (but don't trigger exit).

**Inputs:** `cci_14_history`, `current_color`, `direction`

**Logic:**
```
counter_patterns = scan_for([HFE_against, TT_against, FAMIR_against])

IF counter_pattern detected:
  → action = TIGHTEN_STOP
  → tighten_destination = depends on T1/T2 status:
      pre-T1: stop → 50% of T1 distance
      post-T1: stop → entry
      post-T2: stop → T1 level
```

**Action:** 🔄 TIGHTEN STOP (no close)

---

### Stage B9 — Market State Query (Touch-Point)

```
ID:               B9_market_state_query
Type:             🔗 Touch-Point (advisory only)
Priority Class:   PARTIAL
Editable:         ✅ YES
Blocking:         ❌ NO (NEVER auto-exits — only suggests partial)
```

**Purpose:** Detect momentum loss to suggest partial close.

**Inputs:** Query Multi-System: `/market-state`

**Logic:**
```
state = query(multi_system, "market_state")
prev_state = previous_query_result

IF prev_state == EXTENDING and state == SEARCHING:
  → momentum_warning = LOST
  → suggest: partial close C2 early, hold C3 trail
```

**Default action:** Partial close C2 if T1 already hit. Hold C3.

**Degraded mode:** Skip.

---

### Stage B10 — T1 Milestone

```
ID:               B10_t1_milestone
Type:             🎨 Woodies Core
Priority Class:   TARGET
Editable:         ✅ YES (BE policy)
```

**Purpose:** Handle T1 hit event.

**Inputs:** `current_price`, `t1_price`, `direction`, `entry_classification`, `t1_already_hit`

**Logic:**
```
IF (direction == LONG and current_price >= t1_price) or
   (direction == SHORT and current_price <= t1_price):
   
  IF not t1_already_hit:
    → close C1 (1 contract)
    → ⚠️ DO NOT MOVE STOP (D-002: T1 = stop-hunt zone)
    → mark t1_already_hit = true
```

**Action:** 💰 Close C1 + NO BE move

**Edit notes:**
- D-002 mandates NO BE on T1. To override (NOT recommended), set `move_be_on_t1: true`.

---

### Stage B11 — T2 Milestone

```
ID:               B11_t2_milestone
Type:             🎨 Woodies Core
Priority Class:   TARGET
Editable:         ✅ YES (BE policy, classification logic)
```

**Purpose:** Handle T2 hit event.

**Inputs:** `current_price`, `t2_price`, `direction`, `entry_classification`

**Logic:**
```
IF T2 hit:
  IF entry_classification == REACTIVE:
    → close ALL (no runner — Reactive = mean reversion target)
    → terminal: 💰 SUCCESS — Reactive Win
  
  IF entry_classification == INITIATIVE:
    → close C2 (1 contract)
    → ✅ Smart BE: move stop to entry (D-055)
    → activate C3 trail mode
```

**Edit notes:**
- D-055 mandates Smart BE on T2 only. To change BE policy, edit `be_policy`.
- To allow Reactive runner, set `reactive_runner_enabled: true`.

---

### Stage B12 — T3 Milestone

```
ID:               B12_t3_milestone
Type:             🎨 Woodies Core
Priority Class:   TARGET
Editable:         ✅ YES
```

**Purpose:** Handle T3 hit event (Initiative only).

**Inputs:** `current_price`, `t3_price`

**Logic:**
```
IF T3 hit:
  → close C3
  → terminal: 💰 SUCCESS — Initiative Full Win
```

---

### Stage B13 — Trail Check (Post-T2 Initiative)

```
ID:               B13_trail_check
Type:             🎨 Woodies Core
Priority Class:   TRAIL
Editable:         ✅ YES
```

**Purpose:** Vegas trail logic for C3 runner.

**Inputs:** `vegas_ema_169`, `current_price`, `direction`, `t2_already_hit`

**Logic:**
```
IF t2_already_hit and trail_mode_active:
  IF direction == LONG and current_price crosses below vegas_ema_169:
    → close C3
    → terminal: 💰 Trail Exit
  
  IF direction == SHORT and current_price crosses above vegas_ema_169:
    → close C3
    → terminal: 💰 Trail Exit
```

**Edit notes:**
- To change trail indicator (currently EMA 169), edit `trail_indicator`.

---

### Stage B14 — Hold (Default No-Action)

```
ID:               B14_hold
Type:             🎨 Woodies Core
Priority Class:   NO_ACTION
Editable:         ❌ NO (always last)
```

**Purpose:** Default state when no other stage triggers an action.

**Action:** 🟡 HOLD — wait for next bar update.

---

<a name="6-terminal-states-catalog"></a>
## 6. Terminal States Catalog

```
ENTRY PHASE — 5 outcomes:
  🟡 SKIP — Color veto (A1)
  🟡 SKIP — No pattern (A3)
  🟡 SKIP — Universal block (A7)
  🟢 BUY  (LONG) — A7 approves with direction LONG
  🔴 SELL (SHORT) — A7 approves with direction SHORT

ACTIVE PHASE — 12 outcomes:
  🔴 STOP LOSS         (B1)
  🔴 EOD FORCE         (B2)
  🔴 STRATEGIC EXIT    (B3 — color flip)
  🔴 SUFFERING EXIT    (B4 — only if convert_warning_to_exit=true)
  🔴 CLARITY EXIT      (B5 — only if convert_warning_to_exit=true)
  🔴 NEWS EXIT         (B6)
  🔴 TIME STOP         (B7)
  🔄 TIGHTEN           (B3 degradation, B4 default, B5 default, B8)
  💰 PARTIAL           (B9 — momentum loss)
  💰 SUCCESS Reactive  (B11 — Reactive T2)
  💰 SUCCESS Initiative (B12 — T3)
  💰 SUCCESS Trail     (B13 — Vegas exit)
  🟡 HOLD              (B14 — default)
```

---

<a name="7-editing-guide"></a>
## 7. Editing Guide

### How to re-order stages
1. Open this file's Configuration Block (Section 2).
2. Move the YAML entry to the desired position.
3. The engine reads order from the YAML at startup.

### How to disable a stage
1. In the Configuration Block, set `enabled: false` for that stage.
2. The engine skips it. No code changes needed.

### How to add a new stage
1. Add YAML entry in the Configuration Block with new ID.
2. Add a new section (Section 4 or 5) with full spec following the template.
3. Add detection/decision logic to the engine module that matches the ID.

### How to change a touch-point's blocking behavior
1. Locate the touch-point stage (A2, A4, A5, B4, B5, B9).
2. Change `blocking: false` → `blocking: true` to make it veto-capable.
3. **Warning:** This violates the standalone principle. Use only with deliberate decision.

### How to convert advisory warning to hard exit
1. For B4: set `auto_exit_on_suffering_flip: true`.
2. For B5: set `state_4_auto_exit: true`.
3. For B9: set `state_change_auto_partial: true`.

### How to change priority hierarchy
1. Edit `priority_class` for any stage (ABSOLUTE_EXIT, STRATEGIC_EXIT, ADVISORY_EXIT, TIME_EXIT, TARGET, TIGHTEN, PARTIAL, TRAIL, NO_ACTION).
2. Within same class, order in YAML determines which runs first.

### How to add new pattern to A3
1. Add pattern detection logic to `patterns_list` in A3.
2. Specify category (TREND_CONFIRMING or NEW_TREND).
3. Specify direction logic.
4. Update A6's `pattern_classification_map`.

---

## Document History

| Version | Date | Change |
|---------|------|--------|
| V1.0 | May 9, 2026 | Initial — STANDALONE Woodies tree, 6 advisory touch-points, fully modular architecture |

---

**End of MEMS26_WOODIES_DECISION_TREE_V1.md**
