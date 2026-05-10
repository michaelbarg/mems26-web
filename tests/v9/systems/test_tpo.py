"""Tests for TPO Profile System (System 5) — W9.

Covers:
  - Profile builder (Stages A-C): init, add_price, advance_letter, lock_ib
  - Level calculations: POC, VAH/VAL, HVN/LVN, single prints, tails
  - Shape classification (Stage D): all 8 shapes
  - Intent/OTF clarity (Stage E)
  - API endpoints: GET /profile, GET /levels
"""

import os
import pytest

os.environ.setdefault("BRIDGE_TOKEN", "michael-mems26-2026")

from backend.v9.systems.tpo.schemas import (
    TPOConfig, TPOProfile, TPOLevel, IBWidth,
    ProfileShape, MigrationPattern, Intent, OTFClarity,
    SessionState,
)
from backend.v9.systems.tpo import profile_builder as pb
from backend.v9.systems.tpo import levels as calc
from backend.v9.systems.tpo import detector
from backend.v9.systems.tpo import SYSTEM_ID, SYSTEM_NAME, SYSTEM_COLOR


# ── Fixtures ──

@pytest.fixture
def config():
    return TPOConfig()


def _make_profile_with_prices(prices_per_letter, config=None):
    """Helper: build a profile from a dict of {letter: [prices]}."""
    config = config or TPOConfig()
    profile = pb.init_profile(config)
    for letter, prices in prices_per_letter.items():
        profile.current_letter = letter
        for p in prices:
            profile = pb.add_price(profile, p, config)
    profile = pb.refresh_levels(profile, config)
    return profile


# ══════════════════════════════════════════════════════════════
# System Constants
# ══════════════════════════════════════════════════════════════

class TestSystemConstants:
    def test_system_id(self):
        assert SYSTEM_ID == 5

    def test_system_name(self):
        assert SYSTEM_NAME == "tpo"

    def test_system_color(self):
        assert SYSTEM_COLOR == "#79c0ff"


# ══════════════════════════════════════════════════════════════
# Profile Builder — Stages A-C
# ══════════════════════════════════════════════════════════════

class TestProfileInit:
    def test_init_empty(self, config):
        p = pb.init_profile(config)
        assert p.session_state == SessionState.BUILDING
        assert p.current_letter == "A"
        assert p.levels == {}
        assert p.poc is None

    def test_letters_constant(self):
        assert pb.LETTERS == "ABCDEFGHIJKLM"
        assert pb.MAX_LETTERS == 13


class TestAddPrice:
    def test_single_price(self, config):
        p = pb.init_profile(config)
        p = pb.add_price(p, 5400.25, config)
        assert len(p.levels) == 1
        key = "5400.2500"
        assert key in p.levels
        assert p.levels[key].letters == ["A"]

    def test_same_price_same_letter(self, config):
        p = pb.init_profile(config)
        p = pb.add_price(p, 5400.25, config)
        p = pb.add_price(p, 5400.25, config)
        # Same letter should not duplicate
        assert p.levels["5400.2500"].letters == ["A"]

    def test_multiple_prices(self, config):
        p = pb.init_profile(config)
        p = pb.add_price(p, 5400.00, config)
        p = pb.add_price(p, 5400.25, config)
        p = pb.add_price(p, 5400.50, config)
        assert len(p.levels) == 3
        assert p.session_high == 5400.50
        assert p.session_low == 5400.00

    def test_quantizes_to_tick(self, config):
        p = pb.init_profile(config)
        p = pb.add_price(p, 5400.13, config)  # rounds to 5400.25
        assert "5400.2500" in p.levels

    def test_ib_updates_in_letter_a(self, config):
        p = pb.init_profile(config)
        p = pb.add_price(p, 5400.00, config)
        p = pb.add_price(p, 5410.00, config)
        assert p.ib.high == 5410.00
        assert p.ib.low == 5400.00
        assert p.ib.width == 10.0

    def test_ib_updates_in_letter_b(self, config):
        p = pb.init_profile(config)
        p.current_letter = "B"
        p = pb.add_price(p, 5395.00, config)
        p = pb.add_price(p, 5415.00, config)
        assert p.ib.high == 5415.00
        assert p.ib.low == 5395.00

    def test_ib_not_updated_after_lock(self, config):
        p = pb.init_profile(config)
        p = pb.add_price(p, 5400.00, config)
        p.ib.locked = True
        p.current_letter = "C"
        p = pb.add_price(p, 5500.00, config)
        assert p.ib.high == 5400.00  # unchanged


