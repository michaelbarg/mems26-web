"""V9 API: chart replay aggregator (read-only).

GET /api/v9/chart/replay?date=YYYY-MM-DD → one bundle for marking a historical
trade's day, so the in-dashboard marking chart can show the SAME picture the
standalone marker tool had: 5-min bars (OHLCV + Woodies CCI), the CVD series,
the day's key levels (POC / VAH / VAL / IB high-low), and that day's trades.

Composes EXISTING canonical tables only — never synthesizes (Rule 1: null when
the source is silent). Additive and read-only; does not touch ingest, the
bridge, sc_study, or any existing market-data route (§7a).

Tables (verified 2026-06-15 against live PG):
  v9_bars_5min_woodies  — OHLCV + cci_14 + cci_6_tcci + trend_state per 5m bar
  v9_bars_5min          — cumulative_delta / poc_vol / vah / val per 5m bar
  v9_bars_cumulative_delta — CVD series (ts ISO string, delta, cumulative)
  v9_tpo_history        — 30-min POC/VAH/VAL/IB snapshots
  v9_tpo_sessions       — daily POC/VAH/VAL/IB fallback (trading_date)
  v9_trades             — the day's trades
"""

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Query

from backend.v9.db.read import read_all, read_one, read_scalar

router = APIRouter(prefix="/api/v9/chart", tags=["v9-chart-replay"])


def _iso(ts: Any) -> Optional[str]:
    if ts is None:
        return None
    if isinstance(ts, datetime):
        return ts.isoformat()
    return str(ts)


def _f(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


@router.get("/replay")
def chart_replay(date: str = Query(..., description="ET trading date, YYYY-MM-DD")):
    """Return {date, bars, cvd, levels, trades} for one ET trading date.

    Every numeric field is passed through as-is or null — no synthesis.
    """
    bars_rows = read_all(
        """
        SELECT w.ts AS ts, w.open AS o, w.high AS h, w.low AS l, w.close AS c,
               w.volume AS v, w.cci_14 AS cci, w.cci_6_tcci AS tcci,
               w.trend_state AS trend, f.cumulative_delta AS cum_delta
        FROM v9_bars_5min_woodies w
        LEFT JOIN v9_bars_5min f ON f.ts = w.ts AND f.symbol = w.symbol
        WHERE (w.ts AT TIME ZONE 'America/New_York')::date = :date
          AND w.symbol = 'MES'
        ORDER BY w.ts ASC
        """,
        {"date": date},
    )
    bars = [
        {
            "ts": _iso(r["ts"]), "o": _f(r["o"]), "h": _f(r["h"]), "l": _f(r["l"]),
            "c": _f(r["c"]), "v": _f(r["v"]), "cci": _f(r["cci"]), "tcci": _f(r["tcci"]),
            "trend": r["trend"], "cum_delta": _f(r["cum_delta"]),
        }
        for r in bars_rows
    ]

    # CVD — ts stored as ISO string; dedup by ts (bridge can double-insert).
    cvd_rows = read_all(
        """
        SELECT DISTINCT ts, delta, cumulative
        FROM v9_bars_cumulative_delta
        WHERE substring(ts, 1, 10) = :date
        ORDER BY ts ASC
        """,
        {"date": date},
    )
    seen: set = set()
    cvd = []
    for r in cvd_rows:
        ts = _iso(r["ts"])
        if ts in seen:
            continue
        seen.add(ts)
        cvd.append({"ts": ts, "d": _f(r["delta"]), "cum": _f(r["cumulative"])})

    # Levels — prefer last 30-min TPO snapshot of the day; fall back to session row.
    levels = read_one(
        """
        SELECT poc, vah, val, ib_high, ib_low
        FROM v9_tpo_history
        WHERE (ts AT TIME ZONE 'America/New_York')::date = :date
        ORDER BY ts DESC
        LIMIT 1
        """,
        {"date": date},
    )
    if not levels or all(levels.get(k) is None for k in ("poc", "vah", "val")):
        sess = read_one(
            """
            SELECT poc_price AS poc, vah_price AS vah, val_price AS val, ib_high, ib_low
            FROM v9_tpo_sessions
            WHERE trading_date = :date
            ORDER BY id DESC
            LIMIT 1
            """,
            {"date": date},
        )
        levels = sess or levels
    levels = {k: _f(v) for k, v in (levels or {}).items()}

    # Previous-day high/low + floor pivots (computed from the prior TRADING day's
    # bars — H/L/C). Never synthesized when the prior day has no bars (Rule 1).
    prior_date = read_scalar(
        "SELECT max((ts AT TIME ZONE 'America/New_York')::date) "
        "FROM v9_bars_5min_woodies WHERE (ts AT TIME ZONE 'America/New_York')::date < :date",
        {"date": date},
    )
    if prior_date is not None:
        pd_iso = prior_date.isoformat() if hasattr(prior_date, "isoformat") else str(prior_date)
        hlc = read_one(
            "SELECT max(high) AS h, min(low) AS l, "
            "(array_agg(close ORDER BY ts DESC))[1] AS c "
            "FROM v9_bars_5min_woodies "
            "WHERE (ts AT TIME ZONE 'America/New_York')::date = :pd",
            {"pd": pd_iso},
        )
        h, l, c = _f((hlc or {}).get("h")), _f((hlc or {}).get("l")), _f((hlc or {}).get("c"))
        levels["pdh"], levels["pdl"] = h, l
        if h is not None and l is not None and c is not None:
            pp = (h + l + c) / 3.0
            rng = h - l
            levels.update({
                "pp": round(pp, 2),
                "r1": round(2 * pp - l, 2), "s1": round(2 * pp - h, 2),
                "r2": round(pp + rng, 2), "s2": round(pp - rng, 2),
                "r3": round(h + 2 * (pp - l), 2), "s3": round(l - 2 * (h - pp), 2),
            })

    trades_rows = read_all(
        """
        SELECT id, firing_system, direction, pattern_id_at_entry AS pattern,
               entry_ts, entry_price, stop, t1, t2, t3,
               exit_ts, exit_price, exit_reason, outcome, pnl_usd
        FROM v9_trades
        WHERE (entry_ts AT TIME ZONE 'America/New_York')::date = :date
          AND is_synthetic = 0
        ORDER BY entry_ts ASC
        """,
        {"date": date},
    )
    trades = [
        {
            "id": r["id"], "firing_system": r["firing_system"], "direction": r["direction"],
            "pattern": r["pattern"], "entry_ts": _iso(r["entry_ts"]), "entry_price": _f(r["entry_price"]),
            "stop": _f(r["stop"]), "t1": _f(r["t1"]), "t2": _f(r["t2"]), "t3": _f(r["t3"]),
            "exit_ts": _iso(r["exit_ts"]), "exit_price": _f(r["exit_price"]),
            "exit_reason": r["exit_reason"], "outcome": r["outcome"], "pnl_usd": _f(r["pnl_usd"]),
        }
        for r in trades_rows
    ]

    return {
        "date": date,
        "counts": {"bars": len(bars), "cvd": len(cvd), "trades": len(trades)},
        "bars": bars,
        "cvd": cvd,
        "levels": levels,
        "trades": trades,
    }
