# Handoff to Claude Desktop · Pkg 3a Stream 1 (EXIT_V6 fix · Neutral split)

**Date:** 2026-05-23 20:25 IL
**From:** Michael (via Cursor agent · G3 PASS on Pkg 0/1/2a)
**To:** Claude Desktop
**Task:** Write the full MEGA prompt for Claude Code (CC) to execute Pkg 3a Stream 1 · split `DayType.Neutral` into `Neutral_Extreme` + `Neutral_Center` per EXIT_V6 and D-091.Q1.
**Authority:** D-091 §Pkg 3a sub-decisions Q1 + EXIT_V6 §Time Stop windows + Master Summary Sheet 3

---

## 0 · Pkg 2a G3 verdict · PASS

Pkg 2a finished. G3 review: 12/12 ✅, 20 tests green (+11 new), 517 backend tests no-regression, lines 205-207 byte-identical (chronic toxicity preserved). Family mapping verified: `REACTIVE→"Reactive"(1.0×)`, `INITIATIVE→"OFA"(1.5×)`. Spec verbatim from Master Sheet 2 rows 3-6.

Pkg 2bc blocked on Zohar reply (`docs/handoff/ZOHAR_PKG2BC_SPEC_CLARIFICATION.md`).

Pkg 3a is next non-blocked Pipeline 1 package. Sequenced as Stream 1 (this handoff · enum split + plumbing · ~3-4h CC) → Stream 2 (deferred · day_type_targets module + wiring · 1d CC).

---

## 1 · Pkg 3a Stream 1 scope · Neutral enum split

Replace single `DayType.Neutral` (45min · no internal distinction) with **two day types** per EXIT_V6 §Time Stop windows:

| Day Type | Code | Time Stop window | Open price relative to yesterday's VA |
|----------|------|------------------|----------------------------------------|
| Neutral Extreme | NeuE | 45 min | At or outside yesterday's VAH/VAL (±1 tick of VA edge or beyond) |
| Neutral Center  | NeuC | 30 min | Inside yesterday's VA, closer to POC than either VA edge |

