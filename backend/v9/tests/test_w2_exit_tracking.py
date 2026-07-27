"""W2 — exit-tracking via CLOSED_TRADE_PNL fallback (trade 513, 2026-07-25).

Real incident: ZLR LONG trade 513 exited via Sierra bracket (stop hit) but
fill_poller never saw a STOP fill line (deployed DLL lacks Pipeline 5 fill
monitor). The trade stayed FILLED, slot blocked, PnL never recorded.

Fix: EXIT_TRACK_ACTIVITY_V1 — fill_poller watches trade_activity_events.jsonl
for CLOSED_TRADE_PNL events. When detected + Sierra position_qty=0 + a FILLED
trade exists → close it with Sierra's authoritative PnL.

Tests:
1. Flag OFF → no-op (byte-identical)
2. Flag ON + CLOSED_TRADE_PNL + flat → trade closed, PnL set, slot freed
3. Flag ON + CLOSED_TRADE_PNL but Sierra NOT flat → no close (partial exit)
4. Flag ON + CLOSED_TRADE_PNL but no FILLED trade → no crash, no close
5. Exit price back-computed correctly for LONG and SHORT
6. revert→RED: removing the fix makes tests 2-5 fail
"""
import json
import os
import types
from datetime import datetime, timezone
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]


def _mk_poller(tmp_path, trades, *, gateway=True):
    """Construct a FillPoller with stubs for TM + gateway."""
    from backend.v9.services import fill_poller as fp

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
    tm.get_active_trades = lambda: list(trades)
    tm._closed = []
    tm._stop_hits = []
    tm._db = types.SimpleNamespace(flush=lambda: None)

    def _on_stop_hit(trade_id, fill_ts=None, fill_price=None):
        tm._stop_hits.append((trade_id, fill_ts, fill_price))
        # Simulate what the real on_stop_hit does
        for t in trades:
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
        for t in trades:
            if t.id == trade_id:
                t.state = "CLOSED"
                t.exit_reason = reason
                if exit_price is not None:
                    t.exit_price = exit_price
                break

    tm.on_stop_hit = _on_stop_hit
    tm.close_trade = _close_trade
    tm._set_outcome = _set_outcome

    poller._tm = tm
    poller._gw_closes = []
    if gateway:
        poller._gateway = types.SimpleNamespace()
        poller._notify_gateway_close = lambda tid, outcome: poller._gw_closes.append((tid, outcome))
    else:
        poller._gateway = None
        poller._notify_gateway_close = lambda tid, outcome: None
    return poller, tm


def _mk_trade(*, tid=513, state="FILLED", mode="live", direction="LONG",
              entry_price=7478.0, contracts=2):
    t = types.SimpleNamespace()
    t.id = tid
    t.state = state
    t.mode = mode
    t.direction = direction
    t.entry_price = entry_price
    t.stop = entry_price - 16 if direction == "LONG" else entry_price + 16
    t.pnl_usd = None
    t.pnl_sierra = None
    t.exit_ts = None
    t.exit_price = None
    t.exit_reason = None
    t.outcome = None
    t.quality = {"contracts": contracts}
    return t


