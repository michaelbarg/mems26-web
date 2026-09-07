"""T-251 — a stop on ONE leg of a ladder must not close the books.

Incident **#1008** (LIVE, 2026-09-04, SHORT 5c @ 7717, stop 7723.50). Sierra
bracketed the size as four OCO groups — c1 10977/10978 · c2 10980/10981 (2c) ·
c3 10983/10984 · c4 —/10986 (stop-only). The day went:

    18:30:58  SMART_BE          stop 7723.50 -> 7716.75
    18:31:00  TARGET_REALISM    t2   7706.00 -> 7707.25
    18:35:42  order 10986 (c4)  STOP 1c @ 7716.75   -> books said CLOSED +72.5
    19:08:02  order 10984 (c3)  STOP 1c @ 7724.75   -> PNL_CORRECTION 72.5 -> 32.5

`TradeManager.on_stop_hit` transitioned to CLOSED with **no condition on
quantity**, so c4's leg closed the trade while the T-62 exit-fill ledger said
Σqty = 4 of 5 and c3 was still working at the broker. What that cost, measured:

  * CLOSED drops the row out of `get_active_trades` (`manager.py` —
    `_ACTIVE_TRADE_STATES`), so `bar_level_detector` stopped scanning it:
    **zero `runner_reversal` checks between 18:36 and 19:08** on an inverted
    short whose stop had been dragged out to 7724.75.
  * `on_trade_close` booked the day's P&L and pushed "closed +72.5" to the
    phone 32 minutes before the trade actually ended at +32.50.
  * `reconcile` could not find 1008 among the open trades and raised
    `[StuckSlot] LIVE PATH BLOCKED` at 18:45:44 — a false alarm.

The fix makes the **ledger** the authority (never `position_qty`: the account
is shared with Eti, so an account-level quantity cannot attribute a leg). One
leg of an incomplete ladder leaves the trade PARTIAL, writes no exit columns,
and books realized-only P&L.

Mutation: delete the `filled < n_contracts` condition in `on_stop_hit` and
`test_a_five_contract_trade_stays_open_where_a_four_contract_one_closes` goes
red — the first stop closes the books again.
"""
import os
from datetime import datetime, timezone

import pytest

# Set env before any backend imports (same contract as tests/v9/services)
os.environ.setdefault("BRIDGE_TOKEN", "michael-mems26-2026")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.v9.db.models.trades import V9Trade
from backend.v9.db.session import Base
from backend.v9.services.trade_manager.manager import (
    _ACTIVE_TRADE_STATES,
    TradeManager,
)

MES = 5.0
ENTRY = 7717.0
INITIAL_STOP = 7723.5

#: the four Sierra fills of #1008, in the order the DLL reported them.
#: (label as the DLL names it, order_id, price, contracts)
T0_FILL = ("T1", 10977, 7714.0, 1)      # DLL "T1" -> logical T0 (c1 scalp)
T1_FILL = ("T2", 10980, 7711.5, 2)      # DLL "T2" -> logical T1 (c2 holds 2c)
C4_STOP = (10986, 7716.75, 1)           # 18:35:42 — the leg that closed the books
C3_STOP = (10984, 7724.75, 1)           # 19:08:02 — the contract still alive


def _ts(minute, second):
    return datetime(2026, 9, 4, 15, minute, second, tzinfo=timezone.utc)


@pytest.fixture
def db():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    session = sessionmaker(bind=eng)()
    yield session
    session.rollback()
    session.close()


