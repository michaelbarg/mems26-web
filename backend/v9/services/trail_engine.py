"""TrailEngine — D-094 Pkg 3b Stream 3 · 4-layer trail management on 5-min bars.

Layer 1 (HL/LH swing trail):  5-bar sliding window of lows/highs; fires once
                               len(last_5_lows) >= 5 and t2 gate open.
Layer 2 (Chandelier exit):    ATR-14 Wilder continuous; ATR frozen at engage
                               via _engage_chandelier(); stop = max_high_since_t2
                               (or min_low) - k*frozen_ATR.
Layer 3 (Time stop):          cheapest check, runs FIRST; fires once
                               time_stop_minutes elapses from entry_ts.
Layer 4 (D-094 §3.B services): 5 contextual services run in D-094 order after
                               layers 1-3; each can TIGHTEN or EXIT.

Subscribes to bar_router "5min" events.  on_bar_close is async (BarRouter protocol);
_process_trade is synchronous for easy unit-testing.

State persisted to trade.quality["trail_state"] as JSON via TrailState.to_dict().
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

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

    D-094 Pkg 3b Stream 3 fields:
    - last_5_lows / last_5_highs: sliding window of the 5 most recent bar lows/highs
    - max_high_since_t2 / min_low_since_t2: extremes tracked since t2 gate opened
    - chandelier_engaged: True once _engage_chandelier() has run (ATR frozen)
    - t2_bar_ts: ISO ts of the bar where chandelier was first engaged
    - t2_atr_at_engage: frozen ATR value from engage moment (None = not engaged)
    """

    # 5-bar sliding window
    last_5_lows: List[float] = field(default_factory=list)
    last_5_highs: List[float] = field(default_factory=list)

    # Chandelier extremes tracked since t2 gate opened
    max_high_since_t2: Optional[float] = None
    min_low_since_t2: Optional[float] = None

    # Chandelier engage state
    chandelier_engaged: bool = False
    t2_bar_ts: Optional[str] = None
    t2_atr_at_engage: Optional[float] = None

    # Bookkeeping (kept from Stream 2)
    bars_processed: int = 0
    last_bar_ts: Optional[str] = None
    time_stop_fired: bool = False
    trail_active: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to plain dict for JSON storage."""
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TrailState":
        """Restore from JSON dict stored in trade.quality["trail_state"]."""
        return cls(
            last_5_lows=list(d.get("last_5_lows") or []),
            last_5_highs=list(d.get("last_5_highs") or []),
            max_high_since_t2=d.get("max_high_since_t2"),
            min_low_since_t2=d.get("min_low_since_t2"),
            chandelier_engaged=bool(d.get("chandelier_engaged", False)),
            t2_bar_ts=d.get("t2_bar_ts"),
            t2_atr_at_engage=d.get("t2_atr_at_engage"),
            bars_processed=int(d.get("bars_processed", 0)),
            last_bar_ts=d.get("last_bar_ts"),
            time_stop_fired=bool(d.get("time_stop_fired", False)),
            trail_active=bool(d.get("trail_active", False)),
        )


# ── TrailEngine ───────────────────────────────────────────────────────────────

class TrailEngine:
    """4-layer trail management engine (D-094 Pkg 3b Stream 3).

    Args:
        trade_manager:     TradeManager instance (injected).
        bar_router:        BarRouter instance; subscribe called in __init__.
        yesterday_bars:    list of yesterday's bar objects for ATR-14 seam.
        mode:              "shadow" | "demo" | "live" — filters list_trades_past_t1.
        fetch_bars_since:  Optional[Callable] — fetches bars from DB since a ts.
        woodies_provider:  Optional[Callable] — returns get_layer4_context() dict.
    """

    def __init__(
        self,
        trade_manager,
        bar_router,
        yesterday_bars: Optional[List[Any]] = None,
        mode: Optional[str] = None,
        fetch_bars_since: Optional[Callable] = None,
        woodies_provider: Optional[Callable] = None,
    ) -> None:
        self._tm = trade_manager
        self._mode = mode
        self._yesterday_bars: List[Any] = list(yesterday_bars or [])
        self._today_bars: List[Any] = []          # accumulate today's closed bars
        self._fetch_bars_since = fetch_bars_since
        self._woodies_provider = woodies_provider

        bar_router.subscribe("5min", self.on_bar_close)
        logger.info("[TrailEngine] subscribed to 5min bars (mode=%s)", mode)

    # ── public async entry point (BarRouter protocol) ─────────────────────────

    async def on_bar_close(self, event) -> None:
        """Called by BarRouter on every closed 5-min bar.

        D-094 §3.B.3 wiring order per trade:
          (a) _update_mfe
          (b) _process_trade  (Layers 1-3)
          (c) _apply_layer4   (Layer 4 contextual services)

        Accumulates today's bars for ATR continuity.
        """
        bar = self._normalize_bar(event)
        if bar is None:
            return

        # Accumulate bar for ATR smoothing
        self._today_bars.append(event.payload if hasattr(event, "payload") else event)

        bar_ts = bar.get("ts", "")

        try:
            trades = self._tm.list_trades_past_t1(mode=self._mode)
        except Exception as exc:
            logger.error("[TrailEngine] list_trades_past_t1 failed: %s", exc, exc_info=True)
            return

        for trade in trades:
            try:
                # (a) update MFE quality fields
                self._update_mfe(trade, bar)
                # (b) layers 1-3
                self._process_trade(trade, bar)
                # (c) layer 4 contextual services
                self._apply_layer4(trade, bar, bar_ts)
            except Exception as exc:
                logger.error(
                    "[TrailEngine] on_bar_close failed trade_id=%s: %s",
                    getattr(trade, "id", "?"), exc, exc_info=True,
                )

    # ── per-trade synchronous processing (Layers 1-3) ────────────────────────

    def _process_trade(self, trade, bar: Dict[str, Any]) -> None:
        """Apply 3 layers of trail logic to a single trade.

        Layer 3 (time stop) is evaluated FIRST — cheapest, no price math.
        Layer 1 (HL/LH 5-bar window) and Layer 2 (Chandelier frozen ATR)
        share the t2 gate.
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

        # ── Update 5-bar sliding windows ─────────────────────────────────────
        state.last_5_lows.append(bar_low)
        state.last_5_highs.append(bar_high)
        # Keep only last 5
        if len(state.last_5_lows) > 5:
            state.last_5_lows = state.last_5_lows[-5:]
        if len(state.last_5_highs) > 5:
            state.last_5_highs = state.last_5_highs[-5:]

        state.bars_processed += 1
        state.last_bar_ts = bar_ts

        # ── t2 gate: Layers 1+2 only activate after t2_hit_ts ─────────────────
        if trade.t2_hit_ts is None:
            self._save_state(trade, state)
            return

        state.trail_active = True

        # Update max_high / min_low since t2 opened
        if state.max_high_since_t2 is None or bar_high > state.max_high_since_t2:
            state.max_high_since_t2 = bar_high
        if state.min_low_since_t2 is None or bar_low < state.min_low_since_t2:
            state.min_low_since_t2 = bar_low

        # ── Layer 2: Chandelier ATR stop (frozen ATR) ─────────────────────────
        self._engage_chandelier(trade, bar, state)
        chandelier_stop = self._compute_chandelier_stop_v3(trade, state, direction)
        if chandelier_stop is not None:
            self._move_stop_tighter_only(
                trade, chandelier_stop, direction, "chandelier_atr14_frozen", bar_ts
            )

        # ── Layer 1: HL/LH 5-bar swing trail ─────────────────────────────────
        if len(state.last_5_lows) >= 5 and len(state.last_5_highs) >= 5:
            swing_stop = self._compute_swing_stop_5bar(state, direction)
            if swing_stop is not None:
                self._move_stop_tighter_only(
                    trade, swing_stop, direction, "hl_lh_trail_5bar", bar_ts
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

    def _compute_swing_stop_5bar(
        self,
        state: TrailState,
        direction: str,
    ) -> Optional[float]:
        """HL/LH trail: LONG → min of last_5_lows; SHORT → max of last_5_highs.

        Only fires when both windows have >= 5 entries.
        """
        if direction == "LONG":
            if len(state.last_5_lows) < 5:
                return None
            return min(state.last_5_lows)
        if direction == "SHORT":
            if len(state.last_5_highs) < 5:
                return None
            return max(state.last_5_highs)
        return None

    # ── Layer 2 helpers ───────────────────────────────────────────────────────

    def _engage_chandelier(self, trade, bar: Dict[str, Any], state: TrailState) -> None:
        """Run once per trade: freeze ATR and write audit to cross_context.

        Idempotent — returns immediately if already engaged.
        """
        if state.chandelier_engaged:
            return

        atr = compute_continuous_atr14(self._yesterday_bars, self._today_bars)
        if atr is None:
            # Not enough bars yet — do not engage; remain dormant
            return

        state.chandelier_engaged = True
        state.t2_bar_ts = bar.get("ts")
        state.t2_atr_at_engage = float(atr)

        entry = {
            "event": "chandelier_engaged",
            "bar_ts": state.t2_bar_ts,
            "atr_frozen": state.t2_atr_at_engage,
            "max_high_since_t2": state.max_high_since_t2,
            "min_low_since_t2": state.min_low_since_t2,
        }
        self._append_cross_context(trade, entry)
        logger.info(
            "[TrailEngine] chandelier engaged: trade=%s bar_ts=%s atr=%.4f",
            trade.id, state.t2_bar_ts, state.t2_atr_at_engage,
        )

    def _compute_chandelier_stop_v3(
        self,
        trade,
        state: TrailState,
        direction: str,
    ) -> Optional[float]:
        """Chandelier exit using frozen ATR (t2_atr_at_engage).

        Uses max_high_since_t2 for LONG, min_low_since_t2 for SHORT.
        Raises ValueError if chandelier is engaged but ATR is None (impossible
        by construction — no silent fallback per D-094 spec).
        """
        if not state.chandelier_engaged:
            return None

        atr = state.t2_atr_at_engage
        if atr is None:
            raise ValueError(
                f"[TrailEngine] chandelier_engaged=True but t2_atr_at_engage=None for "
                f"trade={trade.id}; state corrupt — reconstruct required"
            )

        quality = trade.quality if isinstance(trade.quality, dict) else {}
        pattern_name: Optional[str] = quality.get("pattern_name")
        family = _pattern_to_family(pattern_name) if pattern_name else None
        k = ATR_MULTIPLIERS.get(family, 1.5) if family else 1.5

        if direction == "LONG":
            if state.max_high_since_t2 is None:
                return None
            return state.max_high_since_t2 - k * atr
        if direction == "SHORT":
            if state.min_low_since_t2 is None:
                return None
            return state.min_low_since_t2 + k * atr
        return None

    # ── Cross-context helpers ─────────────────────────────────────────────────

    def _append_cross_context(self, trade, entry: dict) -> None:
        """Append an audit entry to trade.quality["cross_context"].

        Validates JSON-serializability before storing.
        Reassigns the list so SQLAlchemy detects the mutation.
        """
        # Validate JSON-serializability
        try:
            json.dumps(entry)
        except (TypeError, ValueError) as exc:
            logger.warning(
                "[TrailEngine] cross_context entry not JSON-serializable (trade=%s): %s",
                getattr(trade, "id", "?"), exc,
            )
            return

        quality = dict(trade.quality) if isinstance(trade.quality, dict) else {}
        existing = list(quality.get("cross_context") or [])
        existing.append(entry)
        quality["cross_context"] = existing    # reassign — SQLAlchemy detects
        trade.quality = quality

    # ── State persistence ─────────────────────────────────────────────────────

    def _load_state(self, trade) -> TrailState:
        """Load TrailState from trade.quality["trail_state"]; init if absent.

        Falls back to _reconstruct_state_from_db on corrupt state.
        """
        quality = trade.quality if isinstance(trade.quality, dict) else {}
        raw = quality.get("trail_state")
        if isinstance(raw, dict):
            try:
                return TrailState.from_dict(raw)
            except Exception as exc:
                logger.warning(
                    "[TrailEngine] corrupt trail_state for trade=%s (%s); reconstructing",
                    getattr(trade, "id", "?"), exc,
                )
                return self._reconstruct_state_from_db(trade)
        return TrailState()

    def _reconstruct_state_from_db(self, trade) -> TrailState:
        """Rebuild TrailState from bars since entry; chandelier stays dormant (ATR=None).

        Used as fallback when trail_state is corrupt or missing.
        """
        state = TrailState()
        if self._fetch_bars_since is None:
            logger.warning(
                "[TrailEngine] _reconstruct_state_from_db: no fetch_bars_since "
                "callable; returning fresh state for trade=%s",
                getattr(trade, "id", "?"),
            )
            return state

        entry_ts = getattr(trade, "entry_ts", None)
        if entry_ts is None:
            return state

        try:
            bars = self._fetch_bars_since(entry_ts)
        except Exception as exc:
            logger.warning(
                "[TrailEngine] fetch_bars_since failed for trade=%s: %s",
                getattr(trade, "id", "?"), exc,
            )
            return state

        for bar in bars:
            h = self._bar_attr(bar, "high") or self._bar_attr(bar, "h") or 0.0
            l = self._bar_attr(bar, "low") or self._bar_attr(bar, "l") or 0.0
            ts = self._bar_attr(bar, "ts") or ""

            state.last_5_lows.append(float(l))
            state.last_5_highs.append(float(h))
            if len(state.last_5_lows) > 5:
                state.last_5_lows = state.last_5_lows[-5:]
            if len(state.last_5_highs) > 5:
                state.last_5_highs = state.last_5_highs[-5:]

            state.bars_processed += 1
            state.last_bar_ts = str(ts)

        # chandelier remains dormant (ATR=None) — caller will _engage_chandelier
        # on next bar when ATR becomes available
        logger.info(
            "[TrailEngine] reconstructed state from %d bars for trade=%s",
            len(bars), getattr(trade, "id", "?"),
        )
        return state

    def _save_state(self, trade, state: TrailState) -> None:
        """Persist TrailState back to trade.quality["trail_state"].

        Reassigns trade.quality so SQLAlchemy detects the mutation.
        """
        quality = dict(trade.quality) if isinstance(trade.quality, dict) else {}
        quality["trail_state"] = state.to_dict()
        trade.quality = quality

    # ── MFE tracking ─────────────────────────────────────────────────────────

    def _update_mfe(self, trade, bar: Dict[str, Any]) -> None:
        """Update quality["mfe_high"] and quality["mfe_low"] from current bar.

        Called before _process_trade on every bar (D-094 §3.B.3 step a).
        """
        quality = dict(trade.quality) if isinstance(trade.quality, dict) else {}
        bar_high = bar.get("high", 0.0)
        bar_low = bar.get("low", 0.0)

        mfe_high = quality.get("mfe_high")
        mfe_low = quality.get("mfe_low")

        updated = False
        if mfe_high is None or bar_high > mfe_high:
            quality["mfe_high"] = float(bar_high)
            updated = True
        if mfe_low is None or bar_low < mfe_low:
            quality["mfe_low"] = float(bar_low)
            updated = True

        if updated:
            trade.quality = quality

    # ── Layer 4 wiring ────────────────────────────────────────────────────────

    def _adapt_trade_for_layer4(self, trade, bar_close: float) -> Dict[str, Any]:
        """Build the trade dict expected by all Layer 4 evaluate() calls.

        Bridges TradeManager trade object → flat dict with both stop/stop_price keys.
        """
        quality = trade.quality if isinstance(trade.quality, dict) else {}
        entry_price = getattr(trade, "entry_price", None)
        stop = getattr(trade, "stop", None)
        t2 = quality.get("t2_price") or quality.get("t2")
        mfe = quality.get("mfe_high") if (trade.direction or "").upper() == "LONG" \
            else quality.get("mfe_low")

        return {
            "direction": (trade.direction or "").upper(),
            "entry": entry_price,
            "stop": stop,
            "stop_price": stop,         # Layer 4 services use stop_price key
            "current_price": bar_close,
            "t2": t2,
            "mfe": mfe,
            "day_type_at_entry": quality.get("day_type"),
        }

    def _apply_layer4(self, trade, bar: Dict[str, Any], bar_ts: str) -> None:
        """Run 5 Layer 4 services in D-094 order.

        D-094 §3.B.3 step (c): services are stateless — each call to evaluate()
        is independent. The tightest TIGHTEN_STOP wins; EXIT routes immediately.

        Services (D-094 §3.B.3 order):
          1. mfe_peak_tighten (universal)
          2. cci_flat_tighten (S4 only · needs cci_history)
          3. tcci_cross_exit (S4 only · EXIT short-circuits)
          4. swi_tighten (universal · uses Woodies snapshot if available)
          5. day_type_targets_verify (universal · LAST)
        """
        # Guard: skip if fill-locked
        if self._tm.is_fill_locked(trade.id):
            return

        bar_close = bar.get("close") or bar.get("c") or bar.get("high")
        if bar_close is None:
            return

        trade_dict = self._adapt_trade_for_layer4(trade, float(bar_close))

        # Fetch Woodies context (SWI, CCI history, direction change)
        woodies_ctx: Dict[str, Any] = {}
        if self._woodies_provider is not None:
            try:
                woodies_ctx = self._woodies_provider() or {}
            except Exception as exc:
                logger.warning("[TrailEngine] woodies_provider failed: %s", exc)

        swi = woodies_ctx.get("swi") or {}
        cci_history: List[float] = woodies_ctx.get("cci_history") or []
        direction_change_event = woodies_ctx.get("direction_change_event")
        current_day_type = self._fetch_current_day_type()

        # Import Layer 4 service modules (frozen — DO NOT modify)
        from backend.v9.services.layer4 import tcci_cross_exit
        from backend.v9.services.layer4 import mfe_peak_tighten
        from backend.v9.services.layer4 import cci_flat_tighten
        from backend.v9.services.layer4 import swi_tighten
        from backend.v9.services.layer4 import day_type_targets_verify

        candidate_stops: List[Dict] = []

        # 1. MFE peak tighten (universal)
        try:
            result = mfe_peak_tighten.evaluate(trade_dict)
            if result and result.get("action") == "TIGHTEN_STOP" and result.get("new_stop") is not None:
                candidate_stops.append(result)
        except Exception as exc:
            logger.warning("[TrailEngine] mfe_peak_tighten failed trade=%s: %s", trade.id, exc)

        # 2. CCI flat tighten (S4 only · needs cci_history)
        if cci_history and len(cci_history) >= 3:
            try:
                result = cci_flat_tighten.evaluate(trade_dict, cci_history)
                if result and result.get("action") == "TIGHTEN_STOP" and result.get("new_stop") is not None:
                    candidate_stops.append(result)
            except Exception as exc:
                logger.warning("[TrailEngine] cci_flat_tighten failed trade=%s: %s", trade.id, exc)

        # 3. TCCI cross exit (S4 only · EXIT short-circuits)
        if direction_change_event:
            try:
                result = tcci_cross_exit.evaluate(trade_dict, direction_change_event)
                if result and result.get("action") == "EXIT":
                    self._append_cross_context(trade, {
                        "event": "layer4_exit",
                        "rule": "TCCI_CROSS",
                        "bar_ts": bar_ts,
                        "notes": result.get("reasoning_notes"),
                    })
                    self._tm.close_trade(trade.id, "TCCI_CROSS_AGAINST_TRADE")
                    return
            except Exception as exc:
                logger.warning("[TrailEngine] tcci_cross_exit failed trade=%s: %s", trade.id, exc)

        # 4. SWI tighten (universal · uses Woodies snapshot if available)
        if swi and swi.get("value") is not None:
            try:
                result = swi_tighten.evaluate(trade_dict, swi)
                if result and result.get("action") == "TIGHTEN_STOP" and result.get("new_stop") is not None:
                    candidate_stops.append(result)
            except Exception as exc:
                logger.warning("[TrailEngine] swi_tighten failed trade=%s: %s", trade.id, exc)

        # Apply TIGHTEST candidate stop (Gap 13 · tightens only · v4 Patch A)
        if candidate_stops:
            self._apply_tightest_stop(trade, candidate_stops, bar_ts)

        # 5. Day type targets verify (universal · LAST per §3.B.3)
        if current_day_type:
            try:
                result = day_type_targets_verify.evaluate(trade_dict, current_day_type)
                if result:
                    self._handle_day_type_action(trade, result, bar_ts)
            except Exception as exc:
                logger.warning("[TrailEngine] day_type_targets_verify failed trade=%s: %s", trade.id, exc)

    def _apply_tightest_stop(
        self,
        trade,
        candidates: List[Dict],
        bar_ts: str,
    ) -> None:
        """Apply tightest new_stop via _move_stop_tighter_only (Gap 13 + Gap 15).

        Routes through _move_stop_tighter_only so fill_lock + direction-tighter
        guards apply. Audit appended only on success (post-move trade.stop != old_stop).

        LONG: highest new_stop wins (closest to entry below price).
        SHORT: lowest new_stop wins (closest to entry above price).
        """
        if not candidates:
            return
        direction = (trade.direction or "").upper()
        if direction not in ("LONG", "SHORT"):
            return

        winner = (max if direction == "LONG" else min)(
            candidates, key=lambda a: a["new_stop"],
        )
        old_stop = trade.stop

        self._move_stop_tighter_only(
            trade, float(winner["new_stop"]), direction,
            f"LAYER4_{winner.get('rule', 'UNKNOWN')}", bar_ts,
        )

        # Append layer4_tighten audit ONLY if stop actually moved
        if trade.stop != old_stop:
            self._append_cross_context(trade, {
                "event": "layer4_tighten",
                "rule": winner.get("rule"),
                "new_stop": winner["new_stop"],
                "old_stop": old_stop,
                "bar_ts": bar_ts,
                "notes": winner.get("reasoning_notes"),
            })

    def _handle_day_type_action(self, trade, action: dict, bar_ts: str) -> None:
        """D-094 escalation: WARN -> CLOSE_ALL when current_day_type is NO_TRADE.

        The Layer 4 service returns WARN for ALL day-type mismatches. We
        escalate ONLY when reclassification is to a no_trade day type.
        All WARN rules are logged to cross_context. Escalation gate stays
        narrow: only DAY_TYPE_TARGETS_MISMATCH + no_trade reclass triggers close.
        """
        if action.get("action") != "WARN":
            return

        rule = action.get("rule", "UNKNOWN_WARN")
        from backend.v9.systems.day_type.targets_table import get_targets
        current_day_type = action.get("current_day_type")
        current_targets = get_targets(current_day_type) if current_day_type else None

        # Default: log WARN to cross_context · no close
        if rule != "DAY_TYPE_TARGETS_MISMATCH" or not current_targets or not current_targets.get("no_trade"):
            self._append_cross_context(trade, {
                "event": "layer4_warn",
                "rule": rule,
                "current_day_type": current_day_type,
                "bar_ts": bar_ts,
                "notes": action.get("reasoning_notes"),
            })
            return

        # Escalation: close the trade (no_trade reclass)
        self._append_cross_context(trade, {
            "event": "layer4_exit",
            "rule": "DAY_TYPE_NO_TRADE_RECLASS",
            "current_day_type": current_day_type,
            "bar_ts": bar_ts,
            "notes": action.get("reasoning_notes"),
        })
        try:
            self._tm.close_trade(trade.id, "DAY_TYPE_NO_TRADE_RECLASS")
        except Exception:
            logger.exception(
                "[TrailEngine] close_trade failed during day_type escalation trade_id=%s",
                trade.id,
            )

    def _fetch_current_day_type(self) -> Optional[str]:
        """Read current day type classification from V9DayTypeState via SessionLocal."""
        try:
            from backend.v9.db.session import SessionLocal
            from backend.v9.systems.day_type.models import V9DayTypeState

            db = SessionLocal()
            try:
                row = (
                    db.query(V9DayTypeState)
                    .order_by(V9DayTypeState.ts.desc())
                    .first()
                )
                if row is not None:
                    return row.day_type
                return None
            finally:
                db.close()
        except Exception as exc:
            logger.warning("[TrailEngine] _fetch_current_day_type failed: %s", exc)
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

    # ── Static helper ─────────────────────────────────────────────────────────

    @staticmethod
    def _bar_attr(bar, key: str):
        """Read field from bar object (attr-first) or dict."""
        if hasattr(bar, key):
            return getattr(bar, key)
        if isinstance(bar, dict):
            return bar.get(key)
        return None

    # ── Bar normalisation ─────────────────────────────────────────────────────

    def _normalize_bar(self, event) -> Optional[Dict[str, Any]]:
        """Extract high / low / close / ts from a BarEvent.payload.

        Returns None if the payload is missing required fields.
        """
        try:
            payload = event.payload if hasattr(event, "payload") else event
            if not isinstance(payload, dict):
                payload = dict(payload)

            high = payload.get("high") or payload.get("h")
            low = payload.get("low") or payload.get("l")
            close = payload.get("close") or payload.get("c")
            ts = payload.get("ts") or ""

            if high is None or low is None:
                logger.warning("[TrailEngine] bar missing high/low: %s", payload)
                return None

            return {
                "high": float(high),
                "low": float(low),
                "close": float(close) if close is not None else float(high),
                "ts": str(ts),
            }
        except Exception as exc:
            logger.error("[TrailEngine] _normalize_bar failed: %s", exc)
            return None
