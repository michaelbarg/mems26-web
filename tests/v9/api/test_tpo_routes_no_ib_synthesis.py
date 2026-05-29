"""Anti-regression: _ib_from_bars() deleted per 2026-05-28 evening revocation.

When Sierra IB Study reports ib.found=false, the response must carry
ib_high=None and ib_source="missing". No bars-derived synthesis.
Per CLAUDE.md Rule 1: honest failure > synthetic value.
"""

from backend.v9.api.v9.tpo_routes import _normalize_sierra_tpo


def test_normalize_sierra_tpo_returns_missing_when_dll_silent():
    """When ib.found=false, response carries ib_high=None, ib_source='missing'."""
    out = _normalize_sierra_tpo(
        {"ib": {"found": False}, "session": {"poc": 5500, "vah": 5510, "val": 5490}},
        age_s=0.5,
    )
    assert out["ib_high"] is None
    assert out["ib_low"] is None
    assert out["ib_found"] is False
    assert out["ib_source"] == "missing"


def test_normalize_sierra_tpo_returns_sierra_live_when_found():
    """When ib.found=true, response carries ib_source='sierra_live'."""
    out = _normalize_sierra_tpo(
        {"ib": {"found": True, "high": 5520.0, "low": 5500.0, "mid": 5510.0},
         "session": {"poc": 5500, "vah": 5510, "val": 5490}},
        age_s=0.5,
    )
    assert out["ib_high"] == 5520.0
    assert out["ib_low"] == 5500.0
    assert out["ib_found"] is True
    assert out["ib_source"] == "sierra_live"


def test_no_ib_from_bars_function_exists():
    """_ib_from_bars must not exist in tpo_routes module."""
    import backend.v9.api.v9.tpo_routes as mod
    assert not hasattr(mod, "_ib_from_bars"), (
        "_ib_from_bars should be deleted — IB only from Sierra Study. "
        "See 2026-05-28 evening revocation in AMENDMENTS_LOG.md."
    )
