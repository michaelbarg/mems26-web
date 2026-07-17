"""N3 no-late-entry gate (ZONE_LIMIT_ENTRY_V1, default OFF).

Michael ruling 2026-07-17: "לא תהיה כניסה באף תבנית בשלב מאוחר מדי" — no
pattern may enter too late after its signal. Anti-tautological: drives the
REAL route_setup gate chain (same harness as test_rr_graded_rotation) and
asserts on blocked_by + whether shadow execution was actually reached.

Axes under test:
  (a) ADVERSE price drift beyond ZONE_LIMIT_MAX_DRIFT_PT (default 2.0) →
      blocked (chasing). FAVORABLE drift (a better fill) must pass.
  (b) signal age beyond ZONE_LIMIT_MAX_AGE_SEC (default 180) — ONLY when
      the setup carries bar_ts (S2/S4 setups don't today → dormant for
      them; CONFLUENCE_RI_ZLR setups do).
Fail-open contract (Source-of-Truth Rule 1): flag OFF, missing price
source, or missing timestamp must never block.
"""
import time

import backend.v9.api.v9.price_routes as pr
from backend.v9.gateway import trading_gateway as tg


def _gw(monkeypatch):
    monkeypatch.setattr(tg, "is_within_firing_window", lambda: True)
    gw = tg.TradingGateway()
    monkeypatch.setattr(gw, "_execute_shadow", lambda *a, **k: {"trade_id": "t"})
    monkeypatch.setattr(gw, "_capture_cross_context",
                        lambda: {"day_type_machine": {}, "woodies_system": {}, "tpo_system": {}})
    return gw


def _long():  # S4-shaped setup exactly like production: NO bar_ts key
    return {"direction": "LONG", "classification": "ZLR", "entry_price": 7600.00,
            "stop": 7594.00, "t1": 7607.00, "t2": 7612.00, "t3": None}


def _short():
    return {"direction": "SHORT", "classification": "ZLR", "entry_price": 7600.00,
            "stop": 7606.00, "t1": 7593.00, "t2": 7588.00, "t3": None}


def _price(monkeypatch, px):
    monkeypatch.setattr(pr, "get_live_price_snapshot",
                        lambda *a, **k: {"price": px, "age_sec": 0.2, "source": "cache"})


def test_flag_off_no_block_even_with_huge_drift(monkeypatch):
    monkeypatch.delenv("ZONE_LIMIT_ENTRY_V1", raising=False)
    _price(monkeypatch, 7650.00)  # 50pt chase — absurd, but flag is OFF
    r = _gw(monkeypatch).route_setup(_long(), 4)
    assert r["blocked_by"] != "zone_limit_late_entry"
    assert r["shadow"] == "t"  # reached execution untouched


def test_on_fresh_and_close_passes(monkeypatch):
    monkeypatch.setenv("ZONE_LIMIT_ENTRY_V1", "1")
    _price(monkeypatch, 7600.75)  # 0.75pt adverse — inside the 2.0 default
    s = _long()
    s["bar_ts"] = time.time() - 30  # 30s-old signal — fresh
    r = _gw(monkeypatch).route_setup(s, 4)
    assert r["blocked_by"] != "zone_limit_late_entry"
    assert r["shadow"] == "t"


def test_on_no_bar_ts_s4_shape_passes(monkeypatch):
    # S2/S4 production setups carry no bar_ts — the age axis must stay
    # dormant (fail-open), never block on a missing timestamp.
    monkeypatch.setenv("ZONE_LIMIT_ENTRY_V1", "1")
    _price(monkeypatch, 7599.50)  # favorable side, well within limits
    r = _gw(monkeypatch).route_setup(_long(), 4)
    assert r["blocked_by"] != "zone_limit_late_entry"
    assert r["shadow"] == "t"


