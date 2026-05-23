"""TASK A — CVD point timestamps must align with price bar unix (ET -04:00)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CVD_MAPPING = ROOT / "frontend/v9/src/v9/components/chart/v5b/cvdMapping.ts"
CVD_PANE = ROOT / "frontend/v9/src/v9/components/chart/v5b/CvdChartPane.tsx"


def test_cvd_sierra_et_offset_helper_exists():
    src = CVD_MAPPING.read_text(encoding="utf-8")
    assert "alignCvdPointTimesToPriceBars" in src
    assert "EDT_SHIFT" in src or "4 * 3600" in src


def test_apply_cvd_uses_align_before_normalize():
    src = CVD_PANE.read_text(encoding="utf-8")
    assert "alignCvdPointTimesToPriceBars(rawPoints, barList)" in src
    assert "CVD align check" in src
