"""System wrappers — adapts each of the 6 V9 systems to BaseSystem interface.

Each wrapper:
- Declares subscribed_streams
- Implements analyze() by calling the existing detection/analysis code
- Gracefully handles missing data (returns None, never crashes)

System roles per Master Matrix V1.0 (restored by D-089, 2026-05-23):
  Firing (can generate trade Signals): 5-Min (2), Footprint (3), Woodies (4)
  Observer (no trade signals):         DayType (1), TPO (5), Killzone (6)

D-089 supersedes D-082 (S3 Observer-only) + D-086 (S3 SHADOW firing tolerated,
"revisit before LIVE"). The 3 firing systems are now canonical: S2, S3, S4.
Decision doc: docs/decisions/D-089_S3_FIRING_LOCKED.md
NOTE: `if mode == "LIVE":` safety net in `footprint/footprint_system.py::_fire()`
      remains KEEP until Michael explicitly removes it (no removal pre-SHADOW).

NOTE: TickReversal is an Entry Mechanism (15-tick reversal bar), NOT a system.
      System 3 = Footprint (per Constitution V3 D-049).
"""

from __future__ import annotations

import logging
from typing import List, Optional

from backend.v9.systems.base_system import BaseSystem, Signal

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# System 1: DayType — OBSERVING (per Master Matrix V1.0)
# ═══════════════════════════════════════════════════════════════════

class DayTypeSystem(BaseSystem):
    """System 1: Day Type classification engine.

    REAL S1 path: main.py bar_router.subscribe("5min", _day_type_on_bar)
    which enriches bars with Sierra IB/session_min and feeds
    app.state.day_type_machine.process_bar().

    This wrapper is DISCONNECTED — the EventDispatcher subscription to
    cumulative_delta/volume_profile was a dead path (CVD/VP payloads lack
    OHLC/IB → BarInput zeros → state machine stuck at A1). See VERIFY_DAYTYPE.
    """

    subscribed_streams: List[str] = []  # DISCONNECTED — real S1 in main.py
    system_id: int = 1
    name: str = "day_type"

    def __init__(self) -> None:
        # T-220 (2026-09-01): this wrapper used to build a SECOND live
        # DayTypeStateMachine at boot (app.py:init_event_dispatcher registers
        # DayTypeSystem() in the trading process). It is never fed — the class
        # is DISCONNECTED (subscribed_streams == []) — and its result is
        # discarded, so it was pure duplicate state sitting next to the
        # canonical app.state.day_type_machine. Now built lazily and loudly:
        # if this path ever comes alive, the log says so instead of a silent
        # second brain appearing. The canonical machine stays main.py:228.
        from backend.v9.systems.day_type.schemas import BarInput
        self._machine = None
        self._BarInput = BarInput

    def _get_machine(self):
        if self._machine is None:
            from backend.v9.systems.day_type.state_machine import DayTypeStateMachine
            logger.warning(
                "[DayTypeSystem] building a SECOND DayTypeStateMachine — this "
                "wrapper is supposed to be DISCONNECTED (subscribed_streams=%s). "
                "The canonical machine is app.state.day_type_machine (main.py).",
                self.subscribed_streams)
            self._machine = DayTypeStateMachine()
        return self._machine

    def analyze(self, stream_name: str, bar: dict) -> Optional[Signal]:
        """Process bar through day type state machine.

        Returns a Signal when the state machine locks on a day type
        with high confidence and the playbook suggests a trade.
        """
        try:
            bar_input = self._BarInput(
                ts=bar.get("ts", 0),
                session_min=bar.get("session_min", 0),
                open=bar.get("o", bar.get("open", 0)),
                high=bar.get("h", bar.get("high", 0)),
                low=bar.get("l", bar.get("low", 0)),
                close=bar.get("c", bar.get("close", 0)),
                volume=bar.get("vol", bar.get("volume", 0)),
                pd_high=bar.get("pd_high"),
                pd_low=bar.get("pd_low"),
                pd_close=bar.get("pd_close"),
                pd_settle=bar.get("pd_settle"),
                overnight_high=bar.get("overnight_high"),
                overnight_low=bar.get("overnight_low"),
                atr=bar.get("atr"),
                ib_high=bar.get("ib_high"),
                ib_low=bar.get("ib_low"),
                extensions_up=bar.get("extensions_up", 0),
                extensions_down=bar.get("extensions_down", 0),
                returned_to_range=bar.get("returned_to_range", False),
            )

            state = self._get_machine().process_bar(bar_input)

            # D-090: S1 = OBSERVER per Registry — classification continues,
            # but Signal generation is blocked. Remove this guard to re-enable
            # S1 firing (requires a new D-decision).
            return None

        except Exception:
            logger.exception("[DayTypeSystem] analyze failed for stream %s", stream_name)

        return None


