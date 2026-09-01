"""T-211 — the T0 exit-fill leg must survive to the DB, and the dedup key must
compare instants rather than timezone spellings.

ROOT (proven from production, 2026-09-01):
`TradeManager.on_target_hit`'s `target == "T0"` branch `return`s BEFORE the
`self._db.flush()` that every other target branch falls through to. The leg
that `_record_exit_fill` just appended to `trade.quality` lives only in the
SQLAlchemy identity map; minutes later the NEXT fill re-reads `quality` from a
refreshed session, does not see the T0 leg, and appends onto the stale list —
so the leg is not merely "not written", it is OVERWRITTEN. `_log_management`
writes its own row, which is why `T0_HIT` survives in
`v9_trade_management_log` while the fill does not. That asymmetry was the
fingerprint:

  #942  T0_HIT 17:22:24 logged · Sierra order 10845 T0 1c @7663.25 (entry
        7660.25, +3.00pt) · absent from quality.exit_fills · booked at the
        stop instead (+0.25pt) → $13.75 error.
  #948  T0_HIT 18:47:08 logged · Sierra order 10857 T0 1c @7671.75 (entry
        7668.75, +3.00pt) · absent · booked at the stop (-7.50pt) → $52.50
        error on a trade booked -$187.50 whose true P&L was -$135.00.

SECOND defect, same function: the dedup key embedded `ts.isoformat()`
verbatim, and the call sites disagree on zone —
`on_target_hit`/`on_stop_hit` pass UTC, `update_closed_trade_pnl` passes
`trade.exit_ts` rendered by the ORM in the session zone. Observed raw on #948:
"2026-09-01T16:15:15+00:00" and "2026-09-01T19:15:15+03:00" — same second.

Anti-tautological: drives the REAL TradeManager methods with a fake DB session
that records flush() calls; no reimplementation of the ledger.

if reverted → RED because: removing the flush() from the T0 branch makes
test_t0_branch_flushes fail; removing the UTC normalisation makes
test_dedup_is_tz_insensitive fail (the leg gets appended twice).
"""
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace

import pytest


class _FakeDB:
    def __init__(self):
        self.flushes = 0

    def flush(self):
        self.flushes += 1

    def commit(self):
        pass


def _mk_manager():
    """Real TradeManager, no __init__ side effects."""
    from backend.v9.services.trade_manager.manager import TradeManager
    tm = TradeManager.__new__(TradeManager)
    tm._db = _FakeDB()
    return tm


def _mk_trade(**kw):
    t = SimpleNamespace(id=942, quality={}, direction="LONG", entry_price=7660.25,
                        t1=7667.75, t2=7669.0, t3=7679.0, t4=None, stop=7652.75,
                        state="PARTIAL")
    for k, v in kw.items():
        setattr(t, k, v)
    return t


# ── defect 1: the T0 branch must flush ───────────────────────────────────────

def test_t0_branch_flushes():
    """Static proof on the real source: the `target == "T0"` block contains a
    `self._db.flush()` before its `return`.

    A behavioural driver of on_target_hit would need the whole state machine,
    emitter and snapshot stack; the defect is precisely the presence or absence
    of one call inside one branch, so that is what is asserted — on the real
    file, not on a copy.
    """
    import inspect
    from backend.v9.services.trade_manager.manager import TradeManager

    lines = [ln for ln in inspect.getsource(TradeManager.on_target_hit).splitlines()]
    # code lines only — the explanatory comment legitimately contains the word
    # "return", and matching on it would make this test lie.
    code = [ln for ln in lines if not ln.strip().startswith("#")]
    start = next(i for i, ln in enumerate(code) if 'if target == "T0":' in ln)
    end = next(i for i, ln in enumerate(code[start:], start)
               if ln.strip() == "return")
    t0_block = "\n".join(code[start:end])
    assert "self._db.flush()" in t0_block, (
        "T-211 regression: the T0 branch returns without flushing — the "
        "exit-fill leg will be lost when the session refreshes.\n" + t0_block)


