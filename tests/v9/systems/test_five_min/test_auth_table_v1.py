"""Tests for Auth Table V1 (Pkg 8 · S2_AUTH_TABLE_V1.md)."""
import logging
import pytest
from typing import get_args
from backend.v9.systems.five_min.auth_table_v1 import get_auth_cell, _AUTH_TABLE_V1, DAY_TYPES
from backend.v9.systems.five_min.output_schema import PatternName


class TestCoverage:
    def test_table_coverage_70_cells(self):
        assert len(_AUTH_TABLE_V1) == 70

    def test_pattern_coverage_perfect(self):
        assert {k[0] for k in _AUTH_TABLE_V1} == set(get_args(PatternName))

    def test_day_type_coverage_perfect(self):
        assert {k[1] for k in _AUTH_TABLE_V1} == set(DAY_TYPES)
        assert len(DAY_TYPES) == 7


class TestInvariants:
    def test_all_verdicts_valid(self):
        for (p, d), (v, h, m, l) in _AUTH_TABLE_V1.items():
            assert v in ('FULL', 'REDUCED', 'SKIP'), f"Bad verdict {v} at ({p},{d})"

    def test_all_contracts_in_range(self):
        for (p, d), (v, h, m, l) in _AUTH_TABLE_V1.items():
            for c in (h, m, l):
                assert c in (0, 1, 2, 3), f"Bad contracts {c} at ({p},{d})"

    def test_nt_row_global_skip(self):
        for p in get_args(PatternName):
            assert _AUTH_TABLE_V1[(p, "Nontrend")] == ("SKIP", 0, 0, 0), f"NT violated for {p}"

    def test_skip_verdict_zero_contracts(self):
        for (p, d), (v, h, m, l) in _AUTH_TABLE_V1.items():
            if v == 'SKIP':
                assert (h, m, l) == (0, 0, 0), f"SKIP non-zero at ({p},{d})"

    def test_max_contracts_le_3(self):
        mx = max(max(v[1], v[2], v[3]) for v in _AUTH_TABLE_V1.values())
        assert mx == 3


class TestSpotChecks:
    def test_reactive_long_neuC_full_3_2_2(self):
        assert _AUTH_TABLE_V1[('REACTIVE_LONG', 'Neutral_Center')] == ('FULL', 3, 2, 2)

    def test_initiative_long_norm_skip(self):
        assert _AUTH_TABLE_V1[('INITIATIVE_LONG', 'Normal')] == ('SKIP', 0, 0, 0)

    def test_inverse_hns_tdd_skip(self):
        assert _AUTH_TABLE_V1[('INVERSE_HNS_LONG', 'Trend_DD')] == ('SKIP', 0, 0, 0)

    def test_double_bottom_tn_skip(self):
        assert _AUTH_TABLE_V1[('DOUBLE_BOTTOM_EE_LONG', 'Trend_Normal')] == ('SKIP', 0, 0, 0)

    def test_bull_flag_neuC_typo_fixed(self):
        assert _AUTH_TABLE_V1[('BULL_FLAG_LONG', 'Neutral_Center')] == ('SKIP', 0, 0, 0)

    def test_hns_top_short_matches_inverse_hns_long(self):
        for d in DAY_TYPES:
            assert _AUTH_TABLE_V1[('HNS_TOP_SHORT', d)] == _AUTH_TABLE_V1[('INVERSE_HNS_LONG', d)]


class TestAPI:
    def test_get_auth_cell_unknown_pattern_raises(self):
        with pytest.raises(ValueError, match="not in PatternName"):
            get_auth_cell('FAKE_PATTERN', 'Trend_Normal')

    def test_get_auth_cell_unknown_day_type_fallback(self, caplog):
        with caplog.at_level(logging.WARNING):
            result = get_auth_cell('REACTIVE_LONG', 'UNKNOWN')
        assert result == ('FULL', 3, 2, 2)  # Neutral_Center fallback
        assert any("unknown day_type" in r.message for r in caplog.records)
