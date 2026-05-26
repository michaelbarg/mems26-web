# Pkg 3a · Stream 2 · Day-type targets module + T1Setup + NT NO_TRADE gate

**Authority:** D-091 §Pkg 3a sub-decisions · Q1 (NeuE/NeuC) Q2 (NT gate location) Q4 (emit-only) all LOCKED 23/5 20:10
**Predecessor:** Stream 1 G3 PASS (`689ac41`) + Stream 1.5 G3 PASS (`548f1f6`)
**Status:** Spec ready · Cursor handoff for Claude Desktop mega-prompt → CC exec.
**Estimated CC time:** 4-6 hours (largest of the 3a streams).
**Independent of:** Stream 1.5 (already shipped). Stream 2 reads `current_day_type` from `_on_day_type_update` events + DB hydrate.

---

## §1 · Why this exists

Stream 1 wired NeuE/NeuC at the **classification layer** (DayTypeStateMachine + api.py).
Stream 1.5 wired it at the **state-machine re-classification layer** (`_rescore_from_behavior`).
**Stream 2 wires it at the consumption layer** — making sure S2's setup emission actually
**uses** the correct day type for targets and time stops, and rejects setups on NO_TRADE days.

Three concrete bugs Stream 2 fixes:

1. **`backend/v9/systems/five_min/five_min_system.py:708`** passes
   `day_type=self.opening_type` to `emit_t1_setup`. `self.opening_type` is an `OpeningType`
   enum value (`"OPEN_DRIVE"` etc.), not a `DayType` string. Result:
   `get_targets("OPEN_DRIVE")` returns `None` → `time_stop_mapper` silently defaults to 60min
   for **every** setup, regardless of actual day type.

2. **`backend/v9/systems/five_min/time_stop_mapper.py`** returns 60min DEFAULT for
   `Trend_Normal` (which should have `None` = no time stop) and for `Nontrend` (which should
   NEVER fire at all). Conflates "no time stop" with "unknown day type".

3. **No NT NO_TRADE gate exists.** Per D-091.Q2, Nontrend days must early-skip pattern
   detection inside `_check_setup` (CPU waste prevention) + emit a rate-limited log + expose
   a SHADOW counter. Without this, S2 would emit setups on NT days that the TradeManager
   would have to reject downstream — but since enforcement is deferred to Pkg 6 (Q4), nothing
   would currently reject them.

Stream 2 also adds the missing T1Setup output fields (`t3_price`) and makes
`time_stop_minutes` optional (None = no time stop, distinct from 60min unknown-fallback).

---

## §2 · Scope · 4 modified files + 1 new module + 2 new test files

### 2.A · NEW · `backend/v9/systems/day_type/day_type_targets.py`

Centralized targets-per-day-type resolver. Thin wrapper around `targets_table.get_targets()`
that resolves R-multiples to actual prices.

