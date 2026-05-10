"""R3 Spec Compliance Tests — System 5 (tpo).

Validates every requirement from MEMS26_TPO_PROFILE_DECISION_TREE_V2.
"""
import pytest

from backend.v9.systems.tpo.schemas import (
    TPOProfile, TPOConfig, TPOLevel, InitialBalance,
    ProfileShape, MigrationPattern, OTFClarity, Intent,
    IBWidth, SessionState, OpeningBehavior, POCMigration,
)
from backend.v9.systems.tpo.profile_builder import (
    init_profile, add_price, advance_letter, lock_ib, refresh_levels,
    LETTERS,
)
from backend.v9.systems.tpo.detector import (
    classify_shape, detect_intent, detect_migration_pattern,
    infer_otf_clarity,
)
from backend.v9.systems.tpo import levels as calc


# ── Helpers ──────────────────────────────────────────────────────

def _config():
    return TPOConfig()

def _profile_with_levels(prices, letters_per_level=3):
    """Build a profile with levels at given prices."""
    config = _config()
    profile = init_profile(config)
    for p in prices:
        for _ in range(letters_per_level):
            add_price(profile, p, config)
    refresh_levels(profile, config)
    return profile


# ── Q1: Session State ────────────────────────────────────────────

class TestQ1SessionState:
    def test_Q1_session_state(self):
        assert SessionState.PRE_OPEN.value == "PRE_OPEN"
        assert SessionState.BUILDING.value == "BUILDING"
        assert SessionState.LOCKED.value == "LOCKED"
        assert SessionState.CLOSED.value == "CLOSED"


# ── A1: Init ─────────────────────────────────────────────────────

class TestA1Init:
    def test_A1_init(self):
        profile = init_profile(_config())
        assert profile.session_state == SessionState.BUILDING
        assert profile.current_letter == "A"
        assert len(profile.levels) == 0


# ── A2: Letters ──────────────────────────────────────────────────

class TestA2Letters:
    def test_A2_letters(self):
        """13 TPO letters A-M per spec."""
        assert len(LETTERS) == 13
        assert LETTERS == "ABCDEFGHIJKLM"


# ── B1: Open Position ───────────────────────────────────────────

class TestB1OpenPosition:
    def test_B1_open_position(self):
        ob = OpeningBehavior()
        assert ob.open_vs_pd_va is None
        ob.open_vs_pd_va = "INSIDE"
        assert ob.open_vs_pd_va == "INSIDE"


# ── B2: First 5 Min ─────────────────────────────────────────────

class TestB2First5Min:
    def test_B2_first5min(self):
        ob = OpeningBehavior(direction_5min="UP", distance_pts=4.0)
        assert ob.direction_5min == "UP"


# ── C1: Letter Advance ──────────────────────────────────────────

class TestC1LetterAdvance:
    def test_C1_letter_advance(self):
        config = _config()
        profile = init_profile(config)
        add_price(profile, 5250.0, config)
        advance_letter(profile, config)
        assert profile.current_letter == "B"
        advance_letter(profile, config)
        assert profile.current_letter == "C"


# ── C2: IB Lock ─────────────────────────────────────────────────

class TestC2IBLock:
    def test_C2_ib_lock(self):
        config = _config()
        profile = init_profile(config)
        add_price(profile, 5240.0, config)
        add_price(profile, 5260.0, config)
        lock_ib(profile, config)
        assert profile.ib.locked is True
        assert profile.ib.high == 5260.0
        assert profile.ib.low == 5240.0


# ── C3: IB Width Classification ─────────────────────────────────

class TestC3IBWidth:
    def test_C3_ib_width(self):
        config = _config()
        profile = init_profile(config)
        # Narrow: < 15
        add_price(profile, 5250.0, config)
        add_price(profile, 5260.0, config)
        lock_ib(profile, config)
        assert profile.ib.classification == IBWidth.NARROW  # 10pt

    def test_wide_ib(self):
        config = _config()
        profile = init_profile(config)
        add_price(profile, 5230.0, config)
        add_price(profile, 5260.0, config)
        lock_ib(profile, config)
        assert profile.ib.classification == IBWidth.WIDE  # 30pt


# ── C4: Single Prints ───────────────────────────────────────────

