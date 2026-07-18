"""Stage 0: OPENING_FIRE_CVD_V1 — CVD-confirm OPEN_DRIVE + pre-lock no-fallback.

Anti-tautological: calls the REAL detect_opening_type and opening_type_gate.decide.
Each test states its revert-RED litmus.

Handoff: docs/handoff/CC_STAGE0_OPENING_FIRE_CVD_2026-06-29.md
Contract: docs/handoff/CC_HANDOFF_CONTRACT.md
"""
import os
import pytest
from unittest.mock import patch

from backend.v9.systems.day_type.opening_detector_v2 import detect_opening_type


def B(o, h, l, c):
    return {"o": o, "h": h, "l": l, "c": c}


FAR = dict(prior_vah=110, prior_val=90, pdh=112, pdl=88)

# OPEN_DRIVE DOWN geometry: open near session high, relentless sell
DRIVE_DN_BARS = [
    B(100, 100.0, 99.4, 99.5), B(99.5, 99.6, 98.9, 99.0),
    B(99.0, 99.1, 97.9, 98.0), B(98.0, 98.1, 96.9, 97.0),
]


# ---------------------------------------------------------------------------
# Test 1: Clean drive fires — OPEN_DRIVE-down + CVD aligned (sell-dominant)
# if reverted → RED because removing cvd_confirm_drive breaks the param contract
# ---------------------------------------------------------------------------
class TestCleanDriveFiresWithAlignedCVD:
    def test_drive_dn_cvd_aligned(self):
        """cvd_pos=0.2 (sell-dominant) + drive-down geometry → OPEN_DRIVE DOWN."""
        r = detect_opening_type(
            DRIVE_DN_BARS, 100.0, cvd_pos=0.2, cvd_confirm_drive=True, **FAR,
        )
        assert r["opening_type"] == "OPEN_DRIVE", f"expected OPEN_DRIVE, got {r}"
        assert r["direction"] == "DOWN"

    def test_drive_up_cvd_aligned(self):
        """cvd_pos=0.8 (buy-dominant) + drive-up geometry → OPEN_DRIVE UP."""
        up_bars = [
            B(100, 100.6, 100.0, 100.5), B(100.5, 101.1, 100.4, 101.0),
            B(101.0, 102.1, 100.9, 102.0), B(102.0, 103.2, 101.9, 103.0),
        ]
        r = detect_opening_type(
            up_bars, 100.0, cvd_pos=0.8, cvd_confirm_drive=True, **FAR,
        )
        assert r["opening_type"] == "OPEN_DRIVE", f"expected OPEN_DRIVE, got {r}"
        assert r["direction"] == "UP"