```python
"""day_type_targets — resolve R-based targets to actual prices per day type.

Reads from targets_table.get_targets() · returns gateway-ready price scheme.
Per D-091.Q1 + EXIT_V6 (7 day types: TN/TDD/V/N/NeuE/NeuC/NT).
"""
from __future__ import annotations
import logging
from typing import Optional, Dict, Any, Literal
from backend.v9.systems.day_type.targets_table import get_targets

logger = logging.getLogger(__name__)


class DayTypeTargetsResult(dict):
    """Type alias for the resolved targets dict (uses dict for JSON-friendliness)."""
    # keys: t1_price · t2_price · t3_price · time_stop_minutes ·
    #       trail_after_t2 · sizing_contracts · no_trade · day_type_canonical


def compute_targets_for_day_type(
    *,
    day_type: Optional[str],
    entry_price: float,
    stop_price: float,
    direction: Literal["LONG", "SHORT"],
) -> Optional[Dict[str, Any]]:
    """Resolve targets for a day type to actual prices.

    Returns dict with:
      - t1_price: float (always · 1R from entry)
      - t2_price: Optional[float] (None if anchor-based "POC"/"extreme"/"open" — Layer 3 wires it)
      - t3_price: Optional[float] (None if no T3 or anchor-based · resolved when t3_r is numeric)
      - time_stop_minutes: Optional[int] (None = no time stop, e.g. Trend_Normal)
      - trail_after_t2: bool
      - sizing_contracts: int
      - no_trade: bool (True for Nontrend · caller MUST short-circuit)
      - day_type_canonical: str (the resolved day type after alias mapping)

    Returns None if day_type unknown (caller treats as "skip / log warning").
    Risk distance R = |entry_price - stop_price|.
    """
    if day_type is None:
        return None

    targets = get_targets(day_type)
    if targets is None:
        logger.warning("[day_type_targets] unknown day_type=%s · returning None", day_type)
        return None

    R = abs(entry_price - stop_price)
    if R <= 0:
        logger.warning("[day_type_targets] non-positive R · entry=%.2f stop=%.2f", entry_price, stop_price)
        return None

    sign = 1.0 if direction == "LONG" else -1.0

    t1_r = targets.get("t1_r")
    t2_r = targets.get("t2_r")
    t3_r = targets.get("t3_r")

    t1_price = entry_price + sign * t1_r * R if t1_r else None
    t2_price = entry_price + sign * t2_r * R if t2_r else None  # None for anchor-based ("POC"/"extreme")
    t3_price = entry_price + sign * t3_r * R if t3_r else None

    return {
        "t1_price": t1_price,
        "t2_price": t2_price,
        "t3_price": t3_price,
        "time_stop_minutes": targets.get("time_stop_minutes"),
        "trail_after_t2": targets.get("trail_after_t2", False),
        "sizing_contracts": targets.get("contracts", 0),
        "no_trade": targets.get("no_trade", False),
        "day_type_canonical": _resolve_canonical(day_type),
    }


def _resolve_canonical(day_type: str) -> str:
    """Map alias/legacy to canonical day type string."""
    upper = day_type.upper().replace(" ", "_")
    aliases = {
        "NEUTRAL": "Neutral_Center",
        "NEUTRAL_CENTER": "Neutral_Center",
        "NEUTRAL_EXTREME": "Neutral_Extreme",
        "NEUE": "Neutral_Extreme",
        "NEUC": "Neutral_Center",
    }
    return aliases.get(upper, day_type)
```

### 2.B · MODIFIED · `backend/v9/systems/five_min/output_schema.py`

Two surgical changes:

```python
# CURRENT (line 27):
    time_stop_minutes: int = Field(ge=1, le=180)

# NEW:
    time_stop_minutes: Optional[int] = Field(default=None, ge=1, le=180)
```

```python
# ADD after line 26 (after t2_price):
    t3_price: Optional[float] = Field(default=None, gt=0)
```

### 2.C · MODIFIED · `backend/v9/systems/five_min/time_stop_mapper.py`

Replace the silent 60min default with explicit `Optional[int]`:

```python
"""time_stop_mapper — maps Day Type to Optional[int] time_stop_minutes.

Per Constitution V3 §Layer 4 targets matrix + EXIT_V6 (D-091).
Returns None when day_type's targets specify no time stop (e.g. Trend_Normal).
Returns None when day_type is unknown — caller MUST handle explicitly.
"""
from __future__ import annotations
from typing import Optional
from backend.v9.systems.day_type.targets_table import get_targets


def get_time_stop(day_type: Optional[str]) -> Optional[int]:
    """Get time_stop_minutes for given Day Type, or None.

    Returns:
      - int 1..180 when day_type has a numeric time_stop_minutes
      - None when day_type has no time stop (Trend_Normal) OR no_trade=True (Nontrend)
      - None when day_type is unknown or None (no silent default per pre-LIVE protocol)
    """
    if day_type is None:
        return None
    targets = get_targets(day_type)
    if targets is None:
        return None
    if targets.get("no_trade", False):
        return None
    time_stop = targets.get("time_stop_minutes")
    if time_stop is None:
        return None
    return int(time_stop)
```