@pytest.fixture(autouse=True)
def _hermetic(monkeypatch, tmp_path):
    """Pin every flag this path reads, and keep the Sierra wire disarmed.

    `on_target_hit("T1")` runs smart-BE, which emits MODIFY_STOP when the
    execution flag for the trade's mode is ON. The trade here is `mode="live"`,
    so both execution flags are forced OFF and the signals dir is a tmp_path —
    a test must never arm the file the DLL polls (2026-07-28).
    """
    monkeypatch.setenv("BE_AFTER_REAL_T1_V1", "1")   # the T0 remap this trade ran under
    monkeypatch.setenv("LIVE_EXECUTION_V1", "0")
    monkeypatch.setenv("DEMO_EXECUTION_ENABLED", "0")
    monkeypatch.setenv("MEMS26_SIGNALS_DIR", str(tmp_path / "signals"))
    monkeypatch.setenv("ZLR_MGMT_V1", "0")
    monkeypatch.setenv("STOP_STRUCTURE_TRAIL_V1", "0")
    monkeypatch.setenv("S6_TREND_BE_DELAY_V1", "0")
    monkeypatch.setenv("GSHEETS_TRADE_LOG", "0")
    monkeypatch.setenv("PNL_REQUIRES_EXIT_PRICE_V1", "0")
    # POST_MORTEM_V1 fires on every LOSS and writes
    # docs/reports/postmortem/PM_<id>.md straight into the git work tree. A
    # test must not leave a tracked artifact behind — generated run-output in
    # git has blocked `git pull` during RTH more than once.
    from backend.v9.services.postmortem import analyzer as _pm
    monkeypatch.setattr(_pm, "on_trade_closed", lambda *a, **k: None)


def _trade_1008(db, contracts=5, tid=1008):
    """#1008 as the gateway wrote it, just before the first stop leg."""
    trade = V9Trade(
        id=tid,
        mode="live",
        firing_system=4,
        direction="SHORT",
        state="PARTIAL",
        entry_ts=_ts(5, 0),
        entry_price=ENTRY,
        stop=INITIAL_STOP,
        t1=7711.5, t2=7706.0, t3=7702.0, t4=None,
        quality={
            "contracts": contracts,
            "has_t0": True,
            "t0_target_pts": 3.0,
            "initial_stop": INITIAL_STOP,
            "sierra_order_id": 10985,
            "c1_target_id": 10977, "c1_stop_id": 10978,
            "c2_target_id": 10980, "c2_stop_id": 10981,
            "c3_target_id": 10983, "c3_stop_id": 10984,
            "c4_target_id": None, "c4_stop_id": 10986,
        },
        cross_context=[],
    )
    db.add(trade)
    db.flush()
    return trade


def _bank_the_two_targets(mgr, tid):
    """T0 (1c @7714) then logical T1 (2c @7711.5) — 3 of 5 contracts out."""
    label, oid, px, qty = T0_FILL
    mgr.on_target_hit(tid, label, fill_ts=_ts(20, 11), fill_price=px,
                      fill_qty=qty, order_id=oid)
    label, oid, px, qty = T1_FILL
    mgr.on_target_hit(tid, label, fill_ts=_ts(26, 3), fill_price=px,
                      fill_qty=qty, order_id=oid)


def _ledger_qty(trade):
    fills = (trade.quality or {}).get("exit_fills") or []
    return sum(int(f.get("qty") or 0) for f in fills)


