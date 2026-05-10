"""W12 Daily Quality Agent — EOD batch job that tags trades with quality grades.

ANALYTICAL only — does NOT gate trades. Sets V9Trade.quality field.
Reads completed trades (outcome is not null), computes quality dimensions,
writes back JSON with grade + dimension scores.

Must be IDEMPOTENT — rerunning same day produces same result.
"""

import logging
from datetime import date, datetime, time, timezone, timedelta
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from backend.v9.db.models.trades import V9Trade
from backend.v9.services.daily_quality_agent.scoring import (
    compute_grade,
    context_quality,
    execution_quality,
    outcome_quality,
    timing_quality,
)

logger = logging.getLogger(__name__)

# US Eastern timezone offset (standard: UTC-5, DST: UTC-4)
# For production, use pytz or zoneinfo. Here we use a fixed offset
# that the caller can override via _et_offset.
_ET_OFFSET_STANDARD = timedelta(hours=-5)
_ET_OFFSET_DST = timedelta(hours=-4)


def _utc_to_et_time(utc_dt: datetime) -> time:
    """Convert UTC datetime to Eastern Time time-of-day.

    Uses a simple DST rule: March second Sunday to November first Sunday.
    For production accuracy, use zoneinfo (Python 3.9+).
    """
    try:
        from zoneinfo import ZoneInfo
        et_dt = utc_dt.astimezone(ZoneInfo("America/New_York"))
        return et_dt.time()
    except ImportError:
        # Assume EDT (UTC-4) during trading season (March-November)
        month = utc_dt.month
        if 3 <= month <= 10:
            offset = _ET_OFFSET_DST
        else:
            offset = _ET_OFFSET_STANDARD
        et_dt = utc_dt + offset
        return et_dt.time()


class DailyQualityAgent:
    """EOD batch processor that grades completed trades.

    Usage:
        agent = DailyQualityAgent(db=session)
        results = agent.run_eod_batch(date(2026, 5, 10))
    """

    def __init__(self, db: Session):
        self._db = db

    def run_eod_batch(self, target_date: date) -> List[Dict]:
        """Process all completed trades for the given date.

        Queries V9Trade rows where:
        - outcome is not null (completed trades only)
        - entry_ts falls on target_date (UTC day boundaries)

        Computes quality dimensions per scoring module, writes back
        to V9Trade.quality as JSON.

        IDEMPOTENT: rerunning produces identical results because
        scoring is deterministic from trade fields.

        Args:
            target_date: The trading date to process.

        Returns:
            List of quality result dicts (one per graded trade).
        """
        trades = self._get_completed_trades(target_date)

        if not trades:
            logger.info("W12 EOD: no completed trades for %s", target_date)
            return []

        results = []
        for trade in trades:
            quality_data = self._score_trade(trade)
            trade.quality = quality_data
            results.append({
                "trade_id": trade.id,
                "grade": quality_data["grade"],
                "dimensions": quality_data["dimensions"],
            })

        self._db.flush()

        logger.info(
            "W12 EOD: graded %d trades for %s",
            len(results), target_date,
        )
        return results

    def _get_completed_trades(self, target_date: date) -> List[V9Trade]:
        """Fetch completed trades for the target date.

        Completed = outcome is not null.
        Date filter = entry_ts within UTC day boundaries.
        """
        day_start = datetime(
            target_date.year, target_date.month, target_date.day,
            0, 0, 0, tzinfo=timezone.utc,
        )
        day_end = datetime(
            target_date.year, target_date.month, target_date.day,
            23, 59, 59, tzinfo=timezone.utc,
        )

        return (
            self._db.query(V9Trade)
            .filter(
                V9Trade.outcome.isnot(None),
                V9Trade.entry_ts >= day_start,
                V9Trade.entry_ts <= day_end,
            )
            .all()
        )

    def _score_trade(self, trade: V9Trade) -> Dict:
        """Compute all quality dimensions for a single trade.

        Returns a dict suitable for V9Trade.quality JSON field:
        {
            "grade": "A",
            "dimensions": {
                "timing": 1.0,
                "execution": 0.95,
                "outcome": 1.0,
                "context": 0.75
            }
        }
        """
        # Timing quality — based on entry time in ET
        timing_score = 0.0
        if trade.entry_ts is not None:
            et_time = _utc_to_et_time(trade.entry_ts)
            timing_score = timing_quality(et_time.hour, et_time.minute)

        # Execution quality — slippage vs expected entry
        # Expected price from cross_context if available, else use entry_price
        expected_price = None
        if trade.cross_context and isinstance(trade.cross_context, dict):
            expected_price = trade.cross_context.get("expected_price")
        exec_score = execution_quality(
            entry_price=trade.entry_price or 0.0,
            expected_price=expected_price,
            stop_price=trade.stop or 0.0,
        )

        # Outcome quality
        outcome_score = outcome_quality(
            outcome=trade.outcome or "",
            exit_reason=trade.exit_reason,
        )

        # Context quality — cross-system agreement
        context_score = context_quality(trade.cross_context)

        dimensions = {
            "timing": timing_score,
            "execution": exec_score,
            "outcome": outcome_score,
            "context": context_score,
        }

        grade = compute_grade(dimensions)

        return {
            "grade": grade,
            "dimensions": dimensions,
        }
