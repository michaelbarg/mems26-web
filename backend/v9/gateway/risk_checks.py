"""Risk checks per 3-Mode Spec V3 section 5.

Configurable risk caps (env vars with defaults):
  - Daily loss cap: RISK_DAILY_LOSS_CAP (default $250)
  - Max trades/day: RISK_MAX_TRADES_DAY (default 5)
  - Time filter: NO new trades after 14:30 ET
  - Consecutive loss limit: RISK_CONSECUTIVE_LOSS_LIMIT (default 2) → STOP DAY

Applied in LIVE always. In SHADOW when RISK_CAPS_SHADOW=1 (flag, default OFF).
"""

import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)


def _env_float(key: str, default: float) -> float:
    try:
        return float(os.environ.get(key, str(default)))
    except (TypeError, ValueError):
        return default


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, str(default)))
    except (TypeError, ValueError):
        return default


# Risk caps — configurable via env vars
DAILY_LOSS_CAP = _env_float("RISK_DAILY_LOSS_CAP", 250.0)
MAX_TRADES_PER_DAY = _env_int("RISK_MAX_TRADES_DAY", 5)
MAX_CONTRACTS = 2
# No-new-live-entries cutoff (ET). Michael ruling 2026-07-19: moved 14:30 → 15:30 ET
# (= 22:30 IL), i.e. block only the LAST 30 MINUTES instead of the last 90.
# Evidence (07-17 shadow book): the old 14:30 cutoff sent 4 shadow trades past it —
# 3 winning S4 shorts (+$148.75) and 1 losing S2 long (−$86.25) = net +$62.50 that the
# cutoff cost us. The losing long was a counter-trend entry that the OTHER gates should
# catch (not a time gate's job). 15:30 still preserves close-of-session discipline.
# Now env-tunable (was hardcoded) so future changes need no code edit — RULED-enforced.
CUTOFF_HOUR = _env_int("RISK_CUTOFF_HOUR_ET", 15)
CUTOFF_MINUTE = _env_int("RISK_CUTOFF_MINUTE_ET", 30)
CONSECUTIVE_LOSS_LIMIT = _env_int("RISK_CONSECUTIVE_LOSS_LIMIT", 2)


def passes_strict_checks(setup: dict, mode: str, gateway) -> bool:
    """Return True if the setup passes all risk checks for the given mode.

    Args:
        setup: Trade setup dict.
        mode: 'shadow', 'demo', or 'live'.
        gateway: TradingGateway instance for daily stats.

    Returns:
        True if trade is allowed, False if blocked.
    """
    # SHADOW bypass unless RISK_CAPS_SHADOW=1
    if mode != "live":
        if os.environ.get("RISK_CAPS_SHADOW", "0").lower() not in ("1", "true", "yes"):
            return True

    # Time filter: no new trades after 14:30 ET
    try:
        from zoneinfo import ZoneInfo
        et_now = datetime.now(ZoneInfo("America/New_York"))
    except ImportError:
        import pytz
        et_now = datetime.now(pytz.timezone("US/Eastern"))

    if et_now.hour > CUTOFF_HOUR or (et_now.hour == CUTOFF_HOUR and et_now.minute >= CUTOFF_MINUTE):
        logger.info("[RiskCheck] BLOCKED: past %d:%02d ET cutoff", CUTOFF_HOUR, CUTOFF_MINUTE)
        return False

    # Daily loss cap
    if gateway._daily_pnl <= -DAILY_LOSS_CAP:
        logger.info("[RiskCheck] BLOCKED: daily loss cap $%.0f reached (pnl=$%.2f)",
                     DAILY_LOSS_CAP, gateway._daily_pnl)
        return False

    # Max trades per day
    if gateway._daily_trades >= MAX_TRADES_PER_DAY:
        logger.info("[RiskCheck] BLOCKED: max %d trades/day reached", MAX_TRADES_PER_DAY)
        return False

    # Consecutive loss limit
    if gateway._consecutive_losses >= CONSECUTIVE_LOSS_LIMIT:
        logger.info("[RiskCheck] BLOCKED: %d consecutive losses → STOP DAY",
                     gateway._consecutive_losses)
        return False

    # News block — placeholder (needs news data source)
    # if _is_near_news_event():
    #     logger.info("[RiskCheck] BLOCKED: news event within ±10 min")
    #     return False

    return True