class TestPartialStopKeepsBooksOpen:
    """The 18:35:42 leg of #1008 — 4 of 5 contracts accounted for."""

    def _upto_the_first_stop(self, db):
        mgr = TradeManager(db=db)
        trade = _trade_1008(db)
        _bank_the_two_targets(mgr, trade.id)
        oid, px, qty = C4_STOP
        mgr.on_stop_hit(trade.id, fill_ts=_ts(35, 42), fill_price=px,
                        fill_qty=qty, order_id=oid)
        return mgr, trade

    def test_one_leg_of_the_ladder_leaves_the_trade_partial(self, db):
        _mgr, trade = self._upto_the_first_stop(db)

        assert _ledger_qty(trade) == 4, "T0 1c + T1 2c + c4 stop 1c"
        assert trade.state == "PARTIAL", (
            "c3 (orders 10983/10984) is still working at the broker — CLOSED "
            "here is the 32-minute supervision hole of 2026-09-04")

    def test_the_books_record_no_exit_while_contracts_are_live(self, db):
        _mgr, trade = self._upto_the_first_stop(db)

        assert trade.exit_ts is None
        assert trade.exit_price is None
        assert trade.exit_reason is None
        assert trade.stop_hit_ts is None, (
            "a stop_hit_ts on a working trade is what let P0-2 stamp the LATER "
            "leg with the EARLIER leg's timestamp — both #1008 stops carry "
            "15:35:42 in the DB, though 10984 really filled at 16:07:59")

    def test_pnl_is_realized_only_while_the_ladder_works(self, db):
        _mgr, trade = self._upto_the_first_stop(db)

        # 1c @7714 (+3.00) + 2c @7711.50 (+5.50) + 1c @7716.75 (+0.25)
        expected = ((ENTRY - 7714.0) * 1 + (ENTRY - 7711.5) * 2
                    + (ENTRY - 7716.75) * 1) * MES
        assert expected == pytest.approx(71.25)
        assert trade.pnl_usd == pytest.approx(71.25), (
            "an empty exit_reason is what keeps _calculate_pnl in realized-only "
            "mode; writing one books the still-live 5th contract at this stop")

    def test_the_trade_stays_under_system6_supervision(self, db):
        """The measured cost of #1008: `get_active_trades` dropped the row, so
        `bar_level_detector` stopped scanning and no runner_reversal ran."""
        mgr, trade = self._upto_the_first_stop(db)

        assert trade.state in _ACTIVE_TRADE_STATES
        active_ids = [t.id for t in mgr.get_active_trades()]
        assert trade.id in active_ids, (
            "a trade with a live contract must remain visible to the detectors")
        assert trade.id in [t.id for t in mgr.get_active_trades(mode="live")]

    def test_management_log_names_the_partial_and_the_remainder(self, db):
        from backend.v9.db.models.trade_log import V9TradeManagementLog
        _mgr, trade = self._upto_the_first_stop(db)

        rows = (db.query(V9TradeManagementLog)
                .filter(V9TradeManagementLog.trade_id == trade.id).all())
        actions = [r.action for r in rows]
        assert "STOP_HIT_PARTIAL" in actions
        assert "STOP_HIT" not in actions, "the trade did not stop out — one leg did"
        entry = [r for r in rows if r.action == "STOP_HIT_PARTIAL"][0]
        assert entry.value["remaining"] == 1
        assert entry.value["qty"] == 1
        assert entry.value["order_id"] == 10986
        assert entry.value["fill_price"] == 7716.75

    def test_the_last_leg_closes_the_books_at_the_real_number(self, db):
        mgr, trade = self._upto_the_first_stop(db)
        oid, px, qty = C3_STOP
        mgr.on_stop_hit(trade.id, fill_ts=_ts(59, 2), fill_price=px,
                        fill_qty=qty, order_id=oid)

        assert _ledger_qty(trade) == 5
        assert trade.state == "CLOSED"
        assert trade.exit_reason == "STOP_HIT"
        assert trade.exit_price == pytest.approx(7724.75)
        assert trade.stop_hit_ts is not None
        # 71.25 - 1c x 7.75pt x $5 = 32.50 — the number the DB held for #1008
        # after the P0-2 correction (15 + 55 + 1.25 - 38.75).
        assert trade.pnl_usd == pytest.approx(32.5)
        assert trade.outcome == "WIN"
        assert trade.id not in [t.id for t in mgr.get_active_trades()]


