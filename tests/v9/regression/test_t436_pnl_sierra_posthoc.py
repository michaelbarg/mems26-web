"""T-436b — the broker's P&L must reach EVERY closed live/demo trade.

Root (verified 2026-09-23, code + DB + journal): `fill_poller._check_activity_exits`
used CLOSED_TRADE_PNL only as a FALLBACK closer. The activity feeder is a 60s
`strings` pass over Sierra's binary TradeActivityLog, so by the time the line
surfaced (measured 21-43s after exit_ts on 22.09's closes) the trade had already
been closed by the normal path (T1 fill from the DLL fills journal, MAE_SCRATCH
flatten via exit_verifier, stop fill) → "no open demo/live trade" → `return`,
with `_activity_exit_pos` already past the line. pnl_sierra stayed NULL on
essentially every closed live trade although the journal carried the number.
Second loss: an open trade + Sierra not flat (the T1 leg of a 2-contract exit)
also `return`ed and dropped what was read.

Fix: events are buffered (`_pnl_unattributed`) and attributed — (a) an open
trade keeps the existing close path; (b) otherwise POST-HOC: the CLOSED
live/demo trade with pnl_sierra NULL whose exit_ts is nearest the group's
scan_ts (±5 min) gets ONLY pnl_sierra. Unclaimed events wait for the trade to
close and expire after 30 min with one warning.

Fixture style mirrors backend/v9/tests/test_w2_exit_tracking.py (poller via
__new__, SimpleNamespace TradeManager) — no DB server: the session is a double
whose query() returns the CLOSED rows; the poller re-checks every condition in
Python, so the double cannot make a wrong row pass.
"""
import json
import logging
import types
from datetime import datetime, timedelta, timezone

import pytest

import backend.v9.services.fill_poller as fp


# ── doubles ──────────────────────────────────────────────────────────────────

class _FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def filter(self, *_a, **_k):
        return self

    def all(self):
        return list(self._rows)


class _FakeDB:
    """The shared TradeManager session: query() hands back the CLOSED rows."""

    def __init__(self, closed):
        self.closed = closed
        self.flushes = 0
        self.commits = 0

    def query(self, _model):
        return _FakeQuery(self.closed)

    def flush(self):
        self.flushes += 1

    def commit(self):
        self.commits += 1


def _mk_trade(*, tid, state, exit_ts=None, entry_ts=None, mode="live",
              direction="LONG", entry_price=7478.0, contracts=1,
              pnl_usd=None, exit_reason=None):
    t = types.SimpleNamespace()
    t.id = tid
    t.state = state
    t.mode = mode
    t.direction = direction
    t.entry_price = entry_price
    t.stop = entry_price - 16 if direction == "LONG" else entry_price + 16
    t.entry_ts = entry_ts
    t.created_at = (entry_ts - timedelta(seconds=3)) if entry_ts else None
    t.exit_ts = exit_ts
    t.exit_price = None
    t.exit_reason = exit_reason
    t.outcome = None
    t.pnl_usd = pnl_usd
    t.pnl_sierra = None
    t.quality = {"contracts": contracts}
    return t


