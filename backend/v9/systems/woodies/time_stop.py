"""W-10 Time Stop Enforcer — Registry #11 LIVE blocker.

Enforces time-based exit for all 9 Woodies patterns.
Per-bar check: if bars_open >= limit_bars → emit TIME_STOP exit.

Default: time_stop_minutes=90 → limit_bars=18 (on 5-min bars).
Kill switch: time_stop_minutes=None or 0 → disabled.

Reference: MEMS26_SYSTEMS_DECISIONS_REGISTRY_2026-05-23.md §7.3 row 11
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger("woodies.time_stop")

_DISPATCHER_CONFIG_PATH = Path(__file__).parent / "config" / "dispatcher_config.yaml"


@dataclass(frozen=True)
class TimeStopResult:
    """Result of time stop check on a single open trade."""
    fired: bool
    bars_open: int
    limit_bars: int
    reason: str
    pattern_id: str
    trade_id: str = ""


class TimeStopEnforcer:
    """Enforces time-based exit per Registry #11.

    Per-bar check on all open Woodies trades.
    Emits WARNING log when bars_open >= limit_bars.
    Does NOT raise exceptions — returns result for caller to act on.
    """

    def __init__(
        self,
        time_stop_minutes: Optional[int] = 90,
        tick_minutes: int = 5,
    ) -> None:
        self.time_stop_minutes = time_stop_minutes
        self.tick_minutes = tick_minutes
        if time_stop_minutes and time_stop_minutes > 0:
            self.limit_bars = time_stop_minutes // tick_minutes
        else:
            self.limit_bars = 0

    def check(
        self,
        bars_open: int,
        pattern_id: str,
        trade_id: str = "",
    ) -> TimeStopResult:
        """Check time stop for a single open trade.

        Args:
            bars_open: how many bars since trade entry
            pattern_id: which pattern's trade (for logging)
            trade_id: trade identifier (for diagnostics)

        Returns:
            TimeStopResult with fired=True if time stop triggers.
        """
        if not self.time_stop_minutes or self.time_stop_minutes <= 0:
            return TimeStopResult(
                fired=False, bars_open=bars_open, limit_bars=0,
                reason="", pattern_id=pattern_id, trade_id=trade_id,
            )

        if bars_open >= self.limit_bars:
            logger.warning(
                "[woodies] TIME_STOP fired · bars_open=%d · limit=%d · pattern=%s",
                bars_open, self.limit_bars, pattern_id,
            )
            return TimeStopResult(
                fired=True,
                bars_open=bars_open,
                limit_bars=self.limit_bars,
                reason="TIME_STOP",
                pattern_id=pattern_id,
                trade_id=trade_id,
            )

        return TimeStopResult(
            fired=False,
            bars_open=bars_open,
            limit_bars=self.limit_bars,
            reason="",
            pattern_id=pattern_id,
            trade_id=trade_id,
        )


def load_time_stop_config(
    config_path: Optional[Path] = None,
) -> dict:
    """Load time_stop_minutes and tick_minutes from dispatcher_config.yaml.

    Returns dict with 'time_stop_minutes' and 'tick_minutes'.
    Falls back to Python defaults (90, 5) if YAML missing or invalid.
    """
    path = config_path or _DISPATCHER_CONFIG_PATH
    defaults = {"time_stop_minutes": 90, "tick_minutes": 5}

    if not path.exists():
        logger.warning(
            "[woodies.time_stop] Config not found at %s — using defaults (90 min / 5 min bars)",
            path,
        )
        return defaults

    try:
        with open(path, "r") as f:
            raw = yaml.safe_load(f)
        if not isinstance(raw, dict):
            logger.warning(
                "[woodies.time_stop] Config invalid (not a dict) — using defaults"
            )
            return defaults

        section = raw.get("time_stop", raw.get("pattern_dispatcher", {}))
        if not isinstance(section, dict):
            section = {}

        result = dict(defaults)
        if "time_stop_minutes" in section:
            tsm = section["time_stop_minutes"]
            result["time_stop_minutes"] = int(tsm) if tsm else None
        if "tick_minutes" in section:
            tm = section["tick_minutes"]
            if tm is not None:
                result["tick_minutes"] = int(tm)

        return result
    except Exception as e:
        logger.warning(
            "[woodies.time_stop] Config load error: %s — using defaults", e,
        )
        return defaults
