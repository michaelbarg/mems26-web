"""T-06 — a ladder must never carry two exit levels at one price.

Root cause (measured on 7 live trades since 07-21, all S4/ZLR): the gateway's
t2 seeding read only setup["stop"], but ZLR ships its stop in
metadata.stop_initial (StopResolver design). The `or t1` fallback made the
step ZERO, so t2 landed EXACTLY on t1 — #693 SHORT entry 7797.75 stored
t1=t2=7793.75 while its metadata.stop_initial=7802.0 sat unread one key away.

Reproduces the live rows, then proves the fix: stop found in metadata → real
step; no stop anywhere → t2 stays ABSENT (Rule 1 — no fabrication); and the
degeneracy guard drops any level that duplicates a lower one, the shape I-59
already ruled ("duplicate t2 becomes None").
"""
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from backend.v9.gateway.trading_gateway import TradingGateway  # noqa: E402

seed = TradingGateway._seed_runner_targets
guard = TradingGateway._target_degeneracy_guard


class TestSeedReadsMetadataStop:
    def test_693_short_seeds_a_real_step_not_t1(self):
        """The exact live row: SHORT t1=7793.75, stop only in metadata
        (7802.0). Old code: t2=t1. Fixed: t2 = t1 − |t1−stop| = 7785.5."""
        s = {"direction": "SHORT", "t1": 7793.75, "t2": None, "t3": 7787.0,
             "stop": None, "metadata": {"stop_initial": 7802.0}}
        t1, t2, t3 = seed(s)
        assert t2 == pytest.approx(7785.5)
        assert t2 != t1

    def test_622_long_mirror(self):
        """#622: LONG t1=7744.75, metadata.stop_initial=7721.5 →
        t2 = t1 + 23.25 = 7768.0 (old code stored t2=t1=7744.75)."""
        s = {"direction": "LONG", "t1": 7744.75, "t2": 0.0, "t3": 7781.5,
             "stop": None, "metadata": {"stop_initial": 7721.5}}
        _, t2, _ = seed(s)
        assert t2 == pytest.approx(7768.0)

    def test_top_level_stop_still_wins(self):
        s = {"direction": "LONG", "t1": 7604.0, "t2": None, "t3": None,
             "stop": 7596.0, "metadata": {"stop_initial": 7590.0}}
        _, t2, _ = seed(s)
        assert t2 == pytest.approx(7604.0 + 8.0)   # uses stop, not stop_initial

    def test_no_stop_anywhere_leaves_t2_absent(self):
        """Rule 1: better an honest missing t2 than a fabricated t2==t1."""
        s = {"direction": "SHORT", "t1": 7793.75, "t2": None, "t3": None,
             "stop": None, "metadata": {}}
        t1, t2, t3 = seed(s)
        assert t2 == 0.0 and t1 == 7793.75

    def test_t3_seeded_one_step_beyond_t2(self):
        s = {"direction": "LONG", "t1": 7600.0, "t2": 7606.0, "t3": None,
             "stop": 7595.0, "metadata": {}}
        _, _, t3 = seed(s)
        assert t3 == pytest.approx(2 * 7606.0 - 7600.0)

    def test_complete_ladder_untouched(self):
        s = {"direction": "LONG", "t1": 7600.0, "t2": 7606.0, "t3": 7612.0,
             "stop": 7595.0, "metadata": {}}
        assert seed(s) == (7600.0, 7606.0, 7612.0)


class TestDegeneracyGuard:
    def test_t2_equal_t1_is_dropped(self):
        t1, t2, t3 = guard(7793.75, 7793.75, 7787.0)
        assert (t1, t2, t3) == (7793.75, 0.0, 7787.0)

    def test_t3_duplicating_t2_is_dropped(self):
        t1, t2, t3 = guard(7600.0, 7606.0, 7606.0)
        assert (t1, t2, t3) == (7600.0, 7606.0, 0.0)

    def test_t3_duplicating_t1_is_dropped(self):
        t1, t2, t3 = guard(7600.0, 7606.0, 7600.0)
        assert t3 == 0.0

    def test_clean_ladder_passes_through(self):
        assert guard(7600.0, 7606.0, 7612.0) == (7600.0, 7606.0, 7612.0)

    def test_absent_levels_are_not_flagged(self):
        assert guard(7600.0, 0.0, 0.0) == (7600.0, 0.0, 0.0)
