# DESKTOP_PKG8_QUALITY_V2_HANDOFF · Cursor → Claude Desktop → CC

**Date:** 2026-05-25 12:25 IL · **Owner draft:** Cursor · **Reviewer:** Michael Barg (already approved spec)
**Authority for this handoff:** `docs/spec_authority/S2_AUTH_TABLE_V1.md` (🔒 LOCKED 25/5 12:22)
**Package:** Pkg 8 · Quality V2 · NEXT in Phase A queue (per D-095 25/5 11:18)
**Branch:** `stabilize/mems26-local-truth-2026-05-16` · HEAD `1e01c4a`
**Phase A status:** 11/13 done · Pkg 8 = 12th · Pkg 6 = 13th (LAST)
**Estimated CC time:** ~3-4h (lookup table + V2 rewrite + tests)

---

## 0 · Cursor-Michael LOCKS (verify-first audit completed 25/5)

These are pre-flight clarifications established during the spec lock chat. CC MUST treat them as authoritative on top of the spec doc.

| # | Lock | Where it matters |
|---|---|---|
| 1 | Auth Table V1 supersedes Constitution V3 §"Quality Tier" flat mapping | `quality_tier.py` rewrite |
| 2 | `verdict='SKIP'` returns `contracts=0` (never 1) — kills `setup_emitter.py:60 max(1, sizing)` advisory floor | `setup_emitter.py` lines 56-60 modify |
| 3 | NT (`Nontrend`) row in Auth Table is global skip (all cells `0/0/0`) — redundant defense in depth with D-091.Q2 NT early-refuse at `setup_emitter.py:43-52` | both layers stay |
| 4 | Unknown `day_type` → fallback to `Neutral_Center` row + `logger.warning` (no silent failure per pre-LIVE protocol) | `quality_tier.py` V2 |
| 5 | Unknown `pattern_name` → `ValueError` (matches `contract_split.get_contract_split()` pattern at `contract_split.py:46-48`) | `quality_tier.py` V2 |
| 6 | V1 signature `get_quality_tier(price, tpo_data=...)` kept as thin DeprecationWarning wrapper for `tests/v9/systems/test_five_min/test_quality_tier.py` (3 tests) | `quality_tier.py` V2 |
| 7 | T1Setup `sizing_contracts: int = Field(ge=0, le=3, default=2)` already supports 0-3 · NO schema migration | `output_schema.py` UNCHANGED |
| 8 | `setup_emitter.py` is the ONLY production caller of `get_quality_tier` (grep verified by Cursor) | minimal blast radius |

---

## 1 · Spec authority (verbatim)

### 1.1 · S2 Auth Table V1 §4 (post-audit · final lookup)

```text
# Format: (HIGH / MEDIUM / LOW) contracts · prefixed by verdict (✅ FULL · ⚠️ REDUCED · ❌ SKIP)
# 10 patterns × 7 day_types = 70 cells

REACTIVE_LONG           : TN ⚠️ 2/1/0 · TDD ⚠️ 2/1/0 · NeuE ✅ 3/2/2 · NV ✅ 3/2/2 · NeuC ✅ 3/2/2 · Norm ✅ 3/2/2 · NT ❌ 0/0/0
REACTIVE_SHORT          : TN ⚠️ 2/2/0 · TDD ⚠️ 2/2/0 · NeuE ✅ 3/2/2 · NV ✅ 3/2/2 · NeuC ✅ 3/2/2 · Norm ✅ 3/2/2 · NT ❌ 0/0/0
INITIATIVE_LONG         : TN ✅ 3/2/1 · TDD ✅ 3/2/1 · NeuE ❌ 0/0/0 · NV ✅ 3/2/1 · NeuC ❌ 0/0/0 · Norm ❌ 0/0/0 · NT ❌ 0/0/0
INITIATIVE_SHORT        : TN ✅ 3/2/1 · TDD ✅ 3/2/1 · NeuE ❌ 0/0/0 · NV ✅ 3/2/1 · NeuC ❌ 0/0/0 · Norm ❌ 0/0/0 · NT ❌ 0/0/0
INVERSE_HNS_LONG        : TN ❌ 0/0/0 · TDD ❌ 0/0/0 · NeuE ✅ 3/2/1 · NV ⚠️ 2/1/0 · NeuC ✅ 3/2/1 · Norm ✅ 3/2/1 · NT ❌ 0/0/0
HNS_TOP_SHORT           : TN ❌ 0/0/0 · TDD ❌ 0/0/0 · NeuE ✅ 3/2/1 · NV ⚠️ 2/1/0 · NeuC ✅ 3/2/1 · Norm ✅ 3/2/1 · NT ❌ 0/0/0
DOUBLE_BOTTOM_EE_LONG   : TN ❌ 0/0/0 · TDD ❌ 0/0/0 · NeuE ✅ 3/2/2 · NV ✅ 3/2/2 · NeuC ✅ 3/2/2 · Norm ✅ 3/2/2 · NT ❌ 0/0/0
DOUBLE_TOP_AA_SHORT     : TN ❌ 0/0/0 · TDD ❌ 0/0/0 · NeuE ✅ 3/2/2 · NV ✅ 3/2/2 · NeuC ✅ 3/2/2 · Norm ✅ 3/2/2 · NT ❌ 0/0/0
BULL_FLAG_LONG          : TN ✅ 3/2/2 · TDD ✅ 3/2/2 · NeuE ⚠️ 2/2/0 · NV ✅ 3/2/2 · NeuC ❌ 0/0/0 · Norm ⚠️ 2/2/0 · NT ❌ 0/0/0
BEAR_FLAG_SHORT         : TN ✅ 3/2/2 · TDD ✅ 3/2/2 · NeuE ⚠️ 2/2/0 · NV ✅ 3/2/1 · NeuC ❌ 0/0/0 · Norm ⚠️ 2/1/0 · NT ❌ 0/0/0
```