# ---------------------------------------------------------------------------
# Test 2: Absorbed drive blocked — same geometry + CVD divergence
# if reverted → RED because without the CVD gate, OPEN_DRIVE fires on divergent CVD
# ---------------------------------------------------------------------------
class TestAbsorbedDriveBlocked:
    def test_drive_dn_cvd_diverges(self):
        """cvd_pos=0.8 (buying) + drive-down geometry → NOT OPEN_DRIVE (absorption)."""
        r = detect_opening_type(
            DRIVE_DN_BARS, 100.0, cvd_pos=0.8, cvd_confirm_drive=True, **FAR,
        )
        assert r["opening_type"] != "OPEN_DRIVE", (
            f"CVD divergence should block OPEN_DRIVE, got {r}"
        )
        # Should have a CVD divergence reason
        assert any("CVD divergence" in reason for reason in r.get("reasons", [])), r

    def test_drive_up_cvd_diverges(self):
        """cvd_pos=0.2 (selling) + drive-up geometry → NOT OPEN_DRIVE."""
        up_bars = [
            B(100, 100.6, 100.0, 100.5), B(100.5, 101.1, 100.4, 101.0),
            B(101.0, 102.1, 100.9, 102.0), B(102.0, 103.2, 101.9, 103.0),
        ]
        r = detect_opening_type(
            up_bars, 100.0, cvd_pos=0.2, cvd_confirm_drive=True, **FAR,
        )
        assert r["opening_type"] != "OPEN_DRIVE", (
            f"CVD divergence should block OPEN_DRIVE, got {r}"
        )

    def test_gate_blocks_with_drive_short_on_absorbed_drive(self):
        """Full gate: drive-down geometry + CVD buying → gate does NOT allow with-drive SHORT.

        if reverted → RED because without CVD gate, decide() allows SHORT on absorbed drive.
        """
        # Bars with 6 entries for drive detection
        dn_bars_6 = [
            B(100, 100.0, 99.4, 99.5), B(99.5, 99.6, 98.9, 99.0),
            B(99.0, 99.1, 97.9, 98.0), B(98.0, 98.1, 96.9, 97.0),
            B(97.0, 97.1, 96.0, 96.2), B(96.2, 96.3, 95.0, 95.2),
        ]
        with patch.dict(os.environ, {
            "OPENING_TYPE_GATE": "1",
            "OPENING_FIRE_CVD_V1": "1",
        }):
            # Mock CVD read to return buy-dominant (divergent from the drive-down)
            with patch(
                "backend.v9.systems.opening_type_gate._compute_opening_cvd_pos",
                return_value=0.8,
            ):
                from backend.v9.systems.opening_type_gate import decide
                allow, reason = decide(
                    direction="SHORT", rth_bars=dn_bars_6, ib_locked=False,
                )
                # Drive-down geometry BUT CVD buying = absorbed drive
                # The detector should NOT emit OPEN_DRIVE → gate should NOT
                # allow "with-drive SHORT"
                assert "with-drive" not in reason.lower() or allow is False, (
                    f"Absorbed drive should not produce with-drive SHORT: {reason}"
                )


# ---------------------------------------------------------------------------
# Test 3: Pre-lock no-fallback — FORMING + old engine "Variation" → no INITIATIVE
# if reverted → RED because removing the FORMING guard lets the old engine's
# premature "Variation" drive pattern selection to INITIATIVE
# ---------------------------------------------------------------------------
class TestPreLockNoFallback:
    def test_forming_nullifies_day_type(self):
        """When classifier is FORMING and flag ON, day_type_at_entry = None (not old engine's value)."""
        import time
        from backend.v9.services.trade_context import extract_g1_entry_context, _NC_CACHE

        # Seed the cache with FORMING (simulates pre-IB-lock classifier state)
        today_iso = __import__("datetime").datetime.now(
            __import__("zoneinfo").ZoneInfo("America/New_York")
        ).date().isoformat()
        _NC_CACHE.update({"date": today_iso, "ts": time.time(), "day_type": "FORMING"})

        # Build a cross_context with old engine reporting "Variation"
        cross_ctx = {
            "systems": {
                "day_type_machine": {"day_type": "Variation"},
            }
        }

        with patch.dict(os.environ, {
            "S1_NEW_CLASSIFIER": "1",
            "OPENING_FIRE_CVD_V1": "1",
        }):
            # Mock _g1_replay_fallback_ok → True so the cache path is reachable
            # (during session hours the 07-16 root-fix blocks it — correct, but
            # irrelevant to what this test validates: FORMING nullification).
            with patch("backend.v9.services.trade_context._g1_replay_fallback_ok", return_value=True):
                result = extract_g1_entry_context(cross_ctx)
            # With flag ON + FORMING, day_type should be None (not "Variation")
            assert result["day_type_at_entry"] is None, (
                f"Pre-lock FORMING should nullify day_type, got {result['day_type_at_entry']}"
            )

    def test_forming_keeps_old_engine_when_flag_off(self):
        """Flag OFF + FORMING → old engine's day_type preserved (backward compat)."""
        import time
        from backend.v9.services.trade_context import extract_g1_entry_context, _NC_CACHE

        today_iso = __import__("datetime").datetime.now(
            __import__("zoneinfo").ZoneInfo("America/New_York")
        ).date().isoformat()
        _NC_CACHE.update({"date": today_iso, "ts": time.time(), "day_type": "FORMING"})

        cross_ctx = {
            "systems": {
                "day_type_machine": {"day_type": "Variation"},
            }
        }

        with patch.dict(os.environ, {
            "S1_NEW_CLASSIFIER": "1",
            "OPENING_FIRE_CVD_V1": "0",
        }):
            result = extract_g1_entry_context(cross_ctx)
            # Flag OFF → old engine's "Variation" preserved
            assert result["day_type_at_entry"] == "Variation", (
                f"Flag OFF should keep old engine value, got {result['day_type_at_entry']}"
            )


