# MEGA PROMPT · Package 3b · Stream 2 · TrailEngine + persistence

**Authority chain (read in order, do not paraphrase):**
1. `docs/decisions/D-094_PKG3B_TRAIL_DECISIONS.md` (LOCKED) — §3.A trail overrides · §3.B Layer 4 wiring order · §3.C 3-layer time stop · §3.D ATR caps · Gaps 1–15
2. `docs/handoff/DESKTOP_PKG3B_TRAIL_LOGIC_HANDOFF.md` §5 (TrailEngine + persistence reference design · revised below where reality differs from spec)
3. Constitution V3 PART 5 B11 (MFE peak tighten) + B12 (day_type_targets_verify) — out of scope for Stream 3b-2 (wired in Stream 3b-3)

**Predecessor commit (HEAD):** `6dfce93` · Pkg 3b Stream 1 (atr_caps.py + BE+1T fix + override hook · G3 PASS)

**Phase A flag (REQUIRED in commit message verbatim):**
`Phase A mechanical · DEMO+ parametric calibration deferred to post-SHADOW per D-094 §4`

**Estimated CC time:** ~3 hours · ~430 LOC + ~29 tests

**Revision v2 (2026-05-24 20:00 IL · refined 20:10 IL):** 6 fixes from Claude Desktop review applied —
(1) test #19 fixture replaced with type-coerce trigger (list(12345) raises);
(2) `_engage_chandelier` docstring documents ATR-dormant-on-early-T2 (intentional Phase A limitation);
(3) `_reconstruct_state_from_db` docstring documents dormant-chandelier-post-restart (intentional Phase A — chandelier_engaged stays True · t2_atr_at_engage stays None · HL/LH still operates · re-engagement REJECTED to avoid silent anchor retreat) + EXPLICIT Stream 3b-3 deferred-patch spec with `is not None` defensive check (preserves recovered max=0.0 edge case · Michael 20:10 IL);
(4) LOCK 2 step 1 — `quality["day_type"]` + `quality["pattern_name"]` writes moved OUT of `if _day_type and _pattern:` block (always written · may be None · TrailEngine handles None);
(5) tests #27/#28 renamed `end_to_end_*` → `integration_*` (TM is MagicMock · not true end-to-end);
(6) NEW test #29 — verify `release_fill_lock` resumes trail computation.

---

## §0 · Three Cursor-Michael LOCKS that revise §5 of the handoff

The original handoff §5 was written before Cursor audited the runtime
codebase. The locks below correct three mismatches and are AUTHORITATIVE
for Stream 3b-2.

### LOCK 1 · Bar-tick subscription (corrects §5.A line 484)

Original §5: `bar_router.subscribe("bar_5min_close", self.on_bar_close)`
**Reality:** the bar_type is `"5min"`, not `"bar_5min_close"`.

**LOCKED:** TrailEngine constructor MUST call:

```python
bar_router.subscribe("5min", self.on_bar_close)
```

`BarRouter` is at `backend/v9/services/bar_router.py`. Handler signature:

```python
async def on_bar_close(self, event: "BarEvent") -> None
```

`BarEvent` fields: `bar_type: str` · `bar_id: str` · `ts: str` (ISO) ·
`payload: Dict[str, Any]` · `session: str` · `mode: str`.
Bar fields are inside `event.payload` (dict with keys `o/h/l/c` or
`open/high/low/close` · `ts` · `vol`).

TrailEngine is NOT a `BaseSystem` subclass. It is a plain class that
subscribes via BarRouter.

### LOCK 2 · Trade-context storage (corrects §5.A lines 504–506, §5.E line 668)

Original §5: `trade.day_type` · `trade.pattern_name` · `trade.t2_filled_at`.
**Reality:** `V9Trade` (`backend/v9/db/models/trades.py`) does NOT have
columns `day_type`, `pattern_name`, or `t2_filled_at`. It HAS `t2_hit_ts`.

**LOCKED:**

1. `accept_setup` (already at `manager.py:154–164` post-Stream-3b-1)
   must be extended to ALSO write:
   ```python
   quality["day_type"] = _day_type        # may be None · TrailEngine handles
   quality["pattern_name"] = _pattern     # may be None · TrailEngine handles
   ```
   **Add these two lines BEFORE the existing `if _day_type and _pattern:`
   block** (not inside it). This guarantees the keys ALWAYS exist in
   `quality` (with None values for legacy trades without day_type/pattern
   metadata) · downstream consumers (TrailEngine + Pkg 6) can use
   `quality.get("day_type")` uniformly without "key present vs absent"
   ambiguity. The existing `if _day_type and _pattern:` block then
   resolves `trail_after_t2` + `t3_label` ONLY when both are present.
   Net: 2 lines added before the existing block.

2. TrailEngine reads from `trade.quality`:
   ```python
   day_type = (trade.quality or {}).get("day_type")
   pattern_name = (trade.quality or {}).get("pattern_name")
   ```

3. T2-hit detection uses the existing column:
   ```python
   def _is_past_t2(self, trade) -> bool:
       return trade.t2_hit_ts is not None
   ```

4. Trail-state recovery from DB uses `t2_hit_ts`:
   ```python
   t2_ts = trade.t2_hit_ts
   ```

NO schema migration. NO new columns on `v9_trades`.

### LOCK 3 · Sierra fill-lock (corrects §5.F)

Original §5: `trade.fill_lock = True` (column).
**Reality:** no such column.

**LOCKED:** in-memory `set[int]` on TradeManager:

```python
# In TradeManager.__init__: add this line
self._fill_locks: set[int] = set()

# Three new methods on TradeManager (instance level):
def acquire_fill_lock(self, trade_id: int) -> None:
    self._fill_locks.add(trade_id)

def release_fill_lock(self, trade_id: int) -> None:
    self._fill_locks.discard(trade_id)

def is_fill_locked(self, trade_id: int) -> bool:
    return trade_id in self._fill_locks
```

Locks are transient (not persisted). On TradeManager restart the set is
empty — this is by design (no stale locks).

---

## §1 · SCOPE

### WRITE NEW (2 files)

| Path | LOC | Purpose |
|------|-----|---------|
| `backend/v9/services/trail_engine.py` | ~330 | TrailEngine class + TrailState dataclass + helpers |
| `tests/v9/services/test_trail_engine.py` | ~545 | 29 golden tests |

### MODIFY EXISTING (2 files · surgical)