Note: The `DEFAULT_TIME_STOP = 60` constant is **removed** entirely. If any caller relied on
it (search the repo), they must be updated to handle `None` explicitly.

### 2.D · MODIFIED · `backend/v9/systems/five_min/setup_emitter.py`

Two changes:

1. **Accept `t3_price` parameter** and pass to T1Setup.
2. **Honor `no_trade=True`** — if the day type is NT, log and return None (defense in depth · should never reach here because of the early-skip gate in §2.E, but emit-layer must also refuse).

```python
def emit_t1_setup(
    pattern_name: PatternName,
    direction: Literal['LONG', 'SHORT'],
    entry_price: float,
    stop_price: float,
    t1_price: float,
    t2_price: float,
    bar_index: int,
    *,
    day_type: Optional[str] = None,
    t3_price: Optional[float] = None,         # NEW
    current_price: Optional[float] = None,
    tpo_data: Optional[dict] = None,
) -> Optional[T1Setup]:
    # ... existing quality_tier + sizing logic ...

    # D-091.Q2 defense-in-depth: refuse NT setups at emit layer
    if day_type:
        from backend.v9.systems.day_type.targets_table import get_targets
        _targets = get_targets(day_type)
        if _targets is not None and _targets.get("no_trade", False):
            logger.warning(
                "[S2] emit_t1_setup refused: day_type=%s is NO_TRADE (D-091.Q2)",
                day_type,
            )
            return None

    # Time stop from Day Type · now Optional[int]
    time_stop = get_time_stop(day_type)

    # Build T1Setup (time_stop_minutes now Optional · t3_price NEW)
    setup = T1Setup(
        pattern_name=pattern_name,
        direction=direction,
        entry_price=entry_price,
        stop_price=stop_price,
        t1_price=t1_price,
        t2_price=t2_price,
        t3_price=t3_price,                    # NEW
        time_stop_minutes=time_stop,
        confidence=75,
        bar_index=bar_index,
        fired_at=datetime.now(timezone.utc),
        quality_tier=quality_tier,
        sizing_contracts=sizing,
        provisional=False,
        provisional_reason=None,
    )

    # ... existing validate_fire + return logic ...
```

### 2.E · MODIFIED · `backend/v9/systems/five_min/five_min_system.py`

**Five surgical edits.**

#### Edit 1 · Add `current_day_type` instance attribute

After existing `self.opening_type: Optional[str] = None` (line 61), add:

```python
        self.current_day_type: Optional[str] = None  # Stream 2 · D-091.Q1 NeuE/NeuC source
        self._nt_skip_count: int = 0                  # Stream 2 · D-091.Q2 SHADOW counter
        self._nt_skip_last_log_ts: float = 0.0        # Rate-limit anchor for NT skip log
```

#### Edit 2 · Hydrate `current_day_type` from DB on startup

After the existing `state = db.query(V9FiveMinState).filter(...).first()` block
(around line 113-117), add a second query for the latest day_type:

```python
        # Stream 2 · hydrate current_day_type from v9_day_type_state (P5.1.2 persist)
        try:
            import sqlite3
            DB_PATH = "/Users/michael/Downloads/mems26_web_git/data/mems26_local.db"
            _conn = sqlite3.connect(DB_PATH)
            _row = _conn.execute(
                "SELECT day_type FROM v9_day_type_state "
                "WHERE date(ts) = date('now', 'localtime') "
                "ORDER BY id DESC LIMIT 1"
            ).fetchone()
            _conn.close()
            if _row and _row[0]:
                self.current_day_type = _row[0]
                logger.info("[FiveMin] Hydrated current_day_type=%s from v9_day_type_state", self.current_day_type)
        except Exception as e:
            logger.warning("[FiveMin] day_type hydrate failed: %s · live updates will populate", e)
```