# ---------------------------------------------------------------------------
# Test 4 (partial): Regression — today's 06-29 absorbed drive bars
# if reverted → RED because without the CVD gate, OPEN_DRIVE fires on absorption
# Note: full replay requires DB + bridge data; this tests the detector logic
# with realistic geometry approximating the 17:10 low + CVD absorption.
# ---------------------------------------------------------------------------
class TestRegression0629:
    def test_absorbed_drive_dn_with_buying_cvd(self):
        """Approximate 06-29 17:10–17:25: drive-down geometry + CVD absorption (+3403 delta).

        cvd_pos > 0.5 (buying into the low) → drive not confirmed.
        """
        # Approximated bars: market dropped from open ~7549, drove down to ~7535
        # but CVD was buying heavily at the low (absorption)
        bars = [
            B(7549, 7549.5, 7545.0, 7546.0),  # bar 1: sell-off from open
            B(7546.0, 7546.5, 7540.0, 7541.0),  # bar 2: continued selling
            B(7541.0, 7542.0, 7535.0, 7536.0),  # bar 3: low of day, absorption
            B(7536.0, 7540.0, 7535.5, 7539.0),  # bar 4: some recovery
        ]
        r = detect_opening_type(
            bars, 7549.0,
            cvd_pos=0.72,  # buy-dominant despite price drop = absorption
            cvd_confirm_drive=True,
            **FAR,
        )
        assert r["opening_type"] != "OPEN_DRIVE", (
            f"06-29 absorbed drive should NOT be OPEN_DRIVE: {r}"
        )


# ---------------------------------------------------------------------------
# Test 5: Flag OFF → behavior unchanged (byte-identical)
# if reverted → RED because the test would fail on the assertion comparing
# flag-ON vs flag-OFF detector output
# ---------------------------------------------------------------------------
class TestFlagOffIdentical:
    def test_detector_without_cvd_confirm_unchanged(self):
        """Without cvd_confirm_drive=True, detector ignores cvd_pos for OPEN_DRIVE."""
        r_no_flag = detect_opening_type(DRIVE_DN_BARS, 100.0, **FAR)
        r_with_cvd_no_confirm = detect_opening_type(
            DRIVE_DN_BARS, 100.0, cvd_pos=0.9, cvd_confirm_drive=False, **FAR,
        )
        assert r_no_flag["opening_type"] == r_with_cvd_no_confirm["opening_type"]
        assert r_no_flag["direction"] == r_with_cvd_no_confirm["direction"]
        # Both should be OPEN_DRIVE (CVD divergence ignored when confirm=False)
        assert r_no_flag["opening_type"] == "OPEN_DRIVE"

    def test_gate_flag_off_allows_everything(self):
        """OPENING_FIRE_CVD_V1=0 → gate behavior identical to before."""
        dn_bars_6 = [
            B(100, 100.0, 99.4, 99.5), B(99.5, 99.6, 98.9, 99.0),
            B(99.0, 99.1, 97.9, 98.0), B(98.0, 98.1, 96.9, 97.0),
            B(97.0, 97.1, 96.0, 96.2), B(96.2, 96.3, 95.0, 95.2),
        ]
        with patch.dict(os.environ, {
            "OPENING_TYPE_GATE": "1",
            "OPENING_FIRE_CVD_V1": "0",
        }):
            from backend.v9.systems.opening_type_gate import decide
            allow, reason = decide(
                direction="SHORT", rth_bars=dn_bars_6, ib_locked=False,
            )
            # Drive-down → SHORT is with-drive → allowed (no CVD check)
            assert allow is True
            assert "with-drive" in reason
