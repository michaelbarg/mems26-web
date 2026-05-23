"""Trade price excursion from v9_bars_5min (Hi/Lo during trade, MFE/MAE, T1 proximity)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy.orm import Session

from backend.v9.db.models.bars_5min import V9Bar5Min
from backend.v9.services.trade_context import _valid_target

BarHL = Tuple[float, float]  # (high, low)
BarTsHL = Tuple[datetime, float, float]  # (ts, high, low)


def _utc(ts: Any) -> Optional[datetime]:
    if ts is None:
        return None
    if isinstance(ts, str):
        try:
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            return None
    if not isinstance(ts, datetime):
        return None
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


def _empty_excursion() -> Dict[str, Any]:
    return {
        "price_high": None,
        "price_low": None,
        "mfe_pts": None,
        "mae_pts": None,
        "t1_closest_pts": None,
        "t1_at_mfe_pts": None,
        "t1_reached": None,
        "bars_count": 0,
    }


def _fetch_bar_hl(db: Session, start: datetime, end: datetime) -> List[BarHL]:
    return [(h, l) for _, h, l in _fetch_bar_ts_hl(db, start, end)]


def _fetch_bar_ts_hl(db: Session, start: datetime, end: datetime) -> List[BarTsHL]:
    rows = (
        db.query(V9Bar5Min.ts, V9Bar5Min.high, V9Bar5Min.low)
        .filter(V9Bar5Min.ts >= start, V9Bar5Min.ts <= end)
        .order_by(V9Bar5Min.ts)
        .all()
    )
    out: List[BarTsHL] = []
    for ts, h, l in rows:
        t = _utc(ts)
        if t is not None:
            out.append((t, float(h), float(l)))
    return out


def prefetch_bars_for_trades(db: Session, trades: Sequence[Any]) -> List[BarTsHL]:
    """One DB query for journal batch — filter per trade in compute_trade_excursion."""
    starts: List[datetime] = []
    ends: List[datetime] = []
    for trade in trades:
        start, end = _trade_window(trade)
        if start is not None:
            starts.append(start)
            ends.append(end)
    if not starts:
        return []
    return _fetch_bar_ts_hl(db, min(starts), max(ends))


def _bars_hl_in_window(all_bars: Sequence[BarTsHL], start: datetime, end: datetime) -> List[BarHL]:
    return [(h, l) for ts, h, l in all_bars if start <= ts <= end]


def _trade_window(trade) -> Tuple[Optional[datetime], datetime]:
    """Bar window: earliest entry/hit ts → exit or now (handles late DB entry_ts)."""
    stamps: List[datetime] = []
    for attr in ("entry_ts", "t1_hit_ts", "t2_hit_ts", "t3_hit_ts", "stop_hit_ts"):
        ts = _utc(getattr(trade, attr, None))
        if ts is not None:
            stamps.append(ts)
    if not stamps:
        return None, datetime.now(timezone.utc)
    start = min(stamps)
    end = _utc(trade.exit_ts) or datetime.now(timezone.utc)
    if end < start:
        end = start
    return start, end


def compute_trade_excursion(
    trade,
    db: Optional[Session] = None,
    *,
    bars: Optional[Sequence[BarHL]] = None,
) -> Dict[str, Any]:
    """Hi/Lo in trade window from 5m bars; MFE/MAE in points from entry; T1 proximity."""
    entry = trade.entry_price
    if entry is None:
        return _empty_excursion()

    if bars is None:
        start_ts, end_ts = _trade_window(trade)
        if start_ts is None:
            return _empty_excursion()
        if db is None:
            return _empty_excursion()
        bars = _fetch_bar_hl(db, start_ts, end_ts)

    if not bars:
        return _empty_excursion()

    price_high = max(h for h, _ in bars)
    price_low = min(l for _, l in bars)
    direction = trade.direction
    entry_f = float(entry)

    if direction == "LONG":
        mfe_pts = round(max(0.0, price_high - entry_f), 2)
        mae_pts = round(max(0.0, entry_f - price_low), 2)
    else:
        mfe_pts = round(max(0.0, entry_f - price_low), 2)
        mae_pts = round(max(0.0, price_high - entry_f), 2)

    t1 = _valid_target(trade.t1)
    t1_closest_pts: Optional[float] = None
    t1_at_mfe_pts: Optional[float] = None
    t1_reached: Optional[bool] = None

    if t1 is not None:
        per_bar: List[float] = []
        for hi, lo in bars:
            if direction == "LONG":
                per_bar.append(max(0.0, t1 - hi))
            else:
                per_bar.append(max(0.0, lo - t1))
        t1_closest_pts = round(min(per_bar), 2)
        t1_reached = trade.t1_hit_ts is not None or t1_closest_pts == 0.0
        if direction == "LONG":
            t1_at_mfe_pts = round(max(0.0, t1 - price_high), 2)
        else:
            t1_at_mfe_pts = round(max(0.0, price_low - t1), 2)

    return {
        "price_high": round(price_high, 2),
        "price_low": round(price_low, 2),
        "mfe_pts": mfe_pts,
        "mae_pts": mae_pts,
        "t1_closest_pts": t1_closest_pts,
        "t1_at_mfe_pts": t1_at_mfe_pts,
        "t1_reached": t1_reached,
        "bars_count": len(bars),
    }
