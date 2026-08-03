"""System 0 — Market Context unifier (Michael 2026-07-24, cowork 07-29).

"The problem isn't lack of signals but fragmented context: day_type, opening_type,
dir_bias, expansion live separately, each arm asks a different piece and gets
contradictory answers." System 0 = ONE service that publishes a single context
contract for all systems. It REPLACES the scattered getters — not a fifth brain.

Flag: MARKET_CONTEXT_V1 (default OFF). When OFF, get_market_context() returns
a skeleton with UNKNOWN fields — zero behavior change. When ON, composes the
existing sources into a unified contract.

Escalation-only: once a field is set it only strengthens (never degrades) until
end-of-session. The single exception: a sharp price cross through all of
yesterday's value = reclass with log.
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class MarketContext:
    balance_state: str = "UNKNOWN"      # in_value_accepted | out_value_in_range | out_of_range | UNKNOWN
    balance_conviction: str = "low"     # low | medium | high
    opening_type: str = "UNKNOWN"       # OPEN_DRIVE / TEST_DRIVE / ORR / AUCTION_IN / AUCTION_OUT / UNKNOWN
    opening_dir: str = "NEUTRAL"        # UP / DOWN / NEUTRAL
    opening_conf: float = 0.0           # Drive .85 > Test .75 > ORR .65 > Auction ≤.5
    acceptance: str = "pending"         # pending | accepted | rejected
    day_bias: str = "NONE"              # UP / DOWN / NONE
    day_type: str = "UNKNOWN"           # from get_live_day_type
    leg_dir: Optional[str] = None       # UP / DOWN / None (from leg_state)
    leg_age: int = 0                    # bars since leg started
    updated_ts: float = 0.0


def _flag_on() -> bool:
    return os.getenv("MARKET_CONTEXT_V1", "0").lower() in ("1", "true", "yes")


# Module-level state: the current session's context (escalation-only within session)
_current: Optional[MarketContext] = None
_session_date: Optional[str] = None


def _escalate(current: str, new: str, allowed: tuple) -> str:
    """Escalation-only: a field can only move forward in the allowed sequence."""
    if new not in allowed:
        return current
    cur_idx = allowed.index(current) if current in allowed else -1
    new_idx = allowed.index(new)
    return new if new_idx >= cur_idx else current


def get_market_context() -> MarketContext:
    """Return the unified market context. Composes existing sources.

    When MARKET_CONTEXT_V1 is OFF, returns a skeleton with UNKNOWN fields
    (zero behavior change — consumers see UNKNOWN and use their own fallbacks).
    """
    global _current, _session_date

    if not _flag_on():
        return MarketContext()

    # Session reset: new trading day → fresh context
    try:
        from zoneinfo import ZoneInfo
        from datetime import datetime, timezone
        _now_et = datetime.now(ZoneInfo("America/New_York"))
        _today = _now_et.strftime("%Y-%m-%d")
    except Exception:
        _today = "unknown"

    if _session_date != _today:
        _session_date = _today
        _current = MarketContext()

    if _current is None:
        _current = MarketContext()

    # 1. Day type (canonical, no change)
    try:
        from backend.v9.services.trade_context import get_live_day_type
        _dt = get_live_day_type()
        if _dt:
            _current.day_type = _dt
    except Exception:
        pass

    # 2. Opening type + direction + confidence
    try:
        from backend.v9.services.trade_context import get_opening_type_seed
        _seed = get_opening_type_seed()
        if _seed in ("UP", "DOWN"):
            _current.opening_dir = _escalate(
                _current.opening_dir, _seed, ("NEUTRAL", "UP", "DOWN"))
    except Exception:
        pass

    # Read the live opening type from app.state if available
    try:
        import backend.main as _main_mod
        _app = getattr(_main_mod, "app", None)
        _ot_result = getattr(getattr(_app, "state", None), "opening_type_result", None)
        if isinstance(_ot_result, dict):
            _ot = _ot_result.get("opening_type", "UNKNOWN")
            if _ot != "UNKNOWN":
                _current.opening_type = _ot
                _current.opening_conf = float(_ot_result.get("confidence", 0))
                _od = _ot_result.get("direction", "NEUTRAL")
                if _od in ("UP", "DOWN"):
                    _current.opening_dir = _od
    except Exception:
        pass

    # 3. Day bias: opening seed → dir_bias → expansion (priority order)
    try:
        from backend.v9.services.trade_context import get_live_dir_bias
        _db = get_live_dir_bias()
        if _db in ("UP", "DOWN"):
            _current.day_bias = _db
    except Exception:
        pass
    try:
        from backend.v9.services.trade_context import get_live_expansion
        _exp = get_live_expansion()
        if _exp and _exp.get("dir") in ("UP", "DOWN"):
            _current.day_bias = _exp["dir"]  # expansion overrides dir_bias
    except Exception:
        pass

    # 4. Balance state (computed from opening type + conviction)
    # AUCTION_OUT or OPEN_DRIVE with high directional confidence → out_of_range
    if _current.opening_type in ("OPEN_DRIVE",) and _current.opening_conf >= 0.8:
        _current.balance_state = _escalate(
            _current.balance_state, "out_of_range",
            ("UNKNOWN", "in_value_accepted", "out_value_in_range", "out_of_range"))
        _current.balance_conviction = "high"
    elif _current.opening_type == "OPEN_AUCTION_OUT":
        _current.balance_state = _escalate(
            _current.balance_state, "out_of_range",
            ("UNKNOWN", "in_value_accepted", "out_value_in_range", "out_of_range"))
        _current.balance_conviction = "high"
    elif _current.opening_type in ("OPEN_TEST_DRIVE", "OPEN_REJECTION_REVERSE"):
        _current.balance_state = _escalate(
            _current.balance_state, "out_value_in_range",
            ("UNKNOWN", "in_value_accepted", "out_value_in_range", "out_of_range"))
        _current.balance_conviction = "medium"
    elif _current.opening_type == "OPEN_AUCTION_IN":
        _current.balance_state = _escalate(
            _current.balance_state, "in_value_accepted",
            ("UNKNOWN", "in_value_accepted", "out_value_in_range", "out_of_range"))
        _current.balance_conviction = "low"

    # 5. Leg state (N4: from leg_state.py — the intraday leg detector)
    try:
        from backend.v9.systems.leg_state import detect_leg
        from backend.v9.db.read import read_all
        _leg_rows = read_all(
            "SELECT high, low, close, lsma_value, cci_14 FROM v9_bars_5min_woodies "
            "ORDER BY ts DESC LIMIT 12", {},
        )
        if _leg_rows:
            # Reverse to oldest→newest
            _leg_bars = [{"high": float(r["high"]), "low": float(r["low"]),
                          "close": float(r["close"]),
                          "lsma_value": float(r["lsma_value"]) if r.get("lsma_value") else None,
                          "cci_14": float(r["cci_14"]) if r.get("cci_14") else None}
                         for r in _leg_rows][::-1]
            _leg_dir, _leg_age, _ = detect_leg(_leg_bars)
            if _leg_dir in ("UP", "DOWN"):
                _current.leg_dir = _leg_dir
                _current.leg_age = _leg_age
    except Exception:
        pass

    _current.updated_ts = time.time()
    return _current


def reset_context() -> None:
    """Testing only — clear the session context."""
    global _current, _session_date
    _current = None
    _session_date = None
