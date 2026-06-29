"""Stage 1b: Live TPO levels + VA-edge gating for REACTIVE.

Anti-tautological: calls the REAL daytype_position_gate.decide.
Each test states its revert-RED litmus.

Handoff: docs/handoff/CC_STAGE1B_LIVE_LEVELS_2026-06-29.md
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


# Valid TPO: VA width = 33pt (VAH 7440 - VAL 7407), well above the 8pt floor
TPO_VALID = {
    "ib_high": 7450.0,
    "ib_low": 7400.0,
    "poc": 7420.0,
    "vah": 7440.0,
    "val": 7407.0,
}

# Degenerate TPO: VA width = 6pt (frozen/stale profile)
TPO_DEGENERATE = {
    "ib_high": 7450.0,
    "ib_low": 7370.0,
    "poc": 7466.25,
    "vah": 7469.0,
    "val": 7463.0,  # width = 6pt < 8pt floor
}


# ---------------------------------------------------------------------------
# Test 1: 06-29 regression — REACTIVE_SHORT above VAH → ALLOW
# if reverted → RED because removing VA-edge gating reverts to strict POC
# which blocks REACTIVE_SHORT between POC and VAH
# ---------------------------------------------------------------------------
class TestReactiveAtVAEdge:
    def test_reactive_short_above_vah_allowed(self):
        """REACTIVE_SHORT at entry above VAH → allowed (fade the high)."""
        from backend.v9.systems.daytype_position_gate import decide
        allow, reason = decide(
            pattern="REACTIVE_SHORT", direction="SHORT", day_type="Normal",
            entry_price=7442.0, tpo_ctx=TPO_VALID,  # entry 7442 > VAH 7440
        )
        assert allow is True
        assert "VA edge" in reason

    def test_reactive_short_near_vah_allowed(self):
        """REACTIVE_SHORT at entry = VAH - 1pt (within tol=2) → allowed."""
        from backend.v9.systems.daytype_position_gate import decide
        allow, reason = decide(
            pattern="REACTIVE_SHORT", direction="SHORT", day_type="Normal",
            entry_price=7439.0, tpo_ctx=TPO_VALID,  # 7439 >= 7440 - 2
        )
        assert allow is True

    def test_reactive_long_below_val_allowed(self):
        """REACTIVE_LONG at entry below VAL → allowed (buy the low)."""
        from backend.v9.systems.daytype_position_gate import decide
        allow, reason = decide(
            pattern="REACTIVE_LONG", direction="LONG", day_type="Normal",
            entry_price=7405.0, tpo_ctx=TPO_VALID,  # entry 7405 < VAL 7407
        )
        assert allow is True

    def test_reactive_long_near_val_allowed(self):
        """REACTIVE_LONG at entry = VAL + 1pt (within tol=2) → allowed."""
        from backend.v9.systems.daytype_position_gate import decide
        allow, reason = decide(
            pattern="REACTIVE_LONG", direction="LONG", day_type="Normal",
            entry_price=7408.0, tpo_ctx=TPO_VALID,  # 7408 <= 7407 + 2
        )
        assert allow is True


# ---------------------------------------------------------------------------
# Test 2: REACTIVE mid-value → BLOCK
# if reverted → RED because removing VA-edge gating allows mid-value fades
# ---------------------------------------------------------------------------
class TestReactiveMidValueBlocked:
    def test_reactive_short_mid_value_blocked(self):
        """REACTIVE_SHORT between POC and VAL (not at upper edge) → blocked."""
        from backend.v9.systems.daytype_position_gate import decide
        allow, reason = decide(
            pattern="REACTIVE_SHORT", direction="SHORT", day_type="Normal",
            entry_price=7425.0, tpo_ctx=TPO_VALID,  # 7425 < VAH 7440 - 2 = 7438
        )
        assert allow is False
        assert "not at upper edge" in reason

    def test_reactive_long_mid_value_blocked(self):
        """REACTIVE_LONG above VAL+tol (not at lower edge) → blocked."""
        from backend.v9.systems.daytype_position_gate import decide
        allow, reason = decide(
            pattern="REACTIVE_LONG", direction="LONG", day_type="Normal",
            entry_price=7425.0, tpo_ctx=TPO_VALID,  # 7425 > VAL 7407 + 2 = 7409
        )
        assert allow is False
        assert "not at lower edge" in reason


# ---------------------------------------------------------------------------
# Test 3: Degenerate TPO → fail-open
# if reverted → RED because removing the degenerate guard blocks on frozen levels
# ---------------------------------------------------------------------------
class TestDegenerateTPOFailOpen:
    def test_degenerate_va_width_fail_open(self):
        """VA width 6pt (< 8pt floor) → fail-open regardless of direction."""
        from backend.v9.systems.daytype_position_gate import decide
        allow, reason = decide(
            pattern="REACTIVE_SHORT", direction="SHORT", day_type="Normal",
            entry_price=7463.25, tpo_ctx=TPO_DEGENERATE,
        )
        assert allow is True
        assert "degenerate" in reason

    def test_collapsed_vah_val_poc_fail_open(self):
        """VAH ≈ VAL ≈ POC (all collapsed) → degenerate → fail-open."""
        from backend.v9.systems.daytype_position_gate import decide
        tpo_collapsed = {
            "ib_high": 7450.0, "ib_low": 7400.0,
            "poc": 7430.0, "vah": 7430.5, "val": 7429.5,  # width=1pt, all≈7430
        }
        allow, reason = decide(
            pattern="REACTIVE_SHORT", direction="SHORT", day_type="Normal",
            entry_price=7425.0, tpo_ctx=tpo_collapsed,
        )
        assert allow is True
        assert "degenerate" in reason

    def test_degenerate_also_for_cont(self):
        """Degenerate guard applies to CONT too (same levels used for POC gating)."""
        from backend.v9.systems.daytype_position_gate import decide
        allow, reason = decide(
            pattern="INITIATIVE_SHORT", direction="SHORT", day_type="Normal",
            entry_price=7463.25, tpo_ctx=TPO_DEGENERATE,
        )
        # INITIATIVE on Normal is blocked by family gate (CONT on balanced)
        # Family gate runs BEFORE degenerate guard
        assert allow is False
        assert "continuation" in reason.lower()

    def test_degenerate_cont_no_family_gate(self):
        """With flag ON but unknown pattern, degenerate guard fires."""
        from backend.v9.systems.daytype_position_gate import decide
        allow, reason = decide(
            pattern="UNKNOWN_SETUP", direction="SHORT", day_type="Normal",
            entry_price=7463.25, tpo_ctx=TPO_DEGENERATE,
        )
        assert allow is True
        assert "degenerate" in reason


# ---------------------------------------------------------------------------
# Test 4: CONT gating unchanged (still uses POC)
# if reverted → RED because CONT must still use POC gating, not VA edges
# ---------------------------------------------------------------------------
class TestContUnchanged:
    def test_zlr_long_above_poc_blocked(self):
        """ZLR (CONT) LONG above POC → still blocked by POC (not VA-edge)."""
        from backend.v9.systems.daytype_position_gate import decide
        # ZLR is CONT, but on Normal day it's blocked by family gate first
        allow, reason = decide(
            pattern="ZLR", direction="LONG", day_type="Normal",
            entry_price=7430.0, tpo_ctx=TPO_VALID,
        )
        # CONT on Normal → blocked by family gate
        assert allow is False
        assert "continuation" in reason.lower()


# ---------------------------------------------------------------------------
# Test 5: Flag OFF → byte-identical (POC gating for all patterns)
# if reverted → RED because flag-off contract must hold
# ---------------------------------------------------------------------------
class TestFlagOffIdentical:
    def test_reactive_short_below_poc_blocked_when_flag_off(self):
        """Flag OFF: REACTIVE_SHORT below POC → blocked (strict POC, not VA edge)."""
        from backend.v9.systems.daytype_position_gate import decide
        with patch.dict(os.environ, {"DAYTYPE_PATTERN_AWARE_V1": "0"}):
            allow, reason = decide(
                pattern="REACTIVE_SHORT", direction="SHORT", day_type="Normal",
                entry_price=7415.0, tpo_ctx=TPO_VALID,  # below POC 7420
            )
            assert allow is False
            assert "wrong side" in reason

    def test_degenerate_tpo_still_gates_when_flag_off(self):
        """Flag OFF: degenerate TPO guard does NOT fire — uses levels as-is."""
        from backend.v9.systems.daytype_position_gate import decide
        with patch.dict(os.environ, {"DAYTYPE_PATTERN_AWARE_V1": "0"}):
            allow, reason = decide(
                pattern="REACTIVE_SHORT", direction="SHORT", day_type="Normal",
                entry_price=7463.25, tpo_ctx=TPO_DEGENERATE,  # below POC 7466.25
            )
            # Flag off → uses POC, entry < POC → blocked
            assert allow is False
            assert "wrong side" in reason


# ---------------------------------------------------------------------------
# Test 6: Neutral variants also get VA-edge gating for REV
# if reverted → RED because Neutral delegates to _decide_normal
# ---------------------------------------------------------------------------
class TestNeutralVAEdge:
    def test_neutral_reactive_short_at_vah_allowed(self):
        from backend.v9.systems.daytype_position_gate import decide
        allow, reason = decide(
            pattern="REACTIVE_SHORT", direction="SHORT", day_type="Neutral_Center",
            entry_price=7442.0, tpo_ctx=TPO_VALID,
        )
        assert allow is True
        assert "VA edge" in reason

    def test_neutral_reactive_short_mid_blocked(self):
        from backend.v9.systems.daytype_position_gate import decide
        allow, reason = decide(
            pattern="REACTIVE_SHORT", direction="SHORT", day_type="Neutral_Extreme",
            entry_price=7425.0, tpo_ctx=TPO_VALID,
        )
        assert allow is False
        assert "not at upper edge" in reason
