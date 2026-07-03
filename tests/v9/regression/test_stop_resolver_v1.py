"""Item-4: STOP_RESOLVER_V1 — structural stop band enforcement.

Anti-tautological: calls the REAL resolve_stop. Tests that FAIL on old code
(no resolver) and PASS with the resolver.

Contract: docs/handoff/CC_HANDOFF_CONTRACT.md

Measured baselines (07-02, post BE-artifact filter):
  REACTIVE 10.8-12pt · FLAGS 15.6pt · GHOST 13pt · FAMIR 11.3pt
  VEGAS 11pt · ZLR 8.5pt · INITIATIVE 6.5-8.3pt · HTLB 5.3pt
"""
import pytest
from backend.v9.systems.stop_anchors.stop_resolver import resolve_stop, StopResolverResult

ATR = 7.0  # representative ATR_5m


# ---------------------------------------------------------------------------
# Test 1: stop too close → skips to next rung
# if reverted → RED because without the floor, the tight stop is accepted
# ---------------------------------------------------------------------------
class TestFloorSkipsToNextRung:
    def test_b3_too_close_uses_b2(self):
        """REACTIVE LONG: b3_low 1pt from entry (below floor 3.5pt) → b2_low used."""
        r = resolve_stop(
            direction="LONG", entry_price=7550.0,
            rungs=[7549.0, 7545.0, 7540.0],  # b3, b2, w4 (prices, not offsets)
            rung_names=["b3_low", "b2_low", "w4_zone"],
            atr_5m=ATR, family="REV",
        )
        assert not r.rejected
        assert r.in_band
        assert r.rung_name == "b2_low", f"Expected b2_low, got {r.rung_name}"
        assert r.risk_points >= 3.5, "Must respect the floor"

    def test_single_rung_below_floor_rejected(self):
        """ZLR with a 1pt stop → rejected (no_stop_in_band)."""
        r = resolve_stop(
            direction="LONG", entry_price=7550.0,
            rungs=[7549.0],  # only rung, 1pt from entry
            rung_names=["breakout_bar"],
            atr_5m=ATR, family="CONT",
        )
        assert r.rejected or r.risk_points >= 3.5


# ---------------------------------------------------------------------------
# Test 2: stop too far → rejected (no_stop_in_band)
# if reverted → RED because without the cap, the 20pt stop is accepted
# ---------------------------------------------------------------------------
class TestCapRejects:
    def test_all_rungs_above_cap_rejected(self):
        """All rungs farther than 1.2×ATR (8.4pt for CONT) → rejected."""
        r = resolve_stop(
            direction="LONG", entry_price=7550.0,
            rungs=[7540.0, 7535.0],  # 10pt, 15pt — both above 8.4 CONT cap
            rung_names=["breakout_bar", "b2_low"],
            atr_5m=ATR, family="CONT",
        )
        assert r.rejected

    def test_rev_has_wider_cap(self):
        """REV cap = 1.5×ATR (10.5pt) → a 9pt rung passes for REV but not CONT."""
        r_rev = resolve_stop(
            direction="LONG", entry_price=7550.0,
            rungs=[7541.0],  # 9pt + 0.75 offset = 9.75pt < 10.5 REV cap
            rung_names=["swing_extreme"],
            atr_5m=ATR, family="REV",
        )
        r_cont = resolve_stop(
            direction="LONG", entry_price=7550.0,
            rungs=[7541.0],  # 9.75pt > 8.4 CONT cap
            rung_names=["breakout_bar"],
            atr_5m=ATR, family="CONT",
        )
        assert not r_rev.rejected, "9.75pt should pass for REV (cap=10.5)"
        assert r_cont.rejected, "9.75pt should be rejected for CONT (cap=8.4)"


# ---------------------------------------------------------------------------
# Test 3: in-band rung selected
# if reverted → RED because there's no resolver to call
# ---------------------------------------------------------------------------
class TestInBandSelection:
    def test_first_valid_rung_selected(self):
        """INITIATIVE LONG: breakout_bar at 5pt (in band [3.5, 8.4]) → selected."""
        r = resolve_stop(
            direction="LONG", entry_price=7550.0,
            rungs=[7545.0],  # 5pt
            rung_names=["breakout_bar"],
            atr_5m=ATR, family="CONT",
        )
        assert not r.rejected
        assert r.in_band
        assert r.rung_name == "breakout_bar"
        assert abs(r.risk_points - 5.75) < 0.5  # 5pt + 0.75 offset ≈ 5.75

    def test_htlb_5_3pt_in_band(self):
        """HTLB (REV): typical stop 5.3pt — within [3.5, 10.5]."""
        r = resolve_stop(
            direction="SHORT", entry_price=7550.0,
            rungs=[7555.3],  # 5.3pt above entry
            rung_names=["consolidation_extreme"],
            atr_5m=ATR, family="REV",
        )
        assert not r.rejected
        assert r.in_band


# ---------------------------------------------------------------------------
# Test 4: grid alignment
# if reverted → RED because stops must be on the MES tick grid
# ---------------------------------------------------------------------------
class TestGridAlignment:
    def test_stop_on_grid(self):
        """Resolved stop must be on the 0.25 tick grid."""
        r = resolve_stop(
            direction="LONG", entry_price=7550.0,
            rungs=[7544.3],  # non-grid price
            rung_names=["b2_low"],
            atr_5m=ATR, family="REV",
        )
        assert not r.rejected
        assert abs((r.stop_price / 0.25) - round(r.stop_price / 0.25)) < 1e-9, \
            f"Stop {r.stop_price} not on 0.25 grid"


# ---------------------------------------------------------------------------
# Test 5: hard cap 25pt
# if reverted → RED because the hard cap is explicit in the spec
# ---------------------------------------------------------------------------
class TestHardCap:
    def test_hard_cap_25pt(self):
        """Even with high ATR, cap never exceeds 25pt."""
        r = resolve_stop(
            direction="LONG", entry_price=7550.0,
            rungs=[7520.0],  # 30pt — above any ATR-relative cap
            rung_names=["extreme"],
            atr_5m=20.0,  # high ATR
            family="REV",
        )
        assert r.rejected or r.risk_points <= 26.0  # 25 + offset tolerance