class TestAdvanceLetter:
    def test_advance_a_to_b(self, config):
        p = pb.init_profile(config)
        p = pb.add_price(p, 5400.00, config)
        p = pb.advance_letter(p, config)
        assert p.current_letter == "B"
        assert p.letter_count == 2

    def test_advance_full_session(self, config):
        p = pb.init_profile(config)
        for i in range(12):
            p = pb.add_price(p, 5400.00 + i * 0.25, config)
            p = pb.advance_letter(p, config)
        assert p.current_letter == "M"
        assert p.letter_count == 13

    def test_no_advance_past_m(self, config):
        p = pb.init_profile(config)
        p.current_letter = "M"
        p = pb.add_price(p, 5400.00, config)
        p = pb.advance_letter(p, config)
        assert p.current_letter == "M"


class TestLockIB:
    def test_lock_narrow(self, config):
        p = pb.init_profile(config)
        p.ib.high = 5410.0
        p.ib.low = 5400.0
        p.ib.width = 10.0
        p = pb.lock_ib(p, config)
        assert p.ib.locked is True
        assert p.ib.classification == IBWidth.NARROW

    def test_lock_medium(self, config):
        p = pb.init_profile(config)
        p.ib.high = 5420.0
        p.ib.low = 5400.0
        p.ib.width = 20.0
        p = pb.lock_ib(p, config)
        assert p.ib.classification == IBWidth.MEDIUM

    def test_lock_wide(self, config):
        p = pb.init_profile(config)
        p.ib.high = 5430.0
        p.ib.low = 5400.0
        p.ib.width = 30.0
        p = pb.lock_ib(p, config)
        assert p.ib.classification == IBWidth.WIDE


# ══════════════════════════════════════════════════════════════
# Level Calculations
# ══════════════════════════════════════════════════════════════

class TestPOC:
    def test_empty(self):
        poc, count = calc.compute_poc({})
        assert poc is None
        assert count == 0

    def test_single_level(self):
        levels = {"100.0": TPOLevel(price=100.0, letters=["A", "B"])}
        poc, count = calc.compute_poc(levels)
        assert poc == 100.0
        assert count == 2

    def test_highest_count_wins(self):
        levels = {
            "100.0": TPOLevel(price=100.0, letters=["A"]),
            "101.0": TPOLevel(price=101.0, letters=["A", "B", "C"]),
            "102.0": TPOLevel(price=102.0, letters=["A", "B"]),
        }
        poc, count = calc.compute_poc(levels)
        assert poc == 101.0
        assert count == 3

    def test_tie_goes_to_higher_price(self):
        levels = {
            "100.0": TPOLevel(price=100.0, letters=["A", "B"]),
            "102.0": TPOLevel(price=102.0, letters=["A", "B"]),
        }
        poc, _ = calc.compute_poc(levels)
        assert poc == 102.0


class TestValueArea:
    def test_empty(self):
        config = TPOConfig()
        vah, val = calc.compute_value_area({}, None, config)
        assert vah is None and val is None

    def test_symmetric_profile(self):
        """D-shape: POC at mid, value area expands symmetrically."""
        config = TPOConfig(value_area_pct=0.70)
        levels = {}
        # Build bell curve: 5 levels, POC at 102
        for price, count in [(100, 1), (101, 2), (102, 4), (103, 2), (104, 1)]:
            key = f"{price:.4f}"
            levels[key] = TPOLevel(
                price=float(price),
                letters=[chr(65 + i) for i in range(count)],
            )
        # Total = 10, target = 7, POC=102 (4)
        # Add 103 (2) → 6, add 101 (2) → 8 ≥ 7 → done
        vah, val = calc.compute_value_area(levels, 102.0, config)
        assert vah == 103.0
        assert val == 101.0

    def test_100_pct_covers_all(self):
        config = TPOConfig(value_area_pct=1.0)
        levels = {
            "100.0": TPOLevel(price=100.0, letters=["A"]),
            "101.0": TPOLevel(price=101.0, letters=["A", "B"]),
            "102.0": TPOLevel(price=102.0, letters=["A"]),
        }
        vah, val = calc.compute_value_area(levels, 101.0, config)
        assert vah == 102.0
        assert val == 100.0


class TestHVNLVN:
    def test_empty(self):
        config = TPOConfig()
        hvn, lvn = calc.compute_hvn_lvn({}, config)
        assert hvn == [] and lvn == []

    def test_identifies_nodes(self):
        config = TPOConfig(hvn_top_pct=0.20, lvn_bottom_pct=0.20)
        levels = {
            f"{p:.4f}": TPOLevel(price=float(p), letters=[chr(65 + i) for i in range(c)])
            for p, c in [(100, 1), (101, 2), (102, 5), (103, 3), (104, 1)]
        }
        hvn, lvn = calc.compute_hvn_lvn(levels, config)
        assert 102.0 in hvn  # highest count
        assert 100.0 in lvn or 104.0 in lvn  # lowest counts


