# Pkg 3c · Contract split per pattern (emit-only · feeds Pkg 6)

**Authority:** D-091 §Contract Distribution (lines 175-183 of `docs/decisions/D-091_S2_LIVE_SCOPE.md`)
**Predecessor:** Pkg 5c G3 PASS (commit `427d687` · 24/5 19:30 IL) · HEAD = `427d687`
**Status:** Spec ready · Cursor handoff for Claude Desktop mega-prompt → CC exec
**Estimated CC time:** ~2 hours (small scope · pure data + minimal wiring · no detection · no integration math)
**Independent of:** Pkg 3b trail engine (orthogonal · 3b is execution-time · 3c is emit-time) · Pkg 6 TradeManager (will CONSUME split percentages · not affect emit)

---

## §1 · Why this exists

D-091 §Contract Distribution defines 5 split schemas, one per pattern family, totaling 100% across T1/T2/T3 (or T1/T2 only for Flag continuation). Currently `T1Setup.sizing_contracts` carries the **total** contract count (day-type-driven · per `targets_table.py`), but **the per-leg split percentage is missing from the canonical output**. Pkg 6 TradeManager will need this to allocate contracts across legs (e.g., 3 contracts × `(0.25, 0.50, 0.25)` Zohar OFA split → Pkg 6 rounds to 1/2/0 or 1/1/1 per its rounding rule).

Pkg 3c is **emit-only**:
- New module `contract_split.py` exposes `get_contract_split(pattern_name) -> Tuple[float, float, float]`.
- T1Setup gains 3 new fields: `t1_pct`, `t2_pct`, `t3_pct` (each `Field(ge=0.0, le=1.0)` · sum must be `1.0 ± 0.001`).
- `setup_emitter.emit_t1_setup` looks up the split at emit time and populates the 3 fields.

