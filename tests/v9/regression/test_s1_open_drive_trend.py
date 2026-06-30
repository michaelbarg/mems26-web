"""S1_OPEN_DRIVE_TREND — OPEN_DRIVE waives the rib>=2.5 Trend floor (Michael 2026-06-30).

Anti-tautological: flag OFF must be byte-identical (Variation); flag ON promotes ONLY when
the full signature holds (OPEN_DRIVE/OPEN_TEST_DRIVE + directional one_tf + close-at-extreme);
the strict rib>=2.5 Trend path is unaffected.
Repro: 06-30 was OPEN_DRIVE + one_tf=UP + close_pos=0.915 + rib=1.5563 → mis-called Variation.
"""
from backend.v9.systems.day_type.daytype_classifier import classify


def _feat(**kw):
    base = dict(
        sides=1, rib=1.55, close_pos=0.92, one_tf="UP",
        opening_type="OPEN_DRIVE", n_bars=20, vol_ratio=1.0, cvd_pos=0.8,
        dd_second_dist=False, returned_through_open=False,
    )
    base.update(kw)
    return base


def test_flag_off_open_drive_stays_variation(monkeypatch):
    monkeypatch.delenv("S1_OPEN_DRIVE_TREND", raising=False)
    r = classify(_feat(), is_eod=True)
    assert r["day_type"] == "Normal_Variation", r


def test_flag_on_open_drive_promotes_trend(monkeypatch):
    monkeypatch.setenv("S1_OPEN_DRIVE_TREND", "1")
    r = classify(_feat(), is_eod=True)
    assert r["day_type"] == "Trend_Normal", r
    assert r.get("open_drive_trend") is True


def test_flag_on_but_not_a_drive_stays_variation(monkeypatch):
    monkeypatch.setenv("S1_OPEN_DRIVE_TREND", "1")
    r = classify(_feat(opening_type="OPEN_AUCTION"), is_eod=True)
    assert r["day_type"] == "Normal_Variation", r


def test_flag_on_but_no_one_tf_stays_variation(monkeypatch):
    monkeypatch.setenv("S1_OPEN_DRIVE_TREND", "1")
    r = classify(_feat(one_tf=None), is_eod=True)
    assert r["day_type"] == "Normal_Variation", r


def test_flag_on_but_not_at_extreme_stays_variation(monkeypatch):
    monkeypatch.setenv("S1_OPEN_DRIVE_TREND", "1")
    r = classify(_feat(close_pos=0.5), is_eod=True)
    assert r["day_type"] == "Normal_Variation", r


def test_strict_rib_trend_path_unaffected(monkeypatch):
    monkeypatch.delenv("S1_OPEN_DRIVE_TREND", raising=False)
    r = classify(_feat(rib=2.8), is_eod=True)  # rib>=2.5 → existing strict Trend path
    assert r["day_type"] == "Trend_Normal", r
