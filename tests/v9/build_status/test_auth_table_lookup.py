"""Tests for build_status/auth_table_lookup.py.

Verifies that the Python const dict faithfully mirrors S2_AUTH_TABLE_V1.md §4.
Source: docs/spec_authority/S2_AUTH_TABLE_V1.md (🔒 LOCKED 2026-05-25 12:22)
"""

import pytest

from backend.v9.systems.build_status.auth_table_lookup import (
    AUTH_TABLE,
    S2_PATTERN_IDS,
    WOODIES_PATTERN_IDS,
    lookup_auth_cell,
    is_skip,
    DAY_TYPE_SHORT_TO_ENUM,
)


class TestAuthTableStructure:
    def test_exactly_10_s2_patterns(self):
        """S2_AUTH_TABLE_V1.md §2: exactly 10 PatternName values."""
        assert len(S2_PATTERN_IDS) == 10

    def test_s2_pattern_ids_exact_order(self):
        """S2_AUTH_TABLE_V1.md §2: verbatim pattern list."""
        expected = [
            "REACTIVE_LONG",
            "REACTIVE_SHORT",
            "INITIATIVE_LONG",
            "INITIATIVE_SHORT",
            "INVERSE_HNS_LONG",
            "HNS_TOP_SHORT",
            "DOUBLE_BOTTOM_EE_LONG",
            "DOUBLE_TOP_AA_SHORT",
            "BULL_FLAG_LONG",
            "BEAR_FLAG_SHORT",
        ]
        assert S2_PATTERN_IDS == expected

    def test_exactly_9_woodies_patterns(self):
        """D-092_S4_WOODIES_UPDATE.md §2: exactly 9 Woodies patterns."""
        assert len(WOODIES_PATTERN_IDS) == 9

    def test_woodies_pattern_ids_exact(self):
        """D-092 §2: verbatim Woodies pattern list."""
        expected = ["ZLR", "TLB", "TT", "GB100", "Vegas", "Ghost", "FaMir", "HTLB", "HFE"]
        assert WOODIES_PATTERN_IDS == expected

    def test_auth_table_has_10_patterns(self):
        """AUTH_TABLE must cover all 10 S2 patterns."""
        assert set(AUTH_TABLE.keys()) == set(S2_PATTERN_IDS)

    def test_auth_table_has_7_day_types_per_pattern(self):
        """Each pattern must have exactly 7 day_type entries."""
        expected_day_types = {
            "Trend_Normal", "Trend_DD", "Neutral_Extreme",
            "Variation", "Neutral_Center", "Normal", "Nontrend",
        }
        for pattern, row in AUTH_TABLE.items():
            assert set(row.keys()) == expected_day_types, f"Pattern {pattern} missing day types"

    def test_total_cells_70(self):
        """10 patterns × 7 day types = 70 cells total."""
        total = sum(len(v) for v in AUTH_TABLE.values())
        assert total == 70

    def test_all_verdicts_valid(self):
        """All verdicts must be FULL, REDUCED, or SKIP."""
        for pattern, row in AUTH_TABLE.items():
            for dt, cell in row.items():
                verdict = cell[0]
                assert verdict in ("FULL", "REDUCED", "SKIP"), (
                    f"Invalid verdict {verdict!r} for {pattern} × {dt}"
                )

    def test_all_contract_values_in_0_to_3(self):
        """All contract values must be in {0, 1, 2, 3}."""
        for pattern, row in AUTH_TABLE.items():
            for dt, cell in row.items():
                for n in cell[1:]:
                    assert 0 <= n <= 3, f"Out-of-range contracts={n} for {pattern} × {dt}"

    def test_nt_global_zeros(self):
        """S2_AUTH_TABLE_V1.md §6.1: NT day = global skip, all contracts=0."""
        for pattern in S2_PATTERN_IDS:
            cell = AUTH_TABLE[pattern]["Nontrend"]
            assert cell == ("SKIP", 0, 0, 0), (
                f"Pattern {pattern} × Nontrend must be SKIP/0/0/0, got {cell}"
            )