Pkg 6 will consume these fields and apply rounding logic to compute actual contract counts per leg (NOT Pkg 3c's concern).

---

## §2 · Spec authority

### §2.A · D-091 §Contract Distribution (verbatim · lines 175-183)

```
| Pattern family               | T1 / T2 / T3 split |
| Default (Bulkowski-modal)    | 50% / 30% / 20% |
| OFA (Reactive + Initiative)  | 25% / 50% / 25% (Zohar) |
| H&S + Inverse H&S            | 33% / 33% / 34% |
| Double Bottom + Double Top   | 33% / 33% / 34% |
| Bull Flag + Bear Flag        | 50% / 50% (no T3 — continuation) |
```

### §2.B · Mapping table · all 10 current PatternName values → split

| PatternName (output_schema.py) | Family | T1 / T2 / T3 |
|---|---|---|
| `REACTIVE_LONG` | OFA (Zohar) | 0.25 / 0.50 / 0.25 |
| `REACTIVE_SHORT` | OFA (Zohar) | 0.25 / 0.50 / 0.25 |
| `INITIATIVE_LONG` | OFA (Zohar) | 0.25 / 0.50 / 0.25 |
| `INITIATIVE_SHORT` | OFA (Zohar) | 0.25 / 0.50 / 0.25 |
| `INVERSE_HNS_LONG` | H&S | 0.33 / 0.33 / 0.34 |
| `HNS_TOP_SHORT` | H&S | 0.33 / 0.33 / 0.34 |
| `DOUBLE_BOTTOM_EE_LONG` | Double | 0.33 / 0.33 / 0.34 |
| `DOUBLE_TOP_AA_SHORT` | Double | 0.33 / 0.33 / 0.34 |
| `BULL_FLAG_LONG` | Flag | 0.50 / 0.50 / 0.00 |
| `BEAR_FLAG_SHORT` | Flag | 0.50 / 0.50 / 0.00 |

**All sums = 1.0 ± 0.001.** Verify at module import time via assertion.

The "Default Bulkowski-modal 50/30/20" is **NOT mapped to any current pattern**. Reserved for future patterns (e.g., Triangle / Cup&Handle if scope expands). Pkg 3c does NOT register a default fallback — unknown `pattern_name` raises `ValueError`.

### §2.C · Boundary with Pkg 6 (TradeManager · LAST)

Pkg 3c emits percentages. Pkg 6 will:
- Read `t1_pct / t2_pct / t3_pct` from `T1Setup`
- Multiply by `sizing_contracts` (integer · day-type-driven · existing field)
- Apply rounding (largest-remainder method · or T1-priority · Pkg 6 decides)
- Place 1-3 sub-orders (or 1-2 for Flag where `t3_pct=0.0`)
- Manage each leg's exit per D-091 §Trade Management

Pkg 3c MUST NOT do any rounding · MUST NOT compute integer contract counts · MUST NOT touch `sizing_contracts` field (it stays as the total).

---

## §3 · SCOPE · 1 NEW file + 2 MODIFIED files + 1 NEW test file + minor test updates

### §3.A · NEW · `backend/v9/systems/five_min/contract_split.py`

Pure-data module · no I/O · no state. ~50 LOC.

```python
"""contract_split — per-pattern T1/T2/T3 contract split percentages per D-091 §Contract Distribution.

Pure lookup module · no state · no I/O. Used by setup_emitter at emit time
to populate T1Setup.t1_pct / t2_pct / t3_pct fields.

Pkg 3c · emit-only. Pkg 6 (TradeManager) consumes these percentages and
applies rounding to integer contract counts based on T1Setup.sizing_contracts.

Authority: D-091 §Contract Distribution (lines 175-183 of D-091_S2_LIVE_SCOPE.md).
"""
from __future__ import annotations
from typing import Dict, Tuple

# Per-pattern split (T1, T2, T3) · each value in [0.0, 1.0] · sum = 1.0 ± 0.001
_SPLIT_MAP: Dict[str, Tuple[float, float, float]] = {
    # OFA family (Zohar 25/50/25)
    "REACTIVE_LONG":          (0.25, 0.50, 0.25),
    "REACTIVE_SHORT":         (0.25, 0.50, 0.25),
    "INITIATIVE_LONG":        (0.25, 0.50, 0.25),
    "INITIATIVE_SHORT":       (0.25, 0.50, 0.25),
    # H&S family (33/33/34)
    "INVERSE_HNS_LONG":       (0.33, 0.33, 0.34),
    "HNS_TOP_SHORT":          (0.33, 0.33, 0.34),
    # Double family (33/33/34)
    "DOUBLE_BOTTOM_EE_LONG":  (0.33, 0.33, 0.34),
    "DOUBLE_TOP_AA_SHORT":    (0.33, 0.33, 0.34),
    # Flag family (50/50 · no T3 · continuation)
    "BULL_FLAG_LONG":         (0.50, 0.50, 0.00),
    "BEAR_FLAG_SHORT":        (0.50, 0.50, 0.00),
}

# Import-time invariant: every entry sums to 1.0 ± 0.001
for _name, _split in _SPLIT_MAP.items():
    _sum = sum(_split)
    assert abs(_sum - 1.0) < 0.001, f"contract_split: {_name} sums to {_sum:.4f} != 1.0"


def get_contract_split(pattern_name: str) -> Tuple[float, float, float]:
    """Return (t1_pct, t2_pct, t3_pct) for the given pattern.

    Raises ValueError if pattern_name is not registered.
    NO silent fallback — pre-LIVE protocol forbids silent failures.
    """
    split = _SPLIT_MAP.get(pattern_name)
    if split is None:
        raise ValueError(
            f"contract_split: pattern_name={pattern_name!r} not registered. "
            f"Known patterns: {sorted(_SPLIT_MAP.keys())}"
        )
    return split
```

### §3.B · MODIFY · `backend/v9/systems/five_min/output_schema.py`

Add 3 new fields to `T1Setup` (between `confidence` and `bar_index`):

```python
class T1Setup(BaseModel):
    """Canonical T1 setup output."""
    system_id: Literal['T1_NUMBER_BAR'] = 'T1_NUMBER_BAR'
    pattern_name: PatternName
    direction: Literal['LONG', 'SHORT']

    entry_price: float = Field(gt=0)
    stop_price: float = Field(gt=0)
    t1_price: float = Field(gt=0)
    t2_price: float = Field(gt=0)
    t3_price: Optional[float] = Field(default=None, gt=0)
    time_stop_minutes: Optional[int] = Field(default=None, ge=1, le=180)
    confidence: int = Field(ge=0, le=100)

    # Pkg 3c · contract split (per D-091 §Contract Distribution)
    t1_pct: float = Field(ge=0.0, le=1.0, default=0.0)
    t2_pct: float = Field(ge=0.0, le=1.0, default=0.0)
    t3_pct: float = Field(ge=0.0, le=1.0, default=0.0)

    bar_index: int = Field(ge=0)
    fired_at: datetime

    quality_tier: Literal['HIGH', 'MEDIUM', 'LOW'] = 'MEDIUM'
    sizing_contracts: int = Field(ge=0, le=3, default=2)
    provisional: bool = True
    provisional_reason: Optional[str] = None
```

**Defaults `0.0` for backward compat:** any code that constructs `T1Setup` without setting these fields gets `0.0, 0.0, 0.0` (which Pkg 6 will treat as "no split info · fall back to 1/0/0 single-leg" — but this code path should never fire in production because `setup_emitter` always populates them per §3.C).

**No validation that sum = 1.0** at schema level · the `setup_emitter` is the single emit path · validation lives there + at module import time in `contract_split.py`.

### §3.C · MODIFY · `backend/v9/systems/five_min/setup_emitter.py` — 1 edit

Add 2 lines: import + call. Insert after the existing import block (around line 17) and use the result when building the T1Setup (around line 65).

```python
# Top of file · after existing imports
from backend.v9.systems.five_min.contract_split import get_contract_split

# Inside emit_t1_setup · after `time_stop = get_time_stop(day_type)` (around line 62)
# and BEFORE the `setup = T1Setup(...)` construction
t1_pct, t2_pct, t3_pct = get_contract_split(pattern_name)

# Then inside the T1Setup constructor call · add 3 kwargs
setup = T1Setup(
    pattern_name=pattern_name,
    direction=direction,
    entry_price=entry_price,
    stop_price=stop_price,
    t1_price=t1_price,
    t2_price=t2_price,
    t3_price=t3_price,
    time_stop_minutes=time_stop,
    confidence=75,
    t1_pct=t1_pct,                       # ← NEW Pkg 3c
    t2_pct=t2_pct,                       # ← NEW Pkg 3c
    t3_pct=t3_pct,                       # ← NEW Pkg 3c
    bar_index=bar_index,
    fired_at=datetime.now(timezone.utc),
    quality_tier=quality_tier,
    sizing_contracts=sizing,
    provisional=False,
    provisional_reason=None,
)
```

That's it for the emitter. `get_contract_split` raises `ValueError` if `pattern_name` is unknown — this propagates up (CC must NOT wrap it in try/except).

### §3.D · NEW · `tests/v9/systems/test_five_min/test_contract_split.py`

~10 unit tests:

| # | Test | Expected |
|---|---|---|
| 1 | `test_reactive_long_is_zohar_25_50_25` | `get_contract_split("REACTIVE_LONG") == (0.25, 0.50, 0.25)` |
| 2 | `test_reactive_short_is_zohar_25_50_25` | same |
| 3 | `test_initiative_long_is_zohar_25_50_25` | same |
| 4 | `test_initiative_short_is_zohar_25_50_25` | same |
| 5 | `test_inverse_hns_long_is_33_33_34` | `(0.33, 0.33, 0.34)` |
| 6 | `test_hns_top_short_is_33_33_34` | same |
| 7 | `test_double_bottom_ee_long_is_33_33_34` | same |
| 8 | `test_double_top_aa_short_is_33_33_34` | same |
| 9 | `test_bull_flag_long_is_50_50_zero` | `(0.50, 0.50, 0.00)` |
| 10 | `test_bear_flag_short_is_50_50_zero` | same |
| 11 | `test_unknown_pattern_raises_value_error` | `pytest.raises(ValueError, match="not registered")` for `"FOO"` |
| 12 | `test_all_splits_sum_to_1_0` | iterate `_SPLIT_MAP` · assert each sums to 1.0 ± 0.001 |
| 13 | `test_module_import_time_invariant_holds` | verify `_SPLIT_MAP` has exactly 10 entries (all 10 current PatternName values) |

### §3.E · MODIFY · `tests/v9/systems/test_five_min/test_output_schema.py`

Existing tests construct `T1Setup` directly without the new fields — they should still pass (defaults = 0.0). Add 1 new test:

```python
def test_t1setup_accepts_contract_split_percentages():
    setup = T1Setup(
        pattern_name="REACTIVE_LONG",
        direction="LONG",
        entry_price=4500, stop_price=4495,
        t1_price=4510, t2_price=4520,
        confidence=75, bar_index=10,
        fired_at=datetime.now(timezone.utc),
        t1_pct=0.25, t2_pct=0.50, t3_pct=0.25,
    )
    assert setup.t1_pct == 0.25
    assert setup.t2_pct == 0.50
    assert setup.t3_pct == 0.25
```

### §3.F · MODIFY · `tests/v9/systems/test_five_min/test_setup_emitter.py`

Existing emit tests (e.g., `test_emit_uses_day_type_time_stop`) should still pass because `setup_emitter` now calls `get_contract_split` for any registered pattern_name. Add 1 new test:

```python
def test_setup_emitter_populates_contract_split_for_reactive_long():
    setup = emit_t1_setup(
        pattern_name="REACTIVE_LONG",
        direction="LONG",
        entry_price=4500, stop_price=4495,
        t1_price=4510, t2_price=4520,
        bar_index=10,
        day_type="Trend_Normal",
    )
    assert setup is not None
    assert (setup.t1_pct, setup.t2_pct, setup.t3_pct) == (0.25, 0.50, 0.25)
```

If pre_fire_validator rejects the setup (e.g., R:R too tight), the test should still construct a fixture that passes validation. If it doesn't, mock the validator.

---

## §4 · Acceptance criteria · G3 PASS gate

1. `pytest tests/v9/systems/test_five_min/test_contract_split.py -v` → **13 passed**
2. `pytest tests/v9/systems/test_five_min/test_output_schema.py -q` → existing + 1 new test all pass
3. `pytest tests/v9/systems/test_five_min/test_setup_emitter.py -q` → existing + 1 new test all pass
4. `pytest tests/v9/systems/ -q` → **679 passed · 1 skipped** (was 666 after 5c · +13 new)
5. `pytest backend/v9/tests/ -q` → **531 passed · 2 skipped** (no regression)
6. `pytest backend/v9/systems/five_min/tests/ -q` → **70 passed · 8 failed** (F4 baseline · ZERO new failures)
7. `ReadLints` on all 4 changed files + 1 new file → 0 errors
8. `backend.main` imports cleanly: `python -c "from backend.v9.systems.five_min.contract_split import get_contract_split; print(get_contract_split('REACTIVE_LONG'))"` → `(0.25, 0.5, 0.25)`
9. `T1Setup(...)` validates with the 3 new fields default to 0.0 (backward compat for tests that don't pass them)
10. Import-time assertion in `contract_split.py` does not break module import (sums are all 1.0 ± 0.001)
11. `get_contract_split("UNKNOWN")` raises `ValueError` with helpful message

---

## §5 · Constraints (must NOT violate)

- **No silent excepts.** `get_contract_split` raises `ValueError` for unknown patterns · `setup_emitter` does NOT wrap it (propagates up · loud failure in dev · caught by `pre_fire_validator` failure path in worst case).
- **No new dependencies** (stdlib only · `typing` already imported).
- **No "while I'm here" refactors:**
  - Do NOT change `sizing_contracts` field (Pkg 6 territory · still day-type-driven from `targets_table`)
  - Do NOT change `targets_table.py` (Pkg 3a frozen)
  - Do NOT modify `day_type_targets.py` (Pkg 3a frozen)
  - Do NOT touch any pattern detector (`patterns/*.py` · all frozen)
  - Do NOT modify `five_min_system.py` (5a/5b/5c integration is locked)
  - Do NOT modify `manager.py` (Pkg 6 territory)
- **Lines 215-217 of `five_min_system.py` MUST stay byte-identical** (chronic toxicity block per Pkg 0).
- **Integer contract rounding is FORBIDDEN in Pkg 3c.** Emit percentages only · let Pkg 6 round.
- **`_SPLIT_MAP` keys MUST be exactly the 10 current `PatternName` Literal values.** Adding/removing entries requires a D-091 amendment.
- **No persistence to DB.** Pkg 3c does not modify any DB model. `t1_pct`/`t2_pct`/`t3_pct` flow through T1Setup at runtime · DB persistence is Pkg 6's call.

---

## §6 · Forbidden zones

```
🛑 DO NOT modify:
  - backend/v9/systems/five_min/patterns/*           (all frozen · Pkg 5a/5b/5c)
  - backend/v9/systems/five_min/five_min_system.py   (Pkg 5a/5b/5c integration frozen)
  - backend/v9/systems/five_min/adaptive_stop.py     (Pkg 1 frozen)
  - backend/v9/systems/day_type/*                    (Pkg 3a frozen)
  - backend/v9/systems/footprint/*                   (Pkg 2bc frozen)
  - backend/v9/services/trade_manager/*              (Pkg 6 territory)
  - backend/v9/db/models/*                           (no schema migration in Pkg 3c)

🛑 DO NOT add:
  - Default fallback for unknown patterns (raise ValueError)
  - DB persistence (Pkg 6's call)
  - Integer rounding logic (Pkg 6 territory)
  - Day-type-conditional split (split is PATTERN-driven · day_type is for sizing_contracts only)
```

---

## §7 · Pre-flight · current code state (verified by Cursor 24/5 19:30 IL)

### §7.A · Files that exist (read-only · do NOT modify outside scope)

```
backend/v9/systems/five_min/
├── __init__.py
├── adaptive_stop.py
├── ...
├── five_min_system.py              # 836 LOC · do NOT touch (5a/5b/5c locked)
├── output_schema.py                # 47 LOC · 1 edit per §3.B (+3 fields)
├── patterns/
│   ├── __init__.py
│   ├── double_bt.py                # Pkg 5b frozen
│   ├── flags.py                    # Pkg 5c frozen
│   └── head_shoulders.py           # Pkg 5a frozen
├── setup_emitter.py                # 107 LOC · 1 edit per §3.C (+2 lines)
└── time_stop_mapper.py             # Pkg 3a frozen
```

Pkg 3c adds: `contract_split.py` + `test_contract_split.py` + minor test updates.

### §7.B · `T1Setup` current schema (just for reference)

See `output_schema.py` lines 21-46. `PatternName` Literal has exactly 10 values (4 OFA + 2 H&S + 2 Double + 2 Flag).

### §7.C · `setup_emitter.emit_t1_setup` flow

1. NT defense-in-depth check (Pkg 3a frozen logic)
2. Quality tier + sizing from TPO
3. Time stop from day type
4. **[NEW Pkg 3c]** Lookup contract split from pattern_name
5. Build T1Setup (now with t1_pct/t2_pct/t3_pct)
6. Pre-fire validation
7. Return T1Setup or None

### §7.D · Test baseline (24/5 19:30 IL · HEAD = `427d687`)

- `tests/v9/systems/` → 666 passed · 1 skipped
- `backend/v9/tests/` → 531 passed · 2 skipped
- `backend/v9/systems/five_min/tests/` → 70 passed · 8 failed (F4 pre-existing · NOT Pkg 3c's responsibility)
- 1 uncommitted file: `backend/v9/systems/five_min/tests/test_time_stop_mapper.py` (hand-fix from Pkg 3a Stream 2 · still dirty · NOT Pkg 3c's responsibility)

---

## §8 · Validation recipe (CC runs after implementation)

```bash
# 1. Lint
python -m pyflakes backend/v9/systems/five_min/contract_split.py
python -m pyflakes backend/v9/systems/five_min/output_schema.py
python -m pyflakes backend/v9/systems/five_min/setup_emitter.py

# 2. New tests
pytest tests/v9/systems/test_five_min/test_contract_split.py -v

# 3. Schema + emitter regression
pytest tests/v9/systems/test_five_min/test_output_schema.py -q
pytest tests/v9/systems/test_five_min/test_setup_emitter.py -q

# 4. Pkg 5a/5b/5c regression check
pytest tests/v9/systems/test_five_min/test_head_shoulders.py -q
pytest tests/v9/systems/test_five_min/test_double_bt.py -q
pytest tests/v9/systems/test_five_min/test_flags.py -q
pytest tests/v9/systems/test_five_min/test_five_min_day_type_wiring.py -q

# 5. Full systems suite (expect 666 → 679)
pytest tests/v9/systems/ -q

# 6. Backend baseline
pytest backend/v9/tests/ -q --no-header

# 7. F4 baseline check
pytest backend/v9/systems/five_min/tests/ -q --no-header

# 8. Chronic toxicity byte-identical
sed -n '/Delegate to existing chart_5min detector/,/return None$/p' backend/v9/systems/five_min/five_min_system.py

# 9. Smoke
python -c "
from backend.v9.systems.five_min.contract_split import get_contract_split
for p in ['REACTIVE_LONG', 'INVERSE_HNS_LONG', 'BULL_FLAG_LONG', 'BEAR_FLAG_SHORT']:
    t1, t2, t3 = get_contract_split(p)
    assert abs((t1 + t2 + t3) - 1.0) < 0.001, f'{p}: sum != 1.0'
    print(f'{p}: ({t1:.2f}, {t2:.2f}, {t3:.2f}) sum={t1+t2+t3:.2f}')

try:
    get_contract_split('UNKNOWN_PATTERN')
    assert False, 'expected ValueError'
except ValueError as e:
    print(f'ValueError correctly raised: {e}')
"
```

---

## §9 · Stop signals (CC outputs `STOP — <reason>` and halts)

1. **D-091 amendment proposed mid-implementation** — if you discover D-091's mapping table is internally inconsistent or contradicts another decision doc · STOP. Do NOT invent split values.
2. **PatternName count drift** — if `output_schema.py` `PatternName` Literal has a count ≠ 10 when you read it · STOP (someone else has changed it · `_SPLIT_MAP` must match exactly).
3. **Pre-fire validator rejects test setup** — if `test_setup_emitter_populates_contract_split_for_reactive_long` fails because validator rejects · STOP and report (don't mock if the real validator should accept · investigate first).
4. **`T1Setup` field count grows beyond +3** — if you find yourself adding more than 3 fields to T1Setup · STOP. Pkg 3c is +3 exactly.
5. **Pkg 6 implementation drift** — if you discover anything that requires modifying `manager.py` · STOP. Pkg 3c does NOT touch trade manager.
6. **Sum != 1.0 ± 0.001** for any entry — STOP (import-time assertion should catch this · but if it slips through, do not silently normalize).
7. **Unknown pattern in production wiring** — if `setup_emitter` is called with a pattern_name not in `_SPLIT_MAP` during integration tests · STOP and report (the test is wrong OR the lookup is wrong).

---

## §10 · Deliverable format (CC outputs after completion)

1. **Files changed** (full paths · A/M/D):
   - `A backend/v9/systems/five_min/contract_split.py`
   - `M backend/v9/systems/five_min/output_schema.py` (+3 fields)
   - `M backend/v9/systems/five_min/setup_emitter.py` (+1 import +1 call +3 kwargs)
   - `A tests/v9/systems/test_five_min/test_contract_split.py`
   - `M tests/v9/systems/test_five_min/test_output_schema.py` (+1 test)
   - `M tests/v9/systems/test_five_min/test_setup_emitter.py` (+1 test)

2. **Commit message:**
   ```
   feat(s2): Pkg 3c · contract split per pattern (emit-only · feeds Pkg 6)

   - NEW backend/v9/systems/five_min/contract_split.py
     · get_contract_split(pattern_name) -> (t1_pct, t2_pct, t3_pct)
     · _SPLIT_MAP covers all 10 current PatternName values
     · Import-time assertion: each entry sums to 1.0 ± 0.001
     · Raises ValueError for unknown pattern (no silent fallback)
     · Per D-091 §Contract Distribution:
         OFA (Reactive + Initiative)  : 0.25 / 0.50 / 0.25 (Zohar)
         H&S (Inv H&S + H&S Top)       : 0.33 / 0.33 / 0.34
         Double (DB Eve&Eve + DT Adam) : 0.33 / 0.33 / 0.34
         Flag (Bull + Bear)            : 0.50 / 0.50 / 0.00 (no T3)
   - MODIFY output_schema.py · T1Setup +3 fields (t1_pct, t2_pct, t3_pct · ge=0 le=1 default=0.0)
   - MODIFY setup_emitter.py · 1 import + 1 lookup call + 3 kwargs to T1Setup
   - NEW test_contract_split.py · 13 unit tests
   - MODIFY test_output_schema.py · +1 test (T1Setup accepts split fields)
   - MODIFY test_setup_emitter.py · +1 test (emitter populates split for REACTIVE_LONG)

   Pkg 3c · emit-only. Pkg 6 (TradeManager · LAST) consumes percentages and
   applies rounding to integer contracts based on T1Setup.sizing_contracts.

   Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
   ```

3. **Self-report:**
   - Any TODOs left? (must be empty)
   - Any spec ambiguity encountered? (list explicitly)
   - Any forbidden constraint accidentally touched? (own up)
   - Lines 215-217 still byte-identical? (yes/no with diff)
   - `_SPLIT_MAP` has exactly 10 entries · all `PatternName` Literal values covered? (yes/no)
   - Import-time sum assertion present? (yes/no)
   - `get_contract_split` raises `ValueError` on unknown (not silently returns default)? (yes/no)

4. **ReadLints output** (paste verbatim · 5 files)

5. **pytest output** (paste verbatim · tail 30 lines each: `test_contract_split.py` · `test_output_schema.py` · `test_setup_emitter.py` · `tests/v9/systems/` · `backend/v9/tests/`)

---

## §11 · Estimated CC time

| Sub-task | Estimated | Notes |
|---|---|---|
| Read existing schema + emitter to understand wiring | 5 min | small files |
| Write `contract_split.py` (constants + lookup + assertion) | 20 min | mostly data |
| Modify `output_schema.py` (+3 fields) | 5 min | trivial |
| Modify `setup_emitter.py` (+1 import +1 call +3 kwargs) | 10 min | surgical |
| Write 13 tests in `test_contract_split.py` | 35 min | mostly parametric |
| Update `test_output_schema.py` + `test_setup_emitter.py` (1 test each) | 15 min | small additions |
| Run validation recipe · iterate | 20 min | expect 0-1 iterations |
| **Total** | **~2 hours CC time** | + Cursor G3 ~10 min (smallest Phase A Pkg) |

---

## §12 · Post-G3 PASS unlocks

| Unlocked | Why |
|---|---|
| **Pkg 6** (TradeManager rewrite · LAST) | Now has `T1Setup.t1_pct/t2_pct/t3_pct` to size legs |
| **Pkg 4a/4b** (Risk Rules) | Not blocked by 3c · can proceed in parallel |
| **G4 LIVE smoke trade UAT** | Setup emission now includes all spec'd metadata |
| Phase A is **2 Pkgs from complete** | 3b (trail · partial as 3b-1) + 3c. Then Pkg 8 + Pkg 6. |

---

*End of Pkg 3c handoff · Cursor agent · 2026-05-24 19:40 IL*
*Spec authority: D-091 §Contract Distribution (lines 175-183) · all 10 PatternName values mapped*
*Awaiting Claude Desktop mega-prompt drafting → CC execution → Cursor G3 review*
