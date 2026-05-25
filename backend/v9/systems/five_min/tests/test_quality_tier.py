"""Tests for Quality Tier V1 (deprecated) + V2 (Auth Table)."""
import logging
import pytest
from unittest.mock import patch
from backend.v9.systems.five_min.quality_tier import get_quality_tier, get_quality_tier_v2


_TPO = {"poc": 5250.0, "vah": 5260.0, "val": 5240.0}


# ── V1 tests (deprecated wrapper) ──

def test_high_at_poc():
    with pytest.warns(DeprecationWarning, match="get_quality_tier_v2"):
        tier, contracts = get_quality_tier(5250.5, tpo_data=_TPO)
    assert tier == 'HIGH'
    assert contracts == 3


def test_medium_in_value_area():
    with pytest.warns(DeprecationWarning, match="get_quality_tier_v2"):
        tier, contracts = get_quality_tier(5255.0, tpo_data=_TPO)
    assert tier == 'MEDIUM'
    assert contracts == 2


def test_low_outside_value():
    with pytest.warns(DeprecationWarning, match="get_quality_tier_v2"):
        tier, contracts = get_quality_tier(5275.0, tpo_data=_TPO)
    assert tier == 'LOW'
    assert contracts == 1


# ── V2 tests ──

def test_v2_reactive_long_neuC_at_poc():
    assert get_quality_tier_v2('REACTIVE_LONG', 'Neutral_Center', 5250.5, tpo_data=_TPO) == ('FULL', 'HIGH', 3)

def test_v2_reactive_long_neuC_in_va():
    assert get_quality_tier_v2('REACTIVE_LONG', 'Neutral_Center', 5255.0, tpo_data=_TPO) == ('FULL', 'MEDIUM', 2)

def test_v2_reactive_long_neuC_outside():
    assert get_quality_tier_v2('REACTIVE_LONG', 'Neutral_Center', 5275.0, tpo_data=_TPO) == ('FULL', 'LOW', 2)

def test_v2_initiative_long_norm_skip():
    v, t, c = get_quality_tier_v2('INITIATIVE_LONG', 'Normal', 5250.5, tpo_data=_TPO)
    assert v == 'SKIP' and c == 0

@pytest.mark.parametrize("pattern", [
    'REACTIVE_LONG', 'REACTIVE_SHORT', 'INITIATIVE_LONG', 'INITIATIVE_SHORT',
    'INVERSE_HNS_LONG', 'HNS_TOP_SHORT', 'DOUBLE_BOTTOM_EE_LONG',
    'DOUBLE_TOP_AA_SHORT', 'BULL_FLAG_LONG', 'BEAR_FLAG_SHORT',
])
def test_v2_nt_day_global_skip(pattern):
    v, t, c = get_quality_tier_v2(pattern, 'Nontrend', 5250.5, tpo_data=_TPO)
    assert v == 'SKIP' and c == 0

def test_v2_unknown_pattern_raises():
    with pytest.raises(ValueError, match="not in PatternName"):
        get_quality_tier_v2('FAKE', 'Trend_Normal', 5250.5, tpo_data=_TPO)

def test_v2_unknown_day_type_fallback(caplog):
    with caplog.at_level(logging.WARNING):
        v, t, c = get_quality_tier_v2('REACTIVE_LONG', 'WeirdType', 5250.5, tpo_data=_TPO)
    assert any("unknown day_type" in r.message for r in caplog.records)
    assert v == 'FULL'

def test_v2_tpo_data_none_fails_safe():
    with patch('backend.v9.systems.five_min.quality_tier._fetch_tpo', return_value=None):
        v, t, c = get_quality_tier_v2('REACTIVE_LONG', 'Neutral_Center', 5250.5)
    assert t == 'MEDIUM' and c == 2

def test_v2_proximity_pt_threshold():
    v, t, c = get_quality_tier_v2('REACTIVE_LONG', 'Neutral_Center', 5252.5, tpo_data=_TPO)
    assert t == 'MEDIUM'  # 2.5 > 2.0 → not HIGH
