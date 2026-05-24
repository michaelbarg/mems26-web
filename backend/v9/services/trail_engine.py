"""TrailEngine — D-094 Pkg 3b Stream 2 · 3-layer trail management on 5-min bars.

Layer 1 (HL/LH swing trail):  tracks rolling highest-high / lowest-low since entry;
                               moves stop only after t2_hit_ts is set.
Layer 2 (Chandelier exit):    ATR-14 Wilder continuous · stop = swing_extreme - k*ATR;
                               activated by same t2 gate.
Layer 3 (Time stop):          cheapest check, runs FIRST; fires once time_stop_minutes
                               elapses from entry_ts regardless of price.

Subscribes to bar_router "5min" events.  on_bar_close is async (BarRouter protocol);
_process_trade is synchronous for easy unit-testing.

State persisted to trade.quality["trail_state"] as JSON via TrailState.to_dict().
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.v9.systems.five_min.atr_caps import (
    ATR_MULTIPLIERS,
    _pattern_to_family,
    compute_continuous_atr14,
    compute_time_stop_minutes,
)
from backend.v9.systems.day_type.targets_table import _TARGETS as TARGETS_DICT

logger = logging.getLogger(__name__)


# ── TrailState ────────────────────────────────────────────────────────────────

@dataclass
class TrailState:
    """Per-trade trail state, persisted to trade.quality["trail_state"].

    All fields are JSON-serialisable primitives so to_dict / from_dict
    provide a lossless round-trip.
    """

    swing_high: Optional[float] = None       # highest bar.high seen since entry
    swing_low: Optional[float] = None        # lowest bar.low seen since entry
    bars_processed: int = 0                  # count of 5-min bars seen for this trade
    last_bar_ts: Optional[str] = None        # ISO ts of last bar processed
    atr14: Optional[float] = None            # last computed Wilder ATR-14
    time_stop_fired: bool = False            # True once Layer 3 close was issued
    trail_active: bool = False               # True once t2 gate opened

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to plain dict for JSON storage."""
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TrailState":
        """Restore from JSON dict stored in trade.quality["trail_state"]."""
        return cls(
            swing_high=d.get("swing_high"),
            swing_low=d.get("swing_low"),
            bars_processed=int(d.get("bars_processed", 0)),
            last_bar_ts=d.get("last_bar_ts"),
            atr14=d.get("atr14"),
            time_stop_fired=bool(d.get("time_stop_fired", False)),
            trail_active=bool(d.get("trail_active", False)),
        )


# ── TrailEngine ───────────────────────────────────────────────────────────────

