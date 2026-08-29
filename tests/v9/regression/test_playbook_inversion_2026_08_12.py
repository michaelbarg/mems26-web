"""F4 (2026-08-12) — the playbook inversion ruling is pinned cell-by-cell.

Michael's morning directive (the ruling; CC_WORKORDER_2026-08-12 F4), from the
48-session audits: GB100 is the only S4 pattern positive in live AND shadow AND
replay; ZLR (65% of volume) is negative everywhere; FAMIR/VEGAS are the two
worst books; GHOST won 0 of 3 live. Allowed S4 day-types: Trend_*/Variation/
Normal — Neutral_*/Nontrend SKIP.

Anti-tautological: reads the REAL config/daytype_playbook.yaml through the
production decide(). Reverting any ruled cell flips a test RED.
"""
import pytest

from backend.v9.systems import daytype_playbook as P


@pytest.fixture(autouse=True)
def _reset():
    P.reset_cache()
    yield
    P.reset_cache()


def _on(mp):
    mp.setenv("DAYTYPE_PLAYBOOK", "1")
    P.reset_cache()


def _v(pattern, day_type, direction="LONG", trend="GRAY"):
    return P.decide(pattern, day_type, direction, trend).verdict


def test_gb100_full_on_allowed_daytypes(monkeypatch):
    _on(monkeypatch)
    for dt in ("Trend_Normal", "Trend_DD", "Normal", "Variation"):
        assert _v("GB100_LONG", dt) == "FULL", (dt, "GB100 REDUCED→FULL is the ruling")


def test_gb100_still_skip_on_neutral(monkeypatch):
    _on(monkeypatch)
    for dt in ("Neutral_Center", "Neutral_Extreme", "Nontrend"):
        assert _v("GB100_LONG", dt) == "SKIP", dt


def test_zlr_reduced_on_trend_variation(monkeypatch):
    _on(monkeypatch)
    for dt in ("Trend_Normal", "Trend_DD", "Variation"):
        assert _v("ZLR_SHORT", dt, "SHORT", "RED") == "REDUCED", (
            dt, "ZLR FULL→REDUCED is the ruling")


def test_zlr_skip_on_normal_and_neutral(monkeypatch):
    # Michael 27.08 ruling: ZLR×Normal changed SKIP→REDUCED ("תבדוק אילו
    # דגלים הורסים ותבטל"). Evidence: 27.08 17:46 ZLR-LONG blocked on +40pt leg.
    _on(monkeypatch)
    assert _v("ZLR_SHORT", "Normal", "SHORT", "RED") == "REDUCED", \
        "Normal: ruling 27.08 SKIP→REDUCED"
    for dt in ("Neutral_Center", "Neutral_Extreme", "Nontrend"):
        assert _v("ZLR_SHORT", dt, "SHORT", "RED") == "SKIP", dt


def test_famir_skip_everywhere(monkeypatch):
    _on(monkeypatch)
    for dt in ("Trend_Normal", "Trend_DD", "Normal", "Variation",
               "Neutral_Center", "Neutral_Extreme", "Nontrend"):
        assert _v("FAMIR_LONG", dt) == "SKIP", (dt, "FAMIR −$1,607 replay — SKIP")


def test_vegas_skip_everywhere(monkeypatch):
    _on(monkeypatch)
    for dt in ("Trend_Normal", "Trend_DD", "Normal", "Variation",
               "Neutral_Center", "Neutral_Extreme", "Nontrend"):
        assert _v("VEGAS_LONG", dt) == "SKIP", (dt, "VEGAS −$1,015 replay — SKIP")


def test_ghost_reduced_rotation_skip_neutral(monkeypatch):
    _on(monkeypatch)
    assert _v("GHOST_SHORT", "Normal", "SHORT", "RED") == "REDUCED"
    assert _v("GHOST_SHORT", "Variation", "SHORT", "RED") == "REDUCED"
    for dt in ("Neutral_Center", "Neutral_Extreme", "Trend_Normal", "Trend_DD"):
        assert _v("GHOST_SHORT", dt, "SHORT", "RED") == "SKIP", dt


def test_unnamed_patterns_untouched(monkeypatch):
    """HTLB/TLB were NOT in the ruling (both measure positive) — their cells
    must still read the pre-inversion values."""
    _on(monkeypatch)
    assert _v("HTLB_LONG", "Variation") == "FULL"
    assert _v("TLB_LONG", "Trend_Normal") == "FULL"
    assert _v("TLB_LONG", "Normal") == "REDUCED"