This is the EXIT_V6 fix (pre-flight #12 in STATUS_BOARD V2 · long-pending). It also unblocks Pipeline 3 (S1 verify · `compliance_manifest.yaml` E2 PARTIAL → IMPLEMENTED).

### ⚠️ Authority hierarchy

> **D-091 §Pkg 3a sub-decisions §Q1 is AUTHORITY for classification rule.**
> **EXIT_V6 §Time Stop windows is AUTHORITY for window values (NeuE=45min · NeuC=30min · NT=NO TRADE).**
> **Tests in §4 of this handoff are AUTHORITY on conflicts.**
> **If conflict — TESTS WIN. STOP and report if any test cannot be satisfied.**

### Spec verbatim (from D-091 §Pkg 3a sub-decisions · LOCKED 23/5 20:10 IL)

**D-091.Q1 · LOCKED:**
- `NeuE` = cash open price is at or outside yesterday's VAH/VAL (within ±1 tick of VA edge or beyond)
- `NeuC` = cash open price is inside yesterday's Value Area, closer to POC than either VA edge
- Data source: yesterday's VA bounds (VAH · POC · VAL) — available via `backend/v9/systems/day_type/prev_day.py::load_tpo_previous_day_summary()` which returns dict with `vah` and `val` from `v9_tpo_sessions`
- **Fallback when S5 VA unavailable at classification time:** classify as **NeuC** (safer · 30min window · shorter Type C exposure). Log `[S1] NeuE/NeuC fallback to NeuC · VA missing` at info level (rate-limited once per session)

**EXIT_V6 §Time Stop windows verbatim (locked 23/5 17:30):**

| Day Type | Code | Window | Action at expiry |
|----------|------|--------|------------------|
| Trend Normal | TN | None | never · ride the trail |
| Trend DD | TDD | 90 min | DD → market exit · else ride |
| Variation | NV | 60 min | DD → market exit · else ride |
| Neutral Extreme | NeuE | 45 min | DD → market exit · else ride |
| Neutral Center | NeuC | 30 min | DD → market exit · else ride |
| Normal | Norm | 30 min | DD → market exit · else ride |
| Nontrend | NT | n/a | **NO TRADE** at all |

---

## 2 · Files in scope

### MODIFY (precise edits · authoritative blast radius)

1. **`backend/v9/systems/day_type/schemas.py`** lines 19-26 · add 2 enum members
2. **`backend/v9/systems/day_type/state_machine.py`** lines 83 · 86 · 139 · 550 · 564 · 653 · **6 hits to split** (line 535 `_rescore_from_behavior` is **DEFERRED to Stream 1.5** per Michael · do NOT modify line 535 in Stream 1)
3. **`backend/v9/systems/day_type/targets_table.py`** lines 15 (docstring table) · 22-25 (`DAY_TYPES` set) · 81-93 (`_TARGETS["Neutral"]` row) · 94-106 (`_TARGETS["Nontrend"]`) · 110-118 (`_ALIASES`)
4. **`backend/v9/systems/day_type/api.py`** line 190 · `day_type = "Neutral"` hardcoded
5. **`backend/v9/systems/day_type/compliance_manifest.yaml`** lines 100-105 (E2) · line 118 (output_fields enum)
6. **`backend/v9/layer3/entry_executor.py`** line 61 · `DAY_TYPE_TARGETS["Neutral"]` row
7. **`backend/v9/systems/day_type/zohar_rules.py`** lines 120-130 · `evaluate_delta()` docstring (informational · no code change · update comment to reflect NeuE/NeuC split)

### WRITE NEW

8. **`backend/v9/systems/day_type/neutral_classifier.py`** (~80-100 LOC) — single helper `classify_neutral_subtype()` per Q1 rule + fallback
9. **`tests/v9/systems/test_day_type/test_neutral_classifier.py`** (~150-200 LOC · 8+ golden tests)
10. **`tests/v9/systems/test_day_type/test_targets_table_v6.py`** (~80-120 LOC · 7+ tests · one per day type)

### UPDATE EXISTING TESTS

11. **`tests/v9/compliance/test_day_type_compliance.py`** lines 257-263 (`test_E2_day_types`) — expect 7 types
12. **`backend/v9/tests/e2e/test_day_type_e2e.py`** line 103+ (Scenario 5 Neutral) — update to verify NeuE OR NeuC assignment based on synthetic VA
13. **`backend/v9/tests/test_day_type_history_model.py`** line 83 — accept both `"Neutral"` (deprecated · legacy DB rows) and new `"Neutral_Center"`/`"Neutral_Extreme"`
14. **`backend/v9/tests/test_zohar_rules.py`** line 46 — docstring update only (delta rule still triggers DOWNGRADE · subtype determined elsewhere)
15. **`backend/v9/tests/fixtures/day_type/synthetic_bars.py`** line 119 — docstring update only

### FORBIDDEN — do NOT touch

- `backend/v9/systems/five_min/` (entire dir · Stream 2 scope)
- `backend/v9/systems/footprint/`, `woodies/`, `tpo/`, `killzone/` (other systems)
- `backend/v9/services/trade_manager/` (Pkg 6 territory)
- `backend/v9/services/sierra_command.py` (Pipeline 5)
- `frontend/`, `bridge/`, `sc_study/`
- `backend/main.py`, `backend/v9/app.py`
- 🛑 `backend/v9/systems/day_type/state_machine.py` lines outside the 7 documented Neutral hits — surgical edits only

---

## 3 · API contract for `neutral_classifier.py`

```python
"""neutral_classifier.py — NeuE vs NeuC classification per D-091.Q1.

Decides between Neutral_Extreme (open at VA edge · 45min window) and
Neutral_Center (open inside VA · 30min window). Used by:
  - state_machine.py::_rescore_from_behavior (replaces `return DayType.Neutral`)
  - api.py::190 (post-IB heuristic when both_sides extension detected)

Fallback rule: if yesterday's VA bounds unavailable, returns Neutral_Center
(the safer / less aggressive choice · 30min window). Logs once per session.
"""
import logging
from typing import Optional

from .schemas import DayType

logger = logging.getLogger(__name__)

# 1 MES tick = 0.25 point (used as edge tolerance for VAH/VAL test)
EDGE_TOLERANCE_PT = 0.25

# Singleton to rate-limit fallback warning to once per session
_fallback_logged_for_date: Optional[str] = None


def classify_neutral_subtype(
    *,
    session_open_price: Optional[float],
    prev_vah: Optional[float],
    prev_val: Optional[float],
    session_date: Optional[str] = None,
) -> DayType:
    """Classify Neutral day as Extreme (NeuE) or Center (NeuC) per D-091.Q1.

    Args:
        session_open_price: First cash-hours bar open price (09:30 ET)
        prev_vah: Yesterday's Value Area High (from S5 TPO via prev_day.load_tpo_previous_day_summary)
        prev_val: Yesterday's Value Area Low
        session_date: Today's date (ISO) · used for rate-limiting fallback log

    Returns:
        DayType.Neutral_Extreme if session_open is at or outside yesterday's VAH/VAL
            (within EDGE_TOLERANCE_PT of edge or beyond)
        DayType.Neutral_Center if session_open is strictly inside the VA
        DayType.Neutral_Center if any input is None (FALLBACK · safer · 30min window)

    Logging:
        Fallback path logs at INFO level once per session_date (rate-limited).
        Non-fallback path does NOT log (high-volume code path).
    """
    global _fallback_logged_for_date

    if session_open_price is None or prev_vah is None or prev_val is None:
        # Fallback: VA bounds or session open unavailable → NeuC (safer)
        if session_date != _fallback_logged_for_date:
            missing = []
            if session_open_price is None:
                missing.append("session_open")
            if prev_vah is None:
                missing.append("prev_vah")
            if prev_val is None:
                missing.append("prev_val")
            logger.info(
                "[S1] NeuE/NeuC fallback to NeuC · missing=%s · session_date=%s",
                ",".join(missing), session_date,
            )
            _fallback_logged_for_date = session_date
        return DayType.Neutral_Center

    # Normal path: compare session_open to VA bounds
    at_or_above_vah = session_open_price >= (prev_vah - EDGE_TOLERANCE_PT)
    at_or_below_val = session_open_price <= (prev_val + EDGE_TOLERANCE_PT)

    if at_or_above_vah or at_or_below_val:
        return DayType.Neutral_Extreme
    return DayType.Neutral_Center
```

**Edge cases CC must handle:**
- All three inputs None → NeuC + log (fallback)
- Any one of three None → NeuC + log (fallback · missing field listed)
- `prev_vah == prev_val` (degenerate VA · 1-tick wide) → fallback to NeuC + log (treat as missing VA — VA is too narrow to classify reliably). NEW edge case · not in §4 below · CC must add `test_degenerate_va` covering `prev_vah - prev_val < 1*tick`. If `prev_vah == prev_val` exactly → NeuC.
- `session_open_price == prev_vah` exactly → NeuE (at edge counts as Extreme)
- `session_open_price == prev_val` exactly → NeuE (at edge counts as Extreme)
- `session_open_price` strictly between val and vah → NeuC

---

## 4 · Golden tests · minimum 14 (CC must implement)

### `test_neutral_classifier.py`

| # | Test | Input | Expected |
|---|------|-------|----------|
| 1 | `test_open_at_vah_exact` | open=4500.0 · vah=4500.0 · val=4480.0 | `Neutral_Extreme` |
| 2 | `test_open_at_val_exact` | open=4480.0 · vah=4500.0 · val=4480.0 | `Neutral_Extreme` |
| 3 | `test_open_above_vah` | open=4505.0 · vah=4500.0 · val=4480.0 | `Neutral_Extreme` |
| 4 | `test_open_below_val` | open=4475.0 · vah=4500.0 · val=4480.0 | `Neutral_Extreme` |
| 5 | `test_open_within_tolerance_below_vah` | open=4499.75 (1 tick below vah) · vah=4500.0 · val=4480.0 | `Neutral_Extreme` (1T tolerance) |
| 6 | `test_open_within_tolerance_above_val` | open=4480.25 (1 tick above val) · vah=4500.0 · val=4480.0 | `Neutral_Extreme` (1T tolerance) |
| 7 | `test_open_strictly_inside_va` | open=4490.0 · vah=4500.0 · val=4480.0 | `Neutral_Center` |
| 8 | `test_open_near_poc_assume_inside` | open=4490.0 · vah=4500.0 · val=4480.0 | `Neutral_Center` (no POC dependency) |
| 9 | `test_fallback_session_open_missing` | open=None · vah=4500.0 · val=4480.0 | `Neutral_Center` · log at INFO once |
| 10 | `test_fallback_vah_missing` | open=4490.0 · vah=None · val=4480.0 | `Neutral_Center` · log at INFO once |
| 11 | `test_fallback_val_missing` | open=4490.0 · vah=4500.0 · val=None | `Neutral_Center` · log at INFO once |
| 12 | `test_fallback_all_missing` | open=None · vah=None · val=None | `Neutral_Center` · log at INFO once |
| 13 | `test_fallback_rate_limited_per_session` | call twice with same `session_date='2026-05-23'` + vah=None | exactly 1 log record · NeuC twice |
| 14 | `test_fallback_logged_again_new_session` | call once with `session_date='2026-05-23'` then once with `session_date='2026-05-24'` | 2 log records |
| 15 (NEW) | `test_degenerate_va` | open=4490.0 · vah=4490.0 · val=4490.0 (zero-width VA) | `Neutral_Center` · log at INFO once (treated as missing VA) |

### `test_targets_table_v6.py`

| # | Test | Day Type | Expected |
|---|------|----------|----------|
| 1 | `test_targets_trend_normal` | TN | `time_stop_minutes=None` · `t1_r=1.0` · `t2_r=2.0` · `t3_r=4.0` · `trail_after_t2=True` · `no_trade=False` |
| 2 | `test_targets_trend_dd` | TDD | `time_stop_minutes=90` · `t1_r=1.0` · `t3_r=4.0` (cap) · `no_trade=False` |
| 3 | `test_targets_variation` | NV | `time_stop_minutes=60` · `t1_r=1.0` · `t2_r=2.5` · `no_trade=False` |
| 4 | `test_targets_normal` | Norm | `time_stop_minutes=30` · `t1_r=1.0` · `t2="POC"` · `t3=None` · `no_trade=False` |
| 5 | `test_targets_neutral_extreme` | NeuE | `time_stop_minutes=45` · `t1_r=1.0` · `t2="extreme"` · `no_trade=False` |
| 6 | `test_targets_neutral_center` | NeuC | `time_stop_minutes=30` · `t1_r=1.0` · `t2="extreme"` · `no_trade=False` |
| 7 | `test_targets_nontrend_no_trade` | NT | `no_trade=True` · `time_stop_minutes` field SHOULD be present but unused (e.g. set to None or N/A) · contracts=0 |
| 8 | `test_legacy_neutral_alias` | "Neutral" (legacy string) | resolves to NeuC config (safer fallback) · log warning ONCE per process |
| 9 | `test_unknown_daytype_returns_none` | "Banana" | `get_targets("Banana")` returns `None` (NOT silent default) |

### Updated `test_E2_day_types` in `tests/v9/compliance/test_day_type_compliance.py`

Replace:
```python
def test_E2_day_types(self):
    """6 day types + UNKNOWN must exist."""
    names = [dt.value for dt in DayType]
    for expected in ["Trend_Normal", "Trend_DD", "Variation", "Normal", "Neutral", "Nontrend"]:
        assert expected in names
```

With:
```python
def test_E2_day_types(self):
    """7 day types + UNKNOWN must exist per EXIT_V6 (NeuE+NeuC split)."""
    names = [dt.value for dt in DayType]
    for expected in [
        "Trend_Normal", "Trend_DD", "Variation",
        "Normal", "Neutral_Extreme", "Neutral_Center", "Nontrend",
    ]:
        assert expected in names, f"Missing day type: {expected}"
    # Legacy "Neutral" must remain present as deprecated alias for backward compat with old DB rows
    assert "Neutral" in names, "Legacy 'Neutral' must remain as deprecated alias"
```

---

## 5 · `schemas.py` precise change

### Current (line 19-26)

```python
class DayType(str, Enum):
    Trend_Normal = "Trend_Normal"
    Trend_DD = "Trend_DD"
    Variation = "Variation"
    Normal = "Normal"
    Neutral = "Neutral"
    Nontrend = "Nontrend"
    UNKNOWN = "UNKNOWN"
```

### New (after Stream 1)

```python
class DayType(str, Enum):
    Trend_Normal = "Trend_Normal"
    Trend_DD = "Trend_DD"
    Variation = "Variation"
    Normal = "Normal"
    Neutral_Extreme = "Neutral_Extreme"   # NEW · 45min window · open at VA edge (D-091.Q1)
    Neutral_Center = "Neutral_Center"     # NEW · 30min window · open inside VA (D-091.Q1)
    Neutral = "Neutral"                   # DEPRECATED · legacy DB rows · maps to NeuC via targets_table aliasing
    Nontrend = "Nontrend"                 # NO TRADE per EXIT_V6 + D-091 Coverage Matrix
    UNKNOWN = "UNKNOWN"
```

**Rationale for keeping `Neutral` as DEPRECATED:** the V9 DB has existing `v9_day_type_history` rows with `day_type="Neutral"` from prior sessions. Removing the enum value entirely would crash existing data loads. Keep + deprecate + map via aliases. New writes always use NeuE or NeuC.

---

## 6 · `targets_table.py` precise change

### Current `_TARGETS["Neutral"]` (lines 81-93) → REPLACE with TWO rows:

```python
"Neutral_Extreme": {
    "t1": "1R",
    "t1_r": 1.0,
    "t2": "extreme",
    "t2_r": None,
    "t3": None,
    "t3_r": None,
    "time_stop_minutes": 45,  # EXIT_V6 + Master Summary Sheet 3
    "trail_after_t2": False,
    "sizing": "HALF",
    "contracts": 1,
    "no_trade": False,
    "reasoning_notes": "Neutral Extreme (D-091.Q1): T2 at opposite extreme · no T3 · 45min window · open at VA edge",
},
"Neutral_Center": {
    "t1": "1R",
    "t1_r": 1.0,
    "t2": "extreme",
    "t2_r": None,
    "t3": None,
    "t3_r": None,
    "time_stop_minutes": 30,  # EXIT_V6 + Master Summary Sheet 3 (faster fade when opens inside VA)
    "trail_after_t2": False,
    "sizing": "HALF",
    "contracts": 1,
    "no_trade": False,
    "reasoning_notes": "Neutral Center (D-091.Q1): T2 at opposite extreme · no T3 · 30min window · open inside VA",
},
```

### Current `_TARGETS["Nontrend"]` (lines 94-106) → REPLACE with NO_TRADE marker:

```python
"Nontrend": {
    "t1": None,
    "t1_r": None,
    "t2": None,
    "t2_r": None,
    "t3": None,
    "t3_r": None,
    "time_stop_minutes": None,
    "trail_after_t2": False,
    "sizing": None,
    "contracts": 0,
    "no_trade": True,  # NEW · EXIT_V6 + D-091 Coverage Matrix: NO TRADE at all
    "reasoning_notes": "Nontrend: NO TRADE per EXIT_V6 + D-091 Coverage Matrix (NT row = n/a everywhere)",
},
```

### `DAY_TYPES` set (lines 22-25) → update:

```python
DAY_TYPES = {
    "Trend_Normal", "Trend_DD", "Variation", "Normal",
    "Neutral_Extreme", "Neutral_Center",  # NEW
    "Nontrend",
}
```

### `_ALIASES` (lines 110-118) → update:

```python
_ALIASES = {
    "TREND_NORMAL": "Trend_Normal",
    "TREND_DD": "Trend_DD",
    "VARIATION": "Variation",
    "NORMAL": "Normal",
    "NORMAL_DAY": "Normal",
    "NEUTRAL": "Neutral_Center",            # DEPRECATED alias · maps to NeuC (safer) · log once
    "NEUTRAL_CENTER": "Neutral_Center",     # NEW
    "NEUTRAL_EXTREME": "Neutral_Extreme",   # NEW
    "NEUE": "Neutral_Extreme",              # short form
    "NEUC": "Neutral_Center",               # short form
    "NONTREND": "Nontrend",
}
```

### Add deprecation logger to `get_targets` (after line 127):

```python
def get_targets(day_type: str) -> Optional[Dict]:
    """Return target configuration for a given day type. ... (existing docstring)

    DEPRECATED INPUT: passing literal "Neutral" maps to "Neutral_Center" (safer fallback)
    and logs a warning ONCE per process. New code MUST use "Neutral_Extreme" or "Neutral_Center".
    """
    canonical_key = day_type.upper().replace(" ", "_")
    if canonical_key == "NEUTRAL":
        _log_deprecated_neutral_once()  # see below
    canonical = _ALIASES.get(canonical_key, day_type)
    return _TARGETS.get(canonical)


_neutral_deprecation_logged = False

def _log_deprecated_neutral_once() -> None:
    global _neutral_deprecation_logged
    if not _neutral_deprecation_logged:
        import logging
        logging.getLogger(__name__).warning(
            "[targets_table] DEPRECATED day_type='Neutral' used · mapped to Neutral_Center · "
            "update caller to use 'Neutral_Extreme' or 'Neutral_Center' per D-091.Q1"
        )
        _neutral_deprecation_logged = True
```

### Update docstring table (line 9-17) to show 7 day types incl. NeuE/NeuC and NT NO TRADE.

---

## 7 · `state_machine.py` precise changes (6 hits · Hit 3 deferred to Stream 1.5)

### Scope refinement (Michael · 23/5 20:34 IL · Option B)

Line 535 (`_rescore_from_behavior`) is **DEFERRED to Stream 1.5**. State machine continues to return `DayType.Neutral` from this method. The deprecated `Neutral` alias maps to `NeuC` config (30min window) via `targets_table.get_targets()` aliasing → **safe default behavior**. The corrected NeuE/NeuC classification is provided through `api.py` (§8) which has direct access to `prev_day` data. No regression.

**Stream 1.5 follow-on task** (drafted after Stream 1 G3 PASS): wire `prev_vah` / `prev_val` / `session_open_price` / `session_date` into `DayTypeStateMachine.__init__` via `_stage_a1` (where `load_tpo_previous_day_summary` is presumably already called). Then re-enable Hit 3 to use `classify_neutral_subtype()`.

### Hit 1 · line 83 (`PLAYBOOK_TEMPLATES`)

Replace `DayType.Neutral` block with TWO blocks:

```python
DayType.Neutral_Extreme: {
    "strategy": "FADE_EXTREMES",
    "sizing": "HALF",
    "time_stop_min": 45,
    "key_rules": [
        "Open at VA edge — wider expected range",
        "Fade extreme ticks back toward POC",
        "45min window before Type C exit (DD path)",
        "Half size · 1 contract",
    ],
},
DayType.Neutral_Center: {
    "strategy": "FADE_EXTREMES",
    "sizing": "HALF",
    "time_stop_min": 30,
    "key_rules": [
        "Open inside VA — narrower expected range",
        "Fade extremes · expect rotation around POC",
        "30min window before Type C exit (DD path · faster fade)",
        "Half size · 1 contract",
    ],
},
```

### Hit 2 · line 139 (`DAY_TYPE_LOOKUP`)

Replace `DayType.Neutral` row with TWO rows:

```python
DayType.Neutral_Extreme: {"directional": "LOW",    "trading": "HIGH"},
DayType.Neutral_Center:  {"directional": "LOW",    "trading": "HIGH"},
```

### Hit 3 · line 535 (`_rescore_from_behavior`) · **SKIP · DEFERRED to Stream 1.5**

**Do NOT modify line 535 in Stream 1.** Per Michael's Option B decision (23/5 20:34 IL):

> The state machine continues to return `DayType.Neutral` from `_rescore_from_behavior`. The deprecated `Neutral` enum value is preserved as alias-mapped to `NeuC` config (30min window) via `targets_table.get_targets()` aliasing rules (§6 of this handoff). This gives a safe, conservative default. The corrected NeuE/NeuC classification is provided through `api.py` line 190 (§8) which has direct access to `prev_day` data via `load_tpo_previous_day_summary()`.

**Expected outcome:** line 535 stays byte-identical to HEAD:
```python
if self.behavior == Behavior.COMPRESSED:
    if self.range_category == RangeCategory.COMPRESSED:
        return DayType.Nontrend
    return DayType.Neutral
```

**Why this works without regression:**
- Downstream consumers of `state_machine.day_type == DayType.Neutral` continue to work (enum member exists)
- `targets_table.get_targets("Neutral")` resolves to `Neutral_Center` config (30min · HALF sizing · 1 contract) via `_ALIASES["NEUTRAL"] = "Neutral_Center"` (§6)
- One deprecation log fires per process (when first legacy `"Neutral"` lookup happens)
- S2 firing path (via `api.py`) gets the **correct** NeuE vs NeuC classification because Q1's data flow happens there

**Stream 1.5 follow-on (drafted AFTER Stream 1 G3 PASS):**
- Wire `prev_vah` / `prev_val` / `session_open_price` / `session_date` into `DayTypeStateMachine.__init__` via `_stage_a1` (where `load_tpo_previous_day_summary` is presumably already called for `pd_high`/`pd_low`/`pd_close`)
- Once those 4 fields exist on the state machine instance, replace line 535's `return DayType.Neutral` with the `classify_neutral_subtype(...)` call documented in §7 of the **previous** version of this handoff (preserved in git history if needed)

**For Stream 1:** line 535 is in the FORBIDDEN edit list. Touching it = G3 fail.

### Hit 4 · line 550 (`_behavior_agrees_with_type`)

Current:
```python
if dt in (DayType.Normal, DayType.Neutral):
    return self.behavior in (Behavior.DEVELOPING, Behavior.COMPRESSED)
```

New:
```python
if dt in (DayType.Normal, DayType.Neutral_Extreme, DayType.Neutral_Center):
    return self.behavior in (Behavior.DEVELOPING, Behavior.COMPRESSED)
```

### Hit 5 · line 564 (`_range_aligns_with_type`)

Current:
```python
if dt in (DayType.Neutral, DayType.Nontrend):
    return self.range_category in (RangeCategory.COMPRESSED, RangeCategory.NORMAL)
```

New:
```python
if dt in (DayType.Neutral_Extreme, DayType.Neutral_Center, DayType.Nontrend):
    return self.range_category in (RangeCategory.COMPRESSED, RangeCategory.NORMAL)
```

### Hit 6 · line 653 (`_check_reeval` range expectation check)

Current:
```python
if self.day_type in (DayType.Nontrend, DayType.Neutral) and ratio > 1.5:
    expected_exceeded = True
```

New:
```python
if self.day_type in (DayType.Nontrend, DayType.Neutral_Extreme, DayType.Neutral_Center) and ratio > 1.5:
    expected_exceeded = True
```

### Hit 7 · line 86 (`time_stop_min` comment)

Already covered by Hit 1 (the comment becomes 45 for NeuE row · 30 for NeuC row).

---

## 8 · `api.py` precise change (line 190)

### Current

```python
# Classification (🟡 V1 rules — CAL-006/007)
if both_sides:
    day_type = "Neutral"
    conf = 60
elif not ib_breached_up and not ib_breached_down:
    day_type = "Normal"
    conf = 70
```

### New

```python
# Classification (🟡 V1 rules — CAL-006/007 + D-091.Q1 NeuE/NeuC split)
if both_sides:
    from backend.v9.systems.day_type.neutral_classifier import classify_neutral_subtype
    from backend.v9.systems.day_type.prev_day import load_tpo_previous_day_summary
    prev_day = load_tpo_previous_day_summary()
    subtype = classify_neutral_subtype(
        session_open_price=session_open_price,  # caller must provide · see signature update below
        prev_vah=prev_day.get("vah"),
        prev_val=prev_day.get("val"),
        session_date=session_date,  # caller must provide
    )
    day_type = subtype.value
    conf = 60
elif not ib_breached_up and not ib_breached_down:
    day_type = "Normal"
    conf = 70
```

**Caller signature update:** the function containing line 190 must add `session_open_price: Optional[float]` and `session_date: Optional[str]` params. Existing callers (route handlers · tests) pass `None` for safety → falls back to NeuC via the classifier's internal fallback.

If session_open_price is not trivially available in this function's existing inputs → STOP and report (may need a Stream 2 follow-up · DO NOT invent a fake session_open derivation).

---

## 9 · `compliance_manifest.yaml` precise change

### Lines 100-105 (E2)

Current:
```yaml
  - id: E2
    name: "Final Day Type Output (7 types)"
    branches: [NORMAL, NORMAL_VARIATION, TREND_NORMAL, TREND_DD, NONTREND, NEUTRAL_CENTER, NEUTRAL_EXTREME]
    status: PARTIAL
    notes: "6 types implemented (Neutral_Center and Neutral_Extreme merged into Neutral)"
```

New:
```yaml
  - id: E2
    name: "Final Day Type Output (7 types)"
    branches: [NORMAL, NORMAL_VARIATION, TREND_NORMAL, TREND_DD, NONTREND, NEUTRAL_CENTER, NEUTRAL_EXTREME]
    status: IMPLEMENTED
    notes: "7 types implemented per D-091.Q1 (NeuE/NeuC split via neutral_classifier · NT marked no_trade=True · legacy 'Neutral' retained as deprecated alias)"
```

### Line 118 (output_fields enum)

Current:
```yaml
    enum: [Trend_Normal, Trend_DD, Variation, Normal, Neutral, Nontrend, UNKNOWN]
```

New:
```yaml
    enum: [Trend_Normal, Trend_DD, Variation, Normal, Neutral_Extreme, Neutral_Center, Neutral, Nontrend, UNKNOWN]
```

(Keep `Neutral` for backward compat with deprecated alias.)

---

## 10 · `entry_executor.py` precise change (line 61)

Current `DAY_TYPE_TARGETS["Neutral"]` row:
```python
"Neutral":      TargetConfig(t1_r=0.75, time_stop_min=30, sizing="HALF", contracts=1),
```

New (replace with TWO rows + keep deprecated alias):
```python
"Neutral_Extreme": TargetConfig(t1_r=0.75, time_stop_min=45, sizing="HALF", contracts=1),
"Neutral_Center":  TargetConfig(t1_r=0.75, time_stop_min=30, sizing="HALF", contracts=1),
"Neutral":         TargetConfig(t1_r=0.75, time_stop_min=30, sizing="HALF", contracts=1),  # DEPRECATED · maps to NeuC
"Nontrend":        TargetConfig(t1_r=0.5,  time_stop_min=20, sizing="MIN",  contracts=1),  # unchanged · Pkg 6 will gate
```

**NOTE:** `entry_executor.py` is Layer 3 legacy code — Stream 2 will likely consolidate this into the new `day_type_targets.py` module. For Stream 1, just maintain consistency (the file is currently used by Layer 3 path · breaking it would regress).

---

## 11 · Files Desktop must inline into the mega prompt

Desktop, attach these full files inline so CC has surgical-edit anchors:

1. `backend/v9/systems/day_type/schemas.py` lines 1-50 (the `DayType` enum)
2. `backend/v9/systems/day_type/state_machine.py` lines 70-150 (`PLAYBOOK_TEMPLATES` + `DAY_TYPE_LOOKUP`)
3. `backend/v9/systems/day_type/state_machine.py` lines 520-570 (`_rescore_from_behavior` + `_behavior_agrees_with_type` + `_range_aligns_with_type`)
4. `backend/v9/systems/day_type/state_machine.py` lines 638-670 (`_check_reeval`)
5. `backend/v9/systems/day_type/targets_table.py` (entire file · 129 LOC)
6. `backend/v9/systems/day_type/api.py` lines 170-220 (the both_sides classification block)
7. `backend/v9/systems/day_type/prev_day.py` lines 90-135 (`load_tpo_previous_day_summary` signature + return shape)
8. `backend/v9/systems/day_type/compliance_manifest.yaml` lines 100-130
9. `backend/v9/layer3/entry_executor.py` lines 50-70 (`DAY_TYPE_TARGETS` block)
10. `tests/v9/compliance/test_day_type_compliance.py` lines 255-275 (`test_E2_day_types`)
11. `docs/spec_authority/S2_EXIT_DEFINITION_V6.md` lines 105-125 (Time Stop windows table)
12. `docs/decisions/D-091_S2_LIVE_SCOPE.md` §Pkg 3a sub-decisions (verbatim from D-091)

---

## 12 · Acceptance criteria (G4 UAT)

CC must self-verify:

- ✅ `pytest tests/v9/systems/test_day_type/test_neutral_classifier.py -q` exit 0 · all 15 tests pass
- ✅ `pytest tests/v9/systems/test_day_type/test_targets_table_v6.py -q` exit 0 · all 9 tests pass
- ✅ `pytest tests/v9/compliance/test_day_type_compliance.py -q` exit 0 · `test_E2_day_types` updated and passes
- ✅ `pytest tests/v9/systems/test_day_type/ -q` exit 0 · no regression in existing day_type tests
- ✅ `pytest tests/v9/ -q` exit 0 · no regression (pre-existing failures verified against HEAD~1 · same set)
- ✅ `BRIDGE_TOKEN=dummy python3 -c "from backend.v9.systems.day_type.schemas import DayType; assert DayType.Neutral_Extreme.value == 'Neutral_Extreme'; assert DayType.Neutral_Center.value == 'Neutral_Center'; assert DayType.Neutral.value == 'Neutral'"` succeeds
- ✅ `BRIDGE_TOKEN=dummy python3 -c "from backend.v9.systems.day_type.neutral_classifier import classify_neutral_subtype, DayType; r = classify_neutral_subtype(session_open_price=4500.0, prev_vah=4500.0, prev_val=4480.0); assert r == DayType.Neutral_Extreme; print('OK')"` succeeds
- ✅ ReadLints clean on all modified files
- ✅ No new dependencies (pure Python · standard library only)
- ✅ `grep -rn "DayType.Neutral\b" backend/` returns hits ONLY in: (a) deprecated-alias path in `targets_table.py` aliases block · (b) `state_machine.py` **line 535** (intentionally preserved per Option B · deferred to Stream 1.5) · (c) test files that document legacy behavior. All hits in `state_machine.py` lines 83/139/550/564/653 must be replaced with the appropriate NeuE/NeuC references (5 replacements + line 86 comment update + line 83 enum-key replacement → 6 surgical edits).
- ✅ `state_machine.py` line 535 byte-identical to HEAD · verify with `git diff HEAD -- backend/v9/systems/day_type/state_machine.py | rg -c "^[+-].*_rescore_from_behavior|^[+-].*return DayType.Neutral$"` returns 0
- ✅ Boot smoke: backend imports + 5 systems register correctly (no broken enum reference)
- ✅ Backward-compat smoke: existing DB row with `day_type="Neutral"` reads without error via `DayType("Neutral")` + `get_targets("Neutral")` maps to NeuC

---

## 13 · Constraints (must not violate)

- **No silent excepts** — every `except` must include `logger.warning(...)` rate-limited
- **No `return None` without prior log** — all error paths must log first
- **No new dependencies** — pure Python
- **Maintain Path A canonical** — no imports from deleted `chart_5min/`
- **Fallback rule is AUTHORITY** — when VA missing, NeuC. Never NeuE. Never error. Never default Neutral.
- **Legacy "Neutral" string MUST continue to work** — DB rows from prior sessions must read without crash · maps to NeuC + 1× deprecation log
- 🛑 **Do NOT delete `DayType.Neutral` enum member** — leave it as deprecated alias for backward compat
- 🛑 **Do NOT modify line 535 of `state_machine.py` (`_rescore_from_behavior`)** — DEFERRED to Stream 1.5 per Michael's Option B (23/5 20:34 IL). Line 535 must remain `return DayType.Neutral` byte-identical to HEAD.
- 🛑 **Do NOT touch `backend/v9/systems/five_min/` in Stream 1** — that's Stream 2 scope
- 🛑 **Do NOT modify `manager.py` or anything in `services/trade_manager/`** — that's Pkg 6 scope
- 🛑 **Do NOT change `Nontrend` to fire trades** — NT remains NO TRADE (this Stream just marks the flag for Stream 2 to gate on)
- 🛑 **TESTS ARE AUTHORITY** — if §4 tests cannot be satisfied by the proposed implementation, STOP and report

---

## 14 · Stop signal triggers

CC must STOP and report (NOT guess) if:

- ~~`state_machine.py` does NOT currently wire `prev_day` context~~ — **RESOLVED by Option B (23/5 20:34)**. Stream 1 does NOT touch line 535. State machine continues returning `DayType.Neutral`, which aliases to NeuC config (30min · safe default) via `targets_table`. No stop needed. (Stream 1.5 will handle prev_day wiring after Stream 1 G3 PASS.)
- `api.py` line 190's function signature does NOT have access to `session_open_price` and `session_date` (verify by reading the function 30 lines up from line 190 · check params). If unavailable → STOP and report which fields are missing. **Fallback within scope:** if signature already accepts `**kwargs` or the function has a single caller you can identify · pass `None` for the missing fields and let `classify_neutral_subtype` fall back to NeuC. Otherwise STOP.
- The test fixture `synthetic_bars.py` line 119 has hardcoded `day_type="Neutral"` assertions in body that would break — STOP and ask whether to update assertions or split fixture.
- `DayType("Neutral")` lookup is called in any cross-system snapshot consumer in a way that would crash if we changed enum members — verify by `grep -rn "DayType(\"Neutral\")\|DayType\\['Neutral'\\]" backend/`.
- 🛑 **Any file outside the §2 "MODIFY" list is touched by an auto-format / multi-line edit** — STOP immediately, `git checkout HEAD -- <file>`, re-apply edits surgically.
- 🛑 **Line 535 of `state_machine.py` is modified accidentally** (auto-format · multi-line edit · global search-replace of `DayType.Neutral`) — STOP immediately, `git checkout HEAD -- backend/v9/systems/day_type/state_machine.py`, re-apply only the 6 surgical Hits (lines 83/86/139/550/564/653) WITHOUT touching line 535.

**Output format on STOP:** `"STOP — <reason> · need Michael decision on <specific question>"`

---

## 15 · Deliverable format CC must produce

1. **Files added** (A): `backend/v9/systems/day_type/neutral_classifier.py` · `tests/v9/systems/test_day_type/test_neutral_classifier.py` · `tests/v9/systems/test_day_type/test_targets_table_v6.py`
2. **Files modified** (M · with diff line ranges): list per §2 above
3. **Commit message:** `feat(s1): EXIT_V6 fix · split Neutral into NeuE+NeuC per D-091.Q1`
4. **pytest output tail** (last 30 lines · including new test counts + per-class pass/fail breakdown)
5. **Boot smoke** output: backend init succeeds · 5 systems register
6. **Backward-compat smoke:** `DayType("Neutral")` resolution + `get_targets("Neutral")` mapping result (paste verbatim)
7. **Self-report:**
   - Any TODOs left? (must be empty)
   - Any spec ambiguity encountered? (list)
   - Any forbidden constraint accidentally violated? (own up)
8. **ReadLints output** (paste verbatim)
9. **Sample classification trace:** 3 invocations with (open=4500, vah=4500, val=4480), (open=4490, vah=4500, val=4480), (open=4490, vah=None, val=4480) → expected outputs NeuE / NeuC / NeuC + 1 fallback log (paste log output)

---

## 16 · Desktop's deliverable

Desktop, please produce a single MEGA prompt for CC following `docs/templates/MEGA_PROMPT_TEMPLATE.md` (7 fields + Stop signal).

Use this handoff as spec authority. Inline the file contents listed in §11. The mega prompt is what Michael will paste into Claude Code.

**Length expectation:** ~600-900 lines (includes inlined files). Quality > brevity.

**After Stream 1 G3 PASS** — Cursor will draft TWO follow-on handoffs in parallel:

1. **Stream 1.5 · prev_day hydration wiring** (`DESKTOP_PKG3A_STREAM1_5_PREVDAY_WIRING_HANDOFF.md`): wire `prev_vah` / `prev_val` / `session_open_price` / `session_date` into `DayTypeStateMachine.__init__` via `_stage_a1`. Then replace line 535's `return DayType.Neutral` with the `classify_neutral_subtype(...)` call. Small surgical task (~1-2h CC).
2. **Stream 2 · Pkg 3a proper** (`DESKTOP_PKG3A_STREAM2_DAY_TYPE_TARGETS_HANDOFF.md`): new `backend/v9/systems/five_min/day_type_targets.py` · `T1Setup.t3_price` schema add · fix `self.opening_type → self.current_day_type` · NT NO_TRADE gate per Q2 · TradeManager emit-only per Q4.

Stream 1.5 and Stream 2 are **independent** (different files · no conflict) — can run in parallel after Stream 1 ships.

---

*End of handoff · Cursor agent · 2026-05-23 20:25 IL*
