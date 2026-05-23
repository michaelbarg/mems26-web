"""Entry / target / exit legs for journal and trades UI."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.v9.services.trade_context import _valid_target
from backend.v9.services.trade_excursion import _utc


def _to_unix(ts) -> Optional[float]:
    dt = _utc(ts)
    if dt is None:
        return None
    return dt.timestamp()


def extract_trade_legs(trade) -> List[Dict[str, Any]]:
    """Ordered lifecycle: ENTRY → T1/T2/T3 hits → STOP/EXIT."""
    legs: List[Dict[str, Any]] = []

    if trade.entry_price is not None and trade.entry_ts is not None:
        legs.append({
            "event": "ENTRY",
            "price": float(trade.entry_price),
            "ts": _to_unix(trade.entry_ts),
        })

    for event, price_attr, ts_attr in (
        ("T1", "t1", "t1_hit_ts"),
        ("T2", "t2", "t2_hit_ts"),
        ("T3", "t3", "t3_hit_ts"),
    ):
        ts = getattr(trade, ts_attr, None)
        price = _valid_target(getattr(trade, price_attr, None))
        if ts is not None and price is not None:
            legs.append({"event": event, "price": price, "ts": _to_unix(ts)})

    if trade.stop_hit_ts is not None and trade.stop is not None:
        legs.append({
            "event": "STOP",
            "price": float(trade.stop),
            "ts": _to_unix(trade.stop_hit_ts),
        })

    if trade.exit_ts is not None:
        exit_p = trade.exit_price
        if exit_p is None and trade.exit_reason == "STOP_HIT" and trade.stop is not None:
            exit_p = trade.stop
        if exit_p is not None:
            legs.append({
                "event": "EXIT",
                "price": float(exit_p),
                "ts": _to_unix(trade.exit_ts),
                "reason": trade.exit_reason,
            })

    legs.sort(key=lambda x: x.get("ts") or 0)
    return legs
