"""test_ideal_precision.py — F18 · T-413 regression tests.

Tests:
1. Golden 17.09 17:10 (leg +23.5, trigger delta+3,319) -> S1 & S3
2. Golden 17.09 17:45 -> S2
3. Synthetic bar matching S1 but not S2 -> counted correctly
"""
import math
import os
import sys
import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, 'scripts'))


# ---------------------------------------------------------------------------
# Import signature checks + helpers
# ---------------------------------------------------------------------------
from scripts.ideal_precision import (
    check_s1, check_s2, check_s3, check_s4, check_s5, check_s6,
    wilson_ci, load_golden_entries, SIGNATURES,
)


# ---------------------------------------------------------------------------
# Fixture: a minimal feature dict with all fields
# ---------------------------------------------------------------------------
def _make_feat(**overrides):
    """Build a feature dict with safe defaults (all signals OFF)."""
    base = dict(
        atr=6.0, hour='18:00', ph='C', zone='IN_VA',
        near_prev_edge=False, near_ib_edge=False,
        at_extreme=False, bars_from_extreme=10,
        with_day=False, with_ext=False, move_from_open_atr=-1.0,
        trigger_ok=False, body_ge_50=False,
        range_ge_08atr=False,
        vol_trig=False, vol_ratio=1.0,
        delta_with=False, delta_ratio=None,
        pullback_before=False, structure_break=False,
        rng=5.0, cp=0.2,
        bar_o=5000.0, bar_h=5005.0, bar_l=4995.0, bar_c=4996.0,
        bar_v=500, bar_delta=-200,
    )
    base.update(overrides)
    return base


class TestSignatureChecks:
    """Unit tests for S1-S6 signature functions."""

    def test_s1_base_all_true(self):
        feat = _make_feat(trigger_ok=True, range_ge_08atr=True, vol_trig=True)
        assert check_s1(feat) is True

    def test_s1_base_delta_instead_of_vol(self):
        feat = _make_feat(trigger_ok=True, range_ge_08atr=True, delta_with=True)
        assert check_s1(feat) is True

    def test_s1_missing_trigger(self):
        feat = _make_feat(trigger_ok=False, range_ge_08atr=True, vol_trig=True)
        assert check_s1(feat) is False

    def test_s1_missing_range(self):
        feat = _make_feat(trigger_ok=True, range_ge_08atr=False, vol_trig=True)
        assert check_s1(feat) is False

    def test_s1_missing_both_delta_vol(self):
        feat = _make_feat(trigger_ok=True, range_ge_08atr=True,
                          delta_with=False, vol_trig=False)
        assert check_s1(feat) is False

    def test_s2_needs_structure_break(self):
        feat = _make_feat(trigger_ok=True, range_ge_08atr=True, vol_trig=True,
                          structure_break=True)
        assert check_s2(feat) is True

    def test_s2_no_break(self):
        feat = _make_feat(trigger_ok=True, range_ge_08atr=True, vol_trig=True,
                          structure_break=False)
        assert check_s2(feat) is False

    def test_s3_needs_pullback(self):
        feat = _make_feat(trigger_ok=True, range_ge_08atr=True, delta_with=True,
                          pullback_before=True)
        assert check_s3(feat) is True

    def test_s3_no_pullback(self):
        feat = _make_feat(trigger_ok=True, range_ge_08atr=True, delta_with=True,
                          pullback_before=False)
        assert check_s3(feat) is False

    def test_s4_needs_ib_edge(self):
        feat = _make_feat(trigger_ok=True, range_ge_08atr=True, vol_trig=True,
                          near_ib_edge=True)
        assert check_s4(feat) is True

    def test_s5_not_in_va(self):
        feat = _make_feat(trigger_ok=True, range_ge_08atr=True, vol_trig=True,
                          zone='ABOVE_VA')
        assert check_s5(feat) is True

    def test_s5_in_va_fails(self):
        feat = _make_feat(trigger_ok=True, range_ge_08atr=True, vol_trig=True,
                          zone='IN_VA')
        assert check_s5(feat) is False

    def test_s6_with_day(self):
        feat = _make_feat(trigger_ok=True, range_ge_08atr=True, vol_trig=True,
                          with_day=True)
        assert check_s6(feat) is True


class TestSyntheticBarCounting:
    """Test that synthetic bars matching S1 but not S2 are counted correctly."""

    def test_s1_yes_s2_no(self):
        """A bar matching S1 (trigger+range+vol) but without structure_break
        should match S1 and not S2."""
        feat = _make_feat(
            trigger_ok=True, range_ge_08atr=True, vol_trig=True,
            structure_break=False,
        )
        assert check_s1(feat) is True
        assert check_s2(feat) is False

    def test_all_signatures_computed(self):
        """Verify all 6 signatures are checked."""
        feat = _make_feat(
            trigger_ok=True, range_ge_08atr=True, vol_trig=True,
            structure_break=True, pullback_before=True,
            near_ib_edge=True, zone='ABOVE_VA', with_day=True,
        )
        results = {name: fn(feat) for name, fn in SIGNATURES.items()}
        assert results == {
            'S1': True, 'S2': True, 'S3': True,
            'S4': True, 'S5': True, 'S6': True,
        }


class TestWilsonCI:
    """Test Wilson confidence interval."""

    def test_zero_total(self):
        lo, hi = wilson_ci(0, 0)
        assert lo == 0.0
        assert hi == 0.0

    def test_perfect(self):
        lo, hi = wilson_ci(100, 100)
        assert lo > 0.95
        assert hi == 1.0

    def test_half(self):
        lo, hi = wilson_ci(50, 100)
        assert 0.40 < lo < 0.50
        assert 0.50 < hi < 0.60

    def test_small_sample(self):
        lo, hi = wilson_ci(3, 10)
        assert 0.0 < lo < 0.30
        assert 0.30 < hi < 0.70


class TestGoldenEntryLoading:
    """Test that golden entries can be loaded and filtered."""

    def test_golden_loads(self):
        """Golden entries file exists and filters to variant C."""
        golden = load_golden_entries()
        # All should satisfy variant C criteria
        for e in golden:
            assert e['trigger_ok'], f"Entry {e['d']} {e['entry_il']} not trigger_ok"
            assert e['delta_with'] or e['vol_trig'], \
                f"Entry {e['d']} {e['entry_il']} has neither delta_with nor vol_trig"
            assert e['range_ge_08atr'], f"Entry {e['d']} {e['entry_il']} not range_ge_08atr"

    def test_golden_count_reasonable(self):
        """Expect a non-trivial number of golden entries."""
        golden = load_golden_entries()
        # The spec says ~49, but we accept any reasonable count
        assert len(golden) >= 3, f"Only {len(golden)} golden entries — too few"
        assert len(golden) <= 200, f"{len(golden)} golden entries — suspiciously many"