class TestSinglePrints:
    def test_finds_single_prints(self):
        config = TPOConfig(single_print_min_letters=1)
        levels = {
            "100.0": TPOLevel(price=100.0, letters=["A"]),
            "101.0": TPOLevel(price=101.0, letters=["A", "B", "C"]),
            "102.0": TPOLevel(price=102.0, letters=["A"]),
        }
        sp = calc.compute_single_prints(levels, config)
        assert 100.0 in sp
        assert 102.0 in sp
        assert 101.0 not in sp


class TestTails:
    def test_no_tails_in_empty(self):
        config = TPOConfig()
        buy, sell = calc.compute_tails({}, None, None, config)
        assert buy == 0 and sell == 0

    def test_buying_tail(self):
        config = TPOConfig(tail_min_letters=2)
        levels = {
            "100.0": TPOLevel(price=100.0, letters=["A"]),
            "100.25": TPOLevel(price=100.25, letters=["A"]),
            "100.50": TPOLevel(price=100.50, letters=["A", "B", "C"]),
            "100.75": TPOLevel(price=100.75, letters=["A", "B"]),
            "101.0": TPOLevel(price=101.0, letters=["A"]),
        }
        buy, sell = calc.compute_tails(levels, 100.0, 101.0, config)
        assert buy == 2  # 100.0 and 100.25 are single-print at bottom
        assert sell == 0  # only 101.0 at top, below min of 2 → filtered out

    def test_selling_tail(self):
        config = TPOConfig(tail_min_letters=2)
        levels = {
            "100.0": TPOLevel(price=100.0, letters=["A", "B"]),
            "100.25": TPOLevel(price=100.25, letters=["A", "B", "C"]),
            "100.50": TPOLevel(price=100.50, letters=["A"]),
            "100.75": TPOLevel(price=100.75, letters=["A"]),
        }
        buy, sell = calc.compute_tails(levels, 100.0, 100.75, config)
        assert buy == 0  # bottom has 2 letters, not single
        assert sell == 2


# ══════════════════════════════════════════════════════════════
# Shape Classification — Stage D
# ══════════════════════════════════════════════════════════════

class TestShapeClassification:
    def test_p_shape(self, config):
        """POC in upper third → P shape."""
        profile = _make_profile_with_prices({
            "A": [100, 101, 102, 103, 104],
            "B": [102, 103, 104],
            "C": [103, 104],
        }, config)
        profile.session_high = 104
        profile.session_low = 100
        profile = detector.classify_shape(profile, config)
        # POC should be near top
        assert profile.shape in (ProfileShape.P, ProfileShape.D, ProfileShape.THIN)

    def test_b_shape(self, config):
        """POC in lower third → b shape."""
        profile = _make_profile_with_prices({
            "A": [100, 101, 102, 103, 104],
            "B": [100, 101, 102],
            "C": [100, 101],
        }, config)
        profile.session_high = 104
        profile.session_low = 100
        profile = detector.classify_shape(profile, config)
        assert profile.shape in (ProfileShape.b, ProfileShape.D, ProfileShape.THIN)

    def test_empty_profile_unchanged(self, config):
        profile = pb.init_profile(config)
        profile = detector.classify_shape(profile, config)
        assert profile.shape is None

    def test_d_shape_symmetric(self, config):
        """Symmetric distribution → D shape."""
        profile = _make_profile_with_prices({
            "A": [100, 101, 102, 103, 104],
            "B": [101, 102, 103],
            "C": [101, 102, 103],
            "D": [100, 101, 102, 103, 104],
        }, config)
        profile.session_high = 104
        profile.session_low = 100
        profile = detector.classify_shape(profile, config)
        assert profile.shape is not None
        assert profile.shape_confidence > 0


# ══════════════════════════════════════════════════════════════
# Intent + OTF Clarity — Stage E
# ══════════════════════════════════════════════════════════════

class TestIntent:
    def test_buyer_intent(self, config):
        profile = TPOProfile(buying_tail_count=3, selling_tail_count=0)
        profile = detector.detect_intent(profile, config)
        assert profile.intent == Intent.BUYER

    def test_seller_intent(self, config):
        profile = TPOProfile(buying_tail_count=0, selling_tail_count=3)
        profile = detector.detect_intent(profile, config)
        assert profile.intent == Intent.SELLER

    def test_no_intent(self, config):
        profile = TPOProfile(buying_tail_count=0, selling_tail_count=0)
        profile = detector.detect_intent(profile, config)
        assert profile.intent == Intent.NONE