#### Edit 3 · Wire `_on_day_type_update` to store day_type

Current (lines 219-222):
```python
    def _on_day_type_update(self, event: dict) -> None:
        """Handle Day Type classification update."""
        # Store for context — used by confluence scoring
        return None
```

New:
```python
    def _on_day_type_update(self, event: dict) -> None:
        """Handle Day Type classification update (Stream 2 · D-091)."""
        payload = event.get("payload", {}) if isinstance(event, dict) else {}
        new_dt = payload.get("day_type") or payload.get("classification")
        if new_dt and isinstance(new_dt, str):
            if new_dt != self.current_day_type:
                logger.info("[FiveMin] current_day_type: %s → %s", self.current_day_type, new_dt)
            self.current_day_type = new_dt
        return None
```

#### Edit 4 · D-091.Q2 NT early-skip gate (before pattern detection)

After `self._bar_buffer = self._bar_buffer[-20:]` (around line 620) and **before** the
`# Run pattern detectors` block (line 622), insert:

```python
        # D-091.Q2 · NT NO_TRADE early-skip (CPU + emit-layer defense)
        if self.current_day_type == "Nontrend":
            self._nt_skip_count += 1
            import time as _time
            _now = _time.monotonic()
            if _now - self._nt_skip_last_log_ts >= 60.0:  # rate-limit 1/min
                logger.info(
                    "[S2] NT NO_TRADE skip · cumulative=%d · D-091.Q2",
                    self._nt_skip_count,
                )
                self._nt_skip_last_log_ts = _now
            return
```

#### Edit 5 · Fix line 708 + compute t3_price

Current (lines 697-711, focus on 698-710):
```python
            # Phase 5.5: Wire to setup_emitter → gateway (SHADOW auto-fire)
            try:
                pattern_name = f"{kind}_{direction}"
                t1_risk = abs(entry_price - stop_price)
                t1_price = (entry_price + t1_risk) if direction == "LONG" else (entry_price - t1_risk)
                t2_price = (entry_price + 2 * t1_risk) if direction == "LONG" else (entry_price - 2 * t1_risk)
                t1_setup = emit_t1_setup(
                    pattern_name, direction,
                    entry_price=entry_price, stop_price=stop_price,
                    t1_price=t1_price, t2_price=t2_price,
                    bar_index=self.buffer_size,
                    day_type=self.opening_type,
                    current_price=entry_price,
                )
```

New:
```python
            # Phase 5.5: Wire to setup_emitter → gateway (SHADOW auto-fire)
            try:
                pattern_name = f"{kind}_{direction}"
                # Stream 2 · resolve targets per day_type (D-091.Q1)
                from backend.v9.systems.day_type.day_type_targets import compute_targets_for_day_type
                _targets = compute_targets_for_day_type(
                    day_type=self.current_day_type,
                    entry_price=entry_price,
                    stop_price=stop_price,
                    direction=direction,
                )
                if _targets is not None:
                    t1_price = _targets["t1_price"]
                    # T2/T3 from day_type when numeric · fallback to R-multiples for now
                    t1_risk = abs(entry_price - stop_price)
                    t2_price = _targets.get("t2_price") or (
                        (entry_price + 2 * t1_risk) if direction == "LONG"
                        else (entry_price - 2 * t1_risk)
                    )
                    t3_price = _targets.get("t3_price")  # None when no T3 or anchor-based
                else:
                    # Fallback R-multiples when day_type unknown (defensive, logged at compute)
                    t1_risk = abs(entry_price - stop_price)
                    t1_price = (entry_price + t1_risk) if direction == "LONG" else (entry_price - t1_risk)
                    t2_price = (entry_price + 2 * t1_risk) if direction == "LONG" else (entry_price - 2 * t1_risk)
                    t3_price = None

                t1_setup = emit_t1_setup(
                    pattern_name, direction,
                    entry_price=entry_price, stop_price=stop_price,
                    t1_price=t1_price, t2_price=t2_price,
                    bar_index=self.buffer_size,
                    day_type=self.current_day_type,    # CHANGED: was self.opening_type
                    t3_price=t3_price,                  # NEW
                    current_price=entry_price,
                )
```

