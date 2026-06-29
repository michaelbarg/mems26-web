"""Stage 1: DAYTYPE_PATTERN_AWARE_V1 — pattern-family gate (CONT vs REV by day-type).

Anti-tautological: calls the REAL daytype_position_gate.decide.
Each test states its revert-RED litmus.

Handoff: docs/handoff/CC_STAGE1_PATTERN_AWARE_GATE_2026-06-29.md
Contract: docs/handoff/CC_HANDOFF_CONTRACT.md
"""
import os
import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def enable_gates():
    with patch.dict(os.environ, {
        "DAYTYPE_POSITION_GATE": "1",
        "DAYTYPE_PATTERN_AWARE_V1": "1",
    }):
        yield


TPO = {
    "ib_high": 7450.0,
    "ib_low": 7400.0,
    "poc": 7407.0,
    "vah": 7440.0,
    "val": 7415.0,
    "session_high": 7480.0,  # above IBH → uptrend if needed
    "session_low": 7395.0,   # below IBL → downtrend if needed
}


# ---------------------------------------------------------------------------
# Test 1: Normal + INITIATIVE_SHORT (CONT) → BLOCK
# if reverted → RED because removing the family gate lets CONT fire on balanced day
# ---------------------------------------------------------------------------
class TestNormalBlocksCont:
    def test_initiative_short_on_normal_blocked(self):
        """The 06-29 bug: INITIATIVE_SHORT on a Normal day → must be blocked."""
        from backend.v9.systems.daytype_position_gate import decide
        allow, reason = decide(
            pattern="INITIATIVE_SHORT", direction="SHORT", day_type="Normal",
            entry_price=7435.0, tpo_ctx=TPO,
        )
        assert allow is False
        assert "continuation" in reason.lower()

    def test_initiative_long_on_normal_blocked(self):
        from backend.v9.systems.daytype_position_gate import decide
        allow, reason = decide(
            pattern="INITIATIVE_LONG", direction="LONG", day_type="Normal",
            entry_price=7390.0, tpo_ctx=TPO,
        )
        assert allow is False
        assert "continuation" in reason.lower()

    def test_zlr_cont_on_neutral_blocked(self):
        """Neutral_Center is balanced → ZLR (CONT) blocked too."""
        from backend.v9.systems.daytype_position_gate import decide
        allow, reason = decide(
            pattern="ZLR", direction="LONG", day_type="Neutral_Center",
            entry_price=7390.0, tpo_ctx=TPO,
        )
        assert allow is False
        assert "continuation" in reason.lower()


# ---------------------------------------------------------------------------
# Test 2: Normal + REACTIVE_SHORT (REV) above POC → ALLOW (existing location logic)
# if reverted → RED because removing the family gate or blocking REV on Normal is wrong
# ---------------------------------------------------------------------------
class TestNormalAllowsRev:
    def test_reactive_short_at_vah_allowed(self):
        from backend.v9.systems.daytype_position_gate import decide
        allow, reason = decide(
            pattern="REACTIVE_SHORT", direction="SHORT", day_type="Normal",
            entry_price=7441.0, tpo_ctx=TPO,  # at VAH 7440 (within edge)
        )
        assert allow is True

    def test_reactive_long_below_poc_allowed(self):
        from backend.v9.systems.daytype_position_gate import decide
        allow, reason = decide(
            pattern="REACTIVE_LONG", direction="LONG", day_type="Normal",
            entry_price=7390.0, tpo_ctx=TPO,  # below POC 7407
        )
        assert allow is True

    def test_ghost_rev_on_normal_falls_through_to_location(self):
        """GHOST (REV) on Normal: family allows REV, then VA-edge gate applies."""
        from backend.v9.systems.daytype_position_gate import decide
        # GHOST SHORT at VAH → allowed (both family and VA-edge agree)
        allow, _ = decide(
            pattern="GHOST", direction="SHORT", day_type="Normal",
            entry_price=7441.0, tpo_ctx=TPO,  # at VAH 7440
        )
        assert allow is True
        # GHOST LONG far above VAL → blocked by VA-edge (not at lower edge)
        allow, reason = decide(
            pattern="GHOST", direction="LONG", day_type="Normal",
            entry_price=7435.0, tpo_ctx=TPO,  # 7435 > VAL 7415 + 2
        )
        assert allow is False
        assert "not at lower edge" in reason  # VA-edge gate, not POC


# ---------------------------------------------------------------------------
# Test 3: Trend_Normal + INITIATIVE (CONT) with-trend → ALLOW
# if reverted → RED because removing the family gate blocks CONT on trend (wrong)
# ---------------------------------------------------------------------------
class TestTrendAllowsCont:
    def test_initiative_long_on_trend_up_allowed(self):
        from backend.v9.systems.daytype_position_gate import decide
        tpo_up = {**TPO, "session_high": 7480.0, "session_low": 7405.0}  # only IBH broken
        allow, _ = decide(
            pattern="INITIATIVE_LONG", direction="LONG", day_type="Trend_Normal",
            entry_price=7470.0, tpo_ctx=tpo_up,
        )
        assert allow is True

    def test_zlr_long_on_trend_up_allowed(self):
        from backend.v9.systems.daytype_position_gate import decide
        tpo_up = {**TPO, "session_high": 7480.0, "session_low": 7405.0}
        allow, _ = decide(
            pattern="ZLR", direction="LONG", day_type="Trend_Normal",
            entry_price=7470.0, tpo_ctx=tpo_up,
        )
        assert allow is True


