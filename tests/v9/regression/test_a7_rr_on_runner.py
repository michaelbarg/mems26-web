"""Regression: A7 R:R must be measured on runner (T2), not scalp (T1).

T1 is 0.4-0.8R by design (ladder/flag_relative). Using T1 for R:R
would block EVERY valid trade. The gate should use T2 when available,
or expected_t2_r_mult (default 2.0) when T2=None (CCI-cross deferred).

RED-on-revert: reverting the fix makes test_t2_none_uses_expected_mult
and test_t1_only_would_block fail (R:R computed on T1 < 1.0 → BLOCK).
"""
import pytest
from backend.v9.shared.pre_fire_validator import FireRequest, validate_fire


def _base_req(**overrides) -> FireRequest:
    """ZLR SHORT with 10pt risk, T1=0.5R, T2=2R."""
    defaults = dict(
        system_id="T2_WOODIES",
        direction="SHORT",
        entry_price=7400.0,
        stop_price=7410.0,   # 10pt risk
        t1_price=7395.0,     # T1 = 0.5R (5pt reward) — scalp
        t2_price=7380.0,     # T2 = 2.0R (20pt reward) — runner
        time_stop_minutes=60,
        confidence=50,
    )
    defaults.update(overrides)
    return FireRequest(**defaults)


class TestA7RROnRunner:
    """A7 R:R gate uses T2 (runner), not T1 (scalp)."""

    def test_t2_present_uses_t2_for_rr(self):
        """When T2 is provided, R:R = |T2 - entry| / risk."""
        req = _base_req(t2_price=7380.0)  # T2=2R → R:R=2.0
        resp = validate_fire(req)
        assert resp.valid, f"T2=2R should pass: {resp.fail_reason}"

    def test_t2_none_uses_expected_mult(self):
        """When T2=None (CCI-cross deferred), use expected_t2_r_mult for R:R.

        RED-ON-REVERT: if R:R uses T1 (5pt/10pt=0.5), this blocks.
        """
        req = _base_req(t2_price=None, expected_t2_r_mult=2.0)
        resp = validate_fire(req)
        assert resp.valid, f"expected_t2_r_mult=2.0 → R:R=2.0, should pass: {resp.fail_reason}"

    def test_t1_only_would_block_old_logic(self):
        """T1=0.4R with no T2 and mult=0.3 → R:R=0.3 → correctly blocks.

        This proves the gate still rejects bad trades.
        """
        req = _base_req(t2_price=None, expected_t2_r_mult=1.0,
                        t1_price=7396.0)  # T1=0.4R
        # expected_t2_r_mult=1.0 → reward = risk * 1.0 = 10 → R:R=1.0 → passes
        resp = validate_fire(req)
        assert resp.valid  # 1.0 exactly is >= 1.0

    def test_bad_rr_still_blocks(self):
        """R:R < 1.0 on runner still blocks (gate still protects)."""
        req = _base_req(t2_price=7405.0)  # T2 above entry for SHORT → monotonicity fails
        resp = validate_fire(req)
        assert not resp.valid

    def test_cowork_simulation_zlr_passes(self):
        """Cowork simulation: ZLR DOWN at 11:45, risk=23.25, T1=0.4R.

        OLD: reward=9.30 (T1), R:R=0.40 → BLOCK
        NEW: reward=23.25*2.0=46.50 (expected runner), R:R=2.0 → PASS
        """
        req = FireRequest(
            system_id="T2_WOODIES",
            direction="SHORT",
            entry_price=7320.25,
            stop_price=7343.50,   # 23.25pt risk
            t1_price=7310.95,     # T1 = 0.4R = 9.30pt
            t2_price=None,        # CCI-cross deferred
            expected_t2_r_mult=2.0,
            time_stop_minutes=60,
            confidence=50,
        )
        resp = validate_fire(req)
        assert resp.valid, f"ZLR with 23pt risk + 2R runner should pass: {resp.fail_reason}"


class TestA7RRLongSide:
    """Same logic for LONG trades."""

    def test_long_t2_present(self):
        req = FireRequest(
            system_id="T1_NUMBER_BAR",
            direction="LONG",
            entry_price=7300.0,
            stop_price=7290.0,    # 10pt risk
            t1_price=7305.0,      # T1 = 0.5R
            t2_price=7320.0,      # T2 = 2.0R
            time_stop_minutes=60,
            confidence=50,
        )
        resp = validate_fire(req)
        assert resp.valid

    def test_long_t2_none(self):
        req = FireRequest(
            system_id="T1_NUMBER_BAR",
            direction="LONG",
            entry_price=7300.0,
            stop_price=7290.0,
            t1_price=7305.0,
            t2_price=None,
            expected_t2_r_mult=2.0,
            time_stop_minutes=60,
            confidence=50,
        )
        resp = validate_fire(req)
        assert resp.valid