def test_t0_branch_flush_precedes_the_return():
    """Order matters: a flush AFTER the return is dead code."""
    import inspect
    from backend.v9.services.trade_manager.manager import TradeManager

    code = [ln for ln in inspect.getsource(TradeManager.on_target_hit).splitlines()
            if not ln.strip().startswith("#")]
    start = next(i for i, ln in enumerate(code) if 'if target == "T0":' in ln)
    ret = next(i for i, ln in enumerate(code[start:], start)
               if ln.strip() == "return")
    flush = next((i for i, ln in enumerate(code[start:ret], start)
                  if "self._db.flush()" in ln), None)
    assert flush is not None and flush < ret, (
        f"flush index={flush} return index={ret}")


# ── defect 2: the dedup key must be timezone-insensitive ─────────────────────

def test_dedup_is_tz_insensitive():
    """The same instant in two zones is ONE fill, not two."""
    tm = _mk_manager()
    trade = _mk_trade()

    utc_ts = datetime(2026, 9, 1, 16, 15, 15, tzinfo=timezone.utc)
    il_ts = utc_ts.astimezone(timezone(timedelta(hours=3)))
    assert utc_ts.isoformat() != il_ts.isoformat()   # different spelling…
    assert utc_ts == il_ts                           # …same instant

    tm._record_exit_fill(trade, "STOP", 7661.25, qty=2, order_id=10861, ts=utc_ts)
    assert len(trade.quality["exit_fills"]) == 1
    tm._record_exit_fill(trade, "STOP", 7661.25, qty=2, order_id=10861, ts=il_ts)
    assert len(trade.quality["exit_fills"]) == 1, (
        "T-211 regression: the same fill was booked twice because the dedup "
        "key compared the timezone spelling instead of the instant: "
        + repr(trade.quality["exit_fills"]))


def test_dedup_still_separates_distinct_orders():
    """Anti-tautology: normalising must NOT merge two real Sierra legs.

    #942 stopped out in two pieces at the same second and the same price —
    orders 10852 (group 3) and 10854 (group 4). Both are real contracts.
    """
    tm = _mk_manager()
    trade = _mk_trade()
    ts = datetime(2026, 9, 1, 14, 58, 38, tzinfo=timezone.utc)

    tm._record_exit_fill(trade, "STOP", 7660.5, qty=1, order_id=10852, ts=ts)
    tm._record_exit_fill(trade, "STOP", 7660.5, qty=1, order_id=10854,
                         ts=ts.astimezone(timezone(timedelta(hours=3))))
    assert len(trade.quality["exit_fills"]) == 2, trade.quality["exit_fills"]


def test_stored_ts_is_utc():
    """The persisted ts must be the UTC rendering, so the ledger is readable
    without knowing which call site wrote the row."""
    tm = _mk_manager()
    trade = _mk_trade()
    il = datetime(2026, 9, 1, 19, 15, 15,
                  tzinfo=timezone(timedelta(hours=3)))
    tm._record_exit_fill(trade, "STOP", 7661.25, qty=1, order_id=10864, ts=il)
    stored = trade.quality["exit_fills"][0]["ts"]
    assert stored.endswith("+00:00"), stored
    assert stored.startswith("2026-09-01T16:15:15"), stored


def test_legacy_row_with_local_zone_is_deduped():
    """A ledger already holding the '+03:00' spelling must not gain a twin."""
    tm = _mk_manager()
    trade = _mk_trade(quality={"exit_fills": [
        {"kind": "STOP", "price": 7661.25, "qty": 1, "order_id": 10864,
         "column": None, "ts": "2026-09-01T19:15:15+03:00"},
    ]})
    tm._record_exit_fill(trade, "STOP", 7661.25, qty=1, order_id=10864,
                         ts=datetime(2026, 9, 1, 16, 15, 15, tzinfo=timezone.utc))
    assert len(trade.quality["exit_fills"]) == 1, trade.quality["exit_fills"]
