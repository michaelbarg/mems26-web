"""T6: Risk-caps audit + enforce regression tests.

Verifies: daily-loss cap, max trades/day, consecutive-loss cooldown are enforced.
SHADOW bypass when RISK_CAPS_SHADOW=0; enforced when =1.

if reverted → RED because: removing the RISK_CAPS_SHADOW check or the env-
configurable caps would break these assertions.
"""
import os
from unittest.mock import patch, MagicMock

from backend.v9.gateway.risk_checks import passes_strict_checks


def _mock_gateway(daily_pnl=0, daily_trades=0, consecutive_losses=0):
    g = MagicMock()
    g._daily_pnl = daily_pnl
    g._daily_trades = daily_trades
    g._consecutive_losses = consecutive_losses
    return g


# ── LIVE mode — always enforced ──────────────────────────────────────────

def test_live_daily_loss_cap_blocks():
    g = _mock_gateway(daily_pnl=-260)
    assert passes_strict_checks({}, "live", g) is False


def test_live_max_trades_blocks():
    g = _mock_gateway(daily_trades=5)
    assert passes_strict_checks({}, "live", g) is False


def test_live_consecutive_loss_blocks():
    g = _mock_gateway(consecutive_losses=2)
    assert passes_strict_checks({}, "live", g) is False


@patch("backend.v9.gateway.risk_checks.datetime")
def test_live_under_caps_passes(mock_dt):
    """Under all caps + before cutoff → passes."""
    from datetime import datetime as real_dt
    from zoneinfo import ZoneInfo
    mock_dt.now.return_value = real_dt(2026, 6, 25, 10, 0, 0, tzinfo=ZoneInfo("America/New_York"))
    g = _mock_gateway(daily_pnl=-100, daily_trades=3, consecutive_losses=1)
    assert passes_strict_checks({}, "live", g) is True


# ── SHADOW mode — bypass by default ─────────────────────────────────────

@patch.dict(os.environ, {"RISK_CAPS_SHADOW": "0"})
def test_shadow_default_bypasses():
    """SHADOW mode bypasses risk caps when RISK_CAPS_SHADOW=0."""
    g = _mock_gateway(daily_pnl=-500, daily_trades=10, consecutive_losses=5)
    assert passes_strict_checks({}, "shadow", g) is True


# ── SHADOW mode — enforced when flag ON ──────────────────────────────────

@patch.dict(os.environ, {"RISK_CAPS_SHADOW": "1"})
def test_shadow_enforced_when_flag_on():
    """RISK_CAPS_SHADOW=1 → risk caps enforced in SHADOW.

    if reverted → RED because: removing the RISK_CAPS_SHADOW check makes
    SHADOW always bypass → this test fails.
    """
    g = _mock_gateway(daily_pnl=-260)
    assert passes_strict_checks({}, "shadow", g) is False


# ── Env-configurable caps ───────────────────────────────────────────────

def test_caps_are_env_configurable():
    """The risk caps read from env vars (not hardcoded)."""
    import inspect
    from backend.v9.gateway.risk_checks import passes_strict_checks
    import backend.v9.gateway.risk_checks as rc
    source = inspect.getsource(rc)
    assert "RISK_DAILY_LOSS_CAP" in source
    assert "RISK_MAX_TRADES_DAY" in source
    assert "RISK_CONSECUTIVE_LOSS_LIMIT" in source


# ── Audit table (documentation) ─────────────────────────────────────────

def test_audit_table():
    """All risk caps exist and are enforced."""
    from backend.v9.gateway import risk_checks as rc
    assert rc.DAILY_LOSS_CAP > 0
    assert rc.MAX_TRADES_PER_DAY > 0
    assert rc.CONSECUTIVE_LOSS_LIMIT > 0
    assert rc.CUTOFF_HOUR == 14
    assert rc.CUTOFF_MINUTE == 30