| Path | Edit | Lines added |
|------|------|-------------|
| `backend/v9/services/trade_manager/manager.py` | Extend `accept_setup` to write `quality["day_type"]` + `quality["pattern_name"]` · Add `_fill_locks` to `__init__` · Add 3 fill-lock methods · Add `list_trades_past_t1(mode=None)` helper · Add `update_stop_with_audit(trade_id, new_stop, reason, bar_ts)` helper | ~50 |
| `backend/v9/db/models/trades.py` | **NO CHANGES** — forbidden per LOCK 2 | 0 |

### FORBIDDEN (do NOT touch)

- ❌ `backend/v9/systems/five_min/adaptive_stop.py` (Pkg 1 · ATR_MULTIPLIERS untouchable per D-094 §3.D Option 3)
- ❌ `backend/v9/systems/five_min/atr_caps.py` (Pkg 3b-1 · already shipped)
- ❌ `backend/v9/systems/five_min/constants.py` (Pkg 3b-1 · already shipped)
- ❌ `backend/v9/systems/day_type/targets_table.py` (Pkg 3a · Pkg 3b-1 · do NOT regress)
- ❌ Any DB migration · any change to `v9_trades` table
- ❌ Any Layer 4 service in `backend/v9/services/layer4/` (deferred to Stream 3b-3)
- ❌ `frontend/` · `sc_study/` · `bridge/` · any DLL
- ❌ Any change to `EventDispatcher` (TrailEngine uses BarRouter, not dispatcher)
- ❌ Any test in `tests/v9/api/`, `tests/v9/bridge/`, `tests/v9/gateway/`, `tests/v9/frontend/`

---

## §2 · `backend/v9/services/trail_engine.py` — full inline spec

CC MUST produce this file as-is, with the exact module docstring, imports,
TrailState dataclass, and TrailEngine class. Helper method bodies are
provided. Do not rename anything.

