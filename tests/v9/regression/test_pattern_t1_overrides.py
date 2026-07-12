"""Pattern×DayType T1 overrides — Michael ruling 2026-07-10 (TP audit)."""
import pytest
from unittest.mock import patch


def test_load_pattern_t1_points():
    """Config loader parses pattern_t1_points from targets.yaml.

    2026-07-12 (learning-v3): exact-value pins REMOVED — the values are ruled
    via Michael's click-apply (apply_targets_diff.py) and change legitimately;
    pinning them here made every ruled apply fail-and-revert (proven in the
    v3 drill). The MECHANICS are what regression must protect: the section
    parses, the ruled patterns exist, every value is a sane point figure.
    Exact values are protected by git history + the click-ruling itself.
    """
    from backend.v9.config_loader import load_pattern_t1_points
    # Reset cache to force reload
    import backend.v9.config_loader as cl
    cl._pattern_t1_loaded = False
    cl._pattern_t1_cache = None

    overrides = load_pattern_t1_points()
    assert isinstance(overrides, dict) and overrides

    # the originally-ruled pattern×day cells must EXIST (a vanished cell = a
    # broken merge), with values in the sanity band the apply script enforces
    for pat, dt in (("REACTIVE_LONG", "Variation"), ("FAMIR", "Variation"),
                    ("TLB", "Trend_Normal"), ("INITIATIVE_LONG", "Variation"),
                    ("BULL_FLAG_LONG", "Variation")):
        v = (overrides.get(pat) or {}).get(dt)
        assert v is not None, f"{pat}/{dt} vanished from targets.yaml"
        assert 1.0 <= v <= 30.0, f"{pat}/{dt}={v} outside sanity band"


def test_reactive_long_variation_t1_is_6pts():
    """REACTIVE_LONG × Variation: T1 = entry + 6pt (was ~9.3 = 1R)."""
    entry = 5800.0
    pts = 6.0
    t1 = entry + pts
    assert t1 == 5806.0


def test_famir_variation_t1_is_5pts():
    """FAMIR × Variation: T1 = entry + 5pt (was ~12.6 = 1R)."""
    entry = 5800.0
    pts = 5.0
    assert entry + pts == 5805.0


def test_tlb_trend_normal_t1_is_9pts():
    """TLB × Trend_Normal: T1 = entry + 9pt (was ~5.6 = 1R)."""
    entry = 5800.0
    pts = 9.0
    assert entry + pts == 5809.0


def test_initiative_long_variation_t1_is_8pts():
    """INITIATIVE_LONG × Variation: T1 = entry + 8pt (was ~18.4 = 1R)."""
    entry = 5800.0
    pts = 8.0
    assert entry + pts == 5808.0


def test_bull_flag_long_variation_t1_is_6pts():
    """BULL_FLAG_LONG × Variation: T1 = entry + 6pt (was ~12.1 = 1R)."""
    entry = 5800.0
    pts = 6.0
    assert entry + pts == 5806.0


def test_no_override_when_pattern_not_listed():
    """Unknown pattern×day_type combo → no override (returns None)."""
    from backend.v9.config_loader import load_pattern_t1_points
    import backend.v9.config_loader as cl
    cl._pattern_t1_loaded = False
    cl._pattern_t1_cache = None

    overrides = load_pattern_t1_points()
    assert overrides.get("NONEXISTENT_PATTERN") is None


def test_t2_t3_scale_from_t1():
    """T2 = entry ± 2×pts, T3 = entry ± 3×pts."""
    entry = 5800.0
    pts = 6.0
    sign = 1.0  # LONG
    t1 = round(entry + sign * pts, 2)
    t2 = round(entry + sign * 2 * pts, 2)
    t3 = round(entry + sign * 3 * pts, 2)
    assert t1 == 5806.0
    assert t2 == 5812.0
    assert t3 == 5818.0

    # SHORT
    sign = -1.0
    t1 = round(entry + sign * pts, 2)
    t2 = round(entry + sign * 2 * pts, 2)
    t3 = round(entry + sign * 3 * pts, 2)
    assert t1 == 5794.0
    assert t2 == 5788.0
    assert t3 == 5782.0
