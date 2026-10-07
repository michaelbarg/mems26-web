# -*- coding: utf-8 -*-
"""T-545 — W2 EXIT-TRACK closed a trade from ANOTHER trade's broker event.

The 05.10 19:24–19:25 shape (SUPERVISOR_2026-10-05 §19:36; same class as #1337 /
T-290): #3038 CEILING_FLIP_SHORT closed; the feeder scanned its CLOSED_TRADE_PNL
(−27.5) at 19:24:06. #3046 GB100 LONG was CREATED at 19:25:04 (PENDING, order
just queued, Sierra flat = its initial state). One second later W2 summed the
58-second-old line into #3046 — it lay inside the 60s `entry slack` below
created_at — saw Sierra flat, and closed #3046 as LOSS −27.5 with a synthesized
exit_price 7810.5. Sierra then filled #3046 and ran it to +53.75 with the books
saying closed (slot freed, position untracked).

W2_EXIT_OWNERSHIP_V1 (default OFF — books only):
  (1) the floor of a trade's legs is never before its created_at;
  (2) a PENDING trade (never observed in position) cannot be closed by the
      activity fallback — the legs are offered post-hoc to the CLOSED trade
      they belong to and otherwise stay buffered.
Flag OFF keeps today's behaviour byte-for-byte (the first test pins it).

Fixture = the T-436b one (FillPoller via __new__, SimpleNamespace TradeManager).
"""
import json
import types
from datetime import datetime, timedelta, timezone

import pytest

import backend.v9.services.fill_poller as fp


class _FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def filter(self, *_a, **_k):
        return self

    def all(self):
        return list(self._rows)


class _FakeDB:
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


def _mk_trade(*, tid, state, created_at, entry_ts=None, exit_ts=None, mode="live",
              direction="LONG", entry_price=7816.0, pnl_usd=None, exit_reason=None):
    t = types.SimpleNamespace()
    t.id = tid
    t.state = state
    t.mode = mode
    t.direction = direction
    t.entry_price = entry_price
    t.stop = entry_price - 8 if direction == "LONG" else entry_price + 8
    t.created_at = created_at
    t.entry_ts = entry_ts
    t.exit_ts = exit_ts
    t.exit_price = None
    t.exit_reason = exit_reason
    t.outcome = None
    t.pnl_usd = pnl_usd
    t.pnl_sierra = None
    t.quality = {"contracts": 1}
    return t


def _mk_poller(active, closed):
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

    tm.on_stop_hit = _on_stop_hit
    tm.close_trade = lambda trade_id, reason=None, exit_price=None, outcome_override=None: tm._closed.append((trade_id, reason))
    tm._set_outcome = _set_outcome
    poller._tm = tm
    poller._gateway = None
    poller._gw_closes = []
    poller._notify_gateway_close = lambda tid, outcome: poller._gw_closes.append((tid, outcome))
    return poller, tm


@pytest.fixture
def env(tmp_path, monkeypatch):
    """EXIT_TRACK_ACTIVITY_V1 on, journal + state under tmp, Sierra FLAT (the
    state a PENDING trade is born in), controllable wall clock. The ownership
    flag is NOT set here — each test chooses."""
    monkeypatch.setenv("EXIT_TRACK_ACTIVITY_V1", "1")
    monkeypatch.setenv("FILL_POLLER_WARN_THROTTLE_S", "0")
    monkeypatch.delenv("W2_EXIT_OWNERSHIP_V1", raising=False)
    events_path = tmp_path / "trade_activity_events.jsonl"
    state_path = tmp_path / "sierra_state.json"
    monkeypatch.setattr(fp, "ACTIVITY_EVENTS_PATH", events_path)
    monkeypatch.setattr(fp, "STATE_PATH", state_path)
    clock = {"now": datetime.now(timezone.utc).timestamp()}
    monkeypatch.setattr(fp, "time", types.SimpleNamespace(time=lambda: clock["now"]))
    events_path.write_text(json.dumps({"type": "POSITION_CHANGE", "new_qty": 0}) + "\n")
    state_path.write_text(json.dumps({"position_qty": 0}))
    return types.SimpleNamespace(events=events_path, state=state_path, clock=clock,
                                 monkeypatch=monkeypatch)


def _append(env, *events):
    with open(env.events, "a", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev) + "\n")


def _pnl_event(pnl, scan_dt, line, account="37138283"):
    return {"type": "CLOSED_TRADE_PNL", "pnl": pnl, "symbol": "MESZ26_FUT_CME.",
            "scan_ts": scan_dt.isoformat(), "line": line, "account": account,
            "is_sim": False}


def _now():
    return datetime.now(timezone.utc)


def _the_05_10_shape(env, *, flag):
    """#3038's leg scanned at T, #3046 created at T+58s (PENDING, Sierra flat).
    Returns (poller, tm, t3046, t3038) after the poll that reads the line."""
    if flag:
        env.monkeypatch.setenv("W2_EXIT_OWNERSHIP_V1", "1")
    now = _now()
    scan = now - timedelta(seconds=200)                     # 19:24:06
    created = scan + timedelta(seconds=58)                  # 19:25:04
    t3038 = _mk_trade(tid=3038, state="CLOSED", created_at=scan - timedelta(minutes=9),
                      entry_ts=scan - timedelta(minutes=8), exit_ts=scan - timedelta(seconds=30),
                      direction="SHORT", entry_price=7822.0, pnl_usd=-27.5, exit_reason="STOP_HIT")
    t3046 = _mk_trade(tid=3046, state="PENDING", created_at=created, entry_ts=None,
                      direction="LONG", entry_price=7816.0)
    poller, tm = _mk_poller(active=[t3046], closed=[t3038])
    poller._check_activity_exits()                          # init read position
    _append(env, _pnl_event(-27.5, scan, line=62))
    poller._check_activity_exits()
    return poller, tm, t3046, t3038