```python
"""TrailEngine · post-T2 trade management subscriber (D-094 Gap 9).

Pkg 3b Stream 2 · written 2026-05-24 · Phase A mechanical.

Lifecycle per bar close:
  1. BarRouter publishes "5min" event after each 5-min bar finalizes.
  2. TrailEngine.on_bar_close(event) iterates all past-T1 open trades.
  3. For each trade (independent failure isolation · one trade's exception
     does NOT stop processing of others):
     a) Layer 3 backstop FIRST (cheapest fail-fast): time_stop check via
        min(day_axis, pattern_axis) per D-094 §3.C. If elapsed >= limit:
        close trade with reason="TIME_STOP_HIT" and return.
     b) Layer 2 post-T2 trail: only if `trade.t2_hit_ts is not None`.
        - On first past-T2 bar: engage chandelier (freeze ATR per Gap 5).
        - HL/LH trail: 5-bar lookback. LONG: min of last 5 lows. SHORT:
          max of last 5 highs.
        - Chandelier trail: max_high_since_t2 - mult * frozen_ATR (LONG)
          or min_low_since_t2 + mult * frozen_ATR (SHORT).
        - Apply tighter of the two via `_move_stop_tighter_only` (Gap 13).
     c) Persist updated state to `trade.quality["trail_state"]` per Gap 10.

Sierra tick fills ALWAYS win over computed trail (Gap 15 + Guardrail M13).
On every `_move_stop_tighter_only` call, check `tm.is_fill_locked(trade.id)`.
If locked: log to cross_context as "trail_compute_discarded_sierra_fill"
and return without mutating stop.

All cross_context appends use `json.dumps(entry, default=str)` to validate
serializability per Gap 11. Non-serializable payloads raise during append,
NOT at DB commit (fail loud, fail early).

Restart recovery (Gap 14):
- `_load_state` reads `trade.quality["trail_state"]` if present.
- If absent or corrupt: `_reconstruct_state_from_db` queries v9_bars_5min
  since `trade.t2_hit_ts` to rebuild max_high/min_low + last_5_lows/highs.
  ATR is NOT recoverable from bars alone; `t2_atr_at_engage` stays None
  and chandelier is inactive until the next live bar provides fresh ATR
  (the audit log notes this state).
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional

from backend.v9.systems.five_min.atr_caps import (
    ATR_MULTIPLIERS,
    _pattern_to_family,
    compute_continuous_atr14,
    compute_time_stop_minutes,
)
from backend.v9.systems.day_type.targets_table import _TARGETS as TARGETS_DICT

logger = logging.getLogger(__name__)


@dataclass
class TrailState:
    """Persistable trail state (Gap 10 · JSON-serializable round-trip)."""

    max_high_since_t2: Optional[float] = None       # LONG chandelier anchor
    min_low_since_t2: Optional[float] = None        # SHORT chandelier anchor
    last_5_lows: List[float] = field(default_factory=list)   # LONG HL trail window
    last_5_highs: List[float] = field(default_factory=list)  # SHORT LH trail window
    chandelier_engaged: bool = False
    t2_bar_ts: Optional[str] = None                 # ISO timestamp of T2-engage bar
    t2_atr_at_engage: Optional[float] = None        # frozen Wilder ATR-14 (Gap 5)

    def to_dict(self) -> dict:
        return {
            "max_high_since_t2": self.max_high_since_t2,
            "min_low_since_t2": self.min_low_since_t2,
            "last_5_lows": list(self.last_5_lows),
            "last_5_highs": list(self.last_5_highs),
            "chandelier_engaged": self.chandelier_engaged,
            "t2_bar_ts": self.t2_bar_ts,
            "t2_atr_at_engage": self.t2_atr_at_engage,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TrailState":
        return cls(
            max_high_since_t2=data.get("max_high_since_t2"),
            min_low_since_t2=data.get("min_low_since_t2"),
            last_5_lows=list(data.get("last_5_lows") or []),
            last_5_highs=list(data.get("last_5_highs") or []),
            chandelier_engaged=bool(data.get("chandelier_engaged", False)),
            t2_bar_ts=data.get("t2_bar_ts"),
            t2_atr_at_engage=data.get("t2_atr_at_engage"),
        )


class TrailEngine:
    """Post-T2 trade management orchestrator (D-094 Gap 9 · SRP boundary).

    Subscribes to BarRouter "5min" events. For each open past-T1 trade,
    applies 3-layer logic per D-094 §3.C. Mutates trades exclusively
    through `tm.update_stop_with_audit` and `tm.close_trade`. Never
    bypasses TradeManager for persistence.

    Args:
        trade_manager: TradeManager instance (provides list/update/close + fill-lock check).
        bar_router: BarRouter to subscribe to "5min" bar-close events.
        fetch_bars: callable (start_iso: str, end_iso: str) -> List[bar_like]
                    used by chandelier engage to compute Wilder ATR-14.
                    A "bar_like" is any object with .high/.low/.close attrs
                    OR a dict with high/low/close keys (compute_continuous_atr14
                    handles both shapes).
        fetch_bars_since: callable (trade_id, since_ts_iso) -> List[bar_like]
                          for restart-recovery reconstruct path.
    """

    def __init__(
        self,
        trade_manager,
        bar_router,
        fetch_bars: Callable[[str, str], List[Any]],
        fetch_bars_since: Callable[[int, str], List[Any]],
    ) -> None:
        self.tm = trade_manager
        self.bar_router = bar_router
        self._fetch_bars = fetch_bars
        self._fetch_bars_since = fetch_bars_since
        bar_router.subscribe("5min", self.on_bar_close)
        logger.info("[TrailEngine] subscribed to bar_router '5min'")

    async def on_bar_close(self, event) -> None:
        """Main entry point · called by BarRouter for each 5-min close.

        BarEvent fields used: event.ts (ISO str) · event.payload (bar dict).
        Bar payload keys: 'h' or 'high' · 'l' or 'low' · 'c' or 'close' · 'ts'.
        """
        bar = self._normalize_bar(event)
        try:
            trades = self.tm.list_trades_past_t1()
        except Exception:
            logger.exception("[TrailEngine] list_trades_past_t1 failed")
            return

        for trade in trades:
            try:
                self._process_trade(trade, bar)
            except Exception as exc:
                logger.warning(
                    "[TrailEngine] _process_trade failed for trade %s: %r",
                    getattr(trade, "id", "?"), exc,
                )
                self._log_audit(trade, "trail_engine_error", {
                    "exc": repr(exc),
                    "bar_ts": str(bar.get("ts")),
                })

    @staticmethod
    def _normalize_bar(event) -> dict:
        """Coerce a BarEvent into a plain dict with high/low/close/ts keys."""
        payload = dict(event.payload) if isinstance(event.payload, dict) else {}
        return {
            "ts": payload.get("ts") or event.ts,
            "high": payload.get("high", payload.get("h")),
            "low": payload.get("low", payload.get("l")),
            "close": payload.get("close", payload.get("c")),
            "open": payload.get("open", payload.get("o")),
        }

    def _process_trade(self, trade, bar: dict) -> None:
        """Apply 3-layer logic for one trade on one bar close."""
        state = self._load_state(trade)

        # === Layer 3 backstop FIRST (cheapest check · fails fast per D-094 §3.C) ===
        day_type = (trade.quality or {}).get("day_type")
        pattern_name = (trade.quality or {}).get("pattern_name") or ""
        family = _pattern_to_family(pattern_name)
        time_stop_min = compute_time_stop_minutes(
            day_type=day_type or "",
            pattern_family=family,
            targets_table=TARGETS_DICT,
        )
        if time_stop_min is not None and trade.entry_ts is not None:
            elapsed_min = self._elapsed_minutes(trade.entry_ts, bar["ts"])
            if elapsed_min is not None and elapsed_min >= time_stop_min:
                self._close_trade(trade, bar, reason="TIME_STOP_HIT", state=state)
                return

        # === Layer 2: post-T2 trail (HL/LH + chandelier) ===
        if state.chandelier_engaged or self._is_past_t2(trade):
            if not state.chandelier_engaged:
                self._engage_chandelier(trade, bar, state)
            self._apply_hl_lh_trail(trade, bar, state)
            self._apply_chandelier_trail(trade, bar, state)

        self._save_state(trade, state)

    def _is_past_t2(self, trade) -> bool:
        return trade.t2_hit_ts is not None

    @staticmethod
    def _elapsed_minutes(entry_ts, bar_ts) -> Optional[float]:
        """Return minutes elapsed from entry_ts (datetime) to bar_ts (ISO str)."""
        from datetime import datetime
        try:
            if isinstance(bar_ts, str):
                bar_dt = datetime.fromisoformat(bar_ts.replace("Z", "+00:00"))
            else:
                bar_dt = bar_ts
            entry_dt = entry_ts if hasattr(entry_ts, "tzinfo") else None
            if entry_dt is None:
                return None
            # Normalize tz so subtract works
            if bar_dt.tzinfo is None and entry_dt.tzinfo is not None:
                bar_dt = bar_dt.replace(tzinfo=entry_dt.tzinfo)
            return (bar_dt - entry_dt).total_seconds() / 60.0
        except Exception:
            return None

    def _engage_chandelier(self, trade, bar: dict, state: TrailState) -> None:
        """First-time engagement at past-T2 bar · freezes Wilder ATR per Gap 5.

        LIMITATION (intentional Phase A · NOT a bug):
        If T2 hits early in the session (e.g., 10:00 ET · only 0-10 bars exist
        since session open), `_fetch_bars_since(trade.id, t2_hit_ts)` returns
        <14 bars. `compute_continuous_atr14` requires >=14 bars and returns
        None when n<14. Therefore `state.t2_atr_at_engage = None` and the
        chandelier remains DORMANT for this trade for its entire lifetime
        (post-T2). HL/LH 5-bar trail still operates normally.
        Yesterday-bar tail support is deferred to Stream 3b-3 per D-094 §3.D.
        Do NOT add fallback ATR sources (e.g., yesterday_bars from DB) in
        Stream 3b-2 — out of scope.
        """
        direction = (trade.direction or "").upper()
        state.chandelier_engaged = True
        state.t2_bar_ts = str(bar["ts"])
        if direction == "LONG":
            state.max_high_since_t2 = float(bar["high"])
        elif direction == "SHORT":
            state.min_low_since_t2 = float(bar["low"])

        # Freeze ATR at engage (Gap 5 · do NOT recompute on subsequent bars)
        try:
            today_bars = self._fetch_bars_since(trade.id, str(trade.t2_hit_ts))
            yesterday_bars: List[Any] = []  # Stream 3b-2 scope · 3b-3 adds tail
            # If today_bars >= 14 → ATR computed. If today_bars < 14 →
            # compute_continuous_atr14 returns None → chandelier dormant
            # for the lifetime of this trade (HL/LH still operates).
            state.t2_atr_at_engage = compute_continuous_atr14(
                yesterday_bars, today_bars,
            )
        except Exception as exc:
            logger.warning(
                "[TrailEngine] ATR freeze failed for trade %s: %r",
                getattr(trade, "id", "?"), exc,
            )
            state.t2_atr_at_engage = None

        self._log_audit(trade, "chandelier_engaged", {
            "bar_ts": str(bar["ts"]),
            "frozen_atr": state.t2_atr_at_engage,
            "direction": direction,
        })

    def _apply_hl_lh_trail(self, trade, bar: dict, state: TrailState) -> None:
        """5-bar HL (LONG) / LH (SHORT) trail · D-094 Gap 2 · tighten only."""
        direction = (trade.direction or "").upper()
        if direction == "LONG":
            window = (state.last_5_lows + [float(bar["low"])])[-5:]
            state.last_5_lows = window
            if len(window) >= 5:
                self._move_stop_tighter_only(
                    trade, min(window), reason="HL_TRAIL", bar=bar,
                )
        elif direction == "SHORT":
            window = (state.last_5_highs + [float(bar["high"])])[-5:]
            state.last_5_highs = window
            if len(window) >= 5:
                self._move_stop_tighter_only(
                    trade, max(window), reason="LH_TRAIL", bar=bar,
                )

    def _apply_chandelier_trail(self, trade, bar: dict, state: TrailState) -> None:
        """Chandelier from peak ± multiplier × frozen ATR · D-094 Gap 3 + §3.D."""
        if state.t2_atr_at_engage is None:
            return  # ATR data was insufficient at engage · chandelier dormant

        pattern_name = (trade.quality or {}).get("pattern_name") or ""
        family = _pattern_to_family(pattern_name)
        if family is None:
            return
        multiplier = ATR_MULTIPLIERS.get(family)
        if multiplier is None:
            return

        direction = (trade.direction or "").upper()
        if direction == "LONG":
            cur = state.max_high_since_t2 if state.max_high_since_t2 is not None else float(bar["high"])
            state.max_high_since_t2 = max(cur, float(bar["high"]))
            chandelier = state.max_high_since_t2 - multiplier * state.t2_atr_at_engage
            self._move_stop_tighter_only(
                trade, chandelier, reason="CHANDELIER_TRAIL", bar=bar,
            )
        elif direction == "SHORT":
            cur = state.min_low_since_t2 if state.min_low_since_t2 is not None else float(bar["low"])
            state.min_low_since_t2 = min(cur, float(bar["low"]))
            chandelier = state.min_low_since_t2 + multiplier * state.t2_atr_at_engage
            self._move_stop_tighter_only(
                trade, chandelier, reason="CHANDELIER_TRAIL", bar=bar,
            )

    def _move_stop_tighter_only(
        self, trade, candidate: float, *, reason: str, bar: dict,
    ) -> None:
        """Never widen · check Sierra fill lock · audit cross_context (Gaps 11+13+15)."""
        if self.tm.is_fill_locked(trade.id):
            self._log_audit(trade, "trail_compute_discarded_sierra_fill", {
                "candidate": float(candidate), "reason": reason,
                "bar_ts": str(bar["ts"]),
            })
            return
        current = trade.stop
        if current is None:
            self._log_audit(trade, "trail_no_prior_stop", {"reason": reason})
            return
        direction = (trade.direction or "").upper()
        if direction == "LONG" and candidate <= float(current):
            return
        if direction == "SHORT" and candidate >= float(current):
            return
        # Tighten via TradeManager helper (which appends audit and persists)
        self.tm.update_stop_with_audit(
            trade_id=trade.id,
            new_stop=float(candidate),
            reason=reason,
            bar_ts=str(bar["ts"]),
        )

    def _close_trade(self, trade, bar: dict, *, reason: str, state: TrailState) -> None:
        """Close trade via TradeManager and persist state one last time."""
        self._log_audit(trade, "trail_close", {
            "reason": reason, "bar_ts": str(bar["ts"]),
        })
        self._save_state(trade, state)
        self.tm.close_trade(trade.id, reason)

    def _log_audit(self, trade, event: str, payload: dict) -> None:
        """Append to cross_context with json.dumps default=str (Gap 11)."""
        entry = {"event": event, **payload}
        json.dumps(entry, default=str)  # validates serializability now
        ctx = list(trade.cross_context) if isinstance(trade.cross_context, list) else []
        ctx.append(entry)
        trade.cross_context = ctx

    def _save_state(self, trade, state: TrailState) -> None:
        """Persist trail state to trade.quality['trail_state'] (Gap 10)."""
        q = dict(trade.quality) if isinstance(trade.quality, dict) else {}
        q["trail_state"] = state.to_dict()
        trade.quality = q

    def _load_state(self, trade) -> TrailState:
        """Restore from trade.quality, with DB-reconstruct fallback (Gap 14)."""
        data = (trade.quality or {}).get("trail_state")
        if data is None:
            return TrailState()
        try:
            return TrailState.from_dict(data)
        except Exception as exc:
            self._log_audit(trade, "trail_state_load_failed", {"exc": repr(exc)})
            return self._reconstruct_state_from_db(trade)

    def _reconstruct_state_from_db(self, trade) -> TrailState:
        """Rebuild from v9_bars_5min since t2_hit_ts (Gap 14 fallback).

        LIMITATION (intentional Phase A · NOT a bug):
        ATR is NOT recoverable from bars alone (Wilder ATR requires running
        the recursive formula from a known seed · the seed is lost on restart).
        We deliberately keep `state.chandelier_engaged = True` AND
        `state.t2_atr_at_engage = None`. Result:
          - `_apply_chandelier_trail` returns early (line: `if state.t2_atr_at_engage is None: return`)
          - chandelier remains DORMANT for the lifetime of this trade
          - HL/LH 5-bar trail still operates normally
          - max_high_since_t2 / min_low_since_t2 ARE recovered correctly from
            bars (used by HL/LH; not consumed by chandelier when ATR=None)

        REJECTED ALTERNATIVE: setting `chandelier_engaged = False` here so
        `_engage_chandelier` runs on the next bar to acquire a fresh ATR
        WOULD WORK for ATR · but `_engage_chandelier` line 368 OVERWRITES
        `state.max_high_since_t2 = float(bar["high"])`, which DISCARDS the
        recovered max and effectively RETREATS the chandelier anchor. That
        causes a silent stop-loosening after restart — unacceptable for
        Phase A.

        DEFERRED TO STREAM 3b-3 (not Stream 3b-2 scope):
        Patch `_engage_chandelier` to preserve recovered max on restart
        re-engage. Use `is not None` (NOT `or`) so a recovered value of
        0.0 is preserved (defensive · MES never trades at 0 but
        type-checked code does not assume that):

            recovered_max = state.max_high_since_t2
            new_high = float(bar["high"])
            if recovered_max is not None:
                state.max_high_since_t2 = max(recovered_max, new_high)
            else:
                state.max_high_since_t2 = new_high

        (symmetric `min(recovered_min, new_low)` for SHORT direction).

        With that patch in place, Stream 3b-2's reconstruct can be changed
        to set `chandelier_engaged = False` so re-engage acquires fresh
        ATR while preserving the peak anchor — fully functional chandelier
        after restart. Trigger for activation: post-SHADOW observation
        that dormant-chandelier-after-restart materially affects trade
        outcomes (e.g., trades that restart >=N% of the time AND show
        worse exit-quality than non-restart trades).
        """
        state = TrailState()
        if trade.t2_hit_ts is None:
            return state
        try:
            bars = self._fetch_bars_since(trade.id, str(trade.t2_hit_ts))
        except Exception:
            return state
        state.t2_bar_ts = str(trade.t2_hit_ts)
        state.chandelier_engaged = True  # Phase A · accept dormant chandelier
        direction = (trade.direction or "").upper()
        if direction == "LONG":
            highs = [self._bar_attr(b, "high") for b in bars]
            lows = [self._bar_attr(b, "low") for b in bars]
            state.max_high_since_t2 = max(highs) if highs else None
            state.last_5_lows = [l for l in lows[-5:] if l is not None]
        else:
            highs = [self._bar_attr(b, "high") for b in bars]
            lows = [self._bar_attr(b, "low") for b in bars]
            state.min_low_since_t2 = min(lows) if lows else None
            state.last_5_highs = [h for h in highs[-5:] if h is not None]
        # ATR seed lost · chandelier dormant for this trade · HL/LH continues
        return state

    @staticmethod
    def _bar_attr(bar: Any, key: str) -> Optional[float]:
        """Read high/low/close from either attribute or dict shape."""
        if hasattr(bar, key):
            v = getattr(bar, key)
            return float(v) if v is not None else None
        if isinstance(bar, dict):
            v = bar.get(key, bar.get(key[0]))
            return float(v) if v is not None else None
        return None
```