def _mk_poller(active, closed, *, clock):
    """FillPoller with a stub TM: `active` feeds get_active_trades, `closed`
    feeds the session's query(). `clock` is a dict {"now": epoch} driving
    fill_poller's time.time() (first_seen / expiry)."""
    poller = fp.FillPoller.__new__(fp.FillPoller)
    poller._running = False
    poller._last_mtime = 0.0
    poller._last_result_mtime = 0.0
    poller._processed_count = 0
    poller._last_poll_ts = 0.0
    poller._order_map = {}
    poller._orphan_fills = []
    poller._orphan_count = 0
    poller._activity_exit_pos = None
    # NOT setting _pnl_unattributed / _pnl_consumed on purpose: the W2 fixture
    # (and any __new__-built poller) must get the lazy buffer.

    tm = types.SimpleNamespace()
    tm.get_active_trades = lambda: list(active)
    tm._db = _FakeDB(closed)
    tm._stop_hits = []
    tm._closed = []

    def _on_stop_hit(trade_id, fill_ts=None, fill_price=None):
        tm._stop_hits.append((trade_id, fill_ts, fill_price))
        for t in active:
            if t.id == trade_id:
                t.state = "CLOSED"
                t.exit_ts = fill_ts
                t.exit_price = fill_price
                t.exit_reason = "STOP_HIT"
                break

    def _set_outcome(trade):
        if trade.pnl_usd is not None:
            trade.outcome = "WIN" if trade.pnl_usd > 0 else ("LOSS" if trade.pnl_usd < 0 else "BE")

    def _close_trade(trade_id, reason=None, exit_price=None, outcome_override=None):
        tm._closed.append((trade_id, reason))

    tm.on_stop_hit = _on_stop_hit
    tm.close_trade = _close_trade
    tm._set_outcome = _set_outcome
    poller._tm = tm
    poller._gateway = None
    poller._gw_closes = []
    poller._notify_gateway_close = lambda tid, outcome: poller._gw_closes.append((tid, outcome))
    return poller, tm


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Flag ON, journal + state paths under tmp, controllable wall clock."""
    monkeypatch.setenv("EXIT_TRACK_ACTIVITY_V1", "1")
    monkeypatch.setenv("FILL_POLLER_WARN_THROTTLE_S", "0")
    events_path = tmp_path / "trade_activity_events.jsonl"
    state_path = tmp_path / "sierra_state.json"
    monkeypatch.setattr(fp, "ACTIVITY_EVENTS_PATH", events_path)
    monkeypatch.setattr(fp, "STATE_PATH", state_path)
    clock = {"now": datetime.now(timezone.utc).timestamp()}
    monkeypatch.setattr(fp, "time", types.SimpleNamespace(time=lambda: clock["now"]))
    # first call only initialises the read position at EOF
    events_path.write_text(json.dumps({"type": "POSITION_CHANGE", "new_qty": 0}) + "\n")
    state_path.write_text(json.dumps({"position_qty": 0}))
    return types.SimpleNamespace(events=events_path, state=state_path, clock=clock)


def _append(env, *events):
    with open(env.events, "a", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev) + "\n")


def _pnl_event(pnl, scan_dt, line, account="37138283"):
    """Exactly the feeder's shape (22.09 fixture): per-contract closes are
    separate lines sharing one scan_ts."""
    return {"type": "CLOSED_TRADE_PNL", "pnl": pnl, "symbol": "MESZ26_FUT_CME.",
            "scan_ts": scan_dt.isoformat(), "line": line, "account": account,
            "is_sim": False}


def _now():
    return datetime.now(timezone.utc)


# ── (i) trade already CLOSED 40s before the line surfaced ────────────────────

def test_closed_trade_gets_pnl_sierra_posthoc_only(env, caplog):
    """The 22.09 shape: #2140 closed by T1 fill at 15:37:25, the feeder scanned
    the +26.25 line at 15:37:46. Only pnl_sierra may change."""
    now = _now()
    scan = now - timedelta(seconds=200)          # settled (> 90s past exit)
    exit_ts = scan - timedelta(seconds=40)
    trade = _mk_trade(tid=2140, state="CLOSED", exit_ts=exit_ts,
                      entry_ts=exit_ts - timedelta(minutes=7), pnl_usd=28.75,
                      exit_reason="T1_HIT")
    poller, tm = _mk_poller(active=[], closed=[trade], clock=env.clock)
    poller._check_activity_exits()                # init read position
    _append(env, _pnl_event(26.25, scan, line=457))

    with caplog.at_level(logging.WARNING, logger="fill_poller"):
        poller._check_activity_exits()

    assert trade.pnl_sierra == 26.25
    assert trade.pnl_usd == 28.75                 # books untouched
    assert trade.state == "CLOSED" and trade.exit_reason == "T1_HIT"
    assert trade.exit_ts == exit_ts
    assert tm._stop_hits == [] and tm._closed == []   # no close path ran
    assert tm._db.flushes == 1 and tm._db.commits == 1
    assert poller._pnl_unattributed == []
    assert any("T-436 pnl_sierra=26.25 attributed post-hoc to trade 2140" in r.getMessage()
               for r in caplog.records)
    assert not any("MIXED?" in r.getMessage() for r in caplog.records)


# ── (ii) not closed yet → buffered, attributed on a later poll ───────────────

def test_event_waits_in_buffer_until_the_trade_closes(env):
    """A 2-contract trade after its T1 fill is PARTIAL — neither open
    (FILLED/PENDING) nor CLOSED. Its runner closes later; the buffered line
    must still land."""
    now = _now()
    scan = now - timedelta(seconds=200)
    trade = _mk_trade(tid=600, state="PARTIAL", entry_ts=scan - timedelta(minutes=5),
                      contracts=1)
    closed = []
    poller, tm = _mk_poller(active=[], closed=closed, clock=env.clock)
    poller._check_activity_exits()
    _append(env, _pnl_event(-36.25, scan, line=270))

    poller._check_activity_exits()                # nothing to attribute yet
    assert trade.pnl_sierra is None
    assert len(poller._pnl_unattributed) == 1

    poller._check_activity_exits()                # no new bytes — still held
    assert len(poller._pnl_unattributed) == 1

    # the runner closes 30s after the scan (normal path), then the poll sees it
    trade.state = "CLOSED"
    trade.exit_ts = scan + timedelta(seconds=30)
    closed.append(trade)
    env.clock["now"] += 5
    poller._check_activity_exits()

    assert trade.pnl_sierra == -36.25
    assert trade.pnl_usd is None                  # never invented
    assert poller._pnl_unattributed == []


# ── (iii) open trade present → the W2 close path is unchanged ───────────────

def test_open_trade_keeps_existing_close_path(env):
    """Byte-for-byte W2: open FILLED trade + Sierra flat → on_stop_hit,
    pnl_usd = pnl_sierra = Sierra's number, BRACKET_EXIT_ACTIVITY."""
    now = _now()
    scan = now - timedelta(seconds=20)
    trade = _mk_trade(tid=513, state="FILLED", entry_ts=scan - timedelta(minutes=3),
                      direction="LONG", entry_price=7478.0, contracts=2)
    poller, tm = _mk_poller(active=[trade], closed=[], clock=env.clock)
    poller._check_activity_exits()
    _append(env, _pnl_event(-35.0, scan, line=120))

    poller._check_activity_exits()

    assert trade.state == "CLOSED"
    assert trade.pnl_usd == -35.0 and trade.pnl_sierra == -35.0
    assert trade.exit_reason == "BRACKET_EXIT_ACTIVITY"
    assert tm._stop_hits[0][0] == 513
    assert trade.exit_price == 7474.5             # 7478 + (-35/2/5)
    assert poller._gw_closes == [(513, "BRACKET_EXIT_ACTIVITY")]
    assert poller._pnl_unattributed == []         # consumed by the close
    assert tm._db.commits == 0                    # the W2 path never committed


