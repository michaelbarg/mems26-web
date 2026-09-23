"""T-436d — `entry_price` must be the price the BROKER filled, not the one we asked.

Root (verified 2026-09-23 from code + DB + journal, not from memory):
`sc_study/MES_AI_DataExport_merged.cpp` wrote the `ENTRY` fills line immediately
after `sc.BuyEntry/SellEntry` returned `r > 0` — i.e. at ORDER_SUBMITTED, before
any fill exists — using `entry_price`, which is `parse_float("\"price\"")` off
trade_command.json: the price the BACKEND sent. `fill_poller` then fed exactly
that number to `on_fill()`, so `v9_trades.entry_price` == command price on every
row (measured: #2230 DB 7780.5 == journal ENTRY order 11328 price 7780.50).
The broker filled 3-5 ticks worse (#2017/#2041/#2152) and the difference was
invisible everywhere: the books never saw it, and `strings` on Sierra's binary
TradeActivityLog does not recover fill prices.

The EXIT legs were already correct — the same file books T1/T2/T3/T4/STOP off
`AvgFillPrice`, gated on `OrderStatusCode == SCT_OSC_FILLED`.

Fix (additive, mirrors the exit-leg pattern in the same file): the DLL emits ONE
extra `ENTRY_FILL` event carrying `AvgFillPrice` once Sierra reports the parent
FILLED; `fill_poller` routes it to `TradeManager.set_entry_fill_price`, which
corrects `entry_price` and preserves the order price + slippage in `quality`.
The `ENTRY` line itself still goes out at submit time — the backend's order-id
map is built from it, and delaying it would orphan a T1/STOP fill that beats it.

if reverted -> RED because: dropping the ENTRY_FILL branch sends the kind down
the `else` arm ("unknown fill kind") and `set_entry_fill_price` is never called;
reverting the DLL block removes the `ENTRY_FILL`/`AvgFillPrice` emitter that
test_dll_emits_entry_fill_with_avg_fill_price asserts on the deployed source.
"""
import json
from pathlib import Path

import pytest

from backend.v9.services.fill_poller import FillPoller


REPO = Path(__file__).resolve().parents[3]
# The DEPLOYED DLL source is the monolith, NOT sc_study/MES_AI_DataExport.cpp:
# ~/SierraChart/ACS_Source/MES_AI_DataExport.cpp is byte-identical to it, and
# build_monolithic_cpp.sh carries an explicit anti-regression guard saying every
# DLL fix since 2026-07-22 was written straight into the monolith.
MONOLITH = REPO / "sc_study" / "MES_AI_DataExport_merged.cpp"


# ── doubles ──────────────────────────────────────────────────────────────────

class _Trade:
    def __init__(self, tid, direction="LONG", entry_price=7800.0, state="FILLED"):
        self.id = tid
        self.direction = direction
        self.entry_price = entry_price
        self.state = state
        self.mode = "live"
        self.quality = {}


class _DB:
    def __init__(self):
        self.flushes = 0

    def flush(self):
        self.flushes += 1


class _TM:
    """Just enough TradeManager to exercise the real set_entry_fill_price."""

    def __init__(self, trade):
        self._trade = trade
        self._db = _DB()
        self.calls = []

    def _get_trade(self, tid):
        return self._trade if self._trade.id == tid else None

    def get_active_trades(self):
        return [self._trade]

    # real implementation, bound to this double
    def set_entry_fill_price(self, trade_id, fill_price):
        from backend.v9.services.trade_manager.manager import TradeManager
        return TradeManager.set_entry_fill_price(self, trade_id, fill_price)

    # anything the poller might reach for on the ENTRY_FILL path is a failure
    def on_fill(self, *a, **k):
        self.calls.append(("on_fill", a, k))

    def on_target_hit(self, *a, **k):
        self.calls.append(("on_target_hit", a, k))

    def on_stop_hit(self, *a, **k):
        self.calls.append(("on_stop_hit", a, k))

    def update_closed_trade_pnl(self, *a, **k):
        self.calls.append(("update_closed_trade_pnl", a, k))

    def set_sierra_order_ids(self, *a, **k):
        self.calls.append(("set_sierra_order_ids", a, k))