# ═══════════════════════════════════════════════════════════════════
# System 3: Footprint — FIRING (per Master Matrix V1.0 / Constitution V3 D-049)
# ═══════════════════════════════════════════════════════════════════

class TickReversalSystem(BaseSystem):
    """System 3: Footprint (order flow analysis) — FIRING system.

    Subscribed to tick_reversal_15, tick_reversal_12, and footprint streams.
    Detects absorption, stacked imbalance, sweep-return, exhaustion signals.
    NOTE: class name kept as TickReversalSystem for backward compat with
    EventDispatcher registration. System 3 = Footprint per Master Matrix.
    """

    subscribed_streams: List[str] = ["tick_reversal_15", "tick_reversal_12", "footprint"]
    system_id: int = 3
    name: str = "footprint"

    def __init__(self) -> None:
        from backend.v9.systems.tick_reversal.signal_engine import detect_all_signals
        from backend.v9.systems.tick_reversal.schemas import BarInput
        self._detect_all_signals = detect_all_signals
        self._BarInput = BarInput
        self._recent_bars: List[dict] = []

    def analyze(self, stream_name: str, bar: dict) -> Optional[Signal]:
        """Process bar through signal engine. Observer: always returns None."""
        try:
            tick_size = 15
            if stream_name == "tick_reversal_12":
                tick_size = 12

            bar_input = self._BarInput(
                ts=str(bar.get("ts", "")),
                o=bar.get("o", bar.get("open", 0)),
                h=bar.get("h", bar.get("high", 0)),
                l=bar.get("l", bar.get("low", 0)),
                c=bar.get("c", bar.get("close", 0)),
                vol=bar.get("vol", bar.get("volume", 0)),
                ask_vol=bar.get("ask_vol", 0),
                bid_vol=bar.get("bid_vol", 0),
                delta=bar.get("delta"),
                tick_size=tick_size,
                footprint=bar.get("footprint"),
            )

            self._recent_bars.append(bar_input)
            # Bounded buffer
            if len(self._recent_bars) > 200:
                self._recent_bars = self._recent_bars[-150:]

            footprint_data = bar.get("footprint") if stream_name == "footprint" else None
            self._detect_all_signals(self._recent_bars, footprint_data=footprint_data)

        except Exception:
            logger.exception("[Footprint/S3] analyze failed for stream %s", stream_name)

        # Observer: never returns a trade signal
        return None


# ═══════════════════════════════════════════════════════════════════
# System 4: Woodies — Firing
# ═══════════════════════════════════════════════════════════════════

class WoodiesSystem(BaseSystem):
    """System 4: Woodies CCI pattern detection.

    Subscribed to woodies_5min stream (D-074).
    Runs 8 CCI pattern detectors and generates trade signals.
    """

    subscribed_streams: List[str] = ["woodies_5min"]
    system_id: int = 4
    name: str = "woodies"

    def __init__(self) -> None:
        from backend.v9.systems.woodies.pattern_engine import detect_all_patterns
        from backend.v9.systems.woodies.schemas import WoodiesBar
        self._detect_all_patterns = detect_all_patterns
        self._WoodiesBar = WoodiesBar
        self._bar_history: List = []

    def analyze(self, stream_name: str, bar: dict) -> Optional[Signal]:
        """Process bar through Woodies pattern engine. Returns Signal on pattern."""
        try:
            ohlc = bar.get("ohlc", {})
            woodies_bar = self._WoodiesBar(
                ts=bar.get("ts", 0),
                open=ohlc.get("o", bar.get("o", bar.get("open", 0))),
                high=ohlc.get("h", bar.get("h", bar.get("high", 0))),
                low=ohlc.get("l", bar.get("l", bar.get("low", 0))),
                close=ohlc.get("c", bar.get("c", bar.get("close", 0))),
                volume=ohlc.get("vol", bar.get("vol", bar.get("volume", 0))),
                cci_14=bar.get("cci_14", 0),
                cci_6_tcci=bar.get("cci_6_tcci", 0),
                ema_34=bar.get("ema_34", 0),
                lsma_value=bar.get("lsma_value", 0),
                swi_value=bar.get("swi_value", 0),
                czi_value=bar.get("czi_value", 0),
                trend_state=bar.get("trend_state", "GRAY"),
                predictor_next_cci=bar.get("predictor_next_cci", 0),
                zlr_detected=bar.get("zlr_detected", False),
                zlr_direction=bar.get("zlr_direction", "NONE"),
            )

            self._bar_history.append(woodies_bar)
            # Bounded buffer
            if len(self._bar_history) > 200:
                self._bar_history = self._bar_history[-150:]

            patterns = self._detect_all_patterns(self._bar_history)

            if patterns:
                best = max(patterns, key=lambda p: p.confidence)

                return Signal(
                    system_id=self.system_id,
                    classification=best.pattern_id,
                    direction=best.direction,
                    confidence=best.confidence,
                    entry_price=best.entry_price if best.entry_price else None,
                    stop=best.stop if best.stop else None,
                    targets=best.targets if best.targets else None,
                    metadata={
                        "pattern_id": best.pattern_id,
                        "patterns_detected": len(patterns),
                    },
                )

        except Exception:
            logger.exception("[WoodiesSystem] analyze failed for stream %s", stream_name)

        return None