### 1.2 · Day-type mapping (verbatim · S2_AUTH_TABLE_V1.md §3)

```python
DAY_TYPE_ALIAS = {
    "TN":   "Trend_Normal",
    "TDD":  "Trend_DD",
    "NeuE": "Neutral_Extreme",
    "NV":   "Variation",
    "NeuC": "Neutral_Center",
    "Norm": "Normal",
    "NT":   "Nontrend",
}
```

### 1.3 · Verdict semantics (verbatim · S2_AUTH_TABLE_V1.md §6.2)

- **✅ FULL** → use HIGH/MEDIUM/LOW per quality-tier classification
- **⚠️ REDUCED** → use HIGH/MEDIUM/LOW per quality-tier classification (already reduced in table — no extra penalty)
- **❌ SKIP** → return `(verdict='SKIP', tier=tier, contracts=0)` for the cell · `setup_emitter` short-circuits to return None

### 1.4 · API signature (verbatim · S2_AUTH_TABLE_V1.md §7)

```python
from typing import Literal, Tuple, Optional

QualityVerdict = Literal['FULL', 'REDUCED', 'SKIP']
QualityTier = Literal['HIGH', 'MEDIUM', 'LOW']


def get_quality_tier_v2(
    pattern_name: str,
    day_type: str,
    price: float,
    *,
    tpo_data: Optional[dict] = None,
) -> Tuple[QualityVerdict, QualityTier, int]:
    """Return (verdict, tier, contracts) for the (pattern × day_type × tier) cell.

    Args:
        pattern_name: PatternName Literal value (e.g., 'BULL_FLAG_LONG')
        day_type: DayType enum value (e.g., 'Trend_Normal')
        price: current price for TPO proximity classification
        tpo_data: optional TPO snapshot (defaults to S5 /api/v9/tpo/current fetch)

    Returns:
        (verdict, tier, contracts):
            verdict ∈ {'FULL', 'REDUCED', 'SKIP'}
            tier    ∈ {'HIGH', 'MEDIUM', 'LOW'}
            contracts ∈ {0, 1, 2, 3}

    Raises:
        ValueError if pattern_name not in PatternName Literal.
    """
```

---

## 2 · Existing code (read-only · do NOT modify outside SCOPE)

### 2.1 · `backend/v9/systems/five_min/quality_tier.py` (65 lines · REPLACE)