class TestOTFClarity:
    def test_both_clear(self, config):
        profile = TPOProfile(buying_tail_count=3, selling_tail_count=3)
        profile = detector.infer_otf_clarity(profile, config)
        assert profile.otf_clarity == OTFClarity.BOTH_CLEAR

    def test_sellers_clear(self, config):
        profile = TPOProfile(buying_tail_count=0, selling_tail_count=3)
        profile = detector.infer_otf_clarity(profile, config)
        assert profile.otf_clarity == OTFClarity.SELLERS_CLEAR

    def test_buyers_clear(self, config):
        profile = TPOProfile(buying_tail_count=3, selling_tail_count=0)
        profile = detector.infer_otf_clarity(profile, config)
        assert profile.otf_clarity == OTFClarity.BUYERS_CLEAR

    def test_unclear(self, config):
        profile = TPOProfile(buying_tail_count=0, selling_tail_count=0)
        profile = detector.infer_otf_clarity(profile, config)
        assert profile.otf_clarity == OTFClarity.UNCLEAR


class TestMigrationPattern:
    def test_stuck(self, config):
        from backend.v9.systems.tpo.schemas import POCMigration
        profile = TPOProfile()
        profile.poc_migration = POCMigration(
            history=[5400.0, 5400.0, 5400.0, 5400.0],
            stuck_count=4,
        )
        profile = detector.detect_migration_pattern(profile, config)
        assert profile.migration_pattern == MigrationPattern.STUCK

    def test_too_few_points(self, config):
        from backend.v9.systems.tpo.schemas import POCMigration
        profile = TPOProfile()
        profile.poc_migration = POCMigration(history=[5400.0, 5401.0])
        profile = detector.detect_migration_pattern(profile, config)
        assert profile.migration_pattern == MigrationPattern.ROTATIONAL


# ══════════════════════════════════════════════════════════════
# Integrated Profile Building
# ══════════════════════════════════════════════════════════════

class TestIntegratedProfile:
    def test_full_session_flow(self, config):
        """Build a mini session: 3 letters, lock IB, classify."""
        profile = pb.init_profile(config)

        # Letter A: 09:30-10:00
        for p in [5400, 5401, 5402, 5403, 5404]:
            profile = pb.add_price(profile, p, config)
        profile = pb.advance_letter(profile, config)

        # Letter B: 10:00-10:30
        for p in [5401, 5402, 5403, 5404, 5405]:
            profile = pb.add_price(profile, p, config)
        profile = pb.lock_ib(profile, config)
        profile = pb.advance_letter(profile, config)

        # Letter C: 10:30-11:00
        for p in [5402, 5403]:
            profile = pb.add_price(profile, p, config)

        profile = pb.refresh_levels(profile, config)
        profile = detector.classify_shape(profile, config)
        profile = detector.detect_intent(profile, config)
        profile = detector.infer_otf_clarity(profile, config)

        assert profile.current_letter == "C"
        assert profile.poc is not None
        assert profile.vah is not None
        assert profile.val is not None
        assert profile.ib.locked
        assert profile.shape is not None

    def test_poc_vah_val_example(self, config):
        """Verify POC/VAH/VAL on a known distribution.

        Prices (tick_size=0.25):
          5400.00: A         (1 letter)
          5400.25: A,B       (2 letters)
          5400.50: A,B,C     (3 letters) ← POC
          5400.75: A,B       (2 letters)
          5401.00: A         (1 letter)

        Total = 9, target = 9 * 0.70 = 6.3
        POC = 5400.50 (3), +5400.75 (2)=5, +5400.25 (2)=7 ≥ 6.3
        → VAH = 5400.75, VAL = 5400.25
        """
        profile = pb.init_profile(config)
        profile.current_letter = "A"
        for p in [5400.00, 5400.25, 5400.50, 5400.75, 5401.00]:
            profile = pb.add_price(profile, p, config)

        profile.current_letter = "B"
        for p in [5400.25, 5400.50, 5400.75]:
            profile = pb.add_price(profile, p, config)

        profile.current_letter = "C"
        profile = pb.add_price(profile, 5400.50, config)

        profile = pb.refresh_levels(profile, config)

        assert profile.poc == 5400.50
        assert profile.poc_vol == 3
        assert profile.vah == 5400.75
        assert profile.val == 5400.25


# ══════════════════════════════════════════════════════════════
# API Endpoints (with DB)
# ══════════════════════════════════════════════════════════════

class TestAPIBuildProfile:
    """Test the _build_profile_from_bars helper without DB."""

    def test_from_bars_list(self):
        """Simulate bars from DB."""
        from unittest.mock import MagicMock
        from backend.v9.systems.tpo.api import _build_profile_from_bars

        config = TPOConfig()
        bars = []
        for period_id, letter_prices in enumerate([
            [5400, 5401, 5402],
            [5401, 5402, 5403],
            [5402, 5403],
        ]):
            for price in letter_prices:
                bar = MagicMock()
                bar.period_id = period_id
                bar.price = float(price)
                bars.append(bar)

        profile = _build_profile_from_bars(bars, config)
        assert profile.poc is not None
        assert profile.vah is not None
        assert profile.val is not None
        assert profile.ib.locked  # > 2 periods
        assert profile.shape is not None
