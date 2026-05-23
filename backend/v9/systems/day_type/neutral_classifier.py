"""neutral_classifier.py — NeuE vs NeuC classification per D-091.Q1."""
import logging
from typing import Optional
from .schemas import DayType

logger = logging.getLogger(__name__)

EDGE_TOLERANCE_PT = 0.25  # 1 MES tick

_fallback_logged_for_date: Optional[str] = None


def classify_neutral_subtype(
    *,
    session_open_price: Optional[float],
    prev_vah: Optional[float],
    prev_val: Optional[float],
    session_date: Optional[str] = None,
) -> DayType:
    """Classify Neutral day as Extreme or Center per D-091.Q1.

    Returns NeuC (fallback) if any input is None or VA is degenerate (<1 tick wide).
    Logs fallback at INFO level once per session_date.
    """
    global _fallback_logged_for_date

    # Degenerate VA check (zero-width or near-zero)
    if prev_vah is not None and prev_val is not None:
        if prev_vah - prev_val < EDGE_TOLERANCE_PT:
            _log_fallback(["degenerate_va"], session_date)
            return DayType.Neutral_Center

    if session_open_price is None or prev_vah is None or prev_val is None:
        missing = []
        if session_open_price is None:
            missing.append("session_open")
        if prev_vah is None:
            missing.append("prev_vah")
        if prev_val is None:
            missing.append("prev_val")
        _log_fallback(missing, session_date)
        return DayType.Neutral_Center

    at_or_above_vah = session_open_price >= (prev_vah - EDGE_TOLERANCE_PT)
    at_or_below_val = session_open_price <= (prev_val + EDGE_TOLERANCE_PT)

    if at_or_above_vah or at_or_below_val:
        return DayType.Neutral_Extreme
    return DayType.Neutral_Center


def _log_fallback(missing: list, session_date: Optional[str]) -> None:
    global _fallback_logged_for_date
    if session_date != _fallback_logged_for_date:
        logger.info(
            "[S1] NeuE/NeuC fallback to NeuC · missing=%s · session_date=%s",
            ",".join(missing), session_date,
        )
        _fallback_logged_for_date = session_date