class TestAuthTableCellValues:
    """Spot-check representative cells against S2_AUTH_TABLE_V1.md §4."""

    def test_reactive_long_tn(self):
        """REACTIVE_LONG × TN = REDUCED 2/1/0."""
        assert AUTH_TABLE["REACTIVE_LONG"]["Trend_Normal"] == ("REDUCED", 2, 1, 0)

    def test_reactive_long_neuc(self):
        """REACTIVE_LONG × NeuC = FULL 3/2/2."""
        assert AUTH_TABLE["REACTIVE_LONG"]["Neutral_Center"] == ("FULL", 3, 2, 2)

    def test_initiative_long_norm_zeroed(self):
        """INITIATIVE_LONG × Norm = SKIP 0/0/0 (audit B zeroed per §5.1)."""
        assert AUTH_TABLE["INITIATIVE_LONG"]["Normal"] == ("SKIP", 0, 0, 0)

    def test_initiative_long_tn(self):
        """INITIATIVE_LONG × TN = FULL 3/2/1."""
        assert AUTH_TABLE["INITIATIVE_LONG"]["Trend_Normal"] == ("FULL", 3, 2, 1)

    def test_inverse_hns_tdd_zeroed(self):
        """INVERSE_HNS_LONG × TDD = SKIP 0/0/0 (audit B §5.1 cell #1)."""
        assert AUTH_TABLE["INVERSE_HNS_LONG"]["Trend_DD"] == ("SKIP", 0, 0, 0)

    def test_double_bottom_tn_zeroed(self):
        """DOUBLE_BOTTOM_EE_LONG × TN = SKIP 0/0/0 (audit B §5.1 cell #3)."""
        assert AUTH_TABLE["DOUBLE_BOTTOM_EE_LONG"]["Trend_Normal"] == ("SKIP", 0, 0, 0)

    def test_bull_flag_neuc_typo_fix(self):
        """BULL_FLAG_LONG × NeuC = SKIP 0/0/0 (typo fix per §1 Q decision t1)."""
        assert AUTH_TABLE["BULL_FLAG_LONG"]["Neutral_Center"] == ("SKIP", 0, 0, 0)

    def test_bull_flag_tn_full(self):
        """BULL_FLAG_LONG × TN = FULL 3/2/2."""
        assert AUTH_TABLE["BULL_FLAG_LONG"]["Trend_Normal"] == ("FULL", 3, 2, 2)

    def test_bear_flag_norm_reduced(self):
        """BEAR_FLAG_SHORT × Norm = REDUCED 2/1/0."""
        assert AUTH_TABLE["BEAR_FLAG_SHORT"]["Normal"] == ("REDUCED", 2, 1, 0)


class TestLookupFunctions:
    def test_lookup_by_enum_value(self):
        cell = lookup_auth_cell("REACTIVE_LONG", "Trend_Normal")
        assert cell == ("REDUCED", 2, 1, 0)

    def test_lookup_by_short_key(self):
        """Short key 'TN' must resolve to Trend_Normal."""
        cell = lookup_auth_cell("REACTIVE_LONG", "TN")
        assert cell == ("REDUCED", 2, 1, 0)

    def test_lookup_unknown_day_type_fallback(self):
        """Unknown day_type falls back to Neutral_Center per §6.4."""
        cell = lookup_auth_cell("REACTIVE_LONG", "GARBAGE_TYPE")
        neuc_cell = lookup_auth_cell("REACTIVE_LONG", "Neutral_Center")
        assert cell == neuc_cell

    def test_lookup_unknown_pattern_raises(self):
        """Unknown pattern raises ValueError per §6.5."""
        with pytest.raises(ValueError, match="Unknown pattern_name"):
            lookup_auth_cell("FAKE_PATTERN", "Trend_Normal")

    def test_is_skip_nt(self):
        assert is_skip("BULL_FLAG_LONG", "Nontrend") is True

    def test_is_skip_full_cell(self):
        assert is_skip("BULL_FLAG_LONG", "Trend_Normal") is False

    def test_is_skip_neuc_bull_flag(self):
        """NeuC × Bull Flag is SKIP (typo fix)."""
        assert is_skip("BULL_FLAG_LONG", "Neutral_Center") is True
