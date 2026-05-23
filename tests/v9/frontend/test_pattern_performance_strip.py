"""Mirror of PatternPerformanceStrip aggregation math (TypeScript).

Keep in sync with frontend/v9/src/v9/components/trades/PatternPerformanceStrip.tsx
`patternKey`, `aggregateByPattern`, `winRatePct`, `profitFactor`, `expectancy`.

Any drift between these and the TS reference will cause the journal Pattern
summary to disagree with what testers see in DB queries — those numbers are
how we decide whether to keep or kill a Woodies pattern before LIVE.
"""

from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional


_SYSTEM_RE = re.compile(r"^(system_\d+|S\d+)$", re.IGNORECASE)


def pattern_key(trade: Dict[str, Any]) -> str:
    raw = trade.get("pattern_id") or trade.get("classification") or trade.get("trigger") or ""
    v = str(raw).strip()
    if not v or v in ("-", "—") or _SYSTEM_RE.match(v):
        return "(none)"
    return v.upper()


def _empty_dir() -> Dict[str, float]:
    return {"total": 0, "wins": 0, "losses": 0, "net": 0.0}


def aggregate_by_pattern(trades: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for t in trades:
        key = pattern_key(t)
        row = out.get(key)
        if row is None:
            row = {
                "pattern": key,
                "total": 0,
                "closed": 0,
                "open": 0,
                "wins": 0,
                "losses": 0,
                "scratch": 0,
                "netUsd": 0.0,
                "grossWin": 0.0,
                "grossLoss": 0.0,
                "byDir": {"LONG": _empty_dir(), "SHORT": _empty_dir()},
            }
            out[key] = row
        row["total"] += 1
        is_closed = t.get("state") == "CLOSED" or (
            t.get("pnl_usd") is not None and t.get("outcome") != "OPEN"
        )
        if is_closed:
            row["closed"] += 1
        else:
            row["open"] += 1
        pnl = t.get("pnl_usd")
        counted = pnl is not None
        if counted:
            row["netUsd"] += pnl
            if pnl > 0:
                row["wins"] += 1
                row["grossWin"] += pnl
            elif pnl < 0:
                row["losses"] += 1
                row["grossLoss"] += abs(pnl)
            else:
                row["scratch"] += 1
        dir_ = "SHORT" if t.get("direction") == "SHORT" else "LONG"
        d = row["byDir"][dir_]
        d["total"] += 1
        if counted:
            d["net"] += pnl
            if pnl > 0:
                d["wins"] += 1
            elif pnl < 0:
                d["losses"] += 1
    return sorted(out.values(), key=lambda r: r["total"], reverse=True)


def win_rate_pct(wins: int, losses: int) -> Optional[float]:
    n = wins + losses
    return (wins / n) * 100 if n > 0 else None


def profit_factor(gross_win: float, gross_loss: float) -> Optional[float]:
    if gross_loss <= 0:
        return math.inf if gross_win > 0 else None
    return gross_win / gross_loss


def expectancy(net_usd: float, closed: int) -> Optional[float]:
    return net_usd / closed if closed > 0 else None


# ── Fixtures matching real V9 trade payload shape (from /api/v9/trades) ─────


def _t(**kw: Any) -> Dict[str, Any]:
    base = {
        "id": 0,
        "pattern_id": None,
        "trigger": None,
        "classification": None,
        "direction": "LONG",
        "state": "CLOSED",
        "outcome": None,
        "pnl_usd": None,
    }
    base.update(kw)
    return base


def test_pattern_key_uses_first_non_empty_source() -> None:
    assert pattern_key(_t(pattern_id="ZLR")) == "ZLR"
    assert pattern_key(_t(pattern_id=None, classification="hfe")) == "HFE"
    assert pattern_key(_t(pattern_id=None, trigger=" TLB ")) == "TLB"


def test_pattern_key_normalises_system_placeholders_to_none() -> None:
    """system_4 / S4 are placeholders TradeManager writes when no pattern fired."""
    assert pattern_key(_t(trigger="system_4")) == "(none)"
    assert pattern_key(_t(trigger="S4")) == "(none)"
    assert pattern_key(_t(trigger="—")) == "(none)"
    assert pattern_key(_t()) == "(none)"


def test_aggregate_groups_and_sorts_by_total() -> None:
    trades = [
        _t(id=1, pattern_id="TLB", direction="LONG", outcome="WIN", pnl_usd=50.0),
        _t(id=2, pattern_id="TLB", direction="SHORT", outcome="LOSS", pnl_usd=-30.0),
        _t(id=3, pattern_id="ZLR", direction="LONG", outcome="LOSS", pnl_usd=-25.0),
        _t(id=4, pattern_id="TLB", direction="LONG", state="FILLED", outcome="OPEN"),
    ]
    rows = aggregate_by_pattern(trades)
    assert [r["pattern"] for r in rows] == ["TLB", "ZLR"]

    tlb = rows[0]
    assert tlb["total"] == 3
    assert tlb["closed"] == 2
    assert tlb["open"] == 1
    assert tlb["wins"] == 1
    assert tlb["losses"] == 1
    assert tlb["netUsd"] == 20.0
    assert tlb["grossWin"] == 50.0
    assert tlb["grossLoss"] == 30.0
    assert tlb["byDir"]["LONG"]["total"] == 2  # incl. the open one
    assert tlb["byDir"]["LONG"]["wins"] == 1
    assert tlb["byDir"]["LONG"]["losses"] == 0
    assert tlb["byDir"]["SHORT"]["total"] == 1
    assert tlb["byDir"]["SHORT"]["losses"] == 1


def test_win_rate_ignores_scratches_and_open_trades() -> None:
    assert win_rate_pct(3, 1) == 75.0
    assert win_rate_pct(0, 0) is None  # no closed-with-PnL trades yet
    assert win_rate_pct(1, 0) == 100.0
    assert win_rate_pct(0, 5) == 0.0


def test_profit_factor_handles_no_losers_and_no_winners() -> None:
    assert profit_factor(100.0, 50.0) == 2.0
    assert profit_factor(100.0, 0.0) == math.inf  # all winners, no losses yet
    assert profit_factor(0.0, 50.0) == 0.0
    assert profit_factor(0.0, 0.0) is None


def test_expectancy_is_dollar_per_closed_trade() -> None:
    assert expectancy(-200.0, 10) == -20.0
    assert expectancy(75.0, 5) == 15.0
    assert expectancy(50.0, 0) is None


def test_open_trades_dont_distort_pnl_or_win_rate() -> None:
    """An OPEN trade contributes to total/open count but never to PnL or W/L."""
    trades = [
        _t(id=1, pattern_id="HFE", outcome="WIN", pnl_usd=40.0),
        _t(id=2, pattern_id="HFE", state="FILLED", outcome="OPEN"),  # open
        _t(id=3, pattern_id="HFE", state="PENDING"),  # no pnl, no outcome
    ]
    rows = aggregate_by_pattern(trades)
    hfe = rows[0]
    assert hfe["total"] == 3
    assert hfe["closed"] == 1  # only the winner counts as closed
    assert hfe["open"] == 2
    assert hfe["wins"] == 1
    assert hfe["losses"] == 0
    assert hfe["netUsd"] == 40.0
    assert win_rate_pct(hfe["wins"], hfe["losses"]) == 100.0


def test_known_db_numbers_match_reference() -> None:
    """Sanity: hard-coded mini-snapshot reproducing the docs/ZLR row.

    From `sqlite3 mems26_local.db` aggregation (2026-05-21): ZLR has 28 total,
    2 wins, 26 losses, win_rate 7.1%, net -$750. Encode that as a regression
    so future TS edits to the aggregator can't silently change the displayed
    P&L for that pattern.
    """
    trades: List[Dict[str, Any]] = []
    for i in range(2):
        trades.append(
            _t(
                id=10 + i,
                pattern_id="ZLR",
                direction="LONG" if i % 2 == 0 else "SHORT",
                outcome="WIN",
                pnl_usd=37.5,  # placeholder per-win amount; aggregate matters
            )
        )
    for i in range(26):
        trades.append(
            _t(
                id=100 + i,
                pattern_id="ZLR",
                direction="LONG" if i % 2 == 0 else "SHORT",
                outcome="LOSS",
                pnl_usd=-(750 + 75) / 26,  # net -$750 after the +$75 winners
            )
        )
    rows = aggregate_by_pattern(trades)
    zlr = rows[0]
    assert zlr["pattern"] == "ZLR"
    assert zlr["total"] == 28
    assert zlr["wins"] == 2
    assert zlr["losses"] == 26
    assert round(zlr["netUsd"], 2) == -750.0
    wr = win_rate_pct(zlr["wins"], zlr["losses"])
    assert wr is not None and round(wr, 1) == 7.1
