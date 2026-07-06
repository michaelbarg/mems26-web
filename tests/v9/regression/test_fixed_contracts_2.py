"""FIXED_CONTRACTS_2 — every firing trade uses 2 contracts (Michael 2026-07-06).

2-contract LIVE sizing. Takes PRECEDENCE over FIXED_CONTRACTS_3. Anti-tautological:
flag ON = 2 whenever the trade fires (fails on old code, which had no _2 handling and
would give 3 under _3 or the tactical/auth count); precedence proven (both set → 2);
reject (SKIP → None) preserved so the flag never fabricates a trade.
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


def test_flag_2_on_forces_2(monkeypatch):
    """FIXED_CONTRACTS_2=1 → contracts == 2 (fails on old: would be tactical<3 or _3's 3)."""
    monkeypatch.delenv("FIXED_CONTRACTS_3", raising=False)
    monkeypatch.setenv("FIXED_CONTRACTS_2", "1")
    r = compute_v2_sizing(**_kw())
    assert r is not None and r.contracts == 2, f"expected 2, got {r and r.contracts}"


def test_2_takes_precedence_over_3(monkeypatch):
    """Both flags set → 2 wins (precedence, not 3)."""
    monkeypatch.setenv("FIXED_CONTRACTS_3", "1")
    monkeypatch.setenv("FIXED_CONTRACTS_2", "1")
    r = compute_v2_sizing(**_kw())
    assert r is not None and r.contracts == 2, f"_2 must win over _3, got {r and r.contracts}"


def test_3_still_works_when_2_off(monkeypatch):
    """_2 unset → falls back to _3 (=3): the standing decision is untouched."""
    monkeypatch.delenv("FIXED_CONTRACTS_2", raising=False)
    monkeypatch.setenv("FIXED_CONTRACTS_3", "1")
    r = compute_v2_sizing(**_kw())
    assert r is not None and r.contracts == 3, f"expected 3 (fallback), got {r and r.contracts}"


def test_reject_preserved_with_flag_2_on(monkeypatch):
    """SKIP auth still rejects with _2 on — flag never fabricates a trade."""
    monkeypatch.setenv("FIXED_CONTRACTS_2", "1")
    am = {("ZLR", "Normal"): ("SKIP", 0, 0, 0)}
    r = compute_v2_sizing(**_kw(auth_matrix=am))
    assert r is None
