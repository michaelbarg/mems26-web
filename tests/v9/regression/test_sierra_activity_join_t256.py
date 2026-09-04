"""T-256 regression — the InternalOrderID join must not repeat T-229's mistakes.

Root (2026-09-04, read in the code not from memory):
`sc_study/MES_AI_DataExport_merged.cpp:3003-3019` writes the `"kind":"ENTRY"`
record **inside the `r > 0` (ORDER SUBMITTED) branch**, carrying
`entry_price` — which line 2866 defines as `parse_float("\"price\"")`, i.e. the
price the BACKEND asked for — and `time(nullptr)`, the submit time. It is a
submission record wearing a fill's name. The real entry fill price is never
read back, so `pnl_usd` is wrong by (requested - filled) x contracts x $5 on
every live trade, in whichever direction the market happened to move.

That day: books -97.50 vs broker -116.25 while `entry_delta` was
+0.50 / +0.75 / +0.25 / 0.00 / -0.75 — the sign FLIPS, which is why the
earlier "constant recording offset" thesis was wrong and why an aggregate
check can agree by luck while individual rows are wrong in both directions.

These tests pin the three parsing invariants that make the join trustworthy.
"""
import datetime as dt
import importlib.util
import struct
from pathlib import Path

import pytest

_MOD = Path(__file__).resolve().parents[3] / "scripts" / "sierra_activity_join.py"
_spec = importlib.util.spec_from_file_location("sierra_activity_join", _MOD)
saj = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(saj)


def _tlv(fid, payload):
    return struct.pack("<II", fid, len(payload)) + payload


def _rec(ts_us, atype, text, oid=None, px=None, cum_qty=None):
    """One TradeActivityLog record in Sierra's TLV layout."""
    b = _tlv(saj.F_RECORD_HEAD, struct.pack("<q", -1))
    b += _tlv(saj.F_ACTIVITY_TYPE, struct.pack("<i", atype))
    b += _tlv(saj.F_TS, struct.pack("<q", ts_us))
    b += _tlv(saj.F_TEXT, text.encode())
    if oid is not None:
        b += _tlv(saj.F_INTERNAL_ORDER_ID, struct.pack("<q", oid))
    if px is not None:
        b += _tlv(saj.F_FILL_PRICE, struct.pack("<d", px * saj.PRICE_SCALE))
    if cum_qty is not None:
        b += _tlv(saj.F_FILL_QTY, struct.pack("<d", cum_qty))
    return b


_FILLED = "Teton CME Routing (Filled). Info: CME  (Trade)."
_PARTIAL = "Teton CME Routing (Partial fill). Info: CME  (Trade)."
_T0 = 3997691703000000        # 2026-09-04 13:55:03 UTC in SCDateTime us


def _write(tmp_path, blob):
    p = tmp_path / "TradeActivityLog_2026-09-04_UTC.37138283.data"
    p.write_bytes(blob)
    return p


def test_activity_type_1_echo_is_not_double_counted(tmp_path):
    """Sierra logs every execution twice: type 1 (order side) + type 2 (trade).

    Counting both doubles every fill and would have made the broker's day
    total -232.50 instead of -116.25.
    """
    blob = (_rec(_T0, 1, _FILLED, oid=10964, px=7745.25, cum_qty=1.0)
            + _rec(_T0 + 80, 2, _FILLED, oid=10964, px=7745.25, cum_qty=1.0))
    fills, _ = saj.parse_activity(_write(tmp_path, blob))
    assert len(fills) == 1
    assert fills[0]["price"] == 7745.25
    assert fills[0]["qty"] == 1.0


def test_fill_qty_is_cumulative_and_must_be_differenced(tmp_path):
    """TLV 114 is CUMULATIVE per order. A 2-lot that fills 1 then 1 shows up as
    cum=1 then cum=2; taking it at face value books 3 contracts for a 2-lot.

    Observed live on 2026-09-04 order 10991 (16:52:32 cum=1, 16:52:33 cum=2),
    which the broker priced as two separate +23.75 lots.
    """
    blob = (_rec(_T0, 2, _PARTIAL, oid=10991, px=7735.0, cum_qty=1.0)
            + _rec(_T0 + 386000, 2, _FILLED, oid=10991, px=7735.0, cum_qty=2.0))
    fills, _ = saj.parse_activity(_write(tmp_path, blob))
    assert [f["qty"] for f in fills] == [1.0, 1.0]
    assert sum(f["qty"] for f in fills) == 2.0


def test_closed_pnl_attaches_to_the_preceding_fill(tmp_path):
    """The cash record lands microseconds AFTER the fill that closed the lot,
    and before the next fill. Attribution must follow that order, never price
    proximity (T-229).
    """
    blob = (_rec(_T0, 2, _FILLED, oid=10966, px=7740.25, cum_qty=1.0)
            + _rec(_T0 + 6625, 4,
                   "Cash Balance update | Closed Trade Profit/Loss: -25.00. "
                   "Symbol: MESU26_FUT_CME. Currency: USD")
            + _rec(_T0 + 6757, 2, _FILLED, oid=10969, px=7740.25, cum_qty=2.0)
            + _rec(_T0 + 6958, 4,
                   "Cash Balance update | Closed Trade Profit/Loss: -50.00. "
                   "Symbol: MESU26_FUT_CME. Currency: USD"))
    fills, pnls = saj.parse_activity(_write(tmp_path, blob))
    assert [p["amount"] for p in pnls] == [-25.0, -50.0]
    saj.attach_pnl(fills, pnls)
    assert {f["order_id"]: f["broker_pnl"] for f in fills} == {
        10966: -25.0, 10969: -50.0}