```python
"""Quality Tier — consume S5 /tpo/current for location-based sizing.

Per Constitution V3 §Layer 2 Quality Tier:
  HIGH (3 contracts): price at POC/VAH/VAL (strong reference)
  MEDIUM (2 contracts): price within value area but not at key level
  LOW (1 contract): price outside value area, no reference

Location source: S5 TPO endpoint /api/v9/tpo/current.
"""
from __future__ import annotations

from typing import Literal, Optional, Tuple

import requests


TPO_ENDPOINT = "http://localhost:8000/api/v9/tpo/current"
PROXIMITY_PT = 2.0  # within 2 points of key level = "at" level


def get_quality_tier(
    price: float,
    *,
    tpo_data: Optional[dict] = None,
) -> Tuple[Literal['HIGH', 'MEDIUM', 'LOW'], int]:
    """Determine quality tier based on price location vs TPO levels.

    Returns (tier, sizing_contracts).
    """
    if tpo_data is None:
        tpo_data = _fetch_tpo()
    if tpo_data is None:
        return ('MEDIUM', 2)  # fallback when TPO unavailable

    poc = tpo_data.get("poc") or tpo_data.get("poc_tpo")
    vah = tpo_data.get("vah")
    val = tpo_data.get("val")

    if poc is None or vah is None or val is None:
        return ('MEDIUM', 2)

    # HIGH: price at POC, VAH, or VAL (within PROXIMITY_PT)
    key_levels = [poc, vah, val]
    for level in key_levels:
        if level is not None and abs(price - level) <= PROXIMITY_PT:
            return ('HIGH', 3)

    # MEDIUM: price within value area (between VAL and VAH)
    if val <= price <= vah:
        return ('MEDIUM', 2)

    # LOW: advisory quality context only. It reduces size but does not hard-block.
    return ('LOW', 1)


def _fetch_tpo() -> Optional[dict]:
    """Fetch TPO state from S5 endpoint."""
    try:
        r = requests.get(TPO_ENDPOINT, timeout=2)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None
```

### 2.2 · `backend/v9/systems/five_min/setup_emitter.py` lines 16, 54-60 (ADAPT · 5-line change)

```python
# Line 16 (current):
from .quality_tier import get_quality_tier

# Lines 54-60 (current):
    # Quality tier from TPO location
    price_for_tier = current_price or entry_price
    quality_tier, sizing = get_quality_tier(price_for_tier, tpo_data=tpo_data)

    # S5 TPO quality is advisory context. It may reduce size, but only the
    # explicit pre_fire validator below can reject the setup at this layer.
    sizing = max(1, sizing)
```

### 2.3 · `backend/v9/systems/five_min/output_schema.py` lines 47-48 (KEEP · already 0-3 range)

```python
quality_tier: Literal['HIGH', 'MEDIUM', 'LOW'] = 'MEDIUM'
sizing_contracts: int = Field(ge=0, le=3, default=2)
```

### 2.4 · `tests/v9/systems/test_five_min/test_quality_tier.py` (24 lines · EXPAND)

```python
"""Tests for Quality Tier (S5 TPO location-based sizing)."""
from backend.v9.systems.five_min.quality_tier import get_quality_tier


def test_high_at_poc():
    tpo = {"poc": 5250.0, "vah": 5260.0, "val": 5240.0}
    tier, contracts = get_quality_tier(5250.5, tpo_data=tpo)
    assert tier == 'HIGH'
    assert contracts == 3


def test_medium_in_value_area():
    tpo = {"poc": 5250.0, "vah": 5260.0, "val": 5240.0}
    tier, contracts = get_quality_tier(5255.0, tpo_data=tpo)
    assert tier == 'MEDIUM'
    assert contracts == 2


def test_low_outside_value():
    tpo = {"poc": 5250.0, "vah": 5260.0, "val": 5240.0}
    tier, contracts = get_quality_tier(5275.0, tpo_data=tpo)
    assert tier == 'LOW'
    assert contracts == 1
```

### 2.5 · `backend/v9/systems/five_min/tests/test_setup_emitter.py` (56 lines · ADAPT · V1→V2 expectations)

CC must update assertions for V2 Auth Table cell values · keep test scenarios identical. See §5 below for exact mapping.

### 2.6 · Existing PatternName Literal (read-only · do NOT modify)

`backend/v9/systems/five_min/output_schema.py:13-19`:

```python
PatternName = Literal[
    'REACTIVE_LONG', 'REACTIVE_SHORT',
    'INITIATIVE_LONG', 'INITIATIVE_SHORT',
    'INVERSE_HNS_LONG', 'HNS_TOP_SHORT',
    'DOUBLE_BOTTOM_EE_LONG', 'DOUBLE_TOP_AA_SHORT',
    'BULL_FLAG_LONG', 'BEAR_FLAG_SHORT',
]
```

### 2.7 · Existing DayType enum (read-only · do NOT modify)

`backend/v9/systems/day_type/schemas.py:19-28`:

```python
class DayType(str, Enum):
    Trend_Normal = "Trend_Normal"
    Trend_DD = "Trend_DD"
    Variation = "Variation"
    Normal = "Normal"
    Neutral_Extreme = "Neutral_Extreme"   # NEW · 45min · open at VA edge (D-091.Q1)
    Neutral_Center = "Neutral_Center"     # NEW · 30min · open inside VA (D-091.Q1)
    Neutral = "Neutral"                   # DEPRECATED · legacy DB rows · maps to NeuC
    Nontrend = "Nontrend"                 # NO TRADE per EXIT_V6 + D-091
    UNKNOWN = "UNKNOWN"
```