---

## §3 · TradeManager surgical additions

**File:** `backend/v9/services/trade_manager/manager.py`

### Edit 1 · `__init__` add `_fill_locks` (1 line)

Find the existing `__init__` method. After the existing instance-attribute
assignments, add:

```python
self._fill_locks: set[int] = set()
```

### Edit 2 · `accept_setup` trail-config block — extend with 2 lines BEFORE the if-block

Locate the existing block at approximately lines 154–164:

```python
# D-094 §3.A · capture resolved trail config (overrides + base)
_day_type = meta.get("day_type")
_pattern = meta.get("pattern") or classification
if _day_type and _pattern:
    try:
        from backend.v9.systems.day_type.targets_table import resolve_trail_config
        cfg = resolve_trail_config(_day_type, _pattern)
        quality["trail_after_t2"] = cfg.get("trail_after_t2", False)
        quality["t3_label"] = cfg.get("t3")
    except Exception:
        pass  # trail config resolution is advisory — do not block trade creation
```

Add 2 lines BEFORE the `if` block (not inside it · per LOCK 2 step 1):

```python
# D-094 §3.A · capture resolved trail config (overrides + base)
_day_type = meta.get("day_type")
_pattern = meta.get("pattern") or classification
# Pkg 3b Stream 2 · always write keys (may be None for legacy trades)
quality["day_type"] = _day_type
quality["pattern_name"] = _pattern
if _day_type and _pattern:
    try:
        from backend.v9.systems.day_type.targets_table import resolve_trail_config
        cfg = resolve_trail_config(_day_type, _pattern)
        quality["trail_after_t2"] = cfg.get("trail_after_t2", False)
        quality["t3_label"] = cfg.get("t3")
    except Exception:
        pass  # trail config resolution is advisory — do not block trade creation
```