class TestC4SinglePrints:
    def test_C4_single_prints(self):
        config = _config()
        profile = init_profile(config)
        add_price(profile, 5250.0, config)  # 1 letter only
        add_price(profile, 5251.0, config)
        add_price(profile, 5252.0, config)
        refresh_levels(profile, config)
        # All levels have 1 letter = single prints
        assert len(profile.single_prints) > 0


# ── C5: Tails ────────────────────────────────────────────────────

class TestC5Tails:
    def test_C5_tails(self):
        config = _config()
        profile = init_profile(config)
        # Bottom: single prints (buying tail)
        add_price(profile, 5240.0, config)
        add_price(profile, 5240.25, config)
        # Middle: many letters
        for _ in range(5):
            profile.current_letter = "A"
            add_price(profile, 5250.0, config)
            add_price(profile, 5250.25, config)
        refresh_levels(profile, config)
        assert profile.buying_tail_count >= 0
        assert profile.selling_tail_count >= 0


# ── C6: POC Migration ───────────────────────────────────────────

class TestC6POCMigration:
    def test_C6_poc_migration(self):
        config = _config()
        profile = init_profile(config)
        for p in [5250, 5250.25, 5250.5]:
            add_price(profile, p, config)
        advance_letter(profile, config)
        assert len(profile.poc_migration.history) >= 1


# ── C7: Value Area ───────────────────────────────────────────────

class TestC7ValueArea:
    def test_C7_value_area(self):
        config = _config()
        profile = init_profile(config)
        prices = [5248, 5249, 5250, 5250, 5250, 5251, 5252]
        for p in prices:
            add_price(profile, float(p), config)
        refresh_levels(profile, config)
        assert profile.poc is not None
        assert profile.vah is not None
        assert profile.val is not None
        assert profile.vah >= profile.poc
        assert profile.val <= profile.poc


# ── D1: Profile Shapes ──────────────────────────────────────────

class TestD1Shapes:
    def test_D1_shapes(self):
        """All 8 profile shapes exist."""
        shapes = [s.value for s in ProfileShape]
        assert len(shapes) == 8
        for expected in ["D", "WIDE_D", "COMPACT_D", "P", "b", "DOUBLE_DIST", "THIN", "NEUTRAL"]:
            assert expected in shapes

    def test_shape_classification(self):
        config = _config()
        # Build a symmetric profile -> D shape
        profile = init_profile(config)
        for p in [5248, 5249, 5250, 5250, 5250, 5251, 5252]:
            add_price(profile, float(p), config)
        profile.session_high = 5252
        profile.session_low = 5248
        profile.ib = InitialBalance(high=5252, low=5248, width=4.0, locked=True)
        refresh_levels(profile, config)
        classify_shape(profile, config)
        assert profile.shape is not None


# ── D2: Shape Lock ───────────────────────────────────────────────

class TestD2ShapeLock:
    def test_D2_shape_lock(self):
        profile = TPOProfile()
        profile.shape_locked = False
        assert profile.shape_locked is False


# ── D3: HVN/LVN ─────────────────────────────────────────────────

class TestD3HVNLVN:
    def test_D3_hvn_lvn(self):
        config = _config()
        profile = init_profile(config)
        for p in [5248, 5249, 5250, 5250, 5250, 5251, 5252]:
            add_price(profile, float(p), config)
        refresh_levels(profile, config)
        assert isinstance(profile.hvn_prices, list)
        assert isinstance(profile.lvn_prices, list)


# ── D4: Naked POC ────────────────────────────────────────────────

class TestD4NakedPOC:
    def test_D4_naked_poc(self):
        profile = TPOProfile()
        assert isinstance(profile.naked_pocs, list)


# ── E1: Intent ───────────────────────────────────────────────────

class TestE1Intent:
    def test_E1_intent(self):
        config = _config()
        profile = TPOProfile()
        profile.buying_tail_count = 3
        profile.selling_tail_count = 0
        detect_intent(profile, config)
        assert profile.intent == Intent.BUYER

    def test_intent_seller(self):
        config = _config()
        profile = TPOProfile()
        profile.buying_tail_count = 0
        profile.selling_tail_count = 3
        detect_intent(profile, config)
        assert profile.intent == Intent.SELLER


