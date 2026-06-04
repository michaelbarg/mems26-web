"""D-RVX variant selector tests — verifies YAML-tunable firing variant.

Tests the production path (_detect_reactive) with bars crafted so that
_rvol_pass=True but _vsa_pass=False, proving the selector changes behavior.

If reverted (b2_drop=_vsa_pass hardcoded) → RED because the B_RVOL
variant would not fire despite being selected in config.
"""

import os
import yaml
import shutil
import pytest

# Ensure BRIDGE_TOKEN is set for app import
os.environ.setdefault("BRIDGE_TOKEN", "test")


@pytest.fixture(autouse=True)
def _env_vsa_on(monkeypatch):
    """Ensure S2_VSA_VOLUME is ON for all tests (variant selector only active when ON)."""
    monkeypatch.setenv("S2_VSA_VOLUME", "true")


def _make_bars_rvol_only():
    """Craft 8 bars where _rvol_pass=True but _vsa_pass=False.

    _vsa_pass requires: b2 < b1 AND b2 < b0 AND b2 <= 0.7*rolling_avg
    _rvol_pass requires: b2 <= 0.5*rolling_avg

    Strategy: b0 has LOW volume (100), b1 has HIGH volume (1000),
    b2 has volume 200. Then:
      - rolling_avg ~ 500 (from bars before the pattern window)
      - b2=200 <= 0.5*500=250 → _rvol_pass=True
      - b2=200 > b0=100 → violates "b2 < b0" → _vsa_pass=False
      - b2=200 <= 0.7*500=350 → VSA avg check passes, but b0 check fails

    Bars 3,4 complete a valid Reactive LONG pattern:
      b1=bearish+high vol, b3=bullish, b4=bullish confirm above b3.high
    """
    base_price = 5500.0
    # 4 lookback bars (establish rolling avg ~500)
    bars = [
        {"ts": 1000 + i, "o": base_price, "h": base_price + 1, "l": base_price - 1, "c": base_price + 0.5, "v": 500}
        for i in range(4)
    ]
    # b0 (bars[-5] relative to pattern window) — low volume
    bars.append({"ts": 1004, "o": base_price, "h": base_price + 1, "l": base_price - 1, "c": base_price + 0.5, "v": 100})
    # b1 — bearish + high volume (sellers dominate)
    bars.append({"ts": 1005, "o": base_price + 2, "h": base_price + 3, "l": base_price - 1, "c": base_price - 0.5, "v": 1000})
    # b2 — volume=200: rvol passes (200 <= 0.5*~460), vsa fails (200 > b0=100... wait, we need b2 > b0)
    # Actually b2=200 > b0=100, so "b2 < b0" fails → _vsa_pass=False. Good.
    bars.append({"ts": 1006, "o": base_price, "h": base_price + 0.5, "l": base_price - 0.5, "c": base_price - 0.25, "v": 200})
    # b3 — bullish (buyers)
    bars.append({"ts": 1007, "o": base_price - 0.5, "h": base_price + 1, "l": base_price - 0.5, "c": base_price + 0.75, "v": 500})
    # b4 — bullish confirm, close above b3.high
    bars.append({"ts": 1008, "o": base_price + 0.5, "h": base_price + 2, "l": base_price + 0.25, "c": base_price + 1.5, "v": 500})
    return bars


class _StubFiveMin:
    """Minimal stub to call _detect_reactive without full system init."""

    def __init__(self):
        self._current_atr_5m = 2.0  # ATR for C_STRICT calc
        self._footprint_system = None

    def _get_belly_from_footprint(self):
        return None  # None passes the "belly is not False" check

    def _get_belly_ratio_from_footprint(self, direction):
        return None  # None passes the ratio check

    def _get_cot_from_footprint(self):
        return 100.0  # COT > AMT for LONG

    def _get_amt_from_footprint(self):
        return 50.0  # AMT < COT

    def _poc_vol_rising(self, bars):
        return False

    def _poc_vol_falling(self, bars):
        return False


def _detect_with_variant(bars, variant, tmp_path):
    """Run _detect_reactive with a given variant selector."""
    from backend.v9.config_loader import reset_s2_firing_cache
    from backend.v9 import config_loader as cl

    # Write s2_firing.yaml with the desired variant
    yaml_path = tmp_path / "s2_firing.yaml"
    yaml_path.write_text(yaml.dump({"variant": variant}))

    # Also need stop_params.yaml etc. for other loaders
    real_config = cl._CONFIG_DIR
    for f in ("auth_matrix.yaml", "targets.yaml", "stop_params.yaml"):
        src = real_config / f
        if src.exists():
            shutil.copy(src, tmp_path / f)

    old_dir = cl._CONFIG_DIR
    cl._CONFIG_DIR = tmp_path
    reset_s2_firing_cache()

    try:
        from backend.v9.systems.five_min.five_min_system import FiveMinSystem
        stub = _StubFiveMin()
        # Bind the detect method to our stub
        detect = FiveMinSystem._detect_reactive.__get__(stub, type(stub))
        result = detect(bars)
        return result  # (direction, confidence, info) or (None, 0, {})
    finally:
        cl._CONFIG_DIR = old_dir
        reset_s2_firing_cache()