### 2.F · MODIFIED · `backend/v9/api/v9/shadow_routes.py`

Add a single endpoint exposing the NT skip counter for SHADOW analysis:

```python
@router.get("/api/v9/five_min/nt_skip_stats")
def get_nt_skip_stats(request: Request):
    """Return cumulative count of NT NO_TRADE skips (D-091.Q2 SHADOW counter)."""
    fm = getattr(request.app.state, "five_min_system", None)
    if fm is None:
        return {"available": False, "reason": "five_min_system not on app.state"}
    return {
        "available": True,
        "nt_skip_count": getattr(fm, "_nt_skip_count", 0),
        "current_day_type": getattr(fm, "current_day_type", None),
    }
```

Place near the existing system-health endpoints in `shadow_routes.py`. Use whatever the
established `request.app.state` attribute name is for the FiveMinSystem instance — verify
before writing.

### 2.G · NEW · `tests/v9/systems/test_day_type/test_day_type_targets.py`

Minimum 10 tests:

1. `test_returns_none_for_none_input` — `compute_targets_for_day_type(day_type=None, ...)` → None.
2. `test_returns_none_for_unknown_day_type` — `day_type="Banana"` → None.
3. `test_returns_none_for_zero_risk` — `entry=stop` → None (with warning).
4. `test_trend_normal_long_no_time_stop` — TN LONG, R=10, expect `time_stop_minutes=None · t1_price=entry+10 · t3_price=entry+40 (4R) · trail_after_t2=True · no_trade=False`.
5. `test_trend_dd_short_90min_time_stop` — TDD SHORT, R=8, expect `time_stop_minutes=90 · t1_price=entry-8 · t2_price=entry-20 (2.5R) · t3_price=entry-32 (4R)`.
6. `test_neutral_extreme_45min_no_t3` — NeuE, expect `time_stop_minutes=45 · t3_price=None · t2_price=None (anchor "extreme")`.
7. `test_neutral_center_30min` — NeuC, expect `time_stop_minutes=30 · t2_price=None · no_trade=False`.
8. `test_nontrend_no_trade_true` — NT, expect `no_trade=True · time_stop_minutes=None · sizing_contracts=0`.
9. `test_legacy_neutral_maps_to_neuc` — `day_type="Neutral"` → canonical resolves to `Neutral_Center`, time_stop=30min.
10. `test_short_direction_sign_correct` — TN SHORT, entry=4500 stop=4510, R=10, expect t1_price=4490 (entry - R).

### 2.H · NEW · `tests/v9/systems/test_five_min/test_five_min_day_type_wiring.py`

Minimum 8 tests covering the wiring changes in `five_min_system.py` + `setup_emitter.py`:

1. `test_current_day_type_starts_none` — `FiveMinSystem(...)`, no init, asserts `current_day_type is None`.
2. `test_on_day_type_update_sets_current_day_type` — feed an event `{"event_type": "day_type", "payload": {"day_type": "Trend_Normal"}}` → `current_day_type == "Trend_Normal"`.
3. `test_on_day_type_update_logs_transition` — sequential events TN → NT, assert 1 INFO log per transition.
4. `test_nt_skip_increments_counter` — set `current_day_type="Nontrend"`, call `process_bar(event)` 3×, assert `_nt_skip_count == 3`.
5. `test_nt_skip_rate_limited_log` — call `process_bar` 100× with `current_day_type="Nontrend"`, assert exactly 1 INFO log emitted (rate-limit 60s).
6. `test_emit_t1_setup_refuses_nontrend` — call `emit_t1_setup(..., day_type="Nontrend", ...)` directly, assert returns None + WARNING log.
7. `test_emit_t1_setup_includes_t3_price` — call with `t3_price=4525.0`, assert returned T1Setup has `t3_price == 4525.0`.
8. `test_emit_t1_setup_accepts_none_time_stop` — call with `day_type="Trend_Normal"` (time_stop_minutes=None per targets), assert T1Setup builds successfully with `time_stop_minutes=None`.