---

## 3 · SCOPE — exactly these files

### WRITE NEW (2 files)

- `backend/v9/systems/five_min/auth_table_v1.py` (~80 LOC · const dict + `get_auth_cell()` lookup)
- `tests/v9/systems/test_five_min/test_auth_table_v1.py` (~180 LOC · 70 coverage cells + edge cases)

### REPLACE (1 file · full rewrite)

- `backend/v9/systems/five_min/quality_tier.py` (~140 LOC after rewrite):
  - Keep V1 `get_quality_tier(price, tpo_data=...)` as DeprecationWarning thin wrapper that forwards to V2 with `pattern_name=None` + `day_type='Neutral_Center'` fallback
  - Add NEW `get_quality_tier_v2(pattern_name, day_type, price, *, tpo_data=...)` per §1.4 spec
  - V2 internal logic:
    1. Classify tier (HIGH/MEDIUM/LOW) from POC/VAH/VAL proximity (existing V1 logic preserved verbatim)
    2. Resolve cell via `auth_table_v1.get_auth_cell(pattern_name, day_type)`
    3. Combine: if cell verdict is SKIP → return SKIP/tier/0 · else return verdict/tier/contracts[tier]

### MODIFY (2 files · narrow line changes)

- `backend/v9/systems/five_min/setup_emitter.py`:
  - Line 16: change import to `from .quality_tier import get_quality_tier_v2`
  - Lines 54-60: rewrite block:
    ```python
    # Quality tier + sizing from Auth Table V1 (pattern × day_type × tier)
    price_for_tier = current_price or entry_price
    # day_type fallback to Neutral_Center per Auth Table §6.4
    _day_type = day_type if day_type else "Neutral_Center"
    verdict, quality_tier, sizing = get_quality_tier_v2(
        pattern_name, _day_type, price_for_tier, tpo_data=tpo_data,
    )

    # SKIP verdict short-circuits — Auth Table V1 §6.2
    if verdict == 'SKIP':
        logger.info(
            "[S2] T1Setup skipped: pattern=%s day_type=%s tier=%s · Auth Table SKIP",
            pattern_name, _day_type, quality_tier,
        )
        return None
    ```
  - Line 85 (`sizing_contracts=sizing`): no change (`sizing` may be 0-3 from Auth Table)
  - Lines 109-112 (`logger.info`): keep verbatim
  - DELETE old `sizing = max(1, sizing)` advisory line (now handled by SKIP semantics)

- `backend/v9/systems/five_min/tests/test_setup_emitter.py`:
  - `test_emit_valid_long`: keep verbatim · V2 cell `(REACTIVE_LONG, Variation, HIGH)` = `3/2/2 → HIGH=3` ✓
  - `test_emit_reduces_low_quality_without_rejecting`: UPDATE `assert setup.sizing_contracts == 1` → `== 2` (V2 cell `(REACTIVE_LONG, Neutral_Center, LOW)` = `3/2/2 → LOW=2` · `day_type` is None → fallback to Neutral_Center)
  - `test_emit_rejects_invalid_rr`: keep verbatim · independent of sizing
  - `test_emit_uses_day_type_time_stop`: setup will now return None because NT row = SKIP. UPDATE assertion: `assert setup is None` (V2 + D-091.Q2 both enforce skip). DELETE `assert setup.time_stop_minutes == 20` line.

### EXPAND (1 file · 3 V1 tests stay · add ~8 V2 tests)

- `tests/v9/systems/test_five_min/test_quality_tier.py`:
  - Keep 3 existing V1 tests verbatim (test the wrapper)
  - Add `test_v2_*` tests covering V2 signature (see §4 golden tests)

### FORBIDDEN — do NOT touch

```text
backend/v9/systems/five_min/contract_split.py        # Pkg 3c · emit-only · separate concern
backend/v9/systems/five_min/adaptive_stop.py         # Pkg 1 · stop sizing
backend/v9/systems/five_min/five_min_system.py       # five_min runtime — no upstream changes
backend/v9/systems/five_min/output_schema.py         # schema already supports 0-3 · zero changes
backend/v9/systems/five_min/patterns/                # Pkg 5a/5b/5c · pattern detectors
backend/v9/systems/day_type/                         # Pkg 3a · day_type system
backend/v9/services/trail_engine.py                  # Pkg 3b-3
backend/v9/services/layer4/                          # Pkg 3b-3
backend/v9/services/trade_manager/                   # Pkg 6 (LAST · LATER)
backend/v9/systems/woodies/                          # Pipeline 2
backend/v9/systems/footprint/                        # Pipeline 4
frontend/                                            # No UI changes
sc_study/ + bridge/                                  # No DLL / bridge changes
backend/v9/db/                                       # No DB schema changes
tests/atomic/test_cross_system_integration.py        # Out of scope · Cursor follow-up if it breaks (see §6)
```