# ---------------------------------------------------------------------------
# Test 4: Trend_Normal + REACTIVE (REV) → BLOCK
# if reverted → RED because removing the family gate lets REV fire on trend day
# ---------------------------------------------------------------------------
class TestTrendBlocksRev:
    def test_reactive_long_on_trend_blocked(self):
        from backend.v9.systems.daytype_position_gate import decide
        allow, reason = decide(
            pattern="REACTIVE_LONG", direction="LONG", day_type="Trend_Normal",
            entry_price=7390.0, tpo_ctx=TPO,
        )
        assert allow is False
        assert "reversal" in reason.lower()

    def test_ghost_on_trend_dd_blocked(self):
        from backend.v9.systems.daytype_position_gate import decide
        allow, reason = decide(
            pattern="GHOST", direction="SHORT", day_type="Trend_DD",
            entry_price=7380.0, tpo_ctx=TPO,
        )
        assert allow is False
        assert "reversal" in reason.lower()


# ---------------------------------------------------------------------------
# Test 5: Nontrend + anything → BLOCK (existing, unchanged)
# if reverted → RED because Nontrend blocking is existing behavior
# ---------------------------------------------------------------------------
class TestNontrendBlocksAll:
    def test_cont_on_nontrend_blocked(self):
        from backend.v9.systems.daytype_position_gate import decide
        with patch.dict(os.environ, {"NONTREND_DISABLE_ALL": "1"}):
            allow, reason = decide(
                pattern="INITIATIVE_SHORT", direction="SHORT", day_type="Nontrend",
                entry_price=7435.0, tpo_ctx=TPO,
            )
            assert allow is False

    def test_rev_on_nontrend_blocked(self):
        from backend.v9.systems.daytype_position_gate import decide
        with patch.dict(os.environ, {"NONTREND_DISABLE_ALL": "1"}):
            allow, reason = decide(
                pattern="REACTIVE_LONG", direction="LONG", day_type="Nontrend",
                entry_price=7390.0, tpo_ctx=TPO,
            )
            assert allow is False


# ---------------------------------------------------------------------------
# Test 6: Regression (today): Normal + INITIATIVE_SHORT @7435, POC 7407 → BLOCK
# if reverted → RED because this is the exact 06-29 scenario
# ---------------------------------------------------------------------------
class TestRegression0629:
    def test_today_initiative_short_on_normal_blocked(self):
        """Exact 06-29 scenario: Normal day, INITIATIVE_SHORT, entry=7435, POC=7407.
        Gate currently ALLOWS (pattern ignored). With flag → BLOCK (CONT on balanced)."""
        from backend.v9.systems.daytype_position_gate import decide
        allow, reason = decide(
            pattern="INITIATIVE_SHORT", direction="SHORT", day_type="Normal",
            entry_price=7435.0,
            tpo_ctx={"poc": 7407.0, "ib_high": 7450.0, "ib_low": 7400.0},
        )
        assert allow is False
        assert "continuation" in reason.lower()
        assert "INITIATIVE_SHORT" in reason


# ---------------------------------------------------------------------------
# Test 7: Flag OFF → identical to current behavior (pattern ignored)
# if reverted → RED because flag-off tests document the backward-compat contract
# ---------------------------------------------------------------------------
class TestFlagOffIdentical:
    def test_initiative_short_on_normal_allowed_when_flag_off(self):
        """Flag OFF: INITIATIVE_SHORT on Normal passes (pattern ignored, location only)."""
        from backend.v9.systems.daytype_position_gate import decide
        with patch.dict(os.environ, {"DAYTYPE_PATTERN_AWARE_V1": "0"}):
            allow, reason = decide(
                pattern="INITIATIVE_SHORT", direction="SHORT", day_type="Normal",
                entry_price=7435.0, tpo_ctx=TPO,  # above POC → location allows SHORT
            )
            assert allow is True

    def test_reactive_on_trend_allowed_when_flag_off(self):
        """Flag OFF: REACTIVE on Trend passes (pattern ignored, location only)."""
        from backend.v9.systems.daytype_position_gate import decide
        tpo_up = {**TPO, "session_high": 7480.0, "session_low": 7405.0}
        with patch.dict(os.environ, {"DAYTYPE_PATTERN_AWARE_V1": "0"}):
            allow, _ = decide(
                pattern="REACTIVE_LONG", direction="LONG", day_type="Trend_Normal",
                entry_price=7470.0, tpo_ctx=tpo_up,
            )
            # Flag off → no family gate → falls to location → LONG with upward trend
            assert allow is True


# ---------------------------------------------------------------------------
# Test 8: Variation blocks REV, allows CONT
# if reverted → RED because Variation should only allow continuation
# ---------------------------------------------------------------------------
class TestVariationContOnly:
    def test_initiative_on_variation_allowed(self):
        from backend.v9.systems.daytype_position_gate import decide
        allow, _ = decide(
            pattern="INITIATIVE_LONG", direction="LONG", day_type="Variation",
            entry_price=7460.0, tpo_ctx=TPO,  # above IBH → expansion up
        )
        assert allow is True

    def test_reactive_on_variation_blocked(self):
        from backend.v9.systems.daytype_position_gate import decide
        allow, reason = decide(
            pattern="REACTIVE_LONG", direction="LONG", day_type="Variation",
            entry_price=7460.0, tpo_ctx=TPO,
        )
        assert allow is False
        assert "reversal" in reason.lower()
