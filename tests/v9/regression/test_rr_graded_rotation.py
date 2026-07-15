"""07-15 evening (Michael: "תיקון שיסדר את הבעיה כדי שהמערכת תסחר היום").

RR_MIN_ROTATION: graded R:R minimum on rotation days. Anti-tautological — drives
the REAL route_setup with the exact 18:15 numbers cc-imac reported from live:
  cand-1 (the winner): entry=7601.25 SHORT, stop_dist=6.50, T1_dist=4.25 → R:R 0.65
  cand-2 (dedup'd):    entry=7599.00 SHORT, stop_dist=7.25, T1_dist=2.00 → R:R 0.28
Flag unset → both blocked (unchanged). Flag=0.65 on a rotation day → cand-1
passes, cand-2 STAYS blocked. Trend day / day-type error → 1.0 (conservative).
"""
import backend.v9.services.trade_context as tc
from backend.v9.gateway import trading_gateway as tg


def _gw(monkeypatch):
    monkeypatch.setattr(tg, "is_within_firing_window", lambda: True)
    gw = tg.TradingGateway()
    monkeypatch.setattr(gw, "_execute_shadow", lambda *a, **k: {"trade_id": "t"})
    monkeypatch.setattr(gw, "_capture_cross_context",
                        lambda: {"day_type_machine": {}, "woodies_system": {}, "tpo_system": {}})
    return gw


def _cand1():  # the blocked winner, 18:15:02
    return {"direction": "SHORT", "classification": "ZLR", "entry_price": 7601.25,
            "stop": 7607.75, "t1": 7597.00, "t2": 7593.00, "t3": 7589.00}


def _cand2():  # the dedup'd second, 18:15:06
    return {"direction": "SHORT", "classification": "ZLR", "entry_price": 7599.00,
            "stop": 7606.25, "t1": 7597.00, "t2": 7593.00, "t3": 7589.00}


def test_flag_unset_blocks_065_unchanged(monkeypatch):
    monkeypatch.setenv("RR_ENTRY_GATE_V1", "1")
    monkeypatch.delenv("RR_MIN_ROTATION", raising=False)
    r = _gw(monkeypatch).route_setup(_cand1(), 4)
    assert r["blocked_by"] == "rr_entry_gate"


def test_rotation_065_passes_the_1815_winner(monkeypatch):
    monkeypatch.setenv("RR_ENTRY_GATE_V1", "1")
    monkeypatch.setenv("RR_MIN_ROTATION", "0.65")
    monkeypatch.setattr(tc, "get_live_day_type", lambda: "Variation")
    r = _gw(monkeypatch).route_setup(_cand1(), 4)
    assert r["blocked_by"] != "rr_entry_gate"


def test_rotation_065_still_blocks_the_028_second(monkeypatch):
    monkeypatch.setenv("RR_ENTRY_GATE_V1", "1")
    monkeypatch.setenv("RR_MIN_ROTATION", "0.65")
    monkeypatch.setattr(tc, "get_live_day_type", lambda: "Variation")
    r = _gw(monkeypatch).route_setup(_cand2(), 4)
    assert r["blocked_by"] == "rr_entry_gate"


def test_trend_day_keeps_full_min(monkeypatch):
    monkeypatch.setenv("RR_ENTRY_GATE_V1", "1")
    monkeypatch.setenv("RR_MIN_ROTATION", "0.65")
    monkeypatch.setattr(tc, "get_live_day_type", lambda: "Trend_Normal")
    r = _gw(monkeypatch).route_setup(_cand1(), 4)
    assert r["blocked_by"] == "rr_entry_gate"


def test_daytype_error_fails_conservative(monkeypatch):
    monkeypatch.setenv("RR_ENTRY_GATE_V1", "1")
    monkeypatch.setenv("RR_MIN_ROTATION", "0.65")
    def _boom():
        raise RuntimeError("no day type")
    monkeypatch.setattr(tc, "get_live_day_type", _boom)
    r = _gw(monkeypatch).route_setup(_cand1(), 4)
    assert r["blocked_by"] == "rr_entry_gate"
