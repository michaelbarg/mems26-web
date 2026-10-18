"""T-527 (BRIEF §3.4, fix-agent 18.10) — scripts/broker_truth.py must LIST every live CLOSED trade.

02.10 (TASK_LOG T-527, run 174): `broker_truth --since 2026-09-01` reported "live trades 57 · matched 52"
while #955 #979 #1220 — SIERRA_FLAT, UNPRICED, inside the window — were not in the table at all.
Root (18.10): their entry_ts is NULL (a PENDING order POSITION_TRUTH closed as SIERRA_FLAT never
filled), and the candidate query filtered `entry_ts >= :s` — NULL fails the comparison, the row is
dropped silently. The matching loop also anchored on entry_ts (TypeError on None). Now the anchor is
coalesce(entry_ts, created_at): the row is listed as NEVER-FILLED with broker=None (never priced), and a
never-filled-in-the-books order that the broker DID fill (#3046, 05.10) is matched through created_at.
Second latent bug: a day with only manual round-trips raised KeyError in the per-day totals.
"""
import datetime as dt
import importlib.util
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
_spec = importlib.util.spec_from_file_location("broker_truth", os.path.join(ROOT, "scripts", "broker_truth.py"))
bt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bt)

UTC = dt.timezone.utc
T0 = dt.datetime(2026, 9, 8, 13, 40, 8, tzinfo=UTC)   # 16:40:08 IL — #1220's created_at


def _trade(tid, entry_ts, created_at, direction="SHORT", price=7701.0, pnl=None, reason="SIERRA_FLAT"):
    return {"id": tid, "mode": "live", "direction": direction, "entry_ts": entry_ts, "exit_ts": None,
            "created_at": created_at, "entry_price": price, "exit_price": None, "exit_reason": reason,
            "pnl_usd": pnl, "pnl_sierra": None, "pat": "OPENING_DRIVE", "contracts": 1}


def _events(order, direction, t_entry, t_exit, pnl, qty=1):
    """One broker round-trip: 0→qty (entry order) … qty→0 (exit order) + CLOSED_TRADE_PNL at the exit."""
    sign = 1 if direction == "LONG" else -1
    return [{"type": "POSITION_CHANGE", "order_id": order, "prev_qty": 0, "new_qty": sign * qty, "_t": t_entry},
            {"type": "POSITION_CHANGE", "order_id": order + 1, "prev_qty": sign * qty, "new_qty": 0, "_t": t_exit},
            {"type": "CLOSED_TRADE_PNL", "pnl": pnl, "_t": t_exit}]


def test_candidate_sql_anchors_on_coalesce_entry_ts_created_at():
    sql = " ".join(bt.TRADES_SQL.split()).lower()
    assert "coalesce(entry_ts, created_at) >= :s" in sql, "a NULL entry_ts must not drop the row"
    assert "mode='live' and state='closed'" in sql
    assert "created_at" in sql.split("from v9_trades")[0], "created_at must be selected (the anchor)"


def test_anchor_ts_falls_back_to_created_at():
    assert bt.anchor_ts({"entry_ts": None, "created_at": T0}) == T0
    assert bt.anchor_ts({"entry_ts": T0, "created_at": T0 - dt.timedelta(hours=1)}) == T0


def test_never_filled_row_is_listed_not_dropped_and_not_priced():
    """#1220's shape: created 16:40:08, SIERRA_FLAT 21 s later, no DLL ENTRY fill, no broker round-trip."""
    rows, unmatched = bt.match_trades([_trade(1220, None, T0)], journal=[], rts=[])
    assert [r["id"] for r in rows] == [1220]
    r = rows[0]
    assert r["filled"] is False and r["broker"] is None and r["match"] is None and r["delta"] is None
    assert r["day"] == "2026-09-08" and r["entry"] == "16:40"
    assert unmatched == []


def test_filled_row_matches_by_order_id_exactly_as_before():
    """Regression guard: the historical path (entry_ts set, journal ENTRY → order id → round-trip) is unchanged."""
    t_entry = T0 + dt.timedelta(minutes=15)
    journal = [(t_entry, {"kind": "ENTRY", "direction": "SHORT", "price": 7694.0, "order_id": 11042, "ts": 0})]
    rts = bt.round_trips(_events(11042, "SHORT", t_entry + dt.timedelta(seconds=2), t_entry + dt.timedelta(minutes=30), -42.5))
    rows, unmatched = bt.match_trades([_trade(1221, t_entry, t_entry, price=7694.0, pnl=-40.0, reason="STOP_HIT")], journal, rts)
    r = rows[0]
    assert r["filled"] is True and r["match"] == "order" and r["entry_order"] == 11042
    assert r["broker"] == -42.5 and r["delta"] == -2.5 and r["mixed"] is False and r["legs"] == 1
    assert unmatched == []


def test_never_filled_in_books_but_filled_at_broker_matches_through_created_at():
    """#3046 (05.10 19:25 GB100 LONG): entry_ts NULL in the books (closed by BRACKET_EXIT_ACTIVITY, −27.50)
    while the DLL journal has its ENTRY and the broker a +53.75 round-trip — invisible before T-527."""
    t_cr = dt.datetime(2026, 10, 5, 16, 25, 7, tzinfo=UTC)
    journal = [(t_cr + dt.timedelta(seconds=4), {"kind": "ENTRY", "direction": "LONG", "price": 7873.0, "order_id": 11408, "ts": 0})]
    rts = bt.round_trips(_events(11408, "LONG", t_cr + dt.timedelta(minutes=1), t_cr + dt.timedelta(minutes=80), 53.75))
    rows, unmatched = bt.match_trades([_trade(3046, None, t_cr, direction="LONG", price=7873.0, pnl=-27.5,
                                              reason="BRACKET_EXIT_ACTIVITY")], journal, rts)
    r = rows[0]
    assert r["filled"] is False and r["match"] == "order" and r["broker"] == 53.75 and r["delta"] == 81.25
    assert unmatched == []


def test_day_totals_manual_only_day_does_not_raise():
    rows = [{"day": "2026-09-02", "books": -10.0, "broker": -12.5}]
    unmatched = [{"day": "2026-08-25", "pnl": 2.5}, {"day": "2026-08-25", "pnl": -1.0}]
    days = bt.day_totals(rows, unmatched)
    assert days["2026-08-25"] == {"books": 0.0, "broker": 0.0, "n": 0, "matched": 0, "manual": 1.5}
    assert days["2026-09-02"] == {"books": -10.0, "broker": -12.5, "n": 1, "matched": 1}