**Rationale:** TrailEngine reads `(trade.quality or {}).get("day_type")`
which returns `None` either way · but writing the keys unconditionally
removes "key present vs absent" ambiguity for downstream consumers
(Pkg 6 may use `"day_type" in quality` as a guard).

### Edit 3 · NEW public methods on `TradeManager` (~40 LOC)

Append AFTER `get_active_trades` (line 390) and BEFORE the `# ── internal
helpers ──` divider (line 392):

```python
    # ── trail-engine API (D-094 Gap 9 · Pkg 3b Stream 2) ───────────

    def list_trades_past_t1(self, mode: Optional[str] = None) -> List[V9Trade]:
        """All non-CLOSED trades that have hit T1 (state == PARTIAL).

        Used by TrailEngine to iterate trades that need trail management.
        Idempotency: pre-T1 trades are skipped here, post-T1 trades hit BE+1T
        already via _apply_smart_be_after_t1 (so BE+1T is not re-applied).
        """
        try:
            self._db.expire_all()
        except Exception:
            pass
        query = self._db.query(V9Trade).filter(
            V9Trade.state == TradeState.PARTIAL.value,
            V9Trade.t1_hit_ts.isnot(None),
        )
        if mode is not None:
            query = query.filter(V9Trade.mode == mode)
        return query.all()

    def update_stop_with_audit(
        self,
        trade_id: int,
        new_stop: float,
        reason: str,
        bar_ts: str,
    ) -> None:
        """Move stop with cross_context audit append (D-094 Gap 11).

        Never widens — caller (TrailEngine) is responsible for the
        direction check. This helper writes the move atomically:
        cross_context.append({event,from,to,reason,bar_ts}) + trade.stop = new_stop
        + db.flush(). SQLAlchemy dirty-tracking via list reassignment.
        """
        trade = self._get_trade(trade_id)
        if trade is None:
            logger.warning(
                "[TradeManager] update_stop_with_audit trade %s not found",
                trade_id,
            )
            return
        stop_before = float(trade.stop) if trade.stop is not None else None
        entry = {
            "event": "stop_move",
            "from": stop_before,
            "to": float(new_stop),
            "reason": reason,
            "bar_ts": bar_ts,
        }
        ctx = list(trade.cross_context) if isinstance(trade.cross_context, list) else []
        ctx.append(entry)
        trade.cross_context = ctx
        trade.stop = float(new_stop)
        self._db.flush()
        logger.info(
            "[TradeManager] trail stop move: trade %s %.2f -> %.2f (%s)",
            trade_id, stop_before if stop_before else 0.0, new_stop, reason,
        )

    def acquire_fill_lock(self, trade_id: int) -> None:
        """Mark trade as receiving a Sierra fill — TrailEngine will skip."""
        self._fill_locks.add(trade_id)

    def release_fill_lock(self, trade_id: int) -> None:
        """Release lock after Sierra fill processed."""
        self._fill_locks.discard(trade_id)

    def is_fill_locked(self, trade_id: int) -> bool:
        """Query lock state (TrailEngine concurrency guard)."""
        return trade_id in self._fill_locks
```