def test_on_long_chased_3pt_blocked(monkeypatch):
    monkeypatch.setenv("ZONE_LIMIT_ENTRY_V1", "1")
    _price(monkeypatch, 7603.00)  # 3pt ABOVE a LONG entry = chasing > 2.0
    r = _gw(monkeypatch).route_setup(_long(), 4)
    assert r["blocked_by"] == "zone_limit_late_entry"
    assert r["shadow"] is None  # blocked BEFORE execution, all modes


def test_on_short_chased_3pt_blocked_mirror(monkeypatch):
    monkeypatch.setenv("ZONE_LIMIT_ENTRY_V1", "1")
    _price(monkeypatch, 7597.00)  # 3pt BELOW a SHORT entry = chasing > 2.0
    r = _gw(monkeypatch).route_setup(_short(), 4)
    assert r["blocked_by"] == "zone_limit_late_entry"
    assert r["shadow"] is None


def test_missing_price_source_fails_open(monkeypatch):
    monkeypatch.setenv("ZONE_LIMIT_ENTRY_V1", "1")
    monkeypatch.setattr(pr, "get_live_price_snapshot", lambda *a, **k: None)
    r = _gw(monkeypatch).route_setup(_long(), 4)
    assert r["blocked_by"] != "zone_limit_late_entry"
    assert r["shadow"] == "t"


def test_favorable_drift_not_blocked_both_directions(monkeypatch):
    monkeypatch.setenv("ZONE_LIMIT_ENTRY_V1", "1")
    # LONG: price came BACK 3pt BELOW entry — a better fill, not a chase.
    _price(monkeypatch, 7597.00)
    r = _gw(monkeypatch).route_setup(_long(), 4)
    assert r["blocked_by"] != "zone_limit_late_entry"
    # SHORT mirror: price 3pt ABOVE the short entry = favorable.
    _price(monkeypatch, 7603.00)
    r2 = _gw(monkeypatch).route_setup(_short(), 4)
    assert r2["blocked_by"] != "zone_limit_late_entry"


def test_stale_signal_age_blocked_when_ts_present(monkeypatch):
    monkeypatch.setenv("ZONE_LIMIT_ENTRY_V1", "1")
    _price(monkeypatch, 7600.25)  # price itself fine — age must trip alone
    s = _long()
    s["bar_ts"] = time.time() - 600  # 10-min-old signal > 180s default
    r = _gw(monkeypatch).route_setup(s, 4)
    assert r["blocked_by"] == "zone_limit_late_entry"
    assert r["shadow"] is None


def test_confluence_pattern_not_exempt(monkeypatch):
    # Michael: applies to EVERY pattern — CONFLUENCE_RI_ZLR included.
    monkeypatch.setenv("ZONE_LIMIT_ENTRY_V1", "1")
    _price(monkeypatch, 7603.25)  # 3.25pt chase on a LONG
    s = _long()
    s["classification"] = "CONFLUENCE_RI_ZLR"
    s["pattern"] = "CONFLUENCE_RI_ZLR"
    r = _gw(monkeypatch).route_setup(s, 4)
    assert r["blocked_by"] == "zone_limit_late_entry"
    assert r["shadow"] is None


def test_params_env_tunable(monkeypatch):
    # Widen the drift limit to 5pt → the same 3pt chase must now pass.
    monkeypatch.setenv("ZONE_LIMIT_ENTRY_V1", "1")
    monkeypatch.setenv("ZONE_LIMIT_MAX_DRIFT_PT", "5.0")
    _price(monkeypatch, 7603.00)
    r = _gw(monkeypatch).route_setup(_long(), 4)
    assert r["blocked_by"] != "zone_limit_late_entry"
    # Tighten the age limit to 10s → a 30s-old signal must now block.
    monkeypatch.setenv("ZONE_LIMIT_MAX_AGE_SEC", "10")
    monkeypatch.setenv("ZONE_LIMIT_MAX_DRIFT_PT", "5.0")
    s = _long()
    s["bar_ts"] = time.time() - 30
    r2 = _gw(monkeypatch).route_setup(s, 4)
    assert r2["blocked_by"] == "zone_limit_late_entry"