def test_reconcile_flags_entry_price_divergence_and_agrees_with_broker(tmp_path):
    """The end-to-end shape of live #998: entry booked 0.50 above the fill.

    books  -137.50  =  (7740.25 - 7745.75) * 5 * $5      <- our arithmetic
    broker -125.00  =  (7740.25 - 7745.25) * 5 * $5      <- what was paid
    """
    blob = _rec(_T0, 2, _FILLED, oid=10973, px=7745.25, cum_qty=5.0)
    ts = _T0
    # per-order cumulative qty — the 1/2/1/1 ladder of a 5-contract entry
    for oid, qty in ((10966, 1.0), (10969, 2.0), (10972, 1.0), (10975, 1.0)):
        ts += 6000
        blob += _rec(ts, 2, _FILLED, oid=oid, px=7740.25, cum_qty=qty)
        ts += 600
        amt = -25.0 * (2 if oid == 10969 else 1)
        blob += _rec(ts, 4, "Cash Balance update | Closed Trade Profit/Loss: "
                            f"{amt:.2f}. Symbol: MESU26_FUT_CME. Currency: USD")
    fills, pnls = saj.parse_activity(_write(tmp_path, blob))
    saj.attach_pnl(fills, pnls)
    trade = {
        "id": 998, "mode": "live", "firing_system": 4, "direction": "LONG",
        "entry_price": 7745.75, "exit_price": 7740.25, "exit_reason": "STOP_FILL",
        "pnl_usd": -137.5, "pnl_sierra": None,
        "quality": {"sierra_order_id": "10973", "c1_stop_id": "10966",
                    "c2_stop_id": "10969", "c3_stop_id": "10972",
                    "c4_stop_id": "10975"},
    }
    r = saj.reconcile([trade], fills)[0]
    assert r["broker_entry"] == 7745.25
    assert r["entry_delta"] == 0.5
    assert r["pnl_broker"] == -125.0
    assert r["pnl_reconstructed"] == -125.0
    assert r["recon_agrees"] is True
    assert r["pnl_delta"] == -12.5          # books overstate the loss by $12.50


def test_mutation_using_books_entry_breaks_the_agreement(tmp_path):
    """Mutation test: if the join silently fell back to the BOOKS entry price
    instead of the fill, the two independent computations would still each be
    self-consistent — but they would stop agreeing with the broker's cash.
    That is the exact failure this whole tool exists to make visible.
    """
    blob = _rec(_T0, 2, _FILLED, oid=10973, px=7745.25, cum_qty=5.0)
    blob += _rec(_T0 + 6000, 2, _FILLED, oid=10966, px=7740.25, cum_qty=5.0)
    blob += _rec(_T0 + 6600, 4, "Cash Balance update | Closed Trade Profit/Loss: "
                                "-125.00. Symbol: MESU26_FUT_CME. Currency: USD")
    fills, pnls = saj.parse_activity(_write(tmp_path, blob))
    saj.attach_pnl(fills, pnls)
    base = {"id": 998, "mode": "live", "firing_system": 4, "direction": "LONG",
            "entry_price": 7745.75, "exit_price": 7740.25,
            "exit_reason": "STOP_FILL", "pnl_usd": -137.5, "pnl_sierra": None,
            "quality": {"sierra_order_id": "10973", "c1_stop_id": "10966"}}
    assert saj.reconcile([base], fills)[0]["recon_agrees"] is True
    # now poison the fill price with the books value — agreement must break
    for f in fills:
        if f["order_id"] == 10973:
            f["price"] = 7745.75
    poisoned = saj.reconcile([base], fills)[0]
    assert poisoned["entry_delta"] == 0.0          # looks clean...
    assert poisoned["pnl_reconstructed"] == -137.5  # ...but disagrees with cash
    assert poisoned["pnl_broker"] == -125.0
    assert poisoned["recon_agrees"] is False


def test_sc_epoch_decodes_to_the_real_wall_clock(tmp_path):
    """TLV 102 is SCDateTime microseconds since 1899-12-30. scripts/
    trade_activity_feed.py still claims the binary log has no recoverable
    timestamp ("`strings` finds zero HH:MM:SS patterns") — true of `strings`,
    false of the file.
    """
    blob = _rec(_T0, 2, _FILLED, oid=1, px=7745.25, cum_qty=1.0)
    fills, _ = saj.parse_activity(_write(tmp_path, blob))
    assert fills[0]["ts"] == dt.datetime(2026, 9, 4, 13, 55, 3,
                                         tzinfo=dt.timezone.utc)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