def _poller(trade):
    tm = _TM(trade)
    p = FillPoller(trade_manager=tm)
    p.register_order(11328, trade.id)
    return p, tm


def _entry_fill(price, order_id=11328):
    return {"kind": "ENTRY_FILL", "order_id": order_id,
            "price": price, "contracts": 1, "ts": 1790180104}


# ── 1. the manager-level correction ──────────────────────────────────────────

def test_long_fill_worse_than_order_is_positive_slippage():
    # #2230's real numbers: LONG, command 7780.50. A 3-tick-worse fill = 7781.25.
    t = _Trade(2230, direction="LONG", entry_price=7780.50)
    _, tm = _poller(t)
    slip = tm.set_entry_fill_price(2230, 7781.25)
    assert t.entry_price == 7781.25, "entry_price must become the BROKER's fill"
    assert t.quality["order_price"] == 7780.50, "the order price must survive for audit"
    assert slip == 0.75 and t.quality["entry_slippage_pts"] == 0.75


def test_short_fill_worse_than_order_is_also_positive_slippage():
    # SHORT filled BELOW the ask is worse — the sign must not flip with direction.
    t = _Trade(2106, direction="SHORT", entry_price=7835.00)
    _, tm = _poller(t)
    slip = tm.set_entry_fill_price(2106, 7834.00)
    assert t.entry_price == 7834.00
    assert slip == 1.0, "SHORT: filled lower = worse = positive slippage"


def test_better_than_asked_fill_is_negative_slippage():
    t = _Trade(1, direction="LONG", entry_price=7800.0)
    _, tm = _poller(t)
    assert tm.set_entry_fill_price(1, 7799.50) == -0.5


def test_second_delivery_does_not_rebaseline():
    """A re-delivered ENTRY_FILL must not measure slippage against the already
    corrected price (that would silently report 0 and erase the real number)."""
    t = _Trade(1, direction="LONG", entry_price=7800.0)
    _, tm = _poller(t)
    tm.set_entry_fill_price(1, 7801.0)
    again = tm.set_entry_fill_price(1, 7801.0)
    assert again == 1.0, "idempotent: the ORIGINAL slippage is returned"
    assert t.quality["order_price"] == 7800.0, "order price must not be overwritten"
    assert t.entry_price == 7801.0


@pytest.mark.parametrize("bad", [None, 0, -1, "abc"])
def test_no_synthetic_price_ever(bad):
    """Rule 1 — a missing/absurd fill price leaves the row alone, never guessed."""
    t = _Trade(1, direction="LONG", entry_price=7800.0)
    _, tm = _poller(t)
    assert tm.set_entry_fill_price(1, bad) is None
    assert t.entry_price == 7800.0
    assert "entry_fill_applied" not in t.quality


def test_unknown_trade_is_silent_none():
    t = _Trade(1)
    _, tm = _poller(t)
    assert tm.set_entry_fill_price(999, 7800.0) is None


# ── 2. the poller routing ────────────────────────────────────────────────────

def test_poller_routes_entry_fill_to_the_price_correction():
    t = _Trade(2230, direction="LONG", entry_price=7780.50)
    p, tm = _poller(t)
    p._process_fill(_entry_fill(7781.25))
    assert t.entry_price == 7781.25


def test_entry_fill_never_transitions_state_or_refills():
    """The trade is already FILLED — this is a price correction and nothing else.
    on_fill() would re-transition, rewrite entry_ts to now() and re-push the
    phone alert, so reaching it at all is the bug."""
    t = _Trade(2230, direction="LONG", entry_price=7780.50, state="FILLED")
    p, tm = _poller(t)
    p._process_fill(_entry_fill(7781.25))
    assert tm.calls == [], f"ENTRY_FILL touched the lifecycle: {tm.calls}"
    assert t.state == "FILLED"