That's the ENTIRE manager.py change. Approximately 50 lines added · zero
removed · zero other methods touched.

---

## §4 · Golden tests (29 · `tests/v9/services/test_trail_engine.py`)

CC must produce exactly these test cases. Use pytest fixtures and the
existing TradeManager fixture pattern from `tests/v9/services/test_trade_manager.py`.

### Test infrastructure (~50 LOC)

```python
import json
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from backend.v9.services.trail_engine import TrailEngine, TrailState


@pytest.fixture
def fake_bar_router():
    router = MagicMock()
    router.subscribe = MagicMock()
    return router


@pytest.fixture
def fake_trade_manager():
    tm = MagicMock()
    tm._fill_locks = set()
    tm.is_fill_locked = lambda tid: tid in tm._fill_locks
    tm.acquire_fill_lock = lambda tid: tm._fill_locks.add(tid)
    tm.release_fill_lock = lambda tid: tm._fill_locks.discard(tid)
    return tm


@pytest.fixture
def fetch_bars_empty():
    return lambda s, e: []


@pytest.fixture
def fetch_bars_since_empty():
    return lambda tid, since: []


def _make_trade(
    *, id=1, direction="LONG", entry_price=4500.0, stop=4490.0,
    t1=4505.0, t2=4515.0, t3=None, t1_hit_ts=None, t2_hit_ts=None,
    state="PARTIAL", day_type="Trend_Normal", pattern_name="REACTIVE",
    quality=None, cross_context=None, entry_ts=None,
):
    trade = MagicMock()
    trade.id = id
    trade.direction = direction
    trade.entry_price = entry_price
    trade.stop = stop
    trade.t1 = t1
    trade.t2 = t2
    trade.t3 = t3
    trade.t1_hit_ts = t1_hit_ts
    trade.t2_hit_ts = t2_hit_ts
    trade.state = state
    trade.entry_ts = entry_ts or datetime(2026, 5, 24, 14, 30, tzinfo=timezone.utc)
    q = quality if quality is not None else {
        "day_type": day_type, "pattern_name": pattern_name,
    }
    trade.quality = q
    trade.cross_context = cross_context if cross_context is not None else []
    return trade


def _make_event(*, high, low, close, ts="2026-05-24T15:00:00+00:00"):
    ev = MagicMock()
    ev.ts = ts
    ev.payload = {"high": high, "low": low, "close": close, "ts": ts}
    return ev
```

### HL/LH trail (6 tests)

1. **`test_hl_trail_long_5_bar_low_tightens_stop`** —
   trade LONG, entry=4500, stop=4490, t2_hit, state already engaged with
   `last_5_lows=[4500, 4498, 4496, 4495, 4497]`. New bar low=4499.
   Expect: window becomes [4498,4496,4495,4497,4499], min=4495,
   `tm.update_stop_with_audit` called with new_stop=4495.0, reason="HL_TRAIL".

2. **`test_hl_trail_long_never_widens`** — same trade but stop already at
   4496. window min=4495 < current 4496. Expect: `update_stop_with_audit`
   NOT called.

3. **`test_hl_trail_short_5_bar_high_tightens_stop`** —
   trade SHORT, entry=4500, stop=4510, last_5_highs=[4502,4504,4506,4505,4503].
   New bar high=4501. Expect: window becomes [4504,4506,4505,4503,4501],
   max=4506, `update_stop_with_audit(new_stop=4506.0, reason="LH_TRAIL")`.

4. **`test_hl_trail_short_never_widens`** — same SHORT trade but stop at
   4505 (already tighter than max=4506). Expect: NOT called.

5. **`test_hl_trail_needs_5_bars_before_firing`** —
   trade LONG, state.last_5_lows=[4498,4496,4495] (only 3 bars). New bar
   low=4497. Expect: window grows to [4498,4496,4495,4497] (4 entries) ·
   `update_stop_with_audit` NOT called (len<5).

6. **`test_hl_trail_sliding_window_drops_oldest`** —
   trade LONG, state.last_5_lows=[4490,4495,4498,4496,4497]. New bar
   low=4499. Expect: window becomes [4495,4498,4496,4497,4499] (oldest
   4490 dropped). min=4495, stop moves to 4495.

### Chandelier (6 tests)

7. **`test_chandelier_engages_at_t2`** — trade LONG just hit T2 (t2_hit_ts
   set, state not engaged in quality). On first bar after T2, expect:
   `_engage_chandelier` runs, state.chandelier_engaged=True,
   state.max_high_since_t2 set to bar.high, state.t2_bar_ts set to bar.ts ISO,
   one cross_context entry with event="chandelier_engaged".

8. **`test_chandelier_atr_frozen_at_engage`** — call `_engage_chandelier`
   with a fetch_bars_since returning 14 dummy bars (high=4500 each,
   low=4498 each, close=4499 each). Expect: state.t2_atr_at_engage is
   a non-None float; call `_engage_chandelier` again with different bars
   on a subsequent call (simulate next bar) — `t2_atr_at_engage` does NOT
   change (frozen).

9. **`test_chandelier_long_uses_max_high_minus_multiplier_atr`** —
   trade LONG, pattern="REACTIVE" (family=OFA_Reactive, mult=1.5),
   state.t2_atr_at_engage=2.0, state.max_high_since_t2=4520.
   Stop currently at 4500. Bar high=4521 (extends max to 4521).
   Expect: chandelier = 4521 - 1.5*2.0 = 4518.0 ·
   `update_stop_with_audit(new_stop=4518.0, reason="CHANDELIER_TRAIL")`.

10. **`test_chandelier_short_uses_min_low_plus_multiplier_atr`** —
    trade SHORT, pattern="INITIATIVE" (family=OFA_Initiative, mult=2.0),
    state.t2_atr_at_engage=2.5, state.min_low_since_t2=4480.
    Stop at 4510. Bar low=4479 (extends min to 4479).
    Expect: chandelier = 4479 + 2.0*2.5 = 4484.0 ·
    `update_stop_with_audit(new_stop=4484.0, reason="CHANDELIER_TRAIL")`.