def test_open_trade_not_flat_holds_the_leg_instead_of_dropping_it(env):
    """Second loss path: the T1 leg's line lands while the runner still works.
    It used to be dropped; now it waits and is summed on the full exit."""
    now = _now()
    scan1 = now - timedelta(seconds=70)
    scan2 = now - timedelta(seconds=10)
    trade = _mk_trade(tid=700, state="FILLED", entry_ts=scan1 - timedelta(minutes=4),
                      direction="SHORT", entry_price=7500.0, contracts=2)
    poller, tm = _mk_poller(active=[trade], closed=[], clock=env.clock)
    poller._check_activity_exits()

    env.state.write_text(json.dumps({"position_qty": -1}))   # runner still on
    _append(env, _pnl_event(43.75, scan1, line=300))
    poller._check_activity_exits()
    assert trade.state == "FILLED"
    assert len(poller._pnl_unattributed) == 1     # held, not dropped

    env.state.write_text(json.dumps({"position_qty": 0}))
    _append(env, _pnl_event(-20.0, scan2, line=340))
    poller._check_activity_exits()
    assert trade.state == "CLOSED"
    assert trade.pnl_usd == 23.75 and trade.pnl_sierra == 23.75
    assert poller._pnl_unattributed == []


# ── (iv) nobody claims it → dropped after 30 min with ONE warning ────────────

