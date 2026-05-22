"""TASK C — SierraLevelsOverlay renders at most six TPO segments."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OVERLAY = ROOT / "frontend/v9/src/v9/components/chart/v5b/SierraLevelsOverlay.tsx"
TPO_LEVELS = ROOT / "frontend/v9/src/v9/components/chart/v5b/tpoLevels.ts"


def test_tpo_overlay_no_stepped_periods_loop():
    src = OVERLAY.read_text(encoding="utf-8")
    assert "last5" not in src
    assert "POC_STEPS" not in src
    assert "periods.slice" not in src


def test_tpo_overlay_six_line_labels_only():
    src = OVERLAY.read_text(encoding="utf-8")
    lv = TPO_LEVELS.read_text(encoding="utf-8")
    for label in ("'POC'", "'VAH'", "'VAL'"):
        assert label in lv
    assert "YVAH" not in src and "YPOC" not in src
    assert "PRICE_SCALE_W" in src and "lwGrayTickTextX" in src
    assert 'textAnchor="start"' in src
    assert "tabular-nums" in src
    assert "spreadLabelYs" not in src
    assert "BADGE_BG" in src and "TpoAxisBadge" in src
    assert "IB High" not in src
    assert "prior_day" not in src
    assert "LEVEL_STYLE" in lv and "RTH_LEVEL_STYLE" in lv
    assert "LineStyle.Dashed" in lv
    # Yesterday's POC/VAH/VAL switched from `createPriceLine` (infinite
    # horizontal) to `LineSeries` bounded to today's RTH window on
    # 2026-05-22 PM after Michael flagged "still infinite" lines. The
    # 6 segment count remains: 3 today (stepped/pink) + 3 yesterday
    # (RTH-bounded white).
    assert "buildTpoPlan" in lv and "LineSeries" in lv
    assert "syncTpoPriceLines" in lv and "syncYesterdayTpoLines" in lv
    chart = (ROOT / "frontend/v9/src/v9/components/chart/v5b/ChartV5b.tsx").read_text(
        encoding="utf-8"
    )
    assert "applyTpoToChart" in chart
    # SierraLevelsOverlay no longer uses inline <line> SVG — labels-only
    # rendering via TpoAxisBadge keeps the right-axis clean (previous
    # `<line>` paths were dropped in P30.9 series of refactors).
    ov = OVERLAY.read_text(encoding="utf-8")
    assert "PRICE_SCALE_W" in ov and "TpoAxisBadge" in ov


def test_tpo_price_validation():
    lv = TPO_LEVELS.read_text(encoding="utf-8")
    assert "isValidMesTpoPrice" in lv
    assert "3000" in lv and "10000" in lv
    assert "pickTodayPeriod" in lv
    assert "session_opened_ts" in lv


def test_chartv5b_no_stale_period_tail_loop():
    chart = (ROOT / "frontend/v9/src/v9/components/chart/v5b/ChartV5b.tsx").read_text(
        encoding="utf-8"
    )
    assert "periods.length - 1" not in chart
    assert "resolveTodayLevels(overlayPayload)" in chart