---

## 4 · Golden tests (must pass · minimum N=24)

### 4.1 · `test_auth_table_v1.py` (NEW · 15 tests minimum)

```text
test_table_coverage_70_cells: len({(p,d) for p in PatternName for d in DAY_TYPES if (p,d) in TABLE}) == 70
test_pattern_coverage_perfect: set(TABLE.keys()) == set of (PatternName × DayType) tuples
test_all_verdicts_valid: all cells have verdict ∈ {FULL, REDUCED, SKIP}
test_all_contracts_in_range: all contract values ∈ {0, 1, 2, 3}
test_nt_row_global_skip: for every PatternName p, TABLE[(p, 'Nontrend')] == ('SKIP', {HIGH:0, MEDIUM:0, LOW:0})
test_skip_verdict_zero_contracts: every SKIP cell has 0 contracts at all 3 tiers
test_reactive_long_neuC_high: TABLE[('REACTIVE_LONG', 'Neutral_Center')] verdict == 'FULL' · HIGH == 3 · MEDIUM == 2 · LOW == 2
test_initiative_long_norm_skip: TABLE[('INITIATIVE_LONG', 'Normal')] verdict == 'SKIP' · all tiers 0
test_inverse_hns_tdd_skip: TABLE[('INVERSE_HNS_LONG', 'Trend_DD')] verdict == 'SKIP' · all tiers 0
test_double_bottom_tn_skip: TABLE[('DOUBLE_BOTTOM_EE_LONG', 'Trend_Normal')] verdict == 'SKIP' · all tiers 0
test_bull_flag_neuC_typo_fixed: TABLE[('BULL_FLAG_LONG', 'Neutral_Center')] verdict == 'SKIP' · LOW == 0  # was 2 in source · fixed per Michael 25/5 12:11
test_hns_top_short_matches_inverse_hns_long: TABLE[('HNS_TOP_SHORT', d)] == TABLE[('INVERSE_HNS_LONG', d)] for all d  # Q4 confirm
test_get_auth_cell_unknown_pattern_raises: get_auth_cell('FAKE_PATTERN', 'Trend_Normal') raises ValueError
test_get_auth_cell_unknown_day_type_fallback: get_auth_cell('REACTIVE_LONG', 'UNKNOWN') logs WARN + returns Neutral_Center cell
test_max_contracts_le_3: max(contracts across all cells) == 3  # Q6 cap enforcement
```

### 4.2 · `test_quality_tier.py` V2 (NEW · 9 tests minimum)

```text
test_v2_reactive_long_neuC_at_poc: get_quality_tier_v2('REACTIVE_LONG', 'Neutral_Center', 5250.5, tpo_data={poc:5250, vah:5260, val:5240}) == ('FULL', 'HIGH', 3)
test_v2_reactive_long_neuC_in_va: get_quality_tier_v2('REACTIVE_LONG', 'Neutral_Center', 5255.0, tpo) == ('FULL', 'MEDIUM', 2)
test_v2_reactive_long_neuC_outside: get_quality_tier_v2('REACTIVE_LONG', 'Neutral_Center', 5275.0, tpo) == ('FULL', 'LOW', 2)
test_v2_initiative_long_norm_skip: get_quality_tier_v2('INITIATIVE_LONG', 'Normal', 5250.5, tpo) == ('SKIP', 'HIGH', 0)
test_v2_nt_day_global_skip: get_quality_tier_v2(any_pattern, 'Nontrend', 5250.5, tpo) verdict == 'SKIP' · contracts == 0
test_v2_unknown_pattern_raises: get_quality_tier_v2('FAKE', 'Trend_Normal', 5250.5, tpo) raises ValueError
test_v2_unknown_day_type_fallback: get_quality_tier_v2('REACTIVE_LONG', 'WeirdType', 5250.5, tpo) → falls back to Neutral_Center cell + WARN log
test_v2_tpo_data_none_fetches_or_fails_safe: get_quality_tier_v2('REACTIVE_LONG', 'Neutral_Center', 5250.5, tpo_data=None) returns MEDIUM tier when fetch fails
test_v2_proximity_pt_threshold: at distance > PROXIMITY_PT, classified as MEDIUM not HIGH (boundary case)
```

