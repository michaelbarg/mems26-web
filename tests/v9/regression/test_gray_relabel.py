"""S4_GRAY_RELABEL_V1 — Michael ruling 2026-07-17 (hard evidence: the DLL paint
lags CCI ~6 bars → S4 blind through the whole 07-17 +56pt rally while paint
stayed GRAY). Relabel GRAY→BLUE/RED at the Stage-1 ±100 line; YELLOW untouched.
"""
import backend.v9.systems.woodies.trend_relabel as tr


def _studies(trend, cci):
    return {"trend_state": trend, "cci_14": cci}


def test_flag_off_no_relabel(monkeypatch):
    monkeypatch.delenv("S4_GRAY_RELABEL_V1", raising=False)
    monkeypatch.delenv("S4_EXTREME_TREND_RELABEL", raising=False)
    s = _studies("GRAY", 182)
    tr.apply_extreme_trend_relabel(s)
    assert s["trend_state"] == "GRAY"           # unchanged
    assert s["trend_original"] == "GRAY"


def test_gray_relabels_blue_at_100(monkeypatch):
    monkeypatch.setenv("S4_GRAY_RELABEL_V1", "1")
    s = _studies("GRAY", 130)                    # 07-17 16:55 bar
    tr.apply_extreme_trend_relabel(s)
    assert s["trend_state"] == "BLUE"
    assert s["trend_original"] == "GRAY"
    assert s.get("trend_relabel_src") == "gray_delag"


def test_gray_relabels_red_when_negative(monkeypatch):
    monkeypatch.setenv("S4_GRAY_RELABEL_V1", "1")
    s = _studies("GRAY", -146)
    tr.apply_extreme_trend_relabel(s)
    assert s["trend_state"] == "RED"


def test_gray_below_threshold_stays_gray(monkeypatch):
    monkeypatch.setenv("S4_GRAY_RELABEL_V1", "1")
    s = _studies("GRAY", 77)                     # 07-17 16:50: CCI<100 → chop, stays GRAY
    tr.apply_extreme_trend_relabel(s)
    assert s["trend_state"] == "GRAY"


def test_yellow_never_touched_by_gray_flag(monkeypatch):
    """Whipsaw guard (P-W5) stays — Michael ruled the GRAY, not the YELLOW."""
    monkeypatch.setenv("S4_GRAY_RELABEL_V1", "1")
    monkeypatch.delenv("S4_EXTREME_TREND_RELABEL", raising=False)
    s = _studies("YELLOW", 250)
    tr.apply_extreme_trend_relabel(s)
    assert s["trend_state"] == "YELLOW"          # blocked, unchanged


def test_threshold_tunable(monkeypatch):
    monkeypatch.setenv("S4_GRAY_RELABEL_V1", "1")
    monkeypatch.setenv("S4_GRAY_RELABEL_CCI", "150")
    s = _studies("GRAY", 130)                    # below 150 now
    tr.apply_extreme_trend_relabel(s)
    assert s["trend_state"] == "GRAY"


def test_legacy_extreme_still_works(monkeypatch):
    """S4_EXTREME_TREND_RELABEL (200, GRAY+YELLOW) preserved byte-identical."""
    monkeypatch.delenv("S4_GRAY_RELABEL_V1", raising=False)
    monkeypatch.setenv("S4_EXTREME_TREND_RELABEL", "1")
    s = _studies("YELLOW", 210)
    tr.apply_extreme_trend_relabel(s)
    assert s["trend_state"] == "BLUE"            # legacy relabels YELLOW at 200