def test_flag_off_pins_the_05_10_behaviour_the_old_line_closes_the_new_pending_trade(env):
    """Characterisation, flag OFF: the 58s-old line is inside the 60s slack,
    Sierra is flat → #3046 is closed as LOSS −27.5 one poll after creation.
    This is the bug; it stays byte-identical until Michael turns the flag on."""
    poller, tm, t3046, t3038 = _the_05_10_shape(env, flag=False)
    assert t3046.state == "CLOSED"
    assert t3046.pnl_usd == -27.5 and t3046.pnl_sierra == -27.5
    assert t3046.exit_reason == "BRACKET_EXIT_ACTIVITY"
    assert tm._stop_hits[0][0] == 3046
    assert poller._gw_closes == [(3046, "BRACKET_EXIT_ACTIVITY")]
    assert t3038.pnl_sierra is None                         # the real owner got nothing


def test_flag_on_the_old_line_never_touches_the_pending_trade_and_lands_on_its_owner(env):
    """Flag ON: floor = created_at ⇒ the line is not #3046's; #3046 stays
    PENDING, slot untouched; the line is attributed post-hoc to #3038
    (CLOSED, pnl_sierra NULL, exit_ts within ±5 min, settled)."""
    poller, tm, t3046, t3038 = _the_05_10_shape(env, flag=True)
    assert t3046.state == "PENDING"
    assert t3046.pnl_usd is None and t3046.pnl_sierra is None
    assert tm._stop_hits == [] and tm._closed == []
    assert poller._gw_closes == []
    assert t3038.pnl_sierra == -27.5
    assert t3038.pnl_usd == -27.5 and t3038.exit_reason == "STOP_HIT"   # books untouched
    assert poller._pnl_unattributed == []


def test_flag_on_a_line_after_creation_while_still_pending_is_held_not_closed(env):
    """A line scanned AFTER created_at but with the trade still PENDING (never
    in position): Sierra flat is its initial state, not an exit — hold."""
    env.monkeypatch.setenv("W2_EXIT_OWNERSHIP_V1", "1")
    now = _now()
    created = now - timedelta(seconds=40)
    scan = created + timedelta(seconds=10)
    trade = _mk_trade(tid=3191, state="PENDING", created_at=created, direction="LONG")
    poller, tm = _mk_poller(active=[trade], closed=[])
    poller._check_activity_exits()
    _append(env, _pnl_event(-17.5, scan, line=9))
    poller._check_activity_exits()
    assert trade.state == "PENDING"
    assert tm._stop_hits == [] and tm._closed == [] and poller._gw_closes == []
    assert len(poller._pnl_unattributed) == 1                # held, not dropped
    poller._check_activity_exits()                            # no new bytes — still held
    assert len(poller._pnl_unattributed) == 1


def test_flag_on_filled_trade_flat_still_closes_exactly_as_before(env):
    """The legitimate W2 path is untouched: FILLED (seen in position), the leg
    scanned after entry, Sierra flat ⇒ on_stop_hit + Sierra P&L."""
    env.monkeypatch.setenv("W2_EXIT_OWNERSHIP_V1", "1")
    now = _now()
    entry = now - timedelta(minutes=3)
    scan = now - timedelta(seconds=20)
    trade = _mk_trade(tid=513, state="FILLED", created_at=entry - timedelta(seconds=3),
                      entry_ts=entry, direction="LONG", entry_price=7478.0)
    poller, tm = _mk_poller(active=[trade], closed=[])
    poller._check_activity_exits()
    _append(env, _pnl_event(-35.0, scan, line=120))
    poller._check_activity_exits()
    assert trade.state == "CLOSED"
    assert trade.pnl_usd == -35.0 and trade.pnl_sierra == -35.0
    assert trade.exit_reason == "BRACKET_EXIT_ACTIVITY"
    assert trade.exit_price == 7471.0                          # 7478 − 35/5
    assert poller._gw_closes == [(513, "BRACKET_EXIT_ACTIVITY")]
    assert poller._pnl_unattributed == []


def test_flag_on_filled_trade_keeps_the_entry_slack_but_not_below_created_at(env):
    """entry_ts stamped 30s late is still covered (floor = entry_ts − 60s), yet
    the floor never drops below created_at."""
    env.monkeypatch.setenv("W2_EXIT_OWNERSHIP_V1", "1")
    now = _now()
    created = now - timedelta(minutes=2)
    trade = _mk_trade(tid=7, state="FILLED", created_at=created,
                      entry_ts=created + timedelta(seconds=30))
    floor = fp.FillPoller._pnl_trade_floor(trade)
    assert floor == created                                    # max(created, entry−60s)
    env.monkeypatch.delenv("W2_EXIT_OWNERSHIP_V1")
    assert fp.FillPoller._pnl_trade_floor(trade) == created - timedelta(seconds=30)