class TestTheGuardIsQuantityDriven:
    """The condition is `Σledger < contracts` — not "a stop arrived"."""

    def test_a_five_contract_trade_stays_open_where_a_four_contract_one_closes(
            self, db):
        """The mutation guard. Same two targets, same stop leg; the ONLY
        difference is the declared size, so the ledger count is what decides.
        Drop `filled < n_contracts` and the 5-contract row closes too."""
        mgr = TradeManager(db=db)
        five = _trade_1008(db, contracts=5, tid=1008)
        four = _trade_1008(db, contracts=4, tid=1009)

        for t in (five, four):
            _bank_the_two_targets(mgr, t.id)
            oid, px, qty = C4_STOP
            mgr.on_stop_hit(t.id, fill_ts=_ts(35, 42), fill_price=px,
                            fill_qty=qty, order_id=oid)

        assert _ledger_qty(five) == 4 and _ledger_qty(four) == 4
        assert five.state == "PARTIAL", "4 of 5 — one contract still working"
        assert four.state == "CLOSED", "4 of 4 — the ladder is fully out"

    def test_a_stop_taking_the_whole_position_closes_in_one_leg(self, db):
        """Sierra can report the whole size on one stop (no scale-outs). The
        books must close exactly as before — the fix must not hold a finished
        trade open."""
        mgr = TradeManager(db=db)
        trade = _trade_1008(db)

        mgr.on_stop_hit(trade.id, fill_ts=_ts(35, 42), fill_price=7723.5,
                        fill_qty=5, order_id=10986)

        assert trade.state == "CLOSED"
        assert trade.exit_reason == "STOP_HIT"
        assert trade.exit_price == pytest.approx(7723.5)
        assert trade.pnl_usd == pytest.approx((ENTRY - 7723.5) * 5 * MES)
        assert trade.outcome == "LOSS"

    def test_the_legacy_path_without_a_quantity_is_unchanged(self, db):
        """`fill_qty=None` — shadow twins and BarLevelDetector. They report no
        per-leg quantity, which honestly means "everything left goes at this
        fill"; that path must stay byte-identical to pre-T-251."""
        mgr = TradeManager(db=db)
        trade = _trade_1008(db)

        mgr.on_stop_hit(trade.id, fill_ts=_ts(35, 42), fill_price=7723.5)

        assert "exit_fills" not in (trade.quality or {})
        assert trade.state == "CLOSED"
        assert trade.exit_reason == "STOP_HIT"
        assert trade.pnl_usd == pytest.approx((ENTRY - 7723.5) * 5 * MES)


class _FakeGateway:
    def __init__(self):
        self.closes = []

    def on_trade_close(self, payload):
        self.closes.append(payload)


class TestFillPollerDoesNotFreeTheSlotOnAPartialStop:
    """`_notify_gateway_close` books the day's P&L, frees the slot and pushes
    "trade closed" to the phone. On #1008 all three fired 32 minutes early."""

    def _poller(self, db, monkeypatch):
        from backend.v9.services import ntfy_notify
        from backend.v9.services.fill_poller import FillPoller
        # Belt-and-braces: never let a test push to Michael's phone.
        monkeypatch.setattr(ntfy_notify, "on_fill", lambda *a, **k: None)

        mgr = TradeManager(db=db)
        trade = _trade_1008(db)
        _bank_the_two_targets(mgr, trade.id)

        gw = _FakeGateway()
        fp = FillPoller(trade_manager=mgr, gateway=gw)
        for oid in (C4_STOP[0], C3_STOP[0]):
            fp.register_order(oid, trade.id)
        return fp, gw, trade

    def test_partial_stop_does_not_notify_then_the_final_one_does(
            self, db, monkeypatch):
        fp, gw, trade = self._poller(db, monkeypatch)

        oid, px, qty = C4_STOP
        fp._process_fill({"kind": "STOP", "order_id": oid, "price": px,
                          "ts": 1788888942, "contracts": qty})

        assert trade.state == "PARTIAL"
        assert gw.closes == [], (
            "the slot, the daily P&L and the phone message must wait for the "
            "contract that is still in the market")

        oid, px, qty = C3_STOP
        fp._process_fill({"kind": "STOP", "order_id": oid, "price": px,
                          "ts": 1788890882, "contracts": qty})

        assert trade.state == "CLOSED"
        assert len(gw.closes) == 1
        assert gw.closes[0]["trade_id"] == trade.id
        assert gw.closes[0]["outcome"] == "STOP"
        assert gw.closes[0]["pnl_usd"] == pytest.approx(32.5)