def test_entry_fill_is_not_an_unknown_kind(caplog):
    t = _Trade(2230, direction="LONG", entry_price=7780.50)
    p, _ = _poller(t)
    with caplog.at_level("WARNING"):
        p._process_fill(_entry_fill(7781.25))
    assert "unknown fill kind" not in caplog.text


def test_entry_fill_on_a_closed_trade_warns_loudly(caplog):
    """A trade that closed before its own entry fill was reported has pnl_usd
    booked off the order price. No silent failures (CLAUDE.md): say so, and do
    NOT re-derive P&L here."""
    t = _Trade(2230, direction="LONG", entry_price=7780.50, state="CLOSED")
    p, tm = _poller(t)
    with caplog.at_level("WARNING"):
        p._process_fill(_entry_fill(7781.25))
    assert t.entry_price == 7781.25
    assert "T-436d" in caplog.text
    assert not any(c[0] == "update_closed_trade_pnl" for c in tm.calls)


def test_the_ordinary_entry_path_is_untouched():
    """The ENTRY line must still fire on_fill at submit time — the order-id map
    is built from it, and a T1/STOP fill that beats the map becomes an ORPHAN
    FILL CRITICAL (I-58)."""
    t = _Trade(2230, direction="LONG", entry_price=None, state="PENDING")
    p, tm = _poller(t)
    p._process_fill({"kind": "ENTRY", "order_id": 11328, "price": 7780.50,
                     "contracts": 1, "ts": 1790180104, "c1_target_id": 11329,
                     "c1_stop_id": 11330})
    assert any(c[0] == "on_fill" for c in tm.calls), "ENTRY must still call on_fill"


# ── 3. the DLL contract + the readers ────────────────────────────────────────

def test_dll_emits_entry_fill_with_avg_fill_price():
    """Guards the deployed monolith. Also guards the regenerate-from-stale-
    modular regression: sc_study/MES_AI_DataExport.cpp has been frozen since
    2026-07-22 and has no order-placement path at all."""
    src = MONOLITH.read_text(errors="ignore")
    assert '\\"kind\\":\\"ENTRY_FILL\\"' in src, "monolith lost the ENTRY_FILL emitter"
    i = src.index('\\"kind\\":\\"ENTRY_FILL\\"')
    block = src[i:i + 400]
    assert "AvgFillPrice" in block, "ENTRY_FILL must carry the REAL fill price"
    # emitted only on a real fill — never synthesized (Rule 1)
    ctx = src[max(0, i - 1200):i]
    assert "SCT_OSC_FILLED" in ctx, "ENTRY_FILL must be gated on the parent being FILLED"


def test_journal_readers_do_not_book_entry_fill_as_an_exit():
    """`t211_backfill_apply` and `fill_truth` classify by BLACKLIST ('anything
    that isn't ENTRY is an exit'), so a new entry-side kind is booked as an exit
    leg / reported as an orphan fill unless it is named."""
    for rel in ("scripts/t211_backfill_apply.py", "scripts/fill_truth.py"):
        src = (REPO / rel).read_text(errors="ignore")
        assert '"ENTRY_FILL"' in src, f"{rel} would misclassify ENTRY_FILL"


def test_exit_kind_whitelists_stay_closed():
    """The two P&L ledgers classify by WHITELIST — ENTRY_FILL must stay out of
    both or a single trade books an extra 'exit' leg."""
    from backend.v9.services.sierra_ledger import EXIT_KINDS as LEDGER_KINDS
    from backend.v9.services.sierra_pnl_reconcile import EXIT_KINDS as RECON_KINDS
    assert "ENTRY_FILL" not in LEDGER_KINDS
    assert "ENTRY_FILL" not in RECON_KINDS


def test_entry_fill_line_shape_is_parseable():
    """The exact line the DLL appends must survive the poller's line reader."""
    line = ('{"kind":"ENTRY_FILL","ts":1790180104,"order_id":11328,'
            '"price":7781.25,"contracts":1}')
    d = json.loads(line)
    assert d["kind"] == "ENTRY_FILL" and d["price"] == 7781.25