def test_unclaimed_event_expires_after_30_min_with_warning(env, caplog):
    now = _now()
    scan = now - timedelta(seconds=200)
    poller, tm = _mk_poller(active=[], closed=[], clock=env.clock)
    poller._check_activity_exits()
    _append(env, _pnl_event(-12.5, scan, line=900))
    poller._check_activity_exits()
    assert len(poller._pnl_unattributed) == 1

    env.clock["now"] += 29 * 60
    poller._check_activity_exits()
    assert len(poller._pnl_unattributed) == 1     # 29 min: still waiting

    env.clock["now"] += 2 * 60
    with caplog.at_level(logging.WARNING, logger="fill_poller"):
        poller._check_activity_exits()
    assert poller._pnl_unattributed == []
    drops = [r for r in caplog.records if "T-436 dropped 1 unattributed" in r.getMessage()]
    assert len(drops) == 1
    assert "-12.50" in drops[0].getMessage()


# ── (v) two legs, same scan_ts → one group, summed ───────────────────────────

def test_two_legs_same_scan_ts_are_summed(env, caplog):
    now = _now()
    scan = now - timedelta(seconds=200)
    exit_ts = scan - timedelta(seconds=25)
    trade = _mk_trade(tid=800, state="CLOSED", exit_ts=exit_ts,
                      entry_ts=exit_ts - timedelta(minutes=9), contracts=2,
                      pnl_usd=-806.25, exit_reason="STOP_FILL")
    poller, tm = _mk_poller(active=[], closed=[trade], clock=env.clock)
    poller._check_activity_exits()
    _append(env, _pnl_event(-198.75, scan, line=121), _pnl_event(-607.5, scan, line=157))

    with caplog.at_level(logging.WARNING, logger="fill_poller"):
        poller._check_activity_exits()

    assert trade.pnl_sierra == -806.25
    assert trade.pnl_usd == -806.25
    assert poller._pnl_unattributed == []
    msg = next(r.getMessage() for r in caplog.records if "attributed post-hoc" in r.getMessage())
    assert "2 leg(s)" in msg and "MIXED?" not in msg


# ── extra pins ───────────────────────────────────────────────────────────────

def test_t1_leg_scanned_minutes_earlier_is_folded_into_the_same_trade(env):
    """2-contract trade: T1 leg line at T-10min (its own group), runner line
    after the close. Both are the trade's legs — pnl_sierra is their sum, not
    the runner alone."""
    now = _now()
    scan_runner = now - timedelta(seconds=200)
    exit_ts = scan_runner - timedelta(seconds=30)
    scan_t1 = exit_ts - timedelta(minutes=10)
    trade = _mk_trade(tid=900, state="PARTIAL", entry_ts=scan_t1 - timedelta(minutes=6),
                      contracts=2)
    closed = []
    poller, tm = _mk_poller(active=[], closed=closed, clock=env.clock)
    poller._check_activity_exits()
    _append(env, _pnl_event(12.5, scan_t1, line=50))
    poller._check_activity_exits()
    assert len(poller._pnl_unattributed) == 1

    trade.state = "CLOSED"
    trade.exit_ts = exit_ts
    closed.append(trade)
    _append(env, _pnl_event(-30.0, scan_runner, line=88))
    env.clock["now"] += 5                          # past the 2s lookup cadence
    poller._check_activity_exits()

    assert trade.pnl_sierra == -17.5
    assert poller._pnl_unattributed == []


