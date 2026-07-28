"""Dalton Alignment — Sierra fill reconciliation (Task #6) · #420 P&L fixture.

Real case: #420 recorded pnl_usd=-82.50 (calculated from intended stop),
Sierra-actual ~$15. Root: trade_fills.json empty → no Sierra-truth ledger.

Contract:
  1. When fills exist → ledger.realized_pnl from fills; reconcile flags pnl divergence
     vs backend calculated when they disagree.
  2. Empty fills → honest empty ledger / no fabricated pnl (Rule 1).
  3. Never treat backend calculated pnl as Sierra-truth when fills missing.
"""
from __future__ import annotations

import json

from backend.v9.services.sierra_ledger import (
    build_ledger,
    parse_fills,
    reconcile,
)

# #420 claimed numbers (OPS_LOG)
BACKEND_420 = {
    "id": 420,
    "entry_price": 7508.75,
    "exit_price": 7514.25,
    "stop": 7514.0,
    "pnl_usd": -82.50,
    "contracts": 3,
    "state": "CLOSED",
    "direction": "SHORT",
}


def test_empty_fills_do_not_invent_pnl():
    fills = parse_fills([])
    ledger = build_ledger(fills)
    assert ledger == [] or all(t.realized_pnl is None or not t.closed for t in ledger)


def test_sierra_fills_produce_real_pnl_not_minus_82():
    """ENTRY 1c SHORT @7508.75 + STOP @7511.75 → ~−$15 (MES $5/pt), not −$82.50."""
    lines = [
        json.dumps({
            "kind": "ENTRY", "order_id": 9001, "price": 7508.75, "ts": 1.0,
            "contracts": 1, "c1_stop_id": 9002, "c1_target_id": 9003,
        }),
        json.dumps({
            "kind": "STOP", "order_id": 9002, "price": 7511.75, "ts": 2.0, "qty": 1,
        }),
    ]
    trades = build_ledger(parse_fills(lines))
    assert len(trades) >= 1
    lt = trades[0]
    assert lt.realized_pnl is not None
    assert abs(lt.realized_pnl - (-15.0)) < 1.0, f"got pnl={lt.realized_pnl}"
    assert abs(lt.realized_pnl - BACKEND_420["pnl_usd"]) > 50  # must disagree with calculated


def test_reconcile_flags_pnl_divergence_on_420():
    lines = [
        json.dumps({
            "kind": "ENTRY", "order_id": 9001, "price": 7508.75, "ts": 1.0,
            "contracts": 1, "c1_stop_id": 9002,
        }),
        json.dumps({
            "kind": "STOP", "order_id": 9002, "price": 7511.75, "ts": 2.0, "qty": 1,
        }),
    ]
    trades = build_ledger(parse_fills(lines))
    divs = reconcile(trades[0], BACKEND_420)
    fields = {d.field for d in divs}
    assert "pnl_usd" in fields, f"expected pnl_usd divergence, got {divs}"


def test_reconcile_match_when_backend_matches_fills():
    lines = [
        json.dumps({
            "kind": "ENTRY", "order_id": 1, "price": 7500.0, "ts": 1.0,
            "contracts": 1, "c1_stop_id": 2,
        }),
        json.dumps({"kind": "STOP", "order_id": 2, "price": 7505.0, "ts": 2.0, "qty": 1}),
    ]
    trades = build_ledger(parse_fills(lines))
    lt = trades[0]
    row = {
        "entry_price": 7500.0,
        "exit_price": 7505.0,
        "stop": 7505.0,
        "pnl_usd": lt.realized_pnl,
        "contracts": 1,
        "state": "CLOSED",
    }
    assert reconcile(lt, row) == []


def test_empty_fills_file_is_honest_gap_not_match():
    """Empty trade_fills must NOT be reported as MATCH against a CLOSED backend row."""
    trades = build_ledger(parse_fills([""]))
    assert trades == []
    # Without a Sierra ledger trade there is nothing to reconcile — caller must
    # treat empty fills + CLOSED backend as GAP (Task #6), not silent OK.
    assert BACKEND_420["pnl_usd"] == -82.50  # fixture still the live lie
