"""T-227 — a banked leg was booked twice on every T0 ladder.

ROOT (proven from production, 2026-09-02, two independent live trades):
`_calculate_pnl` builds its legs from the T-62 fill ledger first and records
which target COLUMN each ledger leg already paid for (`consumed_columns`, from
`f["column"]`, 0=t1..3=t4). It then walks the LADDER GROUPS to add any target
that was hit but has no Sierra fill. The membership test compared a GROUP index
against a set of COLUMN indices:

    for g_idx in range(len(weights)):
        if g_idx in consumed_columns:      # <-- group vs column
            continue
        _col = max(0, g_idx - 1) if _has_t0 else g_idx

With `has_t0` the two indices are offset by one, so exactly ONE already-banked
leg slipped through the guard on every T0 ladder and was added a second time —
once from the ledger at its real fill price, once again from its `*_hit_ts`.

Measured, books vs `scripts/pnl_reconcile.py` (Sierra fills journal):

    #953  books +277.50   Sierra +187.50   delta +90.00 = 18.00pt x 1c
    #971  books +145.00   Sierra  +82.50   delta +62.50 =  6.25pt x 2c

and the code had already said so out loud in /tmp/backend.err.log:
    18:48:13 [TradeManager] T-62 #953: exit legs cover 6c but the trade is
             booked as 5c — contract-count drift, P&L follows the FILLS
    21:41:04 [TradeManager] T-62 #971: exit legs cover 6c ... 7c ...

The fix maps group→column BEFORE the membership test.

Anti-tautological: drives the REAL `TradeManager._calculate_pnl` with the REAL
fill prices/quantities taken from
~/SierraChart_Data/v9_export/trade_fills_journal.jsonl. No reimplementation of
the P&L math.

if reverted → RED because: restoring `if g_idx in consumed_columns` re-adds the
duplicate leg and both trades come back at their inflated book value.
"""
from types import SimpleNamespace

import pytest

from backend.v9.services.trade_manager.manager import TradeManager

POINT = 5.0


class _FakeDB:
    def flush(self):
        pass

    def commit(self):
        pass


def _tm():
    tm = TradeManager.__new__(TradeManager)
    tm._db = _FakeDB()
    return tm


def _mk(**kw):
    t = SimpleNamespace(
        id=0, direction="LONG", entry_price=None, stop=None,
        t1=None, t2=None, t3=None, t4=None,
        t1_hit_ts=None, t2_hit_ts=None, t3_hit_ts=None, t4_hit_ts=None,
        state="CLOSED", exit_reason="STOP_HIT", exit_price=None,
        pnl_usd=None, pnl_r=None, quality={},
    )
    for k, v in kw.items():
        setattr(t, k, v)
    return t


# ── #953 — LONG 5c, entry 7668.75 ────────────────────────────────────────────
# trade_fills_journal.jsonl 2026-09-02 (order ids from the same lines):
#   17:17:32 T1   10887 1c @ 7671.75   -> logical T0  (+3.00pt)
#   17:18:32 T2   10890 2c @ 7672.50   -> logical T1  (+3.75pt x2)
#   17:40:30 T3   10893 1c @ 7686.75   -> logical T2  (+18.00pt)
#   18:48:13 STOP 10896 1c @ 7677.75                  (+9.00pt, stop at BE+)
# = 3.00 + 7.50 + 18.00 + 9.00 = 37.50pt x $5 = $187.50
def _trade_953():
    t = _mk(
        id=953, direction="LONG", entry_price=7668.75, stop=7677.75,
        # NOTE: t1/t2 carry the FILL prices because on_target_hit overwrites the
        # planned level with the Sierra fill — that is why the row in the DB
        # reads t2=7686.75 > t3=7684.75 on a LONG (impossible as a plan).
        t1=7672.50, t2=7686.75, t3=7684.75,
        t1_hit_ts="2026-09-02T17:18:32+00:00",
        t2_hit_ts="2026-09-02T17:40:30+00:00",
        exit_price=7677.75, exit_reason="STOP_HIT",
        quality={
            "contracts": 5, "has_t0": True, "t0_target_pts": 3.0,
            "initial_stop": 7660.50,
            "exit_fills": [
                {"kind": "T0", "price": 7671.75, "qty": 1, "order_id": 10887,
                 "column": None, "ts": "2026-09-02T17:17:32+00:00"},
                {"kind": "T1", "price": 7672.50, "qty": 2, "order_id": 10890,
                 "column": 0, "ts": "2026-09-02T17:18:32+00:00"},
                {"kind": "T2", "price": 7686.75, "qty": 1, "order_id": 10893,
                 "column": 1, "ts": "2026-09-02T17:40:30+00:00"},
                {"kind": "STOP", "price": 7677.75, "qty": 1, "order_id": 10896,
                 "column": None, "ts": "2026-09-02T18:48:13+00:00"},
            ],
        },
    )
    return t


