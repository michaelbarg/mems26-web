"""System 4 — Woodies CCI Decision Maker (STANDALONE).

Computes CCI(14) on every bar.
Detects: Zero-Line Cross, 100/-100 cross, Trend mode.
Publishes signal events independently.
"""
import json
import logging
import sqlite3
from datetime import datetime
from typing import List, Optional, Dict

from backend.v9.systems.base.trading_system import BaseV9TradingSystem, HydrationResult, SystemType
from .cci import cci

logger = logging.getLogger(__name__)


class WoodiesSystem(BaseV9TradingSystem):
    system_id = 4
    name = "woodies"
    color = "#f97316"
    system_type = SystemType.FIRING

    def __init__(self, db_path: str = None):
        self.db_path = db_path or "/Users/michael/Downloads/mems26_web_git/data/mems26_local.db"
        self.bar_buffer: List[Dict] = []
        self.max_buffer = 50
        self.cci_period = 14
        self.last_cci: Optional[float] = None
        self._last_czi: Optional[str] = None
        self._last_swi: Optional[str] = None
        self._cci_history: List[float] = []
        self.current_state = {
            "running": False,
            "hydrated": False,
            "cci_current": None,
            "cci_previous": None,
            "signal": "NEUTRAL",
            "direction": None,
            "strength": 0,
            "buffer_size": 0,
        }

    def subscribed_bar_types(self) -> List[str]:
        return ["5min", "tick_reversal_15"]

    def hydrate(self) -> HydrationResult:
        self.current_state["running"] = True
        self.current_state["hydrated"] = True
        return HydrationResult(
            success=True,
            reached_state="ACTIVE",
            confidence=1.0,
            notes="Woodies CCI ready; subscribed via BarRouter",
        )

    def process(self, event: Dict) -> Optional[Dict]:
        return None

    async def process_bar(self, event) -> None:
        try:
            bar = dict(event.payload) if hasattr(event, 'payload') else dict(event)
            self.bar_buffer.append(bar)
            if len(self.bar_buffer) > self.max_buffer:
                self.bar_buffer.pop(0)

            cci_value = cci(self.bar_buffer, self.cci_period)
            if cci_value is None:
                self.current_state["buffer_size"] = len(self.bar_buffer)
                return

            prev_cci = self.last_cci
            signal_type, direction, strength = self._classify_signal(cci_value, prev_cci)

            # P-WCC-CORE.2: Zero Line context
            czi, swi = self._classify_zero_line_context(cci_value)
            self._last_czi = czi
            self._last_swi = swi

            # P-WCC-CORE.3: CCI history for persistence/pattern checks
            self._cci_history.append(cci_value)
            if len(self._cci_history) > 20:
                self._cci_history = self._cci_history[-20:]

            self.current_state.update({
                "cci_current": round(cci_value, 2),
                "cci_previous": round(prev_cci, 2) if prev_cci is not None else None,
                "signal": signal_type,
                "direction": direction,
                "strength": strength,
                "buffer_size": len(self.bar_buffer),
                "czi_state": czi,
                "swi_state": swi,
                "persistence_bars": min(len(self._cci_history), 20),
            })

            self.last_cci = cci_value
            bar_ts = getattr(event, 'ts', '')

            # P-WCC-CORE.3: TT 6-bar persistence
            tt_signal, tt_bars = self._check_trend_persistence()
            if tt_signal:
                self._fire_signal(tt_signal, bar_ts, event, cci_value, prev_cci, f"TT 6-bar trend ({tt_bars} bars)")

            # P-WCC-CORE.4: ZLR
            zlr = self._check_zlr()
            if zlr:
                self._fire_signal(zlr, bar_ts, event, cci_value, prev_cci, "Zero Line Reject")

            # P-WCC-CORE.5: TLB
            tlb = self._check_tlb()
            if tlb:
                self._fire_signal(tlb, bar_ts, event, cci_value, prev_cci, "Trend Line Break")

            mode = getattr(event, 'mode', 'LIVE')
            if mode == "LIVE" and signal_type != "NEUTRAL":
                self._write_signal(event, cci_value, prev_cci, signal_type, direction, strength)
        except Exception as e:
            logger.error(f"WoodiesSystem.process_bar error: {e}", exc_info=True)

    def _classify_zero_line_context(self, cci_val: float) -> tuple:
        """CZI ±100 / SWI ±200 zone classification."""
        czi = "CZI" if -100 < cci_val < 100 else "TREND_ZONE"
        swi = "SWI" if abs(cci_val) >= 200 else "NORMAL"
        return (czi, swi)

    def _classify_signal(self, current: float, previous: Optional[float]):
        if previous is None:
            if current > 100:
                return "OVERBOUGHT", "BEAR_CAUTION", 1
            if current < -100:
                return "OVERSOLD", "BULL_CAUTION", 1
            return "NEUTRAL", None, 0

        if previous <= 0 < current:
            return "ZLC_BULL", "LONG", 3
        if previous >= 0 > current:
            return "ZLC_BEAR", "SHORT", 3

        if previous < 100 <= current:
            return "OB_ENTER", "BEAR_WATCH", 2
        if previous > 100 >= current:
            return "OB_EXIT", "SHORT", 3
        if previous > -100 >= current:
            return "OS_ENTER", "BULL_WATCH", 2
        if previous < -100 <= current:
            return "OS_EXIT", "LONG", 3

        if current > 0 and previous > 0:
            return "TREND_BULL", "LONG_HOLD", 1
        if current < 0 and previous < 0:
            return "TREND_BEAR", "SHORT_HOLD", 1

        return "NEUTRAL", None, 0

    def _check_trend_persistence(self):
        """TT: 6-bar CCI persistence above/below zero."""
        cci_history = self._cci_history[-6:] if len(self._cci_history) >= 6 else self._cci_history
        if len(cci_history) < 6:
            return (None, len(cci_history))
        all_positive = all(v > 0 for v in cci_history)
        all_negative = all(v < 0 for v in cci_history)
        if all_positive:
            return ("TT_BULL", 6)
        if all_negative:
            return ("TT_BEAR", 6)
        return (None, 0)

    def _check_zlr(self):
        """ZLR: CCI approaches zero then rejects back in trend direction."""
        if len(self._cci_history) < 3:
            return None
        prev2, prev1, cur = self._cci_history[-3:]
        # Bull ZLR: was negative, crossed positive, stays in CZI zone bouncing up
        if prev2 < 0 and prev1 > 0 and 0 < cur < 100 and cur > prev1 * 0.5:
            return "ZLR_BULL"
        # Bear ZLR: was positive, crossed negative, stays in CZI zone dropping
        if prev2 > 0 and prev1 < 0 and -100 < cur < 0 and cur < prev1 * 0.5:
            return "ZLR_BEAR"
        return None

    def _check_tlb(self):
        """TLB: CCI breaks projected trendline by >20 points."""
        if len(self._cci_history) < 6:
            return None
        window = self._cci_history[-6:]
        cur = window[-1]
        slope = (window[-2] - window[0]) / 5
        projected = window[-2] + slope
        if window[-2] < 0 and cur > projected + 20:
            return "TLB_BULL"
        if window[-2] > 0 and cur < projected - 20:
            return "TLB_BEAR"
        return None

    def _fire_signal(self, signal_name, bar_ts, event, cci_value, prev_cci, reasoning):
        """Persist a core pattern signal (TT/ZLR/TLB) to DB."""
        mode = getattr(event, 'mode', 'LIVE')
        if mode != "LIVE":
            return
        self._last_signal = signal_name
        direction = "LONG" if "BULL" in signal_name else "SHORT"
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                """INSERT INTO v9_woodies_signals
                (ts, bar_id, cci_14, cci_prev, signal_type, direction, strength,
                 reasoning, session, created_at, czi_state, swi_state,
                 persistence_bars, signal_type_core, signal_confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    bar_ts, None,
                    cci_value, prev_cci, signal_name, direction, 4,
                    f"CCI {prev_cci:.1f} -> {cci_value:.1f} = {reasoning}" if prev_cci is not None else f"CCI={cci_value:.1f} {reasoning}",
                    getattr(event, 'session', 'UNKNOWN'),
                    datetime.utcnow().isoformat(),
                    self._last_czi, self._last_swi,
                    min(len(self._cci_history), 20),
                    signal_name, 0.75,
                ),
            )
            conn.commit()
            conn.close()
            logger.info("[Woodies] %s signal fired: CCI=%.1f czi=%s swi=%s", signal_name, cci_value, self._last_czi, self._last_swi)
        except Exception as e:
            logger.warning(f"Woodies core signal write failed: {e}")

    def _write_signal(self, event, current, previous, signal_type, direction, strength):
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                """INSERT OR IGNORE INTO v9_woodies_signals
                (ts, bar_id, cci_14, cci_prev, signal_type, direction, strength,
                 reasoning, session, created_at,
                 czi_state, swi_state, persistence_bars)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    getattr(event, 'ts', ''), getattr(event, 'bar_id', ''),
                    current, previous, signal_type, direction, strength,
                    f"CCI {previous:.1f} -> {current:.1f} = {signal_type}" if previous is not None else f"CCI={current:.1f}",
                    getattr(event, 'session', 'UNKNOWN'),
                    datetime.utcnow().isoformat(),
                    self._last_czi, self._last_swi,
                    min(len(self._cci_history), 20),
                ),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Woodies signal write failed: {e}")

    def get_current(self) -> dict:
        state = dict(self.current_state)
        state["czi_state"] = self._last_czi
        state["swi_state"] = self._last_swi
        state["persistence_bars"] = min(len(self._cci_history), 20)
        state["last_signal_type"] = getattr(self, '_last_signal', None)
        return state
