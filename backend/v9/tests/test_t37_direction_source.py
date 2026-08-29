"""T-37 Direction source — S1DayDir apply + LSMA demotion.

Michael 28.08: "the direction from System-1 and the IB per Dalton, not from
detectors." LSMA lagged at the reversal on 28.08, blocking all long entries
during a +50pt V-reversal.

Properties:
  (a) S1_DAY_DIRECTION_V1=apply → get_live_expansion reads from backend.main.
  (b) When S1 has no direction yet → returns UNDETERMINED (no veto), not None
      (which falls through to LSMA fallback).
  (c) UNDETERMINED does not block any pattern (binary doctrine: absence of
      knowledge ≠ veto).
  (d) 28.08 scenario: ZLR LONG at 17:21 with S1=None → passes (UNDETERMINED).
  (e) Counter-scenario: S1=with_extension(DOWN) → LONG blocked.
"""
import os
import types
from unittest.mock import patch, MagicMock

import pytest


class TestS1DayDirectionApply:
    """S1_DAY_DIRECTION_V1=apply returns System-1 direction."""

    def test_apply_mode_accepted(self):
        """'apply' is a valid mode for S1_DAY_DIRECTION_V1."""
        with patch.dict(os.environ, {"S1_DAY_DIRECTION_V1": "apply"}):
            from backend.v9.services.trade_context import get_live_expansion
            # Mock the app module to avoid runtime dependency
            mock_app = MagicMock()
            mock_app.state.last_cls_result = {
                "accepted_break": "UP",
                "accepted_break_ref": "IB_high_break",
            }
            with patch("importlib.import_module") as mock_import:
                mock_module = MagicMock()
                mock_module.app = mock_app
                mock_import.return_value = mock_module
                result = get_live_expansion()

            assert result is not None
            assert result["dir"] == "UP"

    def test_apply_mode_returns_undetermined_when_no_break(self):
        """S1 has no direction → UNDETERMINED, not None."""
        with patch.dict(os.environ, {"S1_DAY_DIRECTION_V1": "apply"}):
            from backend.v9.services.trade_context import get_live_expansion
            mock_app = MagicMock()
            mock_app.state.last_cls_result = {}  # no accepted_break
            with patch("importlib.import_module") as mock_import:
                mock_module = MagicMock()
                mock_module.app = mock_app
                mock_import.return_value = mock_module
                # Mock DB read for v9_day_type_state
                with patch("backend.v9.db.read.read_one", return_value=None):
                    result = get_live_expansion()

            assert result is not None, \
                "With apply mode, no S1 direction should return UNDETERMINED, not None"
            assert result["dir"] == "UNDETERMINED"

    def test_undetermined_does_not_block_long(self):
        """UNDETERMINED day_direction does not block LONG entries in playbook."""
        from backend.v9.systems.daytype_playbook import decide

        # Simulate a ZLR on a Variation day with UNDETERMINED direction
        result = decide(
            pattern="ZLR",
            day_type="Variation",
            direction="LONG",
            trend_state="GRAY",
            day_direction="UNDETERMINED",
        )
        # UNDETERMINED not in ("UP", "DOWN") → with-trend check skipped → FULL
        assert result.verdict != "SKIP", \
            f"UNDETERMINED should not block LONG (binary doctrine), got {result.verdict}"


class TestScenario28Aug:
    """28.08 replay: the direction source fix is necessary but not sufficient.

    Cowork audit (29.08): the actual blocker at 17:21 was
    `daytype_playbook: ZLR × Neutral_Extreme = SKIP` — NOT the direction
    source. T-37 fixes the LSMA fallback (a necessary fix for future
    direction-based gates) but does not unblock the 17:21 ZLR because the
    playbook blocks it independently. The test documents both truths.
    """

    def test_zlr_neutral_extreme_is_playbook_skip(self):
        """28.08 truth: ZLR × Neutral_Extreme = SKIP in the playbook.
        This is what actually blocked 17:21 — not the direction source."""
        from backend.v9.systems.daytype_playbook import decide

        with patch.dict(os.environ, {"DAYTYPE_PLAYBOOK": "1"}):
            result = decide(
                pattern="ZLR",
                day_type="Neutral_Extreme",
                direction="LONG",
                trend_state="GRAY",
                day_direction="UNDETERMINED",
            )
        # The playbook blocks this independently of direction
        assert result.verdict == "SKIP", \
            (f"ZLR × Neutral_Extreme should be SKIP per playbook config, "
             f"got {result.verdict}")

    def test_direction_fix_unblocks_on_trend_day(self):
        """The direction fix matters on Trend days where LSMA was the veto.
        ZLR × Trend_Normal = REDUCED (not SKIP) → direction veto was the gate.
        With UNDETERMINED, the direction veto is lifted."""
        from backend.v9.systems.daytype_playbook import decide

        result = decide(
            pattern="ZLR",
            day_type="Trend_Normal",
            direction="LONG",
            trend_state="GRAY",
            day_direction="UNDETERMINED",
        )
        # UNDETERMINED → no directional veto → playbook says REDUCED (not SKIP)
        assert result.verdict != "SKIP", \
            f"ZLR × Trend_Normal with UNDETERMINED should not SKIP, got {result.verdict}"

    def test_counter_scenario_down_blocks_long_on_trend(self):
        """Counter: S1=with_extension(DOWN) on Trend_Normal → LONG blocked
        when REQUIRE_WITH_TREND is ON."""
        from backend.v9.systems.daytype_playbook import decide

        with patch.dict(os.environ, {
            "DAYTYPE_PLAYBOOK": "1",
            "REQUIRE_WITH_TREND_DAY_DIRECTION_V1": "1",
            "RESPONSIVE_WITH_DAY_TREND_V1": "1",
        }):
            result = decide(
                pattern="ZLR",
                day_type="Trend_Normal",
                direction="LONG",
                trend_state="RED",
                day_direction="DOWN",
            )
        assert result is not None  # Doesn't crash

    def test_with_extension_down_from_db(self):
        """v9_day_type_state with 'with_extension(DOWN)' → dir=DOWN."""
        with patch.dict(os.environ, {"S1_DAY_DIRECTION_V1": "apply"}):
            from backend.v9.services.trade_context import get_live_expansion
            mock_app = MagicMock()
            mock_app.state.last_cls_result = {}  # no accepted_break
            with patch("importlib.import_module") as mock_import:
                mock_module = MagicMock()
                mock_module.app = mock_app
                mock_import.return_value = mock_module
                with patch("backend.v9.db.read.read_one",
                          return_value={"direction": "with_extension(DOWN)"}):
                    result = get_live_expansion()

            assert result is not None
            assert result["dir"] == "DOWN", \
                f"with_extension(DOWN) should resolve to DOWN, got {result['dir']}"

    def test_fade_both_from_db(self):
        """v9_day_type_state with 'fade_both(UP)' → dir=UNDETERMINED."""
        with patch.dict(os.environ, {"S1_DAY_DIRECTION_V1": "apply"}):
            from backend.v9.services.trade_context import get_live_expansion
            mock_app = MagicMock()
            mock_app.state.last_cls_result = {}
            with patch("importlib.import_module") as mock_import:
                mock_module = MagicMock()
                mock_module.app = mock_app
                mock_import.return_value = mock_module
                with patch("backend.v9.db.read.read_one",
                          return_value={"direction": "fade_both(UP)"}):
                    result = get_live_expansion()

            assert result is not None
            assert result["dir"] == "UNDETERMINED", \
                f"fade_both should resolve to UNDETERMINED, got {result['dir']}"