# ── #971 — LONG 5c, entry 7673.25 ────────────────────────────────────────────
#   20:13:46 T1   10924 1c @ 7676.25   -> logical T0  (+3.00pt)
#   20:57:55 T2   10927 2c @ 7679.50   -> logical T1  (+6.25pt x2)
#   21:41:04 STOP 10931 1c @ 7673.75                  (+0.50pt, BE+)
#   21:41:04 STOP 10933 1c @ 7673.75                  (+0.50pt, BE+)
# = 3.00 + 12.50 + 0.50 + 0.50 = 16.50pt x $5 = $82.50
def _trade_971():
    return _mk(
        id=971, direction="LONG", entry_price=7673.25, stop=7673.75,
        t1=7679.50, t2=7682.50, t3=7683.00,
        t1_hit_ts="2026-09-02T20:57:55+00:00",
        exit_price=7673.75, exit_reason="STOP_FILL",
        quality={
            "contracts": 5, "has_t0": True, "t0_target_pts": 3.0,
            "initial_stop": 7667.00,
            "exit_fills": [
                {"kind": "T0", "price": 7676.25, "qty": 1, "order_id": 10924,
                 "column": None, "ts": "2026-09-02T20:13:46+00:00"},
                {"kind": "T1", "price": 7679.50, "qty": 2, "order_id": 10927,
                 "column": 0, "ts": "2026-09-02T20:57:55+00:00"},
                {"kind": "STOP", "price": 7673.75, "qty": 1, "order_id": 10931,
                 "column": None, "ts": "2026-09-02T21:41:04+00:00"},
                {"kind": "STOP", "price": 7673.75, "qty": 1, "order_id": 10933,
                 "column": None, "ts": "2026-09-02T21:41:04+00:00"},
            ],
        },
    )


@pytest.mark.parametrize("factory,sierra,books_before", [
    (_trade_953, 187.50, 277.50),
    (_trade_971, 82.50, 145.00),
])
def test_pnl_equals_sierra_fills(factory, sierra, books_before):
    t = factory()
    _tm()._calculate_pnl(t)
    assert t.pnl_usd == pytest.approx(sierra), (
        f"#{t.id}: booked {t.pnl_usd} — Sierra's own fills sum to {sierra}; "
        f"the pre-fix books said {books_before}"
    )


@pytest.mark.parametrize("factory,n", [(_trade_953, 5), (_trade_971, 5)])
def test_legs_cover_exactly_the_contract_count(factory, n, caplog):
    """The 'exit legs cover 6c but the trade is booked as 5c' warning that fired
    live must no longer be reachable for these two trades."""
    t = factory()
    with caplog.at_level("WARNING"):
        _tm()._calculate_pnl(t)
    assert "exit legs cover" not in caplog.text, caplog.text


def test_no_t0_ladder_is_unaffected():
    """Regression guard: without has_t0 group==column, so the fix is a no-op.

    4 contracts, T1 filled from Sierra, T2 hit with no fill line.
    """
    t = _mk(
        id=1, direction="LONG", entry_price=100.0, stop=95.0,
        t1=102.0, t2=104.0, t3=106.0, t4=108.0,
        t1_hit_ts="x", t2_hit_ts="x",
        exit_price=95.0, exit_reason="STOP_HIT",
        quality={"contracts": 4, "exit_fills": [
            {"kind": "T1", "price": 102.5, "qty": 1, "order_id": 1,
             "column": 0, "ts": "a"},
        ]},
    )
    _tm()._calculate_pnl(t)
    # T1 from the ledger (2.5) + T2 from its hit (4.0) + two unbanked
    # contracts at the exit fill (-5.0 each) = -3.5pt
    assert t.pnl_usd == pytest.approx(-3.5 * POINT)