---

## 5 · `test_setup_emitter.py` changes (line-precise · so CC doesn't drift)

| Current line | Current assertion | V2 expected (CC writes this) | Reason |
|---|---|---|---|
| L17-18 | `tier == 'HIGH'` · `contracts == 3` | unchanged | Cell `(REACTIVE_LONG, Variation, HIGH)` = `3/2/2 → HIGH=3` |
| L30-31 | `tier == 'LOW'` · `contracts == 1` | `tier == 'LOW'` · `contracts == 2` | Cell `(REACTIVE_LONG, Neutral_Center=fallback, LOW)` = `3/2/2 → LOW=2` |
| L42 | `setup is None` (R:R reject) | unchanged | Independent of sizing |
| L54-55 | `setup is not None` · `time_stop == 20` | `setup is None` (NT skip) | NT cells all 0/0/0 + verdict SKIP → emit_t1_setup returns None |

CC must rewrite L54-55 to `assert setup is None  # NT day → Auth Table SKIP` and remove the `time_stop_minutes == 20` line. Optionally add a new assert that captures the WARN log (caplog fixture).

---

## 6 · Known integration ripple (out of Pkg 8 scope · Cursor follow-up)

`tests/atomic/test_cross_system_integration.py:158`:

```python
with patch("backend.v9.systems.five_min.setup_emitter.get_quality_tier", ...)
```

This patch path will no-op after Pkg 8 because `setup_emitter.py` will import `get_quality_tier_v2` instead. The test may still pass if it doesn't depend on the mock taking effect · or it may fail.

**Action:** CC does NOT touch this file. After Pkg 8 G3, Cursor will:
1. Run `pytest tests/atomic/test_cross_system_integration.py -q`
2. If it fails, open a 1-line follow-up to update the patch target to `get_quality_tier_v2`
3. Document in G3 report

---

## 7 · Allowed imports (whitelist)

```python
# auth_table_v1.py
from __future__ import annotations
from typing import Dict, Literal, Optional, Tuple
from backend.v9.systems.five_min.output_schema import PatternName
import logging

# quality_tier.py (V2 rewrite)
from __future__ import annotations
import warnings
import logging
from typing import Literal, Optional, Tuple
import requests
from backend.v9.systems.five_min.auth_table_v1 import get_auth_cell

# test_auth_table_v1.py + test_quality_tier.py (V2 additions)
import pytest
import logging
from typing import get_args
from backend.v9.systems.five_min.auth_table_v1 import get_auth_cell, _AUTH_TABLE_V1, DAY_TYPES
from backend.v9.systems.five_min.quality_tier import get_quality_tier, get_quality_tier_v2
from backend.v9.systems.five_min.output_schema import PatternName

# setup_emitter.py (ADAPT)
# All existing imports keep · only change line 16 from `get_quality_tier` to `get_quality_tier_v2`
```

**NO imports outside this list.** Hallucinated APIs = retry.

---

## 8 · Acceptance criteria

| # | Criterion | Verify |
|---|---|---|
| 1 | `pytest tests/v9/systems/test_five_min/test_auth_table_v1.py -v` → all green (15+) | run + paste tail |
| 2 | `pytest tests/v9/systems/test_five_min/test_quality_tier.py -v` → all green (3 V1 + 9 V2 = 12+) | run + paste tail |
| 3 | `pytest tests/v9/systems/test_five_min/test_setup_emitter.py -v` → all green (4 updated) | run + paste tail |
| 4 | `pytest backend/v9/systems/five_min/tests/ -q` → no new regressions vs HEAD `1e01c4a` (compare counts) | run + paste tail |
| 5 | `pytest tests/v9/ -q` → full suite · zero new failures (record before/after totals) | run + paste tail |
| 6 | ReadLints clean on all 5 edited/new files | paste output |
| 7 | `rg "max\(1, sizing\)" backend/v9/systems/five_min/` → 0 hits (advisory floor removed) | rg |
| 8 | `rg "from .quality_tier import get_quality_tier\b" backend/v9/systems/five_min/setup_emitter.py` → 0 hits (V1 import gone from emitter) | rg |
| 9 | `rg "get_quality_tier_v2" backend/v9/systems/five_min/setup_emitter.py` → exactly 2 hits (1 import + 1 call) | rg |
| 10 | T1Setup `sizing_contracts` schema unchanged (no `output_schema.py` diff) | diff |
| 11 | NT day_type cell verdict always SKIP and contracts always 0 (CC self-runs `test_nt_row_global_skip`) | report inline |
| 12 | Max(contracts) across the full table == 3 (Q6 cap) | report inline |

