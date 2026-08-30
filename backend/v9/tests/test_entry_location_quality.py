"""ENTRY_LOCATION_QUALITY_V1 — position quality gate tests.

28.08 anchor: 17:00/17:35 pass (base of leg), 18:15/18:25 fail (top of leg).
Leg: base ~7730 (session low), extreme ~7782.5 (session high), L ≈ 52.5.
"""
from backend.v9.systems.entry_location_quality import assess_entry_quality


# 28.08 leg parameters
LEG_BASE = 7730.0      # session low (reversal point)
LEG_EXTREME = 7782.5   # session high
ATR = 8.0
VAH = 7771.5
VAL = 7755.5


class TestAnchor28Aug:
    """28.08 replay: early entries pass, late entries fail."""

    def test_1700_long_at_base_passes(self):
        """17:00 OPENING_DRIVE @7749.75 → pos ≈ 0.38 → PASS."""
        r = assess_entry_quality(
            entry_price=7749.75, direction="LONG",
            leg_base=LEG_BASE, leg_extreme=LEG_EXTREME,
            stop_distance=6.0, atr=ATR, vah=VAH, val=VAL)
        assert r["pass"], f"17:00 should pass: {r['reasons']}"
        assert r["pos"] < 0.5
        assert r["label"] in ("base", "mid")

    def test_1735_long_at_base_passes(self):
        """17:35 ZLR @7750.75 → pos ≈ 0.40 → PASS."""
        r = assess_entry_quality(
            entry_price=7750.75, direction="LONG",
            leg_base=LEG_BASE, leg_extreme=LEG_EXTREME,
            stop_distance=7.0, atr=ATR, vah=VAH, val=VAL)
        assert r["pass"], f"17:35 should pass: {r['reasons']}"

    def test_1815_long_chaser_fails(self):
        """18:15 @7774.00 → pos ≈ 0.84 → FAIL (chaser)."""
        r = assess_entry_quality(
            entry_price=7774.0, direction="LONG",
            leg_base=LEG_BASE, leg_extreme=LEG_EXTREME,
            stop_distance=15.0, atr=ATR, vah=VAH, val=VAL)
        assert not r["pass"], "18:15 should fail (chaser)"
        assert r["label"] == "chaser"
        assert any("chaser" in reason for reason in r["reasons"])

    def test_1825_long_chaser_fails(self):
        """18:25 @7777.75 → pos ≈ 0.91 → FAIL (chaser + beyond value)."""
        r = assess_entry_quality(
            entry_price=7777.75, direction="LONG",
            leg_base=LEG_BASE, leg_extreme=LEG_EXTREME,
            stop_distance=18.0, atr=ATR, vah=VAH, val=VAL)
        assert not r["pass"], "18:25 should fail (chaser + beyond value)"
        assert r["pos"] > 0.85


class TestIndividualChecks:
    """Each check works independently."""

    def test_expensive_stop(self):
        r = assess_entry_quality(
            entry_price=7760.0, direction="LONG",
            leg_base=LEG_BASE, leg_extreme=LEG_EXTREME,
            stop_distance=15.0, atr=ATR, vah=VAH, val=VAL)
        assert any("expensive_stop" in reason for reason in r["reasons"])

    def test_cheap_stop_passes(self):
        r = assess_entry_quality(
            entry_price=7750.0, direction="LONG",
            leg_base=LEG_BASE, leg_extreme=LEG_EXTREME,
            stop_distance=5.0, atr=ATR, vah=VAH, val=VAL)
        assert r["pass"]

    def test_pullback_exempts_chaser(self):
        """A chaser position WITH a pullback is allowed."""
        r = assess_entry_quality(
            entry_price=7775.0, direction="LONG",
            leg_base=LEG_BASE, leg_extreme=LEG_EXTREME,
            stop_distance=5.0, atr=ATR, vah=VAH, val=VAL,
            has_pullback=True)
        # pos is still high but pullback exempts the chaser check
        assert not any("chaser" in reason for reason in r["reasons"])


class TestMissingData:
    """Rule 1: missing data → check skipped, not synthetic block."""

    def test_no_leg_skips_pos(self):
        r = assess_entry_quality(
            entry_price=7775.0, direction="LONG",
            leg_base=None, leg_extreme=None,
            stop_distance=5.0, atr=ATR, vah=VAH, val=VAL)
        assert r["pos"] is None
        assert r["pass"], "Missing leg → pos check skipped → pass"

    def test_no_atr_skips_rr(self):
        r = assess_entry_quality(
            entry_price=7775.0, direction="LONG",
            leg_base=LEG_BASE, leg_extreme=LEG_EXTREME,
            stop_distance=15.0, atr=None, vah=VAH, val=VAL)
        assert r["rr"] is None

    def test_no_vah_val_skips_ex(self):
        r = assess_entry_quality(
            entry_price=7775.0, direction="LONG",
            leg_base=LEG_BASE, leg_extreme=LEG_EXTREME,
            stop_distance=5.0, atr=ATR, vah=None, val=None)
        assert r["ex"] is None


class TestShortMirror:
    """SHORT is the exact mirror of LONG."""

    def test_short_at_base_passes(self):
        r = assess_entry_quality(
            entry_price=7775.0, direction="SHORT",
            leg_base=LEG_EXTREME, leg_extreme=LEG_BASE,
            stop_distance=5.0, atr=ATR, vah=VAH, val=VAL)
        assert r["pass"]
        assert r["pos"] < 0.5

    def test_short_chaser_at_bottom_fails(self):
        r = assess_entry_quality(
            entry_price=7735.0, direction="SHORT",
            leg_base=LEG_EXTREME, leg_extreme=LEG_BASE,
            stop_distance=5.0, atr=ATR, vah=VAH, val=VAL)
        assert not r["pass"]
        assert r["label"] == "chaser"