11. **`test_chandelier_never_widens`** — trade LONG, state.max_high=4520,
    ATR=2.0, mult=1.5. Bar high=4515 (lower than max). max stays 4520.
    Chandelier candidate=4517. Stop already at 4518. 4517 < 4518 → no move.

12. **`test_chandelier_skips_if_no_atr_data`** — `state.t2_atr_at_engage=None`.
    Bar high=4521. Expect: `_apply_chandelier_trail` returns early without
    calling `update_stop_with_audit`.

### Time stop / Layer 3 (4 tests)

13. **`test_time_stop_fires_when_elapsed`** — trade entered at
    `2026-05-24T14:30Z` with day_type="Trend_Normal" (assume 90min stop
    per current TARGETS), pattern_name="REACTIVE" (OFA_Reactive, 30min).
    Bar at `2026-05-24T15:05Z` (35 min elapsed). min(90,30)=30 ≤ 35 →
    expect `tm.close_trade(trade.id, "TIME_STOP_HIT")` called.

14. **`test_time_stop_uses_min_day_pattern`** — day_axis=30, pattern_axis=20.
    elapsed=25 min. min=20 → fires. Expect close.

15. **`test_time_stop_no_close_when_both_none`** —
    day_type="Unknown_Type" (not in TARGETS), pattern_name=""
    (no family resolution). compute_time_stop_minutes returns None.
    Expect: `close_trade` NOT called regardless of elapsed.

16. **`test_time_stop_exit_reason_time_stop_hit`** — when time stop fires,
    `close_trade` is called with second arg == "TIME_STOP_HIT" exactly.

### State persistence + restart (5 tests)

17. **`test_save_state_persists_to_quality`** — TrailEngine `_save_state`
    with state.max_high_since_t2=4520, state.last_5_lows=[4490,...].
    Expect `trade.quality["trail_state"]["max_high_since_t2"] == 4520` and
    `trade.quality["trail_state"]["last_5_lows"] == [4490,...]`.

18. **`test_load_state_restores_from_quality`** — set
    `trade.quality = {"trail_state": {"max_high_since_t2": 4520, ...}}`.
    Call `_load_state(trade)` → expect returned state has
    max_high_since_t2 == 4520.

19. **`test_load_state_corrupt_falls_back_to_db_reconstruct`** —
    Set `trade.quality = {"trail_state": {"last_5_lows": 12345}}` (a non-iterable
    int where a list is expected · `list(12345)` raises TypeError inside
    `TrailState.from_dict` line `last_5_lows=list(data.get("last_5_lows") or [])`).
    Test fixture must include `trade.t2_hit_ts` set + provide a non-empty
    `fetch_bars_since` returning ≥1 bar so `_reconstruct_state_from_db`
    produces a state with `max_high_since_t2` set from the reconstructed bars.
    Expect:
    (a) one cross_context entry with event="trail_state_load_failed" appended;
    (b) the returned TrailState has chandelier_engaged=True (per reconstruct);
    (c) max_high_since_t2 equals max(high) of the fake reconstructed bars
        (NOT None · NOT the corrupt value).
    Rationale: a string for `max_high_since_t2` would NOT raise (dataclass
    has no runtime validators · Python's lack of type enforcement allows
    it to slide through). Using a non-list for `last_5_lows` triggers
    `list(int)` → TypeError, which is the actual exception path we test.

20. **`test_load_state_missing_returns_empty`** — `trade.quality = {}`.
    Expect `TrailState()` defaults (max_high_since_t2=None, last_5_lows=[]).

21. **`test_state_roundtrip_json_serializable`** — construct TrailState
    with all fields set, call `.to_dict()` → `json.dumps(d, default=str)`
    succeeds → `json.loads(s)` → `TrailState.from_dict(loaded)` → values
    equal original.

### Cross-context audit (3 tests)

22. **`test_stop_move_appends_to_cross_context`** — trigger an HL_TRAIL
    that moves stop. Then inspect `tm.update_stop_with_audit.call_args`:
    new_stop, reason, bar_ts match expectations. (Note: actual append is
    inside TradeManager.update_stop_with_audit — TrailEngine just calls it.)
    Verify the call signature is `(trade_id=int, new_stop=float, reason=str, bar_ts=str)`.

23. **`test_cross_context_json_serializable_with_datetime`** —
    construct trade with `cross_context=[]`, call `_log_audit(trade, "test",
    {"ts": datetime.now()})`. Expect: `json.dumps(trade.cross_context[-1],
    default=str)` succeeds.

24. **`test_cross_context_preserves_history`** —
    trade.cross_context starts as `[{"event": "entry"}]`. After audit
    append, cross_context has 2 entries; first one is unchanged.

### Concurrency / Sierra fill (3 tests · was 2)

25. **`test_trail_compute_discarded_when_fill_lock_set`** —
    `tm.acquire_fill_lock(trade.id)`. TrailEngine processes the trade,
    HL_TRAIL would move stop. Expect: `tm.update_stop_with_audit` NOT
    called.

26. **`test_fill_lock_logged_to_cross_context`** — same scenario as #25.
    Expect: one cross_context entry with
    event="trail_compute_discarded_sierra_fill".

29. **`test_trail_resumes_after_fill_lock_released`** —
    Defensive symmetry check (fill_lock release path).
    Trade LONG with stop=4490, t2_hit, state with full
    `last_5_lows=[4500, 4498, 4496, 4495, 4497]`.
    Step 1: `tm.acquire_fill_lock(trade.id)`. Run `TrailEngine.on_bar_close`
            with bar low=4499 (would tighten to 4496). Expect:
            `tm.update_stop_with_audit` NOT called · one cross_context
            entry with event="trail_compute_discarded_sierra_fill".
    Step 2: `tm.release_fill_lock(trade.id)`. Run `TrailEngine.on_bar_close`
            again with bar low=4498 (window becomes [4496,4495,4497,4499,4498],
            min=4495). Expect:
            `tm.update_stop_with_audit` IS called with new_stop=4495.0,
            reason="HL_TRAIL".
    Rationale: tests #25 + #26 prove the lock BLOCKS trail. This proves
    the lock RELEASE re-enables trail · ensuring Sierra fill completion
    doesn't permanently disable trail computation.

### Integration (2 tests · TM is MagicMock · NOT true end-to-end with DB)