class TrailEngine:
    """3-layer trail management engine.

    Args:
        trade_manager: TradeManager instance (injected — do NOT import BarRouter class).
        bar_router:    BarRouter instance (injected); subscribe called in __init__.
        yesterday_bars: list of yesterday's bar objects for ATR-14 seam computation.
        mode:          "shadow" | "demo" | "live"  — filters list_trades_past_t1.
    """

    def __init__(
        self,
        trade_manager,
        bar_router,
        yesterday_bars: Optional[List[Any]] = None,
        mode: Optional[str] = None,
    ) -> None:
        self._tm = trade_manager
        self._mode = mode
        self._yesterday_bars: List[Any] = list(yesterday_bars or [])
        self._today_bars: List[Any] = []          # accumulate today's closed bars

        bar_router.subscribe("5min", self.on_bar_close)
        logger.info("[TrailEngine] subscribed to 5min bars (mode=%s)", mode)

    # ── public async entry point (BarRouter protocol) ─────────────────────────

    async def on_bar_close(self, event) -> None:
        """Called by BarRouter on every closed 5-min bar.

        Iterates all trades past T1, delegates per-trade logic to _process_trade.
        Accumulates today's bars for ATR continuity.
        """
        bar = self._normalize_bar(event)
        if bar is None:
            return

        # Accumulate bar for ATR smoothing
        self._today_bars.append(event.payload if hasattr(event, "payload") else event)

        try:
            trades = self._tm.list_trades_past_t1(mode=self._mode)
        except Exception as exc:
            logger.error("[TrailEngine] list_trades_past_t1 failed: %s", exc, exc_info=True)
            return

        for trade in trades:
            try:
                self._process_trade(trade, bar)
            except Exception as exc:
                logger.error(
                    "[TrailEngine] _process_trade failed trade_id=%s: %s",
                    getattr(trade, "id", "?"), exc, exc_info=True,
                )

    # ── per-trade synchronous processing ─────────────────────────────────────

    def _process_trade(self, trade, bar: Dict[str, Any]) -> None:
        """Apply 3 layers of trail logic to a single trade.

        Layer 3 (time stop) is evaluated FIRST — cheapest, no price math.
        Layer 1 (HL/LH swing) and Layer 2 (Chandelier) share the t2 gate.
        """
        trade_id = trade.id
        direction = (trade.direction or "").upper()
        if direction not in ("LONG", "SHORT"):
            return

        # Skip if Sierra fill is in progress (concurrency guard — LOCK 3)
        if self._tm.is_fill_locked(trade_id):
            logger.debug("[TrailEngine] trade %s fill-locked, skipping", trade_id)
            return

        # Load or init trail state
        state = self._load_state(trade)

        bar_high = bar["high"]
        bar_low = bar["low"]
        bar_ts = bar["ts"]

        # ── Layer 3: Time stop (runs FIRST — cheapest) ────────────────────────
        if state.time_stop_fired:
            return  # already issued close for this trade

        if self._check_time_stop(trade, state, bar_ts):
            self._save_state(trade, state)
            return  # close issued; stop processing layers 1+2

        # ── Update swing extremes (needed by both Layer 1 and Layer 2) ────────
        if state.swing_high is None or bar_high > state.swing_high:
            state.swing_high = bar_high
        if state.swing_low is None or bar_low < state.swing_low:
            state.swing_low = bar_low

        state.bars_processed += 1
        state.last_bar_ts = bar_ts

        # ── t2 gate: Layers 1+2 only activate after t2_hit_ts ─────────────────
        if trade.t2_hit_ts is None:
            self._save_state(trade, state)
            return

        state.trail_active = True

        # ── Layer 2: Chandelier ATR stop ──────────────────────────────────────
        atr = compute_continuous_atr14(self._yesterday_bars, self._today_bars)
        state.atr14 = atr

        if atr is not None:
            chandelier_stop = self._compute_chandelier_stop(trade, state, atr, direction)
            if chandelier_stop is not None:
                self._move_stop_tighter_only(
                    trade, chandelier_stop, direction, "chandelier_atr14", bar_ts
                )

        # ── Layer 1: HL/LH swing trail ────────────────────────────────────────
        swing_stop = self._compute_swing_stop(state, direction)
        if swing_stop is not None:
            self._move_stop_tighter_only(
                trade, swing_stop, direction, "hl_lh_swing", bar_ts
            )

        self._save_state(trade, state)

    # ── Layer 3 helper ────────────────────────────────────────────────────────

    def _check_time_stop(
        self,
        trade,
        state: TrailState,
        bar_ts: str,
    ) -> bool:
        """Return True and call close_trade if time stop elapsed.

        Uses compute_time_stop_minutes(day_type, pattern_family, targets_table=TARGETS_DICT)
        which returns min(day_axis_stop, pattern_axis_stop).
        """
        entry_ts = trade.entry_ts
        if entry_ts is None:
            return False

        quality = trade.quality if isinstance(trade.quality, dict) else {}
        day_type: Optional[str] = quality.get("day_type")
        pattern_name: Optional[str] = quality.get("pattern_name")

        if day_type is None:
            return False

        pattern_family = _pattern_to_family(pattern_name) if pattern_name else None
        minutes = compute_time_stop_minutes(
            day_type,
            pattern_family,
            targets_table=TARGETS_DICT,
        )
        if minutes is None:
            return False

        # Normalise entry_ts to UTC-aware datetime
        if isinstance(entry_ts, str):
            try:
                entry_ts = datetime.fromisoformat(entry_ts.replace("Z", "+00:00"))
            except ValueError:
                return False
        if entry_ts.tzinfo is None:
            entry_ts = entry_ts.replace(tzinfo=timezone.utc)

        now_utc = datetime.now(timezone.utc)
        elapsed_minutes = (now_utc - entry_ts).total_seconds() / 60.0

        if elapsed_minutes >= minutes:
            logger.info(
                "[TrailEngine] time-stop fired: trade=%s elapsed=%.1fmin limit=%dmin",
                trade.id, elapsed_minutes, minutes,
            )
            state.time_stop_fired = True
            self._tm.close_trade(trade.id, "TIME_STOP")
            return True

        return False

    # ── Layer 1 helper ────────────────────────────────────────────────────────

    def _compute_swing_stop(
        self,
        state: TrailState,
        direction: str,
    ) -> Optional[float]:
        """HL/LH trail: LONG → trailing stop at swing_low; SHORT → swing_high."""
        if direction == "LONG":
            return state.swing_low
        if direction == "SHORT":
            return state.swing_high
        return None

    # ── Layer 2 helper ────────────────────────────────────────────────────────

    def _compute_chandelier_stop(
        self,
        trade,
        state: TrailState,
        atr: float,
        direction: str,
    ) -> Optional[float]:
        """Chandelier exit: swing_extreme ± k*ATR14.

        k (multiplier) comes from ATR_MULTIPLIERS keyed by pattern family.
        Falls back to 1.5 if pattern is unknown.
        """
        quality = trade.quality if isinstance(trade.quality, dict) else {}
        pattern_name: Optional[str] = quality.get("pattern_name")
        family = _pattern_to_family(pattern_name) if pattern_name else None
        k = ATR_MULTIPLIERS.get(family, 1.5) if family else 1.5

        if direction == "LONG":
            if state.swing_high is None:
                return None
            return state.swing_high - k * atr
        if direction == "SHORT":
            if state.swing_low is None:
                return None
            return state.swing_low + k * atr
        return None

    # ── Stop movement guard ───────────────────────────────────────────────────

    def _move_stop_tighter_only(
        self,
        trade,
        candidate: float,
        direction: str,
        reason: str,
        bar_ts: str,
    ) -> None:
        """Move stop only if candidate is tighter than current stop.

        Enforces direction invariant:
          LONG  → new_stop must be > current_stop (moves stop UP, tighter)
          SHORT → new_stop must be < current_stop (moves stop DOWN, tighter)

        Also checks fill lock once more inside the guard (belt-and-suspenders).
        """
        trade_id = trade.id

        # Belt-and-suspenders fill lock re-check
        if self._tm.is_fill_locked(trade_id):
            return

        current_stop = trade.stop
        if current_stop is None:
            return

        try:
            current_stop = float(current_stop)
            candidate = float(candidate)
        except (TypeError, ValueError):
            return

        if direction == "LONG":
            if candidate <= current_stop:
                return   # not tighter
        elif direction == "SHORT":
            if candidate >= current_stop:
                return   # not tighter
        else:
            return

        self._tm.update_stop_with_audit(
            trade_id,
            new_stop=candidate,
            reason=reason,
            bar_ts=bar_ts,
        )
        logger.debug(
            "[TrailEngine] stop moved: trade=%s %s %.4f → %.4f (%s)",
            trade_id, direction, current_stop, candidate, reason,
        )

    # ── State persistence ─────────────────────────────────────────────────────

    def _load_state(self, trade) -> TrailState:
        """Load TrailState from trade.quality["trail_state"]; init if absent."""
        quality = trade.quality if isinstance(trade.quality, dict) else {}
        raw = quality.get("trail_state")
        if isinstance(raw, dict):
            try:
                return TrailState.from_dict(raw)
            except Exception:
                pass
        return TrailState()

    def _save_state(self, trade, state: TrailState) -> None:
        """Persist TrailState back to trade.quality["trail_state"].

        Reassigns trade.quality so SQLAlchemy detects the mutation.
        """
        quality = dict(trade.quality) if isinstance(trade.quality, dict) else {}
        quality["trail_state"] = state.to_dict()
        trade.quality = quality

    # ── Bar normalisation ─────────────────────────────────────────────────────

    def _normalize_bar(self, event) -> Optional[Dict[str, Any]]:
        """Extract high / low / ts from a BarEvent.payload.

        Returns None if the payload is missing required fields.
        """
        try:
            payload = event.payload if hasattr(event, "payload") else event
            if not isinstance(payload, dict):
                payload = dict(payload)

            high = payload.get("high") or payload.get("h")
            low = payload.get("low") or payload.get("l")
            ts = payload.get("ts") or ""

            if high is None or low is None:
                logger.warning("[TrailEngine] bar missing high/low: %s", payload)
                return None

            return {
                "high": float(high),
                "low": float(low),
                "ts": str(ts),
            }
        except Exception as exc:
            logger.error("[TrailEngine] _normalize_bar failed: %s", exc)
            return None