def test_variant_a_vsa_no_fire(tmp_path):
    """A_VSA selected, _vsa_pass=False → does NOT fire."""
    bars = _make_bars_rvol_only()
    direction, conf, info = _detect_with_variant(bars, "A_VSA", tmp_path)
    assert direction is None, f"A_VSA should NOT fire (vsa_pass=False), got {direction}"


def test_variant_b_rvol_fires(tmp_path):
    """B_RVOL selected, _rvol_pass=True → FIRES.

    If reverted (b2_drop=_vsa_pass hardcoded) → RED because _vsa_pass=False
    and the variant selector is ignored, so this bar set would not fire.
    """
    bars = _make_bars_rvol_only()
    direction, conf, info = _detect_with_variant(bars, "B_RVOL", tmp_path)
    assert direction == "LONG", f"B_RVOL should fire LONG (_rvol_pass=True), got {direction}"


def test_variant_union_fires(tmp_path):
    """UNION selected, _rvol_pass=True (OR gate) → FIRES."""
    bars = _make_bars_rvol_only()
    direction, conf, info = _detect_with_variant(bars, "UNION", tmp_path)
    assert direction == "LONG", f"UNION should fire LONG, got {direction}"


def test_variant_intersection_no_fire(tmp_path):
    """INTERSECTION selected, _vsa_pass=False (AND gate) → does NOT fire."""
    bars = _make_bars_rvol_only()
    direction, conf, info = _detect_with_variant(bars, "INTERSECTION", tmp_path)
    assert direction is None, f"INTERSECTION should NOT fire (vsa=F), got {direction}"


def test_default_a_vsa_zero_change(tmp_path):
    """Default (no s2_firing.yaml) = A_VSA = identical to pre-change behavior.

    Uses bars where _vsa_pass=True to confirm the default fires as before.
    """
    from backend.v9.config_loader import reset_s2_firing_cache
    from backend.v9 import config_loader as cl

    # Don't write s2_firing.yaml — tests the fallback
    real_config = cl._CONFIG_DIR
    for f in ("auth_matrix.yaml", "targets.yaml", "stop_params.yaml"):
        src = real_config / f
        if src.exists():
            shutil.copy(src, tmp_path / f)

    old_dir = cl._CONFIG_DIR
    cl._CONFIG_DIR = tmp_path
    reset_s2_firing_cache()

    try:
        from backend.v9.systems.five_min.five_min_system import FiveMinSystem

        # Build bars where ALL variants pass (b2 very low vol)
        base = 5500.0
        bars = [
            {"ts": 1000 + i, "o": base, "h": base + 1, "l": base - 1, "c": base + 0.5, "v": 500}
            for i in range(4)
        ]
        # b0
        bars.append({"ts": 1004, "o": base, "h": base + 1, "l": base - 1, "c": base + 0.5, "v": 500})
        # b1 — bearish + high vol
        bars.append({"ts": 1005, "o": base + 2, "h": base + 3, "l": base - 1, "c": base - 0.5, "v": 1000})
        # b2 — very low vol (passes all variants)
        bars.append({"ts": 1006, "o": base, "h": base + 0.25, "l": base - 0.25, "c": base, "v": 10})
        # b3 — bullish
        bars.append({"ts": 1007, "o": base - 0.5, "h": base + 1, "l": base - 0.5, "c": base + 0.75, "v": 500})
        # b4 — confirm above b3.high
        bars.append({"ts": 1008, "o": base + 0.5, "h": base + 2, "l": base + 0.25, "c": base + 1.5, "v": 500})

        stub = _StubFiveMin()
        detect = FiveMinSystem._detect_reactive.__get__(stub, type(stub))
        direction, conf, info = detect(bars)
        assert direction == "LONG", f"Default A_VSA should fire LONG with all-pass bars, got {direction}"
    finally:
        cl._CONFIG_DIR = old_dir
        reset_s2_firing_cache()


def test_invalid_variant_falls_back_to_a_vsa(tmp_path):
    """Invalid variant in YAML → fallback A_VSA + warning (no crash)."""
    from backend.v9.config_loader import reset_s2_firing_cache, load_s2_firing
    from backend.v9 import config_loader as cl

    yaml_path = tmp_path / "s2_firing.yaml"
    yaml_path.write_text(yaml.dump({"variant": "GARBAGE"}))

    old_dir = cl._CONFIG_DIR
    cl._CONFIG_DIR = tmp_path
    reset_s2_firing_cache()

    try:
        result = load_s2_firing()
        assert result == "A_VSA", f"Invalid variant should fallback to A_VSA, got {result}"
    finally:
        cl._CONFIG_DIR = old_dir
        reset_s2_firing_cache()