# ═══════════════════════════════════════════════════════════════════
# System 5: TPO — Observer (no trade signals)
# ═══════════════════════════════════════════════════════════════════

class TPOSystem(BaseSystem):
    """System 5: TPO profile observer.

    Subscribed to volume_profile stream.
    Updates POC/VAH/VAL levels. Observer: does NOT generate trade signals.
    """

    subscribed_streams: List[str] = ["volume_profile"]
    system_id: int = 5
    name: str = "tpo"

    def __init__(self) -> None:
        from backend.v9.systems.tpo.levels import compute_poc, compute_value_area
        from backend.v9.systems.tpo.schemas import TPOLevel, TPOConfig
        self._compute_poc = compute_poc
        self._compute_value_area = compute_value_area
        self._TPOLevel = TPOLevel
        self._config = TPOConfig()
        self.poc: Optional[float] = None
        self.vah: Optional[float] = None
        self.val: Optional[float] = None

    def analyze(self, stream_name: str, bar: dict) -> Optional[Signal]:
        """Update POC/VAH/VAL from volume profile data. Observer: returns None.

        Accepts two shapes for ``b['levels']``:
          1. Legacy dict ``{price_str: {price, letters}}`` (pre-2026-05-22).
          2. Sierra-canonical list ``[{p, v, pct, poc, va}, ...]`` (current
             ``volume_profile.json::profiles[].levels``). Normalized here so
             a single downstream code path produces the POC/VAH/VAL.

        Previously this method assumed dict — when the bars POST handler
        started dispatching the actual Sierra-shape profile entries on
        2026-05-22, this raised ``AttributeError: 'list' object has no
        attribute 'items'`` (P31 Phase 1 regression — fixed inline).
        """
        try:
            bars_data = bar.get("bars", [bar])
            for b in bars_data:
                levels_raw = b.get("levels", {})
                if not levels_raw:
                    continue

                # Normalize Sierra list shape into the legacy dict shape so
                # the rest of the loop stays identical.
                if isinstance(levels_raw, list):
                    converted: dict = {}
                    for entry in levels_raw:
                        if not isinstance(entry, dict):
                            continue
                        price = entry.get("p")
                        if price is None:
                            continue
                        # Sierra doesn't expose TPO letters per price — use a
                        # synthetic single-letter list so `_compute_poc` /
                        # `_compute_value_area` still vote by volume.
                        vol = entry.get("v") or 0
                        letters_count = max(1, int(vol))
                        converted[str(price)] = {
                            "price": float(price),
                            "letters": ["A"] * letters_count,
                        }
                    levels_raw = converted

                levels = {}
                for key, val in levels_raw.items():
                    if isinstance(val, dict):
                        levels[key] = self._TPOLevel(
                            price=val.get("price", float(key)),
                            letters=val.get("letters", []),
                        )

                if levels:
                    poc_price, _count = self._compute_poc(levels)
                    self.poc = poc_price
                    vah, val_price = self._compute_value_area(levels, poc_price, self._config)
                    self.vah = vah
                    self.val = val_price

        except Exception:
            logger.exception("[TPOSystem] analyze failed for stream %s", stream_name)

        # Observer: never returns a trade signal
        return None


# ═══════════════════════════════════════════════════════════════════
# System 6: Killzone — Gate (time-based, no data streams)
# ═══════════════════════════════════════════════════════════════════

class KillzoneSystem(BaseSystem):
    """System 6: Killzone time-based gate.

    No subscribed streams (time-based, not data-driven).
    Checks current time against the killzone schedule.
    Gate: controls whether firing systems can execute.
    """

    subscribed_streams: List[str] = []
    system_id: int = 6
    name: str = "killzone"

    def __init__(self) -> None:
        from backend.v9.systems.killzone.gate import is_gate_open
        from backend.v9.systems.killzone.detector import get_killzone_status
        self._is_gate_open = is_gate_open
        self._get_killzone_status = get_killzone_status
        self.gate_open: bool = False
        self.current_zone: Optional[str] = None

    def analyze(self, stream_name: str, bar: dict) -> Optional[Signal]:
        """Check killzone status. Gate: always returns None."""
        try:
            self.gate_open = self._is_gate_open()
            status = self._get_killzone_status()
            self.current_zone = status.get("current_killzone")
        except Exception:
            logger.exception("[KillzoneSystem] analyze failed for stream %s", stream_name)

        # Gate: never returns a trade signal
        return None
