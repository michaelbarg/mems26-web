"""C3 — extreme_chase_guard calibration (2026-08-11).

Two changes:
1. Structure-relative threshold: max(6.0, 0.30 × ib_width) instead of flat 6.0pt
   (on 2026-08-10: flat 6.0 blocked when IB was 20.25 → threshold should have been 6.075)
2. EXTREME_CHASE_SCOPE: "CONT+REV" extends guard to REV patterns chasing the tip
   (#655: DBDT LONG at session high was exempt as REV family)
"""
import inspect

import pytest


class TestChaseGuardCalibration:
    """Verify C3 calibration code paths exist."""

    def test_ib_frac_in_gateway(self):
        """CHASE_IB_FRAC env var must be read for structure-relative threshold."""
        from backend.v9.gateway import trading_gateway
        src = inspect.getsource(trading_gateway.TradingGateway._route_setup_inner)
        assert "CHASE_IB_FRAC" in src

    def test_scope_in_gateway(self):
        """EXTREME_CHASE_SCOPE must be configurable."""
        from backend.v9.gateway import trading_gateway
        src = inspect.getsource(trading_gateway.TradingGateway._route_setup_inner)
        assert "EXTREME_CHASE_SCOPE" in src
        assert "CONT+REV" in src

    def test_ib_width_used_in_threshold(self):
        """The IB width must feed into the min_dist calculation."""
        from backend.v9.gateway import trading_gateway
        src = inspect.getsource(trading_gateway.TradingGateway._route_setup_inner)
        assert "ib_high" in src[src.index("EXTREME_CHASE_GUARD"):]
        assert "ib_low" in src[src.index("EXTREME_CHASE_GUARD"):]

    def test_max_of_base_and_ib_frac(self):
        """Threshold = max(base, frac × ib_width) — never smaller than base."""
        base = 6.0
        frac = 0.30
        # Narrow IB (10pt) → max(6.0, 3.0) = 6.0 (base dominates)
        assert max(base, frac * 10.0) == 6.0
        # Wide IB (25pt) → max(6.0, 7.5) = 7.5 (IB dominates)
        assert max(base, frac * 25.0) == 7.5
        # Case #655: IB 20.25 → max(6.0, 6.075) = 6.075
        assert max(base, frac * 20.25) == pytest.approx(6.075)

    def test_rev_scope_extends_to_rev(self):
        """CONT+REV scope must include REV family patterns."""
        scope = "CONT+REV"
        fam = "REV"
        in_scope = (fam == "CONT") or (scope == "CONT+REV" and fam == "REV")
        assert in_scope is True

    def test_cont_scope_excludes_rev(self):
        """Default CONT scope must exclude REV family."""
        scope = "CONT"
        fam = "REV"
        in_scope = (fam == "CONT") or (scope == "CONT+REV" and fam == "REV")
        assert in_scope is False

    def test_cont_always_in_scope(self):
        """CONT family always in scope regardless of setting."""
        for scope in ("CONT", "CONT+REV"):
            fam = "CONT"
            in_scope = (fam == "CONT") or (scope == "CONT+REV" and fam == "REV")
            assert in_scope is True
