"""Risk checks per 3-Mode Spec V3 section 5.

LIVE-only strict checks:
  - Daily loss cap: $250
  - Max trades/day: 5
  - Max position: 2 contracts
  - Time filter: NO new trades after 14:30 ET
  - News block: FOMC/CPI/NFP ±10 min (placeholder)
  - Consecutive loss limit: 2 → STOP DAY
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Risk caps
DAILY_LOSS_CAP = 250.0
MAX_TRADES_PER_DAY = 5
MAX_CONTRACTS = 2
CUTOFF_HOUR = 14
CUTOFF_MINUTE = 30
CONSECUTIVE_LOSS_LIMIT = 2


def passes_strict_checks(setup: dict, mode: str, gateway) -> bool:
    """Return True if the setup passes all risk checks for the given mode.

    Args:
        setup: Trade setup dict.
        mode: 'shadow', 'demo', or 'live'.
        gateway: TradingGateway instance for daily stats.

    Returns:
        True if trade is allowed, False if blocked.
    """
    # SHADOW and DEMO bypass strict checks
    if mode != "live":
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
