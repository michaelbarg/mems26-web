"""07-16 (Michael: "מאשר — תקן עכשיו") — RR relief during UNCLASSIFIED-label windows.

Root: the strict-1.0 fallback applied whenever get_live_day_type() returned None
(low-conf early session), which blocked the 7597×2 borderline winners (~R:R 0.9)
right before a +15pt run — even though RR_MIN_ROTATION=0.65 was ruled and live.

Ruling: relief also applies while the label is unclassified, but ONLY in the
post-opening window (10:00–16:00 ET; the opening 30min keeps strict 1.0), and
error paths stay fail-conservative at 1.0. Same anti-tautological harness as
test_rr_graded_rotation (drives the real route_setup with the live numbers).
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


def _cand_borderline():  # ~the 7597 profile: R:R 0.65-0.99 → passes only with relief
    return {"direction": "SHORT", "classification": "ZLR", "entry_price": 7601.25,
            "stop": 7607.75, "t1": 7597.00, "t2": 7593.00, "t3": 7589.00}


def _window(monkeypatch, open_: bool):
    monkeypatch.setattr(tg.TradingGateway, "_rr_unclassified_relief_window",
                        staticmethod(lambda: open_))


def test_unclassified_in_window_gets_relief(monkeypatch):
    monkeypatch.setenv("RR_ENTRY_GATE_V1", "1")
    monkeypatch.setenv("RR_MIN_ROTATION", "0.65")
    monkeypatch.setattr(tc, "get_live_day_type", lambda: None)
    _window(monkeypatch, True)
    r = _gw(monkeypatch).route_setup(_cand_borderline(), 4)
    assert r["blocked_by"] != "rr_entry_gate"


def test_unclassified_in_opening_stays_strict(monkeypatch):
    monkeypatch.setenv("RR_ENTRY_GATE_V1", "1")
    monkeypatch.setenv("RR_MIN_ROTATION", "0.65")
    monkeypatch.setattr(tc, "get_live_day_type", lambda: None)
    _window(monkeypatch, False)  # opening 30min / outside RTH
    r = _gw(monkeypatch).route_setup(_cand_borderline(), 4)
    assert r["blocked_by"] == "rr_entry_gate"


def test_unclassified_flag_unset_stays_blocked(monkeypatch):
    monkeypatch.setenv("RR_ENTRY_GATE_V1", "1")
    monkeypatch.delenv("RR_MIN_ROTATION", raising=False)
    monkeypatch.setattr(tc, "get_live_day_type", lambda: None)
    _window(monkeypatch, True)
    r = _gw(monkeypatch).route_setup(_cand_borderline(), 4)
    assert r["blocked_by"] == "rr_entry_gate"


def test_trend_label_keeps_strict_even_in_window(monkeypatch):
    monkeypatch.setenv("RR_ENTRY_GATE_V1", "1")
    monkeypatch.setenv("RR_MIN_ROTATION", "0.65")
    monkeypatch.setattr(tc, "get_live_day_type", lambda: "Trend_Normal")
    _window(monkeypatch, True)
    r = _gw(monkeypatch).route_setup(_cand_borderline(), 4)
    assert r["blocked_by"] == "rr_entry_gate"


def test_error_path_stays_conservative(monkeypatch):
    monkeypatch.setenv("RR_ENTRY_GATE_V1", "1")
    monkeypatch.setenv("RR_MIN_ROTATION", "0.65")
    def _boom():
        raise RuntimeError("no day type")
    monkeypatch.setattr(tc, "get_live_day_type", _boom)
    _window(monkeypatch, True)
    r = _gw(monkeypatch).route_setup(_cand_borderline(), 4)
    assert r["blocked_by"] == "rr_entry_gate"
