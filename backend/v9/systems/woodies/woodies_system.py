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

            self.current_state.update({
                "cci_current": round(cci_value, 2),
                "cci_previous": round(prev_cci, 2) if prev_cci is not None else None,
                "signal": signal_type,
                "direction": direction,
                "strength": strength,
                "buffer_size": len(self.bar_buffer),
            })

            self.last_cci = cci_value

            mode = getattr(event, 'mode', 'LIVE')
            if mode == "LIVE" and signal_type != "NEUTRAL":
                self._write_signal(event, cci_value, prev_cci, signal_type, direction, strength)
        except Exception as e:
            logger.error(f"WoodiesSystem.process_bar error: {e}", exc_info=True)

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

    def _write_signal(self, event, current, previous, signal_type, direction, strength):
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                """INSERT OR IGNORE INTO v9_woodies_signals
                (ts, bar_id, cci_14, cci_prev, signal_type, direction, strength,
                 reasoning, session, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    getattr(event, 'ts', ''), getattr(event, 'bar_id', ''),
                    current, previous, signal_type, direction, strength,
                    f"CCI {previous:.1f} -> {current:.1f} = {signal_type}" if previous is not None else f"CCI={current:.1f}",
                    getattr(event, 'session', 'UNKNOWN'),
                    datetime.utcnow().isoformat(),
                ),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Woodies signal write failed: {e}")

    def get_current(self) -> dict:
        return dict(self.current_state)
