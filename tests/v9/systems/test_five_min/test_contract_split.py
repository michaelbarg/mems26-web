"""Tests for contract_split module (Pkg 3c · D-091 §Contract Distribution)."""
import pytest
from backend.v9.systems.five_min.contract_split import get_contract_split, _SPLIT_MAP


class TestOFAFamily:
    def test_reactive_long_is_zohar_25_50_25(self):
        assert get_contract_split("REACTIVE_LONG") == (0.25, 0.50, 0.25)

    def test_reactive_short_is_zohar_25_50_25(self):
        assert get_contract_split("REACTIVE_SHORT") == (0.25, 0.50, 0.25)

    def test_initiative_long_is_zohar_25_50_25(self):
        assert get_contract_split("INITIATIVE_LONG") == (0.25, 0.50, 0.25)

    def test_initiative_short_is_zohar_25_50_25(self):
        assert get_contract_split("INITIATIVE_SHORT") == (0.25, 0.50, 0.25)


class TestHnSFamily:
    def test_inverse_hns_long_is_33_33_34(self):
        assert get_contract_split("INVERSE_HNS_LONG") == (0.33, 0.33, 0.34)

    def test_hns_top_short_is_33_33_34(self):
        assert get_contract_split("HNS_TOP_SHORT") == (0.33, 0.33, 0.34)


class TestDoubleFamily:
    def test_double_bottom_ee_long_is_33_33_34(self):
        assert get_contract_split("DOUBLE_BOTTOM_EE_LONG") == (0.33, 0.33, 0.34)

    def test_double_top_aa_short_is_33_33_34(self):
        assert get_contract_split("DOUBLE_TOP_AA_SHORT") == (0.33, 0.33, 0.34)


class TestFlagFamily:
    def test_bull_flag_long_is_50_50_zero(self):
        assert get_contract_split("BULL_FLAG_LONG") == (0.50, 0.50, 0.00)

    def test_bear_flag_short_is_50_50_zero(self):
        assert get_contract_split("BEAR_FLAG_SHORT") == (0.50, 0.50, 0.00)


class TestEdgeCases:
    def test_unknown_pattern_raises_value_error(self):
        with pytest.raises(ValueError, match="not registered"):
            get_contract_split("FOO")

    def test_all_splits_sum_to_1_0(self):
        for name, (t1, t2, t3) in _SPLIT_MAP.items():
            assert abs(t1 + t2 + t3 - 1.0) < 0.001, f"{name} sums to {t1+t2+t3}"

    def test_module_has_exactly_10_entries(self):
        assert len(_SPLIT_MAP) == 10