def _write_activity_events(path, events):
    """Write events to activity journal, return file path."""
    with open(path, "w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev) + "\n")
    return path


def _write_sierra_state(path, position_qty=0, **kwargs):
    data = {"position_qty": position_qty, **kwargs}
    path.write_text(json.dumps(data))
    return path


# ── Test 1: flag OFF → no-op ─────────────────────────────────────────────────

def test_flag_off_is_noop(tmp_path, monkeypatch):
    """EXIT_TRACK_ACTIVITY_V1 unset → _check_activity_exits does nothing."""
    monkeypatch.delenv("EXIT_TRACK_ACTIVITY_V1", raising=False)
    trade = _mk_trade()
    poller, tm = _mk_poller(tmp_path, [trade])

    events_path = tmp_path / "trade_activity_events.jsonl"
    _write_activity_events(events_path, [
        {"type": "CLOSED_TRADE_PNL", "ts": "2026-07-09T19:19:00+00:00", "pnl": -35.0},
    ])
    state_path = tmp_path / "sierra_state.json"
    _write_sierra_state(state_path, position_qty=0)

    import backend.v9.services.fill_poller as fp
    monkeypatch.setattr(fp, "ACTIVITY_EVENTS_PATH", events_path)
    monkeypatch.setattr(fp, "STATE_PATH", state_path)

    poller._check_activity_exits()

    assert trade.state == "FILLED"  # unchanged
    assert tm._stop_hits == []
    assert poller._gw_closes == []


# ── Test 2: flag ON + PnL event + flat → trade closed ────────────────────────

def test_activity_exit_closes_trade(tmp_path, monkeypatch):
    """CLOSED_TRADE_PNL + Sierra flat → trade closed with Sierra PnL."""
    monkeypatch.setenv("EXIT_TRACK_ACTIVITY_V1", "1")
    trade = _mk_trade(tid=513, direction="LONG", entry_price=7478.0, contracts=2)
    poller, tm = _mk_poller(tmp_path, [trade])

    events_path = tmp_path / "trade_activity_events.jsonl"
    state_path = tmp_path / "sierra_state.json"

    import backend.v9.services.fill_poller as fp
    monkeypatch.setattr(fp, "ACTIVITY_EVENTS_PATH", events_path)
    monkeypatch.setattr(fp, "STATE_PATH", state_path)

    # First call: initialize position (EOF)
    _write_activity_events(events_path, [
        {"type": "POSITION_CHANGE", "ts": "2026-07-09T18:55:00+00:00", "new_qty": 2},
    ])
    poller._check_activity_exits()
    assert trade.state == "FILLED"  # just initialized

    # Now append CLOSED_TRADE_PNL + make Sierra flat
    with open(events_path, "a") as f:
        f.write(json.dumps({
            "type": "CLOSED_TRADE_PNL",
            "ts": "2026-07-09T19:19:00+00:00",
            "pnl": -35.0,
        }) + "\n")
    _write_sierra_state(state_path, position_qty=0)

    poller._check_activity_exits()

    assert trade.state == "CLOSED"
    assert trade.pnl_usd == -35.0
    assert trade.pnl_sierra == -35.0
    assert trade.exit_reason == "BRACKET_EXIT_ACTIVITY"
    assert len(tm._stop_hits) == 1
    assert tm._stop_hits[0][0] == 513  # trade_id
    # Exit price back-computed: LONG, PnL=-35, 2 contracts, $5/pt
    # pts = -35 / 2 / 5 = -3.5 → exit = 7478 - 3.5 = 7474.5
    assert trade.exit_price == 7474.5
    # Gateway slot freed
    assert ("BRACKET_EXIT_ACTIVITY",) == (poller._gw_closes[0][1],)


# ── Test 3: Sierra NOT flat → no close ────────────────────────────────────────

def test_no_close_when_sierra_not_flat(tmp_path, monkeypatch):
    """If Sierra still has position (partial target hit), don't close."""
    monkeypatch.setenv("EXIT_TRACK_ACTIVITY_V1", "1")
    trade = _mk_trade(tid=600, contracts=3)
    poller, tm = _mk_poller(tmp_path, [trade])

    events_path = tmp_path / "trade_activity_events.jsonl"
    state_path = tmp_path / "sierra_state.json"

    import backend.v9.services.fill_poller as fp
    monkeypatch.setattr(fp, "ACTIVITY_EVENTS_PATH", events_path)
    monkeypatch.setattr(fp, "STATE_PATH", state_path)

    # Initialize
    _write_activity_events(events_path, [{"type": "POSITION_CHANGE", "ts": "2026-07-09T18:55:00+00:00"}])
    poller._check_activity_exits()

    # Append PnL event but Sierra still has 1 contract
    with open(events_path, "a") as f:
        f.write(json.dumps({
            "type": "CLOSED_TRADE_PNL", "ts": "2026-07-09T19:00:00+00:00", "pnl": 50.0,
        }) + "\n")
    _write_sierra_state(state_path, position_qty=1)

    poller._check_activity_exits()

    assert trade.state == "FILLED"  # NOT closed — partial exit
    assert tm._stop_hits == []


# ── Test 4: no FILLED trade → no crash ────────────────────────────────────────

def test_no_filled_trade_is_safe(tmp_path, monkeypatch):
    """CLOSED_TRADE_PNL with no FILLED trade → silent skip, no crash."""
    monkeypatch.setenv("EXIT_TRACK_ACTIVITY_V1", "1")
    # Only a shadow trade (should be ignored)
    shadow = _mk_trade(tid=100, mode="shadow")
    poller, tm = _mk_poller(tmp_path, [shadow])

    events_path = tmp_path / "trade_activity_events.jsonl"
    state_path = tmp_path / "sierra_state.json"

    import backend.v9.services.fill_poller as fp
    monkeypatch.setattr(fp, "ACTIVITY_EVENTS_PATH", events_path)
    monkeypatch.setattr(fp, "STATE_PATH", state_path)

    _write_activity_events(events_path, [{"type": "POSITION_CHANGE", "ts": "2026-07-09T18:55:00+00:00"}])
    poller._check_activity_exits()

    with open(events_path, "a") as f:
        f.write(json.dumps({
            "type": "CLOSED_TRADE_PNL", "ts": "2026-07-09T19:19:00+00:00", "pnl": -35.0,
        }) + "\n")
    _write_sierra_state(state_path, position_qty=0)

    poller._check_activity_exits()  # should not crash

    assert shadow.state == "FILLED"  # shadow unchanged
    assert tm._stop_hits == []


# ── Test 5: exit price back-computation SHORT ─────────────────────────────────

def test_exit_price_short(tmp_path, monkeypatch):
    """SHORT trade: exit_price = entry - PnL_pts."""
    monkeypatch.setenv("EXIT_TRACK_ACTIVITY_V1", "1")
    trade = _mk_trade(tid=520, direction="SHORT", entry_price=7500.0, contracts=2)
    poller, tm = _mk_poller(tmp_path, [trade])

    events_path = tmp_path / "trade_activity_events.jsonl"
    state_path = tmp_path / "sierra_state.json"

    import backend.v9.services.fill_poller as fp
    monkeypatch.setattr(fp, "ACTIVITY_EVENTS_PATH", events_path)
    monkeypatch.setattr(fp, "STATE_PATH", state_path)

    _write_activity_events(events_path, [{"type": "POSITION_CHANGE", "ts": "2026-07-09T18:55:00+00:00"}])
    poller._check_activity_exits()

    # SHORT PnL +100 = 2 contracts × $5/pt × 10pt → exit = 7500 - 10 = 7490
    with open(events_path, "a") as f:
        f.write(json.dumps({
            "type": "CLOSED_TRADE_PNL", "ts": "2026-07-09T19:19:00+00:00", "pnl": 100.0,
        }) + "\n")
    _write_sierra_state(state_path, position_qty=0)

    poller._check_activity_exits()

    assert trade.state == "CLOSED"
    assert trade.pnl_usd == 100.0
    # exit_price: SHORT, pnl=+100, 2c, $5/pt → pts_per_c = 100/2/5 = 10 → exit = 7500-10 = 7490
    assert trade.exit_price == 7490.0


# ── Test 6: multi-contract PnL summing (the 07-09 bug) ──────────────────────

def test_multi_contract_pnl_summed(tmp_path, monkeypatch):
    """DLL writes one CLOSED_TRADE_PNL per contract. Sum must capture all.

    Real fixture 07-09 15:45: 2-contract exit → [-198.75, -607.5] → total -806.25.
    The pre-fix bug took only the last event (-607.5) → under-counted by $198.75.
    """
    monkeypatch.setenv("EXIT_TRACK_ACTIVITY_V1", "1")
    trade = _mk_trade(tid=513, direction="SHORT", entry_price=7500.0, contracts=2)
    poller, tm = _mk_poller(tmp_path, [trade])

    events_path = tmp_path / "trade_activity_events.jsonl"
    state_path = tmp_path / "sierra_state.json"

    import backend.v9.services.fill_poller as fp
    monkeypatch.setattr(fp, "ACTIVITY_EVENTS_PATH", events_path)
    monkeypatch.setattr(fp, "STATE_PATH", state_path)

    # Initialize
    _write_activity_events(events_path, [
        {"type": "POSITION_CHANGE", "ts": "2026-07-09T15:40:00+00:00"},
    ])
    poller._check_activity_exits()

    # Append TWO per-contract PnL events (the real pattern)
    with open(events_path, "a") as f:
        f.write(json.dumps({
            "type": "CLOSED_TRADE_PNL", "ts": "2026-07-09T15:45:00+00:00", "pnl": -198.75,
        }) + "\n")
        f.write(json.dumps({
            "type": "CLOSED_TRADE_PNL", "ts": "2026-07-09T15:45:00+00:00", "pnl": -607.5,
        }) + "\n")
    _write_sierra_state(state_path, position_qty=0)

    poller._check_activity_exits()

    assert trade.state == "CLOSED"
    # MUST be the SUM: -198.75 + -607.5 = -806.25
    assert trade.pnl_usd == -806.25, f"Expected -806.25 but got {trade.pnl_usd}"
    assert trade.pnl_sierra == -806.25