---

## 9 · Constraints (must not violate · pre-LIVE protocol)

- **No silent excepts.** Every `except` includes `logger.warning("[Pkg8/<module>] <message>", ...)` rate-limited.
- **No `return None` without prior log** at info/warning level explaining why.
- **No new dependencies** (pip / package.json).
- **No "while I'm here" refactors** outside SCOPE files. If you notice an obviously broken thing in a forbidden file, document in §11 deliverable self-report and STOP if it blocks the work.
- **Hardcoded values forbidden** — `PROXIMITY_PT`, `TPO_ENDPOINT`, day-type aliases must be module-level constants at top of file.
- **No async I/O.** `requests.get()` already used in V1 — keep synchronous with 2s timeout.
- **Auth Table cells from §1.1 verbatim.** Any cell mismatch = STOP signal (do NOT adjust based on intuition).
- **V1 wrapper MUST emit DeprecationWarning** via `warnings.warn(..., DeprecationWarning, stacklevel=2)`.
- **Commit message MUST include the Phase A flag** verbatim: `Phase A mechanical · DEMO+ parametric calibration`.

---

## 10 · `auth_table_v1.py` implementation sketch (CC writes this · scaffold only · CC may improve naming)

```python
"""S2 Auth Table V1 · pattern × day_type × tier → contracts lookup.

Pure const dict + lookup function. No state, no I/O. Read by quality_tier.py V2.

Authority: docs/spec_authority/S2_AUTH_TABLE_V1.md (🔒 LOCKED 2026-05-25 12:22).
Source: D-095 path A · 10 PatternName · 7 DayType · 3 quality tiers = 70 cells.

Pkg 8 · Quality V2 · NEXT in Phase A queue.
"""
from __future__ import annotations

import logging
from typing import Dict, Literal, Optional, Tuple

from backend.v9.systems.five_min.output_schema import PatternName

logger = logging.getLogger(__name__)

QualityVerdict = Literal['FULL', 'REDUCED', 'SKIP']
QualityTier = Literal['HIGH', 'MEDIUM', 'LOW']

# Day-type vocabulary per S2_AUTH_TABLE_V1.md §3
DAY_TYPES: Tuple[str, ...] = (
    "Trend_Normal", "Trend_DD", "Neutral_Extreme",
    "Variation", "Neutral_Center", "Normal", "Nontrend",
)

# Source: S2_AUTH_TABLE_V1.md §4 verbatim
# Format: (pattern_name, day_type): (verdict, HIGH, MEDIUM, LOW)
_AUTH_TABLE_V1: Dict[Tuple[str, str], Tuple[QualityVerdict, int, int, int]] = {
    # REACTIVE_LONG (rows 12 source)
    ("REACTIVE_LONG", "Trend_Normal"):     ("REDUCED", 2, 1, 0),
    ("REACTIVE_LONG", "Trend_DD"):         ("REDUCED", 2, 1, 0),
    ("REACTIVE_LONG", "Neutral_Extreme"):  ("FULL",    3, 2, 2),
    ("REACTIVE_LONG", "Variation"):        ("FULL",    3, 2, 2),
    ("REACTIVE_LONG", "Neutral_Center"):   ("FULL",    3, 2, 2),
    ("REACTIVE_LONG", "Normal"):           ("FULL",    3, 2, 2),
    ("REACTIVE_LONG", "Nontrend"):         ("SKIP",    0, 0, 0),

    # ... (60 more cells exactly per §1.1) ...

    ("BEAR_FLAG_SHORT", "Nontrend"):       ("SKIP",    0, 0, 0),
}

# Import-time invariant: 70 cells total
assert len(_AUTH_TABLE_V1) == 70, f"Auth Table V1 has {len(_AUTH_TABLE_V1)} cells, expected 70"

# Import-time invariant: PatternName Literal coverage
from typing import get_args
_pattern_names = set(get_args(PatternName))
_table_patterns = {k[0] for k in _AUTH_TABLE_V1}
assert _table_patterns == _pattern_names, (
    f"Auth Table patterns {_table_patterns} != PatternName Literal {_pattern_names}"
)

# Import-time invariant: max contracts == 3 (Q6 cap)
_max_contracts = max(max(v[1], v[2], v[3]) for v in _AUTH_TABLE_V1.values())
assert _max_contracts == 3, f"Max contracts in table = {_max_contracts}, expected 3"


def get_auth_cell(
    pattern_name: str,
    day_type: str,
) -> Tuple[QualityVerdict, int, int, int]:
    """Return (verdict, HIGH, MEDIUM, LOW) for the given (pattern × day_type) cell.

    Unknown pattern_name → ValueError (no silent fallback).
    Unknown day_type → fallback to Neutral_Center cell + logger.warning.
    """
    from typing import get_args
    if pattern_name not in get_args(PatternName):
        raise ValueError(
            f"auth_table_v1: pattern_name={pattern_name!r} not in PatternName Literal. "
            f"Known: {sorted(get_args(PatternName))}"
        )

    if day_type not in DAY_TYPES:
        logger.warning(
            "[Pkg8/auth_table_v1] unknown day_type=%s · falling back to Neutral_Center "
            "(D-091.Q1 safe default)",
            day_type,
        )
        day_type = "Neutral_Center"

    return _AUTH_TABLE_V1[(pattern_name, day_type)]
```

