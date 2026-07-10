"""FIX-10 — async broker rejection must become REJECTED, not CLOSED/BE.

Real incident (trade 337, 2026-07-10 17:55): PLACE → ORDER_SUBMITTED ack
(order 8700) → Teton margin rejection ("Insufficient Account Value (NLV) for
margin...") → the system recorded CLOSED/BE/pnl=0 and the slot stayed burned.
The rejection is ASYNC (after submit-ack) so the ORDER_FAILED path in
_check_result never fires.

Chain under test:
1. feeder parses the real Teton reject line → ORDER_REJECT event.
2. FillPoller._check_rejections correlates it to the submit-acked PENDING
   trade with no fill → CANCELLED/REJECTED + slot release. FILLED untouched.
"""
import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]

# ── layer 1: feeder parse of the real rejection line ─────────────────────────

def _load_feeder():
    spec = importlib.util.spec_from_file_location(
        "trade_activity_feed", REPO / "scripts" / "trade_activity_feed.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


REAL_REJECT_LINE = (
    "Teton CME Routing (Order reject). Info: Trade Order Error - Insufficient "
    "Account Value (NLV) for margin for order. Margin needed for symbol: 551.32 "
    "USD. MarginPercent: 10%. Margin needed for Account: 551.32. Account Value: "
    "526.54. Max potential quantity: 2. Minimum required NLV: 50.00. Text: Tag"
)


def test_feeder_parses_real_teton_reject():
    feeder = _load_feeder()
    events, _ = feeder._parse_events([REAL_REJECT_LINE])
    rejects = [e for e in events if e["type"] == "ORDER_REJECT"]
    assert len(rejects) == 1
    assert "Insufficient Account Value" in rejects[0]["reason"]


def test_feeder_ignores_normal_lines():
    feeder = _load_feeder()
    events, _ = feeder._parse_events([
        "Updated Internal Position Quantity to 2. Previous: 0. Fill of InternalOrderID: 8720",
    ])
    assert not [e for e in events if e["type"] == "ORDER_REJECT"]


# ── layer 2: poller correlation ──────────────────────────────────────────────

def _mk_poller(tmp_path, trades):
    from backend.v9.services import fill_poller as fp
    poller = fp.FillPoller.__new__(fp.FillPoller)
    tm = types.SimpleNamespace()
    tm.get_active_trades = lambda: trades
    tm._closed = []
    tm.close_trade = lambda tid, reason=None: tm._closed.append((tid, reason))
    tm._db = types.SimpleNamespace(flush=lambda: None)
    poller._tm = tm
    poller._gateway = None
    poller._gw_closes = []
    poller._notify_gateway_close = lambda tid, outcome: poller._gw_closes.append((tid, outcome))
    return poller, tm


def _mk_trade(state="PENDING", mode="live", tid=337):
    t = types.SimpleNamespace()
    t.id = tid
    t.state = state
    t.mode = mode
    t.pnl_usd = None
    t.outcome = None
    t.quality = {"sierra_order_id": 8700}
    return t


def _write_events(path, events):
    with open(path, "w", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")


def _run_cycle(poller, monkeypatch, tmp_path, events_before, events_after):
    """Simulate: first poll (seeds EOF), events appended, second poll."""
    from backend.v9.services import fill_poller as fp
    monkeypatch.setattr(fp, "_SIGNALS_DIR", tmp_path)
    ev = tmp_path / "trade_activity_events.jsonl"
    _write_events(ev, events_before)
    poller._check_rejections()  # seeds at EOF
    with open(ev, "a", encoding="utf-8") as f:
        for e in events_after:
            f.write(json.dumps(e) + "\n")
    poller._check_rejections()


REJ_EV = {"type": "ORDER_REJECT", "reason": "Trade Order Error - Insufficient Account Value (NLV)", "ts": "x", "line": 9}


def test_pending_trade_becomes_rejected(monkeypatch, tmp_path):
    monkeypatch.setenv("ORDER_REJECT_DETECT_V1", "1")
    t = _mk_trade()
    poller, tm = _mk_poller(tmp_path, [t])
    _run_cycle(poller, monkeypatch, tmp_path, [], [REJ_EV])
    assert t.state == "CANCELLED"
    assert t.outcome == "REJECTED"
    assert t.pnl_usd == 0.0
    assert tm._closed and tm._closed[0][0] == 337
    assert poller._gw_closes == [(337, "REJECTED")], "slot must be released"
    assert "Insufficient" in t.quality.get("reject_reason", "")


def test_filled_trade_never_touched(monkeypatch, tmp_path):
    """A FILLED trade (real position) must not be cancelled by a rejection
    event — that's the 308 naked-bracket family, handled elsewhere."""
    monkeypatch.setenv("ORDER_REJECT_DETECT_V1", "1")
    t = _mk_trade(state="FILLED")
    poller, tm = _mk_poller(tmp_path, [t])
    _run_cycle(poller, monkeypatch, tmp_path, [], [REJ_EV])
    assert t.state == "FILLED"
    assert not tm._closed


def test_historical_rejections_ignored(monkeypatch, tmp_path):
    """First run seeds at EOF — old rejections in the journal never act."""
    monkeypatch.setenv("ORDER_REJECT_DETECT_V1", "1")
    t = _mk_trade()
    poller, tm = _mk_poller(tmp_path, [t])
    _run_cycle(poller, monkeypatch, tmp_path, [REJ_EV], [])
    assert t.state == "PENDING"
    assert not tm._closed


def test_flag_off_inert(monkeypatch, tmp_path):
    monkeypatch.delenv("ORDER_REJECT_DETECT_V1", raising=False)
    t = _mk_trade()
    poller, tm = _mk_poller(tmp_path, [t])
    _run_cycle(poller, monkeypatch, tmp_path, [], [REJ_EV])
    assert t.state == "PENDING"
    assert not tm._closed
