"""Regression: pre_fire stop-sanity gates (MEMS_MIN_RISK_POINTS / MEMS_MAX_RISK_POINTS).

Why: the 06-09 replay showed two degenerate-stop classes that still routed —
  • S2 Initiative/Bull-Flag fired with 1-pt stops (instant stop-out, −1pt noise).
  • S4 reversal (HTLB) fired with a 110-pt swing anchor; the size gate could
    only shrink it to 1 contract, not refuse it (still ~$550 risk).
Both clear the R:R gate (reward = risk × mult ≥ risk), so a dedicated min/max
risk gate is needed. Shared validator → covers S2 *and* S4.

These call the PRODUCTION validate_fire (no duplicated logic). Default OFF
(env unset) — no behaviour change until the env is set.

RED-on-revert: delete either gate and the matching flag-ON test FAILS (the
degenerate/oversized request comes back valid).
"""
import pytest

from backend.v9.shared.pre_fire_validator import FireRequest, validate_fire


def _req(entry, stop, t1, direction="SHORT"):
    return FireRequest(
        system_id="T2_WOODIES", direction=direction, entry_price=entry,
        stop_price=stop, t1_price=t1, t2_price=None,
        time_stop_minutes=90, confidence=70,
    )


@pytest.fixture
def env(monkeypatch):
    def _set(**kv):
        for k, v in kv.items():
            if v is None:
                monkeypatch.delenv(k, raising=False)
            else:
                monkeypatch.setenv(k, str(v))
    return _set


def test_gates_off_by_default(env):
    """Env unset → degenerate (1pt) AND oversized (110pt) both still pass."""
    env(MEMS_MIN_RISK_POINTS=None, MEMS_MAX_RISK_POINTS=None)
    assert validate_fire(_req(7387.25, 7388.25, 7385.0)).valid is True   # 1-pt
    assert validate_fire(_req(7254.75, 7364.00, 7233.0)).valid is True   # 110-pt


def test_min_risk_rejects_degenerate_stop(env):
    """MEMS_MIN_RISK_POINTS=2 → the 1-pt S2 stop is rejected; a real 25-pt stop passes."""
    env(MEMS_MIN_RISK_POINTS=2, MEMS_MAX_RISK_POINTS=None)
    r = validate_fire(_req(7387.25, 7388.25, 7385.0))   # risk 1.0pt
    assert r.valid is False and "degenerate" in r.fail_reason
    assert validate_fire(_req(7465.50, 7490.75, 7440.0)).valid is True   # risk 25.25pt


def test_max_risk_rejects_oversized_stop(env):
    """MEMS_MAX_RISK_POINTS=60 → the 110-pt reversal stop is rejected; a 44-pt stop passes."""
    env(MEMS_MIN_RISK_POINTS=None, MEMS_MAX_RISK_POINTS=60)
    r = validate_fire(_req(7254.75, 7364.00, 7233.0))   # risk 109.25pt
    assert r.valid is False and "oversized" in r.fail_reason
    assert validate_fire(_req(7362.50, 7406.25, 7345.0)).valid is True   # risk 43.75pt


def test_both_gates_together(env):
    """Both set → only the sane middle band routes."""
    env(MEMS_MIN_RISK_POINTS=2, MEMS_MAX_RISK_POINTS=60)
    assert validate_fire(_req(7387.25, 7388.25, 7385.0)).valid is False   # 1pt   → min
    assert validate_fire(_req(7254.75, 7364.00, 7233.0)).valid is False   # 110pt → max
    assert validate_fire(_req(7461.25, 7491.75, 7449.0)).valid is True    # 30.5pt → ok
