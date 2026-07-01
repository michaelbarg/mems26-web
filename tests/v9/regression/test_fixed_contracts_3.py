"""FIXED_CONTRACTS_3 — every firing trade uses 3 contracts (Michael 2026-07-01).

Anti-tautological: flag OFF = sizing unchanged (can be <3 on tactical/auth);
flag ON = 3 whenever the trade fires; reject (SKIP → None) preserved so invalid
setups still don't fire. Covers S2 + S4 (both route through compute_v2_sizing).
"""
from backend.v9.config_loader import load_stop_anchors
from backend.v9.systems.stop_anchors.sizing import compute_v2_sizing


def _kw(**over):
    base = dict(
        entry_price=7537.0, stop_price=7530.0, direction="LONG",
        pattern_key="ZLR", day_type="Normal", confidence_tier="low",
        day_has_direction=False, trade_with_trend=None,
        value_area_full_traverse=False, cfg=load_stop_anchors(),
    )
    base.update(over)
    return base


def test_flag_off_can_be_below_3(monkeypatch):
    monkeypatch.delenv("FIXED_CONTRACTS_3", raising=False)
    r = compute_v2_sizing(**_kw())
    assert r is not None and r.contracts < 3  # tactical mode caps at 2


def test_flag_on_forces_3(monkeypatch):
    monkeypatch.setenv("FIXED_CONTRACTS_3", "1")
    r = compute_v2_sizing(**_kw())
    assert r is not None and r.contracts == 3


def test_reject_preserved_with_flag_on(monkeypatch):
    monkeypatch.setenv("FIXED_CONTRACTS_3", "1")
    am = {("ZLR", "Normal"): ("SKIP", 0, 0, 0)}
    r = compute_v2_sizing(**_kw(auth_matrix=am))
    assert r is None  # SKIP still rejects — flag never fabricates a trade