def test_posthoc_lookup_runs_on_a_cadence_not_every_tick(env):
    """A held event must not cost a SELECT on every 0.25s poll: the lookup
    runs every _PNL_POSTHOC_EVERY_S, and the buffer keeps the event meanwhile."""
    now = _now()
    scan = now - timedelta(seconds=200)
    poller, tm = _mk_poller(active=[], closed=[], clock=env.clock)
    queries = []
    tm._db.query = lambda model: queries.append(model) or _FakeQuery([])
    poller._check_activity_exits()
    _append(env, _pnl_event(-2.5, scan, line=11))
    for _ in range(4):                             # same wall-clock instant
        poller._check_activity_exits()
    assert len(queries) == 1
    env.clock["now"] += fp._PNL_POSTHOC_EVERY_S + 0.5
    poller._check_activity_exits()
    assert len(queries) == 2
    assert len(poller._pnl_unattributed) == 1


def test_more_legs_than_contracts_is_written_but_flagged_mixed(env, caplog):
    """T-402: Michael's manual contract in the same position makes the broker
    figure the POSITION's P&L. Still written — the warning says MIXED?."""
    now = _now()
    scan = now - timedelta(seconds=200)
    exit_ts = scan - timedelta(seconds=35)
    trade = _mk_trade(tid=950, state="CLOSED", exit_ts=exit_ts,
                      entry_ts=exit_ts - timedelta(minutes=4), contracts=1,
                      pnl_usd=12.5, exit_reason="T1_HIT")
    poller, tm = _mk_poller(active=[], closed=[trade], clock=env.clock)
    poller._check_activity_exits()
    _append(env, _pnl_event(12.5, scan, line=10), _pnl_event(11.25, scan, line=46))

    with caplog.at_level(logging.WARNING, logger="fill_poller"):
        poller._check_activity_exits()

    assert trade.pnl_sierra == 23.75
    msg = next(r.getMessage() for r in caplog.records if "attributed post-hoc" in r.getMessage())
    assert "MIXED?" in msg


def test_line_scanned_before_the_trade_existed_is_never_its_leg(env):
    """A manual close scanned 3 min before the trade's entry lies inside the
    ±5 min exit window of a short trade — it must not be attributed to it."""
    now = _now()
    scan = now - timedelta(seconds=200)
    exit_ts = scan + timedelta(seconds=60)                 # trade closed AFTER the scan
    trade = _mk_trade(tid=1000, state="CLOSED", exit_ts=exit_ts,
                      entry_ts=scan + timedelta(minutes=3), pnl_usd=5.0,
                      exit_reason="T1_HIT")
    # settle: exit_ts is 140s in the past — past the 90s settle
    poller, tm = _mk_poller(active=[], closed=[trade], clock=env.clock)
    poller._check_activity_exits()
    _append(env, _pnl_event(-100.0, scan, line=5))
    poller._check_activity_exits()

    assert trade.pnl_sierra is None
    assert len(poller._pnl_unattributed) == 1


def test_never_raises_into_the_poll_loop_when_the_session_cannot_query(env):
    """A session double without query() (the W2 fixture) → throttled warning,
    the event stays buffered, nothing propagates."""
    now = _now()
    scan = now - timedelta(seconds=200)
    poller, tm = _mk_poller(active=[], closed=[], clock=env.clock)
    tm._db = types.SimpleNamespace(flush=lambda: None)
    poller._check_activity_exits()
    _append(env, _pnl_event(-1.25, scan, line=77))
    poller._check_activity_exits()                # must not raise
    assert len(poller._pnl_unattributed) == 1


def test_source_still_reads_scan_ts_then_legacy_ts():
    """test_exit_track_dedup pins this literal; keep it after the refactor."""
    import inspect
    src = inspect.getsource(fp)
    assert 'get("scan_ts") or pnl_events[-1].get("ts")' in src


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