Plus regression sanity (existing tests must still pass):
- `tests/atomic/test_five_min_patterns.py` (the big 29-test suite from Pkg 2bc) — all green.
- `tests/v9/systems/test_five_min/` (full directory) — no new failures.

---

## §3 · API contract notes

### 3.1 · `T1Setup.time_stop_minutes: Optional[int]`

Downstream consumers (TradeManager, gateway) must handle `None`. Semantically:
- `int 1..180` → enforce time stop after that many minutes.
- `None` → no time stop OR day_type unknown. Caller decides default behavior. Per D-091.Q4,
  TradeManager just persists; enforcement is in Pkg 6.

### 3.2 · `T1Setup.t3_price: Optional[float]`

- `float > 0` → fire T3 target at that price.
- `None` → no T3 (NeuE/NeuC/Normal/NT) OR T3 is anchor-based (Trend_DD's "4R cap" should
  resolve to float when t3_r is numeric · but if any future targets use anchor strings like
  "open" they'd be None here for Layer 3 to resolve).

### 3.3 · `day_type_targets.compute_targets_for_day_type`

- Returns `None` for **any** unrecoverable input (unknown day_type, R≤0, day_type=None).
- Caller MUST short-circuit on None (skip setup or use defensive fallback).
- Anchor-based T2/T3 (literal strings "POC"/"extreme"/"open" in `targets_table`) currently
  return None for the price; Layer 3 cluster-based resolution is out of Stream 2 scope.

---

## §4 · Forbidden zone

The following must NOT change:

- **`_rescore_from_behavior` body** in `state_machine.py` — Stream 1.5 just shipped this.
- **`neutral_classifier.py`** — Stream 1.
- **`targets_table.py`** — Stream 1. `day_type_targets.py` is a NEW module that READS from it.
- **`schemas.py`** — Stream 1.
- **`api.py`** for day_type — Stream 1 + Stream 1 fix-up.
- **`adaptive_stop.py`** — Pkg 1.
- **Pkg 2bc-shipped files** (`five_min_system.py` constants 215-217 forbidden zone · the
  belly_dominance_ratio + lookback constants block at top of class). Verify byte-identical.
- **`manager.py`** in trade_manager — Pkg 6 will rewrite.
- **DB schema** (`v9_five_min_state` · `v9_day_type_state` · etc.) — no migrations.
- **`BarInput` / `DayTypeState` schemas** — no changes.

G3 will run `git diff 548f1f6 HEAD` and verify only the 6 files listed in §2 changed (plus
the 2 new modules + 2 new test files).

---

## §5 · Acceptance criteria (G3 will check ALL)

1. `pytest tests/v9/systems/test_day_type/test_day_type_targets.py -q` → 10/10 green.
2. `pytest tests/v9/systems/test_five_min/test_five_min_day_type_wiring.py -q` → 8/8 green.
3. `pytest tests/atomic/test_five_min_patterns.py -q` → 29/29 green (Pkg 2bc regression check).
4. `pytest tests/v9/systems/ -q` → ≥554 passed (was 554 after Stream 1.5 · +18 from §2.G+§2.H = 572 expected), 0 new failures.
5. `pytest tests/v9/systems/test_day_type/ -q` → all green (Streams 1 + 1.5 + 2 day_type tests · 33+9+10 = 52+).
6. `pytest backend/v9/tests/test_state_machine_v9.py backend/v9/tests/e2e/test_day_type_e2e.py -q` → all green.
7. Boot smoke: `python3 -c "from backend.main import app; print('OK')"` exits 0.
8. **Wired behavior smoke**:

   ```python
   from backend.v9.systems.day_type.day_type_targets import compute_targets_for_day_type
   r = compute_targets_for_day_type(day_type="Trend_Normal", entry_price=4500, stop_price=4490, direction="LONG")
   assert r["time_stop_minutes"] is None  # TN has no time stop
   assert r["t1_price"] == 4510            # 1R = 10
   assert r["t3_price"] == 4540            # 4R = 40
   assert r["no_trade"] is False
   r2 = compute_targets_for_day_type(day_type="Nontrend", entry_price=4500, stop_price=4490, direction="LONG")
   assert r2["no_trade"] is True
   assert r2["sizing_contracts"] == 0
   ```

9. **NT skip counter smoke**: After feeding 3 bars to a `FiveMinSystem` with `current_day_type="Nontrend"`, GET `/api/v9/five_min/nt_skip_stats` returns `{"available": True, "nt_skip_count": 3, "current_day_type": "Nontrend"}`.
10. `ReadLints` on all 6 modified/new files → 0 errors.
11. No `logger.debug` on failure paths in modified code.
12. T1Setup pydantic validation still passes for `time_stop_minutes=None` and `t3_price=None`.

---

## §6 · Constraints (mega-prompt MUST include)

- **No DB schema changes.** Use existing `v9_day_type_state` and `v9_five_min_state` tables read-only for hydrate.
- **No Pkg 6 work.** TradeManager stays untouched. T1Setup is the contract; persistence/enforcement of `time_stop_minutes` and `t3_price` is Pkg 6's job.
- **No D-091.Q2 enforcement on bypass paths.** The NT gate goes inside `_check_setup` (post-buffer-append) — bars are still buffered (for session context) but pattern detection is skipped. This matches Michael's locked decision.
- **Counter exposure via `request.app.state.five_min_system`.** Verify the actual attribute name before writing the route — it may be `five_min_system` or `_five_min_system` depending on wiring.
- **Rate-limited log** uses `time.monotonic()` and 60-second window. Exact pattern matches the existing precedents in the bridge code.
- **Defense in depth**: NT check exists in BOTH `_check_setup` (early-skip · CPU efficiency) AND `emit_t1_setup` (last-mile refuse · defense). Stream 1.5 +shipped the classification path; Stream 2 closes the consumption side.
- **No `DEFAULT_TIME_STOP = 60` constant.** Removed from `time_stop_mapper.py`. Any call site that imported it must be fixed (search before writing).
- **Inline imports** for `day_type_targets` and `targets_table` inside `five_min_system.py` and `setup_emitter.py` — same pattern as Stream 1 / Stream 1.5.

---

## §7 · Stop signals (CC must abort and ask Michael)

1. If `T1Setup` schema already has `t3_price` or already-optional `time_stop_minutes` (someone else shipped this).
2. If `FiveMinSystem` already has `self.current_day_type` attribute.
3. If `time_stop_mapper.py` already returns `Optional[int]`.
4. If `day_type_targets.py` already exists (duplicate work).
5. If `_on_day_type_update` already populates `current_day_type` (Stream 1.5 or other).
6. If a NT skip gate already exists in `_check_setup` or `process_bar`.
7. If the `v9_day_type_state` table schema has changed since Stream 1 (no `day_type` column or renamed).
8. If `request.app.state.five_min_system` attribute name is different (production code shows a different name) — adapt to that name, do not invent.
9. If any downstream caller of `emit_t1_setup` exists that breaks on `t3_price` kwarg (no Pydantic strict field) — investigate before changing the signature.
10. If `DEFAULT_TIME_STOP` constant is imported by ANY other module (would break on removal) — convert to `None` import or absorb the caller's defaults locally.

---

## §8 · Out of scope · explicitly deferred

- **Pkg 6 TradeManager enforcement** of `time_stop_minutes` and `t3_price`. Stream 2 is emit-only (D-091.Q4). TradeManager stays untouched.
- **Layer 3 cluster/empty-zone resolution** of anchor-based T2 (POC/extreme/open). Stream 2 leaves them as `None` in the target dict; emit_t1_setup falls back to R-multiples for T2 when `targets.t2_price is None`.
- **DB schema migration** to add `day_type` to `v9_five_min_state`. Stream 2 uses `v9_day_type_state` (which already has the column) for hydrate.
- **Frontend wiring** of `t3_price` in cockpit/snapshot UI. Backend contract change is sufficient; UI absorbs in a later pkg.
- **D-091.Q1 NT NO_TRADE** at the API level (rejecting trades from `/api/v9/trade/*` routes for NT days). Out of scope · Pkg 6 + Pkg 5 (gateway routing).
- **Pkg 3a Stream 3+** (trail logic + contract split per pattern) — Pkg 3b/3c work, separate handoff.

---

## §9 · Mega-prompt sanity checklist (for Claude Desktop)

Before generating the mega-prompt, Desktop must verify the handoff contains:

- [x] All 6 file paths + new module + 2 test file paths
- [x] Exact code snippets (not vague descriptions) for each edit
- [x] `Optional[int]` typing for `time_stop_minutes` everywhere downstream
- [x] D-091.Q2 NT skip gate + rate-limited log + counter, placed inside `_check_setup` (NOT `emit_t1_setup` only)
- [x] D-091.Q2 defense-in-depth in `emit_t1_setup` (returns None on no_trade=True)
- [x] Hydrate `current_day_type` from `v9_day_type_state` DB on startup
- [x] `_on_day_type_update` populates `current_day_type` from event payload
- [x] Replace `day_type=self.opening_type` with `day_type=self.current_day_type` at line 708 (THE bug)
- [x] Compute `t3_price` via `compute_targets_for_day_type`
- [x] `nt_skip_stats` endpoint reads from `request.app.state.five_min_system` (verify attr name)
- [x] Forbidden zones for state_machine.py / neutral_classifier.py / targets_table.py / schemas.py / api.py / adaptive_stop.py / manager.py / DB schema / Pkg 2bc constants
- [x] No silent fallbacks; explicit None propagation
- [x] Inline-import pattern (Stream 1 convention)
- [x] No `DEFAULT_TIME_STOP = 60` constant
- [x] 18 minimum tests with concrete numerics

---

## §10 · After exec

CC commits locally with message:

```
feat(s2): day-type targets module + T1Setup t3_price + NT NO_TRADE gate

- NEW backend/v9/systems/day_type/day_type_targets.py
  · compute_targets_for_day_type() resolves R-based targets to actual prices
  · Returns None on unknown/zero-R/no_trade · all 7 day types per D-091.Q1
- T1Setup schema: t3_price Optional[float] · time_stop_minutes Optional[int]
- time_stop_mapper: returns Optional[int] · removes silent 60min default
- setup_emitter: accepts t3_price kwarg · refuses NT setups (defense-in-depth)
- five_min_system:
  · current_day_type instance attr · _on_day_type_update wires it from events
  · hydrate from v9_day_type_state DB on startup
  · D-091.Q2 NT NO_TRADE early-skip in _check_setup + rate-limited log + counter
  · Fix line 708 bug: day_type=self.current_day_type (was self.opening_type)
  · Compute t3_price via day_type_targets module
- shadow_routes: /api/v9/five_min/nt_skip_stats endpoint exposes NT counter

Pkg 3a Stream 2 · D-091.Q1+Q2+Q4 · final stream of Pkg 3a (emit-only · Pkg 6 enforces).
```

Then Cursor G3 reviews per §5 acceptance criteria.

---

*Drafted by Cursor agent · 2026-05-23 21:42 IL · post-Stream-1.5 G3 PASS*