---

## 11 · Deliverable format (CC self-report)

After completion, CC outputs:

1. **Files changed** (full paths · A=add / M=modify / D=delete):
   - A · `backend/v9/systems/five_min/auth_table_v1.py`
   - M · `backend/v9/systems/five_min/quality_tier.py` (full rewrite)
   - M · `backend/v9/systems/five_min/setup_emitter.py` (5-line change)
   - M · `backend/v9/systems/five_min/tests/test_setup_emitter.py` (4 test updates)
   - M · `tests/v9/systems/test_five_min/test_quality_tier.py` (3 V1 + 9 V2)
   - A · `tests/v9/systems/test_five_min/test_auth_table_v1.py`

2. **Commit message** (verbatim · single line · conventional commits):
   ```
   feat(s2): Pkg 8 · Quality V2 · Auth Table V1 (pattern × day_type × tier sizing) · Phase A mechanical · DEMO+ parametric calibration
   ```

3. **Self-report:**
   - Any TODOs left in code? (must be empty)
   - Any spec ambiguity encountered? (list explicitly · STOP signal if blocked)
   - Any forbidden constraint accidentally violated? (own up — Cursor catches in G3 anyway)
   - LOC count breakdown (auth_table_v1 / quality_tier / tests)

4. **ReadLints output** (paste verbatim · all 5 edited/new files)

5. **pytest outputs** (paste verbatim · tail 30 lines for each):
   - `pytest tests/v9/systems/test_five_min/test_auth_table_v1.py -v`
   - `pytest tests/v9/systems/test_five_min/test_quality_tier.py -v`
   - `pytest tests/v9/systems/test_five_min/test_setup_emitter.py -v`
   - `pytest tests/v9/ -q` (full suite · before/after counts must match within `42 failed/1114 passed · 1 skipped` baseline)

---

## 12 · Stop signal

IF any of these conditions met, STOP and output `STOP — <reason> · need Michael decision on <specific question>`:

- §1.1 Auth Table cell value differs from what you'd compute from spec source · STOP (do not adjust)
- Any forbidden file (§3) appears in your edit list · STOP
- An allowed import (§7) doesn't exist · STOP and report
- A golden test scenario (§4) is impossible to construct from current code shape · STOP
- `pytest tests/v9/ -q` baseline count drifts (was: 42 failed / 1114 passed / 1 skipped at HEAD `1e01c4a`) · STOP and inspect
- The Auth Table cell `(REACTIVE_LONG, Neutral_Center, LOW)` returns anything other than `2 contracts` · STOP (typo or transcription drift)
- `setup_emitter.py` line 60 `max(1, sizing)` survives in the diff · STOP (Lock #2 violation)

**DO NOT guess. DO NOT add a comment "TODO: ask Michael".**

---

## 13 · Authority & references

- **Auth Table V1:** `docs/spec_authority/S2_AUTH_TABLE_V1.md` (🔒 LOCKED 2026-05-25 12:22)
- **D-095:** `docs/decisions/D-095_DEFER_4A_4B_SCOPE_ABSORBED.md` (🔒 LOCKED 2026-05-25 11:18)
- **D-091:** `docs/decisions/D-091_S2_LIVE_SCOPE.md` (§Q2 NT NO_TRADE gate)
- **Constitution V3:** `docs/spec_authority/MEMS26_CONSTITUTION_V3_FINAL.txt` (§Layer 2 amendment 2026-05-25 12:22)
- **Pre-LIVE protocol:** `.cursor/rules/mems26-pre-live-protocol.mdc`
- **Mega-prompt template:** `docs/templates/MEGA_PROMPT_TEMPLATE.md`

---

*End of handoff · ready for Claude Desktop to convert into final CC mega-prompt · 2026-05-25 12:25 IL Cursor*