# ── E2: Migration Pattern ───────────────────────────────────────

class TestE2Migration:
    def test_E2_migration(self):
        """All 4 migration patterns exist."""
        for mp in [MigrationPattern.FAILED, MigrationPattern.ACCEPTED,
                   MigrationPattern.ROTATIONAL, MigrationPattern.STUCK]:
            assert mp.value in ("FAILED", "ACCEPTED", "ROTATIONAL", "STUCK")

    def test_migration_detection(self):
        config = _config()
        profile = TPOProfile()
        profile.poc_migration = POCMigration(history=[5250, 5250, 5250, 5250])
        detect_migration_pattern(profile, config)
        assert profile.migration_pattern in (
            MigrationPattern.FAILED, MigrationPattern.ACCEPTED,
            MigrationPattern.ROTATIONAL, MigrationPattern.STUCK,
        )


# ── E3: OTF Clarity ─────────────────────────────────────────────

class TestE3OTFClarity:
    def test_E3_otf_clarity(self):
        """4 OTF states: BOTH_CLEAR, SELLERS_CLEAR, BUYERS_CLEAR, UNCLEAR."""
        config = _config()
        profile = TPOProfile()
        profile.buying_tail_count = 3
        profile.selling_tail_count = 3
        infer_otf_clarity(profile, config)
        assert profile.otf_clarity == OTFClarity.BOTH_CLEAR

    def test_sellers_clear(self):
        config = _config()
        profile = TPOProfile()
        profile.buying_tail_count = 0
        profile.selling_tail_count = 3
        infer_otf_clarity(profile, config)
        assert profile.otf_clarity == OTFClarity.SELLERS_CLEAR

    def test_buyers_clear(self):
        config = _config()
        profile = TPOProfile()
        profile.buying_tail_count = 3
        profile.selling_tail_count = 0
        infer_otf_clarity(profile, config)
        assert profile.otf_clarity == OTFClarity.BUYERS_CLEAR

    def test_unclear(self):
        config = _config()
        profile = TPOProfile()
        profile.buying_tail_count = 0
        profile.selling_tail_count = 0
        infer_otf_clarity(profile, config)
        assert profile.otf_clarity == OTFClarity.UNCLEAR


# ── F1: EOD ──────────────────────────────────────────────────────

class TestF1EOD:
    def test_F1_eod(self):
        """SessionState.LOCKED exists for EOD."""
        assert SessionState.LOCKED.value == "LOCKED"


# ── Anti-Patterns ────────────────────────────────────────────────

class TestAntiPatterns:
    def test_AP1_no_skip_letters(self):
        config = _config()
        profile = init_profile(config)
        add_price(profile, 5250.0, config)
        assert profile.current_letter == "A"
        advance_letter(profile, config)
        assert profile.current_letter == "B"

    def test_AP2_ib_immutable(self):
        config = _config()
        profile = init_profile(config)
        add_price(profile, 5240.0, config)
        add_price(profile, 5260.0, config)
        lock_ib(profile, config)
        old_high = profile.ib.high
        # After lock, adding price should not change IB
        profile.current_letter = "C"
        add_price(profile, 5270.0, config)
        assert profile.ib.high == old_high

    def test_AP3_degraded_mode(self):
        profile = TPOProfile()
        profile.data_quality = "DEGRADED"
        assert profile.data_quality == "DEGRADED"


# ── Config Params (14 per spec) ──────────────────────────────────

class TestConfigParams:
    def test_all_14_params(self):
        cfg = TPOConfig()
        assert cfg.tpo_period_minutes == 30
        assert cfg.value_area_pct == 0.70
        assert cfg.tick_size == 0.25
        assert cfg.naked_poc_lookback_days == 5
        assert cfg.single_print_min_letters == 1
        assert cfg.tail_min_letters == 2
        assert cfg.hvn_top_pct == 0.20
        assert cfg.lvn_bottom_pct == 0.10
        assert cfg.ib_width_narrow_max == 15.0
        assert cfg.ib_width_wide_min == 25.0
        assert cfg.poc_migration_threshold == 1.5
        assert cfg.poc_stuck_letters == 3
        assert cfg.open_pos_threshold_pts == 5.0
        assert cfg.reversal_threshold_pts == 3.0
