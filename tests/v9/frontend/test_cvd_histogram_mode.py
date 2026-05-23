"""CVD pane uses histogram for Sierra {d,cum,t} points, not fake OHLC."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CVD = ROOT / "frontend/v9/src/v9/components/chart/v5b/CvdChartPane.tsx"
CHART = ROOT / "frontend/v9/src/v9/components/chart/v5b/ChartV5b.tsx"
ROUTES = ROOT / "backend/v9/api/v9/cumulative_delta_routes.py"


def test_sierra_api_documents_delta_points_not_ohlc():
    src = ROUTES.read_text(encoding="utf-8")
    assert "points" in src
    assert '"d"' in src or "'d'" in src or "cum" in src


def test_chart_v5b_cvd_uses_candlestick_series():
    src = CHART.read_text(encoding="utf-8")
    assert "HistogramSeries" not in src
    assert src.count("CandlestickSeries") >= 2


def test_cvd_render_mode_detects_ohlc_vs_histogram():
    src = CVD.read_text(encoding="utf-8")
    assert "cvdPointsUseOhlc" in src
    assert "buildCvdHistogramData" in src
    assert "resolveCvdRenderMode" in src
    assert "cvdHeaderFromCandles" in src
    assert "cumOhlcSeries" in src


def test_cvd_header_inside_pane_no_manual_orange_border():
    src = CHART.read_text(encoding="utf-8")
    assert "top: pricePaneH" in src
    assert "cvd-chart-header" in src
    assert "getHTMLElement" in src
    assert "borderTop" not in src.split("cvd-chart-header")[1].split(">")[0]
    assert "separatorColor: '#fb950b'" in src