27. **`test_integration_long_trade_trail_sequence_5_bars`** —
    Simulate via the actual `TrailEngine` instance (with MagicMock TM):
    - Trade LONG, entry=4500, stop=4490, t1=4505, t2=4515.
    - t1_hit_ts set (BE+1T already applied by Stream 3b-1 · stop=4500.25).
    - t2_hit_ts set, bar #1 high=4520 low=4515. Expect: chandelier engages.
    - Bars #2-6 with lows: 4516, 4517, 4518, 4519, 4520. Bar #6
      window=[4516,4517,4518,4519,4520], min=4516.
    - Expect: by bar #6, `update_stop_with_audit` called with HL_TRAIL
      new_stop=4516.0.

28. **`test_integration_short_trade_dual_layer_tighter_wins`** —
    Trade SHORT, pattern="INITIATIVE" (family=OFA_Initiative). t2_hit,
    state.t2_atr_at_engage=2.0 (preloaded). On bars with constantly
    declining highs (4510→4505→4500), LH_TRAIL fires once 5-bar window
    fills. Concurrently, chandelier candidate computed. Expect: both
    chandelier and LH trail run, the tighter one wins via never-widen.
    Verify: at least 2 calls to `update_stop_with_audit` total across
    the 6-bar sequence (one per layer when each first becomes tighter).

---

## §5 · Allowed imports (whitelist · CC do not import outside this list)

In `backend/v9/services/trail_engine.py`:

```python
from __future__ import annotations
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional
from datetime import datetime
from backend.v9.systems.five_min.atr_caps import (
    ATR_MULTIPLIERS,
    _pattern_to_family,
    compute_continuous_atr14,
    compute_time_stop_minutes,
)
from backend.v9.systems.day_type.targets_table import _TARGETS as TARGETS_DICT
```

In `backend/v9/services/trade_manager/manager.py` (edits 1+2+3 only):

```python
# No new imports needed · uses existing V9Trade · TradeState · List · Optional · logger
```

In `tests/v9/services/test_trail_engine.py`:

```python
import json
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from backend.v9.services.trail_engine import TrailEngine, TrailState
```

**Hallucinated imports = retry.** Especially: there is no
`backend.v9.services.event_bus.bar_event` and no `BarRouter` import.
The TrailEngine receives `bar_router` as a constructor arg; it does
not import the class.

---

## §6 · Acceptance criteria

1. `pytest tests/v9/services/test_trail_engine.py -q` → all 29 PASS.
2. `pytest tests/v9/services/test_trade_manager.py -q` → ≥292 PASS
   (294 pre-3b-2 baseline minus 2 pre-existing failures). NO new
   regressions from manager.py edits.
3. `pytest tests/v9/systems/test_five_min/test_atr_caps.py -q` → 19 PASS (unchanged).
4. `pytest tests/v9/systems/test_day_type/ -q` → all pre-3b-2 tests still PASS.
5. `python3 -c "from backend.v9.services.trail_engine import TrailEngine, TrailState; print('OK')"` → prints OK.
6. `python3 -c "from backend.v9.systems.five_min.adaptive_stop import ATR_MULTIPLIERS; assert ATR_MULTIPLIERS['Reactive']==1.0 and ATR_MULTIPLIERS['OFA']==1.5; print('OK')"` → prints OK (Pkg 1 untouched).
7. `git diff 6dfce93..HEAD --stat -- backend/v9/systems/five_min/adaptive_stop.py backend/v9/systems/five_min/atr_caps.py backend/v9/systems/five_min/constants.py backend/v9/systems/day_type/targets_table.py` → ZERO lines changed.
8. ReadLints on the two new/modified files → no new linter errors.
9. `git diff 6dfce93..HEAD --stat -- backend/v9/db/models/trades.py` → ZERO changes.

---

## §7 · Constraints (must not violate)

- **No silent excepts.** Every `except` must `logger.warning(...)` or
  `logger.exception(...)`. The two existing `pass` lines in TrailEngine
  (`_elapsed_minutes` and `_fetch_bars_since` try-blocks) are documented
  with rate-limited info logging at the caller.
- **No `return None` from `_process_trade` without an audit append** —
  if processing aborts mid-way, append a cross_context entry naming
  the layer that aborted.
- **No new dependencies** (no `pip install`).
- **No async I/O inside `_process_trade`** — the BarRouter handler is
  async but everything inside `_process_trade` is sync. `fetch_bars_since`
  is a sync callable (caller can wrap async if needed).
- **Hardcoded magic numbers forbidden.** Use:
  - `ATR_MULTIPLIERS` from atr_caps.py
  - `MES_TICK_SIZE` from constants.py (already shipped)
  - Time-stop minutes from `compute_time_stop_minutes` (do not inline 30/45/etc.)
- **Phase A flag in commit message verbatim:** see top of this document.

---

## §8 · Deliverable format

After running CC, paste back:

1. Files changed (full paths · A/M):
   - A `backend/v9/services/trail_engine.py`
   - A `tests/v9/services/test_trail_engine.py`
   - M `backend/v9/services/trade_manager/manager.py`
2. Commit message (single line, conventional format):
   `feat(s2): Pkg 3b-2 · TrailEngine + persistence · HL/LH + chandelier + restart per D-094 §3.A-C`
   followed by body that includes the Phase A flag verbatim from top of
   this document.
3. Self-report:
   - TODOs left in code? (must be 0)
   - Spec ambiguity encountered? (list explicitly)
   - Forbidden constraint accidentally violated? (own up)
   - Did you add any import outside §5 whitelist?
4. `pytest tests/v9/services/test_trail_engine.py tests/v9/services/test_trade_manager.py -q` output tail (≥30 lines).
5. ReadLints output (paste verbatim).

---

## §9 · Stop signal

STOP and report immediately if any of these occur:

- A required existing helper signature differs from what this prompt
  assumes (e.g., `BarRouter.subscribe` no longer accepts a sync handler).
- A test fixture requires data shape that conflicts with the V9Trade
  model in `backend/v9/db/models/trades.py`.
- An "allowed import" symbol does not exist in the codebase.
- Any forbidden file appears in your edit list.
- ReadLints reports >2 new errors on the new files.
- Pkg 1 regression: `ATR_MULTIPLIERS["Reactive"]` or `["OFA"]` changes value.

Stop format: `STOP — <reason> · need Michael decision on <specific question>`.

DO NOT guess. DO NOT add a `# TODO: ask Michael` comment.

---

*End of mega-prompt · Pkg 3b · Stream 2 · 2026-05-24 19:30 IL*
