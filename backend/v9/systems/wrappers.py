"""System wrappers — adapts each of the 6 V9 systems to BaseSystem interface.

Each wrapper:
- Declares subscribed_streams
- Implements analyze() by calling the existing detection/analysis code
- Gracefully handles missing data (returns None, never crashes)

System roles per Master Matrix V1.0:
  Firing (can generate trade Signals): 5-Min (2), Footprint (3), Woodies (4)
  Observer (no trade signals):         DayType (1), TPO (5), Killzone (6)

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

    Subscribed to cumulative_delta + volume_profile streams.
    Uses the 13-stage state machine to classify the trading day,
    then generates trade signals based on the playbook.
    """

    subscribed_streams: List[str] = ["cumulative_delta", "volume_profile"]
    system_id: int = 1
    name: str = "day_type"

    def __init__(self) -> None:
        from backend.v9.systems.day_type.state_machine import DayTypeStateMachine
        from backend.v9.systems.day_type.schemas import BarInput
        self._machine = DayTypeStateMachine()
        self._BarInput = BarInput

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

            state = self._machine.process_bar(bar_input)

            # Generate signal when locked with playbook
            if state.lock_state.value in ("LOCKED", "LOCKED_LOW_CONF") and state.playbook is not None:
                direction = "LONG"
                if state.behavior.value in ("TRENDING_DOWN",):
                    direction = "SHORT"

                return Signal(
                    system_id=self.system_id,
                    classification=state.day_type.value,
                    direction=direction,
                    confidence=state.confidence,
                    entry_price=bar.get("c", bar.get("close")),
                    metadata={
                        "stage": state.stage.value,
                        "playbook_strategy": state.playbook.strategy,
                        "lock_state": state.lock_state.value,
                    },
                )

        except Exception:
            logger.exception("[DayTypeSystem] analyze failed for stream %s", stream_name)

        return None


# ═══════════════════════════════════════════════════════════════════
# System 2: Chart5Min — Firing
# ═══════════════════════════════════════════════════════════════════

class Chart5MinSystem(BaseSystem):
    """System 2: 5-minute chart pattern detection.

    Subscribed to cumulative_delta (derives 5min bars).
    Runs tiered pattern detection and generates trade setups.
    """

    subscribed_streams: List[str] = ["cumulative_delta"]
    system_id: int = 2
    name: str = "chart_5min"

    def __init__(self) -> None:
        from backend.v9.systems.chart_5min.detector import Chart5MinDetector
        from backend.v9.systems.chart_5min.models import Bar
        self._detector = Chart5MinDetector()
        self._Bar = Bar

    def analyze(self, stream_name: str, bar: dict) -> Optional[Signal]:
        """Process bar through pattern detector. Returns Signal on setup."""
        try:
            bar_obj = self._Bar(
                ts=bar.get("ts", 0),
                o=bar.get("o", bar.get("open", 0)),
                h=bar.get("h", bar.get("high", 0)),
                l=bar.get("l", bar.get("low", 0)),
                c=bar.get("c", bar.get("close", 0)),
                vol=bar.get("vol", bar.get("volume", 0)),
                poc_price=bar.get("poc_price", 0),
                vah=bar.get("vah", 0),
                val=bar.get("val", 0),
            )

            setup = self._detector.process_bar(bar_obj)
            if setup is not None:
                targets = []
                if setup.t1 is not None:
                    targets.append(setup.entry_zone or 0.0)
                if setup.t2 is not None:
                    targets.append(setup.entry_zone or 0.0)
                if setup.t3 is not None:
                    targets.append(setup.entry_zone or 0.0)

                return Signal(
                    system_id=self.system_id,
                    classification=setup.classification or "PATTERN",
                    direction=setup.direction or "LONG",
                    confidence=setup.pattern.completion if setup.pattern else 0.5,
                    entry_price=setup.entry_zone,
                    stop=setup.stop_zone,
                    targets=targets if targets else None,
                    metadata={
                        "pattern_id": setup.pattern.pattern_id if setup.pattern else None,
                        "sizing": setup.sizing,
                        "is_first_hour": setup.is_first_hour,
                    },
                )

        except Exception:
            logger.exception("[Chart5MinSystem] analyze failed for stream %s", stream_name)

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
            logger.exception("[TickReversalSystem] analyze failed for stream %s", stream_name)

        # Observer: never returns a trade signal
        return None


# ═══════════════════════════════════════════════════════════════════
# System 4: Woodies — Firing
# ═══════════════════════════════════════════════════════════════════

class WoodiesSystem(BaseSystem):
    """System 4: Woodies CCI pattern detection.

    Subscribed to woodies_30min stream.
    Runs 8 CCI pattern detectors and generates trade signals.
    """

    subscribed_streams: List[str] = ["woodies_30min"]
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
        """Update POC/VAH/VAL from volume profile data. Observer: returns None."""
        try:
            bars_data = bar.get("bars", [bar])
            for b in bars_data:
                levels_raw = b.get("levels", {})
                if not levels_raw:
                    continue

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
